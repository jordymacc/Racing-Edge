# dashboard/pages/Paper_Trading.py
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path
import sys

# Setup paths to ensure we can import models
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'models'))

from staking import calculate_kelly_stake

st.set_page_config(page_title="Paper Trading Simulator", page_icon="📈", layout="wide")
st.title("📈 Kelly Criterion Paper Trading")
st.markdown("Simulate bankroll growth on your **settled AI predictions** using dynamic Kelly staking.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Staking Parameters")
starting_bankroll = st.sidebar.number_input("Starting Bankroll ($)", min_value=100, max_value=100000, value=1000, step=100)
kelly_multiplier = st.sidebar.slider("Kelly Multiplier", min_value=0.05, max_value=1.0, value=0.25, step=0.05, 
                                     help="0.25 = Quarter Kelly (Recommended). 1.0 = Full Kelly (High Risk)")
max_stake = st.sidebar.slider("Max Stake per Bet (%)", min_value=1.0, max_value=20.0, value=5.0, step=0.5) / 100.0
min_confidence = st.sidebar.slider("Minimum Model Confidence (%)", min_value=50, max_value=99, value=80, step=1) / 100.0

# --- LOAD DATA ---
db_path = BASE_DIR / 'database' / 'racing.db'
conn = sqlite3.connect(str(db_path))

# Fetch all settled bets
query = "SELECT * FROM ml_predictions_log WHERE settled = 1 ORDER BY timestamp ASC"
try:
    df = pd.read_sql(query, conn)
except Exception as e:
    st.error(f"Error loading database: {e}")
    df = pd.DataFrame()
conn.close()

if df.empty:
    st.warning("No settled bets found in the database. Wait for the scheduler to log and settle some results!")
else:
    # --- SIMULATION ENGINE ---
    # Filter by user's confidence threshold
    df = df[df['predicted_win_prob'] >= min_confidence].copy()
    
    bankroll = starting_bankroll
    bankroll_history = [bankroll]
    trade_logs = []
    
    for index, row in df.iterrows():
        # Get optimal stake
        stake_pct, stake_amt = calculate_kelly_stake(
            win_prob=row['predicted_win_prob'],
            odds=row['current_odds'],
            current_bankroll=bankroll,
            multiplier=kelly_multiplier,
            max_stake_pct=max_stake
        )
        
        # Only process if Kelly suggests a bet (edge > 0)
        if stake_amt > 0:
            actual_result = int(row['actual_result'])
            
            # Calculate P&L
            if actual_result == 1:
                # Win
                profit = stake_amt * (row['current_odds'] - 1)
                bankroll += profit
                status = "WIN"
            else:
                # Loss
                profit = -stake_amt
                bankroll -= stake_amt
                status = "LOSS"
                
            bankroll_history.append(bankroll)
            trade_logs.append({
                'Time': row['timestamp'],
                'Race': row['race_name'],
                'Horse': row['horse_name'],
                'Odds': row['current_odds'],
                'Model Prob': f"{row['predicted_win_prob']*100:.1f}%",
                'Stake': f"${stake_amt:.2f}",
                'Result': status,
                'P&L': profit,
                'New Bankroll': bankroll
            })

    # --- RENDER RESULTS ---
    if not trade_logs:
        st.info("No bets qualify under the current parameters. Try lowering the minimum confidence.")
    else:
        # Metrics
        total_trades = len(trade_logs)
        wins = sum(1 for t in trade_logs if t['Result'] == 'WIN')
        win_rate = (wins / total_trades) * 100
        net_profit = bankroll - starting_bankroll
        roi = (net_profit / starting_bankroll) * 100
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Final Bankroll", f"${bankroll:.2f}", f"${net_profit:.2f} Profit")
        col2.metric("Total ROI", f"{roi:.1f}%")
        col3.metric("Win Rate", f"{win_rate:.1f}%")
        col4.metric("Total Bets Placed", total_trades)
        
        # Equity Curve Chart
        chart_data = pd.DataFrame({
            'Bet Number': range(len(bankroll_history)),
            'Bankroll ($)': bankroll_history
        })
        fig = px.line(chart_data, x='Bet Number', y='Bankroll ($)', title='Bankroll Equity Curve', markers=True)
        fig.update_layout(yaxis_tickprefix='$', template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)
        
        # Trade Log Table
        st.subheader("Simulated Trade Log")
        trades_df = pd.DataFrame(trade_logs)
        # Apply color styling to P&L
        def color_pnl(val):
            color = '#00ff00' if val > 0 else '#ff0000'
            return f'color: {color}'
            
        st.dataframe(
            trades_df.style.map(color_pnl, subset=['P&L']),
            use_container_width=True
        )