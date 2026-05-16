horses = [
    {
        "name": "Skyhook",
        "rating": 92,
        "market_odds": 3.50
    },

    {
        "name": "Karinska",
        "rating": 88,
        "market_odds": 6.00
    },

    {
        "name": "Buffalo",
        "rating": 80,
        "market_odds": 5.00
    }
]

print("\nRACE RANKINGS:\n")

horses.sort(key=lambda x: x["rating"], reverse=True)

top_pick = horses[0]

value_pick = None

for horse in horses:

    fair_odds = round(100 / horse["rating"], 2)

    horse["fair_odds"] = fair_odds

    if fair_odds < horse["market_odds"]:
        value_pick = horse

for i, horse in enumerate(horses, start=1):

    print(f"{i}. {horse['name']}")
    print(f"Rating: {horse['rating']}")
    print(f"Fair Odds: ${horse['fair_odds']}")
    print(f"Market Odds: ${horse['market_odds']}")
    print("-------------------")

print("\nFINAL CALL ⭐")

print(f"Top Pick: {top_pick['name']}")

if value_pick:
    print(f"Value Pick: {value_pick['name']}")
else:
    print("Value Pick: None")