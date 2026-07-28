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
