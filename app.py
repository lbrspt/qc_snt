"""
SNT CMT - Sistema de Stock & Produção v3.3
Dados reais CW29 2026
Novidades v3.3:
- Modo LIVE na Produção: lançar consumo de corte em tempo real com validação de desvios
- Movimentação em 3 modos: rolos conhecidos, lote agregado (divisível), metros consolidados
- Edição live: mapa de consumos e pontos de reposição editáveis na grelha
- Exportação Excel + CSV
- Dados corrigidos: linhas TOTAL removidas, refs em processo normalizadas (ref + cor)
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

# ===================== CUSTOM CSS (Pro Design) =====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Dark theme base */
    .stApp { background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%); }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
        padding: 20px 30px;
        border-radius: 16px;
        margin-bottom: 24px;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .main-header h1 { color: #e0e6ed; margin: 0; font-size: 28px; font-weight: 700; }
    .main-header p { color: #8b9dc3; margin: 4px 0 0 0; font-size: 13px; }
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
        background: linear-gradient(145deg, rgba(30,58,95,0.6) 0%, rgba(13,33,55,0.8) 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px; padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.3); }
    .kpi-label { color: #8b9dc3; font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
    .kpi-value { color: #e0e6ed; font-size: 32px; font-weight: 700; margin-bottom: 6px; }
    .kpi-delta { font-size: 12px; font-weight: 500; }
    .kpi-delta.up { color: #22c55e; }
    .kpi-delta.down { color: #ef4444; }
    .kpi-delta.warn { color: #f59e0b; }
    .kpi-delta.info { color: #3b82f6; }

    /* Section titles */
    .section-title {
        color: #e0e6ed; font-size: 16px; font-weight: 600;
        margin: 24px 0 12px 0; padding-bottom: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .section-subtitle { color: #8b9dc3; font-size: 12px; margin-bottom: 16px; }

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
    .stDataFrame thead th { background: #1e3a5f !important; color: #e0e6ed !important; font-weight: 600 !important; font-size: 12px !important; }
    .stDataFrame tbody td { background: rgba(30,58,95,0.3) !important; color: #c4d0e4 !important; font-size: 12px !important; border-bottom: 1px solid rgba(255,255,255,0.03) !important; }
    .stDataFrame tbody tr:hover td { background: rgba(30,58,95,0.5) !important; }

    /* Cards */
    .info-card {
        background: linear-gradient(145deg, rgba(30,58,95,0.4) 0%, rgba(13,33,55,0.6) 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px; padding: 16px;
        margin-bottom: 12px;
    }
    .info-card-title { color: #e0e6ed; font-size: 13px; font-weight: 600; margin-bottom: 8px; }
    .info-card-text { color: #8b9dc3; font-size: 12px; line-height: 1.6; }

    /* Form styling */
    .stSelectbox > div > div { background: rgba(30,58,95,0.4) !important; border-color: rgba(255,255,255,0.1) !important; border-radius: 10px !important; }
    .stNumberInput > div > div > div { background: rgba(30,58,95,0.4) !important; border-color: rgba(255,255,255,0.1) !important; border-radius: 10px !important; }
    .stTextInput > div > div > input { background: rgba(30,58,95,0.4) !important; border-color: rgba(255,255,255,0.1) !important; border-radius: 10px !important; color: #e0e6ed !important; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important; border: none !important; border-radius: 10px !important;
        padding: 8px 20px !important; font-weight: 600 !important; font-size: 13px !important;
        box-shadow: 0 4px 15px rgba(37,99,235,0.3) !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(37,99,235,0.4) !important; }
    .stButton > button[kind="secondary"] { background: rgba(255,255,255,0.08) !important; color: #8b9dc3 !important; box-shadow: none !important; }

    /* Sidebar */
    .css-1d391kg, .css-1lcbmhc { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important; }
    .stSidebar .stRadio > div { background: transparent !important; }
    .stSidebar .stRadio label { color: #8b9dc3 !important; font-size: 13px !important; padding: 8px 12px !important; border-radius: 8px !important; transition: all 0.2s !important; }
    .stSidebar .stRadio label:hover { background: rgba(255,255,255,0.05) !important; color: #e0e6ed !important; }
    .stSidebar .stRadio [aria-checked="true"] + label { background: rgba(37,99,235,0.2) !important; color: #60a5fa !important; font-weight: 600 !important; border-left: 3px solid #2563eb !important; }

    /* Timeline */
    .timeline { position: relative; padding-left: 24px; }
    .timeline::before { content: ''; position: absolute; left: 7px; top: 0; bottom: 0; width: 2px; background: rgba(255,255,255,0.1); }
    .timeline-item { position: relative; padding: 12px 0; }
    .timeline-item::before { content: ''; position: absolute; left: -21px; top: 16px; width: 10px; height: 10px; border-radius: 50%; }
    .timeline-item.completed::before { background: #22c55e; }
    .timeline-item.warning::before { background: #f59e0b; }
    .timeline-item.pending::before { background: #3b82f6; }
    .timeline-date { color: #8b9dc3; font-size: 11px; font-weight: 600; }
    .timeline-text { color: #e0e6ed; font-size: 13px; margin-top: 2px; }
    .timeline-meta { color: #64748b; font-size: 11px; margin-top: 2px; }

    /* Consumo bars */
    .consumo-row { display: flex; align-items: center; gap: 16px; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
    .consumo-model { flex: 2; color: #e0e6ed; font-size: 13px; font-weight: 500; }
    .consumo-fabric { flex: 1; color: #8b9dc3; font-size: 12px; }
    .consumo-val { flex: 0.8; color: #8b9dc3; font-size: 12px; text-align: right; }
    .consumo-bar-bg { flex: 1.5; height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; }
    .consumo-bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
    .consumo-var { flex: 0.6; font-size: 12px; font-weight: 600; text-align: right; }
    .consumo-var.up { color: #ef4444; }
    .consumo-var.down { color: #22c55e; }

    /* Warehouse cards */
    .wh-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
    .wh-card {
        background: linear-gradient(145deg, rgba(30,58,95,0.4) 0%, rgba(13,33,55,0.6) 100%);
        border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        transition: all 0.2s;
    }
    .wh-card:hover { border-color: rgba(255,255,255,0.12); box-shadow: 0 8px 30px rgba(0,0,0,0.25); }
    .wh-name { color: #e0e6ed; font-size: 14px; font-weight: 600; margin-bottom: 8px; }
    .wh-total { color: #60a5fa; font-size: 28px; font-weight: 700; margin-bottom: 4px; }
    .wh-detail { color: #8b9dc3; font-size: 11px; line-height: 1.5; margin-bottom: 8px; }
    .wh-rolls { color: #64748b; font-size: 11px; }

    /* Trace card */
    .trace-card {
        background: linear-gradient(145deg, rgba(30,58,95,0.4) 0%, rgba(13,33,55,0.6) 100%);
        border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 20px;
        margin-bottom: 16px;
    }
    .trace-token {
        display: inline-block; background: rgba(37,99,235,0.15); color: #60a5fa;
        padding: 4px 12px; border-radius: 8px; font-size: 13px; font-weight: 600;
        font-family: 'SF Mono', monospace; border: 1px solid rgba(37,99,235,0.2);
    }
    .trace-details { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 16px 0; }
    .trace-detail-label { color: #64748b; font-size: 11px; text-transform: uppercase; }
    .trace-detail-value { color: #e0e6ed; font-size: 14px; font-weight: 600; margin-top: 4px; }

    /* Live deviation indicator */
    .dev-box { border-radius: 12px; padding: 16px; text-align: center; margin: 12px 0; }
    .dev-box.ok { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); }
    .dev-box.warn { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); }
    .dev-box.bad { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); }
    .dev-value { font-size: 28px; font-weight: 700; }
    .dev-label { font-size: 11px; color: #8b9dc3; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: rgba(30,58,95,0.3) !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; }
    .stTabs [data-baseweb="tab"] { color: #8b9dc3 !important; font-size: 13px !important; border-radius: 8px !important; padding: 8px 16px !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: rgba(37,99,235,0.2) !important; color: #60a5fa !important; font-weight: 600 !important; }

    /* Badges */
    .badge {
        display: inline-flex; align-items: center; padding: 3px 10px;
        border-radius: 6px; font-size: 11px; font-weight: 600;
    }
    .badge.available { background: rgba(34,197,94,0.15); color: #22c55e; }
    .badge.reserved { background: rgba(245,158,11,0.15); color: #f59e0b; }
    .badge.inprocess { background: rgba(59,130,246,0.15); color: #3b82f6; }
    .badge.invoiced { background: rgba(100,116,139,0.15); color: #64748b; }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: rgba(30,58,95,0.2); }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.25); }
</style>
""", unsafe_allow_html=True)

# ===================== DB SETUP =====================
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "snt_cmt_v33.db")

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

def log_movement(move_type, token, from_loc, to_loc, ref_code, metres, po_garment=None, notes=None):
    execute_sql(
        "INSERT INTO movements (date_time, move_type, token, from_location, to_location, ref_code, metres, po_garment, notes) VALUES (?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(), move_type, token, from_loc, to_loc, ref_code, metres, po_garment, notes))

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
PROD_STATUSES = ['PENDING', 'CUTTING', 'SEWING', 'INVOICED']
ROLL_STATUSES = ['AVAILABLE', 'RESERVED', 'IN_PROCESS', 'INVOICED']


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
    ('POAPS2000004273', 'Timeless Wool Blazer Dark Brown Check', 'Tyrrell', 209, None, 292.60, '2026-07-31', 'PENDING'),
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
    ('R-TCB258_EC1-001', 'TCB258/EC1', 28.71, None, 'XBS'),
    ('R-TCB258_EC1-002', 'TCB258/EC1', 26.11, None, 'XBS'),
    ('R-TCB258_EC1-004', 'TCB258/EC1', 33.18, None, 'XBS'),
    ('R-TCB258_EC1-006', 'TCB258/EC1', 52.33, None, 'XBS'),
    ('R-TCB258_EC1-007', 'TCB258/EC1', 54.71, None, 'XBS'),
    ('R-TCB258_EC1-008', 'TCB258/EC1', 46.46, None, 'XBS'),
    ('R-TCB258_EC1-009', 'TCB258/EC1', 47.06, None, 'XBS'),
    ('R-TCB258_EC1-010', 'TCB258/EC1', 47.08, None, 'XBS'),
    ('R-TCB258_EC1-011', 'TCB258/EC1', 51.79, None, 'XBS'),
    ('R-TCB258_EC1-012', 'TCB258/EC1', 52.80, None, 'XBS'),
    ('R-TCB258_EC1-013', 'TCB258/EC1', 52.25, None, 'XBS'),
    ('R-TCB258_EC1-014', 'TCB258/EC1', 52.82, None, 'XBS'),
    ('R-TCB258_EC1-015', 'TCB258/EC1', 41.01, None, 'XBS'),
    ('R-TCB258_EC1-016', 'TCB258/EC1', 59.78, None, 'XBS'),
    ('R-TCB258_EC1-017', 'TCB258/EC1', 64.93, None, 'XBS'),
    ('R-TCB258_EC1-018', 'TCB258/EC1', 42.90, None, 'XBS'),
    ('R-TCB258_EC1-019', 'TCB258/EC1', 42.69, None, 'XBS'),
    ('R-TCB258_EC1-020', 'TCB258/EC1', 54.14, None, 'XBS'),
    ('R-TCB258_EC1-021', 'TCB258/EC1', 51.11, None, 'XBS'),
    ('R-TCB258_EC1-022', 'TCB258/EC1', 62.18, None, 'XBS'),
    ('R-TCB258_EC1-023', 'TCB258/EC1', 33.66, None, 'XBS'),
    ('R-TCB258_EC1-024', 'TCB258/EC1', 42.92, None, 'XBS'),
    ('R-TCB258_EC1-025', 'TCB258/EC1', 54.38, None, 'XBS'),
    ('R-TCB258_EC1-026', 'TCB258/EC1', 54.72, None, 'XBS'),
    ('R-TCB258_EC1-027', 'TCB258/EC1', 54.81, None, 'XBS'),
    ('R-TCB258_EC1-028', 'TCB258/EC1', 52.63, None, 'XBS'),
    ('R-TCB258_EC1-029', 'TCB258/EC1', 45.85, None, 'XBS'),
    ('R-TCB258_EC1-030', 'TCB258/EC1', 48.72, None, 'XBS'),
    ('R-TCB258_EC1-031', 'TCB258/EC1', 46.38, None, 'XBS'),
    ('R-TCB258_EC1-032', 'TCB258/EC1', 54.03, None, 'XBS'),
    ('R-TCB258_EC1-033', 'TCB258/EC1', 54.04, None, 'XBS'),
    ('R-TCB258_EC1-034', 'TCB258/EC1', 54.34, None, 'XBS'),
    ('R-TCB258_EC1-035', 'TCB258/EC1', 54.47, None, 'XBS'),
    ('R-TCB258_EC1-038', 'TCB258/EC1', 26.65, None, 'XBS'),
    ('R-TCB258_EC1-039', 'TCB258/EC1', 53.73, None, 'XBS'),
    ('R-TCB258_EC1-040', 'TCB258/EC1', 29.77, None, 'XBS'),
    ('R-TCB258_EC1-041', 'TCB258/EC1', 40.04, None, 'XBS'),
    ('R-TCB258_EC1-042', 'TCB258/EC1', 44.70, None, 'XBS'),
    ('R-TCB258_EC1-043', 'TCB258/EC1', 39.29, None, 'XBS'),
    ('R-TCB258_EC1-044', 'TCB258/EC1', 39.76, None, 'XBS'),
    ('R-TCB258_EC1-045', 'TCB258/EC1', 51.07, None, 'XBS'),
    ('R-TCB258_EC1-046', 'TCB258/EC1', 42.69, None, 'XBS'),
    ('R-TCB258_EC1-047', 'TCB258/EC1', 50.22, None, 'XBS'),
    ('R-TCB258_EC1-048', 'TCB258/EC1', 51.90, None, 'XBS'),
    ('R-TCB258_EC1-049', 'TCB258/EC1', 52.68, None, 'XBS'),
    ('R-TCB258_EC1-050', 'TCB258/EC1', 42.31, None, 'XBS'),
    ('R-TCB258_EC1-051', 'TCB258/EC1', 42.23, None, 'XBS'),
    ('R-TCB258_EC1-052', 'TCB258/EC1', 35.72, None, 'XBS'),
    ('R-TCB258_EC1-053', 'TCB258/EC1', 19.26, None, 'XBS'),
    ('R-TCB258_EC1-055', 'TCB258/EC1', 49.58, None, 'XBS'),
    ('R-TCB258_EC1-056', 'TCB258/EC1', 51.62, None, 'XBS'),
    ('R-TCB258_EC1-057', 'TCB258/EC1', 52.05, None, 'XBS'),
    ('R-TCB258_EC1-058', 'TCB258/EC1', 15.96, None, 'XBS'),
    ('R-TCB258_EC1-059', 'TCB258/EC1', 45.25, None, 'XBS'),
    ('R-TCB258_EC1-060', 'TCB258/EC1', 45.61, None, 'XBS'),
    ('R-TCB258_EC1-061', 'TCB258/EC1', 50.00, None, 'XBS'),
    ('R-TCB258_EC1-062', 'TCB258/EC1', 49.90, None, 'XBS'),
    ('R-TCB258_EC1-063', 'TCB258/EC1', 40.97, None, 'XBS'),
    ('R-TCB258_EC1-064', 'TCB258/EC1', 41.08, None, 'XBS'),
    ('R-TCB258_EC1-065', 'TCB258/EC1', 46.84, None, 'XBS'),
    ('R-TCB258_EC1-066', 'TCB258/EC1', 46.56, None, 'XBS'),
    ('R-TCB258_EC1-067', 'TCB258/EC1', 50.26, None, 'XBS'),
    ('R-TCB258_EC1-068', 'TCB258/EC1', 50.90, None, 'XBS'),
    ('R-TCB258_EC1-069', 'TCB258/EC1', 22.60, None, 'XBS'),
    ('R-TCB258_EC1-070', 'TCB258/EC1', 60.11, None, 'XBS'),
    ('R-TCB258_EC1-071', 'TCB258/EC1', 24.48, None, 'XBS'),
    ('R-TCB258_EC1-072', 'TCB258/EC1', 38.11, None, 'XBS'),
    ('R-TCB258_EC1-073', 'TCB258/EC1', 63.34, None, 'XBS'),
    ('R-TCB258_EC1-074', 'TCB258/EC1', 51.77, None, 'XBS'),
    ('R-TCB258_EC1-075', 'TCB258/EC1', 48.00, None, 'XBS'),
    ('R-TCB258_EC1-076', 'TCB258/EC1', 48.56, None, 'XBS'),
    ('R-TCB258_EC1-077', 'TCB258/EC1', 46.52, None, 'XBS'),
    ('R-TCB258_EC1-078', 'TCB258/EC1', 46.45, None, 'XBS'),
    ('R-TCB258_EC1-080', 'TCB258/EC1', 40.65, None, 'XBS'),
    ('R-TCB258_EC1-081', 'TCB258/EC1', 44.78, None, 'XBS'),
    ('R-TCB258_EC1-082', 'TCB258/EC1', 44.75, None, 'XBS'),
    ('R-TCB258_EC1-083', 'TCB258/EC1', 44.22, None, 'XBS'),
    ('R-TCB258_EC1-084', 'TCB258/EC1', 45.37, None, 'XBS'),
    ('R-TCB258_EC1-085', 'TCB258/EC1', 45.65, None, 'XBS'),
    ('R-TCB258_EC1-086', 'TCB258/EC1', 45.65, None, 'XBS'),
    ('R-TCB258_EC1-087', 'TCB258/EC1', 64.04, None, 'XBS'),
    ('R-TCB258_EC1-088', 'TCB258/EC1', 58.26, None, 'XBS'),
    ('R-TCB258_EC1-089', 'TCB258/EC1', 59.28, None, 'XBS'),
    ('R-TCB258_EC1-090', 'TCB258/EC1', 59.51, None, 'XBS'),
    ('R-TCB258_EC1-091', 'TCB258/EC1', 59.53, None, 'XBS'),
    ('R-TCB258_EC1-092', 'TCB258/EC1', 42.52, None, 'XBS'),
    ('R-TCB258_EC1-093', 'TCB258/EC1', 55.39, None, 'XBS'),
    ('R-TCB258_EC1-094', 'TCB258/EC1', 56.31, None, 'XBS'),
    ('R-TCB258_EC1-095', 'TCB258/EC1', 55.51, None, 'XBS'),
    ('R-TCB258_EC1-096', 'TCB258/EC1', 42.10, None, 'XBS'),
    ('R-GZIC_GR4-099', 'GZIC GR4', 100.60, '0327-SD-HY', 'XBS'),
    ('R-GZIC_GR4-100', 'GZIC GR4', 102.40, '0327-SD-HY', 'XBS'),
]

# Stock em processo (confeccionadores) — v3.3: ref base + cor separada
# (token, ref_code, metres, color, confeccionador)
IN_PROCESS_STOCK = [
    ('P-Fabrijeans_CostaC-TCB258_EC1-001', 'TCB258/EC1', 827.00, 'Dark Grey Melange', 'Fabrijeans / Costa C'),
    ('P-Fabrijeans_CostaC-TCB258_EC1-002', 'TCB258/EC1', 208.97, 'Pine Green', 'Fabrijeans / Costa C'),
    ('P-Fabrijeans_CostaC-TCB258_EC1-003', 'TCB258/EC1', 229.79, 'Dark Grey Melange', 'Fabrijeans / Costa C'),
    ('P-Fabrijeans_CostaC-TCD524_EC1-001', 'TCD524/EC1', 1245.00, 'Almond', 'Fabrijeans / Costa C'),
    ('P-Samidel-GB14W-001', 'GB14W', 1772.15, 'MH W9U1', 'Samidel'),
    ('P-Samidel-GB14W-002', 'GB14W', 2015.10, 'MH 01U5', 'Samidel'),
    ('P-Samidel-GB14W-003', 'GB14W', 1732.20, 'UNI A0', 'Samidel'),
    ('P-Fabrijeans_CostaC-GB14W-001', 'GB14W', 673.00, 'UNI 10', 'Fabrijeans / Costa C'),
    ('P-Samidel-GB14W-004', 'GB14W', 2439.60, 'UNI 10', 'Samidel'),
    ('P-Fabrijeans_CostaC-GB14W-002', 'GB14W', 30.00, 'UNI 73', 'Fabrijeans / Costa C'),
    ('P-Fabrijeans_CostaC-GB14W-003', 'GB14W', 212.00, 'UNI 91', 'Fabrijeans / Costa C'),
    ('P-Fabrijeans_CostaC-GB14W-004', 'GB14W', 1584.60, 'UNI 93', 'Fabrijeans / Costa C'),
    ('P-Fabrijeans_CostaC-GB14W-005', 'GB14W', 1134.80, 'UNI 1', 'Fabrijeans / Costa C'),
    ('P-Samidel-GB14W-005', 'GB14W', 3922.00, 'UNI 1', 'Samidel'),
    ('P-Fabrijeans_CostaC-GB14W-006', 'GB14W', 725.40, 'UNI Evergreen A1', 'Fabrijeans / Costa C'),
    ('P-Samidel-Guana-001', 'Guana', 796.70, 'S32 Pepper Grey B5', 'Samidel'),
    ('P-Samidel-Guana-002', 'Guana', 1465.90, 'TW6 Midnight Blue 10', 'Samidel'),
    ('P-Fabrijeans_CostaC-Guana-001', 'Guana', 1387.10, 'S32 Cool Brown C2', 'Fabrijeans / Costa C'),
    ('P-Fabrijeans_CostaC-Guana-002', 'Guana', 975.50, '089 Grey Flint B15', 'Fabrijeans / Costa C'),
    ('P-Samidel-TCD340_RY1-001', 'TCD340/RY1', 60.99, 'Berry Pinstripe', 'Samidel'),
    ('P-Fabrijeans_CostaC-TCE278_F1-001', 'TCE278/F1', 5755.33, 'Signature Dark Brown', 'Fabrijeans / Costa C'),
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
        metres REAL,
        po_garment TEXT,
        notes TEXT
    );
    """)

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

        for token, ref, metres, lot, wh in FABRIC_ROLLS:
            cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (token, ref, metres, lot, None, wh, 'AVAILABLE', None,
                          datetime.now().isoformat(), datetime.now().isoformat(), None))

        # In-process stock (confeccionadores) — lotes agregados com token P-
        for token, ref, metres, color, conf in IN_PROCESS_STOCK:
            cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (token, ref, metres, None, color, conf, 'IN_PROCESS', None,
                          datetime.now().isoformat(), datetime.now().isoformat(), f'Lote agregado em {conf}'))

        # Consumos reais CW28/29 com desvios
        for po, model, pcs, exp_m, act_m, dev, date, conf, notes in REAL_CONSUMPTIONS:
            cursor.execute("INSERT INTO consumptions VALUES (NULL,?,?,?,?,?,?,?,?,?)",
                         (po, model, pcs, exp_m, act_m, dev, date, conf, notes))

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
        fr.description,
        fr.reorder_point,
        COALESCE(SUM(CASE WHEN fr2.status = 'AVAILABLE' THEN fr2.metres ELSE 0 END), 0) as disponivel,
        COALESCE(SUM(CASE WHEN fr2.status = 'RESERVED' THEN fr2.metres ELSE 0 END), 0) as reservado,
        COALESCE(SUM(CASE WHEN fr2.status = 'IN_PROCESS' THEN fr2.metres ELSE 0 END), 0) as em_processo,
        COALESCE(SUM(CASE WHEN fr2.status IN ('AVAILABLE', 'RESERVED', 'IN_PROCESS') THEN fr2.metres ELSE 0 END), 0) as total_stock
    FROM fabric_refs fr
    LEFT JOIN fabric_rolls fr2 ON fr.ref_code = fr2.ref_code
    GROUP BY fr.ref_code, fr.description, fr.reorder_point
    """
    stock_df = query_to_df(query)

    incoming_df = query_to_df("SELECT ref_code, COALESCE(SUM(total_metres), 0) as a_chegar FROM incoming_fabric WHERE status IN ('EXPECTED', 'IN_TRANSIT') GROUP BY ref_code")
    necessity_df = query_to_df("SELECT fabric_ref, COALESCE(SUM(metres_expected), 0) as necessidade FROM production WHERE status IN ('PENDING', 'CUTTING', 'SEWING') GROUP BY fabric_ref")

    result = stock_df.merge(incoming_df, on='ref_code', how='left')
    result = result.merge(necessity_df, left_on='ref_code', right_on='fabric_ref', how='left')
    result = result.drop(columns=['fabric_ref'], errors='ignore')
    result = result.fillna(0)

    result['stock_liquido'] = result['disponivel'] + result['em_processo']
    result['planeamento'] = result['stock_liquido'] + result['a_chegar'] - result['necessidade']

    def classify_status(row):
        if row['planeamento'] < 0: return '🔴 falha crítica'
        elif row['disponivel'] < row['reorder_point']: return '🟠 stock baixo'
        elif row['necessidade'] > (row['disponivel'] + row['em_processo']): return '🟡 risco'
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
    df = query_to_df("SELECT * FROM fabric_rolls ORDER BY ref_code, token")
    return to_excel(df, 'Stock Detalhado')

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
    st.markdown("""
    <div class="main-header">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <h1>🏭 SNT CMT</h1>
                <p>Sistema de Stock & Produção v3.3 | CW29 2026</p>
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
            ("STOCK DISPONÍVEL", stock_df['disponivel'].sum(), "rolos em armazém", "up"),
            ("EM PROCESSO (CONF.)", stock_df['em_processo'].sum(), f"{n_pending} POs garment ativas", "warn"),
            ("A CHEGAR", stock_df['a_chegar'].sum(), f"{n_incoming} POs tecido pendentes", "info"),
            ("NECESSIDADE PENDENTE", stock_df['necessidade'].sum(), "POs garment por faturar", "down"),
            ("POSIÇÃO LÍQUIDA", stock_df['stock_liquido'].sum(), "disponível + em processo", "up"),
            ("POSIÇÃO PLANEAMENTO", stock_df['planeamento'].sum(), "líquido + a chegar − necessidade", "info"),
        ]

        cols = st.columns(6)
        for i, (label, value, delta, delta_type) in enumerate(kpi_data):
            with cols[i]:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value:,.0f}<span style="font-size:14px;color:#8b9dc3">m</span></div>
                    <div class="kpi-delta {delta_type}">{delta}</div>
                </div>
                """, unsafe_allow_html=True)

        # Alertas
        st.markdown('<div class="section-title">Alertas do Sistema</div>', unsafe_allow_html=True)

        critical = stock_df[stock_df['status'].str.contains('falha crítica')]
        warning = stock_df[stock_df['status'].str.contains('stock baixo')]
        risk = stock_df[stock_df['status'].str.contains('risco')]
        ok = stock_df[stock_df['status'].str.contains('ok')]

        alerts_html = '<div class="alert-bar">'
        if not critical.empty:
            for _, row in critical.iterrows():
                alerts_html += f'<div class="alert-chip critical"><span class="alert-dot"></span>Falha Crítica: {row["ref_code"]} — planeamento {row["planeamento"]:,.0f}m</div>'
        if not warning.empty:
            for _, row in warning.head(4).iterrows():
                alerts_html += f'<div class="alert-chip warning"><span class="alert-dot"></span>Stock Baixo: {row["ref_code"]} — {row["disponivel"]:,.0f}m &lt; reorder {row["reorder_point"]:,.0f}m</div>'
        if not risk.empty:
            for _, row in risk.head(4).iterrows():
                alerts_html += f'<div class="alert-chip info"><span class="alert-dot"></span>Risco: {row["ref_code"]} — necessidade &gt; stock líquido</div>'
        if not ok.empty:
            ok_refs = ', '.join(ok['ref_code'].head(3).tolist())
            alerts_html += f'<div class="alert-chip ok"><span class="alert-dot"></span>{ok_refs} — equilibrados</div>'
        alerts_html += '</div>'
        st.markdown(alerts_html, unsafe_allow_html=True)

        # Posição de stock
        st.markdown('<div class="section-title">Posição de Stock por Referência de Tecido</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">stock líquido = disponível + em processo | planeamento = líquido + a chegar − necessidade</div>', unsafe_allow_html=True)

        display_df = stock_df[['ref_code', 'description', 'disponivel', 'em_processo', 'stock_liquido', 'a_chegar', 'necessidade', 'planeamento', 'status']].copy()
        display_df = safe_display_df(display_df)
        display_df.columns = ['Ref', 'Descrição', 'Disponível', 'Em Processo', 'Stock Líquido', 'A Chegar', 'Necessidade', 'Planeamento', 'Status']
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

        # Pipeline
        st.markdown('<div class="section-title">Pipeline de Produção por Confeccionador</div>', unsafe_allow_html=True)
        prod_summary = query_to_df("""
            SELECT confeccionador, COUNT(*) as num_pos, SUM(po_qty) as total_pcs, SUM(metres_expected) as total_m
            FROM production WHERE status != 'INVOICED' GROUP BY confeccionador ORDER BY total_m DESC
        """)
        if not prod_summary.empty:
            prod_summary = safe_display_df(prod_summary)
            prod_summary.columns = ['Confeccionador', 'POs Ativas', 'Total Peças', 'Metros Esperados']
            st.dataframe(prod_summary, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erro no dashboard: {e}")
        st.info("A base de dados pode estar a inicializar. Aguarde e recarregue.")


# ===================== UI: STOCK =====================
def render_stock():
    st.markdown('<div class="section-title">📦 Stock por Armazém</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">armazéns centrais + confeccionadores com lotes agregados</div>', unsafe_allow_html=True)

    try:
        wh_df = query_to_df("""
            SELECT warehouse, ref_code, status, COUNT(*) as num_rolls, COALESCE(SUM(metres), 0) as total_metres
            FROM fabric_rolls WHERE status != 'INVOICED'
            GROUP BY warehouse, ref_code, status ORDER BY warehouse, ref_code
        """)

        if not wh_df.empty:
            wh_summary = wh_df.groupby('warehouse').agg({'total_metres': 'sum', 'num_rolls': 'sum'}).reset_index()

            st.markdown('<div class="wh-grid">', unsafe_allow_html=True)
            for _, row in wh_summary.iterrows():
                wh_name = row['warehouse']
                wh_icon = "🏭" if wh_name in WAREHOUSES else "👕"
                detail_df = wh_df[wh_df['warehouse'] == wh_name]
                detail_text = " | ".join([f"{r['ref_code']}: {r['total_metres']:,.0f}m" for _, r in detail_df.head(3).iterrows()])
                in_process = wh_df[(wh_df['warehouse'] == wh_name) & (wh_df['status'] == 'IN_PROCESS')]['total_metres'].sum()

                st.markdown(f"""
                <div class="wh-card">
                    <div class="wh-name">{wh_icon} {wh_name}</div>
                    <div class="wh-total">{row['total_metres']:,.0f}<span style="font-size:13px;color:#8b9dc3">m</span></div>
                    <div class="wh-detail">{detail_text}</div>
                    <div class="wh-rolls">{int(row['num_rolls'])} rolos/lotes | {in_process:,.0f}m em processo</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Filtros
        st.markdown('<div class="section-title">Detalhe de Rolos e Lotes</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            wh_list = query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls ORDER BY warehouse")['warehouse'].tolist()
            selected_wh = st.selectbox("Armazém", ['Todos'] + wh_list, key="stock_wh")
        with col2:
            ref_list = query_to_df("SELECT DISTINCT ref_code FROM fabric_rolls ORDER BY ref_code")['ref_code'].tolist()
            selected_ref = st.selectbox("Referência", ['Todas'] + ref_list, key="stock_ref")
        with col3:
            selected_status = st.selectbox("Status", ['Todos'] + ROLL_STATUSES, key="stock_status")

        query = "SELECT token, ref_code, metres, color, lot, warehouse, status, po_garment, notes FROM fabric_rolls WHERE 1=1"
        params = []
        if selected_wh != 'Todos':
            query += " AND warehouse = ?"; params.append(selected_wh)
        if selected_ref != 'Todas':
            query += " AND ref_code = ?"; params.append(selected_ref)
        if selected_status != 'Todos':
            query += " AND status = ?"; params.append(selected_status)
        query += " ORDER BY ref_code, token LIMIT 500"

        rolls_df = query_to_df(query, params)
        clean_df = safe_display_df(rolls_df)
        clean_df.columns = ['Token', 'Ref', 'Metros', 'Cor', 'Lote', 'Armazém', 'Status', 'PO Garment', 'Notas']
        st.dataframe(clean_df, use_container_width=True, hide_index=True, height=500)

        st.markdown('<div class="section-title">Exportar seleção atual</div>', unsafe_allow_html=True)
        download_pair(rolls_df, f"stock_{datetime.now().strftime('%Y%m%d')}", 'Stock', 'stock_sel')

    except Exception as e:
        st.error(f"Erro ao carregar stock: {e}")


# ===================== UI: INCOMING =====================
def render_incoming():
    st.markdown('<div class="section-title">🚢 A Chegar</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Encomendas de tecido pendentes — só contam para planeamento, não entram no stock líquido</div>', unsafe_allow_html=True)

    incoming_df = query_to_df("""
        SELECT i.po_number, i.supplier, i.ref_code, i.total_metres, i.expected_date, i.status, i.tracking_ref, fr.description
        FROM incoming_fabric i LEFT JOIN fabric_refs fr ON i.ref_code = fr.ref_code
        WHERE i.status IN ('EXPECTED', 'IN_TRANSIT') ORDER BY i.expected_date
    """)

    if not incoming_df.empty:
        clean = safe_display_df(incoming_df)
        clean.columns = ['PO', 'Fornecedor', 'Ref', 'Metros', 'Data Prevista', 'Status', 'Tracking', 'Descrição']
        st.dataframe(clean, use_container_width=True, hide_index=True, height=400)

        # Marcar como recebido → vai para Receção no menu Movimentar
        st.markdown('<div class="section-title">Marcar chegada</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">quando o tecido chega, marca aqui a PO — depois regista os rolos em 🚚 Movimentar → Receção</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            po_sel = st.selectbox("PO de tecido", incoming_df['po_number'].tolist(), key="incoming_po")
        with col2:
            st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
            if st.button("✓ Chegou", key="incoming_arrived"):
                execute_sql("UPDATE incoming_fabric SET status = 'RECEIVED' WHERE po_number = ?", (po_sel,))
                log_movement('ARRIVAL', None, 'Fornecedor', 'XBS', None, None, None, f'PO tecido {po_sel} chegou — aguarda registo de rolos')
                st.success(f"PO {po_sel} marcada como recebida. Regista agora os rolos em 🚚 Movimentar → Receção.")
                st.rerun()

        # Timeline
        st.markdown('<div class="section-title">Calendário de Chegadas</div>', unsafe_allow_html=True)
        st.markdown('<div class="timeline">', unsafe_allow_html=True)
        for _, row in incoming_df.head(10).iterrows():
            status_class = "completed" if row['status'] == 'IN_TRANSIT' else "pending"
            tracking = row['tracking_ref'] if row['tracking_ref'] else 'sem rastreio'
            st.markdown(f"""
            <div class="timeline-item {status_class}">
                <div class="timeline-date">{row['expected_date']}</div>
                <div class="timeline-text">{row['po_number']} — {row['supplier']} {row['ref_code']} {row['total_metres']:,.0f}m</div>
                <div class="timeline-meta">{row['status']} | {tracking}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Nenhuma encomenda pendente.")


# ===================== UI: PRODUCTION (MODO LIVE) =====================
def render_production():
    st.markdown('<div class="section-title">👕 Produção</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">modo live: lança consumos de corte, valida desvios e muda estados — tudo por dropdown</div>', unsafe_allow_html=True)

    tab_live, tab_list, tab_status = st.tabs(["⚡ Modo Live — Registar Corte", "📋 POs Ativas", "🔄 Mudar Estado PO"])

    # ---------- TAB LIVE ----------
    with tab_live:
        active_pos = query_to_df("""
            SELECT po_number, model_name, confeccionador, po_qty, fabric_ref, metres_expected, status
            FROM production WHERE status IN ('PENDING', 'CUTTING', 'SEWING') ORDER BY po_number DESC
        """)

        if active_pos.empty:
            st.info("Sem POs ativas para registar corte.")
        else:
            po_options = active_pos['po_number'].tolist()
            po_sel = st.selectbox("Seleciona a PO garment", po_options, key="live_po",
                                  format_func=lambda p: f"{p} — {active_pos[active_pos['po_number']==p].iloc[0]['model_name'][:45]}")

            po_row = active_pos[active_pos['po_number'] == po_sel].iloc[0]

            # Consumo esperado do mapa (procura por correspondência de modelo)
            map_df = query_to_df("SELECT model_name, m_per_pc_expected, m_per_pc_actual FROM consumption_map WHERE fabric_ref = ?", (po_row['fabric_ref'],))
            expected_mpc = None
            if not map_df.empty:
                model_lower = str(po_row['model_name']).lower()
                for _, m in map_df.iterrows():
                    key = str(m['model_name']).lower().replace(' men plain', '').replace(' men checked', '').replace(' men striped', '')
                    if key and key in model_lower:
                        expected_mpc = m['m_per_pc_actual'] if m['m_per_pc_actual'] else m['m_per_pc_expected']
                        break
                if expected_mpc is None:
                    expected_mpc = map_df.iloc[0]['m_per_pc_expected']

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div class="info-card" style="text-align:center;">
                    <div class="dev-label">Confeccionador</div>
                    <div style="color:#e0e6ed;font-size:16px;font-weight:600;">{po_row['confeccionador']}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="info-card" style="text-align:center;">
                    <div class="dev-label">Peças PO</div>
                    <div style="color:#e0e6ed;font-size:16px;font-weight:600;">{int(po_row['po_qty'])} pcs</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="info-card" style="text-align:center;">
                    <div class="dev-label">Ref Tecido</div>
                    <div style="color:#e0e6ed;font-size:16px;font-weight:600;">{po_row['fabric_ref'] or '—'}</div>
                </div>""", unsafe_allow_html=True)
            with c4:
                mpc_txt = f"{expected_mpc:.2f} m/pc" if expected_mpc else "sem mapa"
                st.markdown(f"""<div class="info-card" style="text-align:center;">
                    <div class="dev-label">Consumo Esperado</div>
                    <div style="color:#e0e6ed;font-size:16px;font-weight:600;">{mpc_txt}</div>
                </div>""", unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                pcs_cut = st.number_input("Peças cortadas", min_value=0, value=int(po_row['po_qty']), step=1, key="live_pcs")
            with col2:
                metres_real = st.number_input("Metros reais consumidos", min_value=0.0, step=0.1, key="live_metres",
                                              value=float(pcs_cut * expected_mpc) if expected_mpc else 0.0)
            with col3:
                st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
                confirm_cut = st.button("✓ Registar corte", key="live_confirm")

            # Validação de desvio em tempo real
            if pcs_cut > 0 and metres_real > 0 and expected_mpc:
                real_mpc = metres_real / pcs_cut
                dev_pct = ((real_mpc - expected_mpc) / expected_mpc) * 100
                dev_class = "ok" if abs(dev_pct) <= 2 else ("warn" if abs(dev_pct) <= 5 else "bad")
                dev_color = {"ok": "#22c55e", "warn": "#f59e0b", "bad": "#ef4444"}[dev_class]
                dev_msg = {"ok": "dentro da tolerância", "warn": "atenção — desvio 2–5%", "bad": "⚠️ DESVIO CRÍTICO > 5%"}[dev_class]
                st.markdown(f"""
                <div class="dev-box {dev_class}">
                    <div class="dev-label">Desvio vs mapa — {dev_msg}</div>
                    <div class="dev-value" style="color:{dev_color};">{dev_pct:+.1f}%</div>
                    <div style="color:#8b9dc3;font-size:12px;">real {real_mpc:.3f} m/pc vs esperado {expected_mpc:.3f} m/pc</div>
                </div>
                """, unsafe_allow_html=True)
            elif not expected_mpc:
                st.warning("⚠️ Este modelo não tem consumo no mapa. O registo fica sem validação de desvio — considera adicioná-lo em 📊 Consumos.")
                real_mpc, dev_pct = (metres_real / pcs_cut if pcs_cut else 0), None
            else:
                real_mpc, dev_pct = 0, None

            if confirm_cut:
                if pcs_cut <= 0 or metres_real <= 0:
                    st.error("Peças e metros têm de ser > 0")
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
                    st.success(f"✅ Corte registado: {pcs_cut} pcs × {real_mpc:.3f} m/pc = {metres_real:,.1f}m" +
                               (f" | desvio {dev_pct:+.1f}%" if dev_pct is not None else ""))
                    st.rerun()

    # ---------- TAB LISTA ----------
    with tab_list:
        status_filter = st.selectbox("Estado", ['Todas'] + PROD_STATUSES, key="prod_filter")
        q = "SELECT po_number, model_name, confeccionador, po_qty, fabric_ref, metres_expected, expected_date, status FROM production"
        if status_filter != 'Todas':
            q += f" WHERE status = '{status_filter}'"
        q += " ORDER BY expected_date"
        prod_df = query_to_df(q)
        if not prod_df.empty:
            clean = safe_display_df(prod_df)
            clean.columns = ['PO', 'Modelo', 'Confeccionador', 'Qty', 'Ref', 'Metros', 'Entrega', 'Status']
            st.dataframe(clean, use_container_width=True, hide_index=True, height=450)
            total_m = prod_df['metres_expected'].fillna(0).sum()
            st.markdown(f'<div class="section-subtitle">{len(prod_df)} POs | {total_m:,.0f}m esperados</div>', unsafe_allow_html=True)
        else:
            st.info("Sem POs neste estado.")

    # ---------- TAB STATUS ----------
    with tab_status:
        st.markdown('<div class="section-subtitle">mudança de estado por dropdown — INVOICED faz baixa automática dos metros em processo</div>', unsafe_allow_html=True)
        all_pos = query_to_df("SELECT po_number, model_name, confeccionador, status FROM production ORDER BY po_number DESC")
        if not all_pos.empty:
            col1, col2 = st.columns(2)
            with col1:
                po_st = st.selectbox("PO garment", all_pos['po_number'].tolist(), key="status_po",
                                     format_func=lambda p: f"{p} — {all_pos[all_pos['po_number']==p].iloc[0]['status']}")
            with col2:
                new_status = st.selectbox("Novo estado", PROD_STATUSES, key="status_new")

            if st.button("✓ Aplicar estado", key="status_apply"):
                if new_status == 'INVOICED':
                    # Baixa automática: metros em processo ligados à PO saem do stock
                    inv = query_to_df("SELECT COALESCE(SUM(metres),0) as m FROM fabric_rolls WHERE po_garment = ? AND status = 'IN_PROCESS'", (po_st,))
                    invoiced_m = inv.iloc[0]['m']
                    execute_sql("UPDATE fabric_rolls SET status = 'INVOICED', notes = 'Faturado — saiu de em processo' WHERE po_garment = ? AND status = 'IN_PROCESS'", (po_st,))
                    execute_sql("UPDATE production SET status = 'INVOICED' WHERE po_number = ?", (po_st,))
                    log_movement('INVOICE', None, 'Em Processo', 'Faturado', None, invoiced_m, po_st, f'{invoiced_m:.1f}m faturados')
                    st.success(f"✅ PO {po_st} faturada — {invoiced_m:,.1f}m saíram de em processo.")
                else:
                    execute_sql("UPDATE production SET status = ? WHERE po_number = ?", (new_status, po_st))
                    log_movement('STATUS', None, None, None, None, None, po_st, f'Estado → {new_status}')
                    st.success(f"✅ PO {po_st} → {new_status}")
                st.rerun()


# ===================== UI: CONSUMOS =====================
def render_consumos():
    st.markdown('<div class="section-title">📊 Consumos</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">mapa partilhado por modelo base — editável na grelha. desvio > 5% gera alerta.</div>', unsafe_allow_html=True)

    tab_map, tab_real, tab_edit = st.tabs(["📊 Mapa Visual", "🧾 Registos Reais", "✏️ Editar Mapa"])

    with tab_map:
        cm_df = query_to_df("""
            SELECT cm.model_name, cm.fabric_ref, cm.m_per_pc_expected, cm.m_per_pc_actual
            FROM consumption_map cm ORDER BY cm.fabric_ref, cm.model_name
        """)
        if not cm_df.empty:
            st.markdown('<div style="display:flex;gap:24px;margin-bottom:12px;font-size:12px;color:#8b9dc3;"><span>esperado</span><span>real médio</span><span>desvio > 5% = alerta</span></div>', unsafe_allow_html=True)
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
                    act_txt = "sem dados"
                    badge = '<span class="badge" style="background:rgba(100,116,139,0.15);color:#64748b;">—</span>'
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
            clean = safe_display_df(cons_df)
            clean.columns = ['ID', 'PO Garment', 'Modelo', 'Peças', 'Metros Esperados', 'Metros Reais', 'Desvio %', 'Data Corte', 'Confeccionador', 'Notas']
            st.dataframe(clean, use_container_width=True, hide_index=True, height=400)
            n_high = cons_df[cons_df['deviation_pct'].fillna(0).abs() > 5].shape[0]
            if n_high:
                st.warning(f"⚠️ {n_high} consumos com desvio > 5%")
            download_pair(cons_df, f"consumos_{datetime.now().strftime('%Y%m%d')}", 'Consumos', 'cons_dl')
        else:
            st.info("Sem consumos registados.")

    with tab_edit:
        st.markdown('<div class="section-subtitle">edita diretamente o consumo standard (m/pc esperado) — alterações gravam ao clicar em Guardar</div>', unsafe_allow_html=True)
        cm_edit = query_to_df("SELECT model_name, fabric_ref, m_per_pc_expected, m_per_pc_actual FROM consumption_map ORDER BY fabric_ref, model_name")
        edited = st.data_editor(
            cm_edit,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "model_name": st.column_config.TextColumn("Modelo", required=True),
                "fabric_ref": st.column_config.SelectboxColumn("Ref Tecido", options=[r[0] for r in FABRIC_REFS], required=True),
                "m_per_pc_expected": st.column_config.NumberColumn("Esperado m/pc", min_value=0.0, step=0.01, format="%.2f", required=True),
                "m_per_pc_actual": st.column_config.NumberColumn("Real Médio m/pc", min_value=0.0, step=0.01, format="%.3f"),
            },
            key="cm_editor"
        )
        if st.button("💾 Guardar mapa de consumos", key="cm_save"):
            execute_sql("DELETE FROM consumption_map")
            rows = [(r['model_name'], r['fabric_ref'], r['m_per_pc_expected'], r['m_per_pc_actual'])
                    for _, r in edited.iterrows() if r['model_name'] and r['fabric_ref'] and r['m_per_pc_expected']]
            execute_many("INSERT OR REPLACE INTO consumption_map VALUES (?,?,?,?)", rows)
            st.success(f"✅ Mapa guardado — {len(rows)} modelos.")
            st.rerun()


# ===================== UI: MOVEMENT (3 MODOS) =====================
def render_movement():
    st.markdown('<div class="section-title">🚚 Movimentar Tecido</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">3 modos: rolos conhecidos (tokens) · lote agregado (divisível) · metros consolidados (FIFO)</div>', unsafe_allow_html=True)

    tab_rolls, tab_lot, tab_bulk, tab_recv, tab_inv = st.tabs([
        "🎫 Rolos Conhecidos", "📦 Lote Agregado", "🔢 Metros Consolidados", "📥 Receção", "📄 Faturação PO"])

    # ---------- MODO 1: ROLOS CONHECIDOS ----------
    with tab_rolls:
        st.markdown('<div class="section-subtitle">seleciona rolos individuais por token e move-os para outro local</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            ref_opts = query_to_df("SELECT DISTINCT ref_code FROM fabric_rolls WHERE status = 'AVAILABLE' ORDER BY ref_code")['ref_code'].tolist()
            m1_ref = st.selectbox("Referência", ref_opts, key="m1_ref")
        with c2:
            wh_opts = query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls WHERE ref_code = ? AND status = 'AVAILABLE'", (m1_ref,))['warehouse'].tolist()
            m1_wh = st.selectbox("De (armazém atual)", wh_opts, key="m1_wh")

        rolls_avail = query_to_df("SELECT token, metres, color FROM fabric_rolls WHERE ref_code = ? AND warehouse = ? AND status = 'AVAILABLE' ORDER BY token", (m1_ref, m1_wh))
        if rolls_avail.empty:
            st.info("Sem rolos disponíveis com estes filtros.")
        else:
            sel_tokens = st.multiselect(
                "Rolos a mover",
                rolls_avail['token'].tolist(),
                format_func=lambda t: f"{t} — {rolls_avail[rolls_avail['token']==t].iloc[0]['metres']:.1f}m" +
                                      (f" ({rolls_avail[rolls_avail['token']==t].iloc[0]['color']})" if rolls_avail[rolls_avail['token']==t].iloc[0]['color'] else ""),
                key="m1_tokens")
            total_sel = rolls_avail[rolls_avail['token'].isin(sel_tokens)]['metres'].sum()
            st.markdown(f'<div class="section-subtitle">{len(sel_tokens)} rolos selecionados — total {total_sel:,.1f}m</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                m1_to = st.selectbox("Para", [l for l in ALL_LOCATIONS if l != m1_wh], key="m1_to")
            with c2:
                m1_status = st.selectbox("Estado no destino", ['AVAILABLE', 'IN_PROCESS'],
                                         format_func=lambda s: 'AVAILABLE (armazém)' if s == 'AVAILABLE' else 'IN_PROCESS (confeccionador)',
                                         key="m1_status")

            if st.button("✓ Mover rolos selecionados", key="m1_go"):
                if not sel_tokens:
                    st.error("Seleciona pelo menos um rolo.")
                else:
                    for t in sel_tokens:
                        execute_sql("UPDATE fabric_rolls SET warehouse = ?, status = ?, date_last_move = ? WHERE token = ?",
                                    (m1_to, m1_status, datetime.now().isoformat(), t))
                        m_val = rolls_avail[rolls_avail['token'] == t].iloc[0]['metres']
                        log_movement('TRANSFER', t, m1_wh, m1_to, m1_ref, m_val, None, f'Rolo movido ({m1_status})')
                    st.success(f"✅ {len(sel_tokens)} rolos ({total_sel:,.1f}m) movidos de {m1_wh} → {m1_to}")
                    st.rerun()

    # ---------- MODO 2: LOTE AGREGADO ----------
    with tab_lot:
        st.markdown('<div class="section-subtitle">lotes P- em confeccionadores — podes mover o total ou dividir (parcial)</div>', unsafe_allow_html=True)
        lots = query_to_df("SELECT token, ref_code, metres, color, warehouse FROM fabric_rolls WHERE status = 'IN_PROCESS' ORDER BY warehouse, ref_code")
        if lots.empty:
            st.info("Sem lotes em processo.")
        else:
            lot_sel = st.selectbox("Lote agregado", lots['token'].tolist(), key="m2_lot",
                                   format_func=lambda t: f"{t} — {lots[lots['token']==t].iloc[0]['metres']:,.1f}m @ {lots[lots['token']==t].iloc[0]['warehouse']}")
            lot_row = lots[lots['token'] == lot_sel].iloc[0]

            c1, c2, c3 = st.columns(3)
            with c1:
                m2_metres = st.number_input("Metros a mover", min_value=0.0, max_value=float(lot_row['metres']),
                                            value=float(lot_row['metres']), step=0.1, key="m2_metres")
            with c2:
                m2_to = st.selectbox("Para", [l for l in ALL_LOCATIONS if l != lot_row['warehouse']], key="m2_to")
            with c3:
                m2_status = st.selectbox("Estado no destino", ['AVAILABLE', 'IN_PROCESS'],
                                         format_func=lambda s: 'AVAILABLE (armazém)' if s == 'AVAILABLE' else 'IN_PROCESS (confeccionador)',
                                         key="m2_status")

            partial = 0 < m2_metres < lot_row['metres']
            if partial:
                st.info(f"✂️ Divisão: o lote original fica com {lot_row['metres'] - m2_metres:,.1f}m e é criado um novo lote de {m2_metres:,.1f}m em {m2_to}")

            if st.button("✓ Mover lote", key="m2_go"):
                if m2_metres <= 0:
                    st.error("Metros > 0 necessários.")
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
                                     f'Divisão de {lot_sel} ({m2_metres:.1f}m)')
                        st.success(f"✅ Lote dividido: {m2_metres:,.1f}m → {new_tok} em {m2_to}")
                    else:
                        execute_sql("UPDATE fabric_rolls SET warehouse = ?, status = ?, date_last_move = ? WHERE token = ?",
                                    (m2_to, m2_status, datetime.now().isoformat(), lot_sel))
                        log_movement('TRANSFER', lot_sel, lot_row['warehouse'], m2_to, lot_row['ref_code'], m2_metres, None, 'Lote movido total')
                        st.success(f"✅ Lote {lot_sel} ({m2_metres:,.1f}m) movido → {m2_to}")
                    st.rerun()

    # ---------- MODO 3: METROS CONSOLIDADOS ----------
    with tab_bulk:
        st.markdown('<div class="section-subtitle">move X metros de uma referência/armazém — o sistema retira dos rolos disponíveis por ordem (FIFO) e cria lote no destino</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            m3_ref = st.selectbox("Referência", query_to_df("SELECT DISTINCT ref_code FROM fabric_rolls WHERE status = 'AVAILABLE' ORDER BY ref_code")['ref_code'].tolist(), key="m3_ref")
        with c2:
            m3_wh = st.selectbox("De (armazém)", query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls WHERE ref_code = ? AND status = 'AVAILABLE'", (m3_ref,))['warehouse'].tolist(), key="m3_wh")

        avail = query_to_df("SELECT COALESCE(SUM(metres),0) as m FROM fabric_rolls WHERE ref_code = ? AND warehouse = ? AND status = 'AVAILABLE'", (m3_ref, m3_wh)).iloc[0]['m']
        st.markdown(f'<div class="section-subtitle">disponível em {m3_wh}: <strong style="color:#60a5fa">{avail:,.1f}m</strong></div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            m3_metres = st.number_input("Metros a mover", min_value=0.0, max_value=float(avail), step=0.1, key="m3_metres")
        with c2:
            m3_to = st.selectbox("Para", [l for l in ALL_LOCATIONS if l != m3_wh], key="m3_to")

        m3_po = st.text_input("PO garment (opcional — reserva)", key="m3_po")

        if st.button("✓ Mover metros", key="m3_go"):
            if m3_metres <= 0 or m3_metres > avail:
                st.error(f"Metros inválidos (disponível: {avail:,.1f}m)")
            else:
                dest_status = 'IN_PROCESS' if m3_to in CONFECCIONADORES else 'AVAILABLE'
                # Cria lote no destino
                new_tok = next_token('P' if dest_status == 'IN_PROCESS' else 'R', m3_ref)
                execute_sql("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (new_tok, m3_ref, m3_metres, None, None, m3_to, dest_status, m3_po or None,
                             datetime.now().isoformat(), datetime.now().isoformat(), f'Consolidado de {m3_wh}'))
                # Retira FIFO dos rolos de origem
                remaining = m3_metres
                src = query_to_df("SELECT token, metres FROM fabric_rolls WHERE ref_code = ? AND warehouse = ? AND status = 'AVAILABLE' ORDER BY date_received, token", (m3_ref, m3_wh))
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
                st.success(f"✅ {m3_metres:,.1f}m movidos de {m3_wh} → {m3_to} como {new_tok}")
                st.rerun()

    # ---------- RECEÇÃO ----------
    with tab_recv:
        st.markdown("<div class='info-card'><div class='info-card-title'>📥 Receção de Novo Tecido</div><div class='info-card-text'>Ao receber tecido de fornecedor, o sistema gera token automático <strong>R-{REF}-{NNN}</strong>. Cada rolo tem token único, metros exatos, lote/cor e histórico completo.</div></div>", unsafe_allow_html=True)

        refs = query_to_df("SELECT ref_code FROM fabric_refs ORDER BY ref_code")['ref_code'].tolist()
        c1, c2, c3 = st.columns(3)
        with c1:
            recv_ref = st.selectbox("Referência", refs, key="recv_ref")
        with c2:
            recv_metres = st.number_input("Metros recebidos", min_value=0.0, step=0.01, key="recv_metres")
        with c3:
            recv_wh = st.selectbox("Armazém destino", WAREHOUSES, key="recv_wh")

        c1, c2 = st.columns(2)
        with c1:
            recv_lot = st.text_input("Lote (opcional)", placeholder="L2026-B", key="recv_lot")
        with c2:
            recv_color = st.text_input("Cor (opcional)", placeholder="Dark Navy", key="recv_color")

        if st.button("✓ Receber e gerar token", key="confirm_recv"):
            if recv_metres > 0:
                token = next_token('R', recv_ref)
                execute_sql("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (token, recv_ref, recv_metres, recv_lot or None, recv_color or None, recv_wh, 'AVAILABLE', None,
                             datetime.now().isoformat(), datetime.now().isoformat(), None))
                log_movement('RECEIPT', token, 'Fornecedor', recv_wh, recv_ref, recv_metres, None, f'Receção lote {recv_lot}' if recv_lot else 'Receção')
                st.success(f"✅ Novo rolo criado: {token} ({recv_metres:,.1f}m)")
                st.rerun()
            else:
                st.error("Metros deve ser > 0")

    # ---------- FATURAÇÃO ----------
    with tab_inv:
        st.markdown("<div class='info-card'><div class='info-card-title'>📄 Faturação de PO Garment</div><div class='info-card-text'>Quando uma PO garment é faturada, os metros em processo ligados a ela saem automaticamente do stock (INVOICED). As movimentações do mês têm de bater certo com a faturação.</div></div>", unsafe_allow_html=True)

        pend_pos = query_to_df("SELECT po_number, model_name, confeccionador FROM production WHERE status != 'INVOICED' ORDER BY po_number DESC")
        if pend_pos.empty:
            st.info("Sem POs por faturar.")
        else:
            invoice_po = st.selectbox("PO garment a faturar", pend_pos['po_number'].tolist(), key="invoice_po",
                                      format_func=lambda p: f"{p} — {pend_pos[pend_pos['po_number']==p].iloc[0]['model_name'][:45]}")
            inv_m = query_to_df("SELECT COALESCE(SUM(metres),0) as m FROM fabric_rolls WHERE po_garment = ? AND status = 'IN_PROCESS'", (invoice_po,)).iloc[0]['m']
            if inv_m > 0:
                st.info(f"Metros em processo ligados a esta PO: {inv_m:,.1f}m")
            else:
                st.warning("Sem metros em processo ligados por token — a faturação só muda o estado da PO.")

            if st.button("✓ Confirmar faturação", key="confirm_invoice"):
                execute_sql("UPDATE fabric_rolls SET status = 'INVOICED', notes = 'Faturado — saiu de em processo' WHERE po_garment = ? AND status = 'IN_PROCESS'", (invoice_po,))
                execute_sql("UPDATE production SET status = 'INVOICED' WHERE po_number = ?", (invoice_po,))
                log_movement('INVOICE', None, 'Em Processo', 'Faturado', None, inv_m, invoice_po, f'{inv_m:.1f}m faturados')
                st.success(f"✅ PO {invoice_po} faturada. {inv_m:,.1f}m saíram de em processo.")
                st.rerun()

    # Regras
    st.markdown('<div class="section-title">Regras de Tokens</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="info-card">
            <div class="info-card-title">✅ Novos Rolos — Token Individual</div>
            <div class="info-card-text">
                Receção de tecido → token automático<br>
                Formato: <span class="trace-token">R-{REF}-{NNN}</span><br><br>
                Cada rolo tem: token único · metros exatos · lote/cor · histórico completo
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="info-card">
            <div class="info-card-title">⚠️ Confeccionadores — Lotes Agregados</div>
            <div class="info-card-text">
                Tecido em confeccionador → <span class="trace-token">P-{CONF}-{REF}-{NNN}</span><br><br>
                Metros totais sem lote original · <strong>divisível</strong> (modo Lote Agregado) · sai de em processo na faturação
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Histórico
    st.markdown('<div class="section-title">Histórico de Movimentações — Últimas 20</div>', unsafe_allow_html=True)
    hist_df = query_to_df("SELECT * FROM movements ORDER BY date_time DESC LIMIT 20")
    if not hist_df.empty:
        clean = safe_display_df(hist_df)
        clean.columns = ['ID', 'Data/Hora', 'Tipo', 'Token', 'De', 'Para', 'Ref', 'Metros', 'PO', 'Notas']
        st.dataframe(clean, use_container_width=True, hide_index=True)
    else:
        st.info("Sem movimentações registadas.")


# ===================== UI: TRACE =====================
def render_trace():
    st.markdown('<div class="section-title">🔍 Rastreio</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">histórico de cada rolo/lote desde entrada até faturação — procura por token, PO garment, lote ou referência</div>', unsafe_allow_html=True)

    search = st.text_input("🔍 Procurar...", placeholder="ex: R-TCB258_EC1-001 · P-Samidel-GB14W-001 · POAPS2000004404", key="trace_search")

    if search:
        token_df = query_to_df("SELECT * FROM fabric_rolls WHERE token = ?", (search,))
        if not token_df.empty:
            row = token_df.iloc[0]
            status_badge = {'AVAILABLE': 'available', 'RESERVED': 'reserved', 'IN_PROCESS': 'inprocess', 'INVOICED': 'invoiced'}.get(row['status'], '')

            st.markdown(f"""
            <div class="trace-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                    <div class="trace-token">{row['token']}</div>
                    <span class="badge {status_badge}">{row['status']}</span>
                </div>
                <div class="trace-details">
                    <div><div class="trace-detail-label">Referência</div><div class="trace-detail-value">{row['ref_code']}</div></div>
                    <div><div class="trace-detail-label">Metros</div><div class="trace-detail-value">{row['metres']:.2f}m</div></div>
                    <div><div class="trace-detail-label">Lote</div><div class="trace-detail-value">{row['lot'] or '—'}</div></div>
                    <div><div class="trace-detail-label">Cor</div><div class="trace-detail-value">{row['color'] or '—'}</div></div>
                    <div><div class="trace-detail-label">Local</div><div class="trace-detail-value">{row['warehouse']}</div></div>
                    <div><div class="trace-detail-label">PO Garment</div><div class="trace-detail-value">{row['po_garment'] or '—'}</div></div>
                    <div><div class="trace-detail-label">Recebido</div><div class="trace-detail-value">{str(row['date_received'])[:10] if row['date_received'] else '—'}</div></div>
                    <div><div class="trace-detail-label">Último Mov.</div><div class="trace-detail-value">{str(row['date_last_move'])[:10] if row['date_last_move'] else '—'}</div></div>
                </div>
                {f'<div style="margin-top:12px;padding:10px;border-radius:8px;background:rgba(245,158,11,0.1);color:#f59e0b;font-size:12px;">📝 {row["notes"]}</div>' if row['notes'] else ''}
            </div>
            """, unsafe_allow_html=True)

            hist_df = query_to_df("SELECT * FROM movements WHERE token = ? OR po_garment = ? ORDER BY date_time DESC", (search, search))
            if not hist_df.empty:
                st.markdown('<div class="section-title">Histórico de Movimentações</div>', unsafe_allow_html=True)
                st.dataframe(safe_display_df(hist_df), use_container_width=True, hide_index=True, height=250)
        else:
            po_df = query_to_df("SELECT * FROM production WHERE po_number = ?", (search,))
            if not po_df.empty:
                st.markdown(f'<div class="section-title">PO: {search}</div>', unsafe_allow_html=True)
                st.dataframe(safe_display_df(po_df), use_container_width=True, hide_index=True)

                cons_df = query_to_df("SELECT * FROM consumptions WHERE po_garment = ?", (search,))
                if not cons_df.empty:
                    st.markdown('<div class="section-title">Consumos Registados</div>', unsafe_allow_html=True)
                    st.dataframe(safe_display_df(cons_df), use_container_width=True, hide_index=True)

                roll_df = query_to_df("SELECT * FROM fabric_rolls WHERE po_garment = ?", (search,))
                if not roll_df.empty:
                    st.markdown('<div class="section-title">Rolos/Lotes Alocados</div>', unsafe_allow_html=True)
                    st.dataframe(safe_display_df(roll_df), use_container_width=True, hide_index=True)

                mov_df = query_to_df("SELECT * FROM movements WHERE po_garment = ? ORDER BY date_time DESC", (search,))
                if not mov_df.empty:
                    st.markdown('<div class="section-title">Movimentações</div>', unsafe_allow_html=True)
                    st.dataframe(safe_display_df(mov_df), use_container_width=True, hide_index=True)
            else:
                st.warning("Nenhum resultado encontrado. Tenta outro token, PO ou referência.")


# ===================== UI: EXPORT =====================
def render_export():
    st.markdown('<div class="section-title">📤 Exportar</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">extratos Excel e CSV para colegas de planeamento e financeiros</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="info-card" style="text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">📊</div>
            <div class="info-card-title">Stock Resumido</div>
            <div class="info-card-text">posição por referência + cor, com planeamento</div>
        </div>
        """, unsafe_allow_html=True)
        df = get_stock_position()
        download_pair(df, f"stock_resumido_{datetime.now().strftime('%Y%m%d')}", 'Stock Resumido', 'exp_sum')

    with col2:
        st.markdown("""
        <div class="info-card" style="text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">📋</div>
            <div class="info-card-title">Stock Detalhado</div>
            <div class="info-card-text">todos os rolos e lotes com tokens</div>
        </div>
        """, unsafe_allow_html=True)
        df2 = query_to_df("SELECT token, ref_code, metres, color, lot, warehouse, status, po_garment, date_last_move, notes FROM fabric_rolls WHERE status != 'INVOICED' ORDER BY ref_code, token")
        download_pair(df2, f"stock_detalhado_{datetime.now().strftime('%Y%m%d')}", 'Stock Detalhado', 'exp_det')

    with col3:
        st.markdown("""
        <div class="info-card" style="text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">📈</div>
            <div class="info-card-title">Consumos & Movimentos</div>
            <div class="info-card-text">cortes com desvios + movimentações do mês (bater com faturação)</div>
        </div>
        """, unsafe_allow_html=True)
        df3 = query_to_df("SELECT * FROM consumptions ORDER BY date_cut DESC")
        download_pair(df3, f"consumos_{datetime.now().strftime('%Y%m%d')}", 'Consumos', 'exp_cons')
        df4 = query_to_df("SELECT * FROM movements WHERE date_time >= ? ORDER BY date_time DESC",
                          ((datetime.now().replace(day=1)).isoformat(),))
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        download_pair(df4, f"movimentos_mes_{datetime.now().strftime('%Y%m')}", 'Movimentos', 'exp_mov')


# ===================== MAIN =====================
def main():
    st.sidebar.markdown("""
    <div style="padding:16px 0 24px 0;text-align:center;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:16px;">
        <div style="font-size:28px;margin-bottom:4px;">🏭</div>
        <div style="color:#e0e6ed;font-size:16px;font-weight:700;">SNT CMT</div>
        <div style="color:#64748b;font-size:11px;">Sistema de Stock & Produção</div>
        <div style="margin-top:8px;display:inline-flex;align-items:center;gap:4px;background:rgba(34,197,94,0.1);color:#22c55e;padding:3px 10px;border-radius:12px;font-size:10px;font-weight:600;">
            <span style="width:5px;height:5px;background:#22c55e;border-radius:50%;display:inline-block;"></span> LIVE
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = {
        "📊 Dashboard": render_dashboard,
        "📦 Stock": render_stock,
        "🚢 A Chegar": render_incoming,
        "👕 Produção": render_production,
        "📊 Consumos": render_consumos,
        "🚚 Movimentar": render_movement,
        "🔍 Rastreio": render_trace,
        "📤 Exportar": render_export
    }

    selection = st.sidebar.radio("Navegar", list(tabs.keys()), label_visibility="collapsed")

    st.sidebar.markdown(f"""
    <div style="position:fixed;bottom:20px;left:20px;right:20px;">
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:12px;color:#64748b;font-size:11px;text-align:center;">
            v3.3 | Dados: CW29 2026<br>{datetime.now().strftime('%Y-%m-%d')}<br>
            <span style="color:#3b82f6;font-weight:600;">SNT CMT</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs[selection]()

if __name__ == "__main__":
    main()
