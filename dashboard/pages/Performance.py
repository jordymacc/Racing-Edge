import os
import sys
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "models"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from theme import inject_css

st.set_page_config(page_title="Performance", page_icon="📈", layout="wide")
inject_css()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    import sqlite3
    return sqlite3.connect(str(BASE_DIR / "database" / "racing.db"))

st.markdown("# 📈 Performance")
st.markdown("<p style='color:#666;margin-top:-1rem;font-size:0.85rem;'>Real P&L tracking on ML predictions</p>",
            unsafe_allow_html=True)

try:
    conn = get_conn()

    # ── Summary stats ──
    if DATABASE_URL:
        summary = pd.read_sql_query("""
            SELECT
                COUNT(*) as total_bets,
                SUM(CASE WHEN actual_result = 'WON' THEN 1 ELSE 0 END) as wins,
                SUM(profit_loss) as total_pl,
                SUM(kelly_bet) as total_staked,
                AVG(edge) as avg_edge
            FROM ml_predictions_log
            WHERE settled = 1
        """, conn)
    else:
        summary = pd.read_sql_query("""
            SELECT
                COUNT(*) as total_bets,
                SUM(CASE WHEN actual_result = 'WON' THEN 1 ELSE 0 END) as wins,
                SUM(profit_loss) as total_pl,
                SUM(kelly_bet) as total_staked,
                AVG(edge) as avg_edge
            FROM ml_predictions_log
            WHERE settled = 1
        """, conn)

    row = summary.iloc[0]
    total = int(row["total_bets"] or 0)
    wins = int(row["wins"] or 0)
    pl = float(row["total_pl"] or 0)
    staked = float(row["total_staked"] or 0)
    avg_edge = float(row["avg_edge"] or 0)
    win_rate = round(wins / total * 100, 1) if total > 0 else 0
    roi = round(pl / staked * 100, 1) if staked > 0 else 0
    bankroll = 500 + pl

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🎯 Total Bets", total)
    col2.metric("✅ Win Rate", f"{win_rate}%", f"{wins}/{total}")
    col3.metric("💰 P&L", f"${pl:+.2f}")
    col4.metric("📊 ROI", f"{roi:+.1f}%")
    col5.metric("🏦 Bankroll", f"${bankroll:.2f}", f"${pl:+.2f}")

    st.divider()

    # ── Unsettled predictions ──
    unsettled_count = pd.read_sql_query(
        "SELECT COUNT(*) as n FROM ml_predictions_log WHERE settled = 0", conn
    ).iloc[0]["n"]

    if unsettled_count > 0:
        st.info(f"⏳ {int(unsettled_count)} predictions waiting to be settled (races not finished yet)")

    # ── Recent settled bets ──
    st.subheader("📋 Settled Bets")

    if total == 0:
        st.info("⏳ No settled bets yet. Predictions are logged throughout the day and settled once races finish.")
    else:
        settled = pd.read_sql_query("""
            SELECT timestamp, race_name, horse_name, current_odds,
                   predicted_win_prob, edge, kelly_bet,
                   actual_result, profit_loss
            FROM ml_predictions_log
            WHERE settled = 1
            ORDER BY timestamp DESC
            LIMIT 100
        """, conn)

        # Format
        settled["timestamp"] = pd.to_datetime(settled["timestamp"]).dt.strftime("%d %b %H:%M")
        settled["predicted_win_prob"] = (settled["predicted_win_prob"] * 100).round(1).astype(str) + "%"
        settled["edge"] = settled["edge"].apply(lambda x: f"{x:+.1f}%")
        settled["current_odds"] = settled["current_odds"].apply(lambda x: f"${x:.2f}")
        settled["kelly_bet"] = settled["kelly_bet"].apply(lambda x: f"${x:.2f}")
        settled["profit_loss"] = settled["profit_loss"].apply(lambda x: f"${x:+.2f}")
        settled.columns = ["Time", "Race", "Horse", "Odds", "ML Prob", "Edge", "Bet", "Result", "P&L"]

        st.dataframe(settled, use_container_width=True, hide_index=True)

        # ── P&L chart ──
        st.subheader("📈 Bankroll Growth")
        pl_data = pd.read_sql_query("""
            SELECT timestamp, SUM(profit_loss) OVER (ORDER BY timestamp) as cumulative_pl
            FROM ml_predictions_log
            WHERE settled = 1
            ORDER BY timestamp
        """, conn)

        if len(pl_data) > 1:
            pl_data["bankroll"] = 500 + pl_data["cumulative_pl"]
            pl_data["timestamp"] = pd.to_datetime(pl_data["timestamp"])
            pl_data = pl_data.set_index("timestamp")
            st.line_chart(pl_data["bankroll"])

    conn.close()

except Exception as e:
    st.error(f"Error loading performance data: {e}")
    import traceback
    st.code(traceback.format_exc())
