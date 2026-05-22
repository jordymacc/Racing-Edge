"""
Kelly Criterion Staking Strategy
JordyMac Racing Engine v1.0

Uses Half Kelly for safer bankroll growth.
Starting bankroll: $500
Max bet: 10% of bankroll per race (safety cap)
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "racing.db"

STARTING_BANKROLL = 500.00
KELLY_FRACTION = 0.5       # Half Kelly
MAX_BET_PCT = 0.10         # Never bet more than 10% of bankroll
MIN_BET = 2.00             # Minimum bet $2
MIN_EDGE = 0.05            # Only bet if we have >5% edge over the market

def setup_kelly_table():
    """Create kelly_bets table if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kelly_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Bankroll tracker table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bankroll_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            bankroll REAL,
            event TEXT
        )
    """)

    # Insert starting bankroll if empty
    cursor.execute("SELECT COUNT(*) FROM bankroll_history")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO bankroll_history (timestamp, bankroll, event)
            VALUES (?, ?, ?)
        """, (datetime.now().isoformat(), STARTING_BANKROLL, "Starting bankroll"))
        print(f"✅ Starting bankroll set: ${STARTING_BANKROLL:.2f}")

    conn.commit()
    conn.close()

def get_current_bankroll():
    """Get the most recent bankroll value"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT bankroll FROM bankroll_history ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else STARTING_BANKROLL
    except:
        return STARTING_BANKROLL
    finally:
        conn.close()

def calculate_kelly(predicted_prob, win_odds, bankroll):
    """
    Calculate Half Kelly bet size.
    
    predicted_prob: model's probability (0-1)
    win_odds: decimal odds e.g. 5.0
    bankroll: current bankroll in dollars
    
    Returns: (edge, kelly_pct, bet_amount)
    """
    if win_odds <= 1.0 or predicted_prob <= 0:
        return 0, 0, 0

    # Kelly formula: (p * b - q) / b
    # where b = odds - 1, p = win prob, q = lose prob
    b = win_odds - 1
    p = predicted_prob
    q = 1 - p

    kelly_pct = (p * b - q) / b

    # Apply Half Kelly
    kelly_pct = kelly_pct * KELLY_FRACTION

    # Edge = how much better our prob is vs implied market prob
    implied_prob = 1 / win_odds
    edge = predicted_prob - implied_prob

    # Only bet if positive edge above threshold
    if kelly_pct <= 0 or edge < MIN_EDGE:
        return edge, 0, 0

    # Apply max bet cap
    kelly_pct = min(kelly_pct, MAX_BET_PCT)

    # Calculate dollar amount
    bet_amount = bankroll * kelly_pct
    bet_amount = max(bet_amount, MIN_BET)
    bet_amount = round(bet_amount, 2)

    return edge, kelly_pct, bet_amount

def log_kelly_bet(race_name, horse_name, predicted_prob, win_odds):
    """Log a recommended Kelly bet to the database"""
    setup_kelly_table()
    bankroll = get_current_bankroll()
    edge, kelly_pct, bet_amount = calculate_kelly(predicted_prob, win_odds, bankroll)

    if bet_amount <= 0:
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO kelly_bets (
            timestamp, race_name, horse_name, predicted_prob,
            win_odds, edge, kelly_pct, recommended_bet,
            bankroll_before, settled
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        datetime.now().isoformat(),
        race_name, horse_name, predicted_prob,
        win_odds, edge, kelly_pct, bet_amount, bankroll
    ))
    conn.commit()
    conn.close()

    print(f"💰 Kelly Bet: {horse_name} @ ${win_odds:.2f}")
    print(f"   Edge: {edge*100:.1f}% | Bet: ${bet_amount:.2f} ({kelly_pct*100:.1f}% of ${bankroll:.2f})")

    return {
        "horse_name": horse_name,
        "race_name": race_name,
        "odds": win_odds,
        "edge": edge,
        "kelly_pct": kelly_pct,
        "bet_amount": bet_amount,
        "bankroll": bankroll
    }

def settle_kelly_bets():
    """Settle outstanding Kelly bets using historical results"""
    setup_kelly_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get unsettled bets
    cursor.execute("""
        SELECT id, race_name, horse_name, recommended_bet, win_odds, bankroll_before
        FROM kelly_bets WHERE settled = 0
    """)
    unsettled = cursor.fetchall()

    if not unsettled:
        conn.close()
        return

    settled_count = 0
    for bet_id, race_name, horse_name, bet_amount, win_odds, bankroll_before in unsettled:
        # Check if result exists
        cursor.execute("""
            SELECT winner FROM historical_results
            WHERE race_name = ? AND horse_name = ?
        """, (race_name, horse_name))
        result = cursor.fetchone()

        if result is None:
            continue

        winner = result[0]
        if winner == 1:
            profit_loss = bet_amount * (win_odds - 1)
            result_str = "WON"
        else:
            profit_loss = -bet_amount
            result_str = "LOST"

        bankroll_after = bankroll_before + profit_loss

        cursor.execute("""
            UPDATE kelly_bets
            SET result = ?, profit_loss = ?, bankroll_after = ?, settled = 1
            WHERE id = ?
        """, (result_str, profit_loss, bankroll_after, bet_id))

        # Update bankroll history
        cursor.execute("""
            INSERT INTO bankroll_history (timestamp, bankroll, event)
            VALUES (?, ?, ?)
        """, (datetime.now().isoformat(), bankroll_after,
              f"{result_str}: {horse_name} @ ${win_odds:.2f}"))

        settled_count += 1
        print(f"  {'✅' if winner else '❌'} {horse_name}: {result_str} ${profit_loss:+.2f} → Bankroll: ${bankroll_after:.2f}")

    conn.commit()
    conn.close()

    if settled_count:
        print(f"\n💰 Settled {settled_count} Kelly bets")

def get_kelly_summary():
    """Print a summary of Kelly betting performance"""
    setup_kelly_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*), SUM(profit_loss), 
               SUM(CASE WHEN result='WON' THEN 1 ELSE 0 END),
               SUM(recommended_bet)
        FROM kelly_bets WHERE settled = 1
    """)
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        print("No settled Kelly bets yet.")
        return

    total_bets, total_pl, wins, total_staked = row
    win_rate = (wins / total_bets * 100) if total_bets else 0
    roi = (total_pl / total_staked * 100) if total_staked else 0
    current_bankroll = get_current_bankroll()

    print(f"\n💰 Kelly Staking Summary")
    print(f"   Bets: {total_bets} | Wins: {wins} ({win_rate:.1f}%)")
    print(f"   Total staked: ${total_staked:.2f}")
    print(f"   P&L: ${total_pl:+.2f} | ROI: {roi:.1f}%")
    print(f"   Current bankroll: ${current_bankroll:.2f}")
    print(f"   Starting bankroll: ${STARTING_BANKROLL:.2f}")
    growth = ((current_bankroll - STARTING_BANKROLL) / STARTING_BANKROLL * 100)
    print(f"   Bankroll growth: {growth:+.1f}%")

if __name__ == "__main__":
    setup_kelly_table()
    print("Testing Kelly Calculator...")
    print()

    tests = [
        ("Strong favourite", 0.45, 2.50),
        ("Mid-range", 0.30, 5.00),
        ("Longshot with edge", 0.20, 8.00),
        ("No edge", 0.15, 8.00),
    ]

    bankroll = get_current_bankroll()
    print(f"Current bankroll: ${bankroll:.2f}\n")

    for name, prob, odds in tests:
        edge, kelly_pct, bet = calculate_kelly(prob, odds, bankroll)
        if bet > 0:
            print(f"✅ {name}: prob={prob:.0%} odds=${odds:.2f} → Bet ${bet:.2f} (edge {edge*100:.1f}%)")
        else:
            print(f"⛔ {name}: prob={prob:.0%} odds=${odds:.2f} → No bet (edge {edge*100:.1f}%)")
