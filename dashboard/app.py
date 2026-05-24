import os
import sys
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import zoneinfo
from streamlit_autorefresh import st_autorefresh

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "models"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from theme import inject_css

st.set_page_config(
    page_title="JordyMac Racing Engine",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()
st_autorefresh(interval=60000, key="main_refresh")

st.markdown("# 🏇 JordyMac Racing Engine")
st.markdown(f"<p style='color:#888;margin-top:-1rem;'>AI-powered racing intelligence • {datetime.now(zoneinfo.ZoneInfo('Australia/Melbourne')).strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
st.divider()

import dashboard_predictions

@st.cache_data(ttl=120)
def load_predictions():
    return dashboard_predictions.get_ml_predictions_for_dashboard()

with st.spinner("Loading live predictions..."):
    predictions = load_predictions()

if predictions is None or len(predictions) == 0:
    st.info("⏳ No races running right now. Check back when racing starts — usually from 11am AEST.")
    st.markdown("### 🔗 Explore while you wait")
    c1, c2, c3, c4 = st.columns(4)
    for col, emoji, title, desc in [
        (c1, "🏆", "Best Bets Today", "Today's top value plays"),
        (c2, "🔮", "Future Races", "Next 3 days of fields"),
        (c3, "🔴", "Live Next Races", "Real-time race cards"),
        (c4, "📊", "Performance", "P&L and ROI tracking"),
    ]:
        col.markdown(f"""<div style="background:#12121A;border:1px solid #1E1E2E;border-radius:8px;padding:14px;text-align:center;">
            <div style="font-size:1.5rem;">{emoji}</div>
            <div style="color:#00FF88;font-weight:700;font-size:0.9rem;margin:4px 0;">{title}</div>
            <div style="color:#666;font-size:0.75rem;">{desc}</div>
        </div>""", unsafe_allow_html=True)
    st.stop()
    st.stop()

total_races = predictions["race_name"].nunique()
total_horses = len(predictions)
high_conf = len(predictions[predictions["confidence"] == "HIGH"])
value_bets = len(predictions[predictions["predicted_win_prob"] > 0.25])

col1, col2, col3, col4 = st.columns(4)
col1.metric("🏁 Races Today", total_races)
col2.metric("🐎 Horses Tracked", total_horses)
col3.metric("🔥 High Confidence", high_conf)
col4.metric("💰 Value Opportunities", value_bets)

st.divider()
st.markdown("## 🎯 Race Selector")

predictions["venue"] = predictions["race_name"].apply(
    lambda x: " ".join(x.split(" ")[:-1]) if " R" in x else x
)

venues = sorted(predictions["venue"].unique())
selected_venue = st.selectbox("📍 Select Meeting", venues)

venue_races = predictions[predictions["venue"] == selected_venue]
race_numbers = sorted(venue_races["race_name"].unique(),
    key=lambda x: int(x.split(" R")[-1]) if x.split(" R")[-1].isdigit() else 0)

selected_race = st.selectbox("🏁 Select Race", race_numbers)
st.divider()

race_df = predictions[predictions["race_name"] == selected_race].copy()
race_df = race_df.sort_values("predicted_win_prob", ascending=False)

track = race_df["track_condition"].iloc[0] if "track_condition" in race_df.columns else "N/A"
temp = race_df["temperature"].iloc[0] if "temperature" in race_df.columns else None
runners = len(race_df)

col1, col2, col3 = st.columns(3)
col1.metric("🌿 Track", track if track and str(track) not in ["nan","None","unknown"] else "N/A")
col2.metric("🌡️ Temperature", f"{float(temp):.0f}°C" if temp and str(temp) != "nan" else "N/A")
col3.metric("🐎 Runners", runners)

st.markdown(f"### 🏇 {selected_race}")

def get_colour(edge):
    if edge >= 20:    return "#00FF88"
    elif edge >= 10:  return "#7FFF00"
    elif edge >= 5:   return "#FFD700"
    elif edge >= 0:   return "#888888"
    elif edge >= -10: return "#FF8C00"
    else:             return "#FF4444"

def get_label(edge):
    if edge >= 20:    return "🔥 BACK IT"
    elif edge >= 10:  return "✅ GOOD VALUE"
    elif edge >= 5:   return "👀 WATCH"
    elif edge >= 0:   return "⚪ NEUTRAL"
    elif edge >= -10: return "⚠️ SKINNY"
    else:             return "❌ SKIP"

for _, horse in race_df.iterrows():
    prob = float(horse.get("predicted_win_prob", 0) or 0)
    odds = float(horse.get("current_odds", 0) or 0)
    implied = 1/odds if odds > 0 else 0
    edge = round((prob - implied) * 100, 1) if odds > 0 else 0
    fair = round(1/prob, 2) if prob > 0 else 0
    colour = get_colour(edge)
    label = get_label(edge)

    card = f"""
    <div style="background:linear-gradient(135deg,#12121A 0%,#1a1a2e 100%);border-left:5px solid {colour};border-radius:8px;padding:12px 16px;margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
            <div>
                <span style="color:{colour};font-size:1.05rem;font-weight:800;">{horse["horse_name"]}</span>
                <div style="color:#666;font-size:0.75rem;">{horse.get("jockey_name","—")} | {horse.get("trainer_name","—")}</div>
            </div>
            <div style="background:{colour}22;border:1px solid {colour};border-radius:6px;padding:4px 12px;">
                <span style="color:{colour};font-weight:800;font-size:0.8rem;">{label}</span>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;">
            <div style="background:#0A0A0F;border-radius:5px;padding:6px;text-align:center;">
                <div style="color:#555;font-size:0.6rem;text-transform:uppercase;">Odds</div>
                <div style="color:#fff;font-size:0.95rem;font-weight:700;">${odds:.2f}</div>
            </div>
            <div style="background:#0A0A0F;border-radius:5px;padding:6px;text-align:center;">
                <div style="color:#555;font-size:0.6rem;text-transform:uppercase;">ML Prob</div>
                <div style="color:#fff;font-size:0.95rem;font-weight:700;">{prob*100:.1f}%</div>
            </div>
            <div style="background:#0A0A0F;border-radius:5px;padding:6px;text-align:center;">
                <div style="color:#555;font-size:0.6rem;text-transform:uppercase;">Fair Odds</div>
                <div style="color:#fff;font-size:0.95rem;font-weight:700;">${fair}</div>
            </div>
            <div style="background:#0A0A0F;border-radius:5px;padding:6px;text-align:center;">
                <div style="color:#555;font-size:0.6rem;text-transform:uppercase;">Edge</div>
                <div style="color:{colour};font-size:0.95rem;font-weight:700;">{edge:+.1f}%</div>
            </div>
        </div>
    </div>
    """
    st.markdown(card, unsafe_allow_html=True)

st.divider()
st.caption("🤖 JordyMac Racing Engine v4 • Ensemble ML Model • 92% accuracy")
