import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import sys

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "racing.db"

st.set_page_config(page_title="Performance Tracker", page_icon="📊", layout="wide")

st.title("📊 Model Performance Tracker")

# Get performance stats
conn = sqlite3.connect(DB_PATH)

# Overall stats
query_overall = """
    SELECT 
        COUNT(*) as total_bets,
        SUM(CASE WHEN actual_result = 1 THEN 1 ELSE 0 END) as wins,
        SUM(profit_loss) as total_pl
    FROM ml_predictions_log
    WHERE settled = 1
"""

df_overall = pd.read_sql_query(query_overall, conn)

if df_overall['total_bets'].iloc[0] > 0:
    total_bets = int(df_overall['total_bets'].iloc[0])
    wins = int(df_overall['wins'].iloc[0])
    losses = total_bets - wins
    total_pl = float(df_overall['total_pl'].iloc[0])
    win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
    roi = (total_pl / (total_bets * 10) * 100) if total_bets > 0 else 0
    
    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Bets", total_bets)
    with col2:
        st.metric("Wins", wins, delta=f"{win_rate:.1f}%")
    with col3:
        st.metric("Losses", losses)
    with col4:
        st.metric("Total P&L", f"${total_pl:,.2f}", delta=f"${total_pl/total_bets:.2f}/bet")
    with col5:
        st.metric("ROI", f"{roi:+.1f}%", delta="Profit" if roi > 0 else "Loss")
    
    st.divider()
    
    # Recent bets
    st.subheader("📋 Recent Settled Bets")
    
    query_recent = """
        SELECT 
            timestamp,
            race_name,
            horse_name,
            ROUND(predicted_win_prob * 100, 1) as confidence_pct,
            current_odds,
            CASE WHEN actual_result = 1 THEN '✅ WON' ELSE '❌ LOST' END as result,
            ROUND(profit_loss, 2) as pl
        FROM ml_predictions_log
        WHERE settled = 1
        ORDER BY timestamp DESC
        LIMIT 50
    """
    
    df_recent = pd.read_sql_query(query_recent, conn)
    df_recent['timestamp'] = pd.to_datetime(df_recent['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    st.dataframe(df_recent, hide_index=True, use_container_width=True)
    
else:
    st.info("⏳ No settled bets yet. Predictions are being tracked and will appear here once races finish!")
    
    # Show pending predictions
    st.subheader("⏳ Pending Predictions")
    
    query_pending = """
        SELECT 
            timestamp,
            race_name,
            horse_name,
            ROUND(predicted_win_prob * 100, 1) as confidence_pct,
            current_odds,
            confidence
        FROM ml_predictions_log
        WHERE settled = 0
        ORDER BY predicted_win_prob DESC
        LIMIT 20
    """
    
    df_pending = pd.read_sql_query(query_pending, conn)
    
    if not df_pending.empty:
        df_pending['timestamp'] = pd.to_datetime(df_pending['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(df_pending, hide_index=True, use_container_width=True)
    else:
        st.write("No pending predictions")

conn.close()

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=30000, key="performance_refresh")
