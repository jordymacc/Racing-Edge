import os
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_df(query, params=None):
    """Run a query and return a DataFrame"""
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(query, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    else:
        conn = sqlite3.connect(str(DB_PATH))
        result = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return result

def get_jockey_win_rate(jockey_name):
    if not jockey_name:
        return 0.0
    try:
        ph = "%s" if DATABASE_URL else "?"
        df = get_df(f"SELECT win_rate FROM jockey_stats WHERE jockey_name = {ph}", (jockey_name,))
        return float(df.iloc[0]["win_rate"]) if len(df) > 0 else 0.0
    except:
        return 0.0

def get_trainer_win_rate(trainer_name):
    if not trainer_name:
        return 0.0
    try:
        ph = "%s" if DATABASE_URL else "?"
        df = get_df(f"SELECT win_rate FROM trainer_stats WHERE trainer_name = {ph}", (trainer_name,))
        return float(df.iloc[0]["win_rate"]) if len(df) > 0 else 0.0
    except:
        return 0.0

def extract_features_for_race(race_name, engine=None):
    ph = "%s" if DATABASE_URL else "?"
    query = f"""
        SELECT horse_name, jockey_name, trainer_name,
               win_odds_racingcom, timestamp,
               track_condition, track_condition_score,
               temperature, rainfall
        FROM odds_snapshots
        WHERE race_name = {ph}
        AND win_odds_racingcom IS NOT NULL
        ORDER BY horse_name, timestamp
    """
    df = get_df(query, (race_name,))

    if df.empty:
        return None

    latest = df.sort_values("timestamp").iloc[-1]
    track_condition   = latest.get("track_condition", None)
    track_cond_score  = float(latest.get("track_condition_score") or 2.0)
    temperature       = latest.get("temperature", None)
    rainfall          = float(latest.get("rainfall") or 0.0)

    is_good  = 1 if track_condition == "Good"  else 0
    is_soft  = 1 if track_condition == "Soft"  else 0
    is_heavy = 1 if track_condition == "Heavy" else 0
    is_synth = 1 if track_condition == "Synth" else 0
    wet_track = 1 if (track_cond_score >= 3 or rainfall > 0) else 0
    temp_val = float(temperature) if temperature is not None else 20.0
    temp_normalized = (temp_val - 20.0) / 10.0

    features = []
    for horse in df["horse_name"].unique():
        horse_df = df[df["horse_name"] == horse].copy().sort_values("timestamp")
        jockey_name  = horse_df["jockey_name"].iloc[-1]
        trainer_name = horse_df["trainer_name"].iloc[-1]
        jockey_win_rate  = get_jockey_win_rate(jockey_name)
        trainer_win_rate = get_trainer_win_rate(trainer_name)
        current_odds = float(horse_df["win_odds_racingcom"].iloc[-1])

        if len(horse_df) >= 2:
            opening_odds    = float(horse_df["win_odds_racingcom"].iloc[0])
            odds_change_pct = ((opening_odds - current_odds) / opening_odds * 100) if opening_odds > 0 else 0
            mean_odds  = float(horse_df["win_odds_racingcom"].mean())
            min_odds   = float(horse_df["win_odds_racingcom"].min())
            max_odds   = float(horse_df["win_odds_racingcom"].max())
            volatility = float(horse_df["win_odds_racingcom"].std()) / mean_odds if mean_odds > 0 else 0
        else:
            opening_odds = current_odds
            odds_change_pct = 0
            mean_odds = min_odds = max_odds = current_odds
            volatility = 0

        all_current_odds = df.groupby("horse_name")["win_odds_racingcom"].last()
        market_rank  = int((all_current_odds <= current_odds).sum())
        is_favorite  = 1 if current_odds == float(all_current_odds.min()) else 0
        implied_prob = 1 / current_odds if current_odds > 0 else 0

        features.append({
            "race_name": race_name,
            "horse_name": horse,
            "jockey_name": jockey_name,
            "trainer_name": trainer_name,
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
            "num_updates": len(horse_df),
            "implied_prob": implied_prob,
            "jockey_win_rate": jockey_win_rate,
            "trainer_win_rate": trainer_win_rate,
            "combined_form": (jockey_win_rate + trainer_win_rate) / 2,
            "jockey_odds_interaction": jockey_win_rate * implied_prob,
            "trainer_odds_interaction": trainer_win_rate * implied_prob,
            "track_condition": track_condition,
            "track_condition_score": track_cond_score,
            "is_good": is_good,
            "is_soft": is_soft,
            "is_heavy": is_heavy,
            "is_synth": is_synth,
            "temperature": temp_val,
            "rainfall": rainfall,
            "wet_track": wet_track,
            "temp_normalized": temp_normalized,
        })

    return pd.DataFrame(features)

# ========================
# KINGSLEY INTEGRATION
# ========================

from kingsley_ratings import add_kingsley_analysis

def analyse_race_with_kingsley(df, race_context=None, speed_map_df=None, bias_profile="Neutral"):
    """
    Your original analyse_race() but now with full Kingsley layer added.
    """
    df = df.copy()
    
    # Run your existing pipeline first
    df = analyse_race(df)                    # Your current function
    
    if speed_map_df is not None:
        df = apply_manual_speed_map(df, speed_map_df)
    
    if bias_profile != "Neutral":
        df = apply_track_bias(df, bias_profile)
    
    if race_context:
        df = apply_v2_context_adjustments(df, race_context)
    
    df = apply_v23_template_scoring(df)
    
    # === ADD KINGSLEY ON TOP ===
    df = add_kingsley_analysis(df)
    
    # Final sort using combined logic
    df = df.sort_values(by=['Kingsley_Score', 'Rating'], ascending=False)
    
    return df
