import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from theme import page_header, inject_css

import streamlit as st
import sqlite3
import pandas as pd
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'models'))

from kelly_staking import (
    calculate_kelly, get_current_bankroll,
    get_kelly_summary, setup_kelly_table,
    STARTING_BANKROLL
)

DB_PATH = BASE_DIR / "database" / "racing.db"

st.set_page_config(page_title="Kelly Staking", page_icon="💰", layout="wide")
inject_css()
st.title("💰 Kelly Criterion Staking")

setup_kelly_table()

# --- Bankroll Summary ---
bankroll = get_current_bankroll()
growth = ((bankroll - STARTING_BANKROLL) / STARTING_BANKROLL * 100)

col1, col2, col3 = st.columns(3)
col1.metric("Current Bankroll", f"${bankroll:.2f}",
            f"{growth:+.1f}% from start")
col2.metric("Starting Bankroll", f"${STARTING_BANKROLL:.2f}")
col3.metric("Strategy", "Half Kelly", "Max 10% per bet")

st.divider()

# --- Live Kelly Recommendations ---
st.subheader("🎯 Live Kelly Recommendations")
st.caption("Only showing bets where our model has >5% edge over the market")

try:
    conn = sqlite3.connect(DB_PATH)
    predictions = pd.read_sql_query("""
        SELECT race_name, horse_name, predicted_win_prob,
               current_odds, confidence
        FROM ml_predictions_log
        WHERE settled = 0
        AND predicted_win_prob IS NOT NULL
        AND current_odds IS NOT NULL
        ORDER BY predicted_win_prob DESC
        LIMIT 50
    """, conn)
    conn.close()

    if predictions.empty:
        st.info("No live predictions yet. The system will populate this as races are scanned.")
    else:
        kelly_rows = []
        for _, row in predictions.iterrows():
            edge, kelly_pct, bet_amount = calculate_kelly(
                row['predicted_win_prob'],
                row['current_odds'],
                bankroll
            )
            if bet_amount > 0:
                kelly_rows.append({
                    "Race": row['race_name'],
                    "Horse": row['horse_name'],
                    "Win Prob": f"{row['predicted_win_prob']*100:.1f}%",
                    "Odds": f"${row['current_odds']:.2f}",
                    "Edge": f"{edge*100:.1f}%",
                    "Kelly %": f"{kelly_pct*100:.1f}%",
                    "Bet Amount": f"${bet_amount:.2f}",
                })

        if kelly_rows:
            df = pd.DataFrame(kelly_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No value bets found right now. Waiting for races with sufficient edge.")

except Exception as e:
    st.error(f"Error loading predictions: {e}")

st.divider()

# --- Settled Bets History ---
st.subheader("📊 Settled Bets History")

try:
    conn = sqlite3.connect(DB_PATH)
    settled = pd.read_sql_query("""
        SELECT timestamp, race_name, horse_name,
               win_odds, edge, recommended_bet,
               result, profit_loss, bankroll_after
        FROM kelly_bets
        WHERE settled = 1
        ORDER BY timestamp DESC
        LIMIT 50
    """, conn)
    conn.close()

    if settled.empty:
        st.info("No settled bets yet. Results will appear here as races finish.")
    else:
        total_pl = settled['profit_loss'].sum()
        wins = len(settled[settled['result'] == 'WON'])
        total = len(settled)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total P&L", f"${total_pl:+.2f}")
        c2.metric("Win Rate", f"{wins/total*100:.1f}%", f"{wins}/{total} bets")
        c3.metric("ROI", f"{total_pl/settled['recommended_bet'].sum()*100:.1f}%")

        settled['timestamp'] = pd.to_datetime(settled['timestamp']).dt.strftime('%d %b %H:%M')
        settled['profit_loss'] = settled['profit_loss'].apply(lambda x: f"${x:+.2f}")
        settled['bankroll_after'] = settled['bankroll_after'].apply(lambda x: f"${x:.2f}")
        settled['edge'] = settled['edge'].apply(lambda x: f"{x*100:.1f}%")
        settled['recommended_bet'] = settled['recommended_bet'].apply(lambda x: f"${x:.2f}")
        settled.columns = ['Time', 'Race', 'Horse', 'Odds', 'Edge',
                           'Bet', 'Result', 'P&L', 'Bankroll']
        st.dataframe(settled, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error loading settled bets: {e}")

# --- Bankroll History Chart ---
st.subheader("📈 Bankroll Growth")

try:
    conn = sqlite3.connect(DB_PATH)
    history = pd.read_sql_query("""
        SELECT timestamp, bankroll FROM bankroll_history
        ORDER BY id ASC
    """, conn)
    conn.close()

    if len(history) > 1:
        history['timestamp'] = pd.to_datetime(history['timestamp'])
        history = history.set_index('timestamp')
        st.line_chart(history['bankroll'])
    else:
        st.info("Bankroll chart will appear here as bets are settled.")

except Exception as e:
    st.error(f"Error loading bankroll history: {e}")
