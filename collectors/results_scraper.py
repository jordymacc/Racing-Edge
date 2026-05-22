import requests
import time
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Origin": "https://www.racing.com",
    "Referer": "https://www.racing.com/",
    "x-api-key": "da2-6nsi4ztsynar3l3frgxf77q5fe",
}

def get_race_results(meet_code):
    """Fetch results for all races at a meeting"""
    url = (
        f"https://graphql.rmdprod.racing.com/?query=query%20getRaceNumberList_CD"
        f"(%24meetCode%3A%20ID!)%20%7B%20getNoCacheRacesForMeet(meetCode%3A%20"
        f"%24meetCode)%20%7B%20raceNumber%20raceStatus%20meet%20%7B%20venue%20%7D%20"
        f"formRaceEntries%20%7B%20horseName%20position%20%7D%20%7D%20%7D"
        f"&variables=%7B%22meetCode%22%3A%22{meet_code}%22%7D"
    )
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠️  Failed: {e}")
        return None


def parse_results(data, meet_code):
    """Extract finishing positions from API response"""
    results = []
    
    try:
        races = data.get("data", {}).get("getNoCacheRacesForMeet", [])
        venue = races[0].get("meet", {}).get("venue") if races else "Unknown"
        
        for race in races:
            race_num = race.get("raceNumber")
            status = race.get("raceStatus", "")
            
            # Check if race has finished (Paying, Closed, Final, etc.)
            if status.upper() not in ["PAYING", "CLOSED", "FINAL", "RESULTED"]:
                continue
            
            entries = race.get("formRaceEntries", [])
            race_name = f"{venue} R{race_num}"
            
            for entry in entries:
                position = entry.get("position")
                horse_name = entry.get("horseName")
                
                # Only save valid positions (1-20, ignore scratched = 109)
                if position and horse_name and position < 100:
                    results.append({
                        "race_name": race_name,
                        "horse_name": horse_name,
                        "finish_position": position,
                        "winner": 1 if position == 1 else 0,
                        "placed": 1 if position <= 3 else 0,
                    })
        
    except Exception as e:
        print(f"  ⚠️  Parse error: {e}")
    
    return results


def save_results_to_db(results):
    """Save race results to database"""
    if not results:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    saved = 0
    
    for result in results:
        # Check if result already exists
        cursor.execute("""
            SELECT COUNT(*) FROM historical_results
            WHERE race_name = ? AND horse_name = ?
        """, (result['race_name'], result['horse_name']))
        
        if cursor.fetchone()[0] > 0:
            continue  # Skip duplicates
        
        cursor.execute("""
            INSERT INTO historical_results (
                race_name, race_date, horse_name, finish_position,
                winner, placed
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            result['race_name'],
            now[:10],
            result['horse_name'],
            result['finish_position'],
            result['winner'],
            result['placed']
        ))
        
        saved += 1
    
    conn.commit()
    conn.close()
    return saved


def scrape_todays_results():
    """Scrape results for all today's meetings"""
    print(f"\n🏆 Results Scraper — {datetime.now().strftime('%H:%M:%S')}\n")
    
    # Get unique meet codes from odds snapshots
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT meet_code FROM odds_snapshots
        WHERE meet_code IS NOT NULL
        AND timestamp > datetime('now', '-12 hours')
    """)
    
    meet_codes = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not meet_codes:
        print("  ⚠️  No meet codes found in database\n")
        return
    
    print(f"  🔍 Checking {len(meet_codes)} meetings for results...")
    
    total_results = 0
    
    for meet_code in meet_codes:
        data = get_race_results(meet_code)
        
        if data:
            results = parse_results(data, meet_code)
            
            if results:
                saved = save_results_to_db(results)
                total_results += saved
                if saved > 0:
                    print(f"  ✅ Meet {meet_code} — {saved} new results")
        
        time.sleep(0.5)
    
    if total_results > 0:
        print(f"\n🎉 Done — {total_results} new results saved!\n")
    else:
        print(f"\n⏳ No new results (all already saved or races still running)\n")


if __name__ == "__main__":
    scrape_todays_results()
