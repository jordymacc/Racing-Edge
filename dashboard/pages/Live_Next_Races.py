import os
import sys
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "models"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from theme import inject_css

st.set_page_config(page_title="Live Next Races", page_icon="🔴", layout="wide")
inject_css()

# Auto refresh every 30 seconds
st_autorefresh(interval=30000, key="live_refresh")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_value_colour(edge_pct):
    if edge_pct >= 20:   return "#00FF88"
    elif edge_pct >= 10: return "#7FFF00"
    elif edge_pct >= 5:  return "#FFD700"
    elif edge_pct >= 0:  return "#888888"
    elif edge_pct >= -10: return "#FF8C00"
    else:                return "#FF4444"

def get_value_label(edge_pct):
    if edge_pct >= 20:    return "🔥 BACK IT"
    elif edge_pct >= 10:  return "✅ GOOD VALUE"
    elif edge_pct >= 5:   return "👀 WATCH"
    elif edge_pct >= 0:   return "⚪ NEUTRAL"
    elif edge_pct >= -10: return "⚠️ SKINNY"
    else:                 return "❌ SKIP"

def fetch_live_data():
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT race_name, horse_name, jockey_name, trainer_name,
                   win_odds_racingcom, timestamp,
                   track_condition, temperature
            FROM odds_snapshots
            WHERE timestamp::timestamp > NOW() - INTERVAL '2 hours'
            AND win_odds_racingcom IS NOT NULL
            ORDER BY race_name, horse_name, timestamp DESC
        """)
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
        cur.execute("SELECT jockey_name, win_rate FROM jockey_stats")
        jockey_df = pd.DataFrame(cur.fetchall(), columns=["jockey_name","win_rate"])
        conn.close()
    else:
        conn = sqlite3.connect(str(BASE_DIR / "database" / "racing.db"))
        df = pd.read_sql_query("""
            SELECT race_name, horse_name, jockey_name, trainer_name,
                   win_odds_racingcom, timestamp,
                   track_condition, temperature
            FROM odds_snapshots
            WHERE timestamp > datetime('now', '-2 hours')
            AND win_odds_racingcom IS NOT NULL
            ORDER BY race_name, horse_name, timestamp DESC
        """, conn)
        jockey_df = pd.read_sql_query("SELECT jockey_name, win_rate FROM jockey_stats", conn)
        conn.close()
    return df, jockey_df

def get_race_predictions(df, jockey_df):
    try:
        import joblib
        from dashboard_predictions import fetch_all_data, build_features
        model_data = joblib.load(BASE_DIR / "models" / "winner_predictor_v4.pkl")
        model = model_data["model"]
        FEATURES = [
            "win_odds_racingcom", "implied_prob", "is_favorite", "market_rank",
            "jockey_win_rate", "trainer_win_rate", "combined_form",
            "jockey_odds_interaction", "trainer_odds_interaction",
            "track_condition_score", "is_good", "is_soft", "is_heavy", "is_synth",
            "temperature", "rainfall", "wet_track", "temp_normalized"
        ]
        odds_df, jockey_df2, trainer_df = fetch_all_data()
        features_df = build_features(odds_df, jockey_df2, trainer_df)
        if features_df is None:
            return {}
        X = features_df[FEATURES].fillna(0)
        features_df["ml_prob"] = model.predict_proba(X)[:, 1]
        result = {}
        for _, row in features_df.iterrows():
            result[(row["race_name"], row["horse_name"])] = row["ml_prob"]
        return result
    except Exception as e:
        return {}

# ── Header ──
st.markdown("# 🔴 Live Next Races")
st.markdown(f"<p style='color:#888;margin-top:-1rem;'>Auto-refreshes every 30 seconds • Last update: {datetime.now().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)

# ── Load data ──
with st.spinner("Loading live races..."):
    try:
        df, jockey_df = fetch_live_data()
        ml_map = get_race_predictions(df, jockey_df)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

if df.empty:
    st.info("⏳ No races found. The scraper will populate this once racing begins.")
    st.stop()

# ── Get latest odds per horse per race ──
latest = df.sort_values("timestamp").groupby(["race_name","horse_name"]).last().reset_index()

# ── Get races sorted by favourite odds (proxy for race proximity) ──
# Sort by most recently updated odds = most likely about to jump
race_latest_ts = df.groupby("race_name")["timestamp"].max().reset_index()
race_latest_ts.columns = ["race_name","latest_ts"]
race_latest_ts = race_latest_ts.sort_values("latest_ts", ascending=False).head(5)
next_races = race_latest_ts["race_name"].tolist()

st.markdown(f"### Showing next {len(next_races)} races across all venues")
st.divider()

# ── Display each race ──
for race_name in next_races:
    race_df = latest[latest["race_name"] == race_name].copy()
    track = race_df["track_condition"].iloc[0] if "track_condition" in race_df.columns else "Unknown"
    temp = race_df["temperature"].iloc[0] if "temperature" in race_df.columns else None
    num_runners = len(race_df)
    fav_odds = float(race_df["win_odds_racingcom"].min())

    # Race header
    col1, col2, col3, col4 = st.columns([3,1,1,1])
    with col1:
        st.markdown(f"## 🏇 {race_name}")
    with col2:
        st.metric("🌿 Track", track if track and track != "nan" and track != "unknown" else "N/A")
    with col3:
        st.metric("🌡️ Temp", f"{float(temp):.0f}°C" if temp and str(temp) != "nan" else "N/A")
    with col4:
        st.metric("🐎 Runners", num_runners)

    # Sort horses by ML prob then odds
    horses = []
    for _, horse in race_df.iterrows():
        name = horse["horse_name"]
        odds = float(horse["win_odds_racingcom"])
        ml_prob = ml_map.get((race_name, name), 0)
        implied_prob = 1 / odds if odds > 0 else 0
        edge = round((ml_prob - implied_prob) * 100, 1)
        horses.append({
            "name": name,
            "jockey": horse.get("jockey_name", "-"),
            "odds": odds,
            "ml_prob": ml_prob,
            "fair_odds": round(1/ml_prob, 2) if ml_prob > 0 else 0,
            "edge": edge,
            "colour": get_value_colour(edge),
            "label": get_value_label(edge),
        })
    
    horses.sort(key=lambda x: x["ml_prob"], reverse=True)

    # Display horses
    for h in horses:
        colour = h["colour"]
        prob_display = f"{h['ml_prob']*100:.1f}%" if h["ml_prob"] > 0 else "—"
        fair_display = f"${h['fair_odds']}" if h["fair_odds"] > 0 else "—"
        
        card = f"""
        <div style="
            background:linear-gradient(135deg,#12121A 0%,#1a1a2e 100%);
            border-left:5px solid {colour};
            border-radius:8px;
            padding:12px 20px;
            margin-bottom:8px;
            display:flex;
            align-items:center;
            justify-content:space-between;
        ">
            <div style="min-width:250px;">
                <span style="color:{colour};font-size:1rem;font-weight:800;">{h["name"]}</span>
                <span style="color:#666;font-size:0.75rem;margin-left:10px;">{h["jockey"]}</span>
            </div>
            <div style="display:flex;gap:30px;align-items:center;">
                <div style="text-align:center;min-width:60px;">
                    <div style="color:#555;font-size:0.65rem;text-transform:uppercase;">Odds</div>
                    <div style="color:#fff;font-weight:700;">${h["odds"]:.2f}</div>
                </div>
                <div style="text-align:center;min-width:60px;">
                    <div style="color:#555;font-size:0.65rem;text-transform:uppercase;">ML Prob</div>
                    <div style="color:#fff;font-weight:700;">{prob_display}</div>
                </div>
                <div style="text-align:center;min-width:60px;">
                    <div style="color:#555;font-size:0.65rem;text-transform:uppercase;">Fair Odds</div>
                    <div style="color:#fff;font-weight:700;">{fair_display}</div>
                </div>
                <div style="text-align:center;min-width:70px;">
                    <div style="color:#555;font-size:0.65rem;text-transform:uppercase;">Edge</div>
                    <div style="color:{colour};font-weight:700;">{h["edge"]:+.1f}%</div>
                </div>
                <div style="
                    background:{colour}22;
                    border:1px solid {colour};
                    border-radius:6px;
                    padding:5px 12px;
                    min-width:120px;
                    text-align:center;
                ">
                    <span style="color:{colour};font-weight:800;font-size:0.85rem;">{h["label"]}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(card, unsafe_allow_html=True)

    st.divider()
