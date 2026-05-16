import requests
from bs4 import BeautifulSoup

url = "https://example.com"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)

print("STATUS CODE:")
print(response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

print("\nPAGE TITLE:\n")

print(soup.title.text)