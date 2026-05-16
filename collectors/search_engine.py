import requests
from bs4 import BeautifulSoup

url = "https://example.com"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)

soup = BeautifulSoup(response.text, "html.parser")

search_word = "domain"

paragraphs = soup.find_all("p")

print("\nSEARCH RESULTS:\n")

for p in paragraphs:
    text = p.text

    if search_word.lower() in text.lower():
        print(text)