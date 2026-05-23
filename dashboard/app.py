import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

import os
import sys
import streamlit as st
from engines.race_intelligence_engine import run_race_intelligence
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from theme import inject_css


# Define BASE_DIR first (before we use it)
BASE_DIR = Path(__file__).resolve().parent.parent

# Now we can use BASE_DIR in imports
import sys

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
    predictions = dashboard_predictions.get_ml_predictions_for_dashboard()
    predictions = run_race_intelligence(predictions)

    if predictions is not None and len(predictions) > 0:
        st.subheader("🏆 Top ML Picks")
        top_picks = predictions.nlargest(5, 'predicted_win_prob')

except Exception as e:
    st.error(f"ML Error: {e}")

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
inject_css()

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
    