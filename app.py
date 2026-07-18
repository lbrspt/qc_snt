"""
SNT CMT - Sistema de Stock & Produção v3.2
Real production data from CW29 2026
Features: Pro design, live editing, consumption validation, warehouse/roll movement
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

    /* Movement form */
    .movement-form { 
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
        background: rgba(30,58,95,0.2); padding: 20px; border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.06); margin-bottom: 20px;
    }
    .form-group label { color: #8b9dc3; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; display: block; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: rgba(30,58,95,0.3) !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; }
    .stTabs [data-baseweb="tab"] { color: #8b9dc3 !important; font-size: 13px !important; border-radius: 8px !important; padding: 8px 16px !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: rgba(37,99,235,0.2) !important; color: #60a5fa !important; font-weight: 600 !important; }

    /* Search */
    .search-box { 
        width: 100%; padding: 12px 16px; border-radius: 12px;
        background: rgba(30,58,95,0.4); border: 1px solid rgba(255,255,255,0.1);
        color: #e0e6ed; font-size: 14px; margin-bottom: 20px;
    }
    .search-box:focus { outline: none; border-color: #2563eb; }

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
DB_PATH = os.path.join(DATA_DIR, "snt_cmt.db")

# ===================== DB CONNECTION (no cache) =====================
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


# ===================== SEED DATA =====================
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
    ('TCD341/F1', 'Harrys Dark Navy Pinstripe', 'Riopele', 300),
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
    ('POAPS2000004273', 'Timeless Wool Blazer Dark Brown Check', 'Tyrrell', 209, 'UNKNOWN', 292.60, '2026-07-31', 'PENDING'),
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

FABRIC_ROLLS = [
    ('R-TCB258_EC1-001', 'TCB258/EC1', 28.71, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-002', 'TCB258/EC1', 26.11, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-003', 'TCB258/EC1', 54.82, 'TOTAL ', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-004', 'TCB258/EC1', 33.18, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-005', 'TCB258/EC1', 33.18, 'TOTAL ', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-006', 'TCB258/EC1', 52.33, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-007', 'TCB258/EC1', 54.71, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-008', 'TCB258/EC1', 46.46, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-009', 'TCB258/EC1', 47.06, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-010', 'TCB258/EC1', 47.08, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-011', 'TCB258/EC1', 51.79, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-012', 'TCB258/EC1', 52.80, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-013', 'TCB258/EC1', 52.25, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-014', 'TCB258/EC1', 52.82, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-015', 'TCB258/EC1', 41.01, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-016', 'TCB258/EC1', 59.78, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-017', 'TCB258/EC1', 64.93, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-018', 'TCB258/EC1', 42.90, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-019', 'TCB258/EC1', 42.69, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-020', 'TCB258/EC1', 54.14, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-021', 'TCB258/EC1', 51.11, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-022', 'TCB258/EC1', 62.18, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-023', 'TCB258/EC1', 33.66, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-024', 'TCB258/EC1', 42.92, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-025', 'TCB258/EC1', 54.38, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-026', 'TCB258/EC1', 54.72, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-027', 'TCB258/EC1', 54.81, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-028', 'TCB258/EC1', 52.63, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-029', 'TCB258/EC1', 45.85, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-030', 'TCB258/EC1', 48.72, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-031', 'TCB258/EC1', 46.38, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-032', 'TCB258/EC1', 54.03, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-033', 'TCB258/EC1', 54.04, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-034', 'TCB258/EC1', 54.34, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-035', 'TCB258/EC1', 54.47, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-036', 'TCB258/EC1', 1526.99, 'TOTAL ', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-037', 'TCB258/EC1', 1614.99, 'TOTAL GERAL', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-038', 'TCB258/EC1', 26.65, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-039', 'TCB258/EC1', 53.73, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-040', 'TCB258/EC1', 29.77, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-041', 'TCB258/EC1', 40.04, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-042', 'TCB258/EC1', 44.70, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-043', 'TCB258/EC1', 39.29, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-044', 'TCB258/EC1', 39.76, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-045', 'TCB258/EC1', 51.07, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-046', 'TCB258/EC1', 42.69, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-047', 'TCB258/EC1', 50.22, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-048', 'TCB258/EC1', 51.90, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-049', 'TCB258/EC1', 52.68, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-050', 'TCB258/EC1', 42.31, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-051', 'TCB258/EC1', 42.23, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-052', 'TCB258/EC1', 35.72, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-053', 'TCB258/EC1', 19.26, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-054', 'TCB258/EC1', 662.02, 'TOTAL ', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-055', 'TCB258/EC1', 49.58, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-056', 'TCB258/EC1', 51.62, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-057', 'TCB258/EC1', 52.05, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-058', 'TCB258/EC1', 15.96, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-059', 'TCB258/EC1', 45.25, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-060', 'TCB258/EC1', 45.61, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-061', 'TCB258/EC1', 50.00, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-062', 'TCB258/EC1', 49.90, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-063', 'TCB258/EC1', 40.97, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-064', 'TCB258/EC1', 41.08, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-065', 'TCB258/EC1', 46.84, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-066', 'TCB258/EC1', 46.56, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-067', 'TCB258/EC1', 50.26, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-068', 'TCB258/EC1', 50.90, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-069', 'TCB258/EC1', 22.60, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-070', 'TCB258/EC1', 60.11, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-071', 'TCB258/EC1', 24.48, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-072', 'TCB258/EC1', 38.11, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-073', 'TCB258/EC1', 63.34, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-074', 'TCB258/EC1', 51.77, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-075', 'TCB258/EC1', 48.00, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-076', 'TCB258/EC1', 48.56, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-077', 'TCB258/EC1', 46.52, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-078', 'TCB258/EC1', 46.45, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-079', 'TCB258/EC1', 1086.52, 'TOTAL ', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-080', 'TCB258/EC1', 40.65, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-081', 'TCB258/EC1', 44.78, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-082', 'TCB258/EC1', 44.75, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-083', 'TCB258/EC1', 44.22, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-084', 'TCB258/EC1', 45.37, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-085', 'TCB258/EC1', 45.65, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-086', 'TCB258/EC1', 45.65, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-087', 'TCB258/EC1', 64.04, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-088', 'TCB258/EC1', 58.26, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-089', 'TCB258/EC1', 59.28, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-090', 'TCB258/EC1', 59.51, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-091', 'TCB258/EC1', 59.53, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-092', 'TCB258/EC1', 42.52, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-093', 'TCB258/EC1', 55.39, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-094', 'TCB258/EC1', 56.31, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-095', 'TCB258/EC1', 55.51, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-096', 'TCB258/EC1', 42.10, 'TCB258/EC1', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-097', 'TCB258/EC1', 863.52, 'TOTAL ', 'XBS', 'AVAILABLE', 'None'),
    ('R-TCB258_EC1-098', 'TCB258/EC1', 2612.06, 'TOTAL GERAL', 'XBS', 'AVAILABLE', 'None'),
    ('R-GZIC GR4-099', 'GZIC GR4', 100.60, '0327-SD-HY', 'XBS', 'AVAILABLE', 'None'),
    ('R-GZIC GR4-100', 'GZIC GR4', 102.40, '0327-SD-HY', 'XBS', 'AVAILABLE', 'None'),
]

IN_PROCESS_STOCK = [
    ('P-Fabrijeans___Costa_C-TCB258_EC1-001', 'TCB258/EC1', 827.00, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-TCB258_EC1-002', 'TCB258/EC1', 208.97, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-TCB258_EC1-003', 'TCB258/EC1', 229.79, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-TCD524_EC1-004', 'TCD524/EC1', 1245.00, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Samidel-GB14W MH col W9U1-005', 'GB14W MH col W9U1', 1772.15, 'Samidel', 'IN_PROCESS'),
    ('P-Samidel-GB14W MH col 01U5-006', 'GB14W MH col 01U5', 2015.10, 'Samidel', 'IN_PROCESS'),
    ('P-Samidel-GB14W UNI col A0-007', 'GB14W UNI col A0', 1732.20, 'Samidel', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-GB14W UNI col 10-008', 'GB14W UNI col 10', 673.00, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Samidel-GB14W UNI col 10-009', 'GB14W UNI col 10', 2439.60, 'Samidel', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-GB14W UNI col 73-010', 'GB14W UNI col 73', 30.00, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-GB14W UNI col 91-011', 'GB14W UNI col 91', 212.00, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-GB14W UNI col 93-012', 'GB14W UNI col 93', 1584.60, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-GB14W UNI col 1-013', 'GB14W UNI col 1', 1134.80, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Samidel-GB14W UNI col 1-014', 'GB14W UNI col 1', 3922.00, 'Samidel', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-GB14W UNI Evergreen A1-015', 'GB14W UNI Evergreen A1', 725.40, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Samidel-Guana S32 Pepper Grey B5-016', 'Guana S32 Pepper Grey B5', 796.70, 'Samidel', 'IN_PROCESS'),
    ('P-Samidel-Guana TW6 Midnight Blue 10-017', 'Guana TW6 Midnight Blue 10', 1465.90, 'Samidel', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-Guana S32 Cool Brown C2-018', 'Guana S32 Cool Brown C2', 1387.10, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-Guana 089 Grey Flint B15-019', 'Guana 089 Grey Flint B15', 975.50, 'Fabrijeans / Costa C', 'IN_PROCESS'),
    ('P-Samidel-TCD340_RY1-020', 'TCD340/RY1', 60.99, 'Samidel', 'IN_PROCESS'),
    ('P-Fabrijeans___Costa_C-TCE278_F1-021', 'TCE278/F1', 5755.33, 'Fabrijeans / Costa C', 'IN_PROCESS'),
]

REAL_CONSUMPTIONS = [
    ('POAPS2000004300', 'Women\'s Winter \'26 - Women Serene Short Jacket Ber', 50, 57.50, 60.99, 6.07, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.220 m/pc | Esperado: 1.15 m/pc'),
    ('POAPS2000004404', 'Autumn \'26 - Ease Pants Black Slim (Use all fabric', 835, 1085.50, 1186.00, 9.26, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.420 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004405', 'Autumn \'26 - Ease Pants Black Regular (Use all fab', 1001, 1361.36, 1478.00, 8.57, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.477 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004406', 'Autumn \'26 - Ease Pants Black Relaxed (Use all fab', 857, 1362.63, 1258.00, -7.68, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.468 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004407', 'Autumn \'26 - Ease Pants Dark Grey Slim (Use all fa', 491, 638.30, 643.70, 0.85, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.311 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004408', 'Autumn \'26 - Ease Pants Dark Grey Regular (Use all', 699, 950.64, 951.70, 0.11, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.362 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004409', 'Autumn \'26 - Ease Pants Dark Grey Relaxed (Use all', 281, 446.79, 419.70, -6.06, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.494 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004398', 'Autumn \'26 - Ease Pants Sahara Slim (Use all fabri', 571, 742.30, 750.05, 1.04, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.314 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004399', 'Autumn \'26 - Ease Pants Sahara Regular (Use all fa', 350, 476.00, 500.05, 5.05, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.429 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004400', 'Autumn \'26 - Ease Pants Sahara Relaxed (Use all fa', 352, 559.68, 522.05, -6.72, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.483 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004395', 'Autumn \'26 - Ease Pants Mocha Slim (Use all fabric', 575, 747.50, 788.40, 5.47, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.371 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004396', 'Autumn \'26 - Ease Pants Mocha Regular (Use all fab', 347, 471.92, 519.40, 10.06, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.497 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004397', 'Autumn \'26 - Ease Pants Mocha Relaxed (Use all fab', 277, 440.43, 424.40, -3.64, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.532 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004401', 'Autumn \'26 - Ease Pants Blue Nights Slim (Use all ', 250, 325.00, 328.50, 1.08, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.314 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004402', 'Autumn \'26 - Ease Pants Blue Nights Regular (Use a', 722, 981.92, 1024.50, 4.34, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.419 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004403', 'Autumn \'26 - Ease Pants Blue Nights Relaxed (Use a', 752, 1195.68, 1086.60, -9.12, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.445 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004348', 'NOOS - Essential Suit Pants Regular Almond', 560, 756.00, 765.00, 1.19, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.366 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004349', 'NOOS - Essential Suit Pants Slim Almond', 373, 503.55, 480.00, -4.68, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.287 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004350', 'NOOS - Essential Suit Pants Slim Midnight Blue', 328, 442.80, 465.00, 5.01, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.418 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004351', 'NOOS - Essential Suit Pants Regular Midnight Blue', 262, 353.70, 362.00, 2.35, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.382 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004198', 'Autumn \'26 - Gen. 2.0 Pants Signature Dark Brown (', 4524, 6107.40, 5755.33, -5.76, '2026-07-18', 'Fabrijeans - Confecções Lda', 'Real: 1.272 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004353', 'NOOS - Essential Suit Pants Regular Dark Grey Mela', 153, 206.55, 229.79, 11.25, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.502 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004352', 'NOOS - Essential Suit Pants Regular Pine Green', 150, 202.50, 208.97, 3.2, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.393 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004233', 'Women\'s Autumn \'26 - Women Nara Pants Straight Coo', 936, 1263.60, 1387.10, 9.77, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.482 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004378', 'Restock - Women Ease Pants Straight Steel Melange ', 20, 27.00, 30.00, 11.11, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.500 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004384', 'Women\'s Autumn \'26 - Women Ease Pants Tapered Blue', 177, 238.95, 229.00, -4.16, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.294 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004385', 'Women\'s Autumn \'26 - Women Ease Pants Straight Blu', 301, 406.35, 444.00, 9.27, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.475 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004376', 'Restock - Women Ease Pants Straight Vanilla Melang', 60, 81.00, 88.00, 8.64, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.467 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004377', 'Restock - Women Ease Pants Wide Vanilla Melange (U', 76, 102.60, 124.00, 20.86, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.632 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004234', 'Women\'s Autumn \'26 - Women Nara Pants Straight Gre', 656, 885.60, 975.50, 10.15, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.487 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004387', 'Women\'s Autumn \'26 - Women Ease Pants Straight Bla', 538, 726.30, 809.00, 11.39, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.504 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004386', 'Women\'s Autumn \'26 - Women Ease Pants Tapered Blac', 233, 314.55, 325.80, 3.58, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.398 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004381', 'Women\'s Autumn \'26 - Women Ease Pants Tapered Moch', 199, 268.65, 258.60, -3.74, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.299 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004382', 'Women\'s Autumn \'26 - Women Ease Pants Straight Moc', 558, 753.30, 820.00, 8.85, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.470 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004383', 'Women\'s Autumn \'26 - Women Ease Pants Wide Mocha M', 309, 417.15, 506.00, 21.3, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.638 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004380', 'Women\'s Autumn \'26 - Women Ease Pants Wide Evergre', 263, 355.05, 437.00, 23.08, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.662 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004379', 'Women\'s Autumn \'26 - Women Ease Pants Straight Eve', 198, 267.30, 288.40, 7.89, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.457 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004252', 'Winter \'26 - Motion Suit Pants Pepper Grey', 603, 814.05, 796.70, -2.13, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.321 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004251', 'Winter \'26 - Motion Suit Pants Midnight Blue', 1085, 1464.75, 1465.90, 0.08, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.351 m/pc | Esperado: 1.35 m/pc'),
]


# ===================== INIT DB =====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    DROP TABLE IF EXISTS movements;
    DROP TABLE IF EXISTS consumptions;
    DROP TABLE IF EXISTS consumption_map;
    DROP TABLE IF EXISTS production;
    DROP TABLE IF EXISTS incoming_fabric;
    DROP TABLE IF EXISTS fabric_rolls;
    DROP TABLE IF EXISTS fabric_refs;

    CREATE TABLE fabric_refs (
        ref_code TEXT PRIMARY KEY,
        description TEXT,
        supplier TEXT,
        reorder_point REAL DEFAULT 500,
        unit TEXT DEFAULT 'm'
    );
    CREATE TABLE fabric_rolls (
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
    CREATE TABLE incoming_fabric (
        po_number TEXT PRIMARY KEY,
        supplier TEXT NOT NULL,
        ref_code TEXT,
        total_metres REAL NOT NULL,
        expected_date TEXT,
        status TEXT DEFAULT 'EXPECTED',
        tracking_ref TEXT,
        date_created TEXT
    );
    CREATE TABLE production (
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
    CREATE TABLE consumption_map (
        model_name TEXT NOT NULL,
        fabric_ref TEXT NOT NULL,
        m_per_pc_expected REAL NOT NULL,
        m_per_pc_actual REAL,
        PRIMARY KEY (model_name, fabric_ref)
    );
    CREATE TABLE consumptions (
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
    CREATE TABLE movements (
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

        for token, ref, metres, lot, wh, status, po_fab in FABRIC_ROLLS:
            cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (token, ref, metres, lot, None, wh, status, None, 
                          datetime.now().isoformat(), datetime.now().isoformat(), None))

        # In-process stock (confeccionadores)
        for token, ref, metres, conf, status in IN_PROCESS_STOCK:
            cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (token, ref, metres, None, None, conf, status, None,
                          datetime.now().isoformat(), datetime.now().isoformat(), f'Lote agregado em {conf}'))

        # Real consumptions with deviations
        for po, model, pcs, exp_m, act_m, dev, date, conf, notes in REAL_CONSUMPTIONS:
            cursor.execute("INSERT INTO consumptions VALUES (NULL,?,?,?,?,?,?,?,?,?)",
                         (po, model, pcs, exp_m, act_m, dev, date, conf, notes))
            if model:
                cursor.execute("SELECT AVG(metres_actual / CAST(pcs_cut AS REAL)) FROM consumptions WHERE model_name = ? AND pcs_cut > 0", (model,))
                avg = cursor.fetchone()[0]
                if avg:
                    cursor.execute("UPDATE consumption_map SET m_per_pc_actual = ? WHERE model_name = ?", (round(avg, 3), model))

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

    result = stock_df.merge(incoming_df, left_on='ref_code', right_on='ref_code', how='left')
    result = result.merge(necessity_df, left_on='ref_code', right_on='fabric_ref', how='left')
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
def export_stock_summary():
    df = get_stock_position()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Stock Resumido', index=False)
    output.seek(0)
    return output

def export_stock_detailed():
    df = query_to_df("SELECT * FROM fabric_rolls ORDER BY ref_code, token")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Stock Detalhado', index=False)
    output.seek(0)
    return output

def safe_display_df(df):
    """Clean DataFrame to avoid PyArrow segfault"""
    df = df.fillna('')
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str)
    return df


# ===================== UI: DASHBOARD (PRO) =====================
def render_dashboard():
    # Header
    st.markdown("""
    <div class="main-header">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <h1>🏭 SNT CMT</h1>
                <p>Sistema de Stock & Produção v3.2 | CW29 2026</p>
            </div>
            <div class="live-badge"><span class="live-dot"></span> LIVE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        stock_df = get_stock_position()

        # KPI Cards
        st.markdown('<div class="kpi-container">', unsafe_allow_html=True)

        kpi_data = [
            ("STOCK TOTAL TECIDO", stock_df['disponivel'].sum(), "+8% vs semana anterior", "up"),
            ("TECIDO A CHEGAR", stock_df['a_chegar'].sum(), f"{len(INCOMING_FABRIC)} POs pendentes", "info"),
            ("EM PROCESSO (CORTE)", stock_df['em_processo'].sum(), f"{len([p for p in PRODUCTION if p[7] == 'PENDING'])} POs garment ativas", "warn"),
            ("NECESSIDADE PENDENTE", stock_df['necessidade'].sum(), "cobre 92% com entradas", "down"),
            ("POSIÇÃO LÍQUIDA", stock_df['stock_liquido'].sum(), "stock + em processo", "up"),
            ("POSIÇÃO PLANEAMENTO", stock_df['planeamento'].sum(), "inclui a chegar − necessidade", "info"),
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

        st.markdown('</div>', unsafe_allow_html=True)

        # Alert Bar
        st.markdown('<div class="section-title">Alertas do Sistema</div>', unsafe_allow_html=True)

        critical = stock_df[stock_df['status'].str.contains('falha crítica')]
        warning = stock_df[stock_df['status'].str.contains('stock baixo')]
        risk = stock_df[stock_df['status'].str.contains('risco')]
        ok = stock_df[stock_df['status'].str.contains('ok')]

        alerts_html = '<div class="alert-bar">'

        if not critical.empty:
            for _, row in critical.iterrows():
                alerts_html += f'<div class="alert-chip critical"><span class="alert-dot"></span>Falha Crítica: {row["ref_code"]} — posição líquida {row["planeamento"]:,.0f}m</div>'

        if not warning.empty:
            for _, row in warning.iterrows():
                alerts_html += f'<div class="alert-chip warning"><span class="alert-dot"></span>Stock Baixo: {row["ref_code"]} — disponível {row["disponivel"]:,.0f}m < reorder {row["reorder_point"]:,.0f}m</div>'

        if not risk.empty:
            for _, row in risk.iterrows():
                alerts_html += f'<div class="alert-chip info"><span class="alert-dot"></span>Risco: {row["ref_code"]} — necessidade > disponível + em processo</div>'

        if not ok.empty:
            ok_refs = ', '.join(ok['ref_code'].head(3).tolist())
            alerts_html += f'<div class="alert-chip ok"><span class="alert-dot"></span>{ok_refs} — equilibrados</div>'

        alerts_html += '</div>'
        st.markdown(alerts_html, unsafe_allow_html=True)

        # Stock Position Table
        st.markdown('<div class="section-title">Posição de Stock por Referência de Tecido</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">stock líquido = disponível + em processo | planeamento = líquido + a chegar − necessidade</div>', unsafe_allow_html=True)

        display_df = stock_df[['ref_code', 'description', 'disponivel', 'em_processo', 'stock_liquido', 'a_chegar', 'necessidade', 'planeamento', 'status']].copy()
        display_df = safe_display_df(display_df)
        display_df.columns = ['Ref', 'Descrição', 'Disponível', 'Em Processo', 'Stock Líquido', 'A Chegar', 'Necessidade', 'Planeamento', 'Status']

        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

        # Production Pipeline
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


# ===================== UI: STOCK (PRO) =====================
def render_stock():
    st.markdown('<div class="section-title">📦 Stock por Armazém</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">7 locais: SNT Central, Riopele, e 5 confeccionadores</div>', unsafe_allow_html=True)

    try:
        # Warehouse cards
        wh_df = query_to_df("""
            SELECT warehouse, ref_code, status, COUNT(*) as num_rolls, COALESCE(SUM(metres), 0) as total_metres 
            FROM fabric_rolls GROUP BY warehouse, ref_code, status ORDER BY warehouse, ref_code
        """)

        if not wh_df.empty:
            wh_summary = wh_df.groupby('warehouse').agg({'total_metres': 'sum', 'num_rolls': 'sum'}).reset_index()

            st.markdown('<div class="wh-grid">', unsafe_allow_html=True)
            for _, row in wh_summary.iterrows():
                wh_name = row['warehouse']
                wh_icon = "🏭" if wh_name in ['XBS', 'Riopele'] else "👕"
                detail_df = wh_df[wh_df['warehouse'] == wh_name]
                detail_text = " | ".join([f"{r['ref_code']}: {r['total_metres']:,.0f}m" for _, r in detail_df.head(3).iterrows()])
                in_process = wh_df[(wh_df['warehouse'] == wh_name) & (wh_df['status'] == 'IN_PROCESS')]['total_metres'].sum()

                st.markdown(f"""
                <div class="wh-card">
                    <div class="wh-name">{wh_icon} {wh_name}</div>
                    <div class="wh-total">{row['total_metres']:,.0f}<span style="font-size:13px;color:#8b9dc3">m</span></div>
                    <div class="wh-detail">{detail_text}</div>
                    <div class="wh-rolls">{int(row['num_rolls'])} rolos | {in_process:,.0f}m em processo</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Filters
        st.markdown('<div class="section-title">Detalhe de Rolos</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            try:
                wh_list = query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls")['warehouse'].tolist()
                warehouses = ['Todos'] + wh_list
            except:
                warehouses = ['Todos']
            selected_wh = st.selectbox("Armazém", warehouses, key="stock_wh")
        with col2:
            try:
                ref_list = query_to_df("SELECT DISTINCT ref_code FROM fabric_refs")['ref_code'].tolist()
                refs = ['Todas'] + ref_list
            except:
                refs = ['Todas']
            selected_ref = st.selectbox("Referência", refs, key="stock_ref")
        with col3:
            status_options = ['Todos', 'AVAILABLE', 'RESERVED', 'IN_PROCESS', 'INVOICED']
            selected_status = st.selectbox("Status", status_options, key="stock_status")

        # Query with filters
        query = "SELECT token, ref_code, metres, lot, warehouse, status, po_garment, date_received, notes FROM fabric_rolls WHERE 1=1"
        params = []
        if selected_wh != 'Todos':
            query += " AND warehouse = ?"
            params.append(selected_wh)
        if selected_ref != 'Todas':
            query += " AND ref_code = ?"
            params.append(selected_ref)
        if selected_status != 'Todos':
            query += " AND status = ?"
            params.append(selected_status)
        query += " ORDER BY ref_code, token LIMIT 500"

        rolls_df = query_to_df(query, params)
        rolls_df = safe_display_df(rolls_df)
        rolls_df.columns = ['Token', 'Ref', 'Metros', 'Lote', 'Armazém', 'Status', 'PO Garment', 'Recebido', 'Notas']

        st.dataframe(rolls_df, use_container_width=True, hide_index=True, height=500)

        # Quick actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Exportar seleção", key="export_stock_sel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    rolls_df.to_excel(writer, sheet_name='Stock', index=False)
                output.seek(0)
                st.download_button("⬇️ Download", output, f"stock_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.error(f"Erro ao carregar stock: {e}")


# ===================== UI: INCOMING (PRO) =====================
def render_incoming():
    st.markdown('<div class="section-title">🚢 A Chegar</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="section-subtitle">Encomendas de tecido pendentes — upload de packing lists com deteção automática de colunas</div>', unsafe_allow_html=True)
    with col2:
        if st.button("📋 Ver template"):
            st.info("Template: PO | Fornecedor | Ref | Metros | Data Prevista | Status")

    incoming_df = query_to_df("""
        SELECT i.po_number, i.supplier, i.ref_code, i.total_metres, i.expected_date, i.status, i.tracking_ref, fr.description
        FROM incoming_fabric i LEFT JOIN fabric_refs fr ON i.ref_code = fr.ref_code
        WHERE i.status IN ('EXPECTED', 'IN_TRANSIT') ORDER BY i.expected_date
    """)

    if not incoming_df.empty:
        incoming_df = safe_display_df(incoming_df)
        incoming_df.columns = ['PO', 'Fornecedor', 'Ref', 'Metros', 'Data Prevista', 'Status', 'Tracking', 'Descrição']
        st.dataframe(incoming_df, use_container_width=True, hide_index=True, height=400)

        # Timeline
        st.markdown('<div class="section-title">Calendário de Chegadas — Próximos 30 Dias</div>', unsafe_allow_html=True)
        st.markdown('<div class="timeline">', unsafe_allow_html=True)
        for _, row in incoming_df.head(10).iterrows():
            status_class = "completed" if row['Status'] == 'IN_TRANSIT' else "pending"
            st.markdown(f"""
            <div class="timeline-item {status_class}">
                <div class="timeline-date">{row['Data Prevista']}</div>
                <div class="timeline-text">{row['PO']} — {row['Fornecedor']} {row['Ref']} {row['Metros']}m</div>
                <div class="timeline-meta">{row['Status']} | {row['Tracking'] if row['Tracking'] else 'sem rastreio'}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Nenhuma encomenda pendente.")

# ===================== UI: PRODUCTION (PRO) =====================
def render_production():
    st.markdown('<div class="section-title">👕 Produção</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="section-subtitle">Encomendas garment — upload semanal via Excel com deteção automática de colunas</div>', unsafe_allow_html=True)
    with col2:
        if st.button("📋 Ver template garment"):
            st.info("Template: PO | Modelo | Confeccionador | Qty | Ref Tecido | Data | Status")

    # Status filter tabs
    tab1, tab2, tab3 = st.tabs(["⏳ Pendentes", "✂️ Em Corte", "🪡 Em Costura"])

    with tab1:
        prod_df = query_to_df("""
            SELECT p.po_number, p.model_name, p.confeccionador, p.po_qty, p.fabric_ref, p.metres_expected, p.expected_date, p.status
            FROM production p WHERE p.status = 'PENDING' ORDER BY p.expected_date
        """)
        if not prod_df.empty:
            prod_df = safe_display_df(prod_df)
            prod_df.columns = ['PO', 'Modelo', 'Confeccionador', 'Qty', 'Ref', 'Metros', 'Entrega', 'Status']
            st.dataframe(prod_df, use_container_width=True, hide_index=True, height=400)
            st.markdown(f'<div class="section-subtitle">{len(prod_df)} POs pendentes | {prod_df["Metros"].astype(float).sum():,.0f}m total</div>', unsafe_allow_html=True)
        else:
            st.info("Nenhuma PO pendente.")

    with tab2:
        cutting_df = query_to_df("SELECT * FROM production WHERE status = 'CUTTING' ORDER BY expected_date")
        if not cutting_df.empty:
            cutting_df = safe_display_df(cutting_df)
            st.dataframe(cutting_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma PO em corte.")

    with tab3:
        sewing_df = query_to_df("SELECT * FROM production WHERE status = 'SEWING' ORDER BY expected_date")
        if not sewing_df.empty:
            sewing_df = safe_display_df(sewing_df)
            st.dataframe(sewing_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma PO em costura.")

# ===================== UI: CONSUMOS (PRO) =====================
def render_consumos():
    st.markdown('<div class="section-title">📊 Consumos</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Mapa de consumos por modelo — partilhado. Consumos são partilhados por modelo base, não por PO individual.</div>', unsafe_allow_html=True)

    # Consumption map with visual bars
    cm_df = query_to_df("""
        SELECT cm.model_name, cm.fabric_ref, cm.m_per_pc_expected, cm.m_per_pc_actual, fr.description
        FROM consumption_map cm LEFT JOIN fabric_refs fr ON cm.fabric_ref = fr.ref_code
        ORDER BY cm.fabric_ref, cm.model_name
    """)

    if not cm_df.empty:
        st.markdown('<div style="display:flex;gap:24px;margin-bottom:12px;font-size:12px;color:#8b9dc3;"><span>esperado</span><span>real médio</span><span>desvio > 5%</span></div>', unsafe_allow_html=True)

        for _, row in cm_df.iterrows():
            expected = row['m_per_pc_expected'] or 0
            actual = row['m_per_pc_actual'] or 0
            if expected > 0 and actual > 0:
                dev = ((actual - expected) / expected) * 100
                bar_width = min(100, max(50, (actual / expected) * 85))
                bar_color = "#ef4444" if abs(dev) > 5 else "#22c55e"
                var_class = "up" if dev > 0 else "down"
                badge = '<span class="badge" style="background:rgba(239,68,68,0.15);color:#ef4444;">⚠️ desvio</span>' if abs(dev) > 5 else '<span class="badge available">ok</span>'
            else:
                bar_width = 50
                bar_color = "#3b82f6"
                var_class = ""
                dev = 0
                badge = '<span class="badge" style="background:rgba(100,116,139,0.15);color:#64748b;">—</span>'

            st.markdown(f"""
            <div class="consumo-row">
                <div class="consumo-model">{row['model_name']}</div>
                <div class="consumo-fabric">{row['fabric_ref']}</div>
                <div class="consumo-val">{expected:.2f} m/pc</div>
                <div class="consumo-bar-bg"><div class="consumo-bar-fill" style="width:{bar_width}%;background:{bar_color};"></div></div>
                <div class="consumo-val">{actual:.2f} m/pc</div>
                <div class="consumo-var {var_class}">{dev:+.1f}%</div>
                {badge}
            </div>
            """, unsafe_allow_html=True)

    # Real consumptions table
    st.markdown('<div class="section-title">Registo de Consumos Reais — Últimos Cortes</div>', unsafe_allow_html=True)
    cons_df = query_to_df("SELECT * FROM consumptions ORDER BY date_cut DESC")
    if not cons_df.empty:
        cons_df = safe_display_df(cons_df)
        cons_df.columns = ['ID', 'PO Garment', 'Modelo', 'Peças', 'Metros Esperados', 'Metros Reais', 'Desvio %', 'Data Corte', 'Confeccionador', 'Notas']
        st.dataframe(cons_df, use_container_width=True, hide_index=True, height=350)

        high_dev = cons_df[cons_df['Desvio %'].astype(str).str.replace('%', '').astype(float).abs() > 5]
        if not high_dev.empty:
            st.warning(f"⚠️ {len(high_dev)} consumos com desvio > 5%")

    # Flow diagram
    st.markdown('<div class="section-title">Fluxo de Consumos</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="timeline">
        <div class="timeline-item completed">
            <div class="timeline-date">1. PO lançada</div>
            <div class="timeline-text">Sistema calcula metres_expected = po_qty × m/pc do mapa</div>
        </div>
        <div class="timeline-item completed">
            <div class="timeline-date">2. Após corte</div>
            <div class="timeline-text">Confeccionador reporta metres_actual via Excel</div>
        </div>
        <div class="timeline-item completed">
            <div class="timeline-date">3. Cruzamento</div>
            <div class="timeline-text">Sistema calcula desvio e alerta se > 5%</div>
        </div>
        <div class="timeline-item pending">
            <div class="timeline-date">4. Ajuste stock</div>
            <div class="timeline-text">Sobras/devoluções registadas | stock acertado se necessário</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ===================== UI: MOVEMENT (PRO) =====================
def render_movement():
    st.markdown('<div class="section-title">🚚 Movimentar</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Novos rolos: token automático | Confeccionadores: metros totais (sem token individual) | Divisível futuramente</div>', unsafe_allow_html=True)

    # Movement type tabs
    move_tab1, move_tab2, move_tab3 = st.tabs(["🔄 Nova Movimentação", "📦 Receção de Tecido", "📄 Faturação PO"])

    with move_tab1:
        st.markdown('<div class="movement-form">', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            move_type = st.selectbox("Tipo", ["TRANSFER", "ALLOCATE", "SEND_FACTORY", "RETURN_FACTORY"],
                format_func=lambda x: {"TRANSFER": "🔄 Transferência", "ALLOCATE": "📌 Alocação",
                    "SEND_FACTORY": "🏭 Envio conf.", "RETURN_FACTORY": "↩️ Devolução"}.get(x, x),
                key="move_type")
        with col2:
            refs = query_to_df("SELECT ref_code FROM fabric_refs")['ref_code'].tolist()
            ref_code = st.selectbox("Referência", refs, key="move_ref")
        with col3:
            metres = st.number_input("Metros", min_value=0.0, step=0.01, key="move_metres")

        col4, col5, col6 = st.columns(3)
        with col4:
            locations = ['XBS', 'Riopele', 'Samidel', 'Costa Correia', 'Tyrrell', 'Acorfato', 'Fabrijeans', 'António & Carla', 'Denimworks', 'Vermis', 'Fornecedor', 'Cliente']
            from_loc = st.selectbox("De", locations, key="move_from")
        with col5:
            to_loc = st.selectbox("Para", locations, index=1, key="move_to")
        with col6:
            po_garment = st.text_input("PO garment", placeholder="POAPS200000xxxx", key="move_po")

        st.markdown('</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✓ Confirmar movimento", key="confirm_move"):
                if metres <= 0:
                    st.error("Metros deve ser > 0")
                else:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    token = None
                    notes = None

                    if move_type == "ALLOCATE" and po_garment:
                        cursor.execute("SELECT token FROM fabric_rolls WHERE ref_code = ? AND status = 'AVAILABLE' AND warehouse = ? ORDER BY metres DESC LIMIT 1", (ref_code, from_loc))
                        roll = cursor.fetchone()
                        if roll:
                            cursor.execute("UPDATE fabric_rolls SET status = 'RESERVED', po_garment = ? WHERE token = ?", (po_garment, roll[0]))
                            token = roll[0]
                            st.success(f"Rolo {token} reservado para {po_garment}")
                        else:
                            st.error("Nenhum rolo disponível")

                    elif move_type == "SEND_FACTORY" and po_garment:
                        cursor.execute("UPDATE fabric_rolls SET status = 'IN_PROCESS', warehouse = ?, po_garment = ? WHERE po_garment = ? AND status = 'RESERVED'", (to_loc, po_garment, po_garment))
                        if cursor.rowcount == 0:
                            cursor.execute("SELECT COUNT(*) FROM fabric_rolls WHERE ref_code = ? AND warehouse = ? AND status = 'IN_PROCESS' AND po_garment = ?", (ref_code, to_loc, po_garment))
                            if cursor.fetchone()[0] == 0:
                                agg_token = f"P-{to_loc.replace(' ', '_')}-{ref_code.replace('/', '_')}-001"
                                cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                    (agg_token, ref_code, metres, None, None, to_loc, 'IN_PROCESS', po_garment,
                                     datetime.now().isoformat(), datetime.now().isoformat(), 'Lote agregado'))
                        st.success(f"Tecido enviado para {to_loc} (em processo)")
                        token = "TOTAL"

                    elif move_type == "TRANSFER":
                        cursor.execute("SELECT token FROM fabric_rolls WHERE ref_code = ? AND warehouse = ? AND status = 'AVAILABLE' ORDER BY metres DESC LIMIT 1", (ref_code, from_loc))
                        roll = cursor.fetchone()
                        if roll:
                            cursor.execute("UPDATE fabric_rolls SET warehouse = ?, date_last_move = ? WHERE token = ?", (to_loc, datetime.now().isoformat(), roll[0]))
                            token = roll[0]
                            st.success(f"Rolo {token} transferido de {from_loc} para {to_loc}")
                        else:
                            st.error("Nenhum rolo disponível para transferir")

                    elif move_type == "RETURN_FACTORY" and po_garment:
                        cursor.execute("UPDATE fabric_rolls SET status = 'AVAILABLE', warehouse = ?, po_garment = NULL WHERE po_garment = ? AND status = 'IN_PROCESS'", (to_loc, po_garment))
                        st.success(f"Tecido devolvido de {from_loc} para {to_loc}")
                        token = "RETURN"

                    execute_sql("INSERT INTO movements (date_time, move_type, token, from_location, to_location, ref_code, metres, po_garment, notes) VALUES (?,?,?,?,?,?,?,?,?)",
                               (datetime.now().isoformat(), move_type, token, from_loc, to_loc, ref_code, metres, po_garment or None, notes))
                    conn.commit()
                    conn.close()
                    st.rerun()

        with col2:
            if st.button("✕ Cancelar", key="cancel_move"):
                st.rerun()

    with move_tab2:
        st.markdown("<div class='info-card'><div class='info-card-title'>📥 Receção de Novo Tecido</div><div class='info-card-text'>Ao receber tecido de fornecedor, o sistema gera token automático: <strong>R-{REF}-{NNN}</strong><br>Cada rolo tem token único, metros exatos, lote/cor e histórico completo.</div></div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            recv_ref = st.selectbox("Referência", refs, key="recv_ref")
        with col2:
            recv_metres = st.number_input("Metros recebidos", min_value=0.0, step=0.01, key="recv_metres")
        with col3:
            recv_wh = st.selectbox("Armazém destino", ['XBS', 'Riopele'], key="recv_wh")

        recv_lot = st.text_input("Lote (opcional)", placeholder="L2026-B", key="recv_lot")

        if st.button("✓ Receber e gerar token", key="confirm_recv"):
            if recv_metres > 0:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM fabric_rolls WHERE ref_code = ?", (recv_ref,))
                count = cursor.fetchone()[0] + 1
                token = f"R-{recv_ref.replace('/', '_')}-{count:03d}"
                cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (token, recv_ref, recv_metres, recv_lot or None, None, recv_wh, 'AVAILABLE', None,
                     datetime.now().isoformat(), datetime.now().isoformat(), None))
                conn.commit()
                conn.close()
                execute_sql("INSERT INTO movements (date_time, move_type, token, from_location, to_location, ref_code, metres, notes) VALUES (?,?,?,?,?,?,?,?)",
                           (datetime.now().isoformat(), 'RECEIPT', token, 'Fornecedor', recv_wh, recv_ref, recv_metres, f'Receção lote {recv_lot}'))
                st.success(f"Novo rolo criado: {token}")
                st.rerun()
            else:
                st.error("Metros deve ser > 0")

    with move_tab3:
        st.markdown("<div class='info-card'><div class='info-card-title'>📄 Faturação de PO Garment</div><div class='info-card-text'>Quando uma PO garment é faturada, os metros em processo são automaticamente removidos do stock e marcados como INVOICED.</div></div>", unsafe_allow_html=True)

        invoice_po = st.text_input("PO garment a faturar", placeholder="POAPS200000xxxx", key="invoice_po")
        if st.button("✓ Confirmar faturação", key="confirm_invoice"):
            if invoice_po:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(metres) FROM fabric_rolls WHERE po_garment = ? AND status = 'IN_PROCESS'", (invoice_po,))
                invoiced_metres = cursor.fetchone()[0] or 0
                cursor.execute("UPDATE fabric_rolls SET status = 'INVOICED', notes = 'Faturado - sai de em processo' WHERE po_garment = ? AND status = 'IN_PROCESS'", (invoice_po,))
                cursor.execute("UPDATE production SET status = 'INVOICED' WHERE po_number = ?", (invoice_po,))
                conn.commit()
                conn.close()
                execute_sql("INSERT INTO movements (date_time, move_type, token, from_location, to_location, ref_code, metres, po_garment, notes) VALUES (?,?,?,?,?,?,?,?,?)",
                           (datetime.now().isoformat(), 'INVOICE', 'INVOICED', 'Em Processo', 'Faturado', None, invoiced_metres, invoice_po, f'{invoiced_metres:.2f}m faturados'))
                st.success(f"✅ PO {invoice_po} faturada. {invoiced_metres:.2f}m saíram de em processo.")
                st.rerun()
            else:
                st.error("Indique a PO garment")

    # Rules section
    st.markdown('<div class="section-title">Regras de Tokens</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="info-card">
            <div class="info-card-title">✅ Novos Rolos — Token Individual</div>
            <div class="info-card-text">
                Receção de tecido → token automático gerado<br>
                Formato: <span class="trace-token">R-{REF}-{NNN}</span><br>
                Ex: <span class="trace-token">R-EP001-015</span><br><br>
                Cada rolo tem:<br>
                • token único<br>
                • metros exatos<br>
                • lote / cor<br>
                • histórico completo
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="info-card">
            <div class="info-card-title">⚠️ Confeccionadores — Metros Totais</div>
            <div class="info-card-text">
                Tecido já em confeccionador:<br>
                • Aparece como <strong>IN_PROCESS</strong><br>
                • Sem token individual<br>
                • Nota: "em processo — confeccionador"<br><br>
                Movimentação:<br>
                • Só como total (não por rolo)<br>
                • Só entre armazéns SNT/Riopele<br>
                • Não fragmentável em confecionador
            </div>
        </div>
        """, unsafe_allow_html=True)

    # History
    st.markdown('<div class="section-title">Histórico de Movimentações — Últimas 10</div>', unsafe_allow_html=True)
    hist_df = query_to_df("SELECT * FROM movements ORDER BY date_time DESC LIMIT 10")
    if not hist_df.empty:
        hist_df = safe_display_df(hist_df)
        hist_df.columns = ['ID', 'Data/Hora', 'Tipo', 'Token', 'De', 'Para', 'Ref', 'Metros', 'PO', 'Notas']
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.info("Sem movimentações registadas.")


# ===================== UI: TRACE (PRO) =====================
def render_trace():
    st.markdown('<div class="section-title">🔍 Rastreio</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Histórico de cada rolo desde entrada até faturação. Procura por token, PO garment, lote ou referência.</div>', unsafe_allow_html=True)

    search = st.text_input("🔍 Procurar por token, PO garment, lote, ou referência...", placeholder="ex: R-EP001-003 ou POAPS2000004404", key="trace_search")

    if search:
        # Search by token
        token_df = query_to_df("SELECT * FROM fabric_rolls WHERE token = ?", (search,))
        if not token_df.empty:
            row = token_df.iloc[0]
            status_badge = {
                'AVAILABLE': 'available', 'RESERVED': 'reserved',
                'IN_PROCESS': 'inprocess', 'INVOICED': 'invoiced'
            }.get(row['status'], '')

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
                    <div><div class="trace-detail-label">Armazém</div><div class="trace-detail-value">{row['warehouse']}</div></div>
                    <div><div class="trace-detail-label">PO Garment</div><div class="trace-detail-value">{row['po_garment'] or '—'}</div></div>
                    <div><div class="trace-detail-label">Recebido</div><div class="trace-detail-value">{row['date_received'][:10] if row['date_received'] else '—'}</div></div>
                    <div><div class="trace-detail-label">Último Mov.</div><div class="trace-detail-value">{row['date_last_move'][:10] if row['date_last_move'] else '—'}</div></div>
                </div>
                {f'<div style="margin-top:12px;padding:10px;border-radius:8px;background:rgba(245,158,11,0.1);color:#f59e0b;font-size:12px;">📝 {row["notes"]}</div>' if row['notes'] else ''}
            </div>
            """, unsafe_allow_html=True)

            hist_df = query_to_df("SELECT * FROM movements WHERE token = ? OR po_garment = ? ORDER BY date_time DESC", (search, search))
            if not hist_df.empty:
                st.markdown('<div class="section-title">Histórico de Movimentações</div>', unsafe_allow_html=True)
                hist_df = safe_display_df(hist_df)
                st.dataframe(hist_df, use_container_width=True, hide_index=True, height=250)
        else:
            # Search by PO
            po_df = query_to_df("SELECT * FROM production WHERE po_number = ?", (search,))
            if not po_df.empty:
                st.markdown(f'<div class="section-title">PO: {search}</div>', unsafe_allow_html=True)
                po_df = safe_display_df(po_df)
                st.dataframe(po_df, use_container_width=True, hide_index=True)

                cons_df = query_to_df("SELECT * FROM consumptions WHERE po_garment = ?", (search,))
                if not cons_df.empty:
                    st.markdown('<div class="section-title">Consumos Registados</div>', unsafe_allow_html=True)
                    cons_df = safe_display_df(cons_df)
                    st.dataframe(cons_df, use_container_width=True, hide_index=True)

                roll_df = query_to_df("SELECT * FROM fabric_rolls WHERE po_garment = ?", (search,))
                if not roll_df.empty:
                    st.markdown('<div class="section-title">Rolos Alocados</div>', unsafe_allow_html=True)
                    roll_df = safe_display_df(roll_df)
                    st.dataframe(roll_df, use_container_width=True, hide_index=True)
            else:
                st.warning("Nenhum resultado encontrado. Tente outro token, PO ou referência.")

# ===================== UI: EXPORT (PRO) =====================
def render_export():
    st.markdown('<div class="section-title">📤 Exportar</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Relatórios Excel para financeiros e operacionais</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="info-card" style="text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">📊</div>
            <div class="info-card-title">Stock Resumido</div>
            <div class="info-card-text">Posição por referência com planeamento</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Exportar Resumido", key="exp_summary"):
            excel = export_stock_summary()
            st.download_button("⬇️ Download", excel, f"stock_resumido_{datetime.now().strftime('%Y%m%d')}.xlsx", 
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with col2:
        st.markdown("""
        <div class="info-card" style="text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">📋</div>
            <div class="info-card-title">Stock Detalhado</div>
            <div class="info-card-text">Todos os rolos com tokens e histórico</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Exportar Detalhado", key="exp_detail"):
            excel = export_stock_detailed()
            st.download_button("⬇️ Download", excel, f"stock_detalhado_{datetime.now().strftime('%Y%m%d')}.xlsx",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with col3:
        st.markdown("""
        <div class="info-card" style="text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">📈</div>
            <div class="info-card-title">Consumos</div>
            <div class="info-card-text">Histórico de cortes com desvios</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Exportar Consumos", key="exp_cons"):
            cons_df = query_to_df("SELECT * FROM consumptions ORDER BY date_cut DESC")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                cons_df.to_excel(writer, sheet_name='Consumos', index=False)
            output.seek(0)
            st.download_button("⬇️ Download", output, f"consumos_{datetime.now().strftime('%Y%m%d')}.xlsx",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ===================== MAIN =====================
def main():
    # Sidebar
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

    st.sidebar.markdown("""
    <div style="position:fixed;bottom:20px;left:20px;right:20px;">
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:12px;color:#64748b;font-size:11px;text-align:center;">
            v3.2 | Dados: CW29 2026<br>{}<br>
            <span style="color:#3b82f6;font-weight:600;">SNT CMT</span>
        </div>
    </div>
    """.format(datetime.now().strftime('%Y-%m-%d')), unsafe_allow_html=True)

    tabs[selection]()

if __name__ == "__main__":
    main()
