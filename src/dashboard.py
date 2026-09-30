import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(page_title="HealX Dashboard", layout="wide")
st.title("Enterprise Self-Healing XML Dashboard")

# SQLite DB Path Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "healx_db.db")

if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(BASE_DIR, "healx.db")

try:
    conn = sqlite3.connect(DB_PATH)
    
    # Check for 'healx_audit_logs' or 'payloads'
    table_check = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND (name='healx_audit_logs' OR name='payloads');", conn
    )

    if table_check.empty:
        st.warning("⚠️ அட்டவணைகள் எதுவும் கிடைக்கவில்லை. Worker-ஐ இயக்கி புதிய மெசேஜ் அனுப்பவும்.")
    else:
        actual_table = table_check['name'].iloc[0]
        df = pd.read_sql_query(f"SELECT * FROM {actual_table}", conn)

        col1, col2, col3 = st.columns(3)

        total_processed = len(df)
        
        # Check status column
        status_col = 'status' if 'status' in df.columns else None
        healed_count = len(df[df[status_col] == 'HEALED']) if status_col else 0
        
        # Calculate fine savings from DB or compute dynamically
        if 'est_fine_prevented_usd' in df.columns:
            total_saved = df['est_fine_prevented_usd'].sum()
        else:
            total_saved = healed_count * 150.0

        col1.metric("Total Processed", total_processed)
        col2.metric("Auto-Healed", healed_count)
        col3.metric("Fine Saved ($)", f"${total_saved:,.2f}")

        st.subheader("Processed Payloads Log")
        st.dataframe(df, use_container_width=True)

    conn.close()
except Exception as e:
    st.error(f"Database Read Error: {e}")