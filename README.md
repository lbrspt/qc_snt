## v8.4 — Descrições (Memo Main) sincronizadas no upload de tecido

| Problema | Correção |
|---|---|
| **Ficheiro novo carregado, mas o Memo (Main) continuava "antigo" na grelha** | Causa raiz: a coluna **Descrição** da grelha A Chegar vem do **catálogo** (`fabric_refs`, via JOIN) — que o reset **preserva por design** — e o upload só inseria descrições para refs **novas**; as existentes nunca eram atualizadas. O Item Number ficava bem porque vive na própria linha da encomenda. O upload de tecido passa a fazer **UPDATE da descrição** de todas as refs presentes no ficheiro sempre que o Memo (Main) diferir; quando a mesma ref tem memos diferentes em várias POs, **ganha o da PO mais recente** (Creation Date). Memos vazios nunca apagam a descrição existente. A mensagem de sucesso indica quantas descrições foram atualizadas |

**Nota:** não precisas de reset para isto fazer efeito — basta voltar a carregar o ficheiro de encomendas de tecido atual e as descrições do catálogo ficam sincronizadas com os memos desse ficheiro.

---

## v8.3 — Reset & Recarga sem "memória" · upload de tecido é snapshot do ficheiro

| Problema | Correção |
|---|---|
| **"O sistema parece ter memória" — após reset + recarga, o tecido a chegar mostrava os dados do ficheiro antigo** | Três fontes de "memória" fechadas: **(1)** o reset passa a limpar também a sessão de uploads — as marcas "ficheiro já carregado" e os ficheiros retidos nos uploaders desaparecem, tudo fresco no mesmo separador, sem F5; **(2)** após cada carga bem-sucedida o ficheiro é largado do uploader — deixa de ser possível re-carregar o ficheiro velho por engano (era a origem mais provável: o uploader guardava o ficheiro anterior entre ações); **(3)** o upload de tecido passa a ser **snapshot exato do ficheiro** — linhas em aberto (EXPECTED) que já não venham no ficheiro são **apagadas**, quantidades alteradas são atualizadas. A tabela fica **exatamente** como o ficheiro carregado |
| **Re-upload podia fazer regredir uma PO já faturada/em trânsito para EXPECTED** | UPSERT condicional: só linhas EXPECTED são atualizadas. Faturadas, em trânsito e recebidas **nunca são tocadas** pelo upload (mantêm destino, fatura e estado) |
| **Sem forma de limpar só o tecido a chegar** | Novo botão **🧹 Limpar encomendas de tecido em aberto (EXPECTED)** na secção b) do Reset & Recarga — limpa só o tecido a chegar sem reset completo |
| **Pouca visibilidade do que foi carregado** | A mensagem de sucesso do upload de tecido indica agora **nome do ficheiro, linhas, POs, metros e linhas removidas**; a pré-visualização também mostra o nome e os totais do ficheiro — vês sempre o que está a entrar |

**Como aplicar:** copiar `app.py` → commit → Railway. **Sem re-seed** — o nome da BD não muda e as migrações são idempotentes.

---

## v8.2 — Movimentar funciona com os lotes agregados (tokens AGG-)

| Problema | Correção |
|---|---|
| **Após a importação de stock, M1/M2/M3 sem opções ("No options to select")** | Os três caminhos do ⚙️ Movimentar filtravam por prefixo de token da era pré-v8: M1 Rolos Conhecidos e M3 Metros Consolidados só viam `R-` (receções manuais), M2 Lote Agregado só via `P-` (divisões). Os lotes do upload v8 (`AGG-####`) ficavam fora de todos. **M1 e M3 passam a aceitar qualquer token** AVAILABLE; **M2 aceita `P-` e `AGG-`** (incluindo os em processo — é por aqui que devolves excedente a stock). O corte (Passo B) e o Regularizar já não filtravam por prefixo. Testado: 23 refs AVAILABLE, 94 lotes em M2 (29 em processo), FIFO M3 sobre lotes AGG com conservação total 84.764,9m |

**Nota — Lote Agregado vs Metros Consolidados:** com o novo stock sobrepõem-se bastante, mas não são iguais: **M2** move/divide **um lote específico** (e é o único que mostra lotes **em processo**, para devolver a stock); **M3** move **X metros em FIFO** de uma ref+armazém (pode tirar de vários rolos) e cria um lote novo no destino. Para o stock agregado atual, M3 acaba quase sempre por dividir o mesmo lote AGG — mas continua a ser o caminho rápido "metros → destino".

---

## v8.1 — POs em curso: corte consome SEMPRE o em processo primeiro (armazém partilhado)

| Situação | Correção |
|---|---|
| **POs garment em curso (Fabrijeans / Costa Correia) com tecido já em processo** | O upload do audit guardou o em processo FJ/CC no armazém `Fabrijeans / Costa C`, mas as POs garment vêm com confeccionador `Fabrijeans` ou `Costa Correia`. O Passo A do corte (atribuir token a rolos já em processo sem token) fazia correspondência exata `armazém = confeccionador` — para estas POs saltava o em processo e ia buscar stock novo. Passa a procurar em **todo o armazém físico partilhado** (`wh_group`/`wh_members`, v5.1): a PO consome **primeiro o em processo agregado**, com divisão exata, e só o que faltar vem de stock. Rolos divididos mantêm o armazém físico onde estão. Testado end-to-end com os ficheiros reais: corte acumulado 500+200m todo do em processo, stock intocado, faturação exata 700m |

**Procedimento recomendado para POs em curso (qualquer confeccionador):**
1. Carrega as POs garment (⚙️ Sistema » 🔄 Reset & Recarga » c).
2. Na tabela de **👕 Produção**, completa **ref de tecido** e **cor exata do lote em processo** (o dropdown de cores já oferece as cores em stock, incluindo as dos lotes agregados) e o molde base, se pedido.
3. Se a PO **já cortou** peças antes do arranque: regista um **corte de arranque** com as pcs e metros reais já cortados (notas: "corte acumulado — arranque"). A partir daí regista os cortes normalmente.
4. Ao registar cada corte, o sistema atribui o token **primeiro aos lotes em processo sem token** desse confeccionador (ref+cor, FIFO, divisão exata) — **não desconta stock enquanto houver em processo**. Reconciliação cumulativa: ligado = soma dos consumos registados, nunca duplica.
5. Ao faturar: deduz de em processo **exatamente** os metros consumidos; se houver excedente ligado, é libertado (fica em processo sem token, reutilizável por outras POs).

---

## v8.0 — SNT APS Portugal · contraste do tema clean · Reset & Recarga de dados

| Pedido | Implementação |
|---|---|
| **Tema clean sem contraste no texto** | Causa raiz: o Streamlit segue o **tema do sistema operativo** (claro/escuro) para os elementos internos dos widgets — com o SO em escuro, o menu lateral, os selectboxes e as caixas de texto herdavam texto claro sobre o fundo claro do tema clean. Novo bloco CSS força as cores do tema da app em **todos** os elementos internos (menu lateral, selectboxes, inputs, tabs, expanders, file uploaders, dropdowns). Verificado em browser real nas **4 combinações** (dark/clean × SO claro/escuro) |
| **Limpar cabeçalho e rodapé + novo nome** | Rebrand **SNT APS Portugal · Stock & Produção** (sidebar, cabeçalho, rodapé, título do separador). Removidos: brand-line "SNT · CMT · ULTRA", badge AUTO, subtítulo com versão "v7.4 \| CW29 2026" e rodapé fixo "v7.1 \| Dados: CW29 2026". Cabeçalho e rodapé mostram agora **data e semana CW atuais calculadas em runtime**, a título indicativo |
| **Reset dos dados de stock e encomendas** | Novo menu **⚙️ Sistema » 🔄 Reset & Recarga**: **1)** download de backup da BD (ponto de restauro); **2)** reset seguro com confirmação escrita `RESET` — apaga rolos/lotes, tecido a chegar, POs garment, consumos e movimentos; **preserva** catálogo de refs, **mapas de consumo (standards por molde)**, parâmetros de planeamento e configurações. O reset fica registado no sync_log |
| **a) Novo stock agregado (audit Excel)** | Upload da folha `stock_CWxx`: cada célula **(stock)** vira **1 lote AVAILABLE** e cada **(in process)** **1 lote IN_PROCESS** nessa entidade (tokens `AGG-####`, lotes agregados de metros — novos uploads por rolo geram tokens próprios). Reconciliação visível antes de carregar (ficheiro vs a importar). Ajustes negativos do audit são compensados no maior lote da linha, com nota — o total importado bate certo com o ficheiro (**84.764,9m** no audit CW31) |
| **b) Tecido a chegar (PurchaseOrders NetSuite)** | Uma linha por **PO · ref · cor** (POs multi-cor divididas com sufixo `PO·Cor`). Ref casada por prefixo com o catálogo; refs novas entram automaticamente. Estado EXPECTED — destino atribuído depois na grelha A Chegar (v7.4) |
| **c) Encomendas garment (PurchaseOrders NetSuite)** | POs finais importadas como PENDING **sem ref de tecido** (o ficheiro não traz) — confeccionador mapeado para os nomes canónicos; completas ref/cor na tabela de Produção para ativar planeamento e tokens |
| **d) Histórico de consumos (All PO 2023-2026)** | Lê as sheets por ano (aliases de colunas por ano, deduplica linhas exatas), insere consumos **validados** (não poluem as aprovações), **cria as POs antigas como INVOICED** (ligação ref/molde para o recálculo), atualiza ref/cor em POs existentes e **recalcula o real médio do mapa** — os **standards por molde não são alterados**. No fim, **avisa a lista de modelos sem molde base** no mapa para alocares em 📊 Consumos |

> **Como aplicar (Railway):** copiar `app.py` → commit → deploy. **Não** re-seedar: o reset é feito por ti dentro da app (⚙️ Sistema » 🔄 Reset & Recarga), com backup descarregado antes. Os seeds de arranque continuam byte-idênticos aos da v5.0 (só correm em BD vazia).

---

## v7.4 — Receção de matéria-prima unificada · faturação exata (excedente volta a processo/stock)

| Pedido | Implementação |
|---|---|
| **Unificar a chegada de matéria-prima (havia 2 menus)** | Tudo o que é entrada de tecido vive agora em **📦 Stock » 🚢 A Chegar** com 3 separadores: **📋 Encomendas** (grelha + nova encomenda + carga em massa + marcar chegada + timeline), **📥 Receção** (registo manual de rolos — saiu de ⚙️ Movimentar) e **📤 Packing list** (idem). ⚙️ Movimentar fica só com movimentações internas (M1/M2/M3) e faturação. Um só ponto de entrada → os dados comunicam com todo o sistema (stock, planeamento, alertas, consumos leem a mesma BD em direto) |
| **"Em A Chegar não consigo atribuir armazém"** | A coluna **destino** (armazém/confeccionador) passa a ser **editável na grelha** — e se o rolo em trânsito já existir, move-se com ela. O formulário de nova encomenda já tinha destino; a receção manual e a packing list têm seletor próprio |
| **Metragem atualizada → remanescente em processo ou de volta a stock** | **Faturação EXATA** (nos dois caminhos: tabela de produção e ⚙️ Movimentar » Faturação): deduz de em processo **apenas os metros consumidos** em cortes, com divisão exata do último rolo. Se corrigires um consumo para baixo (📐 Consumos » editar registos), o **excedente ligado à PO perde o token e fica IN_PROCESS no confeccionador** — reflete-se em processo, é **reutilizado automaticamente pelo próximo corte de outra PO nesse confeccionador** (v7.2), e se não tiver uso moves-no para stock em ⚙️ Movimentar (como AVAILABLE já não precisa de token). O pré-ecrã de faturação mostra ligado vs consumido e o excedente a libertar. Se for tudo esgotado, deduz-se tudo — como pediste |

---

## v7.3 — Tecido a chegar: cor específica · faturação → stock em trânsito · packing = quantidade líquida

> Nova cadeia do tecido: **encomenda (com cor) → faturada pelo fornecedor (entra em stock na quantidade encomendada) → packing list (ajusta para a quantidade líquida entregue/faturada) → receção.**

| Pedido | Implementação |
|---|---|
| **Alocar cor específica ao tecido a chegar** | A cor passa a ser **obrigatória** no formulário de nova encomenda. A tabela de encomendas em aberto é agora uma **grelha editável** (cor + data de faturação) — as encomendas antigas sem cor completam-se diretamente na grelha |
| **Data de faturação da PO de tecido** | Nova coluna `date_invoiced` (migração idempotente), editável na grelha com validação AAAA-MM-DD, visível também na timeline |
| **Faturada → entra em stock a quantidade encomendada** | Ao gravar a data de faturação, a encomenda passa a **INVOICED** e é criado automaticamente um **rolo consolidado em stock** (ref + cor + metros encomendados, no destino) sinalizado **"Em trânsito"**. Conta como stock (posição, armazéns, planeamento) mas **não é consumível** — fica excluído do corte (token v7.2), do Movimentar (M1/M3) e da Regularização até chegar. **Limpar a data reverte** (rolo removido) enquanto estiver intacto; se já foi movido/consumido, avisa para regularizar |
| **Packing → quantidade líquida** | A importação de packing passa a aceitar POs **INVOICED** e, ao receber, **substitui o rolo em trânsito pela quantidade líquida** dos rolos do packing — o Δ (encomendado vs líquido) fica registado como movimento **PACK-ADJ** e no aviso de confirmação. Sem packing, **"Marcar chegada"** confirma o rolo em trânsito como stock físico (perde a sinalização e passa a consumível) |
| **Coerência do resto do sistema** | "A chegar" (posição/planeamento) deixa de contar POs faturadas (já estão em stock — sem duplicação); alertas de **tecido em atraso** passam a incluir faturadas em trânsito não recebidas |

---

## v7.2 — Cadeia de vida do rolo fechada: token sempre atribuído (corte → em processo → faturado)

> Regra de negócio (confirmada): **ao locar corte, os rolos passam de stock para em processo; ao faturar, saem de em processo; o token da PO tem de estar atribuído quer seja metragem agrupada, quer rolos individuais.** A auditoria v7.1 mostrou que a cadeia estava partida em dois pontos — esta versão fecha-a.

| Ponto da cadeia | Antes (partido) | Agora (v7.2) |
|---|---|---|
| **Locar corte** | Registava o consumo mas **não mexia nos rolos** — nada passava de stock para em processo, nada ficava com token | Ao confirmar o corte (modo live), os metros cortados passam **automaticamente** para em processo **com o token da PO**: 1º rolos já em processo no confeccionador sem token (ganham o token), 2º rolos AVAILABLE da ref+cor em **FIFO** — sempre com **divisão exata** do último rolo. Reconciliação **cumulativa**: cortes parciais da mesma PO acumulam sem duplicar nem saltar rolos. Se faltar stock, aviso com os metros em falta (e aparece nos 🚨 Alertas) |
| **M1 — rolos individuais** | Movia para Em Processo **sem token** | **Dropdown de POs ativas da ref, obrigatório** ao mover para Em Processo — cada rolo fica com o token (movimentos dentro de armazém como AVAILABLE não precisam) |
| **M2 — lote agregado** | Idem, nem na divisão parcial | Igual a M1 — token obrigatório, aplicado ao lote movido **e** ao novo lote da divisão |
| **M3 — metros consolidados** | PO em **texto livre** (podia ficar vazio ou errado) | **Dropdown validado** de POs ativas da ref; obrigatório quando o destino é confeccionador; o lote consolidado herda cor da PO como antes |
| **Faturar** | `IN_PROCESS → INVOICED` só dos rolos **com token** — como quase nenhum tinha, deduzia 0m (foi o caso da POAPS2000004348) | Regra mantida — e como a montante o token fica **sempre** atribuído, a baixa passa a acontecer sempre. O ⚖️ Regularizar (v7.1) continua disponível para POs antigas |

**Extra:** as confirmações (flash) passam a suportar **várias mensagens** — ex.: corte registado + aviso de stock em falta, tudo visível após o refresh.

---

## v7.1 — Cor editável em faturadas · ⚖️ Regularizar baixa de metros

| Pedido | Implementação |
|---|---|
| **PO faturada sem cor (POAPS2000004348)** | A vista **Produção » INVOICED** passa a permitir editar a **cor da PO** (dropdown com validação por ref — a mesma regra da tabela principal). Corrigir a cor atualiza logo o Andamento, a matriz cor × armazém e as roturas dinâmicas, que leem a cor da PO |
| **Baixa de metros em falta** | Causa: a faturação só deduz rolos **ligados à PO** (token); se a PO foi faturada sem rolos ligados, só mudou o estado — os metros ficaram em stock. Nova secção **⚖️ Regularizar baixa de metros** na vista INVOICED: por PO mostra consumido (cortes reais) vs já deduzido e o que falta; **⚡ FIFO automático** tira os metros dos rolos mais antigos da ref+cor com **divisão exata do último rolo** (o resto fica disponível), ou escolhes os rolos manualmente. Tudo registado como movimento INVOICE |

**Como resolver a POAPS2000004348:** Produção » INVOICED → na linha da PO escolhe a cor (TCB258/EC1 — para "Almond" será Beige 0862 ou equivalente) → 💾 Guardar → em ⚖️ Regularizar baixa seleciona a PO (aparece "em falta 765m" — o corte real) → ⚡ Baixa automática FIFO. Fica cor atribuída + 765m deduzidos do stock + rasto completo em Movimentos.

---

## v7.0 — Simplificação total: 6 menus · automações sem clique · receção num clique

> Critério: **nada se perde, tudo se funde**. Todas as funções continuam disponíveis — com menos navegação e menos confirmações manuais.

| Pedido | Implementação |
|---|---|
| **Menus simplificados (10 → 6)** | **⚡ Hoje** — Ultra + centro de alertas completo + posição por ref + breakdown por cor + pipeline (absorve o antigo 📊 Dashboard e a página 🚨 Alertas, agora eliminadas como menus); **📦 Stock** — com 🚢 A Chegar como separador interno; **👕 Produção**, **📊 Consumos**, **🗓 Planeamento** — como estavam; **⚙️ Sistema** — Movimentar · Rastreio · Exportar · Integrações num só menu. O ⚡ Hoje mostra **badge com o nº de alertas críticos** diretamente no menu |
| **Descartar redundâncias** | Dashboard removido (conteúdo absorvido no Hoje), página Alertas removida (idêntica, dentro do Hoje), A Chegar deixou de ser menu, Integrações entrou no Sistema. Nenhuma função foi apagada — só fundida |
| **Simplificar processos (automação)** | **Cor da PO automática**: no arranque da sessão, as POs sem cor cuja sugestão é inequívoca ficam logo com cor — sem abrir o painel 🎨. **Molde auto-associado**: POs sem molde cujo nome do modelo resolve para uma entrada do mapa da ref ficam associadas — só restam manuais os casos ambíguos. Um aviso único resume o que foi aplicado |
| **Receção num clique** | "Marcar chegada" em Stock » A Chegar passa a **criar também o rolo consolidado** no destino (ref + cor + metros da encomenda) quando não há packing list — chegada e stock num único gesto. Com packing list, a importação automática mantém-se como estava |

---

## v6.0 ULTRA (PROTÓTIPO) — Alertas automáticos · Master Planning · NetSuite · Stock ao vivo por armazém

> Versão experimental: tudo o que já existe mantém-se igual; as novidades são **4 páginas novas** (⚡ Ultra, 🚨 Alertas, 🗓 Planeamento, 🔌 Integrações) + 3 tabelas novas na BD (idempotentes). Objetivo: **mínima intervenção** — a app observa, alerta e planeja sozinha.

| Pedido | Implementação |
|---|---|
| **1) Alertas automáticos (aprovações · desvios · falta molde/consumo · tecido em atraso)** | Nova página **🚨 Alertas** gerada a cada abertura, zero intervenção: **✋ Aprovações pendentes** — desvios de corte >5% por autorizar, com botão **Aprovar** direto no alerta; **🧩 Molde/consumo em falta** — POs ativas sem entrada no mapa (com caminho para associar); **🚢 Tecido em atraso** — POs de tecido com data prevista passada e não recebidas |
| **1b) Tecidos a acabar — dinâmico, ligado às POs impactadas** | **📉 Rotura dinâmica por ref+cor**: (disponível + em processo + a chegar) vs necessidade das POs ativas (metros declarados ou qty × m/pc do mapa). Cada alerta mostra disponível/a chegar/necessidade, **quantos metros faltam** e **que POs são impactadas** |
| **2) Master Planning** | Nova página **🗓 Planeamento**: plano **retrógado** por PO — prazo final da peça → acabamento → confeção → corte — cruzado com o tecido (em stock ou ETA de chegada). **Lead times editáveis** (guardados na BD), mini-**gantt** por PO com marcador "hoje", e estado automático: 🟢 no prazo · 🔴 tecido chega tarde · 🔴 sem tecido · 🟠 corte em atraso · ⚫ prazo passado |
| **3) NetSuite + script de extração (alimentação automática)** | Nova página **🔌 Integrações**: configuração NetSuite (Account/Token, guardada na BD), **teste de ligação** e **sincronização simulados** com registo em log — pronto a ligar ao endpoint real. Inclui **`netsuite_extract_pos.py`** descarregável: extrai Purchase Orders via SuiteQL REST + TBA e grava CSV no formato já aceite em Produção » Carregar POs. Agendado (cron/Task Scheduler), **o carregamento manual deixa de ser preciso** — até lá, mantém-se tudo como está |
| **4) Salto visual + stock real a qualquer momento** | Nova página de entrada **⚡ Ultra**: KPIs vivos (stock real, em curso, a chegar, alertas críticos, POs em risco), **cartões por armazém** com metros em armazém / em curso / a chegar e barras proporcionais, alertas prioritários e próximas entregas — o estado real da fábrica num ecrã |

---

## v5.5 — Confirmações persistentes (pop-ups já não desaparecem)

| Pedido | Implementação |
|---|---|
| **Pop-ups de confirmação desapareciam demasiado rápido** | Causa: após cada gravação a app recarregava (`st.rerun()`) e a mensagem de sucesso era limpa no mesmo instante — mal se conseguia ler. Novo sistema de mensagens **flash**: a confirmação é guardada antes do recarregamento e aparece **no topo da página seguinte**, ficando visível até à próxima interação. Aplicado às 21 confirmações da app: tabela de produção, datas de faturação, registo de corte, movimentações (3 modos + divisão de lote), receções, faturação, associações de molde, cores da PO, mapa de consumos e uploads |

---

## v5.4 — Semana/data de faturação editável · Associação de molde só em Consumos · PO4445 (mapa por ref)

| Pedido | Implementação |
|---|---|
| **1) Edição da semana de faturação (controlo)** | Nova coluna **`date_invoiced`** na produção. Ao marcar uma PO como **INVOICED** na tabela principal, a data fica automaticamente como **hoje**; as POs já faturadas recebem a data do 1º movimento INVOICE (migração automática, idempotente). A vista **Produção » INVOICED** é agora editável: alteras a **Data de Faturação** (AAAA-MM-DD) e a coluna **Semana (CW)** calcula-se sozinha. A vista por período do Stock passa a usar esta data — editar a data muda a semana onde a faturação conta |
| **2) Associação de molde — sítio único** | Confirmado: era redundante. A associação PO → modelo base passa a existir **só em 📊 Consumos » 🔗 Modelo base das POs** (fonte única de verdade). No ⚡ Modo Live, se a PO não tem mapa, aparece um aviso com o caminho para associar. A ✏️ Tabela de Produção continua a editar tudo o resto (peças, metros, datas, estado, cor…) |
| **3) POAPS2000004445 sem m/pc** | Causa encontrada: tinhas associado a PO (tecido **TCD524/EC1**) à entrada "Essential Suit Pants · Regular" da ref **TCB258/EC1** — o sistema procura sempre dentro da **ref da própria PO**, por isso a associação cruzada nunca resolvia e o m/pc ficava em branco (no Live também). Agora o dropdown de associação **só mostra entradas da ref da PO**; se não houver nenhuma, a app diz para a criar. **O que fazer:** em ✏️ Editar Mapa cria a entrada `Essential Suit Pants · Regular · TCD524/EC1` (ou edita a existente para essa ref) — a associação manual que já tinhas feito passa a resolver de imediato, sem voltares a escolher nada |

---

## v5.3 — Contraste clean reforçado (Edge) · Exports Excel formatados · Mapa recalcula ao associar modelo

| Pedido | Implementação |
|---|---|
| **1) Contraste entre browsers (Edge/clean)** | No modo claro os campos de formulário estavam quase invisíveis (branco sobre branco). Novo `INPUT_BORDER` por tema: todos os inputs, selects, datas, uploaders e grelhas têm agora contorno visível (azul ao focar); bordas e texto secundário do clean mais fortes. Se no Edge ainda vires cores estranhas, verifica `edge://flags/#enable-force-dark` (o "modo escuro automático" inverte as cores por cima de qualquer CSS — deve estar desligado) |
| **2) Export da Vista por período igual à vista** | Todos os exports Excel passam a sair **formatados como a app**: cabeçalho azul corporativo, números com separador de milhares, linha **TOTAL** em destaque, larguras automáticas e primeira linha fixa. A Vista por período exporta agora com cabeçalhos no idioma (Ref, Stock Início, Entradas, Faturado, Stock Fim) + linha TOTAL; a matriz cor × armazém também ganha linha TOTAL |
| **3) Consumos — dúvidas** | **a)** Sim: o ⚡ Modo Live serve também para POs sem valor estimado — regista pcs + metros reais e o corte fica guardado (desvio fica "—" até haver valor esperado). **b)** Sim: lançamentos novos são SEMPRE no Modo Live; correções de valores já lançados fazem-se em Consumos » 🏃 Andamento & Registos » ✏️ Corrigir registos reais. Novo: ao associares a PO a um modelo base (🔗 Consumos ou inline no Live), o **real médio do mapa é recalculado na hora** — os cortes já lançados passam a contar imediatamente |

---

## v5.2 — Design corporativo SNT · Contraste garantido em Edge e Chrome · Responsivo PC/mobile

| Pedido | Implementação |
|---|---|
| **Layout e cores corporativas** | Paletas dark/clean reconstruídas na identidade do **SNT Label Tool**: azul SNT (#2E7CF6), superfícies planas (fim dos gradientes em camadas), header com overline de marca "SNT · CMT" + barra de acento, botões primários em azul corporativo sólido. Zero alterações a dados ou lógica — só apresentação |
| **Edge com mau contraste** | Causa: cinzas translúcidos (rgba) e cores semânticas claras que o Edge lavava (sobretudo com tema de SO/browser a interferir). Agora: **todas as cores de texto são sólidas** e cada tema tem as suas cores semânticas (ok/aviso/erro/info) — rácios medidos: texto principal 15,9:1 (dark) / 17,8:1 (clean), secundário ≥ 7,3:1, tudo ≥ WCAG AA nos dois browsers. `color-scheme` por tema mantido + antialiasing explícito + foco visível ao teclado |
| **Navegação PC / mobile** | Media queries novas: cartões de PO/armazém colapsam para 1 coluna, KPIs para 2, tabelas mantêm scroll horizontal, header e tabs compactos, botões e itens de menu com alvo de toque ≥ 44px |
| **Performance** | Fundos planos em vez de gradientes multi-camada, sombras mais leves, botões sem gradiente — menos repaints no scroll. (Os dados já vinham otimizados: tabelas HTML próprias sem PyArrow, LIMITs nas listagens) |

---

## v5.1 — Cores fixas por ref · Cor da PO em massa + auto-sugestão · Armazém Fabrijeans/Costa Correia consolidado

| Pedido | Implementação |
|---|---|
| **1) Que cor conta? + correção sem ir PO a PO** | A cor que conta para stock e consumos é **a cor da PO** (linha `ref · cor` do cartão/registo); a cor no nome do modelo é a cor da peça — apenas informativa (agora dito no próprio painel). No painel **🎨 Cor da PO** (Produção → Tabela) há agora duas vias rápidas: **✨ Sugestões automáticas** — a palavra-cor do nome do modelo (ex.: "Black") casada com as cores da ref em stock, só sem ambiguidade (44 POs resolvidas de uma vez nos dados atuais) — e **⚡ Atribuição em massa**: escolhes ref → cor → POs (pré-selecionadas as que estão sem cor ou com cor fora da ref) |
| **2) Cores fixas e únicas por ref** | A PO só aceita as **cores próprias da ref** — as que constam em stock (rolos/lotes) ou a chegar. O painel 🎨 lista apenas essas; a ✏️ Tabela de Produção **bloqueia a gravação** enquanto houver cor fora da ref e mostra as cores válidas (ex.: "Black 017" só existe na Riopele TCB258/EC1 — não entra num Carreman). O upload CSV de POs já avisava (⚠️) nestes casos. No 🏃 Andamento, PO sem cor mostra **"⚠️ sem cor na PO"** em vez de adivinhar a cor mais comum da ref (era a fonte das cores trocadas nos cartões) |
| **3) Armazém Costa Correia → "Fabrijeans / Costa Correia"** | São empresas distintas mas partilham o armazém físico. Nas **vistas de armazém** (📦 Stock por Armazém, 🎨 Matriz cor × armazém, filtro de armazém do detalhe de rolos) passam a aparecer consolidadas como **"Fabrijeans / Costa Correia"** (inclui os lotes antigos "Fabrijeans / Costa C"). A produção continua atribuída a cada empresa — pipeline, POs, consumos e movimentos mantêm Fabrijeans e Costa Correia separados |

---

## v5.0 — Cor da PO ligada ao stock · Registos corrigíveis · Histórico completo · Stock por período · Matriz cor×armazém

| Pedido | Implementação |
|---|---|
| **1a) Associar cor existente da ref à PO** | A coluna Cor da ✏️ Tabela de Produção passou de texto livre para **dropdown com todas as cores existentes no sistema**. Novo painel **🎨 Cor da PO**: escolhes a PO e vês **só as cores dessa ref** (stock + encomendas + outras POs). Aviso ⚠️ automático quando uma cor não pertence à ref da PO |
| **1b) Relação com stock** | No ⚡ Modo Live, por baixo dos cartões: metros disponíveis da **ref** e da **cor da PO** |
| **2a) Cor no Andamento** | A cor mostrada vinha de um fallback "indicativo" (cor mais comum da ref) ou de texto livre — por isso apareciam cores de outra ref. Agora: prioridade à cor gravada na PO, e ⚠️ quando a cor não pertence à ref |
| **2b) Cor nos registos/desvios** | A tabela de registos tem coluna **Cor** sempre ligada à PO em produção (com ⚠️ se incoerente) |
| **2c) Onde lançar + m/pc** | **Lança SEMPRE em 👕 Produção → ⚡ Modo Live.** "Live" e "real" são o mesmo dado: cada corte lançado vira um registo real; o mapa mostra a média. Para corrigir valores reais: Consumos → 🏃 Andamento & Registos → **✏️ Corrigir registos reais** (o mapa recalcula só). A coluna **m/pc** (metros por peça, 2 casas) tem agora a coluna **Fonte**: 📈 média real → 📐 standard → 📋 declarado na PO |
| **3) Histórico completo** | Seleção de âmbito: últimas 20/100/500, **todas** ou **por período** + filtro por tipo + exportação Excel/CSV |
| **4a) Stock por período** | 📦 Stock → 🗓️ Vista por período: atalhos **mês corrente**, **mês anterior**, **qualquer mês completo** (ex.: janeiro) ou período à medida. Por ref: stock início, entradas, faturado, stock fim (reconstruído: fim = atual + faturado posterior − entradas posteriores). Exportável |
| **4b) Matriz cor × armazém** | 📦 Stock → 🎨 Matriz cor × armazém: linhas ref+cor, colunas por entidade com **D**isponível e em **P**rocesso, subtotais por linha e por coluna — como o teu Fabric audit. Exportável |
| **5) Alertas sem ruído** | Alertas do dashboard só sobre refs com atividade (stock/encomenda/necessidade) — "stock baixo" caiu de 17 para 4. "Sem cor" no Stock só conta stock real (metres > 0) — os lotes zerados por consolidação deixaram de poluir |

---

## v4.2 — Contraste de tema à prova de SO · A Chegar com cor + local de entrega · Receção num só passo

| Pedido | Implementação |
|---|---|
| **2) Tema vs cor do SO** | Causa: tabs, expanders, file uploader, calendário e toasts seguiam o tema do SO (não estavam cobertos pelo CSS da app). Agora: `color-scheme` por tema + CSS explícito para todos esses elementos — o tema da app (dark ou clean) ganha sempre, com qualquer cor de SO. Nota: a grelha interna do data_editor usa o tema do viewer do Streamlit (definição do browser), mas é sempre legível |
| **1a) Tracking → Local Entrega** | O campo tracking foi substituído por **Local Entrega** na tabela, na timeline e no formulário |
| **1b) Coluna Cor** | Nova coluna `color` nas encomendas de tecido — no formulário (cores conhecidas da ref + nova cor), no upload CSV e na tabela (com ponto de cor) |
| **1c) Dupla marcação eliminada** | A packing list tem agora um campo opcional **"Ligar a encomenda de tecido em aberto"** — no fim da importação a encomenda fica RECEIVED automaticamente (com reconciliação de metros). "Marcar Chegada" no menu A Chegar fica só para o caso de não haver packing |
| **1d) Destino em todas as entidades** | O dropdown de destino do packing e o Local Entrega das encomendas aceitam **armazéns + confeccionadores** (o formato Riopele continua a rotear pelo recebedor) |

---

## v4.1 — Cor na PO garment · Metragem por cor · Packing Riopele

| Pedido | Implementação |
|---|---|
| **Cor na PO garment** | Nova coluna `production.color` (migração automática). O upload CSV de POs garment passa a **gravar** a cor (antes era só validada e descartada). Editável na ✏️ Tabela de Produção, visível no ⚡ Modo Live, e os lotes consolidados (Movimentar → 📦 Consolidar) com PO ligada **herdam a cor da PO** |
| **Dashboard: cada cor com a sua metragem** | Nova vista expansível **🔎 Metragem por cor** por baixo da posição de stock: ref + cor com disponível, em processo e total exatos |
| **4 packings Riopele "Report 1"** | O upload de packing list deteta automaticamente o formato Riopele (Lote/Material/Acabamento/Cor/Remessa/Líquido/Recebedor): ref = Material/Acabamento (TCB25800051 + EC1 → `TCB258/EC1`), códigos de cor resolvidos para o nome oficial (1049 → Medium Beige Melange 1049; 0318 → Dark Grey 0318 ⚠️ ambíguo com "Dark Grey Melange 0318" — verifica após importar), destino pelo recebedor (Samidel ✓, Costa Correia ✓; "Costa e Silva e Nascimento" ⚠️ desconhecido → armazém selecionado). Os 4 ficheiros testados: **82 rolos · 3.470,7m** |

### Como corrigir a PO Carreman-Azic (126m sem cor)
A PO `POAPS2000004232` (Women Ashryn Blazer, 126m) aponta para a ref `Carreman-Azic`, mas o stock desse artigo está nas refs **GZIC GR4 / GZIC GR5 / GZIC 002** (Samidel + XBS — ver o teu Fabric audit). Com a v4.1: **Produção → ✏️ Tabela de Produção** → nessa PO muda **Ref Tecido** para a ref GZIC correta e escreve a **Cor** → 💾 Guardar. A necessidade de 126m passa a contar contra a ref certa e o dashboard deixa de mostrar a linha sem cor.

---

# SNT CMT — Sistema de Stock & Produção v4.0

Sistema de gestão de stock de tecidos, encomendas garment e consumos para a SNT.
Dados reais carregados: CW29 2026.

## v4.0 — Consumos por modelo base + fit · Produção unificada · Dashboard limpo

| Pedido | Implementação |
|---|---|
| **1) Rolos/packings intocados** | Seeds de rolos, lotes de confeccionadores e consumos reais **byte-a-byte iguais** à v3.10. Mesma BD `snt_cmt_v37.db` — as migrações v4 correm no arranque e não perdem nada (total validado: 103.058,79m / 397 rolos) |
| **2) Consumos reformulados** | O consumo deixou de estar preso à **cor** do modelo: novo mapa por **modelo base + fit** (`consumption_map_v4`). "Ease Pants Black Slim", "Ease Pants Blue Nights Slim"… → uma entrada **Ease Pants · Slim** (std 1,30 · real 1,346). O menu Consumos passa de 4 submenus repetitivos para **2 ecrãs**: 📊 **Mapa por Modelo** (visual agrupado por modelo base, edição da grelha e associações PO↔modelo) e 🏃 **Andamento & Registos** (guia só-leitura das produções em corte com nota de desvios + registos reais + autorizações — tudo num só sítio) |
| **2b) Modelo base por PO** | Deteção **automática** a partir do nome da PO (remove cor, "(Use all fabric)", "Men/Women"); quando não encontra, podes **alocar manualmente** — em Consumos → 🔗 Modelo base das POs, ou inline no Modo Live. A associação fica guardada na PO (`base_model`) e tem prioridade sobre a deteção |
| **3a) Consumo esperado corrigido** | O bug: o match antigo comparava o nome completo (com cor) e caía num fallback errado. Agora resolve por base+fit com hierarquia (manual → base+fit → base → variante Plain) e, sem mapa, usa o **standard declarado na própria PO** (metros ÷ qty, badge 📋). Resultado: **60/60 POs com consumo esperado** |
| **3b) Produção sem menus repetidos** | A ✏️ **Tabela de Produção** passa a ter a coluna **Estado** (PENDING/CUTTING/INVOICED) — mudar para INVOICED faz a baixa automática dos metros em processo (com movimento INVOICE). O separador "🔄 Mudar Estado PO" foi **removido**. Novas colunas só-leitura: **Modelo Base** e **m/pc** resolvido; metros em falta são auto-calculados (qty × standard) ao gravar |
| **4) Dashboard limpo** | Refs sem stock, sem encomendas e sem necessidade (Carreman-Garco, Delegant, TC6677…) deixam de poluir a posição de stock — ficam escondidas por omissão, com checkbox "Mostrar refs sem stock nem movimento" para as ver. Tabela ordenada por planeamento (críticos primeiro) |

### Notas técnicas v4
- Nova tabela `consumption_map_v4 (base_model, fit, fabric_ref, m_per_pc_expected, m_per_pc_actual)` construída uma vez a partir do mapa antigo + consumos reais + standards declarados nas POs.
- Nova coluna `production.base_model` ('Base|Fit'; NULL = deteção automática).
- Função-chave nova: `derive_model_fit()` — reduz qualquer nome comercial a (modelo base, fit).
- O mapa antigo `consumption_map` fica intacto na BD (não é usado pela v4).

---

## v3.10 — Packing lists: rolos individuais em lote para o armazém

| O que mudou | Detalhe |
|---|---|
| **📤 Carregar packing list** | Em Ferramentas → Movimentar → 📥 Receção (junto ao registo manual): upload Excel/CSV, uma linha por rolo. Colunas flexíveis: ref_code, metres · opcionais roll, color, lot, po_number + template CSV |
| **Armazém de destino** | Seletor XBS/Riopele por carregamento — todos os rolos do ficheiro entram AVAILABLE nesse armazém |
| **Tokens automáticos** | R-{REF}-{NNN} gerados em lote, continuando a numeração existente por ref (sem colisões); nº do rolo do fornecedor e PO ficam nas notas para rastreio |
| **Validação com reconciliação** | ❌ ref/metros em falta · ⚠️ ref nova (regista no catálogo), cor em falta/desconhecida, rolo repetido no ficheiro, sem lote, PO inexistente/já recebida, e **packing vs encomenda**: "PO POTEC001: packing 131,7m vs encomenda 200,0m (Δ -68,3m)" |
| **PO ligada → receção automática** | Se a packing traz po_number de uma encomenda EXPECTED/IN_TRANSIT, ao importar fica RECEIVED (com movimento ARRIVAL) |
| **Sumário ref+cor** | Antes de importar: rolos e metros por ref+color com linha TOTAL, além da pré-visualização linha a linha |

Sem re-seed: base mantém-se `snt_cmt_v37.db`.

## v3.9 — Carga em massa via Excel/CSV com validação

| O que mudou | Detalhe |
|---|---|
| **📤 Carregar POs** (Produção) | Novo separador: upload Excel/CSV de encomendas garment. Colunas flexíveis (aceita sinónimos PT/EN: PO/po_number, Modelo/model_name, Conf, Qty, Ref, Cor, Metros, Data, Status) + template CSV para download |
| **📤 Carregar encomendas** (A Chegar) | Expander: upload Excel/CSV de encomendas de tecido (po_number, supplier, ref_code, total_metres + opcionais) |
| **Relatório de validação** | Antes de importar: chips com X válidas / Y avisos / Z erros e tabela linha a linha (❌ erro exclui a linha · ⚠️ aviso com auto-correção). Nada entra sem clicar "✅ Importar N linhas" |
| **Auto-correções** | Ref nova → regista no catálogo ao importar ⚠️ · metros em falta → qty × m/pc standard ⚠️ · datas dd/mm/aaaa → ISO ⚠️ · números PT (1.234,56) e EN · cor desconhecida para a ref → aviso |
| **Erros detetados** | PO em falta/duplicada (no ficheiro ou na BD), qty/metros inválidos, modelo/confeccionador/fornecedor/ref em falta |
| **Idempotente** | Re-carregar o mesmo ficheiro mostra as linhas já importadas como duplicadas — sem risco de duplicar |

Sem re-seed: base mantém-se `snt_cmt_v37.db`.

## v3.8.1 — Registar novas encomendas de tecido

| O que mudou | Detalhe |
|---|---|
| **Formulário "➕ Nova encomenda de tecido"** | No menu 🚢 A Chegar: PO, fornecedor (com opção "➕ Novo…"), ref (com "➕ Novo…" que regista a ref no catálogo), metros, data prevista, estado (EXPECTED/IN_TRANSIT) e tracking. Valida duplicados e campos obrigatórios |
| **Fluxo completo** | Registar encomenda (A Chegar) → marcar chegada → registar rolos na Receção (Ferramentas → Movimentar) → stock AVAILABLE. A encomenda entra logo no KPI "a chegar" e fica registada nos movimentos (ORDER) |

Nota: encomendas garment (POs) lançam-se na Produção → ✏️ Tabela Editável (linha nova no fim da grelha → Guardar).

Sem re-seed: base mantém-se `snt_cmt_v37.db`.

## v3.8 — Quadro "Em Curso" + autorização de cortes extra

| O que mudou | Detalhe |
|---|---|
| **Novo separador 🏃 Em Curso** (Consumos) | Cartão visual por PO em corte: progresso de pcs (barra), metros usados, **m/pc atual vs standard**, chip de desvio 🟢/🟠/🔴 e **projeção de metros extra no fim da PO**. Ordenado do pior desvio para o melhor — vê-se logo qual a PO afetada |
| **Autorização de corte extra** | Novo expander "✅ Autorizar desvios" nos Registos: marque o corte extra aprovado (checkbox + nota) e grave. O desvio autorizado **deixa de contar** no quadro (fica 🔵) e a projeção passa a ser líquida de extras autorizados |
| **Registos com sinal claro** | Coluna **Sinal** (🟢/🟠/🔴/🔵 + %), fila de chips-resumo (dentro / atenção / desvio / autorizados) e filtro Todos / Só desvios / Só autorizados |
| **Dashboard diz qual a PO** | Novo chip crítico nos alertas: "desvio consumo: …4380 +10.4% · …4383 +9.8% · …4377 (+15 mais)" — nomes as POs com desvio > 5% não autorizado |
| **Consistência de estados** | PO com cortes registados fica automaticamente CUTTING (migração em cada arranque — as 38 POs com atividade aparecem no quadro) |

**Sem re-seed**: base mantém-se `snt_cmt_v37.db` — as migrações correm no arranque e preservam tudo.

## v3.7.2 — Clean Mode redesenhado a sério

| O que mudou | Detalhe |
|---|---|
| **Sidebar temática** | O seletor CSS da sidebar estava obsoleto (classes antigas do Streamlit) — a sidebar ficava escura no modo clean. Agora usa `[data-testid="stSidebar"]`: clara no clean, escura no dark |
| **Tabelas 100% tematizadas** | As 13 listagens deixaram `st.dataframe` (canvas, cores fixas do SO) e passaram a tabelas HTML próprias (`render_table`): header fixo, hover, números alinhados à direita com separador de milhares, linha TOTAL realçada, coluna Token discreta em monospace — sempre a condizer com o tema |
| **Texto e labels invisíveis corrigidos** | Markdown, títulos e labels dos widgets herdavam a cor do SO (branco no fundo branco). Agora seguem sempre o tema |
| **Inputs completos** | Selectbox, multiselect (tags incl.), número, texto, data e as listas popup tematizados; placeholders discretos |
| **Radios em "pills"** | Círculo escondido; navegação da sidebar com pill ativa + barra lateral accent; seletor das Ferramentas com aspeto segmented control |
| **Alertas nativos** | st.success/info/warning/error passam a cartão neutro legível nos dois temas |
| **Limitação conhecida** | As 2 grelhas editáveis (Produção, Mapa de Consumos — `st.data_editor`) seguem o tema do sistema operativo; é uma restrição do componente |

Sem re-seed: base mantém-se `snt_cmt_v37.db`.

## v3.7.1 — Correção do Movimentar + Movimentar englobado nas Ferramentas

| O que mudou | Detalhe |
|---|---|
| **Erro no Movimentar corrigido** | `UnboundLocalError: t` — uma variável de ciclo `for t in ...` escondia a função de tradução `t()` dentro do menu Movimentar; renomeada (e prevenção do mesmo padrão no Stock) |
| **"Movimentar" dentro das Ferramentas** | Menu lateral com 6 entradas; dentro de Ferramentas: seletor horizontal 🚚 Movimentar / 🔍 Rastreio / 📤 Exportar |
| **Sem re-seed** | Base mantém-se `snt_cmt_v37.db` — atualizar não perde dados |

Nota técnica: usa-se um seletor horizontal porque o Streamlit não suporta separadores (tabs) dentro de separadores — e o Movimentar já tem os seus 5 separadores internos.

## v3.7 — 7 melhorias pedidas

| O que mudou | Detalhe |
|---|---|
| **Consumo com média real** | `get_mpc()` usa sempre a média produtiva real quando existe; senão o standard. Badge ⚡ real / 📐 standard no cálculo. O mapa deriva entradas das produções reais |
| **Menu Ferramentas** | Rastreio e Exportar unificados |
| **PT / EN** | Seletor de idioma na barra lateral; toda a interface traduzida |
| **Dark / Clean mode** | Seletor de tema na barra lateral (escuro por omissão) |
| **Movimentar por remessa** | Seleção rápida de todos os rolos da mesma remessa+cor de uma vez |
| **Stock: cabeçalho compacto** | Tabela-resumo por local (Available / In Process / Total + rolos) com linha TOTAL, em vez dos cartões grandes |
| **AVAILABLE vs IN_PROCESS (audit CW29)** | Colunas "(stock)" passam a AVAILABLE: Tyrrell 3.002,01m disponível; Fabrijeans/Costa 34.943,42m disponível + 14.988,49m em processo |

⚠️ A v3.7 usava base nova (`snt_cmt_v37.db`).

## v3.6 — Stock = Fabric Audit CW29 (ao cêntimo) + Totais em todas as tabelas

| O que mudou | Detalhe |
|---|---|
| **Stock sincronizado com o Fabric Audit CW29** | Total geral **103.058,79m** — bate certo ao cêntimo com o audit |
| **Confeccionadores corrigidos** | Fabrijeans/Costa C 49.931,91m · Samidel 28.518,55m · Acorfato 3.503,74m · Tyrrell 3.002,01m · António & Carla 47,00m — cada lote com **ref + cor** (88 lotes) |
| **Distinção stock vs em processo** | Nos confeccionadores, os lotes trazem nota "Stock conf." (ainda não cortado) vs "Em processo" — como no audit |
| **GB14W cores completas** | código + nome: "UNI 1 Black", "MH W9U1 Sahara", "UNI 93 Mocha Melange"… |
| **Refs novas** | ACASH KD, TCC482/F1, TCD488/EC1, TCD741/F1, TCE081/EC1, TCE604/F1, 4600 48389 (ligada à PO Timeless Wool Blazer), coleção UNI-MH FW 25.26 |
| **XBS reconciliado com o audit** | 18.055,58m: complemento TCD648 Black 001 (+2.846,26m sem packing), GZIC com as cores reais do audit (Dark Navy/Dark Brown/Dark Beige), ajustes −32,01m e −4,53m |
| **Linha TOTAL em todas as tabelas** | Somatório de metros (e qty) no fim de todas as listagens — Dashboard, Stock (respeita os filtros ativos), A Chegar, Produção, Consumos, Movimentações, Rastreio — e também nos **extratos Excel/CSV** |

⚠️ Base nova (`snt_cmt_v36.db`) — ponto de partida certo e definitivo a partir do audit CW29.

## v3.5 — Stock XBS completo com cores

| O que mudou | Detalhe |
|---|---|
| **Stock XBS completo** | 319 rolos importados do STOCK XBS (antes: 92 e incompleto) — **15.245,86m** |
| **Cor em todos os rolos** | Cada rolo tem ref + cor oficial: TCB258/EC1 (Black 017, Midnight Blue 0917, Dark Grey 0318, Beige 0862), TCD648/F1 (Navy 004, Dark Grey 018, Black 001, Sand 002, Green 003), 43793 (Sand 2952, Black 344), GZIC GR4 (Dark Navy B5T01) |
| **Totais validados** | Metros por ref+cor batem certo ao cêntimo com o Excel |
| **Devoluções identificadas** | 144 rolos marcados com nota "Devolvido pela Samidel" (os RETIRADO DA SAMIDEL do ficheiro) |
| **Refs novas com stock real** | TCD648/F1 passa de 0m → 7.732m disponíveis; 43793 de 0m → 981m; GZIC GR4 de 203m → 1.515m |

⚠️ **Ponto de partida novo**: a v3.5 usa uma base nova (`snt_cmt_v35.db`). O que foi lançado manualmente nas versões anteriores fica guardado no ficheiro antigo (backup no volume), mas não é migrado — é o reset combinado para começar com dados certos.

| Ref | Cor | Rolos | Metros |
|---|---|---|---|
| TCB258/EC1 | Black 017 | 33 | 1.614,99 |
| TCB258/EC1 | Midnight Blue 0917 | 57 | 2.612,06 |
| TCB258/EC1 | Dark Grey 0318 | 11 | 555,35 |
| TCB258/EC1 | Beige 0862 | 4 | 234,80 |
| TCD648/F1 | Navy 004 | 56 | 2.317,72 |
| TCD648/F1 | Dark Grey 018 | 57 | 2.481,24 |
| TCD648/F1 | Black 001 | 58 | 2.362,44 |
| TCD648/F1 | Green 003 | 7 | 338,64 |
| TCD648/F1 | Sand 002 | 7 | 232,02 |
| 43793 | Sand 2952 | 5 | 318,40 |
| 43793 | Black 344 | 10 | 662,90 |
| GZIC GR4 | Dark Navy B5T01 | 14 | 1.515,30 |

## v3.4.1 — Atribuir Cor em Massa

| Novidade | Detalhe |
|---|---|
| **🎨 Atribuir / corrigir cor** (menu 📦 Stock) | Ferramenta para atribuir cor em massa aos rolos da XBS (que vieram do stock sem cor): filtra por ref/armazém, vê só os rolos sem cor, seleciona ou aplica a TODOS os listados, escolhe cor existente ou nova |
| **Alerta de rolos sem cor** | Chip amarelo no Stock mostra quantos rolos faltam colorir até a estrutura ref + cor estar completa |

Os lotes de confeccionadores (Samidel, Costa Correia…) já têm cor — esta ferramenta serve para os rolos físicos da XBS e qualquer rolo futuro.

## Novidades v3.4

| Pedido | Implementação |
|---|---|
| **Cor sempre ligada à referência** | Ponto de cor visual (🔵🟢⚫🟤🔘🟡🟣🔴🟠) consistente em todo o site: tabelas (coluna Cor), seleções de lotes/rolos, rastreio e dashboard (coluna **Cores** por referência). Cores com nome são mapeadas (navy→🔵, black→⚫, grey→🔘, brown→🟤, green→🟢, sand/beige→🟡...); códigos sem nome recebem cor estável automática |
| **Token discreto** | Nas seleções vês `🔵 GB14W · UNI 10 · 673m @ Fabrijeans — P-…-001` (token sempre no fim); nas tabelas continua na última coluna |
| **Receção com picker de cor** | Ao receber tecido, escolhes uma cor já existente para a ref ou "➕ Nova cor…" |
| **Produção editável** | Tab "✏️ Tabela Editável": edita células, adiciona/remove linhas, grava com um clique. Faturação continua na tab ao lado (faz baixa de stock) |
| **Estado SEWING removido** | Fluxo simplificado: PENDING → CUTTING → INVOICED |

**Migração automática**: a v3.4 adiciona a coluna `color` aos movimentos sem perder dados existentes.

## Correções v3.3.1 (IMPORTANTE — deploy obrigatório)

| Problema | Causa | Correção |
|---|---|---|
| App crashava e voltava sempre à Dashboard ao usar campos selecionáveis | Segmentation fault do PyArrow (Python 3.13 + PyArrow recente incompatível com Streamlit 1.40) | Versões fixadas no `requirements.txt`: `numpy==2.1.3` + `pyarrow==18.1.0` — **tens de fazer push do requirements.txt também** |
| Token ocupava demasiado destaque | Estrutura das tabelas | Token passa a ser a **última coluna** de todas as tabelas; **Fornecedor Tecido + Ref Tecido + Cor Tecido** sempre nas primeiras colunas |

## Novidades v3.3

| Funcionalidade | Onde | Como funciona |
|---|---|---|
| **Modo Live — Registar Corte** | 👕 Produção | Escolhe a PO → escreve peças + metros reais → desvio calculado e validado em tempo real (verde ≤2%, amarelo 2–5%, vermelho >5%) |
| **Mudar Estado PO** | 👕 Produção | Dropdown PENDING → CUTTING → SEWING → INVOICED; INVOICED faz baixa automática dos metros em processo |
| **Movimentação 3 modos** | 🚚 Movimentar | 🎫 Rolos conhecidos (multiseleção por token) · 📦 Lote agregado (mover total ou **dividir** parcial) · 🔢 Metros consolidados (sistema retira FIFO dos rolos e cria lote no destino) |
| **Editar Mapa de Consumos** | 📊 Consumos | Grelha editável: altera m/pc standard, adiciona modelos, guarda com um clique |
| **Exportação Excel + CSV** | 📤 Exportar | Resumido, detalhado, consumos e **movimentos do mês** (para bater com faturação) |
| **Marcar chegada de PO tecido** | 🚢 A Chegar | Um clique marca a PO como recebida; depois registas os rolos na Receção |

## Correções de dados v3.3

- **Linhas TOTAL/TOTAL GERAL removidas** dos rolos XBS — eram subtotais do Excel que duplicavam o stock (ex: TCB258/EC1 aparecia com ~4.900m a mais).
- **Stock em processo normalizado**: referência base + campo cor separado (ex: `GB14W` + cor `UNI 1`), para o stock agregar corretamente por referência.
- Referências em falta adicionadas: `TCD340/RY1`, `TCD342/RY1`.

## Deploy (Railway)

O volume `qc_snt-volume` já está ligado com mount path `/app/data` — nada a alterar.

```bash
# 1. Substituir os ficheiros na pasta local do projeto
# 2. Commit + push
git add .
git commit -m "v3.6 - Stock sincronizado com Fabric Audit CW29 + totais nas tabelas"
git push origin main
# 3. Railway faz deploy automático (1-2 min)
```

**URL**: https://qcsnt-production.up.railway.app/

⚠️ **Nota**: a v3.3.1 cria automaticamente uma base de dados nova (`snt_cmt_v33.db`) com os dados corrigidos — **não precisas de apagar nada** no Railway. Se já tinhas feito deploy da v3.3, a base mantém-se e os dados são os mesmos.

## Cálculo de Stock

| Conceito | Fórmula |
|----------|---------|
| **Stock Líquido** | Disponível (R-) + Em Processo (P-) |
| **Posição Planeamento** | Líquido + A Chegar − Necessidade |
| **Sai de Em Processo** | Quando PO garment é faturada (→ INVOICED) |

## Tokens

- **R-{REF}-{NNN}**: rolos individuais (receções, armazém central)
- **P-{CONF}-{REF}-{NNN}**: lotes agregados em confeccionadores (metros totais, **divisíveis**)

## Estrutura

```
snt_cmt_system/
├── app.py              # Aplicação Streamlit completa
├── requirements.txt    # Dependências
├── railway.toml        # Start command Railway
└── README.md           # Este ficheiro
```
