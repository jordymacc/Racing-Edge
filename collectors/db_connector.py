import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

def save_odds_snapshot(race_name, horse_name, win_odds_sportsbet=None,
                       win_odds_tab=None, win_odds_racingcom=None,
                       place_odds_sportsbet=None, place_odds_tab=None,
                       place_odds_racingcom=None, lay_odds=None,
                       minutes_to_jump=None):
    """Save one row of odds data into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO odds_snapshots (
            timestamp, race_name, horse_name,
            win_odds_sportsbet, win_odds_tab, win_odds_racingcom,
            place_odds_sportsbet, place_odds_tab, place_odds_racingcom,
            lay_odds, minutes_to_jump
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        race_name,
        horse_name,
        win_odds_sportsbet,
        win_odds_tab,
        win_odds_racingcom,
        place_odds_sportsbet,
        place_odds_tab,
        place_odds_racingcom,
        lay_odds,
        minutes_to_jump
    ))

    conn.commit()
    conn.close()


def save_many_odds(rows):
    """Save multiple rows at once. Much faster for full race cards.

    Each row should be a dict like:
    {
        'race_name': 'R1 Flemington',
        'horse_name': 'Black Caviar',
        'win_odds_sportsbet': 2.40,
        'win_odds_tab': 2.50,
        ...
    }
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    for row in rows:
        cursor.execute("""
            INSERT INTO odds_snapshots (
                timestamp, race_name, horse_name,
                win_odds_sportsbet, win_odds_tab, win_odds_racingcom,
                place_odds_sportsbet, place_odds_tab, place_odds_racingcom,
                lay_odds, minutes_to_jump
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            row.get('race_name'),
            row.get('horse_name'),
            row.get('win_odds_sportsbet'),
            row.get('win_odds_tab'),
            row.get('win_odds_racingcom'),
            row.get('place_odds_sportsbet'),
            row.get('place_odds_tab'),
            row.get('place_odds_racingcom'),
            row.get('lay_odds'),
            row.get('minutes_to_jump')
        ))

    conn.commit()
    conn.close()
    print(f"✅ Saved {len(rows)} odds snapshots at {now}")


def get_latest_odds(race_name):
    """Pull the most recent odds for a race."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM odds_snapshots
        WHERE race_name = ?
        ORDER BY timestamp DESC
    """, (race_name,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def count_snapshots():
    """Quick check — how many snapshots do we have?"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM odds_snapshots")
    count = cursor.fetchone()[0]
    conn.close()
    return count