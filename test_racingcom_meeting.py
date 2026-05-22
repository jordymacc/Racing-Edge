import requests

URL = "PASTE_YOUR_URL_HERE"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Origin": "https://www.racing.com",
    "Referer": "https://www.racing.com/",
}

r = requests.get(URL, headers=headers, timeout=30)
print("Status:", r.status_code)
print("First 300 chars:", r.text[:300])
