import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

def calculate_jockey_stats():
    """Calculate win rates for all jockeys - FIXED"""
    conn = sqlite3.connect(DB_PATH)
    
    # Fix: Use DISTINCT race+horse combinations to avoid duplicates
    query = """
        SELECT 
            o.jockey_name,
            COUNT(DISTINCT o.race_name || '|' || o.horse_name) as total_rides,
            COUNT(DISTINCT CASE WHEN r.winner = 1 
                THEN o.race_name || '|' || o.horse_name 
                END) as wins
        FROM odds_snapshots o
        LEFT JOIN historical_results r 
            ON o.race_name = r.race_name 
            AND o.horse_name = r.horse_name
        WHERE o.jockey_name IS NOT NULL
        GROUP BY o.jockey_name
        HAVING total_rides > 0
    """
    
    df = pd.read_sql_query(query, conn)
    df['win_rate'] = df['wins'] / df['total_rides']
    df['last_updated'] = datetime.now().isoformat()
    
    # Save to jockey_stats table
    for _, row in df.iterrows():
        conn.execute("""
            INSERT OR REPLACE INTO jockey_stats 
            (jockey_name, total_rides, total_wins, win_rate, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (
            row['jockey_name'],
            int(row['total_rides']),
            int(row['wins']),
            float(row['win_rate']),
            row['last_updated']
        ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Jockey stats calculated for {len(df)} jockeys")
    print("\nTop 10 jockeys by win rate (min 2 rides):")
    top = df[df['total_rides'] >= 2].nlargest(10, 'win_rate')
    for _, row in top.iterrows():
        print(f"  {row['jockey_name']:25s} "
              f"{int(row['wins'])}/{int(row['total_rides'])} rides "
              f"({row['win_rate']*100:.1f}%)")
    
    return df


def calculate_trainer_stats():
    """Calculate win rates for all trainers - FIXED"""
    conn = sqlite3.connect(DB_PATH)
    
    # Fix: Use DISTINCT race+horse combinations
    query = """
        SELECT 
            o.trainer_name,
            COUNT(DISTINCT o.race_name || '|' || o.horse_name) as total_starters,
            COUNT(DISTINCT CASE WHEN r.winner = 1 
                THEN o.race_name || '|' || o.horse_name 
                END) as wins
        FROM odds_snapshots o
        LEFT JOIN historical_results r 
            ON o.race_name = r.race_name 
            AND o.horse_name = r.horse_name
        WHERE o.trainer_name IS NOT NULL
        GROUP BY o.trainer_name
        HAVING total_starters > 0
    """
    
    df = pd.read_sql_query(query, conn)
    df['win_rate'] = df['wins'] / df['total_starters']
    df['last_updated'] = datetime.now().isoformat()
    
    # Save to trainer_stats table
    for _, row in df.iterrows():
        conn.execute("""
            INSERT OR REPLACE INTO trainer_stats 
            (trainer_name, total_starters, total_wins, win_rate, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (
            row['trainer_name'],
            int(row['total_starters']),
            int(row['wins']),
            float(row['win_rate']),
            row['last_updated']
        ))
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Trainer stats calculated for {len(df)} trainers")
    print("\nTop 10 trainers by win rate (min 2 starts):")
    top = df[df['total_starters'] >= 2].nlargest(10, 'win_rate')
    for _, row in top.iterrows():
        print(f"  {row['trainer_name']:25s} "
              f"{int(row['wins'])}/{int(row['total_starters'])} starts "
              f"({row['win_rate']*100:.1f}%)")
    
    return df


if __name__ == "__main__":
    print("🏇 Calculating jockey/trainer statistics...\n")
    print("=" * 60)
    calculate_jockey_stats()
    calculate_trainer_stats()
    print("\n" + "=" * 60)
    print("✅ Fixed stats ready for ML model!")
