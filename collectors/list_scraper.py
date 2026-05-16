import requests
from bs4 import BeautifulSoup

url = "https://example.com"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)

soup = BeautifulSoup(response.text, "html.parser")

paragraphs = soup.find_all("p")

print("PARAGRAPHS FOUND:\n")

for p in paragraphs:
    print(p.text)