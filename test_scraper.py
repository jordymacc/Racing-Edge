print("START - Script is running!")

import requests
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Origin": "https://www.racing.com",
    "Referer": "https://www.racing.com/",
    "x-api-key": "da2-6nsi4ztsynar3l3frgxf77q5fe",
}

print("Step 1: Imports loaded")

today = datetime.now().strftime("%Y-%m-%d")
print(f"Step 2: Today is {today}")

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

print("Step 3: Making API request...")

try:
    r = requests.get(url, headers=HEADERS, timeout=30)
    print(f"Step 4: Got response - Status {r.status_code}")
    
    data = r.json()
    meetings = data.get("data", {}).get("GetRaceMeetingsByStateNew", [])
    
    print(f"Step 5: Found {len(meetings)} total meetings")
    
    todays = [m for m in meetings if m.get("date") == today]
    print(f"Step 6: {len(todays)} are today")
    
    for m in todays[:3]:  # Just show first 3
        print(f"  - {m.get('venue')} ({m.get('state')}) - {m.get('racesCount')} races")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("DONE!")
