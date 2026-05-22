"""
Sets up PostgreSQL tables for JordyMac Racing Engine
Run once to initialise the database
"""
import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ No DATABASE_URL found. Set it in your environment.")
    exit()

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("Setting up PostgreSQL tables...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TEXT,
    race_name TEXT,
    horse_name TEXT,
    jockey_name TEXT,
    trainer_name TEXT,
    win_odds_racingcom REAL,
    place_odds_racingcom REAL,
    meet_code TEXT,
    track_condition TEXT,
    track_condition_score REAL,
    temperature REAL,
    rainfall REAL
)
""")

cursor.execute("""
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS jockey_stats (
    id SERIAL PRIMARY KEY,
    jockey_name TEXT UNIQUE,
    total_rides INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS trainer_stats (
    id SERIAL PRIMARY KEY,
    trainer_name TEXT UNIQUE,
    total_starters INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ml_predictions_log (
    id SERIAL PRIMARY KEY,
    timestamp TEXT,
    race_name TEXT,
    horse_name TEXT,
    predicted_win_prob REAL,
    current_odds REAL,
    confidence TEXT,
    actual_result TEXT,
    profit_loss REAL,
    settled INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS kelly_bets (
    id SERIAL PRIMARY KEY,
    timestamp TEXT,
    race_name TEXT,
    horse_name TEXT,
    predicted_prob REAL,
    win_odds REAL,
    edge REAL,
    kelly_pct REAL,
    recommended_bet REAL,
    bankroll_before REAL,
    bankroll_after REAL,
    result TEXT,
    profit_loss REAL,
    settled INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS bankroll_history (
    id SERIAL PRIMARY KEY,
    timestamp TEXT,
    bankroll REAL,
    event TEXT
)
""")

conn.commit()
conn.close()
print("✅ All PostgreSQL tables created successfully!")
