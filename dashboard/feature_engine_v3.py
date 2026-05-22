import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

def get_jockey_win_rate(jockey_name, conn):
    if not jockey_name:
        return 0.0
    cursor = conn.cursor()
    cursor.execute("SELECT win_rate FROM jockey_stats WHERE jockey_name = ?", (jockey_name,))
    result = cursor.fetchone()
    return float(result[0]) if result else 0.0

def get_trainer_win_rate(trainer_name, conn):
    if not trainer_name:
        return 0.0
    cursor = conn.cursor()
    cursor.execute("SELECT win_rate FROM trainer_stats WHERE trainer_name = ?", (trainer_name,))
    result = cursor.fetchone()
    return float(result[0]) if result else 0.0

def extract_features_for_race(race_name):
    """Extract ML features INCLUDING jockey/trainer/track/weather"""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT 
            horse_name, jockey_name, trainer_name,
            win_odds_racingcom, timestamp,
            track_condition, track_condition_score,
            temperature, rainfall
        FROM odds_snapshots
        WHERE race_name = ?
        AND win_odds_racingcom IS NOT NULL
        ORDER BY horse_name, timestamp
    """
    df = pd.read_sql_query(query, conn, params=(race_name,))

    if df.empty:
        conn.close()
        return None

    # Get track/weather from most recent snapshot for this race
    latest = df.sort_values('timestamp').iloc[-1]
    track_condition    = latest.get('track_condition', None)
    track_cond_score   = latest.get('track_condition_score', 2.0) or 2.0
    temperature        = latest.get('temperature', None)
    rainfall           = latest.get('rainfall', 0.0) or 0.0

    # Encode track condition
    is_good  = 1 if track_condition == 'Good'  else 0
    is_soft  = 1 if track_condition == 'Soft'  else 0
    is_heavy = 1 if track_condition == 'Heavy' else 0
    is_synth = 1 if track_condition == 'Synth' else 0
    wet_track = 1 if (track_cond_score >= 3 or rainfall > 0) else 0

    # Normalise temperature (use 20 as default if missing)
    temp_val = float(temperature) if temperature is not None else 20.0
    temp_normalized = (temp_val - 20.0) / 10.0

    features = []

    for horse in df['horse_name'].unique():
        horse_df = df[df['horse_name'] == horse].copy().sort_values('timestamp')

        jockey_name  = horse_df['jockey_name'].iloc[-1]
        trainer_name = horse_df['trainer_name'].iloc[-1]
        jockey_win_rate  = get_jockey_win_rate(jockey_name, conn)
        trainer_win_rate = get_trainer_win_rate(trainer_name, conn)

        current_odds = horse_df['win_odds_racingcom'].iloc[-1]

        if len(horse_df) >= 2:
            opening_odds    = horse_df['win_odds_racingcom'].iloc[0]
            odds_change_pct = ((opening_odds - current_odds) / opening_odds * 100) if opening_odds > 0 else 0
            mean_odds  = horse_df['win_odds_racingcom'].mean()
            min_odds   = horse_df['win_odds_racingcom'].min()
            max_odds   = horse_df['win_odds_racingcom'].max()
            volatility = horse_df['win_odds_racingcom'].std() / mean_odds if mean_odds > 0 else 0
        else:
            opening_odds = current_odds
            odds_change_pct = 0
            mean_odds = min_odds = max_odds = current_odds
            volatility = 0

        all_current_odds = df.groupby('horse_name')['win_odds_racingcom'].last()
        market_rank  = (all_current_odds <= current_odds).sum()
        is_favorite  = 1 if current_odds == all_current_odds.min() else 0
        implied_prob = 1 / current_odds if current_odds > 0 else 0

        features.append({
            'race_name': race_name,
            'horse_name': horse,
            'jockey_name': jockey_name,
            'trainer_name': trainer_name,
            # Odds
            'current_odds': current_odds,
            'win_odds_racingcom': current_odds,
            'opening_odds': opening_odds,
            'odds_change_pct': odds_change_pct,
            'mean_odds': mean_odds,
            'min_odds': min_odds,
            'max_odds': max_odds,
            'volatility': volatility,
            'market_rank': market_rank,
            'is_favorite': is_favorite,
            'num_updates': len(horse_df),
            'implied_prob': implied_prob,
            # Jockey/Trainer
            'jockey_win_rate': jockey_win_rate,
            'trainer_win_rate': trainer_win_rate,
            'combined_form': (jockey_win_rate + trainer_win_rate) / 2,
            'jockey_odds_interaction': jockey_win_rate * implied_prob,
            'trainer_odds_interaction': trainer_win_rate * implied_prob,
            # Track/Weather
            'track_condition': track_condition,
            'track_condition_score': track_cond_score,
            'is_good': is_good,
            'is_soft': is_soft,
            'is_heavy': is_heavy,
            'is_synth': is_synth,
            'temperature': temp_val,
            'rainfall': rainfall,
            'wet_track': wet_track,
            'temp_normalized': temp_normalized,
        })

    conn.close()
    return pd.DataFrame(features)
