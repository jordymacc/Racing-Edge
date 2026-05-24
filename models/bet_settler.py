"""
Auto-settler for ML predictions
- Logs predictions to PostgreSQL
- Settles bets when results come in
- Tracks real P&L
"""
import os
import psycopg2
from datetime import datetime
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL")
DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

def get_conn():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL), "pg"
    import sqlite3
    return sqlite3.connect(str(DB_PATH)), "sqlite"

def setup_tables():
    conn, db = get_conn()
    cur = conn.cursor()
    ph = "%s" if db == "pg" else "?"

    if db == "pg":
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ml_predictions_log (
                id SERIAL PRIMARY KEY,
                timestamp TEXT,
                race_name TEXT,
                horse_name TEXT,
                predicted_win_prob REAL,
                current_odds REAL,
                confidence TEXT,
                edge REAL,
                kelly_bet REAL,
                actual_result TEXT,
                profit_loss REAL,
                settled INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS historical_results (
                id SERIAL PRIMARY KEY,
                race_name TEXT,
                race_date TEXT,
                horse_name TEXT,
                finish_position INTEGER,
                winner INTEGER DEFAULT 0,
                placed INTEGER DEFAULT 0
            )
        """)
    conn.commit()
    conn.close()
    print("✅ Bet settler tables ready")

def log_predictions(predictions_df):
    """Log ML predictions to database"""
    if predictions_df is None or predictions_df.empty:
        return 0

    conn, db = get_conn()
    cur = conn.cursor()
    ph = "%s" if db == "pg" else "?"
    now = datetime.now().isoformat()
    logged = 0

    for _, row in predictions_df.iterrows():
        try:
            prob = float(row.get("predicted_win_prob", 0) or 0)
            odds = float(row.get("current_odds", 0) or 0)
            implied = 1/odds if odds > 0 else 0
            edge = round((prob - implied) * 100, 1)

            # Kelly bet
            if prob > 0 and odds > 1:
                b = odds - 1
                kelly = (prob * b - (1-prob)) / b * 0.5
                kelly = max(0, min(kelly, 0.10))
                kelly_bet = round(500 * kelly, 2)
            else:
                kelly_bet = 0

            # Only log if positive edge
            if edge <= 0:
                continue

            cur.execute(f"""
                INSERT INTO ml_predictions_log
                (timestamp, race_name, horse_name, predicted_win_prob,
                 current_odds, confidence, edge, kelly_bet, settled)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},0)
                ON CONFLICT DO NOTHING
            """ if db == "pg" else f"""
                INSERT OR IGNORE INTO ml_predictions_log
                (timestamp, race_name, horse_name, predicted_win_prob,
                 current_odds, confidence, edge, kelly_bet, settled)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},0)
            """, (
                now,
                row.get("race_name"),
                row.get("horse_name"),
                prob,
                odds,
                row.get("confidence", "LOW"),
                edge,
                kelly_bet,
                0
            ))
            logged += 1
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    if logged > 0:
        print(f"  📝 Logged {logged} predictions")
    return logged

def settle_predictions():
    """Match unsettled predictions against results"""
    conn, db = get_conn()
    cur = conn.cursor()
    ph = "%s" if db == "pg" else "?"

    # Get unsettled predictions
    cur.execute("""
        SELECT id, race_name, horse_name, current_odds, kelly_bet
        FROM ml_predictions_log
        WHERE settled = 0
    """)
    unsettled = cur.fetchall()

    if not unsettled:
        conn.close()
        return 0

    settled_count = 0
    total_pl = 0

    for pred_id, race_name, horse_name, odds, kelly_bet in unsettled:
        # Check if result exists
        cur.execute(f"""
            SELECT winner, finish_position FROM historical_results
            WHERE race_name = {ph} AND horse_name = {ph}
            LIMIT 1
        """, (race_name, horse_name))
        result = cur.fetchone()

        if result is None:
            continue

        winner, position = result
        bet = kelly_bet or 10.0

        if winner == 1:
            pl = round(bet * (odds - 1), 2)
            result_str = "WON"
        else:
            pl = -round(bet, 2)
            result_str = "LOST"

        cur.execute(f"""
            UPDATE ml_predictions_log
            SET settled = 1, actual_result = {ph}, profit_loss = {ph}
            WHERE id = {ph}
        """, (result_str, pl, pred_id))

        settled_count += 1
        total_pl += pl

    conn.commit()
    conn.close()

    if settled_count > 0:
        print(f"  ✅ Settled {settled_count} bets | P&L: ${total_pl:+.2f}")

    return settled_count

def get_performance_summary():
    """Get overall betting performance"""
    conn, db = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN actual_result = 'WON' THEN 1 ELSE 0 END) as wins,
            SUM(profit_loss) as total_pl,
            SUM(kelly_bet) as total_staked,
            AVG(edge) as avg_edge
        FROM ml_predictions_log
        WHERE settled = 1
    """)
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return None

    total, wins, pl, staked, avg_edge = row
    return {
        "total_bets": total,
        "wins": wins or 0,
        "win_rate": round((wins or 0) / total * 100, 1),
        "total_pl": round(pl or 0, 2),
        "total_staked": round(staked or 0, 2),
        "roi": round((pl or 0) / (staked or 1) * 100, 1),
        "avg_edge": round(avg_edge or 0, 1)
    }

if __name__ == "__main__":
    setup_tables()
    print("Testing settler...")
    summary = get_performance_summary()
    if summary:
        print(f"Total bets: {summary['total_bets']}")
        print(f"Win rate: {summary['win_rate']}%")
        print(f"ROI: {summary['roi']}%")
    else:
        print("No settled bets yet")
