import os
import sqlite3
from pathlib import Path
from datetime import datetime

SQLITE_PATH = Path(__file__).resolve().parent / "racing.db"
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL), "pg"
    return sqlite3.connect(str(SQLITE_PATH)), "sqlite"

def save_odds(rows, meet_code):
    if not rows:
        return
    conn, db = get_conn()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    ph = "%s" if db == "pg" else "?"
    for row in rows:
        cursor.execute(f"""
            INSERT INTO odds_snapshots (
                timestamp, race_name, horse_name, jockey_name, trainer_name,
                win_odds_racingcom, place_odds_racingcom, meet_code,
                track_condition, track_condition_score, temperature, rainfall
            ) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
        """, (
            now, row.get("race_name"), row.get("horse_name"),
            row.get("jockey_name"), row.get("trainer_name"),
            row.get("win_odds_racingcom"), row.get("place_odds_racingcom"),
            meet_code, row.get("track_condition"), row.get("track_condition_score"),
            row.get("temperature"), row.get("rainfall"),
        ))
    conn.commit()
    conn.close()

def get_pandas_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(str(SQLITE_PATH))

if __name__ == "__main__":
    conn, db = get_conn()
    print(f"Connected to {db.upper()}")
    conn.close()
