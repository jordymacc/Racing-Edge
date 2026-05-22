import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

def setup_tracking_tables():
    """Create tables for tracking predictions vs results"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for logged predictions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_predictions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            race_name TEXT,
            horse_name TEXT,
            predicted_win_prob REAL,
            current_odds REAL,
            confidence TEXT,
            actual_result INTEGER,
            profit_loss REAL,
            settled INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Performance tracking tables created")


def log_prediction(race_name, horse_name, win_prob, odds, confidence):
    """Log a prediction for later tracking"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO ml_predictions_log 
        (timestamp, race_name, horse_name, predicted_win_prob, current_odds, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        race_name,
        horse_name,
        win_prob,
        odds,
        confidence
    ))
    
    conn.commit()
    conn.close()


def settle_predictions():
    """Check results and calculate P&L for unsettled predictions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get unsettled predictions
    cursor.execute("""
        SELECT id, race_name, horse_name, current_odds
        FROM ml_predictions_log
        WHERE settled = 0
    """)
    
    unsettled = cursor.fetchall()
    
    settled_count = 0
    
    for pred_id, race_name, horse_name, odds in unsettled:
        # Check if race has a result
        cursor.execute("""
            SELECT winner FROM historical_results
            WHERE race_name = ? AND horse_name = ?
        """, (race_name, horse_name))
        
        result = cursor.fetchone()
        
        if result is not None:
            actual_result = result[0]
            
            # Calculate P&L (assume $10 bet)
            stake = 10
            if actual_result == 1:  # Won
                profit_loss = (odds - 1) * stake
            else:  # Lost
                profit_loss = -stake
            
            # Update prediction
            cursor.execute("""
                UPDATE ml_predictions_log
                SET actual_result = ?, profit_loss = ?, settled = 1
                WHERE id = ?
            """, (actual_result, profit_loss, pred_id))
            
            settled_count += 1
    
    conn.commit()
    conn.close()
    
    return settled_count


def get_performance_stats():
    """Calculate overall performance statistics"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            COUNT(*) as total_bets,
            SUM(CASE WHEN actual_result = 1 THEN 1 ELSE 0 END) as wins,
            SUM(profit_loss) as total_pl,
            AVG(predicted_win_prob) as avg_confidence
        FROM ml_predictions_log
        WHERE settled = 1
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df['total_bets'].iloc[0] == 0:
        return None
    
    stats = {
        'total_bets': int(df['total_bets'].iloc[0]),
        'wins': int(df['wins'].iloc[0]),
        'losses': int(df['total_bets'].iloc[0] - df['wins'].iloc[0]),
        'win_rate': df['wins'].iloc[0] / df['total_bets'].iloc[0] * 100,
        'total_pl': float(df['total_pl'].iloc[0]),
        'roi': (df['total_pl'].iloc[0] / (df['total_bets'].iloc[0] * 10)) * 100
    }
    
    return stats


def print_performance_report():
    """Print detailed performance report"""
    stats = get_performance_stats()
    
    if stats is None:
        print("\n📊 No settled bets yet")
        return
    
    print("\n" + "=" * 60)
    print("📊 JORDYMAC PERFORMANCE REPORT")
    print("=" * 60)
    print(f"Total Bets:    {stats['total_bets']}")
    print(f"Wins:          {stats['wins']} ✅")
    print(f"Losses:        {stats['losses']} ❌")
    print(f"Win Rate:      {stats['win_rate']:.1f}%")
    print(f"Total P&L:     ${stats['total_pl']:+.2f}")
    print(f"ROI:           {stats['roi']:+.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    setup_tracking_tables()
    settle_predictions()
    print_performance_report()
