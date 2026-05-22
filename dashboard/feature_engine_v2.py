import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

def get_jockey_win_rate(jockey_name, conn):
    """Get historical win rate for a jockey"""
    if not jockey_name:
        return 0.0
    cursor = conn.cursor()
    cursor.execute("""
        SELECT win_rate FROM jockey_stats 
        WHERE jockey_name = ?
    """, (jockey_name,))
    result = cursor.fetchone()
    return float(result[0]) if result else 0.0


def get_trainer_win_rate(trainer_name, conn):
    """Get historical win rate for a trainer"""
    if not trainer_name:
        return 0.0
    cursor = conn.cursor()
    cursor.execute("""
        SELECT win_rate FROM trainer_stats 
        WHERE trainer_name = ?
    """, (trainer_name,))
    result = cursor.fetchone()
    return float(result[0]) if result else 0.0


def extract_features_for_race(race_name):
    """Extract ML features INCLUDING jockey/trainer stats"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            horse_name,
            jockey_name,
            trainer_name,
            win_odds_racingcom,
            timestamp
        FROM odds_snapshots
        WHERE race_name = ?
        AND win_odds_racingcom IS NOT NULL
        ORDER BY horse_name, timestamp
    """
    
    df = pd.read_sql_query(query, conn, params=(race_name,))
    
    if df.empty:
        conn.close()
        return None
    
    features = []
    
    for horse in df['horse_name'].unique():
        horse_df = df[df['horse_name'] == horse].copy()
        horse_df = horse_df.sort_values('timestamp')
        
        if len(horse_df) < 1:
            continue
        
        # Get jockey/trainer names
        jockey_name = horse_df['jockey_name'].iloc[-1]
        trainer_name = horse_df['trainer_name'].iloc[-1]
        
        # Get win rates
        jockey_win_rate = get_jockey_win_rate(jockey_name, conn)
        trainer_win_rate = get_trainer_win_rate(trainer_name, conn)
        
        # Odds features
        current_odds = horse_df['win_odds_racingcom'].iloc[-1]
        
        if len(horse_df) >= 2:
            opening_odds = horse_df['win_odds_racingcom'].iloc[0]
            odds_change_pct = ((opening_odds - current_odds) / opening_odds * 100) if opening_odds > 0 else 0
            mean_odds = horse_df['win_odds_racingcom'].mean()
            std_odds = horse_df['win_odds_racingcom'].std()
            min_odds = horse_df['win_odds_racingcom'].min()
            max_odds = horse_df['win_odds_racingcom'].max()
            volatility = std_odds / mean_odds if mean_odds > 0 else 0
        else:
            opening_odds = current_odds
            odds_change_pct = 0
            mean_odds = current_odds
            min_odds = current_odds
            max_odds = current_odds
            volatility = 0
        
        # Market features
        all_current_odds = df.groupby('horse_name')['win_odds_racingcom'].last()
        market_rank = (all_current_odds <= current_odds).sum()
        is_favorite = 1 if current_odds == all_current_odds.min() else 0
        
        features.append({
            'race_name': race_name,
            'horse_name': horse,
            'jockey_name': jockey_name,
            'trainer_name': trainer_name,

            # Odds features
            'current_odds': current_odds,
            'opening_odds': opening_odds,
            'odds_change_pct': odds_change_pct,
            'mean_odds': mean_odds,
            'min_odds': min_odds,
            'max_odds': max_odds,
            'volatility': volatility,
            'market_rank': market_rank,
            'is_favorite': is_favorite,
            'num_updates': len(horse_df),

            # ⭐ NEW: Jockey/Trainer features
            'jockey_win_rate': jockey_win_rate,
            'trainer_win_rate': trainer_win_rate,
            'combined_form': (jockey_win_rate + trainer_win_rate) / 2,
        })
    
    conn.close()
    return pd.DataFrame(features)


def build_training_dataset():
    """Build complete training dataset with all features"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT DISTINCT r.race_name 
        FROM historical_results r
        INNER JOIN odds_snapshots o 
            ON r.race_name = o.race_name
        WHERE o.win_odds_racingcom IS NOT NULL
    """
    
    races = pd.read_sql_query(query, conn)['race_name'].tolist()
    
    print(f"🔧 Building enhanced features for {len(races)} races...")
    
    all_features = []
    
    for i, race in enumerate(races):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(races)}")
        
        features = extract_features_for_race(race)
        
        if features is not None and len(features) > 0:
            all_features.append(features)
    
    if not all_features:
        print("❌ No features extracted")
        return None
    
    X = pd.concat(all_features, ignore_index=True)
    print(f"✅ Features extracted: {len(X)} horses")
    
    labels_query = "SELECT race_name, horse_name, winner, placed FROM historical_results"
    y = pd.read_sql_query(labels_query, conn)
    conn.close()
    
    dataset = pd.merge(X, y, on=['race_name', 'horse_name'], how='inner')
    dataset['winner'] = dataset['winner'].astype(int)
    dataset['placed'] = dataset['placed'].astype(int)
    
    print(f"✅ Dataset: {len(dataset)} horses, {dataset['winner'].sum()} winners\n")
    
    return dataset


if __name__ == "__main__":
    df = build_training_dataset()
    if df is not None:
        print("Feature columns:")
        print([c for c in df.columns if c not in ['race_name', 'horse_name', 'jockey_name', 'trainer_name', 'winner', 'placed']])
        print(f"\nSample jockey win rates:")
        print(df[['horse_name', 'jockey_name', 'jockey_win_rate', 'trainer_win_rate', 'winner']].head(10))
