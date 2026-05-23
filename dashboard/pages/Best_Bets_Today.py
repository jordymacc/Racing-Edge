import os
import sys
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "models"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from theme import inject_css

st.set_page_config(page_title="Best Bets Today", page_icon="🏆", layout="wide")
inject_css()

st_autorefresh(interval=60000, key="bestbets_refresh")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_value_colour(edge_pct):
    if edge_pct >= 20:   return "#00FF88"
    elif edge_pct >= 10: return "#7FFF00"
    return "#888888"

def get_value_label(edge_pct):
    if edge_pct >= 20:   return "🔥 BACK IT"
    elif edge_pct >= 10: return "✅ GOOD VALUE"
    return ""

def get_kelly_bet(edge_pct, ml_prob, odds, bankroll=500):
    """Half Kelly bet size"""
    if ml_prob <= 0 or odds <= 1:
        return 0
    b = odds - 1
    kelly = (ml_prob * b - (1 - ml_prob)) / b
    half_kelly = kelly * 0.5
    if half_kelly <= 0:
        return 0
    half_kelly = min(half_kelly, 0.10)
    return round(bankroll * half_kelly, 2)

# ── Header ──
st.markdown("# 🏆 Best Bets Today")
st.markdown(f"<p style='color:#888;margin-top:-1rem;'>Only showing BACK IT (edge >20%) and GOOD VALUE (edge >10%) • Refreshes every 60s • {datetime.now().strftime('%d %b %Y %H:%M')}</p>", unsafe_allow_html=True)

# ── Load data ──
with st.spinner("Finding best bets..."):
    try:
        from dashboard_predictions import fetch_all_data, build_features
        import joblib

        model_data = joblib.load(BASE_DIR / "models" / "winner_predictor_v4.pkl")
        model = model_data["model"]
        FEATURES = [
            "win_odds_racingcom", "implied_prob", "is_favorite", "market_rank",
            "jockey_win_rate", "trainer_win_rate", "combined_form",
            "jockey_odds_interaction", "trainer_odds_interaction",
            "track_condition_score", "is_good", "is_soft", "is_heavy", "is_synth",
            "temperature", "rainfall", "wet_track", "temp_normalized"
        ]

        odds_df, jockey_df, trainer_df = fetch_all_data()
        features_df = build_features(odds_df, jockey_df, trainer_df)

        if features_df is None or features_df.empty:
            st.info("⏳ No race data yet today. Check back once racing begins.")
            st.stop()

        X = features_df[FEATURES].fillna(0)
        features_df["ml_prob"] = model.predict_proba(X)[:, 1]
        features_df["implied_prob_mkt"] = 1 / features_df["win_odds_racingcom"].replace(0, 999)
        features_df["edge"] = (features_df["ml_prob"] - features_df["implied_prob_mkt"]) * 100
        features_df["fair_odds"] = (1 / features_df["ml_prob"].replace(0, 999)).round(2)

        # Only keep BACK IT and GOOD VALUE
        value_df = features_df[features_df["edge"] >= 10].copy()
        value_df = value_df.sort_values("edge", ascending=False)

    except Exception as e:
        st.error(f"Error loading predictions: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

if value_df.empty:
    st.info("⏳ No value bets found yet today. The model will flag bets as odds update throughout the day.")
    st.stop()

# ── Summary metrics ──
total_bets = len(value_df)
avg_edge = value_df["edge"].mean()
back_it = len(value_df[value_df["edge"] >= 20])
good_value = len(value_df[value_df["edge"] < 20])

col1, col2, col3, col4 = st.columns(4)
col1.metric("🎯 Total Value Bets", total_bets)
col2.metric("🔥 BACK IT", back_it)
col3.metric("✅ GOOD VALUE", good_value)
col4.metric("📊 Avg Edge", f"{avg_edge:.1f}%")

st.divider()

# ── Group by venue ──
value_df["venue"] = value_df["race_name"].apply(
    lambda x: " ".join(x.split(" ")[:-1]) if " R" in x else x
)

venues = value_df["venue"].unique()

for venue in sorted(venues):
    venue_df = value_df[value_df["venue"] == venue].copy()
    
    # Venue header
    st.markdown(f"## 📍 {venue}")
    st.markdown(f"<p style='color:#888;margin-top:-0.5rem;'>{len(venue_df)} value bet(s) found</p>", 
                unsafe_allow_html=True)

    for _, bet in venue_df.iterrows():
        colour = get_value_colour(bet["edge"])
        label = get_value_label(bet["edge"])
        kelly = get_kelly_bet(bet["edge"], bet["ml_prob"], bet["win_odds_racingcom"])
        race_num = bet["race_name"].split(" R")[-1] if " R" in bet["race_name"] else "?"

        card = f"""
        <div style="
            background:linear-gradient(135deg, #12121A 0%, #1a1a2e 100%);
            border:1px solid {colour}44;
            border-left:6px solid {colour};
            border-radius:10px;
            padding:16px 24px;
            margin-bottom:12px;
        ">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
                <div>
                    <div style="color:#888;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;">
                        Race {race_num}
                    </div>
                    <div style="color:{colour};font-size:1.3rem;font-weight:800;margin:2px 0;">
                        {bet["horse_name"]}
                    </div>
                    <div style="color:#666;font-size:0.8rem;">
                        {bet.get("jockey_name", "-")} | {bet.get("trainer_name", "-")}
                    </div>
                </div>
                <div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap;">
                    <div style="text-align:center;">
                        <div style="color:#555;font-size:0.65rem;text-transform:uppercase;">Market Odds</div>
                        <div style="color:#fff;font-size:1.2rem;font-weight:700;">${bet["win_odds_racingcom"]:.2f}</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="color:#555;font-size:0.65rem;text-transform:uppercase;">Fair Odds</div>
                        <div style="color:#fff;font-size:1.2rem;font-weight:700;">${bet["fair_odds"]}</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="color:#555;font-size:0.65rem;text-transform:uppercase;">ML Prob</div>
                        <div style="color:#fff;font-size:1.2rem;font-weight:700;">{bet["ml_prob"]*100:.1f}%</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="color:#555;font-size:0.65rem;text-transform:uppercase;">Edge</div>
                        <div style="color:{colour};font-size:1.2rem;font-weight:700;">{bet["edge"]:+.1f}%</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="color:#555;font-size:0.65rem;text-transform:uppercase;">Kelly Bet</div>
                        <div style="color:{colour};font-size:1.2rem;font-weight:700;">${kelly:.2f}</div>
                    </div>
                    <div style="
                        background:{colour}22;
                        border:2px solid {colour};
                        border-radius:8px;
                        padding:8px 20px;
                        text-align:center;
                        min-width:130px;
                    ">
                        <div style="color:{colour};font-size:1rem;font-weight:800;">{label}</div>
                    </div>
                </div>
            </div>
        </div>
        """
        st.markdown(card, unsafe_allow_html=True)

    st.divider()

# ── Footer ──
st.markdown(f"<p style='color:#444;font-size:0.75rem;text-align:center;'>Powered by JordyMac Racing Engine v4 • Kelly stake based on $500 bankroll • For paper trading only</p>", 
            unsafe_allow_html=True)
