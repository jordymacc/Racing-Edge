import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from feature_engine_v3 import extract_features_for_race
import sqlite3

MODEL_PATH = Path(__file__).resolve().parent / "winner_predictor_v4.pkl"
DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

FEATURES = [
    'win_odds_racingcom', 'implied_prob', 'is_favorite', 'market_rank',
    'jockey_win_rate', 'trainer_win_rate', 'combined_form',
    'jockey_odds_interaction', 'trainer_odds_interaction',
    'track_condition_score', 'is_good', 'is_soft', 'is_heavy', 'is_synth',
    'temperature', 'rainfall', 'wet_track', 'temp_normalized'
]

def get_ml_predictions_for_dashboard():
    try:
        model_data = joblib.load(MODEL_PATH)
        model = model_data['model']

        conn = sqlite3.connect(DB_PATH)
        races = pd.read_sql_query("""
            SELECT DISTINCT race_name 
            FROM odds_snapshots
            WHERE timestamp > datetime('now', '-2 hours')
            AND win_odds_racingcom IS NOT NULL
            ORDER BY race_name
        """, conn)['race_name'].tolist()
        conn.close()

        all_predictions = []

        for race in races:
            df = extract_features_for_race(race)
            if df is None or len(df) == 0:
                continue

            X = df[FEATURES].fillna(0)
            win_probs = model.predict_proba(X)[:, 1]

            df['predicted_win_prob'] = win_probs
            df['confidence'] = df['predicted_win_prob'].apply(
                lambda x: 'HIGH' if x > 0.3 else 'MEDIUM' if x > 0.15 else 'LOW'
            )
            all_predictions.append(df)

        if all_predictions:
            return pd.concat(all_predictions, ignore_index=True)
        return None

    except Exception as e:
        print(f"ML Prediction Error: {e}")
        return None

def get_top_picks(n=5):
    predictions = get_ml_predictions_for_dashboard()
    if predictions is None:
        return None
    top_picks = predictions.nlargest(n, 'predicted_win_prob')
    return top_picks[['race_name', 'horse_name', 'current_odds',
                      'predicted_win_prob', 'is_favorite', 'confidence']]
