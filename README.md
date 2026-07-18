# SNT CMT — Sistema de Stock & Produção v3.1

Sistema de gestão de stock de tecidos, encomendas garment e consumos para a SNT.
Dados reais carregados: CW29 2026.

## Deploy em 5 Passos (Railway)

| Passo | Ação | Tempo |
|-------|------|-------|
| 1 | Criar conta em [railway.app](https://railway.app) (login com GitHub) | 1 min |
| 2 | Criar repo privado em [github.com/new](https://github.com/new) | 1 min |
| 3 | Enviar código: `git init && git add . && git commit -m "v3.1" && git push` | 1 min |
| 4 | No Railway: New Project → Deploy from GitHub → selecionar repo | 2 min |
| 5 | **CRÍTICO**: Adicionar Volume → ligar ao serviço → mount path `/app/data` | 1 min |

**URL**: `https://<nome>.up.railway.app`

## Estrutura do Projeto

```
snt_cmt_system/
├── app.py              # Aplicação Streamlit
├── init_data.sql       # Dados iniciais (189 refs, 448 rolls, 103 incoming, 107 production, 82 consumos)
├── requirements.txt    # Dependências
├── railway.toml        # Configuração Railway
├── README.md           # Este ficheiro
└── templates/          # Templates Excel
```

## Dados Carregados (CW29 2026)

| Dado | Quantidade | Origem |
|------|-----------|--------|
| Referências tecido | 189 | stock_CW28 + Consumption.xlsx |
| Rolos XBS (individual) | 360 | STOCK XBS.xlsx |
| Stock confeccionadores (total) | 88 | stock_CW28 |
| POs tecido a chegar | 103 | Fabric audit incoming + SQL |
| POs garment | 107 | INSERT_DADOS_CORRECTO.sql |
| Consumos standard | 82 | Consumption.xlsx |

## Tokens

- **R-** prefix: Rolos individuais (XBS, receções)
- **T-** prefix: Metros totais em confeccionadores (agregados, divisíveis)

## Cálculo de Stock

| Conceito | Fórmula |
|----------|---------|
| **Stock Líquido** | Disponível (R-) + Em Processo (T-) |
| **Posição Planeamento** | Líquido + A Chegar − Necessidade |
| **Sai de Em Processo** | Quando PO garment é faturada (→ INVOICED) |

## Upload Excel Inteligente

O sistema deteta colunas automaticamente. Não precisas de layout próprio.

## Suporte

Para questões: abre um issue no GitHub.
