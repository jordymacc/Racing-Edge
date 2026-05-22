import streamlit as st
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "racing.db"

st.set_page_config(page_title="System Status", page_icon="⚙️", layout="wide")

st.title("⚙️ System Status")

conn = sqlite3.connect(DB_PATH)

# Database stats
st.subheader("📊 Database Statistics")

col1, col2, col3 = st.columns(3)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM odds_snapshots")
odds_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM odds_snapshots WHERE date(timestamp) = date('now')")
odds_today = cursor.fetchone()[0]

with col1:
    st.metric("Total Odds Snapshots", f"{odds_count:,}")
    st.caption(f"{odds_today:,} captured today")

cursor.execute("SELECT COUNT(*) FROM historical_results")
results_count = cursor.fetchone()[0]

with col2:
    st.metric("Race Results", f"{results_count:,}")

cursor.execute("SELECT COUNT(*) FROM ml_predictions_log")
predictions_count = cursor.fetchone()[0]

with col3:
    st.metric("ML Predictions", f"{predictions_count:,}")

st.divider()

# Recent activity
st.subheader("🕐 Recent Activity")

cursor.execute("SELECT MAX(timestamp) FROM odds_snapshots")
last_odds = cursor.fetchone()[0]

if last_odds:
    last_odds_dt = datetime.fromisoformat(last_odds)
    minutes_ago = (datetime.now() - last_odds_dt).total_seconds() / 60
    
    if minutes_ago < 2:
        st.success(f"✅ Last odds update: {minutes_ago:.0f} min ago")
    elif minutes_ago < 10:
        st.warning(f"⚠️ Last odds update: {minutes_ago:.0f} min ago")
    else:
        st.error(f"❌ Last odds update: {minutes_ago:.0f} min ago")

conn.close()

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=30000, key="status_refresh")
