# SNT CMT — Sistema de Stock & Produção

Sistema de gestão de stock de tecidos, encomendas garment e consumos para a SNT.

## Deploy em 5 Passos (Railway)

| Passo | Ação | Tempo |
|-------|------|-------|
| 1 | Criar conta em [railway.app](https://railway.app) (login com GitHub) | 1 min |
| 2 | Criar repo privado em [github.com/new](https://github.com/new) | 1 min |
| 3 | Enviar código: `git init && git add . && git commit -m "v1" && git push` | 1 min |
| 4 | No Railway: New Project → Deploy from GitHub → selecionar repo | 2 min |
| 5 | **CRÍTICO**: Settings → Volumes → New Volume → `/app/data` | 1 min |

**URL final**: `https://snt-cmt-system.up.railway.app`

## Estrutura do Projeto

```
snt_cmt_system/
├── app.py              # Aplicação Streamlit completa
├── requirements.txt    # Dependências Python
├── railway.toml        # Configuração Railway
├── README.md           # Este ficheiro
├── .gitignore
└── templates/          # Templates Excel para upload
    ├── template_encomendas_tecido.xlsx
    ├── template_encomendas_garment.xlsx
    └── template_consumos.xlsx
```

## Cálculo de Stock

| Conceito | Fórmula | Onde vês |
|----------|---------|----------|
| **Stock Líquido** | Disponível + Em Processo | Tab 📦 Stock |
| **Posição Planeamento** | Disponível + Em Processo + A Chegar − Necessidade | Tab 📊 Dashboard |
| **Sai de Em Processo** | Quando PO garment é faturada (status → INVOICED) | Automático |
| **Incoming** | Só para planeamento, não entra no stock líquido | Tab 🚢 A Chegar |

## Upload Excel Inteligente

Não precisas de layout próprio! O sistema deteta colunas automaticamente pelo nome.

### Encomendas de Tecido
- `po_number` / `po` / `n_po` / `numero_po`
- `supplier` / `fornecedor`
- `metros` / `qty` / `total_metres` / `total`
- `expected_date` / `data_prevista` / `previsao` / `delivery_date`
- `status` / `estado` / `situacao`

### Encomendas Garment
- `po` / `numero_po` / `po_number` / `n_po` / `order_no`
- `modelo` / `model_name` / `style` / `style_name` / `descricao`
- `confeccionador` / `factory` / `fornecedor_garment` / `supplier`
- `pcs` / `qty` / `po_qty` / `quantidade` / `units`
- `tecido` / `fabric_ref` / `ref_tecido` / `material`
- `entrega` / `expected_date` / `data_prevista` / `delivery_date` / `previsao`
- `status` / `estado` / `situacao`

### Consumos
- `po` / `po_number` / `numero_po`
- `consumo_real` / `metres_actual` / `m_real` / `metros_real`
- `pcs_real` / `qty_produced` / `pcs_produzidas`
- `data_corte` / `date_cut` / `corte`
- `notas` / `notes` / `observacoes`

**Prompt de substituição**: Ao carregar, o sistema pergunta se queres adicionar, substituir ou cancelar.

## Tokens e Rastreabilidade

- **Novos rolos**: Token automático `R-{REF}-{NNN}` (ex: `R-EP001-015`)
- **Confeccionadores**: Metros totais sem token individual
- **Histórico completo**: Desde entrada até faturação

## Exportar Relatórios

- Stock resumido (por referência)
- Stock detalhado (por rolo/token)
- Movimentações
- Consumos por modelo

## Backup da Base de Dados

No Railway, vai a "Deployments" → clica no deploy ativo → "Shell" → executa:
```bash
cp data/snt_cmt.db /tmp/backup.db
```
Download via "Files" → `/tmp/backup.db`.

## Suporte

Para questões: abre um issue no GitHub ou contacta o administrador do sistema.
