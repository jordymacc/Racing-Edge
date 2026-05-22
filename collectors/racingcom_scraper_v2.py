import requests
import time
from datetime import datetime
from pathlib import Path
import sqlite3

print("🔧 Script loaded successfully (v2 - Enhanced)")

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Origin": "https://www.racing.com",
    "Referer": "https://www.racing.com/",
    "x-api-key": "da2-6nsi4ztsynar3l3frgxf77q5fe",
}

def get_todays_meetings():
    """Pull all meeting codes for today from racing.com"""
    print("  🔍 Fetching meetings...")
    today = datetime.now().strftime("%Y-%m-%d")

    url = (
        "https://graphql.rmdprod.racing.com/?query=query%20getRaceMeetingsByState"
        "(%24daysForward%3A%20Int!%2C%20%24daysBack%3A%20Int!)%20%7B%0A%20%20"
        "GetRaceMeetingsByStateNew(%0A%20%20%20%20daysForward%3A%20%24daysForward%0A"
        "%20%20%20%20daysBack%3A%20%24daysBack%0A%20%20%20%20states%3A%20%22VIC%7C"
        "SA%7CQLD%7CNSW%7CWA%7CACT%7CNT%7CTAS%22%0A%20%20)%20%7B%0A%20%20%20%20id%0A"
        "%20%20%20%20racesCount%0A%20%20%20%20date%0A%20%20%20%20venue%0A%20%20%20%20"
        "state%0A%20%20%7D%0A%7D&operationName=getRaceMeetingsByState"
        "&variables=%7B%22daysForward%22%3A0%2C%22daysBack%22%3A0%7D"
    )

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()

        all_meetings = data.get("data", {}).get("GetRaceMeetingsByStateNew", [])
        todays_meetings = [m for m in all_meetings if m.get("date") == today]
        
        print(f"  ✅ Found {len(todays_meetings)} meetings")
        
        meetings = []
        for m in todays_meetings:
            meetings.append({
                "meetCode": m.get("id"),
                "venue": {"venueName": m.get("venue"), "state": m.get("state")},
                "racesCount": m.get("racesCount", 8),
                "meetDate": m.get("date")
            })
        
        return meetings

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return []

def get_race_odds(meet_code, race_number):
    """Pull odds for a single race - NOW WITH JOCKEY/TRAINER INFO"""
    url = (
        f"https://graphql.rmdprod.racing.com/?query=query%20getRaceResults_CD"
        f"(%24meetCode%3A%20ID!%20%24raceNumber%3A%20Int!)%20%7B%20"
        f"getRaceForm(meetCode%3A%20%24meetCode%20raceNumber%3A%20%24raceNumber)%20"
        f"%7B%20formRaceEntries%20%7B%20horseName%20scratched%20barrierNumber%20"
        f"jockeyName%20trainerName%20"
        f"odds%20%7B%20oddsWin%20oddsPlace%20%7D%20%7D%20%7D%20%7D"
        f"&variables=%7B%22meetCode%22%3A%22{meet_code}%22%2C%22raceNumber%22%3A{race_number}%7D"
    )

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except:
        return None

def parse_odds(data, meet_code, race_number, venue_name):
    """Extract horse odds - NOW WITH JOCKEY/TRAINER"""
    rows = []
    try:
        entries = data.get("data", {}).get("getRaceForm", {}).get("formRaceEntries", [])
        race_name = f"{venue_name} R{race_number}"

        for entry in entries:
            if entry.get("scratched"):
                continue

            horse_name = entry.get("horseName", "Unknown")
            jockey_name = entry.get("jockeyName")
            trainer_name = entry.get("trainerName")
            
            odds_list = entry.get("odds", [])
            win_odds = None
            place_odds = None

            for odds_item in odds_list:
                if odds_item.get("oddsWin"):
                    try:
                        win_str = str(odds_item["oddsWin"]).replace("$", "")
                        win_odds = float(win_str)
                        
                        place_str = odds_item.get("oddsPlace")
                        if place_str:
                            place_odds = float(str(place_str).replace("$", ""))
                        else:
                            place_odds = None
                        
                        break
                    except:
                        pass

            rows.append({
                "race_name": race_name,
                "horse_name": horse_name,
                "jockey_name": jockey_name,
                "trainer_name": trainer_name,
                "win_odds_racingcom": win_odds,
                "place_odds_racingcom": place_odds,
            })
    except:
        pass

    return rows

def save_to_db(rows, meet_code):
    """Save to database - NOW WITH JOCKEY/TRAINER"""
    if not rows:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    for row in rows:
        cursor.execute("""
            INSERT INTO odds_snapshots (
                timestamp, race_name, horse_name, jockey_name, trainer_name,
                win_odds_racingcom, place_odds_racingcom, meet_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            row.get("race_name"),
            row.get("horse_name"),
            row.get("jockey_name"),
            row.get("trainer_name"),
            row.get("win_odds_racingcom"),
            row.get("place_odds_racingcom"),
            meet_code
        ))

    conn.commit()
    conn.close()

def scrape_all_races():
    """Scrape everything"""
    print(f"\n🏇 Starting scrape — {datetime.now().strftime('%H:%M:%S')}\n")

    meetings = get_todays_meetings()

    if not meetings:
        print("⚠️  No meetings\n")
        return

    total = 0

    for meeting in meetings:
        meet_code = meeting.get("meetCode")
        venue_name = meeting.get("venue", {}).get("venueName", "Unknown")
        races_count = meeting.get("racesCount", 8)
        state = meeting.get("venue", {}).get("state", "")

        print(f"📍 {venue_name} ({state}) — {races_count} races")

        for race_num in range(1, races_count + 1):
            data = get_race_odds(meet_code, race_num)

            if data:
                rows = parse_odds(data, meet_code, race_num, venue_name)
                if rows:
                    save_to_db(rows, meet_code)
                    total += len(rows)
                    print(f"  ✅ R{race_num} — {len(rows)} horses (with jockey/trainer)")

            time.sleep(0.2)

        print()

    print(f"✅ Done — {total} horses saved\n")

if __name__ == "__main__":
    print("🚀 JordyMac Enhanced Scraper (v2)!")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            scrape_all_races()
            print("⏳ Waiting 60 seconds...\n")
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)
