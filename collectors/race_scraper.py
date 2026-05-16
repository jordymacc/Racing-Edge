from bs4 import BeautifulSoup

with open("fake_race.html", "r") as file:
    html = file.read()

soup = BeautifulSoup(html, "html.parser")

rows = soup.find_all("tr")

print("\nRACE DATA:\n")

for row in rows:
    columns = row.find_all("td")

    if columns:
        horse = columns[0].text
        barrier = columns[1].text
        odds = columns[2].text

        print(f"Horse: {horse}")
        print(f"Barrier: {barrier}")
        print(f"Odds: {odds}")
        print("----------------")