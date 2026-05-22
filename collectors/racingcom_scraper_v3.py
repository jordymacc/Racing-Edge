import requests
import time
from datetime import datetime
from pathlib import Path
import sqlite3

print("🔧 Script loaded successfully (v3 - Track Conditions + Weather)")

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "racing.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Origin": "https://www.racing.com",
    "Referer": "https://www.racing.com/",
    "x-api-key": "da2-6nsi4ztsynar3l3frgxf77q5fe",
}

# Australian venue coordinates for weather lookup
VENUE_COORDS = {
    "Flemington": (-37.7895, 144.9063),
    "Caulfield": (-37.8770, 145.0415),
    "Moonee Valley": (-37.7515, 144.9271),
    "Sandown": (-37.9330, 145.1010),
    "Pakenham": (-38.0710, 145.4880),
    "Cranbourne": (-38.1010, 145.2830),
    "Bendigo": (-36.7570, 144.2794),
    "Ballarat": (-37.5622, 143.8503),
    "Geelong": (-38.1499, 144.3617),
    "Flemington": (-37.7895, 144.9063),
    "Gold Coast": (-28.0167, 153.4000),
    "Aquis Park": (-28.0167, 153.4000),
    "Mount Gambier": (-37.8318, 140.7832),
    "Kilcoy": (-26.9333, 152.5667),
    "Inverell": (-29.7667, 151.1167),
    "Canberra": (-35.2820, 149.1286),
    "Acton": (-35.2820, 149.1286),
    "Rockhampton": (-23.3791, 150.5100),
    "Rosehill": (-33.8310, 150.9960),
    "Eagle Farm": (-27.4298, 153.0760),
    "Doomben": (-27.4110, 153.0630),
    "Randwick": (-33.8960, 151.2180),
    "Rosehill": (-33.8310, 150.9960),
    "Warwick Farm": (-33.9120, 150.9340),
    "Hawkesbury": (-33.6070, 150.7940),
    "Kembla Grange": (-34.4760, 150.8230),
    "Morphettville": (-34.9710, 138.5540),
    "Murray Bridge": (-35.1190, 139.2730),
    "Ascot": (-31.9370, 115.9430),
    "Belmont": (-31.9560, 115.9680),
}

TRACK_CONDITION_SCORE = {
    "Firm": 1, "Good": 2, "Soft": 3, "Heavy": 4,
    "firm": 1, "good": 2, "soft": 3, "heavy": 4,
}

def get_weather(venue_name):
    """Get current weather for a venue using Open-Meteo (free, no API key)"""
    coords = None
    for key, val in VENUE_COORDS.items():
        if key.lower() in venue_name.lower():
            coords = val
            break

    if not coords:
        return None, None

    lat, lon = coords
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,precipitation,rain,wind_speed_10m"
            f"&timezone=Australia%2FSydney"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        current = data.get("current", {})
        temp = current.get("temperature_2m")
        rain = current.get("rain", 0)
        return temp, rain
    except:
        return None, None

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
    """Pull odds + track condition for a single race"""
    url = (
        f"https://graphql.rmdprod.racing.com/?query=query%20getRaceResults_CD"
        f"(%24meetCode%3A%20ID!%20%24raceNumber%3A%20Int!)%20%7B%20"
        f"getRaceForm(meetCode%3A%20%24meetCode%20raceNumber%3A%20%24raceNumber)%20"
        f"%7B%20trackCondition%20formRaceEntries%20%7B%20horseName%20scratched%20"
        f"barrierNumber%20jockeyName%20trainerName%20"
        f"odds%20%7B%20oddsWin%20oddsPlace%20%7D%20%7D%20%7D%20%7D"
        f"&variables=%7B%22meetCode%22%3A%22{meet_code}%22%2C%22raceNumber%22%3A{race_number}%7D"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except:
        return None

def parse_odds(data, meet_code, race_number, venue_name, temperature, rainfall):
    """Extract horse odds with track condition + weather"""
    rows = []
    try:
        race_form = data.get("data", {}).get("getRaceForm", {})
        entries = race_form.get("formRaceEntries", [])
        track_condition = race_form.get("trackCondition", None)
        track_condition_score = TRACK_CONDITION_SCORE.get(track_condition, None)
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
                        win_odds = float(str(odds_item["oddsWin"]).replace("$", ""))
                        place_str = odds_item.get("oddsPlace")
                        if place_str:
                            place_odds = float(str(place_str).replace("$", ""))
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
                "track_condition": track_condition,
                "track_condition_score": track_condition_score,
                "temperature": temperature,
                "rainfall": rainfall,
            })
    except:
        pass
    return rows

def save_to_db(rows, meet_code):
    """Save to database with track condition + weather"""
    if not rows:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add new columns if they don't exist yet
    for col, coltype in [
        ("track_condition", "TEXT"),
        ("track_condition_score", "REAL"),
        ("temperature", "REAL"),
        ("rainfall", "REAL"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE odds_snapshots ADD COLUMN {col} {coltype}")
        except:
            pass

    now = datetime.now().isoformat()

    for row in rows:
        cursor.execute("""
            INSERT INTO odds_snapshots (
                timestamp, race_name, horse_name, jockey_name, trainer_name,
                win_odds_racingcom, place_odds_racingcom, meet_code,
                track_condition, track_condition_score, temperature, rainfall
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            row.get("race_name"),
            row.get("horse_name"),
            row.get("jockey_name"),
            row.get("trainer_name"),
            row.get("win_odds_racingcom"),
            row.get("place_odds_racingcom"),
            meet_code,
            row.get("track_condition"),
            row.get("track_condition_score"),
            row.get("temperature"),
            row.get("rainfall"),
        ))

    conn.commit()
    conn.close()

def scrape_all_races():
    """Scrape everything with track conditions + weather"""
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

        # Get weather once per venue
        temperature, rainfall = get_weather(venue_name)
        weather_str = f"🌡️ {temperature}°C 🌧️ {rainfall}mm" if temperature else "weather N/A"
        print(f"📍 {venue_name} ({state}) — {races_count} races — {weather_str}")

        for race_num in range(1, races_count + 1):
            data = get_race_odds(meet_code, race_num)
            if data:
                rows = parse_odds(data, meet_code, race_num, venue_name, temperature, rainfall)
                if rows:
                    track = rows[0].get("track_condition") or "unknown"
                    save_to_db(rows, meet_code)
                    total += len(rows)
                    print(f"  ✅ R{race_num} — {len(rows)} horses — Track: {track}")
            time.sleep(0.2)
        print()

    print(f"✅ Done — {total} horses saved\n")

if __name__ == "__main__":
    print("🚀 JordyMac Scraper v3 — Track Conditions + Weather!")
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
