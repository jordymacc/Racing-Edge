horses = [
    {
        "name": "Skyhook",
        "my_price": 2.80,
        "market_price": 3.50
    },

    {
        "name": "Karinska",
        "my_price": 6.00,
        "market_price": 5.00
    },

    {
        "name": "Buffalo",
        "my_price": 7.00,
        "market_price": 9.00
    }
]

print("\nOVERLAY CHECKER:\n")

for horse in horses:

    name = horse["name"]
    my_price = horse["my_price"]
    market_price = horse["market_price"]

    print(f"Horse: {name}")
    print(f"My Price: ${my_price}")
    print(f"Market Price: ${market_price}")

    if my_price < market_price:
        print("VALUE BET ✅")

    else:
        print("NO VALUE ❌")

    print("-------------------")