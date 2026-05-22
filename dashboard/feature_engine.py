import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

def extract_features_for_race(race_name):
    """Extract ML features for all horses in a race"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            horse_name,
            win_odds_racingcom,
            timestamp
        FROM odds_snapshots
        WHERE race_name = ?
        AND win_odds_racingcom IS NOT NULL
        ORDER BY horse_name, timestamp
    """
    
    df = pd.read_sql_query(query, conn, params=(race_name,))
    conn.close()
    
    if df.empty:
        return None
    
    features = []
    
    for horse in df['horse_name'].unique():
        horse_df = df[df['horse_name'] == horse].copy()
        horse_df = horse_df.sort_values('timestamp')
        
        # Need at least 1 odds snapshot
        if len(horse_df) < 1:
            continue
        
        current_odds = horse_df['win_odds_racingcom'].iloc[-1]
        
        # If we have multiple snapshots, calculate movement
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
        
        # Market rank
        all_current_odds = df.groupby('horse_name')['win_odds_racingcom'].last()
        market_rank = (all_current_odds <= current_odds).sum()
        is_favorite = 1 if current_odds == all_current_odds.min() else 0
        
        features.append({
            'race_name': race_name,
            'horse_name': horse,
            'current_odds': current_odds,
            'opening_odds': opening_odds,
            'odds_change_pct': odds_change_pct,
            'mean_odds': mean_odds,
            'min_odds': min_odds,
            'max_odds': max_odds,
            'volatility': volatility,
            'market_rank': market_rank,
            'is_favorite': is_favorite,
            'num_updates': len(horse_df)
        })
    
    return pd.DataFrame(features)


def build_training_dataset():
    """Build complete training dataset"""
    conn = sqlite3.connect(DB_PATH)
    
    # Get races that have BOTH results AND odds
    query = """
        SELECT DISTINCT r.race_name 
        FROM historical_results r
        INNER JOIN odds_snapshots o 
            ON r.race_name = o.race_name
        WHERE o.win_odds_racingcom IS NOT NULL
    """
    
    races = pd.read_sql_query(query, conn)['race_name'].tolist()
    
    print(f"🔧 Building features for {len(races)} races with complete data...")
    
    all_features = []
    races_processed = 0
    
    for i, race in enumerate(races):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(races)}")
        
        features = extract_features_for_race(race)
        
        if features is not None and len(features) > 0:
            all_features.append(features)
            races_processed += 1
    
    print(f"  ✅ Successfully processed {races_processed}/{len(races)} races")
    
    if not all_features:
        print("❌ No features extracted")
        return None
    
    # Combine
    X = pd.concat(all_features, ignore_index=True)
    print(f"✅ Features extracted: {len(X)} horses")
    
    # Get labels
    labels_query = "SELECT race_name, horse_name, winner, placed FROM historical_results"
    y = pd.read_sql_query(labels_query, conn)
    conn.close()
    
    # Merge
    dataset = pd.merge(X, y, on=['race_name', 'horse_name'], how='inner')
    
    dataset['winner'] = dataset['winner'].astype(int)
    dataset['placed'] = dataset['placed'].astype(int)
    
    print(f"✅ Dataset built: {len(dataset)} horses, {dataset['winner'].sum()} winners\n")
    
    return dataset


if __name__ == "__main__":
    df = build_training_dataset()
    if df is not None:
        print("Sample data:")
        print(df[['horse_name', 'current_odds', 'odds_change_pct', 'is_favorite', 'winner']].head(10))
        print(f"\nDataset shape: {df.shape}")
        print(f"Winners: {df['winner'].sum()}")
        print(f"Non-winners: {(df['winner'] == 0).sum()}")
        print(f"Win rate: {df['winner'].mean()*100:.1f}%")
