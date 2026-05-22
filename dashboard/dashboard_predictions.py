import joblib
import pandas as pd
from pathlib import Path
from feature_engine import extract_features_for_race
import sqlite3

MODEL_PATH = Path(__file__).resolve().parent / "winner_predictor_v2.pkl"
DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

def get_ml_predictions_for_dashboard():
    """Get ML predictions formatted for Streamlit dashboard"""
    
    try:
        # Load model
        model_data = joblib.load(MODEL_PATH)
        model = model_data['model']
        features = model_data['features']
        
        # Get recent races with odds
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT DISTINCT race_name 
            FROM odds_snapshots
            WHERE timestamp > datetime('now', '-2 hours')
            AND win_odds_racingcom IS NOT NULL
            ORDER BY race_name
        """
        
        races = pd.read_sql_query(query, conn)['race_name'].tolist()
        conn.close()
        
        all_predictions = []
        
        for race in races:
            race_features = extract_features_for_race(race)
            
            if race_features is None or len(race_features) == 0:
                continue
            
            # Predict
            X = race_features[features].fillna(0)
            win_probs = model.predict_proba(X)[:, 1]
            
            race_features['win_probability'] = win_probs
            race_features['confidence'] = race_features['win_probability'].apply(
                lambda x: 'HIGH' if x > 0.3 else 'MEDIUM' if x > 0.15 else 'LOW'
            )
            
            all_predictions.append(race_features)
        
        if all_predictions:
            return pd.concat(all_predictions, ignore_index=True)
        else:
            return None
            
    except Exception as e:
        print(f"ML Prediction Error: {e}")
        return None


def get_top_picks(n=5):
    """Get top N picks across all races"""
    predictions = get_ml_predictions_for_dashboard()
    
    if predictions is None:
        return None
    
    top_picks = predictions.nlargest(n, 'win_probability')
    
    return top_picks[['race_name', 'horse_name', 'current_odds', 
                      'win_probability', 'is_favorite', 'confidence']]
