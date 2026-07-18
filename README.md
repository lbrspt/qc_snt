# SNT CMT — Sistema de Stock & Produção v3.3.1

Sistema de gestão de stock de tecidos, encomendas garment e consumos para a SNT.
Dados reais carregados: CW29 2026.

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
git commit -m "v3.3.1 - Fix segfault PyArrow (requirements) + token na ultima coluna"
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
