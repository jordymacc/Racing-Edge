import sqlite3
from pathlib import Path

# Always saves racing.db in the database folder
DB_PATH = Path(__file__).resolve().parent / "racing.db"

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Table 1: Races ──────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS races (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            race_name     TEXT,
            track         TEXT,
            race_date     TEXT,
            jump_time     TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Table 2: Horses ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS horses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id       INTEGER,
            horse_name    TEXT,
            barrier       INTEGER,
            jockey        TEXT,
            trainer       TEXT,
            weight        REAL,
            FOREIGN KEY (race_id) REFERENCES races(id)
        )
    """)

    # ── Table 3: Odds Snapshots ──────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odds_snapshots (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp             TEXT,
            race_name             TEXT,
            horse_name            TEXT,
            win_odds_sportsbet    REAL,
            win_odds_tab          REAL,
            win_odds_racingcom    REAL,
            place_odds_sportsbet  REAL,
            place_odds_tab        REAL,
            place_odds_racingcom  REAL,
            lay_odds              REAL,
            minutes_to_jump       REAL
        )
    """)

    # ── Table 4: Historical Results ──────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_results (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            race_name        TEXT,
            race_date        TEXT,
            track            TEXT,
            horse_name       TEXT,
            finish_position  INTEGER,
            winner           INTEGER,  -- 1 = won, 0 = lost
            placed           INTEGER,  -- 1 = placed, 0 = didnt place
            win_odds         REAL,
            place_odds       REAL,
            lay_odds         REAL
        )
    """)

    # ── Table 5: Model Predictions ───────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_predictions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        TEXT,
            race_name        TEXT,
            horse_name       TEXT,
            win_probability  REAL,
            place_probability REAL,
            lay_probability  REAL,
            signal           TEXT,  -- BACK WIN / BACK PLACE / LAY / NO BET
            confidence       REAL,
            minutes_to_jump  REAL
        )
    """)

    # ── Table 6: Bet Log ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bet_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        TEXT,
            race_name        TEXT,
            horse_name       TEXT,
            bet_type         TEXT,  -- WIN / PLACE / LAY
            odds             REAL,
            stake            REAL,
            result           TEXT,  -- WON / LOST / PENDING
            profit_loss      REAL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ racing.db tables created successfully!")
    print(f"📁 Saved at: {DB_PATH}")

if __name__ == "__main__":
    setup_database()