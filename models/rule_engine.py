import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

def get_odds_movement(race_name, minutes_back=5):
    """
    Compare current odds vs odds from X minutes ago
    Returns list of horses with biggest moves
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now()
    cutoff = (now - timedelta(minutes=minutes_back)).isoformat()
    
    # Get odds from X minutes ago
    cursor.execute("""
        SELECT horse_name, win_odds_racingcom, timestamp
        FROM odds_snapshots
        WHERE race_name = ? 
        AND timestamp < ?
        AND win_odds_racingcom IS NOT NULL
        ORDER BY timestamp ASC
    """, (race_name, cutoff))
    
    old_odds = {row[0]: float(row[1]) for row in cursor.fetchall()}
    
    # Get current odds
    cursor.execute("""
        SELECT horse_name, win_odds_racingcom, timestamp
        FROM odds_snapshots
        WHERE race_name = ?
        AND win_odds_racingcom IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 20
    """, (race_name,))
    
    current_odds = {}
    for row in cursor.fetchall():
        horse = row[0]
        if horse not in current_odds:
            current_odds[horse] = float(row[1])
    
    conn.close()
    
    # Calculate movement
    movements = []
    for horse, current in current_odds.items():
        if horse in old_odds:
            old = old_odds[horse]
            change = old - current  # Positive = shortening (good)
            pct_change = (change / old) * 100 if old > 0 else 0
            
            movements.append({
                "horse": horse,
                "old_odds": old,
                "current_odds": current,
                "change": change,
                "pct_change": pct_change
            })
    
    # Sort by biggest moves
    movements.sort(key=lambda x: x['pct_change'], reverse=True)
    return movements


def get_current_favourites():
    """Get current favourite for each upcoming race"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get latest odds snapshot
    cursor.execute("""
        SELECT DISTINCT race_name FROM odds_snapshots
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    
    races = [row[0] for row in cursor.fetchall()]
    
    favourites = []
    
    for race in races:
        cursor.execute("""
            SELECT horse_name, win_odds_racingcom, place_odds_racingcom
            FROM odds_snapshots
            WHERE race_name = ?
            AND win_odds_racingcom IS NOT NULL
            ORDER BY timestamp DESC, win_odds_racingcom ASC
            LIMIT 1
        """, (race,))
        
        result = cursor.fetchone()
        if result:
            favourites.append({
                "race": race,
                "horse": result[0],
                "win_odds": result[1],
                "place_odds": result[2] or 0
            })
    
    conn.close()
    return favourites


def get_betting_signals():
    """
    Main function — returns betting signals for all races
    """
    signals = []
    
    # Get all unique races from recent data
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT race_name 
        FROM odds_snapshots
        WHERE timestamp > datetime('now', '-10 minutes')
        ORDER BY race_name
    """)
    
    races = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    for race in races:
        movements = get_odds_movement(race, minutes_back=5)
        
        if movements:
            # SIGNAL 1: Steam Move (odds shortening fast)
            for move in movements[:3]:  # Top 3 movers
                if move['pct_change'] > 15:  # 15%+ move
                    signals.append({
                        "race": race,
                        "horse": move['horse'],
                        "signal": "STEAM MOVE",
                        "current_odds": move['current_odds'],
                        "movement": f"{move['pct_change']:.1f}%",
                        "confidence": "HIGH" if move['pct_change'] > 25 else "MEDIUM",
                        "bet_type": "WIN"
                    })
            
            # SIGNAL 2: Drift Warning (odds blowing out)
            for move in movements[-3:]:  # Bottom 3 movers
                if move['pct_change'] < -20:  # Drifting 20%+
                    signals.append({
                        "race": race,
                        "horse": move['horse'],
                        "signal": "DRIFT WARNING",
                        "current_odds": move['current_odds'],
                        "movement": f"{move['pct_change']:.1f}%",
                        "confidence": "AVOID",
                        "bet_type": "LAY"
                    })
    
    return signals


def print_signals():
    """Pretty print betting signals"""
    signals = get_betting_signals()
    
    print(f"\n🎯 BETTING SIGNALS — {datetime.now().strftime('%H:%M:%S')}\n")
    
    if not signals:
        print("⚠️  No strong signals detected yet")
        print("   (Need more data collection time)\n")
        return
    
    for sig in signals:
        emoji = "🔥" if sig['confidence'] == "HIGH" else "⚡"
        print(f"{emoji} {sig['signal']}")
        print(f"   Race: {sig['race']}")
        print(f"   Horse: {sig['horse']}")
        print(f"   Odds: ${sig['current_odds']}")
        print(f"   Movement: {sig['movement']}")
        print(f"   Confidence: {sig['confidence']}")
        print(f"   Bet Type: {sig['bet_type']}")
        print()


if __name__ == "__main__":
    print_signals()
