import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import inject_css

import os
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# Define BASE_DIR first (before we use it)
BASE_DIR = Path(__file__).resolve().parent.parent

# Now we can use BASE_DIR in imports
import sys
sys.path.insert(0, str(BASE_DIR / 'models'))

from ratings_engine import (
    analyse_race,
    clean_number_column,
    create_basic_rating,
    calculate_fair_odds,
    apply_v2_context_adjustments,
    apply_v23_template_scoring,
    apply_manual_speed_map,
)

from csv_tools import (
    create_race_template,
    validate_uploaded_csv,
    create_column_summary,
)

from rule_engine import get_betting_signals

# Load live odds
odds_df = pd.read_csv(BASE_DIR / "live_odds.csv")
# ═══════════════════════════════════════════════════════════
# 🎯 LIVE BETTING SIGNALS SECTION
# ═══════════════════════════════════════════════════════════

st.title("🐎 JordyMac Racing Engine")
st.subheader("🎯 Live Betting Signals")

# Auto-refresh every 30 seconds
st_autorefresh(interval=30000, key="signals_refresh")

try:
    signals = get_betting_signals()
    
    if signals:
        st.success(f"✅ {len(signals)} active signals detected")
        
        for sig in signals:
            # Create colored boxes based on signal type
            if sig['confidence'] == "HIGH":
                with st.container():
                    st.markdown(f"### 🔥 {sig['signal']}")
                    st.success(f"**{sig['race']}**")
            elif sig['confidence'] == "AVOID":
                with st.container():
                    st.markdown(f"### 🚨 {sig['signal']}")
                    st.error(f"**{sig['race']}**")
            else:
                with st.container():
                    st.markdown(f"### ⚡ {sig['signal']}")
                    st.warning(f"**{sig['race']}**")
            
            # Display signal details in columns
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🐴 Horse", sig['horse'])
            with col2:
                st.metric("💰 Current Odds", f"${sig['current_odds']:.2f}")
            with col3:
                st.metric("📊 Movement", sig['movement'], delta=sig['movement'])
            with col4:
                st.metric("🎲 Bet Type", sig['bet_type'])
            
            # Confidence badge
            if sig['confidence'] == "HIGH":
                st.markdown("**Confidence:** 🟢 HIGH")
            elif sig['confidence'] == "MEDIUM":
                st.markdown("**Confidence:** 🟡 MEDIUM")
            else:
                st.markdown("**Confidence:** 🔴 AVOID")
            
            st.divider()
    
    else:
        st.info("⏳ No strong signals detected yet. Collecting more data...")
        st.caption("Signals require at least 5 minutes of odds movement data.")

except Exception as e:
    st.warning(f"⚠️ Betting signals unavailable: {e}")
    st.caption("Make sure the scraper is running to collect live odds data.")

st.divider()

# Continue with your existing dashboard code below...
# -----------------------------
# SAFE APP COLUMN HELPER
# -----------------------------
def ensure_app_columns(dataframe):
    safe_df = dataframe.copy()

    default_values = {
        "Horse": "",
        "Rating": 0,
        "Confidence": 0,
        "Win Execution": 0,
        "Fair Odds": 0,
        "Market Odds": 0,
        "Overlay": False,
        "Overlay %": 0,
        "Bet Call": "NO BET ❌",
        "Model Notes": "No model notes available",
        "V2 Adjustment": 0,
        "Race Context": "",
        "Odds Source": "Uploaded / Database Odds",
        "Map Score": 5,
        "Recent Form Score": 5,
        "Track Suitability Score": 5,
        "Distance Suitability Score": 5,
        "V2.3 Template Score": 5,
        "Map Position": "Neutral",
        "Map Source": "CSV / Default",
    }

    for column, default_value in default_values.items():
        if column not in safe_df.columns:
            safe_df[column] = default_value

    return safe_df

# ═══════════════════════════════════════════════════════════
# 🤖 ML PREDICTIONS SECTION
# ═══════════════════════════════════════════════════════════

st.header("🤖 Machine Learning Predictions")

try:
    # Ensure models folder is in path
    import sys
    from pathlib import Path
    
    models_path = str(Path(__file__).resolve().parent.parent / 'models')
    if models_path not in sys.path:
        sys.path.insert(0, models_path)
    
    import dashboard_predictions
    
    # Get predictions
    predictions = dashboard_predictions.get_ml_predictions_for_dashboard()
    
    if predictions is not None and len(predictions) > 0:
        
        # Top picks across all races
        st.subheader("🏆 Top ML Picks")
        
if 'win_probability' not in predictions.columns and 'predicted_prob' in predictions.columns:
    predictions['win_probability'] = predictions['predicted_prob']

        top_picks = predictions.nlargest(5, 'win_probability')
        
        for idx, pick in top_picks.iterrows():
            # Color based on confidence
            if pick['confidence'] == 'HIGH':
                st.success(f"**{pick['race_name']}** — {pick['horse_name']}")
            elif pick['confidence'] == 'MEDIUM':
                st.warning(f"**{pick['race_name']}** — {pick['horse_name']}")
            else:
                st.info(f"**{pick['race_name']}** — {pick['horse_name']}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("💰 Odds", f"${pick['current_odds']:.1f}")
            with col2:
                st.metric("🎯 Win Probability", f"{pick['win_probability']*100:.1f}%")
            with col3:
                fav_label = "✅ Fav" if pick['is_favorite'] == 1 else "❌"
                st.metric("📊 Market", fav_label)
            with col4:
                confidence_emoji = "🔥" if pick['confidence'] == 'HIGH' else "⚡" if pick['confidence'] == 'MEDIUM' else "💡"
                st.metric("🎲 Confidence", f"{confidence_emoji} {pick['confidence']}")
            
            st.divider()
        
        st.caption("🤖 Powered by Gradient Boosting ML Model | Updates every 30 seconds")
    
    else:
        st.info("⏳ ML predictions loading... (need recent odds data)")

except Exception as e:
    st.error(f"⚠️ ML predictions unavailable: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.caption("Debug: Check if model exists and paths are correct")

st.divider()
# -----------------------------
# SAFE TABLE VIEW HELPER
# -----------------------------
def safe_view(dataframe, columns):
    """
    Safely selects columns for dashboard tables.
    If a column is missing, ensure_app_columns creates it first.
    """
    safe_df = ensure_app_columns(dataframe)

    for column in columns:
        if column not in safe_df.columns:
            safe_df[column] = ""

    return safe_df[columns]


# -----------------------------
# VERSION 2.6 MARKET MOVEMENT DETECTION (STEAM/DRIFT)
# -----------------------------
def apply_market_movement(df):
    working_df = df.copy()

    if "Previous Odds" not in working_df.columns:
        working_df["Previous Odds"] = working_df["Market Odds"]

    if "Current Odds" not in working_df.columns:
        working_df["Current Odds"] = working_df["Market Odds"]

    working_df["Previous Odds"] = pd.to_numeric(
        working_df["Previous Odds"], errors="coerce"
    ).fillna(0)

    working_df["Current Odds"] = pd.to_numeric(
        working_df["Current Odds"], errors="coerce"
    ).fillna(0)

    working_df["Odds Change"] = working_df["Current Odds"] - working_df["Previous Odds"]

    working_df["Odds Change %"] = working_df.apply(
        lambda row: round(
            ((row["Current Odds"] - row["Previous Odds"]) / row["Previous Odds"]) * 100,
            2
        )
        if row["Previous Odds"] > 0 else 0,
        axis=1
    )

    def classify_move(row):
        if row["Current Odds"] < row["Previous Odds"]:
            return "Steamer"
        elif row["Current Odds"] > row["Previous Odds"]:
            return "Drifter"
        return "No Change"

    working_df["Market Move"] = working_df.apply(classify_move, axis=1)

    def steam_signal(row):
        if row["Market Move"] == "Steamer" and row["Odds Change %"] <= -15:
            return "🔥 Strong Steam"
        elif row["Market Move"] == "Steamer" and row["Odds Change %"] <= -8:
            return "⚡ Light Steam"
        elif row["Market Move"] == "Drifter" and row["Odds Change %"] >= 15:
            return "❄️ Strong Drift"
        elif row["Market Move"] == "Drifter" and row["Odds Change %"] >= 8:
            return "🌫️ Light Drift"
        return "—"

    working_df["Steam Signal"] = working_df.apply(steam_signal, axis=1)

    return working_df


    if df is None or df.empty:
        return

    conn = sqlite3.connect("database/racing.db")
    ensure_market_snapshots_table(conn)

    snapshot_ts = datetime.now().isoformat()

    rows = []
    for _, row in df.iterrows():
        rows.append(
            (
                snapshot_ts,
                race_name,
                str(row.get("Horse", "")),
                float(row.get("Market Odds", 0)) if pd.notna(row.get("Market Odds", 0)) else 0,
                float(row.get("Fair Odds", 0)) if pd.notna(row.get("Fair Odds", 0)) else 0,
                int(bool(row.get("Overlay", False))),
                float(row.get("Confidence", 0)) if pd.notna(row.get("Confidence", 0)) else 0,
                str(row.get("Odds Source", "")),
            )
        )

    conn.executemany(
        """
        INSERT INTO market_snapshots(
            snapshot_ts, race, horse, market_odds, fair_odds, overlay, confidence, odds_source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows
    )
    conn.commit()
    conn.close()
def detect_false_favourites(df):
    working_df = df.copy()

    working_df["Market Odds"] = pd.to_numeric(
        working_df["Market Odds"], errors="coerce"
    ).fillna(999)

    false_favs = working_df[
        (working_df["Market Odds"] <= 4.0) &
        (working_df["Overlay"] == False) &
        (working_df["Confidence"] <= 6)
    ].copy()

    false_favs["False Favourite Flag"] = "⚠️ False Favourite"
    return false_favs
# -----------------------------
# VERSION 2.7 SNAPSHOT STORAGE
# -----------------------------
def ensure_market_snapshots_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_ts TEXT NOT NULL,
            race TEXT NOT NULL,
            horse TEXT NOT NULL,
            market_odds REAL,
            fair_odds REAL,
            overlay INTEGER,
            confidence REAL,
            odds_source TEXT
        )
        """
    )
    conn.commit()


def load_last_snapshot_previous_odds(df, race_name):
    if df is None or df.empty:
        return df

    conn = sqlite3.connect("database/racing.db")
    ensure_market_snapshots_table(conn)

    query = """
    WITH ranked AS (
        SELECT
            horse,
            snapshot_ts,
            market_odds,
            ROW_NUMBER() OVER (PARTITION BY horse ORDER BY snapshot_ts DESC) AS rn
        FROM market_snapshots
        WHERE race = ?
    )
    SELECT horse, snapshot_ts, market_odds
    FROM ranked
    WHERE rn = 1
    """

    snap_df = pd.read_sql(query, conn, params=(race_name,))
    conn.close()

    if snap_df.empty:
        return df

    odds_map = dict(zip(snap_df["horse"], snap_df["market_odds"]))
    ts_map = dict(zip(snap_df["horse"], snap_df["snapshot_ts"]))

    if "Previous Odds" not in df.columns:
        df["Previous Odds"] = df["Market Odds"]

    df["Previous Odds"] = df["Horse"].map(odds_map).fillna(df["Previous Odds"])
    df["Previous Odds Timestamp"] = df["Horse"].map(ts_map)

    prev_ts = pd.to_datetime(df["Previous Odds Timestamp"], errors="coerce")
    df["Minutes Since Last Snapshot"] = (
        (pd.Timestamp.now() - prev_ts).dt.total_seconds() / 60
    )

    return df


def save_market_snapshots(df, race_name):
    if df is None or df.empty:
        return

    conn = sqlite3.connect("database/racing.db")
    ensure_market_snapshots_table(conn)

    snapshot_ts = datetime.now().isoformat()

    rows = []
    for _, row in df.iterrows():
        rows.append(
            (
                snapshot_ts,
                race_name,
                str(row.get("Horse", "")),
                float(row.get("Market Odds", 0)) if pd.notna(row.get("Market Odds", 0)) else 0,
                float(row.get("Fair Odds", 0)) if pd.notna(row.get("Fair Odds", 0)) else 0,
                int(bool(row.get("Overlay", False))),
                float(row.get("Confidence", 0)) if pd.notna(row.get("Confidence", 0)) else 0,
                str(row.get("Odds Source", "")),
            )
        )

    conn.executemany(
        """
        INSERT INTO market_snapshots(
            snapshot_ts, race, horse, market_odds, fair_odds, overlay, confidence, odds_source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows
    )
    conn.commit()
    conn.close()
def load_odds_map_from_snapshots(race_name, minutes_ago):
    conn = sqlite3.connect("database/racing.db")
    cutoff_ts = (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()

    query = """
    WITH ranked AS (
        SELECT
            horse,
            market_odds,
            snapshot_ts,
            ROW_NUMBER() OVER (PARTITION BY horse ORDER BY snapshot_ts DESC) AS rn
        FROM market_snapshots
        WHERE race = ?
          AND snapshot_ts <= ?
    )
    SELECT horse, market_odds
    FROM ranked
    WHERE rn = 1
    """

    snap_df = pd.read_sql(query, conn, params=(race_name, cutoff_ts))
    conn.close()

    if snap_df.empty:
        return {}

    return dict(zip(snap_df["horse"], snap_df["market_odds"]))


def apply_v28_window_signals(df, race_name):
    working_df = df.copy()

    # Ensure numeric
    working_df["Market Odds"] = pd.to_numeric(working_df["Market Odds"], errors="coerce").fillna(0)

    # Make sure Minutes Since Last Snapshot exists (for Late Plunge)
    if "Minutes Since Last Snapshot" not in working_df.columns:
        working_df["Minutes Since Last Snapshot"] = 999

    # --- 5-minute window (steam) ---
    odds_5m = load_odds_map_from_snapshots(race_name, 5)
    working_df["Odds 5m Ago"] = working_df["Horse"].map(odds_5m)
    working_df["Odds 5m Ago"] = pd.to_numeric(working_df["Odds 5m Ago"], errors="coerce")

    working_df["Odds Change 5m %"] = working_df.apply(
        lambda r: (
            ((r["Market Odds"] - r["Odds 5m Ago"]) / r["Odds 5m Ago"]) * 100
            if pd.notna(r["Odds 5m Ago"]) and r["Odds 5m Ago"] > 0
            else None
        ),
        axis=1
    )

    def signal_5m(row):
        pct = row["Odds Change 5m %"]
        if pct is None:
            return "—"
        # Steam = shortening => negative pct
        if pct <= -15:
            return "🔥 5-min Strong Steam"
        if pct <= -8:
            return "⚡ 5-min Light Steam"
        return "—"

    working_df["5m Signal"] = working_df.apply(signal_5m, axis=1)

    # --- 10-minute window (drift) ---
    odds_10m = load_odds_map_from_snapshots(race_name, 10)
    working_df["Odds 10m Ago"] = working_df["Horse"].map(odds_10m)
    working_df["Odds 10m Ago"] = pd.to_numeric(working_df["Odds 10m Ago"], errors="coerce")

    working_df["Odds Change 10m %"] = working_df.apply(
        lambda r: (
            ((r["Market Odds"] - r["Odds 10m Ago"]) / r["Odds 10m Ago"]) * 100
            if pd.notna(r["Odds 10m Ago"]) and r["Odds 10m Ago"] > 0
            else None
        ),
        axis=1
    )

    def signal_10m(row):
        pct = row["Odds Change 10m %"]
        if pct is None:
            return "—"
        # Drift = drifting longer => positive pct
        if pct >= 15:
            return "❄️ 10-min Strong Drift"
        if pct >= 8:
            return "🌫️ 10-min Light Drift"
        return "—"

    working_df["10m Signal"] = working_df.apply(signal_10m, axis=1)

    # --- Late plunge (use V2.6 steam + time since last snapshot) ---
    def late_plunge(row):
        mins = row.get("Minutes Since Last Snapshot", 999)
        if row.get("Steam Signal", "") == "🔥 Strong Steam" and mins <= 5:
            return "🚨 Late Plunge"
        return "—"

    working_df["Late Plunge Signal"] = working_df.apply(late_plunge, axis=1)

    return working_df

# -----------------------------
# PAGE SETUP
# -----------------------------
st.title("🐎 JordyMac Racing Engine")

st.write("Last Updated:", datetime.now())

st_autorefresh(interval=30000, key="refresh")
# -----------------------------
# SYSTEM HEALTH CHECK
# -----------------------------
with st.expander("System Health Check 🛠️"):

    health_checks = []

    # Check app.py
    health_checks.append(
        {
            "Check": "dashboard/app.py exists",
            "Status": "✅ PASS" if os.path.exists("dashboard/app.py") else "❌ FAIL"
        }
    )

    # Check ratings_engine.py
    health_checks.append(
        {
            "Check": "dashboard/ratings_engine.py exists",
            "Status": "✅ PASS" if os.path.exists("dashboard/ratings_engine.py") else "❌ FAIL"
        }
    )

    # Check database
    health_checks.append(
        {
            "Check": "database/racing.db exists",
            "Status": "✅ PASS" if os.path.exists("database/racing.db") else "❌ FAIL"
        }
    )

    # Check database tables
    try:

        conn_check = sqlite3.connect("database/racing.db")

        table_check = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table'",
            conn_check
        )

        conn_check.close()

        health_checks.append(
            {
                "Check": "SQLite database opens",
                "Status": "✅ PASS"
            }
        )

        health_checks.append(
            {
                "Check": "Database table count",
                "Status": str(len(table_check))
            }
        )

    except Exception as error:

        health_checks.append(
            {
                "Check": "SQLite database opens",
                "Status": f"❌ FAIL: {error}"
            }
        )

    health_df = pd.DataFrame(health_checks)

    st.dataframe(health_df)

# -----------------------------
# CSV UPLOADER
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload Race CSV",
    type=["csv"],
    key="race_csv_uploader"
)


# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("Race Selector")

race = st.sidebar.selectbox(
    "Choose Race",
    [
        "Pakenham Race 1",
        "Morphettville Race 3"
    ],
    key="race_selector"
)

with st.sidebar.expander("V2.7 Snapshot Storage 🧾"):
    v27_save_snapshots = st.checkbox(
        "Save market snapshots every refresh",
        value=True
    )
with st.sidebar.expander("V2.8 Window Alerts ⏱️"):
    v28_enable = st.checkbox(
        "Enable 5-min Steam / 10-min Drift / Late Plunge",
        value=True
    )
# -----------------------------
# MODEL WEIGHT CONTROLS
# -----------------------------
with st.sidebar.expander("Model Weights ⚖️"):

    market_weight = st.slider(
        "Market Weight",
        min_value=0,
        max_value=100,
        value=35,
        step=5,
        key="market_weight"
    )

    barrier_weight = st.slider(
        "Barrier Weight",
        min_value=0,
        max_value=100,
        value=15,
        step=5,
        key="barrier_weight"
    )

    weight_weight = st.slider(
        "Weight Carried Weight",
        min_value=0,
        max_value=100,
        value=10,
        step=5,
        key="weight_weight"
    )

    jockey_weight = st.slider(
        "Jockey Weight",
        min_value=0,
        max_value=100,
        value=15,
        step=5,
        key="jockey_weight"
    )

    trainer_weight = st.slider(
        "Trainer Weight",
        min_value=0,
        max_value=100,
        value=15,
        step=5,
        key="trainer_weight"
    )

    position_weight = st.slider(
        "File Order / Fallback Weight",
        min_value=0,
        max_value=100,
        value=10,
        step=5,
        key="position_weight"
    )

model_weights = {
    "market": market_weight,
    "barrier": barrier_weight,
    "weight": weight_weight,
    "jockey": jockey_weight,
    "trainer": trainer_weight,
    "position": position_weight
}
# -----------------------------
# VERSION 2 RACE CONTEXT CONTROLS
# -----------------------------
with st.sidebar.expander("V2 Race Context 🧠"):

    track_condition = st.selectbox(
        "Track Condition",
        [
            "Good 3",
            "Good 4",
            "Soft 5",
            "Soft 6",
            "Soft 7",
            "Heavy 8",
            "Heavy 9",
            "Heavy 10"
        ],
        key="v2_track_condition"
    )

    race_distance = st.number_input(
        "Race Distance (metres)",
        min_value=800,
        max_value=4000,
        value=1200,
        step=100,
        key="v2_race_distance"
    )

    race_pressure = st.selectbox(
        "Race Pressure",
        [
            "Low",
            "Even",
            "High"
        ],
        key="v2_race_pressure"
    )

race_context = {
    "track_condition": track_condition,
    "distance": race_distance,
    "race_pressure": race_pressure
}

# -----------------------------
# DATABASE TABLES
# -----------------------------
table_names = {
    "Pakenham Race 1": "pakenham_r1",
    "Morphettville Race 3": "morphettville_r3"
}


# -----------------------------
# LOAD DATA
# -----------------------------
if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    st.success("Uploaded CSV is now being used for this race ✅")

else:

    selected_table = table_names[race]

    try:

        conn = sqlite3.connect("database/racing.db")

        query = f"SELECT * FROM {selected_table}"

        df = pd.read_sql(query, conn)

        conn.close()

    except Exception as error:

        st.error("Could not load the database race table.")

        st.write(error)

        st.stop()


# -----------------------------
# PAGE HEADER
# -----------------------------
st.header(race)
# -----------------------------
# VERSION 2 CSV TEMPLATE + VALIDATOR
# -----------------------------
with st.expander("Version 2 CSV Template + Upload Validator 📄"):

    st.write(
        "Download the clean race template, or inspect the uploaded CSV to see "
        "which columns are found, missing, or extra."
    )

    template_df = create_race_template()

    template_csv = template_df.to_csv(index=False)

    st.download_button(
        label="Download Version 2 Race Template CSV",
        data=template_csv,
        file_name="race_template_v2.csv",
        mime="text/csv",
        key="download_v2_race_template"
    )

    if uploaded_file is not None:

        st.write("### Uploaded CSV Column Validation")

        validation = validate_uploaded_csv(df)

        st.dataframe(
            validation["validation_table"],
            use_container_width=True
        )

        if len(validation["missing_columns"]) > 0:

            st.warning(
                f"Missing template columns: {validation['missing_columns']}"
            )

        else:

            st.success("Uploaded CSV matches the Version 2 template ✅")

        if len(validation["extra_columns"]) > 0:

            st.info(
                f"Extra columns found: {validation['extra_columns']}"
            )

        st.write("### Uploaded CSV Column Summary")

        column_summary = create_column_summary(df)

        st.dataframe(
            column_summary,
            use_container_width=True
        )

    else:

        st.info("Upload a CSV to see column validation.")

# -----------------------------
# COLUMN MAPPING
# -----------------------------
required_columns = [
    "Horse",
    "Rating",
    "Fair Odds",
    "Market Odds"
]

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns and uploaded_file is not None:

    st.warning("Your uploaded CSV needs mapping before analysis.")

    st.write("Preview of uploaded file:")

    st.dataframe(df.head())

    available_columns = list(df.columns)

    auto_option = "Create Automatically / Not In File"

    options = [auto_option] + available_columns

    horse_col = st.selectbox(
        "Which column contains horse names?",
        available_columns,
        key="map_horse_col"
    )

    rating_col = st.selectbox(
        "Which column contains your rating?",
        options,
        key="map_rating_col"
    )

    fair_odds_col = st.selectbox(
        "Which column contains fair odds / my price?",
        options,
        key="map_fair_odds_col"
    )

    market_odds_col = st.selectbox(
        "Which column contains market odds / live odds?",
        options,
        key="map_market_odds_col"
    )

    mapped_df = pd.DataFrame()

    mapped_df["Horse"] = df[horse_col].astype(str)

    if rating_col == auto_option:

        mapped_df["Rating"] = create_basic_rating(
            df,
            weights=model_weights
        )

    else:

        mapped_df["Rating"] = clean_number_column(df[rating_col])

    if fair_odds_col == auto_option:

        mapped_df["Fair Odds"] = calculate_fair_odds(mapped_df["Rating"])

    else:

        mapped_df["Fair Odds"] = clean_number_column(df[fair_odds_col])

    if market_odds_col == auto_option:

        mapped_df["Market Odds"] = mapped_df["Fair Odds"]

    else:

        mapped_df["Market Odds"] = clean_number_column(df[market_odds_col])

    df = mapped_df


# -----------------------------
# FINAL REQUIRED COLUMN CHECK
# -----------------------------
missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:

    st.error(
        f"Still missing required columns: {missing_columns}"
    )

    st.stop()


# -----------------------------
# ANALYSE RACE
# -----------------------------
df = analyse_race(df)

if df.empty:

    st.warning("No valid runners found after analysing the data.")

    st.stop()


# -----------------------------
# VERSION 2 MANUAL LIVE ODDS UPDATER
# -----------------------------
with st.expander("Version 2 Manual Live Odds Updater 🔴"):

    st.write(
        "Edit the Market Odds below to reflect the latest prices you are seeing. "
        "Tick the apply box to push those odds into the model."
    )

    odds_editor_df = df[["Horse", "Market Odds"]].copy()

    edited_odds_df = st.data_editor(
        odds_editor_df,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="manual_live_odds_editor"
    )

    apply_manual_live_odds = st.checkbox(
        "Apply manual live odds to model",
        value=False,
        key="apply_manual_live_odds"
    )

    if apply_manual_live_odds:

        edited_odds_df["Market Odds"] = pd.to_numeric(
            edited_odds_df["Market Odds"],
            errors="coerce"
        ).fillna(0)

        # store previous odds BEFORE changing
        df["Previous Odds"] = pd.to_numeric(
            df["Market Odds"], errors="coerce"
        ).fillna(0)

        odds_map = edited_odds_df.set_index("Horse")["Market Odds"].to_dict()

        # set current odds from the edited mapping
        df["Current Odds"] = df["Horse"].map(odds_map).fillna(df["Market Odds"])
        df["Market Odds"] = df["Current Odds"]

        df["Odds Source"] = "Manual Live Odds"

        st.success("Manual live odds applied to the model ✅")

    else:

        # initialize columns if missing
        if "Current Odds" not in df.columns:
            df["Current Odds"] = df["Market Odds"]

        if "Previous Odds" not in df.columns:
            df["Previous Odds"] = df["Market Odds"]

        df["Odds Source"] = "Uploaded / Database Odds"
        
# Apply Version 2 race context layer
df = apply_v2_context_adjustments(
    df,
    race_context
)

# V2.7: if NOT using manual odds, pull previous odds from the last saved snapshot
if not apply_manual_live_odds:
    df = load_last_snapshot_previous_odds(df, race)

df = apply_market_movement(df)

# V2.8: window signals from saved snapshots
try:
    v28_enable
except NameError:
    v28_enable = False

if v28_enable:
    df = apply_v28_window_signals(df, race)
    with st.expander("V2.8 ⏱️ 5-min Steam / 10-min Drift / Late Plunge"):
        strong_5 = df[df["5m Signal"].str.contains("Strong", na=False)]
        drift_10 = df[df["10m Signal"].str.contains("Drift", na=False)]
        late = df[df["Late Plunge Signal"] != "—"]

        if not strong_5.empty:
            st.success(f"🔥 {len(strong_5)} strong 5-min steam runners")
            st.dataframe(
                safe_view(
                    strong_5,
                    ["Horse", "Market Odds", "Odds 5m Ago", "Odds Change 5m %", "5m Signal", "Overlay", "Bet Call"]
                ),
                use_container_width=True
            )
        else:
            st.info("No strong 5-min steam right now.")

        if not drift_10.empty:
            st.warning(f"❄️ {len(drift_10)} 10-min drift runners detected")
            st.dataframe(
                safe_view(
                    drift_10,
                    ["Horse", "Market Odds", "Odds 10m Ago", "Odds Change 10m %", "10m Signal", "Overlay", "Bet Call"]
                ),
                use_container_width=True
            )
        else:
            st.info("No 10-min drift detected right now.")

        if not late.empty:
            st.error(f"🚨 {len(late)} late plunges detected")
            st.dataframe(
                safe_view(
                    late,
                    ["Horse", "Market Odds", "Steam Signal", "Minutes Since Last Snapshot", "Late Plunge Signal", "Overlay", "Bet Call"]
                ),
                use_container_width=True
            )
        else:
            st.info("No late plunges detected right now.")   
    
# V2.7: save current market odds snapshot
if v27_save_snapshots:
    save_market_snapshots(df, race)
# -----------------------------
# VERSION 2.4 MANUAL SPEED MAP INPUT
# -----------------------------
with st.expander("Version 2.4 Manual Speed Map Input 🐎"):

    st.write(
        "Set each runner's expected race position. "
        "This feeds into the map score before the V2.3 template scoring runs."
    )

    if "Map Position" not in df.columns:
        df["Map Position"] = "Neutral"

    speed_map_editor_df = df[
        [
            "Horse",
            "Map Position"
        ]
    ].copy()

    speed_map_editor_df["Map Position"] = speed_map_editor_df["Map Position"].fillna("Neutral")

    edited_speed_map_df = st.data_editor(
        speed_map_editor_df,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="manual_speed_map_editor",
        column_config={
            "Map Position": st.column_config.SelectboxColumn(
                "Map Position",
                options=[
                    "Lead",
                    "On-speed",
                    "Handy",
                    "Midfield",
                    "Back",
                    "Wide",
                    "Neutral"
                ],
                required=True
            )
        }
    )

    apply_manual_map = st.checkbox(
        "Apply manual speed map to model",
        value=False,
        key="apply_manual_speed_map"
    )

    if apply_manual_map:

        df = apply_manual_speed_map(
            df,
            edited_speed_map_df
        )

        st.success("Manual speed map applied to model ✅")

    else:

        if "Map Source" not in df.columns:
            df["Map Source"] = "CSV / Default"
            # -----------------------------
# VERSION 2.5 TRACK BIAS INPUT
# -----------------------------
with st.expander("Version 2.5 Track Bias Engine 🎛️"):

    st.write(
        "Apply race-day track pattern adjustments."
    )

    selected_bias = st.selectbox(
        "Track Bias Profile",
        [
            "Neutral",
            "Leader Bias",
            "Backmarker Bias",
            "Wide Lanes",
            "Inside Rail"
        ],
        index=0
    )

    apply_bias = st.checkbox(
        "Apply track bias adjustments",
        value=False,
        key="apply_track_bias"
    )

    if apply_bias:

        df = apply_track_bias(
            df,
            selected_bias
        )

        st.success(
            f"{selected_bias} applied successfully ✅"
        )
# Apply Version 2.3 clean-template scoring
df = apply_v23_template_scoring(df)

# Make sure all dashboard display columns exist
df = ensure_app_columns(df)

# -----------------------------
# SEARCH + FILTERS
# -----------------------------
search = st.text_input(
    "Search Horse",
    key="horse_search"
)

overlay_only = st.checkbox(
    "Show Overlays Only",
    key="overlay_filter"
)


if search:

    df = df[
        df["Horse"].str.contains(search, case=False, na=False)
    ]


if overlay_only:

    df = df[
        df["Overlay"] == True
    ]


if df.empty:

    st.warning(
        "No runners found. Try changing the search or turning off overlay filter."
    )

    st.stop()


# -----------------------------
# COLOUR ROWS
# -----------------------------
def colour_rows(row):

    if row["Overlay"]:

        return ["background-color: lightgreen"] * len(row)

    else:

        return ["background-color: #ffcccc"] * len(row)


# -----------------------------
# DISPLAY TABLE
# -----------------------------
styled_df = df.style.apply(
    colour_rows,
    axis=1
)

st.dataframe(styled_df)
with st.expander("Version 2.6 Live Market Steam Detection 📈"):

    st.write("Tracks market moves (steamers/drifters) and false favourites.")

    steam_columns = [
        "Horse",
        "Previous Odds",
        "Current Odds",
        "Odds Change",
        "Odds Change %",
        "Market Move",
        "Steam Signal",
        "Rating",
        "Fair Odds",
        "Market Odds",
        "Overlay",
        "Overlay %",
        "Bet Call"
    ]

    steam_view = safe_view(df, steam_columns).sort_values(
        by="Odds Change %",
        ascending=True
    )

    st.dataframe(steam_view, use_container_width=True)

    false_favs_df = detect_false_favourites(df)
    
    if not false_favs_df.empty:
        st.warning("⚠️ False Favourite Alert")
        st.dataframe(
            false_favs_df[
                ["Horse", "Market Odds", "Fair Odds", "Confidence", "Bet Call", "False Favourite Flag"]
            ],
            use_container_width=True
        )
# -----------------------------
# CLEAN TABBED DASHBOARD
# -----------------------------
st.subheader("Race Dashboard Tabs 🧭")

overview_tab, ratings_tab, overlays_tab, execution_tab, downloads_tab = st.tabs(
    [
        "Overview 🏠",
        "Race Ratings 🐎",
        "Value / Overlays 💰",
        "Win Execution 🧠",
        "Downloads 📥"
    ]
)
with overview_tab:

    st.subheader("Overview 🏠")

    overview_col1, overview_col2, overview_col3, overview_col4, overview_col5 = st.columns(5)

    overlay_count = len(df[df["Overlay"] == True])

    market_percentage = round(
        (
            100 / pd.to_numeric(
                df["Market Odds"],
                errors="coerce"
            ).replace(0, pd.NA)
        ).sum(),
        2
    )

    top_pick_preview = df.sort_values(
        by="Rating",
        ascending=False
    ).iloc[0]

    leader_count = len(
        df[
            df["Map Position"].isin(
                ["Lead", "On-speed"]
            )
        ]
    )

    backmarker_count = len(
        df[
            df["Map Position"].isin(
                ["Back", "Wide"]
            )
        ]
    )

    if leader_count >= 4:

        race_shape = "High Pressure"

    elif leader_count <= 1:

        race_shape = "Leader Favoured"

    else:

        race_shape = "Balanced Tempo"

    with overview_col1:
        st.metric("Top Pick", top_pick_preview["Horse"])

    with overview_col2:
        st.metric("Top Rating", top_pick_preview["Rating"])

    with overview_col3:
        st.metric("Market %", f"{market_percentage}%")

    with overview_col4:
        st.metric("Overlay Count", overlay_count)

    with overview_col5:
        st.metric("Race Shape", race_shape)

    st.write("### Quick Race Read")

    if top_pick_preview["Confidence"] >= 9 and top_pick_preview["Win Execution"] >= 8:

        st.success(
            "Strong race profile ✅ The top pick has both a strong rating and strong win execution."
        )

    elif overlay_count >= 2:

        st.info(
            "This race has multiple overlay chances 💰 The market may have missed something."
        )

    elif market_percentage >= 120:

        st.warning(
            "High market percentage ⚠️ Be careful forcing a bet in a high-overround market."
        )

    else:

        st.info(
            "Moderate race profile. Treat this as a watch race unless price is attractive."
        )
st.write("### Track Bias")

if apply_bias:

    st.info(
        f"Current Bias Profile: {selected_bias}"
    )

else:

    st.info(
        "No track bias currently applied."
    )
    st.write("### Map Shape")

    if leader_count >= 4:

        st.error(
            "🔥 HOT SPEED: Expect pressure on leaders and possible setup for closers."
        )

    elif leader_count == 3:

        st.warning(
            "⚠️ Genuine tempo likely."
        )

    elif leader_count <= 1:

        st.success(
            "🐎 SOFT LEAD possible — major advantage to on-speed runners."
        )

    else:

        st.info(
            "Balanced race tempo profile."
        )

    if backmarker_count >= 4:

        st.info(
            "Multiple backmarkers engaged — watch for tempo collapse late."
        )
with ratings_tab:

    st.subheader("Race Ratings 🐎")

    ratings_columns = [
        "Horse",
        "Rating",
        "Confidence",
        "Win Execution",
        "Fair Odds",
        "Market Odds",
        "Odds Source",
        "Overlay",
        "Overlay %",
        "Bet Call",
        "Model Notes"
    ]

    ratings_view = safe_view(
        df,
        ratings_columns
    ).sort_values(
        by="Rating",
        ascending=False
    )

    st.dataframe(
        ratings_view,
        use_container_width=True
    )

    st.write("### Top 4 Rated")

    top_4_tab = ratings_view.head(4).reset_index(drop=True)

    top_cols = st.columns(4)

    for i, col in enumerate(top_cols):

        if i < len(top_4_tab):

            runner = top_4_tab.iloc[i]

            with col:

                st.metric(f"#{i + 1}", runner["Horse"])
                st.write(f"Rating: {runner['Rating']}")
                st.write(f"Confidence: {runner['Confidence']}/10")
                st.write(f"Win Execution: {runner['Win Execution']}/10")
                st.write(f"Call: {runner['Bet Call']}")
                st.write(runner["Model Notes"])
# -----------------------------
# OVERLAY SUMMARY VARIABLES
# -----------------------------
overlay_df = df[df["Overlay"] == True].copy()

if len(overlay_df) > 0:

    best_overlay = overlay_df.sort_values(
        by="Overlay %",
        ascending=False
    ).iloc[0]

else:

    best_overlay = {
        "Horse": "No Overlay",
        "Overlay %": 0
    }
with overlays_tab:

    st.subheader("Value / Overlays 💰")

    overlay_df = df[df["Overlay"] == True].sort_values(
        by="Overlay %",
        ascending=False
    )

    overlay_columns = [
        "Horse",
        "Rating",
        "Fair Odds",
        "Market Odds",
        "Odds Source",
        "Overlay %",
        "Confidence",
        "Win Execution",
        "Bet Call",
        "Model Notes"
    ]

    if overlay_df.empty:

        st.warning("No overlays found in this race.")

    else:

        st.success(f"{len(overlay_df)} overlay runner(s) found ✅")

        st.dataframe(
            safe_view(
                overlay_df,
                overlay_columns
            ),
            use_container_width=True
        )

        st.metric("Best Overlay", best_overlay["Horse"])
        st.write(f"Best Overlay Price Gap: {best_overlay['Overlay %']}%")
# -----------------------------
# WIN EXECUTION SUMMARY VARIABLE
# -----------------------------
execution_df = df.copy()

if len(execution_df) > 0:

    best_execution = execution_df.sort_values(
        by="Win Execution",
        ascending=False
    ).iloc[0]

else:

    best_execution = {
        "Horse": "No Runner"
    }
with execution_tab:

    st.subheader("Win Execution 🧠")

    execution_columns = [
        "Horse",
        "Rating",
        "Confidence",
        "Win Execution",
        "Fair Odds",
        "Market Odds",
        "Overlay",
        "Bet Call",
        "Model Notes"
    ]

    execution_view = safe_view(
        df,
        execution_columns
    ).sort_values(
        by="Win Execution",
        ascending=False
    )

    st.dataframe(
        execution_view,
        use_container_width=True
    )

    st.metric("Best Win Execution", best_execution["Horse"])

    st.write(
        "Win Execution estimates how cleanly a runner can actually win. "
        "This early version uses market confidence, barrier/gate risk, weight carried, "
        "and overlay status where available."
    )

with downloads_tab:

    st.subheader("Downloads 📥")

    tab_csv_output = df.to_csv(index=False)

    st.download_button(
        label="Download Current Analysed Race CSV",
        data=tab_csv_output,
        file_name="current_analysed_race.csv",
        mime="text/csv",
        key="tab_download_current_race"
    )

    if st.button("Save Current Analysed Race to Database", key="tab_save_current_race"):

        conn = sqlite3.connect("database/racing.db")

        safe_table_name = race.lower().replace(" ", "_")

        df.to_sql(
            f"analysed_{safe_table_name}",
            conn,
            if_exists="replace",
            index=False
        )

        conn.close()

        st.success("Current analysed race saved to database ✅")
# -----------------------------
# MODEL SETTINGS DISPLAY
# -----------------------------
with st.expander("Current Model Settings 🧠"):

    st.write("These are the current weights being used by the automatic rating model.")

    weights_df = pd.DataFrame(
        {
            "Factor": [
                "Market",
                "Barrier",
                "Weight Carried",
                "Jockey",
                "Trainer",
                "File Order / Fallback"
            ],
            "Weight": [
                model_weights["market"],
                model_weights["barrier"],
                model_weights["weight"],
                model_weights["jockey"],
                model_weights["trainer"],
                model_weights["position"]
            ]
        }
    )

    st.dataframe(weights_df)
# -----------------------------
# VERSION 2 CONTEXT DISPLAY
# -----------------------------
with st.expander("Version 2 Race Context 🧠"):

    st.write("These race-level settings are now being applied to the model.")

    context_df = pd.DataFrame(
        [
            {
                "Track Condition": race_context["track_condition"],
                "Distance": race_context["distance"],
                "Race Pressure": race_context["race_pressure"]
            }
        ]
    )

    st.dataframe(context_df)

    v2_view = df[
        [
            "Horse",
            "Rating",
            "V2 Adjustment",
            "Race Context",
            "Win Execution",
            "Bet Call",
            "Model Notes"
        ]
    ].sort_values(
        by="Rating",
        ascending=False
    )

    st.dataframe(v2_view)

# -----------------------------
# WIN EXECUTION EXPLAINER
# -----------------------------
with st.expander("Win Execution Score 🧠"):

    st.write(
        "This score estimates how cleanly a runner can actually win. "
        "It currently uses market confidence, barrier/gate risk, weight carried, "
        "and overlay status where those columns are available."
    )

    execution_df = df[
        [
            "Horse",
            "Rating",
            "Confidence",
            "Win Execution",
            "Fair Odds",
            "Market Odds",
            "Overlay"
        ]
    ].sort_values(
        by="Win Execution",
        ascending=False
    )

    st.dataframe(execution_df)


# -----------------------------
# DASHBOARD STATS
# -----------------------------
overlay_count = len(
    df[df["Overlay"] == True]
)

market_percentage = round(
    (100 / df["Market Odds"]).sum(),
    2
)

best_overlay = df.sort_values(
    by="Overlay %",
    ascending=False
).iloc[0]

best_execution = df.sort_values(
    by="Win Execution",
    ascending=False
).iloc[0]


col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Overlay Count",
        overlay_count
    )

with col2:

    st.metric(
        "Market %",
        f"{market_percentage}%"
    )

with col3:

    st.metric(
        "Best Overlay",
        best_overlay["Horse"]
    )

with col4:

    st.metric(
        "Best Execution",
        best_execution["Horse"]
    )


# -----------------------------
# BIG OVERLAY ALERT
# -----------------------------
if best_overlay["Overlay %"] >= 20:

    st.success(
        f"🔥 BIG OVERLAY FOUND: {best_overlay['Horse']} at {best_overlay['Market Odds']}"
    )

else:

    st.info(
        "No major overlay above 20% in this race."
    )


## -----------------------------
# TOP 4 SELECTIONS
# -----------------------------
st.subheader("Top 4 Selections 🏆")

top_4 = df.head(4).reset_index(drop=True)

selection_cols = st.columns(4)

for i, col in enumerate(selection_cols):

    if i < len(top_4):

        runner = top_4.iloc[i]

        with col:

            st.metric(
                label=f"#{i + 1}",
                value=runner["Horse"]
            )

            st.write(f"Rating: {runner['Rating']}")
            st.write(f"Fair Odds: {runner['Fair Odds']}")
            st.write(f"Market Odds: {runner['Market Odds']}")
            st.write(f"Confidence: {runner['Confidence']}/10")
            st.write(f"Win Execution: {runner['Win Execution']}/10")

            if "Bet Call" in runner:
                st.write(f"Call: {runner['Bet Call']}")

            if "Model Notes" in runner:
                st.write(runner["Model Notes"])

            if runner["Overlay"]:

                st.success("Overlay ✅")

            else:

                st.error("No Overlay ❌")
# -----------------------------
# RACE SUMMARY
# -----------------------------
st.subheader("Race Summary 📝")

top_pick_preview = df.iloc[0]

if overlay_count >= 2:

    race_summary = "This race has multiple overlay chances. The model sees possible market weakness."

elif top_pick_preview["Rating"] >= 90:

    race_summary = "The model has found a clear top-rated runner with strong win confidence."

elif market_percentage >= 120:

    race_summary = "This market looks high-overround or potentially compressed. Be careful forcing a bet."

else:

    race_summary = "This race looks moderate. Use the Top Pick and Value Pick carefully."

st.write(race_summary)


# -----------------------------
# BET / NO BET WARNING
# -----------------------------
st.subheader("Bet / No Bet Read 🚦")

if top_pick_preview["Confidence"] >= 9 and top_pick_preview["Win Execution"] >= 8:

    st.success("BET RACE ✅ Strong rating and strong win execution profile.")

elif top_pick_preview["Confidence"] >= 8 and top_pick_preview["Win Execution"] >= 7:

    st.info("WATCH / POSSIBLE BET 👀 Strong top pick, but check price and map carefully.")

elif overlay_count >= 1 and best_overlay["Overlay %"] >= 20:

    st.info("VALUE WATCH 💰 There is an overlay, but win execution still needs checking.")

else:

    st.warning("NO BET LEAN ❌ Confidence or win execution is not strong enough yet.")


# -----------------------------
# DOWNLOAD ANALYSED RACE
# -----------------------------
csv_output = df.to_csv(index=False)

st.download_button(
    label="Download Analysed Race CSV",
    data=csv_output,
    file_name="analysed_race.csv",
    mime="text/csv"
)


# -----------------------------
# SAVE ANALYSED RACE TO DATABASE
# -----------------------------
if st.button("Save Analysed Race to Database"):

    conn = sqlite3.connect("database/racing.db")

    safe_table_name = race.lower().replace(" ", "_")

    df.to_sql(
        f"analysed_{safe_table_name}",
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()

    st.success("Analysed race saved to database ✅")


# -----------------------------
# VIEW SAVED ANALYSED RACES
# -----------------------------
st.subheader("Saved Analysed Races 🗄️")

try:

    conn = sqlite3.connect("database/racing.db")

    saved_tables = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'analysed_%'",
        conn
    )

    if saved_tables.empty:

        st.info("No analysed races saved yet.")

    else:

        saved_race_table = st.selectbox(
            "Choose a saved analysed race",
            saved_tables["name"].tolist(),
            key="saved_race_selector"
        )

        saved_df = pd.read_sql(
            f"SELECT * FROM {saved_race_table}",
            conn
        )

        st.dataframe(saved_df)

        saved_csv = saved_df.to_csv(index=False)

        st.download_button(
            label="Download Saved Race CSV",
            data=saved_csv,
            file_name=f"{saved_race_table}.csv",
            mime="text/csv",
            key="download_saved_race"
        )

    conn.close()

except Exception as error:

    st.warning("Could not load saved analysed races yet.")

    st.write(error)


# -----------------------------
# SIDEBAR STATS
# -----------------------------
st.sidebar.metric(
    "Overlays",
    overlay_count
)

st.sidebar.metric(
    "Market %",
    f"{market_percentage}%"
)


# -----------------------------
# TOP PICK
# -----------------------------
top_pick = df.iloc[0]


# -----------------------------
# VALUE PICK
# -----------------------------
value_rows = df[
    df["Overlay"] == True
]

if len(value_rows) > 0:

    value_pick = value_rows.iloc[0]["Horse"]

else:

    value_pick = "None"


# -----------------------------
# FINAL CALL
# -----------------------------
# -----------------------------
# BET LOGGER + RESULTS TRACKER
# -----------------------------
st.subheader("Bet Logger + Results Tracker 📈")

results_file = "results.csv"

results_columns = [
    "Date",
    "Race",
    "Horse",
    "Bet Type",
    "Stake",
    "Odds",
    "Result",
    "Profit"
]

# Create results.csv if it does not exist
if not os.path.exists(results_file):

    empty_results = pd.DataFrame(
        columns=results_columns
    )

    empty_results.to_csv(
        results_file,
        index=False
    )


# Load existing results
results_df = pd.read_csv(results_file)


# BET ENTRY FORM
with st.form("bet_logger_form"):

    st.write("Add a new bet/result")

    bet_col1, bet_col2 = st.columns(2)

    with bet_col1:

        bet_date = st.text_input(
            "Date",
            value=datetime.now().strftime("%Y-%m-%d")
        )

        bet_race = st.text_input(
            "Race",
            value=race
        )

        bet_horse = st.text_input(
            "Horse"
        )

        bet_type = st.selectbox(
            "Bet Type",
            [
                "Win",
                "Place",
                "Each-Way",
                "No Bet",
                "Watch Only"
            ]
        )

    with bet_col2:

        bet_stake = st.number_input(
            "Stake / Units",
            min_value=0.0,
            value=1.0,
            step=0.25
        )

        bet_odds = st.number_input(
            "Odds",
            min_value=0.0,
            value=1.0,
            step=0.10
        )

        bet_result = st.selectbox(
            "Result",
            [
                "Pending",
                "Win",
                "Lose",
                "Place"
            ]
        )

        bet_profit = st.number_input(
            "Profit / Loss",
            value=0.0,
            step=0.25
        )

    submitted_bet = st.form_submit_button(
        "Save Bet"
    )


if submitted_bet:

    if bet_horse.strip() == "":

        st.warning("Please enter a horse name before saving.")

    else:

        new_bet = pd.DataFrame(
            [
                {
                    "Date": bet_date,
                    "Race": bet_race,
                    "Horse": bet_horse,
                    "Bet Type": bet_type,
                    "Stake": bet_stake,
                    "Odds": bet_odds,
                    "Result": bet_result,
                    "Profit": bet_profit
                }
            ]
        )

        results_df = pd.concat(
            [
                results_df,
                new_bet
            ],
            ignore_index=True
        )

        results_df.to_csv(
            results_file,
            index=False
        )

        st.success("Bet saved to results tracker ✅")


# RELOAD RESULTS AFTER SAVE
results_df = pd.read_csv(results_file)


# CLEAN NUMBER COLUMNS
if not results_df.empty:

    results_df["Stake"] = pd.to_numeric(
        results_df["Stake"],
        errors="coerce"
    ).fillna(0)

    results_df["Odds"] = pd.to_numeric(
        results_df["Odds"],
        errors="coerce"
    ).fillna(0)

    results_df["Profit"] = pd.to_numeric(
        results_df["Profit"],
        errors="coerce"
    ).fillna(0)


# DISPLAY RESULTS
st.write("### Saved Betting Results")

if results_df.empty:

    st.info("No bets saved yet.")

else:

    st.dataframe(results_df)

    total_profit = results_df["Profit"].sum()

    total_staked = results_df["Stake"].sum()

    if total_staked > 0:

        roi = round(
            (total_profit / total_staked) * 100,
            2
        )

    else:

        roi = 0

    result_col1, result_col2, result_col3, result_col4 = st.columns(4)

    with result_col1:

        st.metric(
            "Total Profit",
            f"{round(total_profit, 2)} units"
        )

    with result_col2:

        st.metric(
            "Total Staked",
            f"{round(total_staked, 2)} units"
        )

    with result_col3:

        st.metric(
            "ROI",
            f"{roi}%"
        )

    with result_col4:

        st.metric(
            "Bets Logged",
            len(results_df)
        )

    if total_profit > 0:

        st.success("Current results are profitable ✅")

    elif total_profit == 0:

        st.info("Results are break-even so far.")

    else:

        st.error("Current results are negative ❌")


# DOWNLOAD RESULTS
results_csv = results_df.to_csv(index=False)

st.download_button(
    label="Download Results CSV",
    data=results_csv,
    file_name="results.csv",
    mime="text/csv",
    key="download_results_csv"
)
