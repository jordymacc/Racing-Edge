import os
import sqlite3
import joblib
import pandas as pd
import numpy as np
from engines.bullet_price_v2 import calculate_bullet_price_v2
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(__file__).resolve().parent / "winner_predictor_v4.pkl"
DB_PATH = BASE_DIR / "database" / "racing.db"
DATABASE_URL = os.environ.get("DATABASE_URL")

FEATURES = [
    "win_odds_racingcom", "implied_prob", "is_favorite", "market_rank",
    "jockey_win_rate", "trainer_win_rate", "combined_form",
    "jockey_odds_interaction", "trainer_odds_interaction",
    "track_condition_score", "is_good", "is_soft", "is_heavy", "is_synth",
    "temperature", "rainfall", "wet_track", "temp_normalized"
]

def fetch_all_data():
    """Fetch ALL recent odds + jockey/trainer stats in 3 queries total"""
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # All recent odds in one query
        cur.execute("""
            SELECT race_name, horse_name, jockey_name, trainer_name,
                   win_odds_racingcom, timestamp,
                   track_condition, track_condition_score,
                   temperature, rainfall
            FROM odds_snapshots
            WHERE timestamp::timestamp > NOW() - INTERVAL '3 hours'
            AND win_odds_racingcom IS NOT NULL
            ORDER BY race_name, horse_name, timestamp
        """)
        cols = [d[0] for d in cur.description]
        odds_df = pd.DataFrame(cur.fetchall(), columns=cols)

        # All jockey stats
        cur.execute("SELECT jockey_name, win_rate FROM jockey_stats")
        jockey_df = pd.DataFrame(cur.fetchall(), columns=["jockey_name", "win_rate"])

        # All trainer stats
        cur.execute("SELECT trainer_name, win_rate FROM trainer_stats")
        trainer_df = pd.DataFrame(cur.fetchall(), columns=["trainer_name", "win_rate"])

        conn.close()
    else:
        conn = sqlite3.connect(str(DB_PATH))
        odds_df = pd.read_sql_query("""
            SELECT race_name, horse_name, jockey_name, trainer_name,
                   win_odds_racingcom, timestamp,
                   track_condition, track_condition_score,
                   temperature, rainfall
            FROM odds_snapshots
            WHERE timestamp > datetime('now', '-3 hours')
            AND win_odds_racingcom IS NOT NULL
            ORDER BY race_name, horse_name, timestamp
        """, conn)
        jockey_df = pd.read_sql_query("SELECT jockey_name, win_rate FROM jockey_stats", conn)
        trainer_df = pd.read_sql_query("SELECT trainer_name, win_rate FROM trainer_stats", conn)
        conn.close()

    return odds_df, jockey_df, trainer_df

def build_features(odds_df, jockey_df, trainer_df):
    """Build features for all horses in one pass"""
    if odds_df.empty:
        return None

    # Merge jockey/trainer stats
    odds_df = odds_df.merge(jockey_df.rename(columns={"win_rate": "jockey_win_rate"}),
                            on="jockey_name", how="left")
    odds_df = odds_df.merge(trainer_df.rename(columns={"win_rate": "trainer_win_rate"}),
                            on="trainer_name", how="left")
    odds_df["jockey_win_rate"] = odds_df["jockey_win_rate"].fillna(0)
    odds_df["trainer_win_rate"] = odds_df["trainer_win_rate"].fillna(0)

    features = []
    for race_name, race_df in odds_df.groupby("race_name"):
        # Get track/weather from latest snapshot
        latest = race_df.sort_values("timestamp").iloc[-1]
        track_condition  = latest.get("track_condition")
        track_cond_score = float(latest.get("track_condition_score") or 2.0)
        temperature      = float(latest.get("temperature") or 20.0)
        rainfall         = float(latest.get("rainfall") or 0.0)

        is_good  = 1 if track_condition == "Good"  else 0
        is_soft  = 1 if track_condition == "Soft"  else 0
        is_heavy = 1 if track_condition == "Heavy" else 0
        is_synth = 1 if track_condition == "Synth" else 0
        wet_track = 1 if (track_cond_score >= 3 or rainfall > 0) else 0
        temp_normalized = (temperature - 20.0) / 10.0

        # Get latest odds per horse
        horse_latest = race_df.sort_values("timestamp").groupby("horse_name").last().reset_index()
        horse_first  = race_df.sort_values("timestamp").groupby("horse_name").first().reset_index()

        min_odds_val = float(horse_latest["win_odds_racingcom"].min())

        for _, horse in horse_latest.iterrows():
            name         = horse["horse_name"]
            current_odds = float(horse["win_odds_racingcom"])
            opening_row  = horse_first[horse_first["horse_name"] == name]
            opening_odds = float(opening_row["win_odds_racingcom"].iloc[0]) if len(opening_row) > 0 else current_odds
            num_updates  = len(race_df[race_df["horse_name"] == name])
            horse_odds   = race_df[race_df["horse_name"] == name]["win_odds_racingcom"].astype(float)

            mean_odds    = float(horse_odds.mean())
            min_odds     = float(horse_odds.min())
            max_odds     = float(horse_odds.max())
            volatility   = float(horse_odds.std() / mean_odds) if mean_odds > 0 and num_updates > 1 else 0
            odds_change_pct = ((opening_odds - current_odds) / opening_odds * 100) if opening_odds > 0 else 0
            implied_prob = 1 / current_odds if current_odds > 0 else 0
            is_favorite  = 1 if current_odds == min_odds_val else 0
            market_rank  = int((horse_latest["win_odds_racingcom"].astype(float) <= current_odds).sum())

            jockey_wr  = float(horse.get("jockey_win_rate") or 0)
            trainer_wr = float(horse.get("trainer_win_rate") or 0)

            features.append({
                "race_name": race_name,
                "horse_name": name,
                "jockey_name": horse.get("jockey_name"),
                "trainer_name": horse.get("trainer_name"),
                "current_odds": current_odds,
                "win_odds_racingcom": current_odds,
                "opening_odds": opening_odds,
                "odds_change_pct": odds_change_pct,
                "mean_odds": mean_odds,
                "min_odds": min_odds,
                "max_odds": max_odds,
                "volatility": volatility,
                "market_rank": market_rank,
                "is_favorite": is_favorite,
                "num_updates": num_updates,
                "implied_prob": implied_prob,
                "jockey_win_rate": jockey_wr,
                "trainer_win_rate": trainer_wr,
                "combined_form": (jockey_wr + trainer_wr) / 2,
                "jockey_odds_interaction": jockey_wr * implied_prob,
                "trainer_odds_interaction": trainer_wr * implied_prob,
                "track_condition": track_condition,
                "track_condition_score": track_cond_score,
                "is_good": is_good,
                "is_soft": is_soft,
                "is_heavy": is_heavy,
                "is_synth": is_synth,
                "temperature": temperature,
                "rainfall": rainfall,
                "wet_track": wet_track,
                "temp_normalized": temp_normalized,
            })

    return pd.DataFrame(features)

def get_ml_predictions_for_dashboard():
    try:
        model_data = joblib.load(MODEL_PATH)
        model = model_data["model"]

        print("  Fetching data...")
        odds_df, jockey_df, trainer_df = fetch_all_data()
        print(f"  {len(odds_df)} odds rows, {len(odds_df['race_name'].unique())} races")

        df = build_features(odds_df, jockey_df, trainer_df)
df = calculate_bullet_price_v2(df)
        if df is None or df.empty:
            return None

        X = df[FEATURES].fillna(0)
        df["predicted_win_prob"] = model.predict_proba(X)[:, 1]
        df["confidence"] = df["predicted_win_prob"].apply(
            lambda x: "HIGH" if x > 0.3 else "MEDIUM" if x > 0.15 else "LOW"
        )
        print(f"  Done! {len(df)} predictions")
        return df

    except Exception as e:
        print(f"ML Prediction Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_top_picks(n=5):
    predictions = get_ml_predictions_for_dashboard()
    if predictions is None:
        return None
    return predictions.nlargest(n, "predicted_win_prob")[
        ["race_name", "horse_name", "current_odds", "predicted_win_prob", "is_favorite", "confidence"]
    ]

def extract_features_for_race(race_name, engine=None):
    """Single race features for Race Viewer"""
    odds_df, jockey_df, trainer_df = fetch_all_data()
    odds_df = odds_df[odds_df["race_name"] == race_name]
    if odds_df.empty:
        return None
    result = build_features(odds_df, jockey_df, trainer_df)
    return result
