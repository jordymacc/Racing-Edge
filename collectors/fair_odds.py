horses = [
    {
        "name": "Skyhook",
        "rating": 40,
        "market_odds": 3.50
    },

    {
        "name": "Karinska",
        "rating": 25,
        "market_odds": 5.00
    },

    {
        "name": "Buffalo",
        "rating": 15,
        "market_odds": 9.00
    }
]

print("\nFAIR ODDS MODEL:\n")

for horse in horses:

    name = horse["name"]
    rating = horse["rating"]
    market_odds = horse["market_odds"]

    probability = rating / 100

    fair_odds = round(1 / probability, 2)

    print(f"Horse: {name}")
    print(f"Rating: {rating}%")
    print(f"Fair Odds: ${fair_odds}")
    print(f"Market Odds: ${market_odds}")

    if fair_odds < market_odds:
        print("OVERLAY FOUND ✅")

    else:
        print("NO VALUE ❌")

    print("--------------------")