import os
import sys
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "models"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from theme import inject_css

st.set_page_config(page_title="Race Viewer", page_icon="🏇", layout="wide")
inject_css()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(str(BASE_DIR / "database" / "racing.db"))

def get_value_colour(edge_pct):
    """Returns colour based on edge percentage"""
    if edge_pct >= 20:
        return "#00FF88"   # Neon green - massive value
    elif edge_pct >= 10:
        return "#7FFF00"   # Yellow-green - good value
    elif edge_pct >= 5:
        return "#FFD700"   # Gold - slight value
    elif edge_pct >= 0:
        return "#888888"   # Grey - neutral
    elif edge_pct >= -10:
        return "#FF8C00"   # Orange - slight overpriced
    else:
        return "#FF4444"   # Red - strongly overpriced

def get_value_label(edge_pct):
    if edge_pct >= 20:
        return "🔥 BACK IT"
    elif edge_pct >= 10:
        return "✅ GOOD VALUE"
    elif edge_pct >= 5:
        return "👀 WATCH"
    elif edge_pct >= 0:
        return "⚪ NEUTRAL"
    elif edge_pct >= -10:
        return "⚠️ SKINNY"
    else:
        return "❌ SKIP"

# ── Title ──
st.markdown("# 🏇 Race Viewer")
st.markdown("<p style='color:#888888;margin-top:-1rem;'>Colour-coded value ratings for today's races</p>", unsafe_allow_html=True)

# ── Load today's races ──
try:
    conn = get_conn()
    ph = "%s" if DATABASE_URL else "?"
    races_df = pd.read_sql_query(f"""
        SELECT DISTINCT race_name
        FROM odds_snapshots
        WHERE timestamp::timestamp > NOW() - INTERVAL '3 hours'
        ORDER BY race_name
    """ if DATABASE_URL else """
        SELECT DISTINCT race_name
        FROM odds_snapshots
        WHERE timestamp > datetime('now', '-3 hours')
        ORDER BY race_name
    """, conn)
    conn.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

if races_df.empty:
    st.info("⏳ No races found yet today. The scraper will populate this once racing begins.")
    st.stop()

race_list = races_df["race_name"].tolist()

# ── Race selector ──
st.sidebar.markdown("## 🏇 Select Race")
selected_race = st.sidebar.selectbox("Choose a race", race_list)

# ── Manual ratings input ──
st.sidebar.markdown("---")
st.sidebar.markdown("## ✏️ Manual Ratings")
st.sidebar.markdown("<small style='color:#888'>Enter your own ratings (optional). Leave 0 to use ML only.</small>", unsafe_allow_html=True)

# ── Load horses for selected race ──
try:
    conn = get_conn()
    horses_df = pd.read_sql_query(f"""
        SELECT DISTINCT ON (horse_name)
            horse_name,
            jockey_name,
            trainer_name,
            win_odds_racingcom,
            track_condition,
            temperature,
            rainfall
        FROM odds_snapshots
        WHERE race_name = '{selected_race}'
        AND win_odds_racingcom IS NOT NULL
        ORDER BY horse_name, timestamp DESC
    """ if DATABASE_URL else f"""
        SELECT
            horse_name,
            jockey_name,
            trainer_name,
            win_odds_racingcom,
            track_condition,
            temperature,
            rainfall
        FROM odds_snapshots
        WHERE race_name = ?
        AND win_odds_racingcom IS NOT NULL
        GROUP BY horse_name
        ORDER BY win_odds_racingcom ASC
    """, conn, params=(selected_race,) if not DATABASE_URL else None)
    conn.close()
except Exception as e:
    st.error(f"Error loading race: {e}")
    st.stop()

if horses_df.empty:
    st.warning("No horses found for this race.")
    st.stop()

# ── Load ML predictions ──
try:
    import joblib
    sys.path.insert(0, str(BASE_DIR / "models"))
    from dashboard_predictions import fetch_all_data, build_features
    model_path = BASE_DIR / "models" / "winner_predictor_v4.pkl"
    model_data = joblib.load(model_path)
    model = model_data["model"]
    FEATURES = [
        "win_odds_racingcom", "implied_prob", "is_favorite", "market_rank",
        "jockey_win_rate", "trainer_win_rate", "combined_form",
        "jockey_odds_interaction", "trainer_odds_interaction",
        "track_condition_score", "is_good", "is_soft", "is_heavy", "is_synth",
        "temperature", "rainfall", "wet_track", "temp_normalized"
    ]
    odds_df, jockey_df, trainer_df = fetch_all_data()
    st.caption(f"Debug: {len(odds_df)} total odds rows, races: {odds_df['race_name'].nunique()}")
    race_odds = odds_df[odds_df["race_name"] == selected_race]
    st.caption(f"Debug: {len(race_odds)} rows for {selected_race}")
    if not race_odds.empty:
        race_features = build_features(race_odds, jockey_df, trainer_df)
        st.caption(f"Debug: features={len(race_features) if race_features is not None else 'None'}")
        if race_features is not None:
            X = race_features[FEATURES].fillna(0)
            probs = model.predict_proba(X)[:, 1]
            race_features["ml_prob"] = probs
            ml_map = dict(zip(race_features["horse_name"], race_features["ml_prob"]))
        else:
            ml_map = {}
    else:
        ml_map = {}
except Exception as e:
    ml_map = {}
    st.warning(f"ML model not available: {e}")

# ── Get track/weather info ──
track_condition = horses_df["track_condition"].iloc[0] if "track_condition" in horses_df.columns else "Unknown"
temperature = horses_df["temperature"].iloc[0] if "temperature" in horses_df.columns else None
rainfall = horses_df["rainfall"].iloc[0] if "rainfall" in horses_df.columns else 0

# ── Race header ──
col1, col2, col3, col4 = st.columns(4)
col1.metric("📍 Race", selected_race.split(" R")[0] if " R" in selected_race else selected_race)
col2.metric("🏁 Race No.", selected_race.split(" R")[-1] if " R" in selected_race else "-")
col3.metric("🌿 Track", track_condition or "Unknown")
col4.metric("🌡️ Weather", f"{temperature:.0f}°C {'🌧️' if rainfall and rainfall > 0 else '☀️'}" if temperature else "N/A")

st.divider()

# ── Manual ratings input in sidebar ──
manual_ratings = {}
for horse in horses_df["horse_name"].tolist():
    manual_ratings[horse] = st.sidebar.number_input(
        horse, min_value=0.0, max_value=100.0, value=0.0, step=0.5,
        key=f"rating_{horse}"
    )

# ── Build value table ──
st.subheader(f"🎯 Value Analysis — {selected_race}")

rows = []
for _, horse in horses_df.iterrows():
    name = horse["horse_name"]
    odds = horse["win_odds_racingcom"]
    ml_prob = ml_map.get(name, 0)
    manual = manual_ratings.get(name, 0)

    # Fair odds from ML
    ml_fair_odds = round(1 / ml_prob, 2) if ml_prob > 0 else 0
    ml_edge = round((ml_prob - 1/odds) * 100, 1) if odds > 0 else 0

    # Manual rating edge (if entered)
    if manual > 0:
        manual_prob = manual / 100
        manual_fair_odds = round(1 / manual_prob, 2)
        manual_edge = round((manual_prob - 1/odds) * 100, 1)
        combined_edge = round((ml_edge + manual_edge) / 2, 1)
    else:
        manual_fair_odds = "-"
        manual_edge = "-"
        combined_edge = ml_edge

    rows.append({
        "horse": name,
        "jockey": horse.get("jockey_name", "-"),
        "odds": odds,
        "ml_prob": ml_prob,
        "ml_fair": ml_fair_odds,
        "ml_edge": ml_edge,
        "manual_rating": manual if manual > 0 else "-",
        "manual_fair": manual_fair_odds,
        "manual_edge": manual_edge,
        "combined_edge": combined_edge,
        "colour": get_value_colour(combined_edge if isinstance(combined_edge, (int, float)) else ml_edge),
        "label": get_value_label(combined_edge if isinstance(combined_edge, (int, float)) else ml_edge),
    })

# Sort by combined edge descending
rows.sort(key=lambda x: x["combined_edge"] if isinstance(x["combined_edge"], (int, float)) else -99, reverse=True)

# ── Display each horse as a colour-coded card ──
for row in rows:
    colour = row["colour"]
    
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, #12121A 0%, #1a1a2e 100%);
        border-left: 5px solid {colour};
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    ">
        <div>
            <span style="color:{colour};font-size:1.1rem;font-weight:800;">{row["horse"]}</span>
            <span style="color:#888;font-size:0.8rem;margin-left:12px;">{row["jockey"]}</span>
        </div>
        <div style="display:flex;gap:40px;align-items:center;">
            <div style="text-align:center;">
                <div style="color:#888;font-size:0.7rem;text-transform:uppercase;">Odds</div>
                <div style="color:#fff;font-weight:700;font-size:1.1rem;">${row["odds"]:.2f}</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#888;font-size:0.7rem;text-transform:uppercase;">ML Prob</div>
                <div style="color:#fff;font-weight:700;">{row["ml_prob"]*100:.1f}%</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#888;font-size:0.7rem;text-transform:uppercase;">Fair Odds</div>
                <div style="color:#fff;font-weight:700;">${row["ml_fair"]}</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#888;font-size:0.7rem;text-transform:uppercase;">ML Edge</div>
                <div style="color:{colour};font-weight:700;">{row["ml_edge"]:+.1f}%</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#888;font-size:0.7rem;text-transform:uppercase;">Manual Rating</div>
                <div style="color:#fff;font-weight:700;">{row["manual_rating"]}</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#888;font-size:0.7rem;text-transform:uppercase;">Manual Edge</div>
                <div style="color:{colour};font-weight:700;">{row["manual_edge"] if isinstance(row["manual_edge"], str) else f"{row['manual_edge']:+.1f}%"}</div>
            </div>
            <div style="
                background:{colour}22;
                border:1px solid {colour};
                border-radius:6px;
                padding:6px 14px;
                text-align:center;
                min-width:120px;
            ">
                <div style="color:{colour};font-weight:800;font-size:0.9rem;">{row["label"]}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# ── Colour legend ──
st.divider()
st.markdown("### 🎨 Colour Guide")
legend_html = """
<div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;">
    <div style="background:#00FF8822;border:1px solid #00FF88;border-radius:6px;padding:6px 14px;color:#00FF88;font-weight:700;">🔥 BACK IT — Edge &gt;20%</div>
    <div style="background:#7FFF0022;border:1px solid #7FFF00;border-radius:6px;padding:6px 14px;color:#7FFF00;font-weight:700;">✅ GOOD VALUE — Edge 10-20%</div>
    <div style="background:#FFD70022;border:1px solid #FFD700;border-radius:6px;padding:6px 14px;color:#FFD700;font-weight:700;">👀 WATCH — Edge 5-10%</div>
    <div style="background:#88888822;border:1px solid #888888;border-radius:6px;padding:6px 14px;color:#888888;font-weight:700;">⚪ NEUTRAL — Edge 0-5%</div>
    <div style="background:#FF8C0022;border:1px solid #FF8C00;border-radius:6px;padding:6px 14px;color:#FF8C00;font-weight:700;">⚠️ SKINNY — Edge -10-0%</div>
    <div style="background:#FF444422;border:1px solid #FF4444;border-radius:6px;padding:6px 14px;color:#FF4444;font-weight:700;">❌ SKIP — Edge &lt;-10%</div>
</div>
"""
st.markdown(legend_html, unsafe_allow_html=True)
