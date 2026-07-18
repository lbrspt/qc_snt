"""
SNT CMT - Sistema de Stock & Produção v3
Streamlit app with SQLite, auto Excel parsing, token tracking, and stock calculations.
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
import json
from datetime import datetime, timedelta
from io import BytesIO
import re

# Page config
st.set_page_config(
    page_title="SNT CMT - Stock & Produção",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure data directory exists
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "snt_cmt.db")

# ===================== DATABASE SCHEMA =====================
INIT_SQL = """
-- Fabric references (material master)
CREATE TABLE IF NOT EXISTS fabric_refs (
    ref_code TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    reorder_point REAL DEFAULT 500,
    unit TEXT DEFAULT 'm'
);

-- Fabric rolls with unique tokens
CREATE TABLE IF NOT EXISTS fabric_rolls (
    token TEXT PRIMARY KEY,
    ref_code TEXT NOT NULL,
    metres REAL NOT NULL,
    lot TEXT,
    color TEXT,
    warehouse TEXT NOT NULL DEFAULT 'SNT Central',
    status TEXT NOT NULL DEFAULT 'AVAILABLE', -- AVAILABLE, RESERVED, IN_PROCESS, INVOICED
    po_garment TEXT,
    date_received TEXT,
    date_last_move TEXT,
    notes TEXT,
    FOREIGN KEY (ref_code) REFERENCES fabric_refs(ref_code)
);

-- Incoming fabric POs
CREATE TABLE IF NOT EXISTS incoming_fabric (
    po_number TEXT PRIMARY KEY,
    supplier TEXT NOT NULL,
    ref_code TEXT NOT NULL,
    total_metres REAL NOT NULL,
    expected_date TEXT,
    status TEXT DEFAULT 'EXPECTED', -- EXPECTED, IN_TRANSIT, RECEIVED, CANCELLED
    tracking_ref TEXT,
    date_created TEXT,
    FOREIGN KEY (ref_code) REFERENCES fabric_refs(ref_code)
);

-- Production / Garment POs
CREATE TABLE IF NOT EXISTS production (
    po_number TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    confeccionador TEXT NOT NULL,
    po_qty INTEGER NOT NULL,
    fabric_ref TEXT NOT NULL,
    metres_expected REAL,
    expected_date TEXT,
    status TEXT DEFAULT 'PENDING', -- PENDING, CUTTING, SEWING, FINISHED, INVOICED
    date_created TEXT,
    FOREIGN KEY (fabric_ref) REFERENCES fabric_refs(ref_code)
);

-- Consumption map (shared by model)
CREATE TABLE IF NOT EXISTS consumption_map (
    model_name TEXT NOT NULL,
    fabric_ref TEXT NOT NULL,
    m_per_pc_expected REAL NOT NULL,
    m_per_pc_actual REAL,
    PRIMARY KEY (model_name, fabric_ref),
    FOREIGN KEY (fabric_ref) REFERENCES fabric_refs(ref_code)
);

-- Consumption records (actual cuts)
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
    notes TEXT,
    FOREIGN KEY (po_garment) REFERENCES production(po_number)
);

-- Movement history
CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_time TEXT NOT NULL,
    move_type TEXT NOT NULL, -- RECEIPT, TRANSFER, ALLOCATE, SEND_FACTORY, RETURN_FACTORY, INVOICE
    token TEXT,
    from_location TEXT,
    to_location TEXT,
    ref_code TEXT,
    metres REAL,
    po_garment TEXT,
    notes TEXT
);

-- Insert default fabric refs if empty
INSERT OR IGNORE INTO fabric_refs (ref_code, description, reorder_point) VALUES
('EP001', 'Ease Pant Fabric', 1000),
('EP002', 'Ease Pant Black', 500),
('EP003', 'Ease Short Fabric', 300),
('EP004', 'Flow Top Fabric', 800),
('EP005', 'Wrap Dress Fabric', 600),
('EP006', 'Cargo Pant Fabric', 1000);

-- Insert default consumption map if empty
INSERT OR IGNORE INTO consumption_map (model_name, fabric_ref, m_per_pc_expected) VALUES
('Ease Pants Regular', 'EP001', 1.20),
('Ease Pants Black', 'EP002', 1.20),
('Ease Short', 'EP003', 0.95),
('Flow Top', 'EP004', 1.50),
('Wrap Dress', 'EP005', 1.80),
('Cargo Pant', 'EP006', 1.30);
"""

def init_db():
    """Initialize database with schema and seed data."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(INIT_SQL)
    conn.commit()
    conn.close()

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
    lastrowid = cursor.lastrowid
    conn.close()
    return lastrowid

def execute_many(query, params_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany(query, params_list)
    conn.commit()
    conn.close()

# Initialize on first run
init_db()

# ===================== SMART EXCEL PARSER =====================
# Column name mappings for auto-detection
TECIDO_COLUMNS = {
    'po_number': ['po', 'n_po', 'numero_po', 'po_number', 'order_no', 'ordem', 'pedido'],
    'supplier': ['supplier', 'fornecedor', 'vendor', 'fabricante', 'origem'],
    'total_metres': ['metros', 'qty', 'total', 'total_metres', 'quantidade', 'meters', 'comprimento', 'metragem'],
    'expected_date': ['expected_date', 'data_prevista', 'previsao', 'delivery_date', 'entrega', 'data_entrega', 'chegada'],
    'status': ['status', 'estado', 'situacao', 'state'],
    'ref_code': ['ref', 'ref_code', 'referencia', 'ref_tecido', 'fabric_ref', 'material', 'tecido']
}

GARMENT_COLUMNS = {
    'po_number': ['po', 'numero_po', 'po_number', 'n_po', 'order_no', 'pedido'],
    'model_name': ['modelo', 'model_name', 'style', 'style_name', 'descricao', 'description', 'model'],
    'confeccionador': ['confeccionador', 'factory', 'fornecedor_garment', 'supplier', 'fabrica', 'produtor'],
    'po_qty': ['pcs', 'qty', 'po_qty', 'quantidade', 'units', 'pieces', 'unidades'],
    'fabric_ref': ['tecido', 'fabric_ref', 'ref_tecido', 'material', 'ref', 'fabric'],
    'expected_date': ['entrega', 'expected_date', 'data_prevista', 'delivery_date', 'previsao', 'data_entrega'],
    'status': ['status', 'estado', 'situacao', 'state']
}

CONSUMO_COLUMNS = {
    'po_garment': ['po', 'po_number', 'numero_po', 'pedido'],
    'metres_actual': ['consumo_real', 'metres_actual', 'm_real', 'metros_real', 'actual', 'real', 'consumo'],
    'pcs_cut': ['pcs_real', 'qty_produced', 'pcs_produzidas', 'pcs_cut', 'pieces_cut', 'unidades'],
    'date_cut': ['data_corte', 'date_cut', 'corte', 'data'],
    'notes': ['notas', 'notes', 'observacoes', 'observations', 'comentarios']
}

def detect_columns(df, column_map):
    """Detect columns in DataFrame based on possible names. Returns mapping."""
    detected = {}
    df_cols_lower = {c.lower().strip(): c for c in df.columns}
    for standard_name, possible_names in column_map.items():
        for name in possible_names:
            if name.lower() in df_cols_lower:
                detected[standard_name] = df_cols_lower[name.lower()]
                break
    return detected

def parse_fabric_excel(uploaded_file):
    """Parse fabric orders Excel with auto column detection."""
    df = pd.read_excel(uploaded_file)
    detected = detect_columns(df, TECIDO_COLUMNS)
    if not detected:
        return None, "Não foi possível detetar colunas. Verifica os nomes das colunas."

    records = []
    for _, row in df.iterrows():
        try:
            record = {
                'po_number': str(row.get(detected.get('po_number', ''), '')).strip(),
                'supplier': str(row.get(detected.get('supplier', ''), '')).strip(),
                'ref_code': str(row.get(detected.get('ref_code', ''), '')).strip(),
                'total_metres': float(row.get(detected.get('total_metres', ''), 0)),
                'expected_date': str(row.get(detected.get('expected_date', ''), '')).strip(),
                'status': str(row.get(detected.get('status', ''), 'EXPECTED')).strip().upper(),
                'date_created': datetime.now().isoformat()
            }
            if record['po_number'] and record['total_metres'] > 0:
                records.append(record)
        except:
            continue
    return records, None

def parse_garment_excel(uploaded_file):
    """Parse garment orders Excel with auto column detection."""
    df = pd.read_excel(uploaded_file)
    detected = detect_columns(df, GARMENT_COLUMNS)
    if not detected:
        return None, "Não foi possível detetar colunas. Verifica os nomes das colunas."

    records = []
    for _, row in df.iterrows():
        try:
            po_qty = int(float(row.get(detected.get('po_qty', ''), 0)))
            fabric_ref = str(row.get(detected.get('fabric_ref', ''), '')).strip()

            # Auto-calculate metres_expected from consumption map
            metres_expected = None
            if fabric_ref:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT m_per_pc_expected FROM consumption_map WHERE fabric_ref = ?",
                    (fabric_ref,)
                )
                result = cursor.fetchone()
                if result:
                    metres_expected = po_qty * result[0]
                conn.close()

            record = {
                'po_number': str(row.get(detected.get('po_number', ''), '')).strip(),
                'model_name': str(row.get(detected.get('model_name', ''), '')).strip(),
                'confeccionador': str(row.get(detected.get('confeccionador', ''), '')).strip(),
                'po_qty': po_qty,
                'fabric_ref': fabric_ref,
                'metres_expected': metres_expected,
                'expected_date': str(row.get(detected.get('expected_date', ''), '')).strip(),
                'status': str(row.get(detected.get('status', ''), 'PENDING')).strip().upper(),
                'date_created': datetime.now().isoformat()
            }
            if record['po_number'] and record['po_qty'] > 0:
                records.append(record)
        except:
            continue
    return records, None

def parse_consumo_excel(uploaded_file):
    """Parse consumption records Excel with auto column detection."""
    df = pd.read_excel(uploaded_file)
    detected = detect_columns(df, CONSUMO_COLUMNS)
    if not detected:
        return None, "Não foi possível detetar colunas. Verifica os nomes das colunas."

    records = []
    for _, row in df.iterrows():
        try:
            po_garment = str(row.get(detected.get('po_garment', ''), '')).strip()
            metres_actual = float(row.get(detected.get('metres_actual', ''), 0))

            # Get expected consumption from production
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT metres_expected, model_name, confeccionador FROM production WHERE po_number = ?",
                (po_garment,)
            )
            result = cursor.fetchone()
            metres_expected = result[0] if result else None
            model_name = result[1] if result else None
            confeccionador = result[2] if result else None
            conn.close()

            deviation = None
            if metres_expected and metres_expected > 0:
                deviation = round(((metres_actual - metres_expected) / metres_expected) * 100, 2)

            record = {
                'po_garment': po_garment,
                'model_name': model_name,
                'pcs_cut': int(float(row.get(detected.get('pcs_cut', ''), 0))) if detected.get('pcs_cut') else None,
                'metres_expected': metres_expected,
                'metres_actual': metres_actual,
                'deviation_pct': deviation,
                'date_cut': str(row.get(detected.get('date_cut', ''), '')).strip(),
                'confeccionador': confeccionador or str(row.get(detected.get('confeccionador', ''), '')).strip(),
                'notes': str(row.get(detected.get('notes', ''), '')).strip()
            }
            if record['po_garment'] and record['metres_actual'] > 0:
                records.append(record)
        except:
            continue
    return records, None

# ===================== STOCK CALCULATIONS =====================
def get_stock_position():
    """Calculate stock position per fabric reference."""
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

    # Incoming
    incoming_query = """
    SELECT ref_code, COALESCE(SUM(total_metres), 0) as a_chegar
    FROM incoming_fabric
    WHERE status IN ('EXPECTED', 'IN_TRANSIT')
    GROUP BY ref_code
    """
    incoming_df = query_to_df(incoming_query)

    # Necessity (pending production)
    necessity_query = """
    SELECT fabric_ref, COALESCE(SUM(metres_expected), 0) as necessidade
    FROM production
    WHERE status IN ('PENDING', 'CUTTING', 'SEWING')
    GROUP BY fabric_ref
    """
    necessity_df = query_to_df(necessity_query)

    # Merge all
    result = stock_df.merge(incoming_df, left_on='ref_code', right_on='ref_code', how='left')
    result = result.merge(necessity_df, left_on='ref_code', right_on='fabric_ref', how='left')
    result = result.fillna(0)

    result['stock_liquido'] = result['disponivel'] + result['em_processo']
    result['planeamento'] = result['stock_liquido'] + result['a_chegar'] - result['necessidade']

    # Status classification
    def classify_status(row):
        if row['planeamento'] < 0:
            return '🔴 falha crítica'
        elif row['disponivel'] < row['reorder_point']:
            return '🟠 stock baixo'
        elif row['necessidade'] > (row['disponivel'] + row['em_processo']):
            return '🟡 risco'
        else:
            return '🟢 ok'

    result['status'] = result.apply(classify_status, axis=1)
    return result

def get_warehouse_stock():
    """Get stock breakdown by warehouse."""
    query = """
    SELECT 
        warehouse,
        ref_code,
        status,
        COUNT(*) as num_rolls,
        COALESCE(SUM(metres), 0) as total_metres
    FROM fabric_rolls
    GROUP BY warehouse, ref_code, status
    ORDER BY warehouse, ref_code
    """
    return query_to_df(query)

def get_roll_details(warehouse=None, ref_code=None):
    """Get detailed roll list."""
    query = """
    SELECT 
        token, ref_code, metres, lot, color, warehouse, status, 
        po_garment, date_received, notes
    FROM fabric_rolls
    WHERE 1=1
    """
    params = []
    if warehouse:
        query += " AND warehouse = ?"
        params.append(warehouse)
    if ref_code:
        query += " AND ref_code = ?"
        params.append(ref_code)
    query += " ORDER BY date_received DESC"
    return query_to_df(query, params)

def get_token_history(token):
    """Get full movement history for a token."""
    query = """
    SELECT * FROM movements 
    WHERE token = ? OR (po_garment = ? AND token IS NULL)
    ORDER BY date_time DESC
    """
    # Also get PO garment if allocated
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT po_garment FROM fabric_rolls WHERE token = ?", (token,))
    po_result = cursor.fetchone()
    po_garment = po_result[0] if po_result else None
    conn.close()

    if po_garment:
        return query_to_df(query, (token, po_garment))
    return query_to_df("SELECT * FROM movements WHERE token = ? ORDER BY date_time DESC", (token,))

def get_po_garment_history(po_number):
    """Get full history for a garment PO."""
    query = """
    SELECT 
        p.*,
        cm.m_per_pc_expected,
        cm.m_per_pc_actual
    FROM production p
    LEFT JOIN consumption_map cm ON p.model_name = cm.model_name AND p.fabric_ref = cm.fabric_ref
    WHERE p.po_number = ?
    """
    po_df = query_to_df(query, (po_number,))

    # Get consumptions
    cons_query = "SELECT * FROM consumptions WHERE po_garment = ? ORDER BY date_cut DESC"
    cons_df = query_to_df(cons_query, (po_number,))

    # Get movements
    move_query = "SELECT * FROM movements WHERE po_garment = ? ORDER BY date_time DESC"
    move_df = query_to_df(move_query, (po_number,))

    return po_df, cons_df, move_df

# ===================== EXPORT FUNCTIONS =====================
def export_stock_summary():
    """Export stock summary to Excel."""
    df = get_stock_position()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Stock Resumido', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Stock Resumido']

        # Format headers
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#333333', 'font_color': 'white',
            'border': 1
        })
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(0, len(df.columns)-1, 18)

    output.seek(0)
    return output

def export_stock_detailed():
    """Export detailed stock (per roll) to Excel."""
    df = get_roll_details()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Stock Detalhado', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Stock Detalhado']
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#333333', 'font_color': 'white',
            'border': 1
        })
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(0, len(df.columns)-1, 18)
    output.seek(0)
    return output

def export_movements():
    """Export movement history to Excel."""
    df = query_to_df("SELECT * FROM movements ORDER BY date_time DESC")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Movimentacoes', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Movimentacoes']
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#333333', 'font_color': 'white',
            'border': 1
        })
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(0, len(df.columns)-1, 18)
    output.seek(0)
    return output

def export_consumptions():
    """Export consumption map to Excel."""
    df = query_to_df("""
        SELECT 
            cm.model_name,
            cm.fabric_ref,
            cm.m_per_pc_expected,
            cm.m_per_pc_actual,
            CASE 
                WHEN cm.m_per_pc_actual IS NOT NULL AND cm.m_per_pc_expected > 0 
                THEN ROUND(((cm.m_per_pc_actual - cm.m_per_pc_expected) / cm.m_per_pc_expected) * 100, 2)
                ELSE NULL 
            END as desvio_pct
        FROM consumption_map cm
        ORDER BY cm.fabric_ref, cm.model_name
    """)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Consumos', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Consumos']
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#333333', 'font_color': 'white',
            'border': 1
        })
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(0, len(df.columns)-1, 18)
    output.seek(0)
    return output

# ===================== UI COMPONENTS =====================
def render_dashboard():
    st.header("📊 Dashboard")

    stock_df = get_stock_position()

    # KPIs
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    total_disponivel = stock_df['disponivel'].sum()
    total_processo = stock_df['em_processo'].sum()
    total_chegar = stock_df['a_chegar'].sum()
    total_necessidade = stock_df['necessidade'].sum()
    total_liquido = stock_df['stock_liquido'].sum()
    total_planeamento = stock_df['planeamento'].sum()

    with col1:
        st.metric("Stock disponível", f"{total_disponivel:,.0f}m")
    with col2:
        st.metric("Em processo", f"{total_processo:,.0f}m")
    with col3:
        st.metric("A chegar", f"{total_chegar:,.0f}m")
    with col4:
        st.metric("Necessidade", f"{total_necessidade:,.0f}m")
    with col5:
        st.metric("Posição líquida", f"{total_liquido:,.0f}m", delta="stock + processo")
    with col6:
        st.metric("Planeamento", f"{total_planeamento:,.0f}m", delta="+ chegar - nec.")

    # Alerts
    st.subheader("Alertas")
    critical = stock_df[stock_df['status'].str.contains('falha crítica')]
    warning = stock_df[stock_df['status'].str.contains('stock baixo|risco')]
    ok = stock_df[stock_df['status'].str.contains('ok')]

    alert_cols = st.columns(4)
    if not critical.empty:
        with alert_cols[0]:
            for _, row in critical.iterrows():
                st.error(f"🔴 {row['ref_code']}: posição líquida {row['planeamento']:,.0f}m")
    if not warning.empty:
        with alert_cols[1]:
            for _, row in warning.iterrows():
                if 'stock baixo' in row['status']:
                    st.warning(f"🟠 {row['ref_code']}: disp. {row['disponivel']:,.0f}m < reorder {row['reorder_point']:,.0f}m")
                else:
                    st.warning(f"🟡 {row['ref_code']}: nec. > disp. + proc.")
    if not ok.empty:
        with alert_cols[2]:
            ok_refs = ", ".join(ok['ref_code'].tolist())
            st.success(f"🟢 {ok_refs} — equilibrados")

    # Stock position table
    st.subheader("Posição de stock por referência")
    st.caption("stock líquido = disponível + em processo | planeamento = líquido + a chegar − necessidade")

    display_df = stock_df[['ref_code', 'description', 'disponivel', 'reservado', 
                           'em_processo', 'stock_liquido', 'a_chegar', 
                           'necessidade', 'planeamento', 'status']].copy()
    display_df.columns = ['Ref', 'Descrição', 'Disponível', 'Reservado', 'Em processo', 
                          'Stock líquido', 'A chegar', 'Necessidade', 'Planeamento', 'Status']
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Production pipeline
    st.subheader("Pipeline de produção por confeccionador")
    pipeline_df = query_to_df("""
        SELECT 
            confeccionador,
            COUNT(*) as po_ativas,
            SUM(CASE WHEN status = 'CUTTING' THEN po_qty ELSE 0 END) as pcs_corte,
            SUM(CASE WHEN status = 'SEWING' THEN po_qty ELSE 0 END) as pcs_costura,
            SUM(CASE WHEN status = 'FINISHED' THEN po_qty ELSE 0 END) as pcs_acabadas,
            MIN(expected_date) as proxima_entrega,
            CASE 
                WHEN SUM(CASE WHEN status = 'CUTTING' THEN 1 ELSE 0 END) > 0 THEN 'CUTTING'
                WHEN SUM(CASE WHEN status = 'SEWING' THEN 1 ELSE 0 END) > 0 THEN 'SEWING'
                WHEN SUM(CASE WHEN status = 'FINISHED' THEN 1 ELSE 0 END) > 0 THEN 'FINISHED'
                ELSE 'PENDING'
            END as overall_status
        FROM production
        WHERE status IN ('PENDING', 'CUTTING', 'SEWING', 'FINISHED')
        GROUP BY confeccionador
    """)
    st.dataframe(pipeline_df, use_container_width=True, hide_index=True)

def render_stock():
    st.header("📦 Stock por Armazém")

    # Warehouse overview
    wh_df = get_warehouse_stock()
    if not wh_df.empty:
        wh_summary = wh_df.groupby('warehouse').agg({
            'total_metres': 'sum',
            'num_rolls': 'sum'
        }).reset_index()

        cols = st.columns(len(wh_summary))
        for i, (_, row) in enumerate(wh_summary.iterrows()):
            with cols[i]:
                st.metric(row['warehouse'], f"{row['total_metres']:,.0f}m", f"{int(row['num_rolls'])} rolos")

    # Roll details
    st.subheader("Detalhe de rolos")

    col1, col2 = st.columns(2)
    with col1:
        warehouses = ['Todos'] + query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls")['warehouse'].tolist()
        selected_wh = st.selectbox("Armazém", warehouses)
    with col2:
        refs = ['Todas'] + query_to_df("SELECT DISTINCT ref_code FROM fabric_refs")['ref_code'].tolist()
        selected_ref = st.selectbox("Referência", refs)

    wh_filter = None if selected_wh == 'Todos' else selected_wh
    ref_filter = None if selected_ref == 'Todas' else selected_ref

    rolls_df = get_roll_details(wh_filter, ref_filter)
    if not rolls_df.empty:
        st.dataframe(rolls_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum rolo encontrado com estes filtros.")

def render_incoming():
    st.header("🚢 A Chegar")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload Excel de encomendas de tecido", type=['xlsx', 'xls'], key="upload_tecido")
    with col2:
        st.info("Colunas detetadas automaticamente: po, fornecedor, metros, data, status, ref")

    if uploaded:
        records, error = parse_fabric_excel(uploaded)
        if error:
            st.error(error)
        elif records:
            st.write(f"{len(records)} registos detetados:")
            preview_df = pd.DataFrame(records)
            st.dataframe(preview_df, use_container_width=True)

            action = st.radio("Ação:", ["Adicionar novos", "Substituir existentes", "Cancelar"], horizontal=True)
            if action == "Adicionar novos":
                if st.button("✓ Confirmar upload"):
                    execute_many("""
                        INSERT OR IGNORE INTO incoming_fabric 
                        (po_number, supplier, ref_code, total_metres, expected_date, status, date_created)
                        VALUES (:po_number, :supplier, :ref_code, :total_metres, :expected_date, :status, :date_created)
                    """, records)
                    st.success(f"{len(records)} encomendas adicionadas!")
                    st.rerun()
            elif action == "Substituir existentes":
                if st.button("✓ Confirmar substituição"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    for r in records:
                        cursor.execute("DELETE FROM incoming_fabric WHERE po_number = ?", (r['po_number'],))
                    conn.commit()
                    conn.close()
                    execute_many("""
                        INSERT INTO incoming_fabric 
                        (po_number, supplier, ref_code, total_metres, expected_date, status, date_created)
                        VALUES (:po_number, :supplier, :ref_code, :total_metres, :expected_date, :status, :date_created)
                    """, records)
                    st.success(f"{len(records)} encomendas substituídas!")
                    st.rerun()

    # Display incoming orders
    incoming_df = query_to_df("""
        SELECT i.*, fr.description
        FROM incoming_fabric i
        LEFT JOIN fabric_refs fr ON i.ref_code = fr.ref_code
        WHERE i.status IN ('EXPECTED', 'IN_TRANSIT')
        ORDER BY i.expected_date
    """)

    if not incoming_df.empty:
        st.subheader(f"Encomendas pendentes — {len(incoming_df)} POs")
        st.dataframe(incoming_df, use_container_width=True, hide_index=True)

        # Timeline
        st.subheader("Calendário de chegadas")
        for _, row in incoming_df.head(10).iterrows():
            status_icon = "🚚" if row['status'] == 'IN_TRANSIT' else "📦"
            st.write(f"{status_icon} **{row['po_number']}** — {row['supplier']} {row['ref_code']} {row['total_metres']:,.0f}m | {row['expected_date']}")
            if row['tracking_ref']:
                st.caption(f"Rastreio: {row['tracking_ref']}")
    else:
        st.info("Nenhuma encomenda pendente.")

def render_production():
    st.header("👕 Produção")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload Excel de encomendas garment", type=['xlsx', 'xls'], key="upload_garment")
    with col2:
        st.info("Colunas detetadas automaticamente: po, modelo, confeccionador, pcs, tecido, entrega, status")

    if uploaded:
        records, error = parse_garment_excel(uploaded)
        if error:
            st.error(error)
        elif records:
            st.write(f"{len(records)} registos detetados:")
            preview_df = pd.DataFrame(records)
            st.dataframe(preview_df, use_container_width=True)

            action = st.radio("Ação:", ["Adicionar novos", "Substituir existentes", "Cancelar"], horizontal=True, key="prod_action")
            if action == "Adicionar novos":
                if st.button("✓ Confirmar upload", key="prod_add"):
                    execute_many("""
                        INSERT OR IGNORE INTO production 
                        (po_number, model_name, confeccionador, po_qty, fabric_ref, metres_expected, expected_date, status, date_created)
                        VALUES (:po_number, :model_name, :confeccionador, :po_qty, :fabric_ref, :metres_expected, :expected_date, :status, :date_created)
                    """, records)
                    st.success(f"{len(records)} POs adicionadas!")
                    st.rerun()
            elif action == "Substituir existentes":
                if st.button("✓ Confirmar substituição", key="prod_replace"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    for r in records:
                        cursor.execute("DELETE FROM production WHERE po_number = ?", (r['po_number'],))
                    conn.commit()
                    conn.close()
                    execute_many("""
                        INSERT INTO production 
                        (po_number, model_name, confeccionador, po_qty, fabric_ref, metres_expected, expected_date, status, date_created)
                        VALUES (:po_number, :model_name, :confeccionador, :po_qty, :fabric_ref, :metres_expected, :expected_date, :status, :date_created)
                    """, records)
                    st.success(f"{len(records)} POs substituídas!")
                    st.rerun()

    # Display production orders
    prod_df = query_to_df("""
        SELECT p.*, fr.description as fabric_desc
        FROM production p
        LEFT JOIN fabric_refs fr ON p.fabric_ref = fr.ref_code
        WHERE p.status != 'INVOICED'
        ORDER BY p.expected_date
    """)

    if not prod_df.empty:
        st.subheader(f"POs ativas — {len(prod_df)}")

        # Add fabric status
        stock_df = get_stock_position()
        stock_map = dict(zip(stock_df['ref_code'], stock_df['disponivel']))

        def get_fabric_status(row):
            avail = stock_map.get(row['fabric_ref'], 0)
            if row['metres_expected'] and avail >= row['metres_expected']:
                return "✅ disponível"
            elif avail > 0:
                return "🟡 parcial"
            else:
                return "🔴 insuficiente"

        prod_df['tecido_status'] = prod_df.apply(get_fabric_status, axis=1)
        st.dataframe(prod_df[['po_number', 'model_name', 'confeccionador', 'po_qty', 
                              'fabric_ref', 'metres_expected', 'expected_date', 
                              'status', 'tecido_status']], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma PO ativa.")

def render_consumos():
    st.header("📊 Consumos")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload Excel de consumos", type=['xlsx', 'xls'], key="upload_consumo")
    with col2:
        st.info("Colunas detetadas: po, consumo_real, pcs_real, data_corte, notas")

    if uploaded:
        records, error = parse_consumo_excel(uploaded)
        if error:
            st.error(error)
        elif records:
            st.write(f"{len(records)} registos detetados:")
            preview_df = pd.DataFrame(records)
            st.dataframe(preview_df, use_container_width=True)

            action = st.radio("Ação:", ["Adicionar novos", "Substituir existentes", "Cancelar"], horizontal=True, key="cons_action")
            if action == "Adicionar novos":
                if st.button("✓ Confirmar upload", key="cons_add"):
                    execute_many("""
                        INSERT INTO consumptions 
                        (po_garment, model_name, pcs_cut, metres_expected, metres_actual, deviation_pct, date_cut, confeccionador, notes)
                        VALUES (:po_garment, :model_name, :pcs_cut, :metres_expected, :metres_actual, :deviation_pct, :date_cut, :confeccionador, :notes)
                    """, records)

                    # Update consumption map with actual average
                    for r in records:
                        if r['model_name'] and r['metres_actual'] and r['pcs_cut']:
                            actual_mpc = r['metres_actual'] / r['pcs_cut']
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            # Get existing actuals to calculate average
                            cursor.execute("""
                                SELECT AVG(metres_actual / CAST(pcs_cut AS REAL)) 
                                FROM consumptions 
                                WHERE model_name = ? AND pcs_cut > 0
                            """, (r['model_name'],))
                            avg_result = cursor.fetchone()
                            if avg_result and avg_result[0]:
                                cursor.execute("""
                                    UPDATE consumption_map 
                                    SET m_per_pc_actual = ? 
                                    WHERE model_name = ?
                                """, (round(avg_result[0], 3), r['model_name']))
                            conn.commit()
                            conn.close()

                    st.success(f"{len(records)} consumos registados!")
                    st.rerun()

    # Consumption map display
    st.subheader("Mapa de consumos por modelo")
    cm_df = query_to_df("""
        SELECT 
            cm.model_name,
            cm.fabric_ref,
            cm.m_per_pc_expected,
            cm.m_per_pc_actual,
            CASE 
                WHEN cm.m_per_pc_actual IS NOT NULL AND cm.m_per_pc_expected > 0 
                THEN ROUND(((cm.m_per_pc_actual - cm.m_per_pc_expected) / cm.m_per_pc_expected) * 100, 2)
                ELSE NULL 
            END as desvio_pct
        FROM consumption_map cm
        ORDER BY cm.fabric_ref, cm.model_name
    """)

    if not cm_df.empty:
        for _, row in cm_df.iterrows():
            cols = st.columns([3, 1, 1, 1, 1])
            with cols[0]:
                st.write(f"**{row['model_name']}** ({row['fabric_ref']})")
            with cols[1]:
                st.write(f"Esp: {row['m_per_pc_expected']:.2f} m/pc")
            with cols[2]:
                if row['m_per_pc_actual']:
                    st.write(f"Real: {row['m_per_pc_actual']:.2f} m/pc")
                else:
                    st.write("Real: —")
            with cols[3]:
                if row['desvio_pct'] is not None:
                    color = "🔴" if abs(row['desvio_pct']) > 5 else "🟢"
                    st.write(f"{color} {row['desvio_pct']:+.1f}%")
                else:
                    st.write("—")
            with cols[4]:
                if row['desvio_pct'] is not None and abs(row['desvio_pct']) > 5:
                    st.warning("Desvio > 5%")

    # Recent consumption records
    st.subheader("Registos de consumos reais")
    cons_df = query_to_df("SELECT * FROM consumptions ORDER BY date_cut DESC LIMIT 20")
    if not cons_df.empty:
        st.dataframe(cons_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum consumo registado ainda.")

def render_movement():
    st.header("🚚 Movimentar")

    st.subheader("Nova movimentação")

    col1, col2, col3 = st.columns(3)
    with col1:
        move_type = st.selectbox("Tipo", [
            "RECEIPT", "TRANSFER", "ALLOCATE", "SEND_FACTORY", 
            "RETURN_FACTORY", "INVOICE"
        ], format_func=lambda x: {
            "RECEIPT": "📥 Receção de tecido (novo token)",
            "TRANSFER": "🔄 Transferência entre armazéns",
            "ALLOCATE": "📌 Alocação a PO garment",
            "SEND_FACTORY": "🏭 Envio para confeccionador",
            "RETURN_FACTORY": "↩️ Devolução de confeccionador",
            "INVOICE": "📄 Faturação PO (sai de em processo)"
        }.get(x, x))

    with col2:
        refs = query_to_df("SELECT ref_code FROM fabric_refs")['ref_code'].tolist()
        ref_code = st.selectbox("Referência tecido", refs)

    with col3:
        metres = st.number_input("Metros", min_value=0.0, step=0.01, format="%.2f")

    col4, col5, col6 = st.columns(3)
    with col4:
        locations = ['SNT Central', 'Riopele', 'Samidel', 'Textilmoda', 'Confetex', 'Modasul', 'Portex', 'Fornecedor', 'Cliente']
        from_loc = st.selectbox("De (origem)", locations)
    with col5:
        to_loc = st.selectbox("Para (destino)", locations, index=1)
    with col6:
        po_garment = st.text_input("PO garment (se aplicável)", placeholder="POAPS200000xxxx")

    if st.button("✓ Confirmar movimento"):
        if metres <= 0:
            st.error("Metros deve ser maior que zero.")
        else:
            # Generate token for RECEIPT
            token = None
            if move_type == "RECEIPT":
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM fabric_rolls WHERE ref_code = ?", (ref_code,))
                count = cursor.fetchone()[0] + 1
                token = f"R-{ref_code}-{count:03d}"

                # Insert new roll
                cursor.execute("""
                    INSERT INTO fabric_rolls (token, ref_code, metres, warehouse, status, date_received, date_last_move)
                    VALUES (?, ?, ?, ?, 'AVAILABLE', ?, ?)
                """, (token, ref_code, metres, to_loc, datetime.now().isoformat(), datetime.now().isoformat()))
                conn.commit()
                conn.close()
                st.success(f"Novo rolo criado: {token}")

            elif move_type == "ALLOCATE":
                if not po_garment:
                    st.error("PO garment obrigatória para alocação.")
                    return
                # Find available roll and allocate
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT token FROM fabric_rolls 
                    WHERE ref_code = ? AND status = 'AVAILABLE' AND warehouse = ?
                    ORDER BY metres DESC
                    LIMIT 1
                """, (ref_code, from_loc))
                roll = cursor.fetchone()
                if roll:
                    cursor.execute("""
                        UPDATE fabric_rolls 
                        SET status = 'RESERVED', po_garment = ?, date_last_move = ?
                        WHERE token = ?
                    """, (po_garment, datetime.now().isoformat(), roll[0]))
                    conn.commit()
                    token = roll[0]
                    st.success(f"Rolo {token} reservado para {po_garment}")
                else:
                    st.error("Nenhum rolo disponível para alocar.")
                conn.close()

            elif move_type == "SEND_FACTORY":
                if not po_garment:
                    st.error("PO garment obrigatória.")
                    return
                # Move to factory as total (no token tracking at factory)
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE fabric_rolls 
                    SET status = 'IN_PROCESS', warehouse = ?, po_garment = ?, date_last_move = ?
                    WHERE ref_code = ? AND status = 'RESERVED' AND po_garment = ?
                """, (to_loc, po_garment, datetime.now().isoformat(), ref_code, po_garment))
                conn.commit()
                conn.close()
                st.success(f"Tecido enviado para {to_loc} (sem token — total)")
                token = "TOTAL"

            elif move_type == "INVOICE":
                if not po_garment:
                    st.error("PO garment obrigatória.")
                    return
                # Mark as invoiced (leaves IN_PROCESS)
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE fabric_rolls 
                    SET status = 'INVOICED', date_last_move = ?
                    WHERE po_garment = ? AND status = 'IN_PROCESS'
                """, (datetime.now().isoformat(), po_garment))
                cursor.execute("""
                    UPDATE production SET status = 'INVOICED' WHERE po_number = ?
                """, (po_garment,))
                conn.commit()
                conn.close()
                st.success(f"PO {po_garment} faturada. Tecido sai de em processo.")
                token = "INVOICED"

            else:
                # Simple transfer
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE fabric_rolls 
                    SET warehouse = ?, date_last_move = ?
                    WHERE token = ?
                """, (to_loc, datetime.now().isoformat(), token))
                conn.commit()
                conn.close()
                st.success(f"Transferência registada.")

            # Record movement
            execute_sql("""
                INSERT INTO movements (date_time, move_type, token, from_location, to_location, ref_code, metres, po_garment, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), move_type, token, from_loc, to_loc, ref_code, metres, po_garment or None, None))
            st.rerun()

    # Movement history
    st.subheader("Histórico de movimentações")
    move_df = query_to_df("SELECT * FROM movements ORDER BY date_time DESC LIMIT 50")
    if not move_df.empty:
        st.dataframe(move_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma movimentação registada.")

def render_trace():
    st.header("🔍 Rastreio")

    search = st.text_input("Procurar por token, PO garment, lote ou referência", placeholder="ex: R-EP001-003 ou POAPS2000004405")

    if search:
        # Search by token
        token_df = query_to_df("SELECT * FROM fabric_rolls WHERE token = ?", (search,))
        if not token_df.empty:
            st.subheader(f"Token: {search}")
            row = token_df.iloc[0]

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Referência", row['ref_code'])
            with col2:
                st.metric("Metros", f"{row['metres']:.2f}m")
            with col3:
                st.metric("Lote", row['lot'] or "—")
            with col4:
                st.metric("Cor", row['color'] or "—")

            st.metric("Status", row['status'])
            st.metric("Armazém", row['warehouse'])
            if row['po_garment']:
                st.metric("PO Garment", row['po_garment'])

            # History
            st.subheader("Histórico de movimentações")
            hist_df = get_token_history(search)
            if not hist_df.empty:
                st.dataframe(hist_df, use_container_width=True, hide_index=True)
            else:
                st.info("Sem histórico de movimentações.")
            return

        # Search by PO garment
        po_df = query_to_df("SELECT * FROM production WHERE po_number = ?", (search,))
        if not po_df.empty:
            st.subheader(f"PO Garment: {search}")
            po_info, cons_df, move_df = get_po_garment_history(search)

            if not po_info.empty:
                row = po_info.iloc[0]
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Modelo", row['model_name'])
                with col2:
                    st.metric("Confeccionador", row['confeccionador'])
                with col3:
                    st.metric("Quantidade", f"{row['po_qty']} pcs")
                with col4:
                    st.metric("Status", row['status'])

            if not cons_df.empty:
                st.subheader("Consumos registados")
                st.dataframe(cons_df, use_container_width=True, hide_index=True)

            if not move_df.empty:
                st.subheader("Movimentações de tecido")
                st.dataframe(move_df, use_container_width=True, hide_index=True)
            return

        st.warning("Nenhum resultado encontrado.")

def render_export():
    st.header("📤 Exportar")

    st.subheader("Relatórios para financeiros")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Exportar stock resumido"):
            excel = export_stock_summary()
            st.download_button(
                label="⬇️ Download Excel",
                data=excel,
                file_name=f"stock_resumido_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        if st.button("📋 Exportar stock detalhado"):
            excel = export_stock_detailed()
            st.download_button(
                label="⬇️ Download Excel",
                data=excel,
                file_name=f"stock_detalhado_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with col2:
        if st.button("🚚 Exportar movimentações"):
            excel = export_movements()
            st.download_button(
                label="⬇️ Download Excel",
                data=excel,
                file_name=f"movimentacoes_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        if st.button("📊 Exportar consumos"):
            excel = export_consumptions()
            st.download_button(
                label="⬇️ Download Excel",
                data=excel,
                file_name=f"consumos_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.info("Os ficheiros Excel são simples, sem macros, prontos para partilhar com financeiros.")

# ===================== MAIN =====================
def main():
    st.sidebar.title("🏭 SNT CMT")
    st.sidebar.caption("Sistema de Stock & Produção")

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

    selection = st.sidebar.radio("Navegar", list(tabs.keys()))
    tabs[selection]()

    st.sidebar.markdown("---")
    st.sidebar.caption(f"v3.0 | {datetime.now().strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main()
