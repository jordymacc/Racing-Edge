import os
import sys
import streamlit as st
import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "models"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from theme import inject_css

st.set_page_config(page_title="Future Races", page_icon="🔮", layout="wide")
inject_css()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_value_colour(edge_pct):
    if edge_pct >= 20:    return "#00FF88"
    elif edge_pct >= 10:  return "#7FFF00"
    elif edge_pct >= 5:   return "#FFD700"
    elif edge_pct >= 0:   return "#888888"
    elif edge_pct >= -10: return "#FF8C00"
    else:                 return "#FF4444"

def get_value_label(edge_pct):
    if edge_pct >= 20:    return "🔥 BACK IT"
    elif edge_pct >= 10:  return "✅ GOOD VALUE"
    elif edge_pct >= 5:   return "👀 WATCH"
    elif edge_pct >= 0:   return "⚪ NEUTRAL"
    elif edge_pct >= -10: return "⚠️ SKINNY"
    else:                 return "❌ SKIP"

st.markdown("# 🔮 Future Races")
st.markdown("<p style='color:#888;margin-top:-1rem;'>Next 3 days of race fields with early ML ratings</p>",
            unsafe_allow_html=True)

# ── Load future races ──
if not DATABASE_URL:
    st.error("No database connection")
    st.stop()

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Check table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'future_races'
        )
    """)
    if not cur.fetchone()[0]:
        st.info("⏳ Future races data not yet collected. The system will populate this within the next 6 hours.")
        conn.close()
        st.stop()

    cur.execute("""
        SELECT DISTINCT race_date, venue, state
        FROM future_races
        WHERE race_date > CURRENT_DATE::text
        ORDER BY race_date, venue
    """)
    meetings = cur.fetchall()
    conn.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

if not meetings:
    st.info("⏳ No future race data yet. The scraper runs every 6 hours and will populate this soon.")
    st.stop()

# ── Date filter ──
dates = sorted(list(set(m[0] for m in meetings)))
st.sidebar.markdown("## 📅 Filter")
selected_date = st.sidebar.selectbox("Select Date", dates,
    format_func=lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%A %d %b"))
selected_state = st.sidebar.selectbox("State", ["All"] + sorted(list(set(m[2] for m in meetings))))

# ── Filter meetings ──
filtered = [(d,v,s) for d,v,s in meetings 
            if d == selected_date and (selected_state == "All" or s == selected_state)]

if not filtered:
    st.info("No meetings found for selected filters.")
    st.stop()

st.markdown(f"### 📅 {datetime.strptime(selected_date, '%Y-%m-%d').strftime('%A %d %B %Y')}")
st.markdown(f"<p style='color:#888;'>{len(filtered)} meeting(s)</p>", unsafe_allow_html=True)

# ── Load ML model ──
try:
    import joblib
    from dashboard_predictions import build_features
    import numpy as np
    model_data = joblib.load(BASE_DIR / "models" / "winner_predictor_v4.pkl")
    model = model_data["model"]
    FEATURES = [
        "win_odds_racingcom", "implied_prob", "is_favorite", "market_rank",
        "jockey_win_rate", "trainer_win_rate", "combined_form",
        "jockey_odds_interaction", "trainer_odds_interaction",
        "track_condition_score", "is_good", "is_soft", "is_heavy", "is_synth",
        "temperature", "rainfall", "wet_track", "temp_normalized"
    ]
    ml_available = True
except:
    ml_available = False

# ── Display each meeting ──
for race_date, venue, state in sorted(filtered):
    st.markdown(f"## 📍 {venue} ({state})")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT race_number, race_name, horse_name, jockey_name,
                   trainer_name, win_odds, barrier
            FROM future_races
            WHERE race_date = %s AND venue = %s
            ORDER BY race_number, win_odds ASC NULLS LAST
        """, (race_date, venue))
        cols = ["race_number","race_name","horse_name","jockey_name",
                "trainer_name","win_odds","barrier"]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
        conn.close()
    except Exception as e:
        st.error(f"Error: {e}")
        continue

    if df.empty:
        continue

    # ── Race selector tabs ──
    races = sorted(df["race_number"].unique())
    if len(races) > 1:
        tabs = st.tabs([f"R{r}" for r in races])
    else:
        tabs = [st.container()]

    for i, race_num in enumerate(races):
        race_df = df[df["race_number"] == race_num].copy()
        race_name = race_df["race_name"].iloc[0]

        with tabs[i]:
            st.markdown(f"**{race_name}** — {len(race_df)} runners")

            # Build ML features if available
            ml_probs = {}
            if ml_available and race_df["win_odds"].notna().any():
                try:
                    # Build minimal feature set from available data
                    valid = race_df[race_df["win_odds"].notna()].copy()
                    valid["win_odds_racingcom"] = valid["win_odds"]
                    valid["implied_prob"] = 1 / valid["win_odds"]
                    min_odds = valid["win_odds"].min()
                    valid["is_favorite"] = (valid["win_odds"] == min_odds).astype(int)
                    valid["market_rank"] = valid["win_odds"].rank()
                    valid["jockey_win_rate"] = 0.0
                    valid["trainer_win_rate"] = 0.0
                    valid["combined_form"] = 0.0
                    valid["jockey_odds_interaction"] = 0.0
                    valid["trainer_odds_interaction"] = 0.0
                    valid["track_condition_score"] = 2.0
                    valid["is_good"] = 0
                    valid["is_soft"] = 0
                    valid["is_heavy"] = 0
                    valid["is_synth"] = 0
                    valid["temperature"] = 20.0
                    valid["rainfall"] = 0.0
                    valid["wet_track"] = 0
                    valid["temp_normalized"] = 0.0
                    X = valid[FEATURES].fillna(0)
                    probs = model.predict_proba(X)[:, 1]
                    for j, (_, row) in enumerate(valid.iterrows()):
                        ml_probs[row["horse_name"]] = probs[j]
                except:
                    pass

            # Display horses
            for _, horse in race_df.iterrows():
                name = horse["horse_name"]
                odds = horse["win_odds"]
                ml_prob = ml_probs.get(name, 0)
                
                if odds and odds > 0 and ml_prob > 0:
                    edge = round((ml_prob - 1/odds) * 100, 1)
                    fair_odds = round(1/ml_prob, 2)
                    colour = get_value_colour(edge)
                    label = get_value_label(edge)
                else:
                    edge = 0
                    fair_odds = 0
                    colour = "#444"
                    label = "—"

                odds_display = f"${odds:.2f}" if odds else "—"
                fair_display = f"${fair_odds}" if fair_odds > 0 else "—"
                prob_display = f"{ml_prob*100:.1f}%" if ml_prob > 0 else "—"
                barrier = horse.get("barrier") or "—"

                card = f"""
                <div style="
                    background:linear-gradient(135deg,#12121A 0%,#1a1a2e 100%);
                    border-left:4px solid {colour};
                    border-radius:8px;
                    padding:10px 14px;
                    margin-bottom:6px;
                ">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
                        <div>
                            <span style="color:{colour};font-size:0.95rem;font-weight:800;">{name}</span>
                            <span style="color:#555;font-size:0.7rem;margin-left:8px;">Barrier {barrier}</span>
                            <div style="color:#666;font-size:0.75rem;">{horse.get("jockey_name") or "—"} | {horse.get("trainer_name") or "—"}</div>
                        </div>
                        <div style="background:{colour}22;border:1px solid {colour};border-radius:5px;padding:3px 10px;">
                            <span style="color:{colour};font-size:0.75rem;font-weight:700;">{label}</span>
                        </div>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:5px;">
                        <div style="background:#0A0A0F;border-radius:5px;padding:6px;text-align:center;">
                            <div style="color:#555;font-size:0.6rem;text-transform:uppercase;">Odds</div>
                            <div style="color:#fff;font-size:0.9rem;font-weight:700;">{odds_display}</div>
                        </div>
                        <div style="background:#0A0A0F;border-radius:5px;padding:6px;text-align:center;">
                            <div style="color:#555;font-size:0.6rem;text-transform:uppercase;">ML Prob</div>
                            <div style="color:#fff;font-size:0.9rem;font-weight:700;">{prob_display}</div>
                        </div>
                        <div style="background:#0A0A0F;border-radius:5px;padding:6px;text-align:center;">
                            <div style="color:#555;font-size:0.6rem;text-transform:uppercase;">Fair Odds</div>
                            <div style="color:#fff;font-size:0.9rem;font-weight:700;">{fair_display}</div>
                        </div>
                        <div style="background:#0A0A0F;border-radius:5px;padding:6px;text-align:center;">
                            <div style="color:#555;font-size:0.6rem;text-transform:uppercase;">Edge</div>
                            <div style="color:{colour};font-size:0.9rem;font-weight:700;">{edge:+.1f}% if odds else "—"</div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(card, unsafe_allow_html=True)

    st.divider()
