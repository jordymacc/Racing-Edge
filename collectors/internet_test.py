import requests

url = "https://www.racingaustralia.horse"

response = requests.get(url)

print("Website Status:")
print(response.status_code)

print("\nFirst 500 characters:\n")

print(response.text[:500])