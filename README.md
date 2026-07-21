# SNT CMT — Sistema de Stock & Produção v3.5

Sistema de gestão de stock de tecidos, encomendas garment e consumos para a SNT.
Dados reais carregados: CW29 2026.

## v3.5 — Stock XBS completo com cores (novo ponto de partida)

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
git commit -m "v3.5 - Stock XBS completo com cores (319 rolos)"
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
