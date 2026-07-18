"""
SNT CMT - Sistema de Stock & Produção v3.1
Real production data from CW29 2026
Features: In-process stock, real consumptions, invoice mechanism
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from io import BytesIO
import re

st.set_page_config(
    page_title="SNT CMT - Stock & Produção",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "snt_cmt.db")

# ===================== DB CONNECTION =====================
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
    ('POAPS2000004300', 'Women''s Winter ''26 - Women Serene Short Jacket Ber', 50, 57.50, 60.99, 6.07, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.220 m/pc | Esperado: 1.15 m/pc'),
    ('POAPS2000004404', 'Autumn ''26 - Ease Pants Black Slim (Use all fabric', 835, 1085.50, 1186.00, 9.26, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.420 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004405', 'Autumn ''26 - Ease Pants Black Regular (Use all fab', 1001, 1361.36, 1478.00, 8.57, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.477 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004406', 'Autumn ''26 - Ease Pants Black Relaxed (Use all fab', 857, 1362.63, 1258.00, -7.68, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.468 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004407', 'Autumn ''26 - Ease Pants Dark Grey Slim (Use all fa', 491, 638.30, 643.70, 0.85, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.311 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004408', 'Autumn ''26 - Ease Pants Dark Grey Regular (Use all', 699, 950.64, 951.70, 0.11, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.362 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004409', 'Autumn ''26 - Ease Pants Dark Grey Relaxed (Use all', 281, 446.79, 419.70, -6.06, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.494 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004398', 'Autumn ''26 - Ease Pants Sahara Slim (Use all fabri', 571, 742.30, 750.05, 1.04, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.314 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004399', 'Autumn ''26 - Ease Pants Sahara Regular (Use all fa', 350, 476.00, 500.05, 5.05, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.429 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004400', 'Autumn ''26 - Ease Pants Sahara Relaxed (Use all fa', 352, 559.68, 522.05, -6.72, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.483 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004395', 'Autumn ''26 - Ease Pants Mocha Slim (Use all fabric', 575, 747.50, 788.40, 5.47, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.371 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004396', 'Autumn ''26 - Ease Pants Mocha Regular (Use all fab', 347, 471.92, 519.40, 10.06, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.497 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004397', 'Autumn ''26 - Ease Pants Mocha Relaxed (Use all fab', 277, 440.43, 424.40, -3.64, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.532 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004401', 'Autumn ''26 - Ease Pants Blue Nights Slim (Use all ', 250, 325.00, 328.50, 1.08, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.314 m/pc | Esperado: 1.30 m/pc'),
    ('POAPS2000004402', 'Autumn ''26 - Ease Pants Blue Nights Regular (Use a', 722, 981.92, 1024.50, 4.34, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.419 m/pc | Esperado: 1.36 m/pc'),
    ('POAPS2000004403', 'Autumn ''26 - Ease Pants Blue Nights Relaxed (Use a', 752, 1195.68, 1086.60, -9.12, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.445 m/pc | Esperado: 1.59 m/pc'),
    ('POAPS2000004348', 'NOOS - Essential Suit Pants Regular Almond', 560, 756.00, 765.00, 1.19, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.366 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004349', 'NOOS - Essential Suit Pants Slim Almond', 373, 503.55, 480.00, -4.68, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.287 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004350', 'NOOS - Essential Suit Pants Slim Midnight Blue', 328, 442.80, 465.00, 5.01, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.418 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004351', 'NOOS - Essential Suit Pants Regular Midnight Blue', 262, 353.70, 362.00, 2.35, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.382 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004198', 'Autumn ''26 - Gen. 2.0 Pants Signature Dark Brown (', 4524, 6107.40, 5755.33, -5.76, '2026-07-18', 'Fabrijeans - Confecções Lda', 'Real: 1.272 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004353', 'NOOS - Essential Suit Pants Regular Dark Grey Mela', 153, 206.55, 229.79, 11.25, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.502 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004352', 'NOOS - Essential Suit Pants Regular Pine Green', 150, 202.50, 208.97, 3.2, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.393 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004233', 'Women''s Autumn ''26 - Women Nara Pants Straight Coo', 936, 1263.60, 1387.10, 9.77, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.482 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004378', 'Restock - Women Ease Pants Straight Steel Melange ', 20, 27.00, 30.00, 11.11, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.500 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004384', 'Women''s Autumn ''26 - Women Ease Pants Tapered Blue', 177, 238.95, 229.00, -4.16, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.294 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004385', 'Women''s Autumn ''26 - Women Ease Pants Straight Blu', 301, 406.35, 444.00, 9.27, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.475 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004376', 'Restock - Women Ease Pants Straight Vanilla Melang', 60, 81.00, 88.00, 8.64, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.467 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004377', 'Restock - Women Ease Pants Wide Vanilla Melange (U', 76, 102.60, 124.00, 20.86, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.632 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004234', 'Women''s Autumn ''26 - Women Nara Pants Straight Gre', 656, 885.60, 975.50, 10.15, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.487 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004387', 'Women''s Autumn ''26 - Women Ease Pants Straight Bla', 538, 726.30, 809.00, 11.39, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.504 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004386', 'Women''s Autumn ''26 - Women Ease Pants Tapered Blac', 233, 314.55, 325.80, 3.58, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.398 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004381', 'Women''s Autumn ''26 - Women Ease Pants Tapered Moch', 199, 268.65, 258.60, -3.74, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.299 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004382', 'Women''s Autumn ''26 - Women Ease Pants Straight Moc', 558, 753.30, 820.00, 8.85, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.470 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004383', 'Women''s Autumn ''26 - Women Ease Pants Wide Mocha M', 309, 417.15, 506.00, 21.3, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.638 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004380', 'Women''s Autumn ''26 - Women Ease Pants Wide Evergre', 263, 355.05, 437.00, 23.08, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.662 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004379', 'Women''s Autumn ''26 - Women Ease Pants Straight Eve', 198, 267.30, 288.40, 7.89, '2026-07-18', 'Costa Correia & Ca Lda.', 'Real: 1.457 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004252', 'Winter ''26 - Motion Suit Pants Pepper Grey', 603, 814.05, 796.70, -2.13, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.321 m/pc | Esperado: 1.35 m/pc'),
    ('POAPS2000004251', 'Winter ''26 - Motion Suit Pants Midnight Blue', 1085, 1464.75, 1465.90, 0.08, '2026-07-18', 'SAMIDEL - CONFECÇÕES LDA', 'Real: 1.351 m/pc | Esperado: 1.35 m/pc'),
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

# ===================== UI: DASHBOARD =====================
def render_dashboard():
    st.header("📊 Dashboard - SNT CMT")
    stock_df = get_stock_position()

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1: st.metric("Disponível", f"{stock_df['disponivel'].sum():,.0f}m")
    with col2: st.metric("Em processo", f"{stock_df['em_processo'].sum():,.0f}m")
    with col3: st.metric("A chegar", f"{stock_df['a_chegar'].sum():,.0f}m")
    with col4: st.metric("Necessidade", f"{stock_df['necessidade'].sum():,.0f}m")
    with col5: st.metric("Líquido", f"{stock_df['stock_liquido'].sum():,.0f}m")
    with col6: st.metric("Planeamento", f"{stock_df['planeamento'].sum():,.0f}m")

    st.subheader("Alertas")
    critical = stock_df[stock_df['status'].str.contains('falha crítica')]
    warning = stock_df[stock_df['status'].str.contains('stock baixo|risco')]
    if not critical.empty:
        for _, row in critical.iterrows():
            st.error(f"🔴 {row['ref_code']}: {row['planeamento']:,.0f}m")
    if not warning.empty:
        for _, row in warning.iterrows():
            st.warning(f"🟡 {row['ref_code']}: disp {row['disponivel']:,.0f}m < reorder {row['reorder_point']:,.0f}m")

    st.subheader("Posição de stock")
    display_df = stock_df[['ref_code', 'description', 'disponivel', 'em_processo', 'stock_liquido', 'a_chegar', 'necessidade', 'planeamento', 'status']]
    display_df.columns = ['Ref', 'Descrição', 'Disponível', 'Em Processo', 'Stock Líquido', 'A Chegar', 'Necessidade', 'Planeamento', 'Status']
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ===================== UI: STOCK =====================
def render_stock():
    st.header("📦 Stock por Armazém")

    wh_df = query_to_df("SELECT warehouse, ref_code, status, COUNT(*) as num_rolls, COALESCE(SUM(metres), 0) as total_metres FROM fabric_rolls GROUP BY warehouse, ref_code, status ORDER BY warehouse, ref_code")

    if not wh_df.empty:
        wh_summary = wh_df.groupby('warehouse').agg({'total_metres': 'sum', 'num_rolls': 'sum'}).reset_index()
        cols = st.columns(min(len(wh_summary), 4))
        for i, (_, row) in enumerate(wh_summary.iterrows()):
            with cols[i % 4]:
                st.metric(row['warehouse'], f"{row['total_metres']:,.0f}m", f"{int(row['num_rolls'])} rolos")

    st.subheader("Detalhe de rolos")

    col1, col2 = st.columns(2)
    with col1:
        warehouses = ['Todos'] + query_to_df("SELECT DISTINCT warehouse FROM fabric_rolls")['warehouse'].tolist()
        selected_wh = st.selectbox("Armazém", warehouses)
    with col2:
        refs = ['Todas'] + query_to_df("SELECT DISTINCT ref_code FROM fabric_refs")['ref_code'].tolist()
        selected_ref = st.selectbox("Referência", refs)

    query = "SELECT * FROM fabric_rolls WHERE 1=1"
    params = []
    if selected_wh != 'Todos':
        query += " AND warehouse = ?"
        params.append(selected_wh)
    if selected_ref != 'Todas':
        query += " AND ref_code = ?"
        params.append(selected_ref)
    query += " ORDER BY ref_code, token LIMIT 200"

    rolls_df = query_to_df(query, params)
    st.dataframe(rolls_df, use_container_width=True, hide_index=True)

# ===================== UI: INCOMING =====================
def render_incoming():
    st.header("🚢 A Chegar")
    incoming_df = query_to_df("SELECT i.*, fr.description FROM incoming_fabric i LEFT JOIN fabric_refs fr ON i.ref_code = fr.ref_code WHERE i.status IN ('EXPECTED', 'IN_TRANSIT') ORDER BY i.expected_date")
    if not incoming_df.empty:
        st.subheader(f"Encomendas pendentes — {len(incoming_df)} POs")
        st.dataframe(incoming_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma encomenda pendente.")

# ===================== UI: PRODUCTION =====================
def render_production():
    st.header("👕 Produção")
    prod_df = query_to_df("SELECT p.*, fr.description as fabric_desc FROM production p LEFT JOIN fabric_refs fr ON p.fabric_ref = fr.ref_code WHERE p.status != 'INVOICED' ORDER BY p.expected_date")
    if not prod_df.empty:
        st.subheader(f"POs ativas — {len(prod_df)}")
        st.dataframe(prod_df[['po_number', 'model_name', 'confeccionador', 'po_qty', 'fabric_ref', 'metres_expected', 'expected_date', 'status']], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma PO ativa.")

# ===================== UI: CONSUMOS =====================
def render_consumos():
    st.header("📊 Consumos")

    cm_df = query_to_df("SELECT cm.*, fr.description FROM consumption_map cm LEFT JOIN fabric_refs fr ON cm.fabric_ref = fr.ref_code ORDER BY cm.fabric_ref, cm.model_name")
    if not cm_df.empty:
        st.subheader("Mapa de consumos")
        for _, row in cm_df.iterrows():
            cols = st.columns([3, 1, 1, 1])
            with cols[0]: st.write(f"**{row['model_name']}** ({row['fabric_ref']})")
            with cols[1]: st.write(f"Esp: {row['m_per_pc_expected']:.2f} m/pc")
            with cols[2]: 
                if row['m_per_pc_actual']:
                    color = "🔴" if abs(row['m_per_pc_actual'] - row['m_per_pc_expected']) / row['m_per_pc_expected'] > 0.05 else "🟢"
                    st.write(f"{color} Real: {row['m_per_pc_actual']:.2f} m/pc")
                else: st.write("Real: —")
            with cols[3]:
                if row['m_per_pc_actual'] and row['m_per_pc_expected'] > 0:
                    dev = ((row['m_per_pc_actual'] - row['m_per_pc_expected']) / row['m_per_pc_expected']) * 100
                    st.write(f"{dev:+.1f}%")

    st.subheader("Consumos reais (CW28)")
    cons_df = query_to_df("SELECT * FROM consumptions ORDER BY date_cut DESC")
    if not cons_df.empty:
        st.dataframe(cons_df[['po_garment', 'model_name', 'pcs_cut', 'metres_expected', 'metres_actual', 'deviation_pct', 'confeccionador', 'notes']], use_container_width=True, hide_index=True)

        high_dev = cons_df[cons_df['deviation_pct'].abs() > 5]
        if not high_dev.empty:
            st.warning(f"⚠️ {len(high_dev)} consumos com desvio > 5%")
            for _, row in high_dev.iterrows():
                st.write(f"  • {row['po_garment']}: {row['deviation_pct']:+.1f}% ({row['metres_actual']:.1f}m vs {row['metres_expected']:.1f}m)")

# ===================== UI: MOVEMENT =====================
def render_movement():
    st.header("🚚 Movimentar")

    st.subheader("Nova movimentação")
    col1, col2, col3 = st.columns(3)
    with col1:
        move_type = st.selectbox("Tipo", ["RECEIPT", "TRANSFER", "ALLOCATE", "SEND_FACTORY", "RETURN_FACTORY", "INVOICE"],
            format_func=lambda x: {"RECEIPT": "📥 Receção", "TRANSFER": "🔄 Transferência", "ALLOCATE": "📌 Alocação",
                "SEND_FACTORY": "🏭 Envio conf.", "RETURN_FACTORY": "↩️ Devolução", "INVOICE": "📄 Faturação (sai de em processo)"}.get(x, x))
    with col2:
        refs = query_to_df("SELECT ref_code FROM fabric_refs")['ref_code'].tolist()
        ref_code = st.selectbox("Referência", refs)
    with col3:
        metres = st.number_input("Metros", min_value=0.0, step=0.01)

    col4, col5, col6 = st.columns(3)
    with col4:
        locations = ['XBS', 'Riopele', 'Samidel', 'Costa Correia', 'Tyrrell', 'Acorfato', 'Fabrijeans', 'António & Carla', 'Denimworks', 'Vermis', 'Fornecedor', 'Cliente']
        from_loc = st.selectbox("De", locations)
    with col5:
        to_loc = st.selectbox("Para", locations, index=1)
    with col6:
        po_garment = st.text_input("PO garment", placeholder="POAPS200000xxxx")

    if st.button("✓ Confirmar movimento"):
        if metres <= 0:
            st.error("Metros deve ser > 0")
        else:
            token = None
            notes = None

            if move_type == "RECEIPT":
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM fabric_rolls WHERE ref_code = ?", (ref_code,))
                count = cursor.fetchone()[0] + 1
                token = f"R-{ref_code.replace('/', '_')}-{count:03d}"
                cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (token, ref_code, metres, None, None, to_loc, 'AVAILABLE', None, 
                     datetime.now().isoformat(), datetime.now().isoformat(), None))
                conn.commit()
                conn.close()
                st.success(f"Novo rolo: {token}")

            elif move_type == "ALLOCATE" and po_garment:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT token FROM fabric_rolls WHERE ref_code = ? AND status = 'AVAILABLE' AND warehouse = ? ORDER BY metres DESC LIMIT 1", (ref_code, from_loc))
                roll = cursor.fetchone()
                if roll:
                    cursor.execute("UPDATE fabric_rolls SET status = 'RESERVED', po_garment = ? WHERE token = ?", (po_garment, roll[0]))
                    conn.commit()
                    token = roll[0]
                    st.success(f"Rolo {token} reservado para {po_garment}")
                else:
                    st.error("Nenhum rolo disponível")
                conn.close()

            elif move_type == "SEND_FACTORY" and po_garment:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE fabric_rolls SET status = 'IN_PROCESS', warehouse = ?, po_garment = ? WHERE po_garment = ? AND status = 'RESERVED'", (to_loc, po_garment, po_garment))
                if cursor.rowcount == 0:
                    cursor.execute("SELECT COUNT(*) FROM fabric_rolls WHERE ref_code = ? AND warehouse = ? AND status = 'IN_PROCESS' AND po_garment = ?", (ref_code, to_loc, po_garment))
                    if cursor.fetchone()[0] == 0:
                        agg_token = f"P-{to_loc.replace(' ', '_')}-{ref_code.replace('/', '_')}-001"
                        cursor.execute("INSERT INTO fabric_rolls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (agg_token, ref_code, metres, None, None, to_loc, 'IN_PROCESS', po_garment,
                             datetime.now().isoformat(), datetime.now().isoformat(), 'Lote agregado'))
                conn.commit()
                conn.close()
                st.success(f"Tecido enviado para {to_loc} (em processo)")
                token = "TOTAL"

            elif move_type == "INVOICE" and po_garment:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(metres) FROM fabric_rolls WHERE po_garment = ? AND status = 'IN_PROCESS'", (po_garment,))
                invoiced_metres = cursor.fetchone()[0] or 0
                cursor.execute("UPDATE fabric_rolls SET status = 'INVOICED', notes = 'Faturado - sai de em processo' WHERE po_garment = ? AND status = 'IN_PROCESS'", (po_garment,))
                cursor.execute("UPDATE production SET status = 'INVOICED' WHERE po_number = ?", (po_garment,))
                conn.commit()
                conn.close()
                st.success(f"✅ PO {po_garment} faturada. {invoiced_metres:.2f}m saíram de em processo.")
                token = "INVOICED"
                notes = f"{invoiced_metres:.2f}m faturados"

            elif move_type == "RETURN_FACTORY" and po_garment:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE fabric_rolls SET status = 'AVAILABLE', warehouse = ?, po_garment = NULL WHERE po_garment = ? AND status = 'IN_PROCESS'", (to_loc, po_garment))
                conn.commit()
                conn.close()
                st.success(f"Tecido devolvido de {from_loc} para {to_loc}")
                token = "RETURN"

            execute_sql("INSERT INTO movements (date_time, move_type, token, from_location, to_location, ref_code, metres, po_garment, notes) VALUES (?,?,?,?,?,?,?,?,?)",
                       (datetime.now().isoformat(), move_type, token, from_loc, to_loc, ref_code, metres, po_garment or None, notes))
            st.rerun()

# ===================== UI: TRACE =====================
def render_trace():
    st.header("🔍 Rastreio")
    search = st.text_input("Procurar por token, PO garment, ou referência", placeholder="ex: P-Samidel-GB14W-001")

    if search:
        token_df = query_to_df("SELECT * FROM fabric_rolls WHERE token = ?", (search,))
        if not token_df.empty:
            st.subheader(f"Token: {search}")
            row = token_df.iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Ref", row['ref_code'])
            with col2: st.metric("Metros", f"{row['metres']:.2f}m")
            with col3: st.metric("Status", row['status'])
            with col4: st.metric("Armazém", row['warehouse'])
            if row['notes']:
                st.info(f"Notas: {row['notes']}")

            hist_df = query_to_df("SELECT * FROM movements WHERE token = ? OR po_garment = ? ORDER BY date_time DESC", (search, search))
            if not hist_df.empty:
                st.subheader("Histórico de movimentações")
                st.dataframe(hist_df, use_container_width=True)
        else:
            po_df = query_to_df("SELECT * FROM production WHERE po_number = ?", (search,))
            if not po_df.empty:
                st.subheader(f"PO: {search}")
                st.dataframe(po_df, use_container_width=True)
                cons_df = query_to_df("SELECT * FROM consumptions WHERE po_garment = ?", (search,))
                if not cons_df.empty:
                    st.subheader("Consumos registados")
                    st.dataframe(cons_df, use_container_width=True)
            else:
                st.warning("Nenhum resultado")

# ===================== UI: EXPORT =====================
def render_export():
    st.header("📤 Exportar")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Stock resumido"):
            excel = export_stock_summary()
            st.download_button("⬇️ Download", excel, f"stock_resumido_{datetime.now().strftime('%Y%m%d')}.xlsx", 
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        if st.button("📋 Stock detalhado"):
            excel = export_stock_detailed()
            st.download_button("⬇️ Download", excel, f"stock_detalhado_{datetime.now().strftime('%Y%m%d')}.xlsx",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with col2:
        if st.button("📊 Consumos"):
            cons_df = query_to_df("SELECT * FROM consumptions ORDER BY date_cut DESC")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                cons_df.to_excel(writer, sheet_name='Consumos', index=False)
            output.seek(0)
            st.download_button("⬇️ Download", output, f"consumos_{datetime.now().strftime('%Y%m%d')}.xlsx",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ===================== MAIN =====================
def main():
    st.sidebar.title("🏭 SNT CMT")
    st.sidebar.caption("Sistema de Stock & Produção v3.1")

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
    st.sidebar.caption(f"v3.1 | Dados: CW29 2026 | {datetime.now().strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main()
