import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from theme import inject_css
import streamlit as st
from pathlib import Path
from datetime import datetime
import pandas as pd
from streamlit_autorefresh import st_autorefresh

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_URL = os.environ.get("DATABASE_URL")

st.set_page_config(page_title="System Status", page_icon="⚙️", layout="wide")
inject_css()
st_autorefresh(interval=30000, key="status_refresh")
st.title("⚙️ System Status")

def get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL), "pg"
    import sqlite3
    return sqlite3.connect(str(BASE_DIR / "database" / "racing.db")), "sqlite"

def q(cursor, sql_pg, sql_lite, db):
    cursor.execute(sql_pg if db == "pg" else sql_lite)
    return cursor.fetchone()[0]

conn, db = get_conn()
cursor = conn.cursor()

# ── Database stats ──
st.subheader("📊 Database Statistics")
col1, col2, col3 = st.columns(3)

odds_count = q(cursor,
    "SELECT COUNT(*) FROM odds_snapshots",
    "SELECT COUNT(*) FROM odds_snapshots", db)

odds_today = q(cursor,
    "SELECT COUNT(*) FROM odds_snapshots WHERE timestamp::timestamp > NOW() - INTERVAL '24 hours'",
    "SELECT COUNT(*) FROM odds_snapshots WHERE date(timestamp) = date('now')", db)

with col1:
    st.metric("Total Odds Snapshots", f"{odds_count:,}")
    st.caption(f"{odds_today:,} captured today")

results_count = q(cursor,
    "SELECT COUNT(*) FROM historical_results",
    "SELECT COUNT(*) FROM historical_results", db)
with col2:
    st.metric("Race Results", f"{results_count:,}")

predictions_count = q(cursor,
    "SELECT COUNT(*) FROM ml_predictions_log",
    "SELECT COUNT(*) FROM ml_predictions_log", db)
with col3:
    st.metric("ML Predictions", f"{predictions_count:,}")

st.divider()

# ── Recent activity ──
st.subheader("🕐 Recent Activity")

cursor.execute("SELECT MAX(timestamp) FROM odds_snapshots")
last_odds = cursor.fetchone()[0]

if last_odds:
    last_odds_str = str(last_odds).split(".")[0].replace("T", " ")
    try:
        last_odds_dt = datetime.fromisoformat(str(last_odds).split("+")[0].split(".")[0])
        minutes_ago = (datetime.utcnow() - last_odds_dt).total_seconds() / 60
        if minutes_ago < 2:
            st.success(f"✅ Last odds update: {minutes_ago:.0f} min ago ({last_odds_str})")
        elif minutes_ago < 10:
            st.warning(f"⚠️ Last odds update: {minutes_ago:.0f} min ago ({last_odds_str})")
        else:
            st.error(f"❌ Last odds update: {minutes_ago:.0f} min ago ({last_odds_str})")
    except:
        st.info(f"Last odds: {last_odds_str}")
else:
    st.warning("No odds data yet")

st.divider()

# ── DB info ──
st.subheader("🗄️ Database")
st.success(f"✅ Connected to {'PostgreSQL ☁️' if db == 'pg' else 'SQLite 💾'}")

conn.close()
