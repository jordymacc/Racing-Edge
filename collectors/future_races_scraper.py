import requests
import time
from datetime import datetime
from pathlib import Path
import os
import psycopg2

print("🔧 Future Races Scraper loaded")

DATABASE_URL = os.environ.get("DATABASE_URL")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Origin": "https://www.racing.com",
    "Referer": "https://www.racing.com/",
    "x-api-key": "da2-6nsi4ztsynar3l3frgxf77q5fe",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
}

def setup_table():
    if not DATABASE_URL:
        print("No DATABASE_URL found")
        return
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS future_races (
            id SERIAL PRIMARY KEY,
            scrape_timestamp TEXT,
            race_date TEXT,
            venue TEXT,
            state TEXT,
            meet_code TEXT,
            race_number INTEGER,
            race_name TEXT,
            horse_name TEXT,
            jockey_name TEXT,
            trainer_name TEXT,
            win_odds REAL,
            barrier INTEGER,
            UNIQUE(race_date, race_name, horse_name)
        )
    """)
    conn.commit()
    conn.close()
    print("✅ future_races table ready")

def get_meetings(days_forward=3):
    url = (
        "https://graphql.rmdprod.racing.com/?query=query%20getRaceMeetingsByState"
        "(%24daysForward%3A%20Int!%2C%20%24daysBack%3A%20Int!)%20%7B%0A%20%20"
        "GetRaceMeetingsByStateNew(%0A%20%20%20%20daysForward%3A%20%24daysForward%0A"
        "%20%20%20%20daysBack%3A%20%24daysBack%0A%20%20%20%20states%3A%20%22VIC%7C"
        "SA%7CQLD%7CNSW%7CWA%7CACT%7CNT%7CTAS%22%0A%20%20)%20%7B%0A%20%20%20%20id%0A"
        "%20%20%20%20racesCount%0A%20%20%20%20date%0A%20%20%20%20venue%0A%20%20%20%20"
        "state%0A%20%20%7D%0A%7D&operationName=getRaceMeetingsByState"
        f"&variables=%7B%22daysForward%22%3A{days_forward}%2C%22daysBack%22%3A0%7D"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("data", {}).get("GetRaceMeetingsByStateNew", [])
    except Exception as e:
        print(f"  ❌ Failed to get meetings: {e}")
        return []

def get_race_entries(meet_code, race_number):
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

def save_entries(entries, race_date, venue, state, meet_code, race_number):
    if not entries or not DATABASE_URL:
        return 0
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    race_name = f"{venue} R{race_number}"
    saved = 0
    for entry in entries:
        if entry.get("scratched"):
            continue
        horse = entry.get("horseName", "Unknown")
        jockey = entry.get("jockeyName")
        trainer = entry.get("trainerName")
        barrier = entry.get("barrierNumber")
        odds_list = entry.get("odds", [])
        win_odds = None
        for o in odds_list:
            if o.get("oddsWin"):
                try:
                    win_odds = float(str(o["oddsWin"]).replace("$",""))
                    break
                except:
                    pass
        try:
            cur.execute("""
                INSERT INTO future_races (
                    scrape_timestamp, race_date, venue, state, meet_code,
                    race_number, race_name, horse_name, jockey_name,
                    trainer_name, win_odds, barrier
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (race_date, race_name, horse_name)
                DO UPDATE SET
                    win_odds = EXCLUDED.win_odds,
                    scrape_timestamp = EXCLUDED.scrape_timestamp
            """, (now, race_date, venue, state, meet_code, race_number,
                  race_name, horse, jockey, trainer, win_odds, barrier))
            saved += 1
        except Exception as e:
            pass
    conn.commit()
    conn.close()
    return saved

def scrape_future_races():
    print(f"\n🔮 Scraping future races — {datetime.now().strftime('%H:%M:%S')}")
    meetings = get_meetings(days_forward=3)
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Australia/Melbourne")).strftime("%Y-%m-%d")
    future_meetings = [m for m in meetings if m.get("date", "") > today]
    print(f"  Found {len(future_meetings)} future meetings")
    total = 0
    for meeting in future_meetings:
        meet_code = meeting.get("id")
        venue = meeting.get("venue", "Unknown")
        state = meeting.get("state", "")
        race_date = meeting.get("date", "")
        races_count = meeting.get("racesCount", 8)
        print(f"  📅 {race_date} — {venue} ({state}) — {races_count} races")
        for race_num in range(1, races_count + 1):
            data = get_race_entries(meet_code, race_num)
            if data:
                entries = data.get("data",{}).get("getRaceForm",{}).get("formRaceEntries",[])
                saved = save_entries(entries, race_date, venue, state,
                                     meet_code, race_num)
                if saved > 0:
                    total += saved
            time.sleep(0.3)
    print(f"  ✅ Saved {total} future race entries")
    return total

if __name__ == "__main__":
    setup_table()
    scrape_future_races()
