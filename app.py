"""
SNT CMT - Sistema de Stock & Produção v3.7
Dados reais CW29 2026
v3.4:
- Sistema de cor: cor sempre ligada à referência com ponto de cor visual em todo o site
- Token sempre na última posição (tabelas, seleções de lotes e rolos)
- Produção: tabela dinâmica editável; estado SEWING removido (PENDING → CUTTING → INVOICED)
- Receção: picker de cor existente ou nova cor
- Movimentos registam cor (migração automática, sem perda de dados)
v3.3:
- Modo LIVE na Produção com validação de desvios | Movimentação em 3 modos
- Edição live do mapa de consumos | Exportação Excel + CSV | Dados corrigidos
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from io import BytesIO
import re
import json

# ===================== PAGE CONFIG =====================
st.set_page_config(
    page_title="SNT CMT — Stock & Produção",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== THEMES (Dark / Clean) =====================
THEMES = {
    'dark': {
        'BG': 'linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%)',
        'TEXT': '#e0e6ed', 'MUTED': '#8b9dc3', 'FAINT': '#64748b', 'ACCENT': '#60a5fa',
        'HEADER_BG': 'linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%)',
        'CARD_BG': 'linear-gradient(145deg, rgba(30,58,95,0.6) 0%, rgba(13,33,55,0.8) 100%)',
        'CARD_BG_SOFT': 'linear-gradient(145deg, rgba(30,58,95,0.4) 0%, rgba(13,33,55,0.6) 100%)',
        'CARD_BORDER': 'rgba(255,255,255,0.06)',
        'INPUT_BG': 'rgba(30,58,95,0.4)',
        'SIDEBAR_BG': 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
        'TABLE_HEAD': '#1e3a5f',
        'TABLE_ROW': 'rgba(30,58,95,0.3)',
        'TABLE_ROW_HOVER': 'rgba(30,58,95,0.5)',
        'BAR_BG': 'rgba(255,255,255,0.05)',
        'LINE': 'rgba(255,255,255,0.1)',
        'BTN_SEC_BG': 'rgba(255,255,255,0.08)',
        'SHADOW': 'rgba(0,0,0,0.3)',
    },
    'clean': {
        'BG': 'linear-gradient(135deg, #f4f6fb 0%, #eaeef6 50%, #e3e9f3 100%)',
        'TEXT': '#1e293b', 'MUTED': '#5b6b85', 'FAINT': '#94a3b8', 'ACCENT': '#2563eb',
        'HEADER_BG': 'linear-gradient(135deg, #ffffff 0%, #e9eef8 100%)',
        'CARD_BG': 'linear-gradient(145deg, #ffffff 0%, #f6f8fc 100%)',
        'CARD_BG_SOFT': 'linear-gradient(145deg, #ffffff 0%, #f2f5fb 100%)',
        'CARD_BORDER': 'rgba(15,23,42,0.08)',
        'INPUT_BG': '#ffffff',
        'SIDEBAR_BG': 'linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%)',
        'TABLE_HEAD': '#e6edf9',
        'TABLE_ROW': '#ffffff',
        'TABLE_ROW_HOVER': '#f1f5fb',
        'BAR_BG': 'rgba(15,23,42,0.06)',
        'LINE': 'rgba(15,23,42,0.1)',
        'BTN_SEC_BG': 'rgba(15,23,42,0.06)',
        'SHADOW': 'rgba(15,23,42,0.08)',
    },
}

CSS_TEMPLATE = """<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root { --text: __TEXT__; --muted: __MUTED__; --faint: __FAINT__; --accent: __ACCENT__; }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: __BG__; }

    /* Header */
    .main-header {
        background: __HEADER_BG__;
        padding: 20px 30px;
        border-radius: 16px;
        margin-bottom: 24px;
        border: 1px solid __CARD_BORDER__;
        box-shadow: 0 8px 32px __SHADOW__;
    }
    .main-header h1 { color: var(--text); margin: 0; font-size: 28px; font-weight: 700; }
    .main-header p { color: var(--muted); margin: 4px 0 0 0; font-size: 13px; }
    .live-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(34,197,94,0.15); color: #22c55e;
        padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600;
        border: 1px solid rgba(34,197,94,0.3);
    }
    .live-dot { width: 6px; height: 6px; background: #22c55e; border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

    /* KPI Cards */
    .kpi-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .kpi-card {
        background: __CARD_BG__;
        border: 1px solid __CARD_BORDER__;
        border-radius: 14px; padding: 20px;
        box-shadow: 0 4px 20px __SHADOW__;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px __SHADOW__; }
    .kpi-label { color: var(--muted); font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
    .kpi-value { color: var(--text); font-size: 32px; font-weight: 700; margin-bottom: 6px; }
    .kpi-delta { font-size: 12px; font-weight: 500; }
    .kpi-delta.up { color: #22c55e; }
    .kpi-delta.down { color: #ef4444; }
    .kpi-delta.warn { color: #f59e0b; }
    .kpi-delta.info { color: #3b82f6; }

    /* Section titles */
    .section-title {
        color: var(--text); font-size: 16px; font-weight: 600;
        margin: 24px 0 12px 0; padding-bottom: 8px;
        border-bottom: 1px solid __CARD_BORDER__;
    }
    .section-subtitle { color: var(--muted); font-size: 12px; margin-bottom: 16px; }

    /* Alert bar */
    .alert-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
    .alert-chip {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 8px 14px; border-radius: 10px; font-size: 12px; font-weight: 500;
        border: 1px solid;
    }
    .alert-chip.critical { background: rgba(239,68,68,0.1); color: #ef4444; border-color: rgba(239,68,68,0.2); }
    .alert-chip.warning { background: rgba(245,158,11,0.1); color: #f59e0b; border-color: rgba(245,158,11,0.2); }
    .alert-chip.info { background: rgba(59,130,246,0.1); color: #3b82f6; border-color: rgba(59,130,246,0.2); }
    .alert-chip.ok { background: rgba(34,197,94,0.1); color: #22c55e; border-color: rgba(34,197,94,0.2); }
    .alert-dot { width: 6px; height: 6px; border-radius: 50%; }
    .alert-chip.critical .alert-dot { background: #ef4444; }
    .alert-chip.warning .alert-dot { background: #f59e0b; }
    .alert-chip.info .alert-dot { background: #3b82f6; }
    .alert-chip.ok .alert-dot { background: #22c55e; }

    /* Tables */
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    .stDataFrame thead th { background: __TABLE_HEAD__ !important; color: var(--text) !important; font-weight: 600 !important; font-size: 12px !important; }
    .stDataFrame tbody td { background: __TABLE_ROW__ !important; color: var(--text) !important; font-size: 12px !important; border-bottom: 1px solid __CARD_BORDER__ !important; }
    .stDataFrame tbody tr:hover td { background: __TABLE_ROW_HOVER__ !important; }

    /* Cards */
    .info-card {
        background: __CARD_BG_SOFT__;
        border: 1px solid __CARD_BORDER__;
        border-radius: 12px; padding: 16px;
        margin-bottom: 12px;
    }
    .info-card-title { color: var(--text); font-size: 13px; font-weight: 600; margin-bottom: 8px; }
    .info-card-text { color: var(--muted); font-size: 12px; line-height: 1.6; }

    /* Form styling */
    .stSelectbox > div > div { background: __INPUT_BG__ !important; border-color: __CARD_BORDER__ !important; border-radius: 10px !important; }
    .stNumberInput > div > div > div { background: __INPUT_BG__ !important; border-color: __CARD_BORDER__ !important; border-radius: 10px !important; }
    .stTextInput > div > div > input { background: __INPUT_BG__ !important; border-color: __CARD_BORDER__ !important; border-radius: 10px !important; color: var(--text) !important; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important; border: none !important; border-radius: 10px !important;
        padding: 8px 20px !important; font-weight: 600 !important; font-size: 13px !important;
        box-shadow: 0 4px 15px rgba(37,99,235,0.3) !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(37,99,235,0.4) !important; }
    .stButton > button[kind="secondary"] { background: __BTN_SEC_BG__ !important; color: var(--muted) !important; box-shadow: none !important; }

    /* Sidebar */
    .css-1d391kg, .css-1lcbmhc { background: __SIDEBAR_BG__ !important; }
    .stSidebar .stRadio > div { background: transparent !important; }
    .stSidebar .stRadio label { color: var(--muted) !important; font-size: 13px !important; padding: 8px 12px !important; border-radius: 8px !important; transition: all 0.2s !important; }
    .stSidebar .stRadio label:hover { background: __BTN_SEC_BG__ !important; color: var(--text) !important; }
    .stSidebar .stRadio [aria-checked="true"] + label { background: rgba(37,99,235,0.2) !important; color: var(--accent) !important; font-weight: 600 !important; border-left: 3px solid #2563eb !important; }

    /* Timeline */
    .timeline { position: relative; padding-left: 24px; }
    .timeline::before { content: ''; position: absolute; left: 7px; top: 0; bottom: 0; width: 2px; background: __LINE__; }
    .timeline-item { position: relative; padding: 12px 0; }
    .timeline-item::before { content: ''; position: absolute; left: -21px; top: 16px; width: 10px; height: 10px; border-radius: 50%; }
    .timeline-item.completed::before { background: #22c55e; }
    .timeline-item.warning::before { background: #f59e0b; }
    .timeline-item.pending::before { background: #3b82f6; }
    .timeline-date { color: var(--muted); font-size: 11px; font-weight: 600; }
    .timeline-text { color: var(--text); font-size: 13px; margin-top: 2px; }
    .timeline-meta { color: var(--faint); font-size: 11px; margin-top: 2px; }

    /* Consumo bars */
    .consumo-row { display: flex; align-items: center; gap: 16px; padding: 10px 0; border-bottom: 1px solid __CARD_BORDER__; }
    .consumo-model { flex: 2; color: var(--text); font-size: 13px; font-weight: 500; }
    .consumo-fabric { flex: 1; color: var(--muted); font-size: 12px; }
    .consumo-val { flex: 0.8; color: var(--muted); font-size: 12px; text-align: right; }
    .consumo-bar-bg { flex: 1.5; height: 6px; background: __BAR_BG__; border-radius: 3px; overflow: hidden; }
    .consumo-bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
    .consumo-var { flex: 0.6; font-size: 12px; font-weight: 600; text-align: right; }
    .consumo-var.up { color: #ef4444; }
    .consumo-var.down { color: #22c55e; }

    /* Warehouse cards */
    .wh-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
    .wh-card {
        background: __CARD_BG_SOFT__;
        border: 1px solid __CARD_BORDER__; border-radius: 14px; padding: 20px;
        box-shadow: 0 4px 20px __SHADOW__;
        transition: all 0.2s;
    }
    .wh-card:hover { border-color: __LINE__; box-shadow: 0 8px 30px __SHADOW__; }
    .wh-name { color: var(--text); font-size: 14px; font-weight: 600; margin-bottom: 8px; }
    .wh-total { color: var(--accent); font-size: 28px; font-weight: 700; margin-bottom: 4px; }
    .wh-detail { color: var(--muted); font-size: 11px; line-height: 1.5; margin-bottom: 8px; }
    .wh-rolls { color: var(--faint); font-size: 11px; }

    /* Trace card */
    .trace-card {
        background: __CARD_BG_SOFT__;
        border: 1px solid __CARD_BORDER__; border-radius: 14px; padding: 20px;
        margin-bottom: 16px;
    }
    .trace-token {
        display: inline-block; background: rgba(37,99,235,0.15); color: var(--accent);
        padding: 4px 12px; border-radius: 8px; font-size: 13px; font-weight: 600;
        font-family: 'SF Mono', monospace; border: 1px solid rgba(37,99,235,0.2);
    }
    .trace-details { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 16px 0; }
    .trace-detail-label { color: var(--faint); font-size: 11px; text-transform: uppercase; }
    .trace-detail-value { color: var(--text); font-size: 14px; font-weight: 600; margin-top: 4px; }

    /* Live deviation indicator */
    .dev-box { border-radius: 12px; padding: 16px; text-align: center; margin: 12px 0; }
    .dev-box.ok { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); }
    .dev-box.warn { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); }
    .dev-box.bad { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); }
    .dev-value { font-size: 28px; font-weight: 700; }
    .dev-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: __CARD_BG_SOFT__ !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; }
    .stTabs [data-baseweb="tab"] { color: var(--muted) !important; font-size: 13px !important; border-radius: 8px !important; padding: 8px 16px !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: rgba(37,99,235,0.2) !important; color: var(--accent) !important; font-weight: 600 !important; }

    /* Badges */
    .badge {
        display: inline-flex; align-items: center; padding: 3px 10px;
        border-radius: 6px; font-size: 11px; font-weight: 600;
    }
    .badge.available { background: rgba(34,197,94,0.15); color: #22c55e; }
    .badge.reserved { background: rgba(245,158,11,0.15); color: #f59e0b; }
    .badge.inprocess { background: rgba(59,130,246,0.15); color: #3b82f6; }
    .badge.invoiced { background: rgba(100,116,139,0.15); color: var(--faint); }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: __TABLE_ROW__; }
    ::-webkit-scrollbar-thumb { background: __LINE__; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--faint); }
</style>
"""

def inject_css():
    theme = st.session_state.get('theme', 'dark')
    pal = THEMES.get(theme, THEMES['dark'])
    css = CSS_TEMPLATE
    for k, v in pal.items():
        css = css.replace(f'__{k}__', v)
    st.markdown(css, unsafe_allow_html=True)

inject_css()

# ===================== I18N (PT / EN) =====================
T = {
'pt': {
 'm_dashboard': '📊 Dashboard', 'm_stock': '📦 Stock', 'm_incoming': '🚢 A Chegar',
 'm_production': '👕 Produção', 'm_consumos': '📊 Consumos', 'm_movement': '🚚 Movimentar',
 'm_tools': '🛠 Ferramentas',
 'sb_system': 'Sistema de Stock & Produção', 'sb_nav': 'Navegar', 'sb_data': 'Dados: CW29 2026',
 'sb_theme': '🎨 Tema', 'sb_lang': '🌐 Idioma',
 'h_sub': 'Sistema de Stock & Produção v3.7 | CW29 2026',
 'k_avail': 'STOCK DISPONÍVEL', 'k_avail_d': 'armazém + stock conf.',
 'k_process': 'EM PROCESSO (CONF.)', 'k_process_d': 'POs garment ativas',
 'k_incoming': 'A CHEGAR', 'k_incoming_d': 'POs tecido pendentes',
 'k_need': 'NECESSIDADE PENDENTE', 'k_need_d': 'POs garment por faturar',
 'k_net': 'POSIÇÃO LÍQUIDA', 'k_net_d': 'disponível + em processo',
 'k_plan': 'POSIÇÃO PLANEAMENTO', 'k_plan_d': 'líquido + a chegar − necessidade',
 'd_alerts': 'Alertas do Sistema',
 'd_pos': 'Posição de Stock por Referência de Tecido',
 'd_pos_sub': 'stock líquido = disponível + em processo | planeamento = líquido + a chegar − necessidade',
 'd_pipe': 'Pipeline de Produção por Confeccionador',
 'd_err': 'Erro no dashboard: ',
 'd_init': 'A base de dados pode estar a inicializar. Aguarde e recarregue.',
 'st_crit': 'falha crítica', 'st_low': 'stock baixo', 'st_risk': 'risco',
 'al_crit': 'Falha Crítica', 'al_low': 'Stock Baixo', 'al_risk': 'Risco',
 'al_risk_txt': 'necessidade > stock líquido', 'al_bal': 'equilibrados',
 'c_supplier': 'Fornecedor', 'c_ref': 'Ref', 'c_color': 'Cor', 'c_metres': 'Metros',
 'c_lot': 'Lote', 'c_wh': 'Armazém', 'c_status': 'Status', 'c_po': 'PO Garment',
 'c_notes': 'Notas', 'c_token': 'Token', 'c_desc': 'Descrição', 'c_colors': 'Cores',
 'c_avail': 'Disponível', 'c_inproc': 'Em Processo', 'c_net': 'Stock Líquido',
 'c_inc': 'A Chegar', 'c_need': 'Necessidade', 'c_plan': 'Planeamento',
 'c_date_exp': 'Data Prevista', 'c_tracking': 'Tracking', 'c_po2': 'PO',
 'c_model': 'Modelo', 'c_conf': 'Confeccionador', 'c_qty': 'Qty', 'c_delivery': 'Entrega',
 'c_state': 'Estado', 'c_fsup': 'Fornecedor Tecido', 'c_fref': 'Ref Tecido',
 'c_loc': 'Local', 'c_dt': 'Data/Hora', 'c_type': 'Tipo', 'c_from': 'De', 'c_to': 'Para',
 'c_pcs': 'Peças', 'c_mexp': 'Metros Esperados', 'c_mreal': 'Metros Reais',
 'c_dev': 'Desvio %', 'c_cutdate': 'Data Corte', 'c_activepo': 'POs Ativas',
 'c_totpcs': 'Total Peças', 'c_type2': 'Tipo', 'c_rollslot': 'Rolos/Lotes',
 'c_availm': 'Available m', 'c_inprocm': 'In Process m', 'c_totalm': 'Total m',
 'opt_all': 'Todos', 'opt_all_f': 'Todas',
 's_title': '📦 Stock por Armazém',
 's_sub': 'resumo compacto por local · available = por alocar | in process = em transformação',
 's_detail': 'Detalhe de Rolos e Lotes', 's_export': 'Exportar seleção atual',
 's_sem_cor': 'rolos/lotes sem cor atribuída — corrige abaixo para teres a estrutura ref + cor completa',
 's_assign': '🎨 Atribuir / corrigir cor de rolos',
 's_assign_sub': 'atribui cor em massa: filtra por ref/armazém, seleciona rolos (ou aplica a todos os listados) e escolhe a cor',
 'f_ref': 'Referência', 'f_wh': 'Armazém', 'f_only_nocolor': 'Mostrar só rolos sem cor',
 'f_rolls': 'Rolos', 'f_apply_all': 'Aplicar a TODOS os {n} rolos listados',
 'f_color_apply': 'Cor a aplicar', 'f_new_color': '➕ Nova cor…', 'f_type_color': 'Escreve a nova cor',
 'b_apply_color': '✓ Aplicar cor', 'err_select_rolls': "Seleciona rolos ou ativa 'Aplicar a TODOS'.",
 'err_pick_color': 'Escolhe ou escreve uma cor.',
 'ok_color': 'aplicada a {n} rolos de {ref}.',
 'ok_nocolor': '✅ Sem rolos por colorir com estes filtros.',
 'i_title': '🚢 A Chegar',
 'i_sub': 'Encomendas de tecido pendentes — só contam para planeamento, não entram no stock líquido',
 'i_none': 'Nenhuma encomenda pendente.', 'i_mark': 'Marcar chegada',
 'i_mark_sub': 'quando o tecido chega, marca aqui a PO — depois regista os rolos em 🚚 Movimentar → Receção',
 'i_po': 'PO de tecido', 'b_arrived': '✓ Chegou',
 'ok_arrived': 'PO {po} marcada como recebida. Regista agora os rolos em 🚚 Movimentar → Receção.',
 'i_cal': 'Calendário de Chegadas', 'i_notrack': 'sem rastreio',
 'p_title': '👕 Produção',
 'p_sub': 'modo live: lança consumos de corte, valida desvios e muda estados — tudo por dropdown',
 'tab_live': '⚡ Modo Live — Registar Corte', 'tab_edit': '✏️ Tabela Editável', 'tab_status': '🔄 Mudar Estado PO',
 'p_sel_po': 'Seleciona a PO garment', 'p_no_active': 'Sem POs ativas para registar corte.',
 'p_pcs': 'Peças cortadas', 'p_metres': 'Metros reais consumidos', 'b_cut': '✓ Registar corte',
 'dev_ok': 'dentro da tolerância', 'dev_warn': 'atenção — desvio 2–5%', 'dev_bad': '⚠️ DESVIO CRÍTICO > 5%',
 'dev_label': 'Desvio vs mapa',
 'p_no_map': '⚠️ Este modelo não tem consumo no mapa. O registo fica sem validação de desvio — considera adicioná-lo em 📊 Consumos.',
 'err_vals': 'Peças e metros têm de ser > 0',
 'ok_cut': '✅ Corte registado: {pcs} pcs × {mpc} m/pc = {m}m',
 'card_conf': 'Confeccionador', 'card_pcs': 'Peças PO', 'card_fref': 'Ref Tecido', 'card_cons': 'Consumo Esperado',
 'src_real': '📈 média real produtiva', 'src_std': '📐 standard predefinido', 'no_map': 'sem mapa',
 'p_edit_sub': 'tabela dinâmica editável — edita células, adiciona ou remove linhas e grava com um clique. faturação fica na tab ao lado (faz baixa de stock).',
 'p_view': 'Ver', 'v_active': 'Ativas (PENDING + CUTTING)',
 'b_save_prod': '💾 Guardar alterações de produção', 'ok_prod': '✅ Produção guardada — {n} POs.',
 'p_no_inv': 'Sem POs faturadas.',
 'p_status_sub': 'mudança de estado por dropdown — INVOICED faz baixa automática dos metros em processo',
 'p_new_status': 'Novo estado', 'b_apply_status': '✓ Aplicar estado',
 'ok_inv': '✅ PO {po} faturada — {m}m saíram de em processo.',
 'ok_status': '✅ PO {po} → {st}',
 'c_title': '📊 Consumos',
 'c_sub': 'mapa partilhado por modelo base — editável na grelha. desvio > 5% gera alerta.',
 'c_tab_map': '📊 Mapa Visual', 'c_tab_real': '🧾 Registos Reais', 'c_tab_edit': '✏️ Editar Mapa',
 'lg_exp': 'esperado', 'lg_real': 'real médio', 'lg_dev': 'desvio > 5% = alerta',
 'c_nodata': 'sem dados', 'c_high': '⚠️ {n} consumos com desvio > 5%',
 'c_edit_sub': 'edita diretamente o consumo standard (m/pc esperado) — alterações gravam ao clicar em Guardar',
 'b_save_cm': '💾 Guardar mapa de consumos', 'ok_cm': '✅ Mapa guardado — {n} modelos.',
 'c_none': 'Sem consumos registados.',
 'ec_exp': 'Esperado m/pc', 'ec_real': 'Real Médio m/pc',
 'mv_title': '🚚 Movimentar Tecido',
 'mv_sub': '3 modos: rolos conhecidos (tokens) · lote agregado (divisível) · metros consolidados (FIFO)',
 'tab_m1': '🎫 Rolos Conhecidos', 'tab_m2': '📦 Lote Agregado', 'tab_m3': '🔢 Metros Consolidados',
 'tab_recv': '📥 Receção', 'tab_inv': '📄 Faturação PO',
 'm1_sub': 'seleciona rolos individuais, ou remessas completas de uma vez, e move para outro local',
 'm1_wh': 'De (armazém atual)', 'm1_lots': '⚡ Seleção rápida por remessa',
 'b_picklots': '⚡ Selecionar rolos das remessas', 'm1_rolls': 'Rolos a mover',
 'm1_count': '{n} rolos selecionados — total {m}m', 'm1_to': 'Para', 'm1_status': 'Estado no destino',
 'st_avail_wh': 'AVAILABLE (armazém)', 'st_inproc_conf': 'IN_PROCESS (confeccionador)',
 'b_m1': '✓ Mover rolos selecionados', 'err_m1': 'Seleciona pelo menos um rolo.',
 'ok_m1': '✅ {n} rolos ({m}m) movidos de {a} → {b}',
 'm1_none': 'Sem rolos disponíveis com estes filtros.',
 'm2_sub': 'lotes P- em confeccionadores — podes mover o total ou dividir (parcial)',
 'm2_lot': 'Lote agregado', 'm2_metres': 'Metros a mover',
 'm2_split': '✂️ Divisão: o lote original fica com {rest}m e é criado um novo lote de {m}m em {to}',
 'b_m2': '✓ Mover lote', 'err_m2': 'Metros > 0 necessários.',
 'ok_m2_split': '✅ Lote dividido: {m}m → {tok} em {to}',
 'ok_m2': '✅ Lote {tok} ({m}m) movido → {to}',
 'm2_none': 'Sem lotes em confeccionadores.',
 'm3_sub': 'move X metros de uma referência/armazém — o sistema retira dos rolos disponíveis por ordem (FIFO) e cria lote no destino',
 'm3_avail': 'disponível em {wh}: **{m}m**', 'm3_po': 'PO garment (opcional — reserva)',
 'b_m3': '✓ Mover metros', 'err_m3': 'Metros inválidos (disponível: {m}m)',
 'ok_m3': '✅ {m}m movidos de {a} → {b} como {tok}',
 'recv_title': '📥 Receção de Novo Tecido',
 'recv_text': 'Ao receber tecido de fornecedor, o sistema gera token automático <strong>R-{REF}-{NNN}</strong>. Cada rolo tem token único, metros exatos, lote/cor e histórico completo.',
 'f_recv_metres': 'Metros recebidos', 'f_recv_wh': 'Armazém destino', 'f_recv_lot': 'Lote (opcional)',
 'f_color': 'Cor', 'b_recv': '✓ Receber e gerar token', 'ok_recv': '✅ Novo rolo criado: {tok} ({m}m)',
 'err_metres': 'Metros deve ser > 0',
 'inv_title': '📄 Faturação de PO Garment',
 'inv_text': 'Quando uma PO garment é faturada, os metros em processo ligados a ela saem automaticamente do stock (INVOICED). As movimentações do mês têm de bater certo com a faturação.',
 'inv_po': 'PO garment a faturar', 'inv_m': 'Metros em processo ligados a esta PO: {m}m',
 'inv_no_m': 'Sem metros em processo ligados por token — a faturação só muda o estado da PO.',
 'b_inv': '✓ Confirmar faturação', 'ok_inv2': '✅ PO {po} faturada. {m}m saíram de em processo.',
 'inv_none': 'Sem POs por faturar.',
 'rules': 'Regras de Tokens', 'rule_new': '✅ Novos Rolos — Token Individual',
 'rule_new_txt': 'Receção de tecido → token automático<br>Formato: <span class="trace-token">R-{REF}-{NNN}</span><br><br>Cada rolo tem: token único · metros exatos · lote/cor · histórico completo',
 'rule_conf': '⚠️ Confeccionadores — Lotes Agregados',
 'rule_conf_txt': 'Tecido em confeccionador → <span class="trace-token">P-{CONF}-{REF}-{NNN}</span><br><br>Metros totais sem lote original · <strong>divisível</strong> (modo Lote Agregado) · sai de em processo na faturação',
 'hist': 'Histórico de Movimentações — Últimas 20', 'mv_none': 'Sem movimentações registadas.',
 'tr_title': '🔍 Rastreio',
 'tr_sub': 'histórico de cada rolo/lote desde entrada até faturação — procura por token, PO garment, lote ou referência',
 'tr_search': '🔍 Procurar...', 'tr_notfound': 'Nenhum resultado encontrado. Tenta outro token, PO ou referência.',
 'tr_hist': 'Histórico de Movimentações', 'tr_cons': 'Consumos Registados',
 'tr_rolls': 'Rolos/Lotes Alocados', 'tr_movs': 'Movimentações',
 'tl_ref': 'Referência', 'tl_metres': 'Metros', 'tl_lot': 'Lote', 'tl_color': 'Cor',
 'tl_loc': 'Local', 'tl_recv': 'Recebido', 'tl_last': 'Último Mov.',
 'ex_title': '📤 Exportar',
 'ex_sub': 'extratos Excel e CSV para colegas de planeamento e financeiros',
 'ex_sum': 'Stock Resumido', 'ex_sum_d': 'posição por referência + cor, com planeamento',
 'ex_det': 'Stock Detalhado', 'ex_det_d': 'todos os rolos e lotes com tokens',
 'ex_cons': 'Consumos & Movimentos', 'ex_cons_d': 'cortes com desvios + movimentações do mês (bater com faturação)',
},
'en': {
 'm_dashboard': '📊 Dashboard', 'm_stock': '📦 Stock', 'm_incoming': '🚢 Incoming',
 'm_production': '👕 Production', 'm_consumos': '📊 Consumption', 'm_movement': '🚚 Move Fabric',
 'm_tools': '🛠 Tools',
 'sb_system': 'Fabric Stock & Production System', 'sb_nav': 'Navigate', 'sb_data': 'Data: CW29 2026',
 'sb_theme': '🎨 Theme', 'sb_lang': '🌐 Language',
 'h_sub': 'Fabric Stock & Production System v3.7 | CW29 2026',
 'k_avail': 'AVAILABLE STOCK', 'k_avail_d': 'warehouse + conf. stock',
 'k_process': 'IN PROCESS (CONF.)', 'k_process_d': 'active garment POs',
 'k_incoming': 'INCOMING', 'k_incoming_d': 'pending fabric POs',
 'k_need': 'PENDING NECESSITY', 'k_need_d': 'uninvoiced garment POs',
 'k_net': 'NET POSITION', 'k_net_d': 'available + in process',
 'k_plan': 'PLANNING POSITION', 'k_plan_d': 'net + incoming − necessity',
 'd_alerts': 'System Alerts',
 'd_pos': 'Stock Position by Fabric Reference',
 'd_pos_sub': 'net stock = available + in process | planning = net + incoming − necessity',
 'd_pipe': 'Production Pipeline by Contractor',
 'd_err': 'Dashboard error: ',
 'd_init': 'The database may be initializing. Please wait and reload.',
 'st_crit': 'critical failure', 'st_low': 'low stock', 'st_risk': 'risk',
 'al_crit': 'Critical failure', 'al_low': 'Low stock', 'al_risk': 'Risk',
 'al_risk_txt': 'necessity > net stock', 'al_bal': 'balanced',
 'c_supplier': 'Supplier', 'c_ref': 'Ref', 'c_color': 'Color', 'c_metres': 'Metres',
 'c_lot': 'Lot', 'c_wh': 'Warehouse', 'c_status': 'Status', 'c_po': 'Garment PO',
 'c_notes': 'Notes', 'c_token': 'Token', 'c_desc': 'Description', 'c_colors': 'Colors',
 'c_avail': 'Available', 'c_inproc': 'In Process', 'c_net': 'Net Stock',
 'c_inc': 'Incoming', 'c_need': 'Necessity', 'c_plan': 'Planning',
 'c_date_exp': 'Expected Date', 'c_tracking': 'Tracking', 'c_po2': 'PO',
 'c_model': 'Model', 'c_conf': 'Contractor', 'c_qty': 'Qty', 'c_delivery': 'Delivery',
 'c_state': 'Status', 'c_fsup': 'Fabric Supplier', 'c_fref': 'Fabric Ref',
 'c_loc': 'Location', 'c_dt': 'Date/Time', 'c_type': 'Type', 'c_from': 'From', 'c_to': 'To',
 'c_pcs': 'Pcs', 'c_mexp': 'Expected Metres', 'c_mreal': 'Actual Metres',
 'c_dev': 'Deviation %', 'c_cutdate': 'Cut Date', 'c_activepo': 'Active POs',
 'c_totpcs': 'Total Pieces', 'c_type2': 'Type', 'c_rollslot': 'Rolls/Lots',
 'c_availm': 'Available m', 'c_inprocm': 'In Process m', 'c_totalm': 'Total m',
 'opt_all': 'All', 'opt_all_f': 'All',
 's_title': '📦 Stock by Warehouse',
 's_sub': 'compact summary by location · available = unallocated | in process = being transformed',
 's_detail': 'Roll & Lot Detail', 's_export': 'Export current selection',
 's_sem_cor': 'rolls/lots without assigned color — fix below to complete the ref + color structure',
 's_assign': '🎨 Assign / fix roll color',
 's_assign_sub': 'bulk color assignment: filter by ref/warehouse, select rolls (or apply to all listed) and pick the color',
 'f_ref': 'Reference', 'f_wh': 'Warehouse', 'f_only_nocolor': 'Show only rolls without color',
 'f_rolls': 'Rolls', 'f_apply_all': 'Apply to ALL {n} listed rolls',
 'f_color_apply': 'Color to apply', 'f_new_color': '➕ New color…', 'f_type_color': 'Type the new color',
 'b_apply_color': '✓ Apply color', 'err_select_rolls': "Select rolls or enable 'Apply to ALL'.",
 'err_pick_color': 'Pick or type a color.',
 'ok_color': 'applied to {n} rolls of {ref}.',
 'ok_nocolor': '✅ No rolls left to color with these filters.',
 'i_title': '🚢 Incoming',
 'i_sub': 'Pending fabric orders — they count for planning only, not for net stock',
 'i_none': 'No pending orders.', 'i_mark': 'Mark arrival',
 'i_mark_sub': 'when the fabric arrives, mark the PO here — then register the rolls in 🚚 Move Fabric → Receiving',
 'i_po': 'Fabric PO', 'b_arrived': '✓ Arrived',
 'ok_arrived': 'PO {po} marked as received. Now register the rolls in 🚚 Move Fabric → Receiving.',
 'i_cal': 'Arrival Calendar', 'i_notrack': 'no tracking',
 'p_title': '👕 Production',
 'p_sub': 'live mode: register cutting consumption, validate deviations and change statuses — all via dropdowns',
 'tab_live': '⚡ Live Mode — Register Cut', 'tab_edit': '✏️ Editable Table', 'tab_status': '🔄 Change PO Status',
 'p_sel_po': 'Select garment PO', 'p_no_active': 'No active POs to register cuts.',
 'p_pcs': 'Pieces cut', 'p_metres': 'Actual metres consumed', 'b_cut': '✓ Register cut',
 'dev_ok': 'within tolerance', 'dev_warn': 'warning — 2–5% deviation', 'dev_bad': '⚠️ CRITICAL DEVIATION > 5%',
 'dev_label': 'Deviation vs map',
 'p_no_map': '⚠️ This model has no consumption in the map. The record will have no deviation validation — consider adding it in 📊 Consumption.',
 'err_vals': 'Pieces and metres must be > 0',
 'ok_cut': '✅ Cut registered: {pcs} pcs × {mpc} m/pc = {m}m',
 'card_conf': 'Contractor', 'card_pcs': 'PO Pieces', 'card_fref': 'Fabric Ref', 'card_cons': 'Expected Consumption',
 'src_real': '📈 real production average', 'src_std': '📐 predefined standard', 'no_map': 'no map',
 'p_edit_sub': 'editable dynamic table — edit cells, add or remove rows and save with one click. Invoicing stays in the next tab (it deducts stock).',
 'p_view': 'Show', 'v_active': 'Active (PENDING + CUTTING)',
 'b_save_prod': '💾 Save production changes', 'ok_prod': '✅ Production saved — {n} POs.',
 'p_no_inv': 'No invoiced POs.',
 'p_status_sub': 'status change via dropdown — INVOICED automatically deducts in-process metres',
 'p_new_status': 'New status', 'b_apply_status': '✓ Apply status',
 'ok_inv': '✅ PO {po} invoiced — {m}m left in-process.',
 'ok_status': '✅ PO {po} → {st}',
 'c_title': '📊 Consumption',
 'c_sub': 'shared map by base model — editable in the grid. deviation > 5% triggers an alert.',
 'c_tab_map': '📊 Visual Map', 'c_tab_real': '🧾 Actual Records', 'c_tab_edit': '✏️ Edit Map',
 'lg_exp': 'expected', 'lg_real': 'actual average', 'lg_dev': 'deviation > 5% = alert',
 'c_nodata': 'no data', 'c_high': '⚠️ {n} consumptions with deviation > 5%',
 'c_edit_sub': 'edit the standard consumption directly (expected m/pc) — changes are saved when you click Save',
 'b_save_cm': '💾 Save consumption map', 'ok_cm': '✅ Map saved — {n} models.',
 'c_none': 'No consumptions recorded.',
 'ec_exp': 'Expected m/pc', 'ec_real': 'Actual Avg m/pc',
 'mv_title': '🚚 Move Fabric',
 'mv_sub': '3 modes: known rolls (tokens) · aggregate lot (splittable) · consolidated metres (FIFO)',
 'tab_m1': '🎫 Known Rolls', 'tab_m2': '📦 Aggregate Lot', 'tab_m3': '🔢 Consolidated Metres',
 'tab_recv': '📥 Receiving', 'tab_inv': '📄 PO Invoicing',
 'm1_sub': 'select individual rolls, or entire shipments at once, and move to another location',
 'm1_wh': 'From (current warehouse)', 'm1_lots': '⚡ Quick select by shipment',
 'b_picklots': '⚡ Select rolls from shipments', 'm1_rolls': 'Rolls to move',
 'm1_count': '{n} rolls selected — total {m}m', 'm1_to': 'To', 'm1_status': 'Status at destination',
 'st_avail_wh': 'AVAILABLE (warehouse)', 'st_inproc_conf': 'IN_PROCESS (contractor)',
 'b_m1': '✓ Move selected rolls', 'err_m1': 'Select at least one roll.',
 'ok_m1': '✅ {n} rolls ({m}m) moved from {a} → {b}',
 'm1_none': 'No rolls available with these filters.',
 'm2_sub': 'P- lots at contractors — move the total or split (partial)',
 'm2_lot': 'Aggregate lot', 'm2_metres': 'Metres to move',
 'm2_split': '✂️ Split: the original lot keeps {rest}m and a new lot of {m}m is created at {to}',
 'b_m2': '✓ Move lot', 'err_m2': 'Metres > 0 required.',
 'ok_m2_split': '✅ Lot split: {m}m → {tok} at {to}',
 'ok_m2': '✅ Lot {tok} ({m}m) moved → {to}',
 'm2_none': 'No lots at contractors.',
 'm3_sub': 'move X metres of a reference/warehouse — the system deducts from available rolls in order (FIFO) and creates a lot at destination',
 'm3_avail': 'available at {wh}: **{m}m**', 'm3_po': 'Garment PO (optional — reserve)',
 'b_m3': '✓ Move metres', 'err_m3': 'Invalid metres (available: {m}m)',
 'ok_m3': '✅ {m}m moved from {a} → {b} as {tok}',
 'recv_title': '📥 New Fabric Receiving',
 'recv_text': 'When receiving fabric from a supplier, the system generates an automatic token <strong>R-{REF}-{NNN}</strong>. Each roll has a unique token, exact metres, lot/color and full history.',
 'f_recv_metres': 'Metres received', 'f_recv_wh': 'Destination warehouse', 'f_recv_lot': 'Lot (optional)',
 'f_color': 'Color', 'b_recv': '✓ Receive & generate token', 'ok_recv': '✅ New roll created: {tok} ({m}m)',
 'err_metres': 'Metres must be > 0',
 'inv_title': '📄 Garment PO Invoicing',
 'inv_text': 'When a garment PO is invoiced, the in-process metres linked to it automatically leave stock (INVOICED). The month movements must match invoicing.',
 'inv_po': 'Garment PO to invoice', 'inv_m': 'In-process metres linked to this PO: {m}m',
 'inv_no_m': 'No in-process metres linked by token — invoicing only changes the PO status.',
 'b_inv': '✓ Confirm invoicing', 'ok_inv2': '✅ PO {po} invoiced. {m}m left in-process.',
 'inv_none': 'No POs to invoice.',
 'rules': 'Token Rules', 'rule_new': '✅ New Rolls — Individual Token',
 'rule_new_txt': 'Fabric receiving → automatic token<br>Format: <span class="trace-token">R-{REF}-{NNN}</span><br><br>Each roll has: unique token · exact metres · lot/color · full history',
 'rule_conf': '⚠️ Contractors — Aggregate Lots',
 'rule_conf_txt': 'Fabric at contractor → <span class="trace-token">P-{CONF}-{REF}-{NNN}</span><br><br>Total metres without original lot · <strong>splittable</strong> (Aggregate Lot mode) · leaves in-process on invoicing',
 'hist': 'Movement History — Last 20', 'mv_none': 'No movements recorded.',
 'tr_title': '🔍 Trace',
 'tr_sub': 'history of every roll/lot from entry to invoicing — search by token, garment PO, lot or reference',
 'tr_search': '🔍 Search...', 'tr_notfound': 'No results found. Try another token, PO or reference.',
 'tr_hist': 'Movement History', 'tr_cons': 'Recorded Consumptions',
 'tr_rolls': 'Allocated Rolls/Lots', 'tr_movs': 'Movements',
 'tl_ref': 'Reference', 'tl_metres': 'Metres', 'tl_lot': 'Lot', 'tl_color': 'Color',
 'tl_loc': 'Location', 'tl_recv': 'Received', 'tl_last': 'Last Move',
 'ex_title': '📤 Export',
 'ex_sub': 'Excel and CSV extracts for planning and finance colleagues',
 'ex_sum': 'Stock Summary', 'ex_sum_d': 'position by reference + color, with planning',
 'ex_det': 'Detailed Stock', 'ex_det_d': 'all rolls and lots with tokens',
 'ex_cons': 'Consumption & Movements', 'ex_cons_d': 'cuts with deviations + month movements (match invoicing)',
},
}

def t(key, **kwargs):
    """Tradução PT/EN com formatação opcional."""
    lang = st.session_state.get('lang', 'pt') if hasattr(st, 'session_state') else 'pt'
    txt = T.get(lang, T['pt']).get(key, T['pt'].get(key, key))
    return txt.format(**kwargs) if kwargs else txt

# ===================== DB SETUP =====================
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "snt_cmt_v37.db")

# ===================== DB CONNECTION (sem cache) =====================
def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def query_to_df(query, params=()):
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_sql(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def execute_many(query, params_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany(query, params_list)
    conn.commit()
    conn.close()

def log_movement(move_type, token, from_loc, to_loc, ref_code, metres, po_garment=None, notes=None, color=None):
    execute_sql(
        "INSERT INTO movements (date_time, move_type, token, from_location, to_location, ref_code, color, metres, po_garment, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(), move_type, token, from_loc, to_loc, ref_code, color, metres, po_garment, notes))

def next_token(prefix, ref_code):
    """Gera próximo token sequencial para um prefixo+ref."""
    safe_ref = ref_code.replace('/', '_').replace(' ', '_')
    like = f"{prefix}-{safe_ref}-%"
    df = query_to_df("SELECT token FROM fabric_rolls WHERE token LIKE ?", (like,))
    n = len(df) + 1
    while True:
        token = f"{prefix}-{safe_ref}-{n:03d}"
        chk = query_to_df("SELECT COUNT(*) as c FROM fabric_rolls WHERE token = ?", (token,))
        if chk.iloc[0]['c'] == 0:
            return token
        n += 1

# ===================== CONSTANTES =====================
WAREHOUSES = ['XBS', 'Riopele']
CONFECCIONADORES = ['Samidel', 'Costa Correia', 'Tyrrell', 'Acorfato', 'Fabrijeans',
                    'Fabrijeans / Costa C', 'António & Carla', 'Denimworks', 'Vermis']
ALL_LOCATIONS = WAREHOUSES + CONFECCIONADORES + ['Fornecedor', 'Cliente']
PROD_STATUSES = ['PENDING', 'CUTTING', 'INVOICED']
ROLL_STATUSES = ['AVAILABLE', 'RESERVED', 'IN_PROCESS', 'INVOICED']

# ===================== SISTEMA DE COR =====================
# A cor anda sempre ligada à referência: representação visual consistente em todo o site
import hashlib as _hashlib

COLOR_KEYWORDS = [
    (('navy', 'midnight', 'blue nights', 'blue', 'azul'), '🔵'),
    (('black', 'preto', 'noir'), '⚫'),
    (('grey', 'gray', 'flint', 'pepper', 'steel', 'cinza', 'melange'), '🔘'),
    (('green', 'pine', 'evergreen', 'verde', 'khaki', 'olive'), '🟢'),
    (('brown', 'mocha', 'cognac', 'espresso', 'walnut', 'camel', 'castanho'), '🟤'),
    (('beige', 'sand', 'vanilla', 'almond', 'sahara', 'cream', 'areia'), '🟡'),
    (('berry', 'purple', 'violet', 'lilac', 'roxo'), '🟣'),
    (('red', 'wine', 'bordeaux', 'vermelho', 'cherry'), '🔴'),
    (('orange', 'rust', 'terracota', 'laranja'), '🟠'),
]
COLOR_PALETTE = ['🔵', '🟢', '🟤', '🟣', '🟠', '🔴', '🟡']

def color_dot(color):
    """Ponto de cor estável para uma cor de tecido."""
    if not color or str(color).strip() in ('', 'None'):
        return '⚪'
    c = str(color).lower()
    for keys, dot in COLOR_KEYWORDS:
        if any(k in c for k in keys):
            return dot
    h = int(_hashlib.md5(c.encode()).hexdigest(), 16)
    return COLOR_PALETTE[h % len(COLOR_PALETTE)]

def color_badge(color):
    """'🔵 Dark Navy' — para colunas Cor nas tabelas."""
    if not color or str(color).strip() in ('', 'None'):
        return ''
    return f"{color_dot(color)} {color}"

def apply_color_badges(df, col='Cor'):
    """Aplica badges de cor a uma coluna de um DataFrame de display."""
    if col in df.columns:
        df[col] = df[col].apply(color_badge)
    return df

def add_total_row(df, exclude=()):
    """Acrescenta linha TOTAL com somatório das colunas numéricas (aplicar ANTES de safe_display_df)."""
    if df.empty:
        return df
    total = {}
    for i, c in enumerate(df.columns):
        if c in exclude:
            total[c] = ''
        elif pd.api.types.is_numeric_dtype(df[c]):
            total[c] = round(df[c].sum(), 2)
        elif i == 0:
            total[c] = '— TOTAL —'
        else:
            total[c] = ''
    return pd.concat([df, pd.DataFrame([total])], ignore_index=True)


# ===================== SEED DATA (CW29 2026, corrigido v3.3) =====================
FABRIC_REFS = [
    ('TCB258/EC1', 'Essential Exclusive', 'Riopele', 1000),
    ('TCD648/F1', 'Freely Exclusive', 'Riopele', 1000),
    ('TCD524/EC1', 'Essential Twill Almond', 'Riopele', 500),
    ('43793', 'Tech Wool', 'Paulo Oliveira', 300),
    ('GB14W', 'Carreman Ease', 'Carreman', 2000),
    ('GZIC GR4', 'Carreman Azic Dark Navy', 'Carreman', 400),
    ('GZIC 002', 'Carreman Azic Dark Beige', 'Carreman', 400),
    ('GZIC GR5', 'Carreman Azic Dark Grey', 'Carreman', 400),
    ('Guana', 'Carreman Guana', 'Carreman', 500),
    ('TCC130/RY1', 'Harrys Brown Herringbone', 'Riopele', 300),
    ('TCC132/RY1', 'Harrys Black', 'Riopele', 300),
    ('TCE278/F1', 'Freely Fancy Signature', 'Riopele', 500),
    ('TCD340/RY1', 'Serene Wool', 'Riopele', 300),
    ('TCD341/F1', 'Harrys Dark Navy Pinstripe', 'Riopele', 300),
    ('TCD342/RY1', 'Heritage Wool', 'Riopele', 300),
    ('TC9973', 'Merci Recycled', 'Riopele', 300),
    ('TCD573/EC1', 'Essential Twill', 'Riopele', 500),
    ('TCC482/RY1', 'Bird Tech Linen', 'Riopele', 300),
    ('TC6677', 'Slit', 'Riopele', 200),
    ('TCE244', 'Walking Summer', 'Riopele', 200),
    ('TCE604', 'SUT Domino Herringbone', 'Riopele', 200),
    ('Carreman-Garco', 'Carreman Garco', 'Carreman', 400),
    ('Carreman-Rhea', 'Carreman Rhea', 'Carreman', 200),
    ('Carreman-Acash', 'Carreman Acash', 'Carreman', 1000),
    ('Carreman-Azic', 'Carreman Azic', 'Carreman', 500),
    ('Carreman-Juana', 'Carreman Juana', 'Carreman', 500),
    ('Delegant', 'Delegant', 'Delegant', 200),
    ('ACASH KD', 'Carreman Acash', 'Carreman', 1000),
    ('TCC482/F1', 'Bird', 'Riopele', 300),
    ('TCD488/EC1', 'Essential Twill', 'Riopele', 200),
    ('TCD741/F1', 'Freely Cloudy Blue', 'Riopele', 300),
    ('TCE081/EC1', 'Essential Night Silver', 'Riopele', 100),
    ('TCE604/F1', 'SUT Domino Herringbone', 'Riopele', 200),
    ('4600 48389', 'Tech Wool Check', 'Paulo Oliveira', 200),
    ('A0 UNI-MH FW 25.26', 'Carreman Ease FW25.26', 'Carreman', 200),
    ('No. 1 UNI-MH FW 25.26', 'Carreman Ease FW25.26', 'Carreman', 200),
    ('No. 8 UNI-MH FW 25.26', 'Carreman Ease FW25.26', 'Carreman', 200),
    ('R1 UNI-MH FW 25.26', 'Carreman Ease FW25.26', 'Carreman', 200),
    ('T6 UNI-MH FW 25.26', 'Carreman Ease FW25.26', 'Carreman', 200),
    ('W08 0601 UNI-MH FW 25.26', 'Carreman Ease FW25.26', 'Carreman', 200),
]

INCOMING_FABRIC = [
    ('POAPS_PT000000169', 'Riopele', 'TCB258/EC1', 430.00, '2026-06-15', 'EXPECTED'),
    ('POAPS_PT000000175', 'Paulo Oliveira', '43793', 1500.00, '2026-07-18', 'EXPECTED'),
    ('POAPS_PT000000176', 'Riopele', 'TCD648/F1', 1699.00, '2026-07-16', 'EXPECTED'),
    ('POAPS_PT000000177', 'Riopele', 'TCD648/F1', 588.00, '2026-07-21', 'EXPECTED'),
    ('POAPS_PT000000178', 'Riopele', 'TCD648/F1', 397.00, '2026-07-21', 'EXPECTED'),
    ('POAPS_PT000000179', 'Riopele', 'TCD648/F1', 1124.00, '2026-07-21', 'EXPECTED'),
    ('POAPS_PT000000180', 'Riopele', 'TCD648/F1', 868.00, '2026-07-21', 'EXPECTED'),
    ('POAPS_PT000000181', 'Riopele', 'TCD648/F1', 600.00, '2026-07-21', 'EXPECTED'),
    ('POAPS_PT000000182', 'Carreman', 'GB14W', 8750.00, '2026-07-23', 'EXPECTED'),
    ('POAPS_PT000000183', 'Carreman', 'GB14W', 8250.00, '2026-07-23', 'EXPECTED'),
]

PRODUCTION = [
    ('POAPS2000004353', 'Essential Suit Pants Regular Dark Grey Melange', 'Costa Correia', 151, 'TCB258/EC1', 211.40, '2026-07-17', 'PENDING'),
    ('POAPS2000004352', 'Essential Suit Pants Regular Pine Green', 'Costa Correia', 151, 'TCB258/EC1', 211.40, '2026-07-17', 'PENDING'),
    ('POAPS2000004351', 'Essential Suit Pants Regular Midnight Blue', 'Costa Correia', 261, 'TCB258/EC1', 365.40, '2026-07-17', 'PENDING'),
    ('POAPS2000004350', 'Essential Suit Pants Slim Midnight Blue', 'Costa Correia', 326, 'TCB258/EC1', 456.40, '2026-07-17', 'PENDING'),
    ('POAPS2000004349', 'Essential Suit Pants Slim Almond', 'Costa Correia', 371, 'TCB258/EC1', 519.40, '2026-07-17', 'PENDING'),
    ('POAPS2000004348', 'Essential Suit Pants Regular Almond', 'Costa Correia', 601, 'TCB258/EC1', 841.40, '2026-07-17', 'PENDING'),
    ('POAPS2000004422', 'Tech Wool Blazer Sand', 'Tyrrell', 151, '43793', 211.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004421', 'Tech Wool Blazer Navy', 'Tyrrell', 265, '43793', 371.00, '2026-07-31', 'PENDING'),
    ('POAPS2000004409', 'Ease Pants Dark Grey Relaxed (Use all fabric)', 'Samidel', 282, 'GB14W', 394.80, '2026-07-31', 'PENDING'),
    ('POAPS2000004408', 'Ease Pants Dark Grey Regular (Use all fabric)', 'Samidel', 700, 'GB14W', 980.00, '2026-07-31', 'PENDING'),
    ('POAPS2000004407', 'Ease Pants Dark Grey Slim (Use all fabric)', 'Samidel', 492, 'GB14W', 688.80, '2026-07-31', 'PENDING'),
    ('POAPS2000004406', 'Ease Pants Black Relaxed (Use all fabric)', 'Samidel', 858, 'GB14W', 1201.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004405', 'Ease Pants Black Regular (Use all fabric)', 'Samidel', 1002, 'GB14W', 1402.80, '2026-07-31', 'PENDING'),
    ('POAPS2000004404', 'Ease Pants Black Slim (Use all fabric)', 'Samidel', 836, 'GB14W', 1170.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004403', 'Ease Pants Blue Nights Relaxed (Use all fabric)', 'Samidel', 753, 'GB14W', 1054.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004402', 'Ease Pants Blue Nights Regular (Use all fabric)', 'Samidel', 723, 'GB14W', 1012.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004401', 'Ease Pants Blue Nights Slim (Use all fabric)', 'Samidel', 251, 'GB14W', 351.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004400', 'Ease Pants Sahara Relaxed (Use all fabric)', 'Samidel', 353, 'GB14W', 494.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004399', 'Ease Pants Sahara Regular (Use all fabric)', 'Samidel', 351, 'GB14W', 491.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004398', 'Ease Pants Sahara Slim (Use all fabric)', 'Samidel', 572, 'GB14W', 800.80, '2026-07-31', 'PENDING'),
    ('POAPS2000004397', 'Ease Pants Mocha Relaxed (Use all fabric)', 'Samidel', 288, 'GB14W', 403.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004396', 'Ease Pants Mocha Regular (Use all fabric)', 'Samidel', 361, 'GB14W', 505.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004395', 'Ease Pants Mocha Slim (Use all fabric)', 'Samidel', 598, 'GB14W', 837.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004394', 'Ease Pants Northern Pine Relaxed (Use all fabric)', 'Samidel', 158, 'GB14W', 221.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004393', 'Ease Pants Northern Pine Regular (Use all fabric)', 'Samidel', 303, 'GB14W', 424.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004392', 'Ease Pants Northern Pine Slim (Use all fabric)', 'Samidel', 334, 'GB14W', 467.60, '2026-07-31', 'PENDING'),
    ('POAPS2000004387', 'Women Ease Pants Straight Black (Use all fabric)', 'Costa Correia', 535, 'GB14W', 749.00, '2026-07-31', 'PENDING'),
    ('POAPS2000004386', 'Women Ease Pants Tapered Black (Use all fabric)', 'Costa Correia', 233, 'GB14W', 326.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004385', 'Women Ease Pants Straight Blue Nights (Use all fabric)', 'Costa Correia', 294, 'GB14W', 411.60, '2026-07-31', 'PENDING'),
    ('POAPS2000004384', 'Women Ease Pants Tapered Blue Nights (Use all fabric)', 'Costa Correia', 179, 'GB14W', 250.60, '2026-07-31', 'PENDING'),
    ('POAPS2000004383', 'Women Ease Pants Wide Mocha Melange (Use all fabric)', 'Costa Correia', 296, 'GB14W', 414.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004382', 'Women Ease Pants Straight Mocha Melange (Use all fabric)', 'Costa Correia', 539, 'GB14W', 754.60, '2026-07-31', 'PENDING'),
    ('POAPS2000004381', 'Women Ease Pants Tapered Mocha Melange (Use all fabric)', 'Costa Correia', 196, 'GB14W', 274.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004380', 'Women Ease Pants Wide Evergreen (Use all fabric)', 'Costa Correia', 268, 'GB14W', 375.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004379', 'Women Ease Pants Straight Evergreen (Use all fabric)', 'Costa Correia', 206, 'GB14W', 288.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004378', 'Women Ease Pants Straight Steel Melange (Use all fabric)', 'Costa Correia', 21, 'GB14W', 29.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004377', 'Women Ease Pants Wide Vanilla Melange (Use all fabric)', 'Costa Correia', 86, 'GB14W', 120.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004376', 'Women Ease Pants Straight Vanilla Melange (Use all fabric)', 'Costa Correia', 61, 'GB14W', 85.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004299', 'Women Serene Blazer Walnut Herringbone (Use all fabric)', 'Tyrrell', 168, 'TCD340/RY1', 235.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004273', 'Timeless Wool Blazer Dark Brown Check', 'Tyrrell', 209, '4600 48389', 292.60, '2026-07-31', 'PENDING'),
    ('POAPS2000004253', 'Motion Suit Pants Cognac', 'Samidel', 1001, '43793', 1401.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004252', 'Motion Suit Pants Pepper Grey', 'Samidel', 600, '43793', 840.00, '2026-07-31', 'PENDING'),
    ('POAPS2000004251', 'Motion Suit Pants Midnight Blue', 'Samidel', 1074, '43793', 1503.60, '2026-07-31', 'PENDING'),
    ('POAPS2000004234', 'Women Nara Pants Straight Grey Flint (Use all fabric)', 'Costa Correia', 655, 'Guana', 917.00, '2026-07-31', 'PENDING'),
    ('POAPS2000004233', 'Women Nara Pants Straight Cool Brown (Use all fabric)', 'Costa Correia', 858, 'Guana', 1201.20, '2026-07-31', 'PENDING'),
    ('POAPS2000004232', 'Women Ashryn Blazer Domino Herringbone (Use all fabric)', 'Acorfato', 90, 'Carreman-Azic', 126.00, '2026-07-31', 'PENDING'),
    ('POAPS2000004227', 'Women Ease Short Skirt Mocha Melange', 'Samidel', 94, 'GB14W', 131.60, '2026-07-31', 'PENDING'),
    ('POAPS2000004226', 'Women Ease Short Skirt Blue Nights', 'Samidel', 121, 'GB14W', 169.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004225', 'Women Ease Short Skirt Black', 'Samidel', 314, 'GB14W', 439.60, '2026-07-31', 'PENDING'),
    ('POAPS2000004205', 'Corduroy Pants Dark Grey', 'Samidel', 657, 'GB14W', 919.80, '2026-07-31', 'PENDING'),
    ('POAPS2000004204', 'Corduroy Pants Dark Navy', 'Samidel', 525, 'GB14W', 735.00, '2026-07-31', 'PENDING'),
    ('POAPS2000004203', 'Corduroy Pants Deep Espresso', 'Samidel', 899, 'GB14W', 1258.60, '2026-07-31', 'PENDING'),
    ('POAPS2000004202', 'Corduroy Pants Khaki', 'Samidel', 820, 'GB14W', 1148.00, '2026-07-31', 'PENDING'),
    ('POAPS2000004201', 'Corduroy Pants Relaxed Fit Black', 'Samidel', 416, 'GB14W', 582.40, '2026-07-31', 'PENDING'),
    ('POAPS2000004200', 'Corduroy Pants Relaxed Fit Deep Espresso', 'Samidel', 472, 'GB14W', 660.80, '2026-07-31', 'PENDING'),
    ('POAPS2000004300', 'Women Serene Short Jacket Berry Pinstripe (Use all fabric)', 'Samidel', 51, 'TCD340/RY1', 71.40, '2026-08-07', 'PENDING'),
    ('POAPS2000004298', 'Women Nara Fitted Blazer Black Check (Use all fabric)', 'Acorfato', 126, 'Guana', 176.40, '2026-08-07', 'PENDING'),
    ('POAPS2000004297', 'Women Serene Pants Wide Black (Use all fabric)', 'Costa Correia', 933, 'TCD340/RY1', 1306.20, '2026-08-07', 'PENDING'),
    ('POAPS2000004296', 'Women Serene Pants Wide Berry Pinstripe (Use all fabric)', 'Costa Correia', 321, 'TCD340/RY1', 449.40, '2026-08-07', 'PENDING'),
    ('POAPS2000004295', 'Women Serene Pants Wide Walnut Herringbone (Use all fabric)', 'Costa Correia', 1121, 'TCD340/RY1', 1569.40, '2026-08-07', 'PENDING'),
]

CONSUMPTION_MAP = [
    ('Essential Blazer Men Checked', 'TCB258/EC1', 2.17),
    ('Essential Blazer Men Plain', 'TCB258/EC1', 1.8),
    ('Essential Blazer Men Striped', 'TCB258/EC1', 1.97),
    ('Essential Jacket  Men Plain', 'TCB258/EC1', 1.62),
    ('Essential Overshirt  Men Checked', 'TCB258/EC1', 1.96),
    ('Essential Overshirt  Men Plain', 'TCB258/EC1', 1.69),
    ('Essential Pants Men Plain', 'TCB258/EC1', 1.38),
    ('Essential Relaxed Fit Pants Men Plain', 'TCB258/EC1', 1.54),
    ('Essential Shorts Men Plain', 'TCB258/EC1', 1.0),
    ('Essential Shorts Men Striped', 'TCB258/EC1', 1.14),
    ('Essential Suit Pants Men Checked', 'TCB258/EC1', 1.76),
    ('Essential Suit Pants Men Plain', 'TCB258/EC1', 1.38),
    ('Essential Suit Pants Men Striped', 'TCB258/EC1', 1.41),
    ('Essential Suit Pants Relaxed Men Plain', 'TCB258/EC1', 1.59),
    ('Essential Vest Men Checked', 'TCB258/EC1', 1.05),
    ('Essential Vest Men Plain', 'TCB258/EC1', 0.9),
    ('Essential Vest Men Striped', 'TCB258/EC1', 1.0),
    ('Gen. 2.0 Pants Men Plain', 'TCD648/F1', 1.35),
    ('Gen. 2.0 Shorts Men Plain', 'TCD648/F1', 0.87),
    ('Heavy Edition Overshirt Men Plain', 'TC9973', 1.55),
    ('Heavy Edition Pants Men Plain', 'TC9973', 1.37),
    ('Heritage Pants Relaxed Fit Men Plain', 'TCD342/RY1', 1.49),
    ('Linen Wide Fit Pants Men Plain', 'TCD573/EC1', 1.47),
    ('Siena Jacket Men Plain', 'Carreman-Garco', 2.05),
    ('Siena Pants Men Plain', 'Carreman-Garco', 1.31),
    ('Siena Shirt Men Plain', 'Carreman-Garco', 1.4),
    ('Siena Shorts Men Plain', 'Carreman-Garco', 0.79),
    ('Tech Linen Bowling Short Sleeve Shirt Men Plain', 'TCC482/RY1', 1.31),
    ('Tech Linen Bowling Short Sleeve Shirt Men Striped', 'TCC482/RY1', 1.37),
    ('Tech Linen Casual Shirt  Men Plain', 'TCC482/RY1', 1.48),
    ('Tech Linen Casual Shirt  Men Striped', 'TCC482/RY1', 1.68),
    ('Tech Linen Elastic Pants Men Plain', 'TCC482/RY1', 1.31),
    ('Tech Linen Elastic Shorts Men Plain', 'TCC482/RY1', 0.89),
    ('Tech Linen Elastic Shorts Men Striped', 'TCC482/RY1', 1.1),
    ('Tech Linen Suit Pants Relaxed Fit Men Plain', 'TCC482/RY1', 1.42),
    ('Tech Wool Blazer Men Plain', '43793', 1.75),
    ('Tech Wool Double Breasted Blazer Men Plain', '43793', 1.71),
    ('Tech Wool Suit Pants Men Plain', '43793', 1.26),
    ('Tech Wool Suit Pants Relaxed Fit Men Plain', '43793', 1.31),
]

# Rolos XBS — v3.3: linhas TOTAL / TOTAL GERAL do Excel removidas (eram subtotais, duplicavam stock)
FABRIC_ROLLS = [
    ('R-TCB258_EC1-001', 'TCB258/EC1', 28.71, '151', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-002', 'TCB258/EC1', 26.11, '151', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-003', 'TCB258/EC1', 33.18, '161', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-004', 'TCB258/EC1', 52.33, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-005', 'TCB258/EC1', 54.71, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-006', 'TCB258/EC1', 46.46, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-007', 'TCB258/EC1', 47.06, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-008', 'TCB258/EC1', 47.08, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-009', 'TCB258/EC1', 51.79, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-010', 'TCB258/EC1', 52.8, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-011', 'TCB258/EC1', 52.25, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-012', 'TCB258/EC1', 52.82, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-013', 'TCB258/EC1', 41.01, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-014', 'TCB258/EC1', 59.78, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-015', 'TCB258/EC1', 64.93, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-016', 'TCB258/EC1', 42.9, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-017', 'TCB258/EC1', 42.69, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-018', 'TCB258/EC1', 54.14, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-019', 'TCB258/EC1', 51.11, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-020', 'TCB258/EC1', 62.18, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-021', 'TCB258/EC1', 33.66, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-022', 'TCB258/EC1', 42.92, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-023', 'TCB258/EC1', 54.38, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-024', 'TCB258/EC1', 54.72, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-025', 'TCB258/EC1', 54.81, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-026', 'TCB258/EC1', 52.63, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-027', 'TCB258/EC1', 45.85, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-028', 'TCB258/EC1', 48.72, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-029', 'TCB258/EC1', 46.38, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-030', 'TCB258/EC1', 54.03, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-031', 'TCB258/EC1', 54.04, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-032', 'TCB258/EC1', 54.34, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-033', 'TCB258/EC1', 54.47, '162', 'Black 017', 'XBS', None),
    ('R-TCB258_EC1-034', 'TCB258/EC1', 26.65, '212', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-035', 'TCB258/EC1', 53.73, '213', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-036', 'TCB258/EC1', 29.77, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-037', 'TCB258/EC1', 40.04, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-038', 'TCB258/EC1', 44.7, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-039', 'TCB258/EC1', 39.29, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-040', 'TCB258/EC1', 39.76, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-041', 'TCB258/EC1', 51.07, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-042', 'TCB258/EC1', 42.69, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-043', 'TCB258/EC1', 50.22, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-044', 'TCB258/EC1', 51.9, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-045', 'TCB258/EC1', 52.68, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-046', 'TCB258/EC1', 42.31, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-047', 'TCB258/EC1', 42.23, '214', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-048', 'TCB258/EC1', 35.72, '212', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-049', 'TCB258/EC1', 19.26, '212', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-050', 'TCB258/EC1', 49.58, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-051', 'TCB258/EC1', 51.62, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-052', 'TCB258/EC1', 52.05, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-053', 'TCB258/EC1', 15.96, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-054', 'TCB258/EC1', 45.25, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-055', 'TCB258/EC1', 45.61, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-056', 'TCB258/EC1', 50.0, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-057', 'TCB258/EC1', 49.9, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-058', 'TCB258/EC1', 40.97, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-059', 'TCB258/EC1', 41.08, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-060', 'TCB258/EC1', 46.84, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-061', 'TCB258/EC1', 46.56, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-062', 'TCB258/EC1', 50.26, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-063', 'TCB258/EC1', 50.9, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-064', 'TCB258/EC1', 22.6, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-065', 'TCB258/EC1', 60.11, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-066', 'TCB258/EC1', 24.48, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-067', 'TCB258/EC1', 38.11, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-068', 'TCB258/EC1', 63.34, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-069', 'TCB258/EC1', 51.77, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-070', 'TCB258/EC1', 48.0, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-071', 'TCB258/EC1', 48.56, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-072', 'TCB258/EC1', 46.52, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-073', 'TCB258/EC1', 46.45, '215', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-074', 'TCB258/EC1', 40.65, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-075', 'TCB258/EC1', 44.78, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-076', 'TCB258/EC1', 44.75, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-077', 'TCB258/EC1', 44.22, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-078', 'TCB258/EC1', 45.37, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-079', 'TCB258/EC1', 45.65, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-080', 'TCB258/EC1', 45.65, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-081', 'TCB258/EC1', 64.04, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-082', 'TCB258/EC1', 58.26, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-083', 'TCB258/EC1', 59.28, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-084', 'TCB258/EC1', 59.51, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-085', 'TCB258/EC1', 59.53, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-086', 'TCB258/EC1', 42.52, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-087', 'TCB258/EC1', 55.39, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-088', 'TCB258/EC1', 56.31, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-089', 'TCB258/EC1', 55.51, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-090', 'TCB258/EC1', 42.1, '216', 'Midnight Blue 0917', 'XBS', None),
    ('R-TCB258_EC1-091', 'TCB258/EC1', 44.55, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-092', 'TCB258/EC1', 41.53, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-093', 'TCB258/EC1', 41.41, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-094', 'TCB258/EC1', 38.48, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-095', 'TCB258/EC1', 36.54, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-096', 'TCB258/EC1', 63.08, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-097', 'TCB258/EC1', 53.69, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-098', 'TCB258/EC1', 56.45, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-099', 'TCB258/EC1', 62.13, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-100', 'TCB258/EC1', 72.5, '18', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-101', 'TCB258/EC1', 44.99, '19', 'Dark Grey 0318', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-102', 'TCB258/EC1', 62.55, '131', 'Beige 0862', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-103', 'TCB258/EC1', 63.99, '131', 'Beige 0862', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-104', 'TCB258/EC1', 54.14, '131', 'Beige 0862', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCB258_EC1-105', 'TCB258/EC1', 54.12, '131', 'Beige 0862', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-001', 'TCD648/F1', 32.03, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-002', 'TCD648/F1', 32.6, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-003', 'TCD648/F1', 44.43, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-004', 'TCD648/F1', 40.6, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-005', 'TCD648/F1', 47.78, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-006', 'TCD648/F1', 47.78, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-007', 'TCD648/F1', 48.16, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-008', 'TCD648/F1', 46.76, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-009', 'TCD648/F1', 43.45, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-010', 'TCD648/F1', 25.51, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-011', 'TCD648/F1', 52.58, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-012', 'TCD648/F1', 39.72, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-013', 'TCD648/F1', 50.08, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-014', 'TCD648/F1', 21.88, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-015', 'TCD648/F1', 36.09, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-016', 'TCD648/F1', 36.8, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-017', 'TCD648/F1', 36.82, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-018', 'TCD648/F1', 33.98, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-019', 'TCD648/F1', 35.85, '78', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-020', 'TCD648/F1', 43.86, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-021', 'TCD648/F1', 43.52, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-022', 'TCD648/F1', 47.42, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-023', 'TCD648/F1', 46.32, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-024', 'TCD648/F1', 45.07, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-025', 'TCD648/F1', 42.61, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-026', 'TCD648/F1', 38.8, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-027', 'TCD648/F1', 38.34, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-028', 'TCD648/F1', 47.6, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-029', 'TCD648/F1', 33.81, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-030', 'TCD648/F1', 34.06, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-031', 'TCD648/F1', 31.74, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-032', 'TCD648/F1', 32.61, '79', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-033', 'TCD648/F1', 44.83, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-034', 'TCD648/F1', 45.03, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-035', 'TCD648/F1', 19.39, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-036', 'TCD648/F1', 41.24, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-037', 'TCD648/F1', 41.02, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-038', 'TCD648/F1', 35.56, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-039', 'TCD648/F1', 35.88, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-040', 'TCD648/F1', 33.28, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-041', 'TCD648/F1', 41.94, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-042', 'TCD648/F1', 46.04, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-043', 'TCD648/F1', 47.31, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-044', 'TCD648/F1', 44.19, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-045', 'TCD648/F1', 42.27, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-046', 'TCD648/F1', 56.77, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-047', 'TCD648/F1', 40.49, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-048', 'TCD648/F1', 40.63, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-049', 'TCD648/F1', 40.64, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-050', 'TCD648/F1', 61.55, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-051', 'TCD648/F1', 55.99, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-052', 'TCD648/F1', 56.01, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-053', 'TCD648/F1', 39.18, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-054', 'TCD648/F1', 39.03, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-055', 'TCD648/F1', 38.38, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-056', 'TCD648/F1', 52.41, '80', 'Navy 004', 'XBS', None),
    ('R-TCD648_F1-057', 'TCD648/F1', 56.28, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-058', 'TCD648/F1', 44.15, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-059', 'TCD648/F1', 45.17, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-060', 'TCD648/F1', 56.16, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-061', 'TCD648/F1', 37.5, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-062', 'TCD648/F1', 56.29, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-063', 'TCD648/F1', 47.23, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-064', 'TCD648/F1', 33.88, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-065', 'TCD648/F1', 44.32, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-066', 'TCD648/F1', 31.99, '16', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-067', 'TCD648/F1', 36.49, '14', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-068', 'TCD648/F1', 58.26, '14', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-069', 'TCD648/F1', 25.67, '14', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-070', 'TCD648/F1', 35.32, '14', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-071', 'TCD648/F1', 59.04, '14', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-072', 'TCD648/F1', 35.0, '14', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-073', 'TCD648/F1', 40.8, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-074', 'TCD648/F1', 49.39, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-075', 'TCD648/F1', 43.46, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-076', 'TCD648/F1', 40.11, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-077', 'TCD648/F1', 53.19, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-078', 'TCD648/F1', 43.48, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-079', 'TCD648/F1', 37.96, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-080', 'TCD648/F1', 40.84, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-081', 'TCD648/F1', 42.58, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-082', 'TCD648/F1', 37.98, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-083', 'TCD648/F1', 43.74, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-084', 'TCD648/F1', 43.74, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-085', 'TCD648/F1', 43.93, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-086', 'TCD648/F1', 46.16, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-087', 'TCD648/F1', 55.97, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-088', 'TCD648/F1', 46.12, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-089', 'TCD648/F1', 37.59, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-090', 'TCD648/F1', 46.16, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-091', 'TCD648/F1', 31.13, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-092', 'TCD648/F1', 49.12, '15', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-093', 'TCD648/F1', 34.62, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-094', 'TCD648/F1', 41.64, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-095', 'TCD648/F1', 39.68, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-096', 'TCD648/F1', 48.22, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-097', 'TCD648/F1', 44.34, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-098', 'TCD648/F1', 34.64, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-099', 'TCD648/F1', 39.63, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-100', 'TCD648/F1', 43.55, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-101', 'TCD648/F1', 31.24, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-102', 'TCD648/F1', 45.7, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-103', 'TCD648/F1', 52.75, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-104', 'TCD648/F1', 46.53, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-105', 'TCD648/F1', 60.3, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-106', 'TCD648/F1', 41.64, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-107', 'TCD648/F1', 30.84, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-108', 'TCD648/F1', 43.21, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-109', 'TCD648/F1', 49.5, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-110', 'TCD648/F1', 43.91, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-111', 'TCD648/F1', 46.8, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-112', 'TCD648/F1', 46.8, '17', 'Dark Grey 018', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-113', 'TCD648/F1', 7.49, '17', 'Dark Grey 018', 'XBS', 'Ajuste audit CW29 (-32.01m)'),
    ('R-TCD648_F1-114', 'TCD648/F1', 43.02, '66', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-115', 'TCD648/F1', 29.22, '67', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-116', 'TCD648/F1', 50.63, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-117', 'TCD648/F1', 46.31, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-118', 'TCD648/F1', 46.44, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-119', 'TCD648/F1', 42.78, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-120', 'TCD648/F1', 42.95, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-121', 'TCD648/F1', 50.44, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-122', 'TCD648/F1', 42.67, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-123', 'TCD648/F1', 45.98, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-124', 'TCD648/F1', 50.97, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-125', 'TCD648/F1', 55.18, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-126', 'TCD648/F1', 40.89, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-127', 'TCD648/F1', 35.13, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-128', 'TCD648/F1', 19.25, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-129', 'TCD648/F1', 56.08, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-130', 'TCD648/F1', 35.61, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-131', 'TCD648/F1', 55.25, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-132', 'TCD648/F1', 47.77, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-133', 'TCD648/F1', 47.15, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-134', 'TCD648/F1', 38.25, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-135', 'TCD648/F1', 55.25, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-136', 'TCD648/F1', 42.22, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-137', 'TCD648/F1', 36.49, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-138', 'TCD648/F1', 53.72, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-139', 'TCD648/F1', 16.3, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-140', 'TCD648/F1', 60.74, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-141', 'TCD648/F1', 45.0, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-142', 'TCD648/F1', 50.0, '68', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-143', 'TCD648/F1', 32.42, '70', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-144', 'TCD648/F1', 18.96, '70', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-145', 'TCD648/F1', 33.1, '70', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-146', 'TCD648/F1', 48.11, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-147', 'TCD648/F1', 47.73, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-148', 'TCD648/F1', 39.52, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-149', 'TCD648/F1', 45.5, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-150', 'TCD648/F1', 19.99, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-151', 'TCD648/F1', 40.02, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-152', 'TCD648/F1', 52.92, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-153', 'TCD648/F1', 44.38, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-154', 'TCD648/F1', 52.92, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-155', 'TCD648/F1', 44.15, '71', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-156', 'TCD648/F1', 51.34, '72', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-157', 'TCD648/F1', 39.18, '72', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-158', 'TCD648/F1', 19.54, '72', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-159', 'TCD648/F1', 51.64, '72', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-160', 'TCD648/F1', 49.78, '72', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-161', 'TCD648/F1', 23.3, '74', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-162', 'TCD648/F1', 25.21, '74', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-163', 'TCD648/F1', 51.24, '74', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-164', 'TCD648/F1', 23.87, '74', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-165', 'TCD648/F1', 47.94, '74', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-166', 'TCD648/F1', 27.0, '74', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-167', 'TCD648/F1', 34.72, '75', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-168', 'TCD648/F1', 34.63, '75', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-169', 'TCD648/F1', 15.0, '75', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-170', 'TCD648/F1', 15.0, '70', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-171', 'TCD648/F1', 51.64, '75', 'Black 001', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-172', 'TCD648/F1', 39.02, '30', 'Green 003', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-173', 'TCD648/F1', 58.38, '30', 'Green 003', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-174', 'TCD648/F1', 39.15, '30', 'Green 003', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-175', 'TCD648/F1', 48.67, '30', 'Green 003', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-176', 'TCD648/F1', 42.88, '30', 'Green 003', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-177', 'TCD648/F1', 57.2, '30', 'Green 003', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-178', 'TCD648/F1', 48.81, '30', 'Green 003', 'XBS', 'Ajuste audit CW29 (-4.53m)'),
    ('R-TCD648_F1-179', 'TCD648/F1', 5.0, '41', 'Sand 002', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-180', 'TCD648/F1', 22.66, '41', 'Sand 002', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-181', 'TCD648/F1', 38.02, '40', 'Sand 002', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-182', 'TCD648/F1', 57.62, '40', 'Sand 002', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-183', 'TCD648/F1', 36.93, '40', 'Sand 002', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-184', 'TCD648/F1', 26.55, '40', 'Sand 002', 'XBS', 'Devolvido pela Samidel'),
    ('R-TCD648_F1-185', 'TCD648/F1', 45.24, '40', 'Sand 002', 'XBS', 'Devolvido pela Samidel'),
    ('R-43793-001', '43793', 65.3, '260578', 'Sand 2952', 'XBS', None),
    ('R-43793-002', '43793', 66.4, '260578', 'Sand 2952', 'XBS', None),
    ('R-43793-003', '43793', 63.1, '260578', 'Sand 2952', 'XBS', None),
    ('R-43793-004', '43793', 57.6, '260578', 'Sand 2952', 'XBS', None),
    ('R-43793-005', '43793', 66.0, '260578', 'Sand 2952', 'XBS', None),
    ('R-43793-006', '43793', 64.9, '260743.1', 'Black 344', 'XBS', None),
    ('R-43793-007', '43793', 67.2, '260743.1', 'Black 344', 'XBS', None),
    ('R-43793-008', '43793', 66.5, '260743.1', 'Black 344', 'XBS', None),
    ('R-43793-009', '43793', 72.0, '260743.1', 'Black 344', 'XBS', None),
    ('R-43793-010', '43793', 60.4, '260743.1', 'Black 344', 'XBS', None),
    ('R-43793-011', '43793', 66.3, '260743.1', 'Black 344', 'XBS', None),
    ('R-43793-012', '43793', 66.0, '260743.1', 'Black 344', 'XBS', None),
    ('R-43793-013', '43793', 66.9, '260743.1', 'Black 344', 'XBS', None),
    ('R-43793-014', '43793', 68.0, '260743.1', 'Black 344', 'XBS', None),
    ('R-43793-015', '43793', 64.7, '260743.1', 'Black 344', 'XBS', None),
    ('R-TCD648_F1-186', 'TCD648/F1', 2846.26, 'AUDIT-CW29', 'Black 001', 'XBS', 'Complemento audit CW29 — sem packing individual'),
    ('R-GZIC_GR4-001', 'GZIC GR4', 421.7, 'AUDIT-CW29', 'Dark Navy B5T01', 'XBS', 'Lote agregado audit CW29 — sem packing individual'),
    ('R-GZIC_GR4-002', 'GZIC GR4', 545.7, 'AUDIT-CW29', 'Dark Brown C7W01', 'XBS', 'Lote agregado audit CW29 — sem packing individual'),
    ('R-GZIC_002-001', 'GZIC 002', 547.9, 'AUDIT-CW29', 'Dark Beige D8', 'XBS', 'Lote agregado audit CW29 — sem packing individual'),
]

# Stock em confeccionadores — v3.6: Fabric Audit CW29 completo (token, ref, metres, color, conf, nota)
IN_PROCESS_STOCK = [
    ('P-Acorfato-Guana-001', 'Guana', 235.0, 'S16 Black Check B102', 'Acorfato', 'Stock conf. (audit CW29)'),
    ('P-Acorfato-Guana-002', 'Guana', 341.5, 'S32 Pepper Grey B5', 'Acorfato', 'Stock conf. (audit CW29)'),
    ('P-Acorfato-Guana-003', 'Guana', 736.7, 'TW6 Midnight Blue 10', 'Acorfato', 'Stock conf. (audit CW29)'),
    ('P-Acorfato-Guana-004', 'Guana', 742.3, 'UN2 Cognac 12', 'Acorfato', 'Stock conf. (audit CW29)'),
    ('P-Acorfato-TCB258_EC1-001', 'TCB258/EC1', 304.49, 'Dark Grey Melange 0318', 'Acorfato', 'Stock conf. (audit CW29)'),
    ('P-Acorfato-TCB258_EC1-002', 'TCB258/EC1', 458.47, 'Medium Beige Melange 1049', 'Acorfato', 'Stock conf. (audit CW29)'),
    ('P-Acorfato-TCB258_EC1-003', 'TCB258/EC1', 502.32, 'Pine Green 1028', 'Acorfato', 'Stock conf. (audit CW29)'),
    ('P-Acorfato-TCE081_EC1-001', 'TCE081/EC1', 5.26, 'Night Silver Pinstripe 001', 'Acorfato', 'Stock conf. (audit CW29)'),
    ('P-Acorfato-TCE604_F1-001', 'TCE604/F1', 177.7, 'Domino Herringbone 001', 'Acorfato', 'Stock conf. (audit CW29)'),
    ('P-Antonio_Carla-43793-001', '43793', 10.0, 'Cocoa Brown 954', 'António & Carla', 'Stock conf. (audit CW29)'),
    ('P-Antonio_Carla-43793-002', '43793', 37.0, 'Navy 7143', 'António & Carla', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-A0_UNI-MH_FW_25.26-001', 'A0 UNI-MH FW 25.26', 201.5, 'Dark Chestnut Melange', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-ACASH_KD-001', 'ACASH KD', 3257.9, 'Black 09', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-ACASH_KD-002', 'ACASH KD', 1277.8, 'Blue Nights 99543', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-ACASH_KD-003', 'ACASH KD', 1049.5, 'Dark Grey Melange 75882', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-ACASH_KD-004', 'ACASH KD', 997.7, 'Dusty Olive 47654', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-ACASH_KD-005', 'ACASH KD', 2456.4, 'Mocha 58640', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-GB14W-001', 'GB14W', 725.4, 'UNI Evergreen A1', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-GB14W-002', 'GB14W', 1134.8, 'UNI 1 Black', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-GB14W-003', 'GB14W', 673.0, 'UNI 10 Blue Nights', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-GB14W-004', 'GB14W', 30.0, 'UNI 73 Steel Melange', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-GB14W-005', 'GB14W', 212.0, 'UNI 91 Vanilla Melange', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-GB14W-006', 'GB14W', 1584.6, 'UNI 93 Mocha Melange', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-Guana-001', 'Guana', 975.5, '089 Grey Flint B15', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-Guana-002', 'Guana', 822.3, 'S16 Black Check B102', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-Guana-003', 'Guana', 1387.1, 'S32 Cool Brown C2', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-No._1_UNI-MH_FW_25.26-001', 'No. 1 UNI-MH FW 25.26', 629.12, 'Black', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-No._8_UNI-MH_FW_25.26-001', 'No. 8 UNI-MH FW 25.26', 214.9, 'Cloud Grey', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-R1_UNI-MH_FW_25.26-001', 'R1 UNI-MH FW 25.26', 180.0, 'Navy', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-T6_UNI-MH_FW_25.26-001', 'T6 UNI-MH FW 25.26', 194.0, 'Dark Green', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCB258_EC1-001', 'TCB258/EC1', 973.64, 'Black 017', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCB258_EC1-002', 'TCB258/EC1', 229.79, 'Dark Grey Melange 0318', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCB258_EC1-003', 'TCB258/EC1', 127.52, 'Medium Beige Melange 1049', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCB258_EC1-004', 'TCB258/EC1', 83.63, 'Midnight Blue 0917', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCB258_EC1-005', 'TCB258/EC1', 827.0, 'Midnight Blue 0917', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCB258_EC1-006', 'TCB258/EC1', 208.97, 'Pine Green 1028', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCB258_EC1-007', 'TCB258/EC1', 14.0, 'Sand 0909', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCC130_RY1-001', 'TCC130/RY1', 1923.97, 'Brown Herringbone 002', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCC132_RY1-001', 'TCC132/RY1', 1669.61, 'Black 003', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCD340_RY1-001', 'TCD340/RY1', 580.63, 'Berry Pinstripe 007', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCD524_EC1-001', 'TCD524/EC1', 560.66, 'Almond 001', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCD524_EC1-002', 'TCD524/EC1', 1245.0, 'Almond 001', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCD648_F1-001', 'TCD648/F1', 3287.75, 'Black 001', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCD648_F1-002', 'TCD648/F1', 60.0, 'Dark Grey 018', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCD648_F1-003', 'TCD648/F1', 1560.64, 'Green 003', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCD648_F1-004', 'TCD648/F1', 3506.65, 'Navy 004', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCD648_F1-005', 'TCD648/F1', 406.16, 'Sand 002', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCD741_F1-001', 'TCD741/F1', 1766.2, 'Cloudy Blue 001', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCE278_F1-001', 'TCE278/F1', 5755.33, 'Signature Dark Brown 006', 'Fabrijeans / Costa C', 'Em processo (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCE278_F1-002', 'TCE278/F1', 2673.18, 'Signature Green 002', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCE278_F1-003', 'TCE278/F1', 271.88, 'Signature Mid Blue 007', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCE278_F1-004', 'TCE278/F1', 290.48, 'Signature Navy 003', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCE278_F1-005', 'TCE278/F1', 2913.84, 'Signature Sand 001', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-TCE604_F1-001', 'TCE604/F1', 640.46, 'Domino Herringbone 001', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Fabrijeans_CostaC-W08_0601_UNI-MH_FW_25.26-001', 'W08 0601 UNI-MH FW 25.26', 351.4, 'Charcoal Melange', 'Fabrijeans / Costa C', 'Stock conf. (audit CW29)'),
    ('P-Samidel-43793-001', '43793', 690.9, 'Navy 7143', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-GB14W-001', 'GB14W', 1068.2, 'MH Northern Pine A101', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-GB14W-002', 'GB14W', 2015.1, 'MH 01U5 Dark Grey', 'Samidel', 'Em processo (audit CW29)'),
    ('P-Samidel-GB14W-003', 'GB14W', 1772.15, 'MH W9U1 Sahara', 'Samidel', 'Em processo (audit CW29)'),
    ('P-Samidel-GB14W-004', 'GB14W', 116.4, 'UNI 1 Black', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-GB14W-005', 'GB14W', 3922.0, 'UNI 1 Black', 'Samidel', 'Em processo (audit CW29)'),
    ('P-Samidel-GB14W-006', 'GB14W', 80.2, 'UNI 10 Blue Nights', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-GB14W-007', 'GB14W', 2439.6, 'UNI 10 Blue Nights', 'Samidel', 'Em processo (audit CW29)'),
    ('P-Samidel-GB14W-008', 'GB14W', 67.3, 'UNI 93 Mocha Melange', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-GB14W-009', 'GB14W', 1732.2, 'UNI A0 Mocha', 'Samidel', 'Em processo (audit CW29)'),
    ('P-Samidel-GZIC_002-001', 'GZIC 002', 1204.4, 'Dark Beige D8', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-GZIC_GR4-001', 'GZIC GR4', 1585.7, 'Dark Brown C7W01', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-GZIC_GR4-002', 'GZIC GR4', 1672.3, 'Dark Navy B5T01', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-GZIC_GR5-001', 'GZIC GR5', 1103.2, 'Dark Grey B2S01', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-Guana-001', 'Guana', 796.7, 'S32 Pepper Grey B5', 'Samidel', 'Em processo (audit CW29)'),
    ('P-Samidel-Guana-002', 'Guana', 1465.9, 'TW6 Midnight Blue 10', 'Samidel', 'Em processo (audit CW29)'),
    ('P-Samidel-Guana-003', 'Guana', 1458.5, 'UN2 Cognac 12', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-TCB258_EC1-001', 'TCB258/EC1', 1609.07, 'Black 017', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-TCB258_EC1-002', 'TCB258/EC1', 128.09, 'Medium Beige Melange 1049', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-TCB258_EC1-003', 'TCB258/EC1', 575.86, 'Midnight Blue 0917', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-TCB258_EC1-004', 'TCB258/EC1', 2156.3, 'Navy 0929', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-TCC482_F1-001', 'TCC482/F1', 388.39, 'Ashes 002', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-TCD340_RY1-001', 'TCD340/RY1', 60.99, 'Berry Pinstripe 007', 'Samidel', 'Em processo (audit CW29)'),
    ('P-Samidel-TCD488_EC1-001', 'TCD488/EC1', 249.1, 'Light Blue 001', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Samidel-TCD648_F1-001', 'TCD648/F1', 160.0, 'Navy 004', 'Samidel', 'Stock conf. (audit CW29)'),
    ('P-Tyrrell-43793-001', '43793', 396.0, 'Sand 2952', 'Tyrrell', 'Stock conf. (audit CW29)'),
    ('P-Tyrrell-4600_48389-001', '4600 48389', 449.7, 'Dark Brown Check 977', 'Tyrrell', 'Stock conf. (audit CW29)'),
    ('P-Tyrrell-GB14W-001', 'GB14W', 22.0, 'UNI 93 Mocha Melange', 'Tyrrell', 'Stock conf. (audit CW29)'),
    ('P-Tyrrell-TCB258_EC1-001', 'TCB258/EC1', 442.53, 'Medium Beige Melange 1049', 'Tyrrell', 'Stock conf. (audit CW29)'),
    ('P-Tyrrell-TCB258_EC1-002', 'TCB258/EC1', 732.62, 'Midnight Blue 0917', 'Tyrrell', 'Stock conf. (audit CW29)'),
    ('P-Tyrrell-TCB258_EC1-003', 'TCB258/EC1', 194.79, 'Pine Green 1028', 'Tyrrell', 'Stock conf. (audit CW29)'),
    ('P-Tyrrell-TCC130_RY1-001', 'TCC130/RY1', 290.02, 'Brown Herringbone 002', 'Tyrrell', 'Stock conf. (audit CW29)'),
    ('P-Tyrrell-TCD524_EC1-001', 'TCD524/EC1', 474.35, 'Almond 001', 'Tyrrell', 'Stock conf. (audit CW29)'),
]

REAL_CONSUMPTIONS = [
    ('POAPS2000004300', 'Women Serene Short Jacket Berry Pinstripe', 50, 57.50, 60.99, 6.07, '2026-07-18', 'Samidel', 'Real: 1.220 m/pc | Esperado: 1.15 m/pc'),
    ('POAPS2000004404', 'Ease Pants Black Slim', 835, 1085.50, 1186.00, 9.26, '2026-07-18', 'Samidel', 'Real: 1.420 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004405', 'Ease Pants Black Regular', 1001, 1361.36, 1478.00, 8.57, '2026-07-18', 'Samidel', 'Real: 1.477 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004406', 'Ease Pants Black Relaxed', 857, 1362.63, 1258.00, -7.68, '2026-07-18', 'Samidel', 'Real: 1.468 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004407', 'Ease Pants Dark Grey Slim', 491, 638.30, 643.70, 0.85, '2026-07-18', 'Samidel', 'Real: 1.311 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004408', 'Ease Pants Dark Grey Regular', 699, 950.64, 951.70, 0.11, '2026-07-18', 'Samidel', 'Real: 1.362 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004409', 'Ease Pants Dark Grey Relaxed', 281, 446.79, 419.70, -6.06, '2026-07-18', 'Samidel', 'Real: 1.494 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004398', 'Ease Pants Sahara Slim', 571, 742.30, 750.05, 1.04, '2026-07-18', 'Samidel', 'Real: 1.314 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004399', 'Ease Pants Sahara Regular', 350, 476.00, 500.05, 5.05, '2026-07-18', 'Samidel', 'Real: 1.429 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004400', 'Ease Pants Sahara Relaxed', 352, 559.68, 522.05, -6.72, '2026-07-18', 'Samidel', 'Real: 1.483 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004395', 'Ease Pants Mocha Slim', 575, 747.50, 788.40, 5.47, '2026-07-18', 'Samidel', 'Real: 1.371 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004396', 'Ease Pants Mocha Regular', 347, 471.92, 519.40, 10.06, '2026-07-18', 'Samidel', 'Real: 1.497 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004397', 'Ease Pants Mocha Relaxed', 277, 440.43, 424.40, -3.64, '2026-07-18', 'Samidel', 'Real: 1.532 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004401', 'Ease Pants Blue Nights Slim', 250, 325.00, 328.50, 1.08, '2026-07-18', 'Samidel', 'Real: 1.314 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004402', 'Ease Pants Blue Nights Regular', 722, 981.92, 1024.50, 4.34, '2026-07-18', 'Samidel', 'Real: 1.419 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004403', 'Ease Pants Blue Nights Relaxed', 752, 1195.68, 1086.60, -9.12, '2026-07-18', 'Samidel', 'Real: 1.445 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004348', 'Essential Suit Pants Regular Almond', 560, 756.00, 765.00, 1.19, '2026-07-18', 'Costa Correia', 'Real: 1.366 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004349', 'Essential Suit Pants Slim Almond', 373, 503.55, 480.00, -4.68, '2026-07-18', 'Costa Correia', 'Real: 1.287 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004350', 'Essential Suit Pants Slim Midnight Blue', 328, 442.80, 465.00, 5.01, '2026-07-18', 'Costa Correia', 'Real: 1.418 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004351', 'Essential Suit Pants Regular Midnight Blue', 262, 353.70, 362.00, 2.35, '2026-07-18', 'Costa Correia', 'Real: 1.382 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004198', 'Gen. 2.0 Pants Signature Dark Brown', 4524, 6107.40, 5755.33, -5.76, '2026-07-18', 'Fabrijeans', 'Real: 1.272 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004353', 'Essential Suit Pants Regular Dark Grey Melange', 153, 206.55, 229.79, 11.25, '2026-07-18', 'Costa Correia', 'Real: 1.502 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004352', 'Essential Suit Pants Regular Pine Green', 150, 202.50, 208.97, 3.2, '2026-07-18', 'Costa Correia', 'Real: 1.393 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004233', 'Women Nara Pants Straight Cool Brown', 936, 1263.60, 1387.10, 9.77, '2026-07-18', 'Costa Correia', 'Real: 1.482 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004378', 'Women Ease Pants Straight Steel Melange', 20, 27.00, 30.00, 11.11, '2026-07-18', 'Costa Correia', 'Real: 1.500 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004384', 'Women Ease Pants Tapered Blue Nights', 177, 238.95, 229.00, -4.16, '2026-07-18', 'Costa Correia', 'Real: 1.294 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004385', 'Women Ease Pants Straight Blue Nights', 301, 406.35, 444.00, 9.27, '2026-07-18', 'Costa Correia', 'Real: 1.475 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004376', 'Women Ease Pants Straight Vanilla Melange', 60, 81.00, 88.00, 8.64, '2026-07-18', 'Costa Correia', 'Real: 1.467 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004377', 'Women Ease Pants Wide Vanilla Melange', 76, 102.60, 124.00, 20.86, '2026-07-18', 'Costa Correia', 'Real: 1.632 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004234', 'Women Nara Pants Straight Grey Flint', 656, 885.60, 975.50, 10.15, '2026-07-18', 'Costa Correia', 'Real: 1.487 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004387', 'Women Ease Pants Straight Black', 538, 726.30, 809.00, 11.39, '2026-07-18', 'Costa Correia', 'Real: 1.504 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004386', 'Women Ease Pants Tapered Black', 233, 314.55, 325.80, 3.58, '2026-07-18', 'Costa Correia', 'Real: 1.398 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004381', 'Women Ease Pants Tapered Mocha Melange', 199, 268.65, 258.60, -3.74, '2026-07-18', 'Costa Correia', 'Real: 1.299 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004382', 'Women Ease Pants Straight Mocha Melange', 558, 753.30, 820.00, 8.85, '2026-07-18', 'Costa Correia', 'Real: 1.470 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004383', 'Women Ease Pants Wide Mocha Melange', 309, 417.15, 506.00, 21.3, '2026-07-18', 'Costa Correia', 'Real: 1.638 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004380', 'Women Ease Pants Wide Evergreen', 263, 355.05, 437.00, 23.08, '2026-07-18', 'Costa Correia', 'Real: 1.662 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004379', 'Women Ease Pants Straight Evergreen', 198, 267.30, 288.40, 7.89, '2026-07-18', 'Costa Correia', 'Real: 1.457 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004252', 'Motion Suit Pants Pepper Grey', 603, 814.05, 796.70, -2.13, '2026-07-18', 'Samidel', 'Real: 1.321 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004251', 'Motion Suit Pants Midnight Blue', 1085, 1464.75, 1465.90, 0.08, '2026-07-18', 'Samidel', 'Real: 1.351 m/pc | Esperado: 1.35 m/pc'),
]


# ===================== INIT DB =====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS fabric_refs (
        ref_code TEXT PRIMARY KEY,
        description TEXT,
        supplier TEXT,
        reorder_point REAL DEFAULT 500,
        unit TEXT DEFAULT 'm'
    );
    CREATE TABLE IF NOT EXISTS fabric_rolls (
        token TEXT PRIMARY KEY,
        ref_code TEXT NOT NULL,
        metres REAL NOT NULL,
        lot TEXT,
        color TEXT,
        warehouse TEXT NOT NULL DEFAULT 'XBS',
        status TEXT NOT NULL DEFAULT 'AVAILABLE',
        po_garment TEXT,
        date_received TEXT,
        date_last_move TEXT,
        notes TEXT
    );
    CREATE TABLE IF NOT EXISTS incoming_fabric (
        po_number TEXT PRIMARY KEY,
        supplier TEXT NOT NULL,
        ref_code TEXT,
        total_metres REAL NOT NULL,
        expected_date TEXT,
        status TEXT DEFAULT 'EXPECTED',
        tracking_ref TEXT,
        date_created TEXT
    );
    CREATE TABLE IF NOT EXISTS production (
        po_number TEXT PRIMARY KEY,
        model_name TEXT NOT NULL,
        confeccionador TEXT NOT NULL,
        po_qty INTEGER NOT NULL,
        fabric_ref TEXT,
        metres_expected REAL,
        expected_date TEXT,
        status TEXT DEFAULT 'PENDING',
        date_created TEXT
    );
    CREATE TABLE IF NOT EXISTS consumption_map (
        model_name TEXT NOT NULL,
        fabric_ref TEXT NOT NULL,
        m_per_pc_expected REAL NOT NULL,
        m_per_pc_actual REAL,
        PRIMARY KEY (model_name, fabric_ref)
    );
    CREATE TABLE IF NOT EXISTS consumptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_garment TEXT NOT NULL,
        model_name TEXT,
        pcs_cut INTEGER,
        metres_expected REAL,
        metres_actual REAL,
        deviation_pct REAL,
        date_cut TEXT,
        confeccionador TEXT,
        notes TEXT
    );
    CREATE TABLE IF NOT EXISTS movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_time TEXT NOT NULL,
        move_type TEXT NOT NULL,
        token TEXT,
        from_location TEXT,
        to_location TEXT,
        ref_code TEXT,
        color TEXT,
        metres REAL,
        po_garment TEXT,
        notes TEXT
    );
    """)

    # Migração: adiciona coluna color a bases antigas (sem perder dados)
    cursor.execute("PRAGMA table_info(movements)")
    existing_cols = [r[1] for r in cursor.fetchall()]
    if 'color' not in existing_cols:
        cursor.execute("ALTER TABLE movements ADD COLUMN color TEXT")

    cursor.execute("SELECT COUNT(*) FROM fabric_refs")
    if cursor.fetchone()[0] == 0:
        for ref, desc, supplier, reorder in FABRIC_REFS:
            cursor.execute("INSERT INTO fabric_refs VALUES (?,?,?,?,?)", (ref, desc, supplier, reorder, 'm'))

        for po, supplier, ref, metres, date, status in INCOMING_FABRIC:
            cursor.execute("INSERT INTO incoming_fabric VALUES (?,?,?,?,?,?,?,?)",
                         (po, supplier, ref, metres, date, status, None, datetime.now().isoformat()))

        for po, model, conf, qty, ref, metres, date, status in PRODUCTION:
            cursor.execute("INSERT INTO production VALUES (?,?,?,?,?,?,?,?,?)",
                         (po, model, conf, qty, ref, metres, date, status, datetime.now().isoformat()))

        for model, ref, mpc in CONSUMPTION_MAP:
            cursor.execute("INSERT OR IGNORE INTO consumption_map VALUES (?,?,?,?)", (model, ref, mpc, None))

        for token, ref, metres, lot, color, wh, notes in FABRIC_ROLLS:
            cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (token, ref, metres, lot, color, wh, 'AVAILABLE', None,
                          datetime.now().isoformat(), datetime.now().isoformat(), notes))

        # Stock em confeccionadores (audit CW29) — "(stock)" = AVAILABLE | "(in process)" = IN_PROCESS
        for token, ref, metres, color, conf, nota in IN_PROCESS_STOCK:
            roll_status = 'IN_PROCESS' if nota.startswith('Em processo') else 'AVAILABLE'
            cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (token, ref, metres, None, color, conf, roll_status, None,
                          datetime.now().isoformat(), datetime.now().isoformat(), nota))

        # Consumos reais CW28/29 com desvios
        for po, model, pcs, exp_m, act_m, dev, date, conf, notes in REAL_CONSUMPTIONS:
            cursor.execute("INSERT INTO consumptions VALUES (NULL,?,?,?,?,?,?,?,?,?)",
                         (po, model, pcs, exp_m, act_m, dev, date, conf, notes))

        # Derivar entradas de mapa para modelos sem standard (Ease, Nara, Motion, Serene…)
        # standard = esperado dos consumos reais | real = média produtiva real
        cursor.execute("""
            INSERT OR IGNORE INTO consumption_map (model_name, fabric_ref, m_per_pc_expected, m_per_pc_actual)
            SELECT c.model_name, p.fabric_ref,
                   ROUND(AVG(c.metres_expected / CAST(c.pcs_cut AS REAL)), 2),
                   ROUND(AVG(c.metres_actual / CAST(c.pcs_cut AS REAL)), 3)
            FROM consumptions c JOIN production p ON c.po_garment = p.po_number
            WHERE c.pcs_cut > 0 AND c.metres_expected > 0 AND p.fabric_ref IS NOT NULL
            GROUP BY c.model_name, p.fabric_ref
        """)

        # Atualizar real médio no mapa de consumos
        cursor.execute("""
            UPDATE consumption_map SET m_per_pc_actual = (
                SELECT ROUND(AVG(c.metres_actual / CAST(c.pcs_cut AS REAL)), 3)
                FROM consumptions c
                WHERE c.pcs_cut > 0 AND (
                    c.model_name = consumption_map.model_name
                    OR c.model_name LIKE '%' || REPLACE(consumption_map.model_name, ' Men Plain', '') || '%'
                )
            )
        """)

    conn.commit()
    conn.close()

init_db()


# ===================== STOCK CALCULATIONS =====================
def get_stock_position():
    query = """
    SELECT
        fr.ref_code,
        fr.supplier,
        fr.description,
        fr.reorder_point,
        COALESCE(SUM(CASE WHEN fr2.status = 'AVAILABLE' THEN fr2.metres ELSE 0 END), 0) as disponivel,
        COALESCE(SUM(CASE WHEN fr2.status = 'RESERVED' THEN fr2.metres ELSE 0 END), 0) as reservado,
        COALESCE(SUM(CASE WHEN fr2.status = 'IN_PROCESS' THEN fr2.metres ELSE 0 END), 0) as em_processo,
        COALESCE(SUM(CASE WHEN fr2.status IN ('AVAILABLE', 'RESERVED', 'IN_PROCESS') THEN fr2.metres ELSE 0 END), 0) as total_stock
    FROM fabric_refs fr
    LEFT JOIN fabric_rolls fr2 ON fr.ref_code = fr2.ref_code
    GROUP BY fr.ref_code, fr.supplier, fr.description, fr.reorder_point
    """
    stock_df = query_to_df(query)

    incoming_df = query_to_df("SELECT ref_code, COALESCE(SUM(total_metres), 0) as a_chegar FROM incoming_fabric WHERE status IN ('EXPECTED', 'IN_TRANSIT') GROUP BY ref_code")
    necessity_df = query_to_df("SELECT fabric_ref, COALESCE(SUM(metres_expected), 0) as necessidade FROM production WHERE status IN ('PENDING', 'CUTTING') GROUP BY fabric_ref")
    cores_df = query_to_df("""
        SELECT ref_code, GROUP_CONCAT(DISTINCT color) as cores
        FROM fabric_rolls WHERE status != 'INVOICED' AND color IS NOT NULL AND color != ''
        GROUP BY ref_code
    """)

    result = stock_df.merge(incoming_df, on='ref_code', how='left')
    result = result.merge(necessity_df, left_on='ref_code', right_on='fabric_ref', how='left')
    result = result.drop(columns=['fabric_ref'], errors='ignore')
    result = result.merge(cores_df, on='ref_code', how='left')
    result['cores'] = result['cores'].fillna('')
    result = result.fillna(0)

    result['stock_liquido'] = result['disponivel'] + result['em_processo']
    result['planeamento'] = result['stock_liquido'] + result['a_chegar'] - result['necessidade']

    def classify_status(row):
        if row['planeamento'] < 0: return '🔴 ' + t('st_crit')
        elif row['disponivel'] < row['reorder_point']: return '🟠 ' + t('st_low')
        elif row['necessidade'] > (row['disponivel'] + row['em_processo']): return '🟡 ' + t('st_risk')
        else: return '🟢 ok'

    result['status'] = result.apply(classify_status, axis=1)
    return result

# ===================== EXPORT =====================
def to_excel(df, sheet_name='Dados'):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output

def to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def export_stock_summary():
    return to_excel(get_stock_position(), 'Stock Resumido')

def export_stock_detailed():
    df = query_to_df("""SELECT fr.supplier, r.ref_code, r.color, r.metres, r.lot, r.warehouse, r.status, r.po_garment, r.date_received, r.date_last_move, r.notes, r.token
                        FROM fabric_rolls r LEFT JOIN fabric_refs fr ON r.ref_code = fr.ref_code
                        ORDER BY r.ref_code, r.token""")
    return to_excel(df, 'Stock Detalhado')

def get_mpc(model_name, fabric_ref=None):
    """Consumo por peça. Prefere sempre a média real produtiva; fallback para o standard predefinido.
    Devolve (m_per_pc, fonte) com fonte = 'real' | 'standard' | None."""
    q = "SELECT model_name, fabric_ref, m_per_pc_expected, m_per_pc_actual FROM consumption_map"
    params = []
    if fabric_ref:
        q += " WHERE fabric_ref = ?"
        params.append(fabric_ref)
    rows = query_to_df(q, params)
    if rows.empty:
        return None, None
    model_lower = str(model_name).lower()
    for _, r in rows.iterrows():
        key = str(r['model_name']).lower().replace(' men plain', '').replace(' men checked', '').replace(' men striped', '')
        if key and key in model_lower:
            if r['m_per_pc_actual']:
                return r['m_per_pc_actual'], 'real'
            return r['m_per_pc_expected'], 'standard'
    r0 = rows.iloc[0]
    if r0['m_per_pc_actual']:
        return r0['m_per_pc_actual'], 'real'
    return r0['m_per_pc_expected'], 'standard'


def safe_display_df(df):
    """Limpa DataFrame para evitar PyArrow segfault"""
    df = df.copy()
    df = df.fillna('')
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str)
    return df

def download_pair(df, base_name, excel_sheet='Dados', key_prefix='dl'):
    """Botões gémeos de download Excel + CSV."""
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Excel", to_excel(df, excel_sheet), f"{base_name}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"{key_prefix}_xlsx")
    with c2:
        st.download_button("⬇️ CSV", to_csv(df), f"{base_name}.csv", "text/csv", key=f"{key_prefix}_csv")


# ===================== UI: DASHBOARD =====================
def render_dashboard():
    st.markdown(f"""
    <div class="main-header">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <h1>🏭 SNT CMT</h1>
                <p>{t('h_sub')}</p>
            </div>
            <div class="live-badge"><span class="live-dot"></span> LIVE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        stock_df = get_stock_position()

        n_incoming = query_to_df("SELECT COUNT(*) as c FROM incoming_fabric WHERE status IN ('EXPECTED','IN_TRANSIT')").iloc[0]['c']
        n_pending = query_to_df("SELECT COUNT(*) as c FROM production WHERE status != 'INVOICED'").iloc[0]['c']

        kpi_data = [
            (t('k_avail'), stock_df['disponivel'].sum(), t('k_avail_d'), "up"),
            (t('k_process'), stock_df['em_processo'].sum(), f"{n_pending} {t('k_process_d')}", "warn"),
            (t('k_incoming'), stock_df['a_chegar'].sum(), f"{n_incoming} {t('k_incoming_d')}", "info"),
            (t('k_need'), stock_df['necessidade'].sum(), t('k_need_d'), "down"),
            (t('k_net'), stock_df['stock_liquido'].sum(), t('k_net_d'), "up"),
            (t('k_plan'), stock_df['planeamento'].sum(), t('k_plan_d'), "info"),
        ]

        cols = st.columns(6)
        for i, (label, value, delta, delta_type) in enumerate(kpi_data):
            with cols[i]:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value:,.0f}<span style="font-size:14px;color:var(--muted)">m</span></div>
                    <div class="kpi-delta {delta_type}">{delta}</div>
                </div>
                """, unsafe_allow_html=True)

        # Alertas
        st.markdown(f'<div class="section-title">{t("d_alerts")}</div>', unsafe_allow_html=True)

        critical = stock_df[stock_df['status'].str.contains(t('st_crit'), regex=False)]
        warning = stock_df[stock_df['status'].str.contains(t('st_low'), regex=False)]
        risk = stock_df[stock_df['status'].str.contains(t('st_risk'), regex=False)]
        ok = stock_df[stock_df['status'].str.contains('ok')]

        alerts_html = '<div class="alert-bar">'
        if not critical.empty:
            for _, row in critical.iterrows():
                alerts_html += f'<div class="alert-chip critical"><span class="alert-dot"></span>{t("al_crit")}: {row["ref_code"]} — {row["planeamento"]:,.0f}m</div>'
        if not warning.empty:
            for _, row in warning.head(4).iterrows():
                alerts_html += f'<div class="alert-chip warning"><span class="alert-dot"></span>{t("al_low")}: {row["ref_code"]} — {row["disponivel"]:,.0f}m &lt; {row["reorder_point"]:,.0f}m</div>'
        if not risk.empty:
            for _, row in risk.head(4).iterrows():
                alerts_html += f'<div class="alert-chip info"><span class="alert-dot"></span>{t("al_risk")}: {row["ref_code"]} — {t("al_risk_txt")}</div>'
        if not ok.empty:
            ok_refs = ', '.join(ok['ref_code'].head(3).tolist())
            alerts_html += f'<div class="alert-chip ok"><span class="alert-dot"></span>{ok_refs} — {t("al_bal")}</div>'
        alerts_html += '</div>'
        st.markdown(alerts_html, unsafe_allow_html=True)

        # Posição de stock
        st.markdown(f'<div class="section-title">{t("d_pos")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-subtitle">{t("d_pos_sub")}</div>', unsafe_allow_html=True)

        display_df = stock_df[['supplier', 'ref_code', 'description', 'cores', 'disponivel', 'em_processo', 'stock_liquido', 'a_chegar', 'necessidade', 'planeamento', 'status']].copy()

        def _cores_short(s):
            if not s:
                return ''
            parts = [p.strip() for p in str(s).split(',') if p.strip()]
            shown = ' '.join(color_dot(p) + p for p in parts[:3])
            return shown + (f" +{len(parts) - 3}" if len(parts) > 3 else '')

        display_df['cores'] = display_df['cores'].apply(_cores_short)
        display_df = add_total_row(display_df)
        display_df = safe_display_df(display_df)
        display_df.columns = [t('c_supplier'), t('c_ref'), t('c_desc'), t('c_colors'), t('c_avail'), t('c_inproc'), t('c_net'), t('c_inc'), t('c_need'), t('c_plan'), t('c_status')]
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

        # Pipeline
        st.markdown(f'<div class="section-title">{t("d_pipe")}</div>', unsafe_allow_html=True)
        prod_summary = query_to_df("""
            SELECT confeccionador, COUNT(*) as num_pos, SUM(po_qty) as total_pcs, SUM(metres_expected) as total_m
            FROM production WHERE status != 'INVOICED' GROUP BY confeccionador ORDER BY total_m DESC
        """)
        if not prod_summary.empty:
            prod_summary = safe_display_df(prod_summary)
            prod_summary.columns = [t('c_conf'), t('c_activepo'), t('c_totpcs'), t('c_mexp')]
            st.dataframe(prod_summary, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"{t('d_err')}{e}")
        st.info(t('d_init'))


# ===================== UI: STOCK =====================
def render_stock():
    st.markdown(f'<div class="section-title">{t("s_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-subtitle">{t("s_sub")}</div>', unsafe_allow_html=True)

    try:
        wh_df = query_to_df("""
            SELECT warehouse, ref_code, status, COUNT(*) as num_rolls, COALESCE(SUM(metres), 0) as total_metres
            FROM fabric_rolls WHERE status != 'INVOICED'
            GROUP BY warehouse, ref_code, status ORDER BY warehouse, ref_code
        """)

        if not wh_df.empty:
            piv = wh_df.pivot_table(index='warehouse', columns='status', values='total_metres', aggfunc='sum').fillna(0).reset_index()
            for col in ['AVAILABLE', 'IN_PROCESS', 'RESERVED']:
                if col not in piv.columns:
                    piv[col] = 0.0
            rolls_n = wh_df.groupby('warehouse')['num_rolls'].sum().reset_index()
            summary = piv.merge(rolls_n, on='warehouse')
            summary['total'] = summary['AVAILABLE'] + summary['IN_PROCESS'] + summary['RESERVED']
            summary['tipo'] = summary['warehouse'].apply(lambda w: '🏭' if w in WAREHOUSES else '👕')
            summary = summary[['tipo', 'warehouse', 'AVAILABLE', 'IN_PROCESS', 'total', 'num_rolls']].sort_values('total', ascending=False)
            summary = safe_display_df(add_total_row(summary))
            summary.columns = ['', t('c_loc'), t('c_availm'), t('c_inprocm'), t('c_totalm'), t('c_rollslot')]
            st.dataframe(summary, use_container_width=True, hide_index=True)

        # Filtros
        st.markdown(f'<div class="section-title">{t("s_detail")}</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            wh_list = query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls ORDER BY warehouse")['warehouse'].tolist()
            selected_wh = st.selectbox(t('f_wh'), [t('opt_all')] + wh_list, key="stock_wh")
        with col2:
            ref_list = query_to_df("SELECT DISTINCT ref_code FROM fabric_rolls ORDER BY ref_code")['ref_code'].tolist()
            selected_ref = st.selectbox(t('f_ref'), [t('opt_all_f')] + ref_list, key="stock_ref")
        with col3:
            selected_status = st.selectbox("Status", [t('opt_all')] + ROLL_STATUSES, key="stock_status")

        query = """SELECT fr.supplier, r.ref_code, r.color, r.metres, r.lot, r.warehouse, r.status, r.po_garment, r.notes, r.token
                   FROM fabric_rolls r LEFT JOIN fabric_refs fr ON r.ref_code = fr.ref_code WHERE 1=1"""
        params = []
        if selected_wh != t('opt_all'):
            query += " AND r.warehouse = ?"; params.append(selected_wh)
        if selected_ref != t('opt_all_f'):
            query += " AND r.ref_code = ?"; params.append(selected_ref)
        if selected_status != t('opt_all'):
            query += " AND r.status = ?"; params.append(selected_status)
        query += " ORDER BY r.ref_code, r.token LIMIT 500"

        rolls_df = add_total_row(query_to_df(query, params))
        clean_df = safe_display_df(rolls_df)
        clean_df.columns = [t('c_supplier'), t('c_ref'), t('c_color'), t('c_metres'), t('c_lot'), t('c_wh'), t('c_status'), t('c_po'), t('c_notes'), t('c_token')]
        clean_df = apply_color_badges(clean_df, 'Cor')
        st.dataframe(clean_df, use_container_width=True, hide_index=True, height=500)

        # --- Atribuir / corrigir cor de rolos ---
        n_sem_cor = query_to_df("SELECT COUNT(*) as c FROM fabric_rolls WHERE (color IS NULL OR color = '') AND status != 'INVOICED'").iloc[0]['c']
        if n_sem_cor > 0:
            st.markdown(f'<div class="alert-bar"><div class="alert-chip warning"><span class="alert-dot"></span>⚠️ {n_sem_cor} {t("s_sem_cor")}</div></div>', unsafe_allow_html=True)

        with st.expander(t('s_assign'), expanded=(n_sem_cor > 0)):
            st.markdown(f'<div class="section-subtitle">{t("s_assign_sub")}</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                ac_refs = query_to_df("SELECT DISTINCT ref_code FROM fabric_rolls WHERE status != 'INVOICED' ORDER BY ref_code")['ref_code'].tolist()
                ac_ref = st.selectbox(t('f_ref'), ac_refs, key="ac_ref")
            with c2:
                ac_whs = query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls WHERE ref_code = ? AND status != 'INVOICED'", (ac_ref,))['warehouse'].tolist()
                ac_wh = st.selectbox(t('f_wh'), [t('opt_all')] + ac_whs, key="ac_wh")

            ac_q = "SELECT token, metres, color, warehouse FROM fabric_rolls WHERE ref_code = ? AND status != 'INVOICED'"
            ac_p = [ac_ref]
            if ac_wh != t('opt_all'):
                ac_q += " AND warehouse = ?"
                ac_p.append(ac_wh)
            ac_only = st.checkbox(t('f_only_nocolor'), value=True, key="ac_only")
            if ac_only:
                ac_q += " AND (color IS NULL OR color = '')"
            ac_q += " ORDER BY token"
            ac_rolls = query_to_df(ac_q, ac_p)

            if ac_rolls.empty:
                st.success(t('ok_nocolor'))
            else:
                ac_sel = st.multiselect(
                    f"{t('f_rolls')} ({len(ac_rolls)})",
                    ac_rolls['token'].tolist(),
                    format_func=lambda t: f"{color_dot(ac_rolls[ac_rolls['token']==t].iloc[0]['color'])} "
                                          f"{ac_rolls[ac_rolls['token']==t].iloc[0]['color'] or 's/cor'}"
                                          f" · {ac_rolls[ac_rolls['token']==t].iloc[0]['metres']:.1f}m"
                                          f" @ {ac_rolls[ac_rolls['token']==t].iloc[0]['warehouse']} — {t}",
                    key="ac_tokens")
                apply_all = st.checkbox(t('f_apply_all', n=len(ac_rolls)), key="ac_all")

                ac_colors = query_to_df("SELECT DISTINCT color FROM fabric_rolls WHERE ref_code = ? AND color IS NOT NULL AND color != '' ORDER BY color", (ac_ref,))['color'].tolist()
                ac_color_sel = st.selectbox(t('f_color_apply'), ac_colors + [t('f_new_color')],
                                            format_func=lambda c: color_badge(c) if c != '➕ Nova cor…' else c,
                                            key="ac_color_sel")
                if ac_color_sel == t('f_new_color'):
                    ac_color = st.text_input(t('f_type_color'), placeholder="Dark Navy", key="ac_color_new")
                else:
                    ac_color = ac_color_sel

                if st.button(t('b_apply_color'), key="ac_apply"):
                    targets = ac_rolls['token'].tolist() if apply_all else ac_sel
                    if not targets:
                        st.error(t('err_select_rolls'))
                    elif not ac_color or not str(ac_color).strip():
                        st.error(t('err_pick_color'))
                    else:
                        ac_color = str(ac_color).strip()
                        execute_many("UPDATE fabric_rolls SET color = ? WHERE token = ?", [(ac_color, t) for t in targets])
                        log_movement('EDIT', None, ac_wh if ac_wh != 'Todos' else None, None, ac_ref, None, None,
                                     f'Cor atribuída → {ac_color} ({len(targets)} rolos)', ac_color)
                        st.success(f"✅ {color_badge(ac_color)} {t('ok_color', n=len(targets), ref=ac_ref)}")
                        st.rerun()

        st.markdown(f'<div class="section-title">{t("s_export")}</div>', unsafe_allow_html=True)
        download_pair(rolls_df, f"stock_{datetime.now().strftime('%Y%m%d')}", 'Stock', 'stock_sel')

    except Exception as e:
        st.error(f"Stock error: {e}")


# ===================== UI: INCOMING =====================
def render_incoming():
    st.markdown(f'<div class="section-title">{t("i_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-subtitle">{t("i_sub")}</div>', unsafe_allow_html=True)

    incoming_df = query_to_df("""
        SELECT i.supplier, i.ref_code, fr.description, i.total_metres, i.expected_date, i.status, i.tracking_ref, i.po_number
        FROM incoming_fabric i LEFT JOIN fabric_refs fr ON i.ref_code = fr.ref_code
        WHERE i.status IN ('EXPECTED', 'IN_TRANSIT') ORDER BY i.expected_date
    """)

    if not incoming_df.empty:
        clean = safe_display_df(add_total_row(incoming_df))
        clean.columns = [t('c_supplier'), t('c_ref'), t('c_desc'), t('c_metres'), t('c_date_exp'), t('c_status'), t('c_tracking'), t('c_po2')]
        st.dataframe(clean, use_container_width=True, hide_index=True, height=400)

        # Marcar como recebido → vai para Receção no menu Movimentar
        st.markdown(f'<div class="section-title">{t("i_mark")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-subtitle">{t("i_mark_sub")}</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            po_sel = st.selectbox(t('i_po'), incoming_df['po_number'].tolist(), key="incoming_po")
        with col2:
            st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
            if st.button(t('b_arrived'), key="incoming_arrived"):
                execute_sql("UPDATE incoming_fabric SET status = 'RECEIVED' WHERE po_number = ?", (po_sel,))
                log_movement('ARRIVAL', None, 'Fornecedor', 'XBS', None, None, None, f'PO tecido {po_sel} chegou — aguarda registo de rolos')
                st.success(t('ok_arrived', po=po_sel))
                st.rerun()

        # Timeline
        st.markdown(f'<div class="section-title">{t("i_cal")}</div>', unsafe_allow_html=True)
        st.markdown('<div class="timeline">', unsafe_allow_html=True)
        for _, row in incoming_df.head(10).iterrows():
            status_class = "completed" if row['status'] == 'IN_TRANSIT' else "pending"
            tracking = row['tracking_ref'] if row['tracking_ref'] else t('i_notrack')
            st.markdown(f"""
            <div class="timeline-item {status_class}">
                <div class="timeline-date">{row['expected_date']}</div>
                <div class="timeline-text">{row['po_number']} — {row['supplier']} {row['ref_code']} {row['total_metres']:,.0f}m</div>
                <div class="timeline-meta">{row['status']} | {tracking}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info(t('i_none'))


# ===================== UI: PRODUCTION (MODO LIVE) =====================
def render_production():
    st.markdown(f'<div class="section-title">{t("p_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-subtitle">{t("p_sub")}</div>', unsafe_allow_html=True)

    tab_live, tab_list, tab_status = st.tabs([t('tab_live'), t('tab_edit'), t('tab_status')])

    # ---------- TAB LIVE ----------
    with tab_live:
        active_pos = query_to_df("""
            SELECT po_number, model_name, confeccionador, po_qty, fabric_ref, metres_expected, status
            FROM production WHERE status IN ('PENDING', 'CUTTING') ORDER BY po_number DESC
        """)

        if active_pos.empty:
            st.info(t('p_no_active'))
        else:
            po_options = active_pos['po_number'].tolist()
            po_sel = st.selectbox(t('p_sel_po'), po_options, key="live_po",
                                  format_func=lambda p: f"{p} — {active_pos[active_pos['po_number']==p].iloc[0]['model_name'][:45]}")

            po_row = active_pos[active_pos['po_number'] == po_sel].iloc[0]

            # Consumo: prefere média real produtiva; fallback standard
            expected_mpc, mpc_source = get_mpc(po_row['model_name'], po_row['fabric_ref'])

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div class="info-card" style="text-align:center;">
                    <div class="dev-label">{t('card_conf')}</div>
                    <div style="color:var(--text);font-size:16px;font-weight:600;">{po_row['confeccionador']}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="info-card" style="text-align:center;">
                    <div class="dev-label">{t('card_pcs')}</div>
                    <div style="color:var(--text);font-size:16px;font-weight:600;">{int(po_row['po_qty'])} pcs</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="info-card" style="text-align:center;">
                    <div class="dev-label">{t('card_fref')}</div>
                    <div style="color:var(--text);font-size:16px;font-weight:600;">{po_row['fabric_ref'] or '—'}</div>
                </div>""", unsafe_allow_html=True)
            with c4:
                mpc_txt = f"{expected_mpc:.2f} m/pc" if expected_mpc else t('no_map')
                src_txt = {"real": t('src_real'), "standard": t('src_std'), None: ""}.get(mpc_source, "")
                st.markdown(f"""<div class="info-card" style="text-align:center;">
                    <div class="dev-label">{t('card_cons')}</div>
                    <div style="color:var(--text);font-size:16px;font-weight:600;">{mpc_txt}</div>
                    <div style="color:var(--muted);font-size:10px;">{src_txt}</div>
                </div>""", unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                pcs_cut = st.number_input(t('p_pcs'), min_value=0, value=int(po_row['po_qty']), step=1, key="live_pcs")
            with col2:
                metres_real = st.number_input(t('p_metres'), min_value=0.0, step=0.1, key="live_metres",
                                              value=float(pcs_cut * expected_mpc) if expected_mpc else 0.0)
            with col3:
                st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
                confirm_cut = st.button(t('b_cut'), key="live_confirm")

            # Validação de desvio em tempo real
            if pcs_cut > 0 and metres_real > 0 and expected_mpc:
                real_mpc = metres_real / pcs_cut
                dev_pct = ((real_mpc - expected_mpc) / expected_mpc) * 100
                dev_class = "ok" if abs(dev_pct) <= 2 else ("warn" if abs(dev_pct) <= 5 else "bad")
                dev_color = {"ok": "#22c55e", "warn": "#f59e0b", "bad": "#ef4444"}[dev_class]
                dev_msg = {"ok": t('dev_ok'), "warn": t('dev_warn'), "bad": t('dev_bad')}[dev_class]
                st.markdown(f"""
                <div class="dev-box {dev_class}">
                    <div class="dev-label">{t('dev_label')} — {dev_msg}</div>
                    <div class="dev-value" style="color:{dev_color};">{dev_pct:+.1f}%</div>
                    <div style="color:var(--muted);font-size:12px;">real {real_mpc:.3f} m/pc vs esperado {expected_mpc:.3f} m/pc</div>
                </div>
                """, unsafe_allow_html=True)
            elif not expected_mpc:
                st.warning(t('p_no_map'))
                real_mpc, dev_pct = (metres_real / pcs_cut if pcs_cut else 0), None
            else:
                real_mpc, dev_pct = 0, None

            if confirm_cut:
                if pcs_cut <= 0 or metres_real <= 0:
                    st.error(t('err_vals'))
                else:
                    exp_m = round(pcs_cut * expected_mpc, 2) if expected_mpc else None
                    execute_sql("INSERT INTO consumptions VALUES (NULL,?,?,?,?,?,?,?,?,?)",
                                (po_sel, po_row['model_name'], pcs_cut, exp_m, metres_real,
                                 round(dev_pct, 2) if dev_pct is not None else None,
                                 datetime.now().strftime('%Y-%m-%d'), po_row['confeccionador'],
                                 f"Live: {real_mpc:.3f} m/pc" if real_mpc else "Live"))
                    # Atualiza estado da PO para CUTTING se ainda PENDING
                    if po_row['status'] == 'PENDING':
                        execute_sql("UPDATE production SET status = 'CUTTING' WHERE po_number = ?", (po_sel,))
                    # Atualiza real médio no mapa
                    if expected_mpc:
                        execute_sql("""
                            UPDATE consumption_map SET m_per_pc_actual = (
                                SELECT ROUND(AVG(metres_actual / CAST(pcs_cut AS REAL)), 3)
                                FROM consumptions WHERE pcs_cut > 0 AND model_name = ?)
                            WHERE model_name = ?""", (po_row['model_name'], po_row['model_name']))
                    log_movement('CUT', None, po_row['confeccionador'], po_row['confeccionador'],
                                 po_row['fabric_ref'], metres_real, po_sel,
                                 f"Corte registado: {pcs_cut} pcs, {metres_real:.1f}m, desvio {dev_pct:+.1f}%" if dev_pct is not None else f"Corte registado: {pcs_cut} pcs")
                    st.success(t('ok_cut', pcs=pcs_cut, mpc=f"{real_mpc:.3f}", m=f"{metres_real:,.1f}") +
                               (f" | {dev_pct:+.1f}%" if dev_pct is not None else ""))
                    st.rerun()

    # ---------- TAB LISTA (EDITÁVEL) ----------
    with tab_list:
        st.markdown(f'<div class="section-subtitle">{t("p_edit_sub")}</div>', unsafe_allow_html=True)
        status_filter = st.selectbox(t('p_view'), [t('v_active'), 'PENDING', 'CUTTING', 'INVOICED'], key="prod_filter")

        base_q = """SELECT p.po_number, fr.supplier as fornecedor, p.fabric_ref, p.model_name, p.confeccionador,
                           p.po_qty, p.metres_expected, p.expected_date, p.status
                    FROM production p LEFT JOIN fabric_refs fr ON p.fabric_ref = fr.ref_code"""
        if status_filter == t('v_active'):
            q = base_q + " WHERE p.status IN ('PENDING','CUTTING') ORDER BY p.expected_date"
        else:
            q = base_q + f" WHERE p.status = '{status_filter}' ORDER BY p.expected_date"
        prod_df = query_to_df(q)

        if status_filter == 'INVOICED':
            if not prod_df.empty:
                clean = safe_display_df(add_total_row(prod_df))
                clean.columns = [t('c_po2'), t('c_fsup'), t('c_fref'), t('c_model'), t('c_conf'), t('c_qty'), t('c_metres'), t('c_delivery'), t('c_state')]
                st.dataframe(clean, use_container_width=True, hide_index=True, height=450)
            else:
                st.info(t('p_no_inv'))
        else:
            refs_opts = query_to_df("SELECT ref_code FROM fabric_refs ORDER BY ref_code")['ref_code'].tolist()
            edited = st.data_editor(
                prod_df,
                use_container_width=True, hide_index=True, num_rows="dynamic", height=450,
                column_config={
                    "po_number": st.column_config.TextColumn("PO", required=True),
                    "fornecedor": st.column_config.TextColumn(t('c_fsup'), disabled=True),
                    "fabric_ref": st.column_config.SelectboxColumn(t('c_fref'), options=refs_opts, required=True),
                    "model_name": st.column_config.TextColumn(t('c_model'), required=True),
                    "confeccionador": st.column_config.SelectboxColumn(t('c_conf'), options=CONFECCIONADORES, required=True),
                    "po_qty": st.column_config.NumberColumn(t('c_qty'), min_value=0, step=1, required=True),
                    "metres_expected": st.column_config.NumberColumn(t('c_metres'), min_value=0.0, step=0.1, format="%.1f"),
                    "expected_date": st.column_config.TextColumn(t('c_delivery')),
                    "status": st.column_config.SelectboxColumn(t('c_state'), options=['PENDING', 'CUTTING'], required=True),
                },
                key="prod_editor")
            total_m = pd.to_numeric(edited['metres_expected'], errors='coerce').fillna(0).sum()
            st.markdown(f'<div class="section-subtitle">{len(edited)} POs | {total_m:,.0f}m esperados</div>', unsafe_allow_html=True)

            if st.button(t('b_save_prod'), key="prod_save"):
                edited = edited.dropna(subset=['po_number'])
                edited = edited[edited['po_number'].astype(str).str.strip() != '']
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT po_number FROM production WHERE status != 'INVOICED'")
                existing = {r[0] for r in cur.fetchall()}
                cur.execute("SELECT po_number FROM production WHERE status = 'INVOICED'")
                invoiced_pos = {r[0] for r in cur.fetchall()}
                keep = set(edited['po_number'].astype(str))
                for po_del in existing - keep:
                    cur.execute("DELETE FROM production WHERE po_number = ? AND status != 'INVOICED'", (po_del,))
                n = 0
                for _, r in edited.iterrows():
                    po_val = str(r['po_number']).strip()
                    if po_val in invoiced_pos:
                        continue
                    qty = 0 if pd.isna(r['po_qty']) else int(r['po_qty'])
                    m_val = 0.0 if pd.isna(r['metres_expected']) else float(r['metres_expected'])
                    cur.execute("INSERT OR REPLACE INTO production VALUES (?,?,?,?,?,?,?,?,?)",
                                (po_val, r['model_name'], r['confeccionador'], qty, r['fabric_ref'],
                                 m_val, r['expected_date'] if pd.notna(r['expected_date']) else None,
                                 r['status'] or 'PENDING', datetime.now().isoformat()))
                    n += 1
                conn.commit()
                conn.close()
                log_movement('EDIT', None, None, None, None, None, None, f'Tabela de produção atualizada ({n} POs)')
                st.success(t('ok_prod', n=n))
                st.rerun()

    # ---------- TAB STATUS ----------
    with tab_status:
        st.markdown(f'<div class="section-subtitle">{t("p_status_sub")}</div>', unsafe_allow_html=True)
        all_pos = query_to_df("SELECT po_number, model_name, confeccionador, status FROM production ORDER BY po_number DESC")
        if not all_pos.empty:
            col1, col2 = st.columns(2)
            with col1:
                po_st = st.selectbox(t('c_po'), all_pos['po_number'].tolist(), key="status_po",
                                     format_func=lambda p: f"{p} — {all_pos[all_pos['po_number']==p].iloc[0]['status']}")
            with col2:
                new_status = st.selectbox(t('p_new_status'), PROD_STATUSES, key="status_new")

            if st.button(t('b_apply_status'), key="status_apply"):
                if new_status == 'INVOICED':
                    # Baixa automática: metros em processo ligados à PO saem do stock
                    inv = query_to_df("SELECT COALESCE(SUM(metres),0) as m FROM fabric_rolls WHERE po_garment = ? AND status = 'IN_PROCESS'", (po_st,))
                    invoiced_m = inv.iloc[0]['m']
                    execute_sql("UPDATE fabric_rolls SET status = 'INVOICED', notes = 'Faturado — saiu de em processo' WHERE po_garment = ? AND status = 'IN_PROCESS'", (po_st,))
                    execute_sql("UPDATE production SET status = 'INVOICED' WHERE po_number = ?", (po_st,))
                    log_movement('INVOICE', None, 'Em Processo', 'Faturado', None, invoiced_m, po_st, f'{invoiced_m:.1f}m faturados')
                    st.success(t('ok_inv', po=po_st, m=f"{invoiced_m:,.1f}"))
                else:
                    execute_sql("UPDATE production SET status = ? WHERE po_number = ?", (new_status, po_st))
                    log_movement('STATUS', None, None, None, None, None, po_st, f'Estado → {new_status}')
                    st.success(t('ok_status', po=po_st, st=new_status))
                st.rerun()


# ===================== UI: CONSUMOS =====================
def render_consumos():
    st.markdown(f'<div class="section-title">{t("c_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-subtitle">{t("c_sub")}</div>', unsafe_allow_html=True)

    tab_map, tab_real, tab_edit = st.tabs([t('c_tab_map'), t('c_tab_real'), t('c_tab_edit')])

    with tab_map:
        cm_df = query_to_df("""
            SELECT cm.model_name, cm.fabric_ref, cm.m_per_pc_expected, cm.m_per_pc_actual
            FROM consumption_map cm ORDER BY cm.fabric_ref, cm.model_name
        """)
        if not cm_df.empty:
            st.markdown(f'<div style="display:flex;gap:24px;margin-bottom:12px;font-size:12px;color:var(--muted);"><span>{t("lg_exp")}</span><span>{t("lg_real")}</span><span>{t("lg_dev")}</span></div>', unsafe_allow_html=True)
            rows_html = ""
            for _, row in cm_df.iterrows():
                expected = row['m_per_pc_expected'] or 0
                actual = row['m_per_pc_actual'] or 0
                if expected > 0 and actual > 0:
                    dev = ((actual - expected) / expected) * 100
                    bar_width = min(100, max(50, (actual / expected) * 85))
                    bar_color = "#ef4444" if abs(dev) > 5 else "#22c55e"
                    var_class = "up" if dev > 0 else "down"
                    badge = '<span class="badge" style="background:rgba(239,68,68,0.15);color:#ef4444;">⚠️ desvio</span>' if abs(dev) > 5 else '<span class="badge available">ok</span>'
                    dev_txt = f"{dev:+.1f}%"
                    act_txt = f"{actual:.2f} m/pc"
                else:
                    bar_width, bar_color, var_class, dev_txt = 50, "#3b82f6", "", "—"
                    act_txt = t('c_nodata')
                    badge = '<span class="badge" style="background:rgba(100,116,139,0.15);color:var(--faint);">—</span>'
                rows_html += f"""
                <div class="consumo-row">
                    <div class="consumo-model">{row['model_name']}</div>
                    <div class="consumo-fabric">{row['fabric_ref']}</div>
                    <div class="consumo-val">{expected:.2f} m/pc</div>
                    <div class="consumo-bar-bg"><div class="consumo-bar-fill" style="width:{bar_width}%;background:{bar_color};"></div></div>
                    <div class="consumo-val">{act_txt}</div>
                    <div class="consumo-var {var_class}">{dev_txt}</div>
                    {badge}
                </div>"""
            st.markdown(rows_html, unsafe_allow_html=True)

    with tab_real:
        cons_df = query_to_df("SELECT * FROM consumptions ORDER BY date_cut DESC, id DESC")
        if not cons_df.empty:
            clean = safe_display_df(add_total_row(cons_df, exclude=['id', 'deviation_pct']))
            clean.columns = ['ID', t('c_po'), t('c_model'), t('c_pcs'), t('c_mexp'), t('c_mreal'), t('c_dev'), t('c_cutdate'), t('c_conf'), t('c_notes')]
            st.dataframe(clean, use_container_width=True, hide_index=True, height=400)
            n_high = cons_df[cons_df['deviation_pct'].fillna(0).abs() > 5].shape[0]
            if n_high:
                st.warning(t('c_high', n=n_high))
            download_pair(cons_df, f"consumos_{datetime.now().strftime('%Y%m%d')}", 'Consumos', 'cons_dl')
        else:
            st.info(t('c_none'))

    with tab_edit:
        st.markdown(f'<div class="section-subtitle">{t("c_edit_sub")}</div>', unsafe_allow_html=True)
        cm_edit = query_to_df("SELECT model_name, fabric_ref, m_per_pc_expected, m_per_pc_actual FROM consumption_map ORDER BY fabric_ref, model_name")
        edited = st.data_editor(
            cm_edit,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "model_name": st.column_config.TextColumn(t('c_model'), required=True),
                "fabric_ref": st.column_config.SelectboxColumn(t('c_fref'), options=[r[0] for r in FABRIC_REFS], required=True),
                "m_per_pc_expected": st.column_config.NumberColumn(t('ec_exp'), min_value=0.0, step=0.01, format="%.2f", required=True),
                "m_per_pc_actual": st.column_config.NumberColumn(t('ec_real'), min_value=0.0, step=0.01, format="%.3f"),
            },
            key="cm_editor"
        )
        if st.button(t('b_save_cm'), key="cm_save"):
            execute_sql("DELETE FROM consumption_map")
            rows = [(r['model_name'], r['fabric_ref'], r['m_per_pc_expected'], r['m_per_pc_actual'])
                    for _, r in edited.iterrows() if r['model_name'] and r['fabric_ref'] and r['m_per_pc_expected']]
            execute_many("INSERT OR REPLACE INTO consumption_map VALUES (?,?,?,?)", rows)
            st.success(t('ok_cm', n=len(rows)))
            st.rerun()


# ===================== UI: MOVEMENT (3 MODOS) =====================
def render_movement():
    st.markdown(f'<div class="section-title">{t("mv_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-subtitle">{t("mv_sub")}</div>', unsafe_allow_html=True)

    tab_rolls, tab_lot, tab_bulk, tab_recv, tab_inv = st.tabs([
        t('tab_m1'), t('tab_m2'), t('tab_m3'), t('tab_recv'), t('tab_inv')])

    # ---------- MODO 1: ROLOS CONHECIDOS ----------
    with tab_rolls:
        st.markdown(f'<div class="section-subtitle">{t("m1_sub")}</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            ref_opts = query_to_df("SELECT DISTINCT ref_code FROM fabric_rolls WHERE status = 'AVAILABLE' AND token LIKE 'R-%' ORDER BY ref_code")['ref_code'].tolist()
            m1_ref = st.selectbox(t('f_ref'), ref_opts, key="m1_ref")
        with c2:
            wh_opts = query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls WHERE ref_code = ? AND status = 'AVAILABLE' AND token LIKE 'R-%'", (m1_ref,))['warehouse'].tolist()
            m1_wh = st.selectbox(t('m1_wh'), wh_opts, key="m1_wh")

        rolls_avail = query_to_df("SELECT token, metres, color, lot FROM fabric_rolls WHERE ref_code = ? AND warehouse = ? AND status = 'AVAILABLE' AND token LIKE 'R-%' ORDER BY token", (m1_ref, m1_wh))
        if rolls_avail.empty:
            st.info(t('m1_none'))
        else:
            # ⚡ seleção rápida por remessa (todos os rolos da mesma remessa+cor de uma vez)
            lots_avail = rolls_avail[rolls_avail['lot'].notna() & (rolls_avail['lot'] != '')]
            if not lots_avail.empty:
                lot_opts = lots_avail.groupby('lot').agg(n=('token', 'count'), m=('metres', 'sum'), cor=('color', 'first')).reset_index()
                sel_lots = st.multiselect(
                    t('m1_lots'), lot_opts['lot'].tolist(), key='m1_lots',
                    format_func=lambda l: f"{color_dot(lot_opts[lot_opts['lot']==l].iloc[0]['cor'])} {l} · "
                                          f"{lot_opts[lot_opts['lot']==l].iloc[0]['cor'] or 's/cor'} · "
                                          f"{lot_opts[lot_opts['lot']==l].iloc[0]['m']:.1f}m "
                                          f"({int(lot_opts[lot_opts['lot']==l].iloc[0]['n'])} rolos)")
                if st.button(t('b_picklots'), key='m1_picklots'):
                    st.session_state['m1_tokens'] = rolls_avail[rolls_avail['lot'].isin(sel_lots)]['token'].tolist()
                    st.rerun()
            sel_tokens = st.multiselect(
                t('m1_rolls'),
                rolls_avail['token'].tolist(),
                format_func=lambda t: f"{color_dot(rolls_avail[rolls_avail['token']==t].iloc[0]['color'])} "
                                      f"{rolls_avail[rolls_avail['token']==t].iloc[0]['color'] if rolls_avail[rolls_avail['token']==t].iloc[0]['color'] else 's/cor'}"
                                      f" · {rolls_avail[rolls_avail['token']==t].iloc[0]['metres']:.1f}m — {t}",
                key="m1_tokens")
            total_sel = rolls_avail[rolls_avail['token'].isin(sel_tokens)]['metres'].sum()
            st.markdown(f'<div class="section-subtitle">{t("m1_count", n=len(sel_tokens), m=f"{total_sel:,.1f}")}</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                m1_to = st.selectbox(t('m1_to'), [l for l in ALL_LOCATIONS if l != m1_wh], key="m1_to")
            with c2:
                m1_status = st.selectbox(t('m1_status'), ['AVAILABLE', 'IN_PROCESS'],
                                         format_func=lambda s: t('st_avail_wh') if s == 'AVAILABLE' else t('st_inproc_conf'),
                                         key="m1_status")

            if st.button(t('b_m1'), key="m1_go"):
                if not sel_tokens:
                    st.error(t('err_m1'))
                else:
                    for t in sel_tokens:
                        execute_sql("UPDATE fabric_rolls SET warehouse = ?, status = ?, date_last_move = ? WHERE token = ?",
                                    (m1_to, m1_status, datetime.now().isoformat(), t))
                        m_val = rolls_avail[rolls_avail['token'] == t].iloc[0]['metres']
                        c_val = rolls_avail[rolls_avail['token'] == t].iloc[0]['color']
                        log_movement('TRANSFER', t, m1_wh, m1_to, m1_ref, m_val, None, f'Rolo movido ({m1_status})', c_val)
                    st.success(t('ok_m1', n=len(sel_tokens), m=f"{total_sel:,.1f}", a=m1_wh, b=m1_to))
                    st.rerun()

    # ---------- MODO 2: LOTE AGREGADO ----------
    with tab_lot:
        st.markdown(f'<div class="section-subtitle">{t("m2_sub")}</div>', unsafe_allow_html=True)
        lots = query_to_df("SELECT token, ref_code, metres, color, warehouse, status FROM fabric_rolls WHERE token LIKE 'P-%' AND status != 'INVOICED' ORDER BY warehouse, ref_code")
        if lots.empty:
            st.info(t('m2_none'))
        else:
            lot_sel = st.selectbox(t('m2_lot'), lots['token'].tolist(), key="m2_lot",
                                   format_func=lambda t: f"{color_dot(lots[lots['token']==t].iloc[0]['color'])} "
                                                         f"{lots[lots['token']==t].iloc[0]['ref_code']}"
                                                         f" · {lots[lots['token']==t].iloc[0]['color'] if lots[lots['token']==t].iloc[0]['color'] else 's/cor'}"
                                                         f" · {lots[lots['token']==t].iloc[0]['metres']:,.1f}m"
                                                         f" @ {lots[lots['token']==t].iloc[0]['warehouse']} — {t}")
            lot_row = lots[lots['token'] == lot_sel].iloc[0]

            c1, c2, c3 = st.columns(3)
            with c1:
                m2_metres = st.number_input(t('m2_metres'), min_value=0.0, max_value=float(lot_row['metres']),
                                            value=float(lot_row['metres']), step=0.1, key="m2_metres")
            with c2:
                m2_to = st.selectbox(t('m1_to'), [l for l in ALL_LOCATIONS if l != lot_row['warehouse']], key="m2_to")
            with c3:
                m2_status = st.selectbox(t('m1_status'), ['AVAILABLE', 'IN_PROCESS'],
                                         format_func=lambda s: t('st_avail_wh') if s == 'AVAILABLE' else t('st_inproc_conf'),
                                         key="m2_status")

            partial = 0 < m2_metres < lot_row['metres']
            if partial:
                st.info(t('m2_split', rest=f"{lot_row['metres'] - m2_metres:,.1f}", m=f"{m2_metres:,.1f}", to=m2_to))

            if st.button(t('b_m2'), key="m2_go"):
                if m2_metres <= 0:
                    st.error(t('err_m2'))
                else:
                    if partial:
                        # Divide: reduz original, cria novo lote no destino
                        execute_sql("UPDATE fabric_rolls SET metres = metres - ?, date_last_move = ? WHERE token = ?",
                                    (m2_metres, datetime.now().isoformat(), lot_sel))
                        new_tok = next_token('P', lot_row['ref_code'])
                        execute_sql("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                    (new_tok, lot_row['ref_code'], m2_metres, None, lot_row['color'], m2_to, m2_status, None,
                                     datetime.now().isoformat(), datetime.now().isoformat(), f'Dividido de {lot_sel}'))
                        log_movement('SPLIT', new_tok, lot_row['warehouse'], m2_to, lot_row['ref_code'], m2_metres, None,
                                     f'Divisão de {lot_sel} ({m2_metres:.1f}m)', lot_row['color'])
                        st.success(t('ok_m2_split', m=f"{m2_metres:,.1f}", tok=new_tok, to=m2_to))
                    else:
                        execute_sql("UPDATE fabric_rolls SET warehouse = ?, status = ?, date_last_move = ? WHERE token = ?",
                                    (m2_to, m2_status, datetime.now().isoformat(), lot_sel))
                        log_movement('TRANSFER', lot_sel, lot_row['warehouse'], m2_to, lot_row['ref_code'], m2_metres, None, 'Lote movido total', lot_row['color'])
                        st.success(t('ok_m2', tok=lot_sel, m=f"{m2_metres:,.1f}", to=m2_to))
                    st.rerun()

    # ---------- MODO 3: METROS CONSOLIDADOS ----------
    with tab_bulk:
        st.markdown(f'<div class="section-subtitle">{t("m3_sub")}</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            m3_ref = st.selectbox(t('f_ref'), query_to_df("SELECT DISTINCT ref_code FROM fabric_rolls WHERE status = 'AVAILABLE' AND token LIKE 'R-%' ORDER BY ref_code")['ref_code'].tolist(), key="m3_ref")
        with c2:
            m3_wh = st.selectbox(t('m1_wh'), query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls WHERE ref_code = ? AND status = 'AVAILABLE' AND token LIKE 'R-%'", (m3_ref,))['warehouse'].tolist(), key="m3_wh")

        avail = query_to_df("SELECT COALESCE(SUM(metres),0) as m FROM fabric_rolls WHERE ref_code = ? AND warehouse = ? AND status = 'AVAILABLE' AND token LIKE 'R-%'", (m3_ref, m3_wh)).iloc[0]['m']
        st.markdown(f'<div class="section-subtitle">{t("m3_avail", wh=m3_wh, m=f"{avail:,.1f}")}</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            m3_metres = st.number_input(t('m2_metres'), min_value=0.0, max_value=float(avail), step=0.1, key="m3_metres")
        with c2:
            m3_to = st.selectbox(t('m1_to'), [l for l in ALL_LOCATIONS if l != m3_wh], key="m3_to")

        m3_po = st.text_input(t('m3_po'), key="m3_po")

        if st.button(t('b_m3'), key="m3_go"):
            if m3_metres <= 0 or m3_metres > avail:
                st.error(t('err_m3', m=f"{avail:,.1f}"))
            else:
                dest_status = 'IN_PROCESS' if m3_to in CONFECCIONADORES else 'AVAILABLE'
                # Cria lote no destino
                new_tok = next_token('P' if dest_status == 'IN_PROCESS' else 'R', m3_ref)
                execute_sql("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (new_tok, m3_ref, m3_metres, None, None, m3_to, dest_status, m3_po or None,
                             datetime.now().isoformat(), datetime.now().isoformat(), f'Consolidado de {m3_wh}'))
                # Retira FIFO dos rolos de origem
                remaining = m3_metres
                src = query_to_df("SELECT token, metres FROM fabric_rolls WHERE ref_code = ? AND warehouse = ? AND status = 'AVAILABLE' AND token LIKE 'R-%' ORDER BY date_received, token", (m3_ref, m3_wh))
                for _, r in src.iterrows():
                    if remaining <= 0:
                        break
                    if r['metres'] <= remaining:
                        execute_sql("UPDATE fabric_rolls SET metres = 0, status = 'INVOICED', notes = ?, date_last_move = ? WHERE token = ?",
                                    (f'Consumido em {new_tok}', datetime.now().isoformat(), r['token']))
                        remaining -= r['metres']
                    else:
                        execute_sql("UPDATE fabric_rolls SET metres = metres - ?, date_last_move = ? WHERE token = ?",
                                    (remaining, datetime.now().isoformat(), r['token']))
                        remaining = 0
                log_movement('CONSOLIDATE', new_tok, m3_wh, m3_to, m3_ref, m3_metres, m3_po or None, f'{m3_metres:.1f}m consolidados (FIFO)')
                st.success(t('ok_m3', m=f"{m3_metres:,.1f}", a=m3_wh, b=m3_to, tok=new_tok))
                st.rerun()

    # ---------- RECEÇÃO ----------
    with tab_recv:
        st.markdown(f"<div class='info-card'><div class='info-card-title'>{t('recv_title')}</div><div class='info-card-text'>{t('recv_text')}</div></div>", unsafe_allow_html=True)

        refs = query_to_df("SELECT ref_code FROM fabric_refs ORDER BY ref_code")['ref_code'].tolist()
        c1, c2, c3 = st.columns(3)
        with c1:
            recv_ref = st.selectbox(t('f_ref'), refs, key="recv_ref")
        with c2:
            recv_metres = st.number_input(t('f_recv_metres'), min_value=0.0, step=0.01, key="recv_metres")
        with c3:
            recv_wh = st.selectbox(t('f_recv_wh'), WAREHOUSES, key="recv_wh")

        c1, c2 = st.columns(2)
        with c1:
            recv_lot = st.text_input(t('f_recv_lot'), placeholder="L2026-B", key="recv_lot")
        with c2:
            existing_colors = query_to_df("SELECT DISTINCT color FROM fabric_rolls WHERE ref_code = ? AND color IS NOT NULL AND color != '' ORDER BY color", (recv_ref,))['color'].tolist()
            recv_color_sel = st.selectbox(t('f_color'), existing_colors + [t('f_new_color')],
                                          format_func=lambda c: color_badge(c) if c != '➕ Nova cor…' else c,
                                          key="recv_color_sel")
            if recv_color_sel == t('f_new_color'):
                recv_color = st.text_input(t('f_type_color'), placeholder="Dark Navy", key="recv_color_new")
            else:
                recv_color = recv_color_sel

        if st.button(t('b_recv'), key="confirm_recv"):
            if recv_metres > 0:
                token = next_token('R', recv_ref)
                execute_sql("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (token, recv_ref, recv_metres, recv_lot or None, recv_color or None, recv_wh, 'AVAILABLE', None,
                             datetime.now().isoformat(), datetime.now().isoformat(), None))
                log_movement('RECEIPT', token, 'Fornecedor', recv_wh, recv_ref, recv_metres, None,
                             f'Receção lote {recv_lot}' if recv_lot else 'Receção', recv_color or None)
                st.success(t('ok_recv', tok=token, m=f"{recv_metres:,.1f}"))
                st.rerun()
            else:
                st.error(t('err_metres'))

    # ---------- FATURAÇÃO ----------
    with tab_inv:
        st.markdown(f"<div class='info-card'><div class='info-card-title'>{t('inv_title')}</div><div class='info-card-text'>{t('inv_text')}</div></div>", unsafe_allow_html=True)

        pend_pos = query_to_df("SELECT po_number, model_name, confeccionador FROM production WHERE status != 'INVOICED' ORDER BY po_number DESC")
        if pend_pos.empty:
            st.info(t('inv_none'))
        else:
            invoice_po = st.selectbox(t('inv_po'), pend_pos['po_number'].tolist(), key="invoice_po",
                                      format_func=lambda p: f"{p} — {pend_pos[pend_pos['po_number']==p].iloc[0]['model_name'][:45]}")
            inv_m = query_to_df("SELECT COALESCE(SUM(metres),0) as m FROM fabric_rolls WHERE po_garment = ? AND status = 'IN_PROCESS'", (invoice_po,)).iloc[0]['m']
            if inv_m > 0:
                st.info(t('inv_m', m=f"{inv_m:,.1f}"))
            else:
                st.warning(t('inv_no_m'))

            if st.button(t('b_inv'), key="confirm_invoice"):
                execute_sql("UPDATE fabric_rolls SET status = 'INVOICED', notes = 'Faturado — saiu de em processo' WHERE po_garment = ? AND status = 'IN_PROCESS'", (invoice_po,))
                execute_sql("UPDATE production SET status = 'INVOICED' WHERE po_number = ?", (invoice_po,))
                log_movement('INVOICE', None, 'Em Processo', 'Faturado', None, inv_m, invoice_po, f'{inv_m:.1f}m faturados')
                st.success(t('ok_inv2', po=invoice_po, m=f"{inv_m:,.1f}"))
                st.rerun()

    # Regras
    st.markdown(f'<div class="section-title">{t("rules")}</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="info-card">
            <div class="info-card-title">{t('rule_new')}</div>
            <div class="info-card-text">{t('rule_new_txt')}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="info-card">
            <div class="info-card-title">{t('rule_conf')}</div>
            <div class="info-card-text">{t('rule_conf_txt')}</div>
        </div>
        """, unsafe_allow_html=True)

    # Histórico
    st.markdown(f'<div class="section-title">{t("hist")}</div>', unsafe_allow_html=True)
    hist_df = query_to_df("SELECT date_time, move_type, from_location, to_location, ref_code, color, metres, po_garment, notes, token FROM movements ORDER BY date_time DESC LIMIT 20")
    if not hist_df.empty:
        clean = safe_display_df(add_total_row(hist_df))
        clean.columns = [t('c_dt'), t('c_type'), t('c_from'), t('c_to'), t('c_ref'), t('c_color'), t('c_metres'), 'PO', t('c_notes'), t('c_token')]
        clean = apply_color_badges(clean, 'Cor')
        st.dataframe(clean, use_container_width=True, hide_index=True)
    else:
        st.info(t('mv_none'))


# ===================== UI: TRACE =====================
def render_trace():
    st.markdown(f'<div class="section-title">{t("tr_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-subtitle">{t("tr_sub")}</div>', unsafe_allow_html=True)

    search = st.text_input(t('tr_search'), placeholder="ex: R-TCB258_EC1-001 · P-Samidel-GB14W-001 · POAPS2000004404", key="trace_search")

    if search:
        token_df = query_to_df("SELECT * FROM fabric_rolls WHERE token = ?", (search,))
        if not token_df.empty:
            row = token_df.iloc[0]
            status_badge = {'AVAILABLE': 'available', 'RESERVED': 'reserved', 'IN_PROCESS': 'inprocess', 'INVOICED': 'invoiced'}.get(row['status'], '')

            st.markdown(f"""
            <div class="trace-card">
                <div style="color:var(--text);font-size:16px;font-weight:600;margin-bottom:10px;">{color_dot(row['color'])} {row['ref_code']} · {row['color'] or 's/cor'}</div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                    <div class="trace-token">{row['token']}</div>
                    <span class="badge {status_badge}">{row['status']}</span>
                </div>
                <div class="trace-details">
                    <div><div class="trace-detail-label">{t('tl_ref')}</div><div class="trace-detail-value">{row['ref_code']}</div></div>
                    <div><div class="trace-detail-label">{t('tl_metres')}</div><div class="trace-detail-value">{row['metres']:.2f}m</div></div>
                    <div><div class="trace-detail-label">{t('tl_lot')}</div><div class="trace-detail-value">{row['lot'] or '—'}</div></div>
                    <div><div class="trace-detail-label">{t('tl_color')}</div><div class="trace-detail-value">{row['color'] or '—'}</div></div>
                    <div><div class="trace-detail-label">{t('tl_loc')}</div><div class="trace-detail-value">{row['warehouse']}</div></div>
                    <div><div class="trace-detail-label">{t('c_po')}</div><div class="trace-detail-value">{row['po_garment'] or '—'}</div></div>
                    <div><div class="trace-detail-label">{t('tl_recv')}</div><div class="trace-detail-value">{str(row['date_received'])[:10] if row['date_received'] else '—'}</div></div>
                    <div><div class="trace-detail-label">{t('tl_last')}</div><div class="trace-detail-value">{str(row['date_last_move'])[:10] if row['date_last_move'] else '—'}</div></div>
                </div>
                {f'<div style="margin-top:12px;padding:10px;border-radius:8px;background:rgba(245,158,11,0.1);color:#f59e0b;font-size:12px;">📝 {row["notes"]}</div>' if row['notes'] else ''}
            </div>
            """, unsafe_allow_html=True)

            hist_df = query_to_df("SELECT date_time, move_type, from_location, to_location, ref_code, color, metres, po_garment, notes, token FROM movements WHERE token = ? OR po_garment = ? ORDER BY date_time DESC", (search, search))
            if not hist_df.empty:
                st.markdown(f'<div class="section-title">{t("tr_hist")}</div>', unsafe_allow_html=True)
                clean = safe_display_df(add_total_row(hist_df))
                clean.columns = [t('c_dt'), t('c_type'), t('c_from'), t('c_to'), t('c_ref'), t('c_color'), t('c_metres'), 'PO', t('c_notes'), t('c_token')]
                clean = apply_color_badges(clean, 'Cor')
                st.dataframe(clean, use_container_width=True, hide_index=True, height=250)
        else:
            po_df = query_to_df("SELECT * FROM production WHERE po_number = ?", (search,))
            if not po_df.empty:
                st.markdown(f'<div class="section-title">PO: {search}</div>', unsafe_allow_html=True)
                st.dataframe(safe_display_df(po_df), use_container_width=True, hide_index=True)

                cons_df = query_to_df("SELECT * FROM consumptions WHERE po_garment = ?", (search,))
                if not cons_df.empty:
                    st.markdown(f'<div class="section-title">{t("tr_cons")}</div>', unsafe_allow_html=True)
                    st.dataframe(safe_display_df(add_total_row(cons_df, exclude=['id', 'deviation_pct'])), use_container_width=True, hide_index=True)

                roll_df = query_to_df("""SELECT fr.supplier, r.ref_code, r.color, r.metres, r.warehouse, r.status, r.token
                                         FROM fabric_rolls r LEFT JOIN fabric_refs fr ON r.ref_code = fr.ref_code
                                         WHERE r.po_garment = ?""", (search,))
                if not roll_df.empty:
                    st.markdown(f'<div class="section-title">{t("tr_rolls")}</div>', unsafe_allow_html=True)
                    clean = safe_display_df(add_total_row(roll_df))
                    clean.columns = [t('c_supplier'), t('c_ref'), t('c_color'), t('c_metres'), t('c_loc'), t('c_status'), t('c_token')]
                    clean = apply_color_badges(clean, 'Cor')
                    st.dataframe(clean, use_container_width=True, hide_index=True)

                mov_df = query_to_df("SELECT date_time, move_type, from_location, to_location, ref_code, color, metres, notes, token FROM movements WHERE po_garment = ? ORDER BY date_time DESC", (search,))
                if not mov_df.empty:
                    st.markdown(f'<div class="section-title">{t("tr_movs")}</div>', unsafe_allow_html=True)
                    clean = safe_display_df(add_total_row(mov_df))
                    clean.columns = [t('c_dt'), t('c_type'), t('c_from'), t('c_to'), t('c_ref'), t('c_color'), t('c_metres'), t('c_notes'), t('c_token')]
                    clean = apply_color_badges(clean, 'Cor')
                    st.dataframe(clean, use_container_width=True, hide_index=True)
            else:
                st.warning(t('tr_notfound'))


# ===================== UI: EXPORT =====================
def render_export():
    st.markdown(f'<div class="section-title">{t("ex_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-subtitle">{t("ex_sub")}</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="info-card" style="text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">📊</div>
            <div class="info-card-title">{t('ex_sum')}</div>
            <div class="info-card-text">{t('ex_sum_d')}</div>
        </div>
        """, unsafe_allow_html=True)
        df = add_total_row(get_stock_position(), exclude=['cores'])
        download_pair(df, f"stock_resumido_{datetime.now().strftime('%Y%m%d')}", 'Stock Resumido', 'exp_sum')

    with col2:
        st.markdown(f"""
        <div class="info-card" style="text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">📋</div>
            <div class="info-card-title">{t('ex_det')}</div>
            <div class="info-card-text">{t('ex_det_d')}</div>
        </div>
        """, unsafe_allow_html=True)
        df2 = query_to_df("""SELECT fr.supplier, r.ref_code, r.color, r.metres, r.lot, r.warehouse, r.status, r.po_garment, r.date_last_move, r.notes, r.token
                             FROM fabric_rolls r LEFT JOIN fabric_refs fr ON r.ref_code = fr.ref_code
                             WHERE r.status != 'INVOICED' ORDER BY r.ref_code, r.token""")
        download_pair(add_total_row(df2), f"stock_detalhado_{datetime.now().strftime('%Y%m%d')}", 'Stock Detalhado', 'exp_det')

    with col3:
        st.markdown(f"""
        <div class="info-card" style="text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">📈</div>
            <div class="info-card-title">{t('ex_cons')}</div>
            <div class="info-card-text">{t('ex_cons_d')}</div>
        </div>
        """, unsafe_allow_html=True)
        df3 = query_to_df("SELECT * FROM consumptions ORDER BY date_cut DESC")
        download_pair(add_total_row(df3, exclude=['id', 'deviation_pct']), f"consumos_{datetime.now().strftime('%Y%m%d')}", 'Consumos', 'exp_cons')
        df4 = query_to_df("SELECT * FROM movements WHERE date_time >= ? ORDER BY date_time DESC",
                          ((datetime.now().replace(day=1)).isoformat(),))
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        download_pair(add_total_row(df4, exclude=['id']), f"movimentos_mes_{datetime.now().strftime('%Y%m')}", 'Movimentos', 'exp_mov')


# ===================== UI: FERRAMENTAS =====================
def render_tools():
    tab_tr, tab_ex = st.tabs([t('tr_title'), t('ex_title')])
    with tab_tr:
        render_trace()
    with tab_ex:
        render_export()


# ===================== MAIN =====================
def main():
    st.sidebar.markdown(f"""
    <div style="padding:16px 0 24px 0;text-align:center;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:16px;">
        <div style="font-size:28px;margin-bottom:4px;">🏭</div>
        <div style="color:var(--text);font-size:16px;font-weight:700;">SNT CMT</div>
        <div style="color:var(--faint);font-size:11px;">{t('sb_system')}</div>
        <div style="margin-top:8px;display:inline-flex;align-items:center;gap:4px;background:rgba(34,197,94,0.1);color:#22c55e;padding:3px 10px;border-radius:12px;font-size:10px;font-weight:600;">
            <span style="width:5px;height:5px;background:#22c55e;border-radius:50%;display:inline-block;"></span> LIVE
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Seletores de idioma e tema
    lc1, lc2 = st.sidebar.columns(2)
    with lc1:
        st.selectbox(t('sb_lang'), ['pt', 'en'],
                     format_func=lambda x: '🇵🇹 PT' if x == 'pt' else '🇬🇧 EN',
                     key='lang', label_visibility='collapsed')
    with lc2:
        st.selectbox(t('sb_theme'), ['dark', 'clean'],
                     format_func=lambda x: '🌙 Dark' if x == 'dark' else '☀️ Clean',
                     key='theme', label_visibility='collapsed')

    tabs = {
        t('m_dashboard'): render_dashboard,
        t('m_stock'): render_stock,
        t('m_incoming'): render_incoming,
        t('m_production'): render_production,
        t('m_consumos'): render_consumos,
        t('m_movement'): render_movement,
        t('m_tools'): render_tools,
    }

    selection = st.sidebar.radio(t('sb_nav'), list(tabs.keys()), label_visibility="collapsed")

    st.sidebar.markdown(f"""
    <div style="position:fixed;bottom:20px;left:20px;right:20px;">
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:12px;color:var(--faint);font-size:11px;text-align:center;">
            v3.7 | {t('sb_data')}<br>{datetime.now().strftime('%Y-%m-%d')}<br>
            <span style="color:#3b82f6;font-weight:600;">SNT CMT</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs[selection]()

if __name__ == "__main__":
    main()
