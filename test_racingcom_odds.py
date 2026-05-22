import requests

URL = "https://graphql.rmdprod.racing.com/?query=query%20getRaceResults_CD(%24meetCode%3A%20ID!%20%24raceNumber%3A%20Int!)%20%7B%20getRaceForm(meetCode%3A%20%24meetCode%20raceNumber%3A%20%24raceNumber)%20%7B%20id%20meetCode%20venue%20%7B%20venueName%20state%20%7D%20raceNumber%20photoFinish%20raceStatus%20rdcClass%20isTrial%20isJumpOut%20videoItems%20%7B%20id%20contenttype%20poster%20%7D%20formRaceEntries%20%7B%20id%20meetCode%20raceNumber%20...RaceWithEntry%20gearHasChanges%20gearChanges%20lastGear%20lastGearDate%20finish%20horseName%20horseCode%20horseCountry%20horseUrl%20silkUrl%20comment%20commentStewards%20race%20%7B%20meet%20%7B%20meetUrl%20meetTips%20%7B%20longComment%20shortComment%20%7D%20%7D%20%7D%20horse%20%7B%20id%20lastFive%20silkUrl%20stats%20%7B%20key%20firsts%20starts%20thirds%20seconds%20%7D%20lastProfessionalRaceEntryItem%20%7B%20raceCode%20position%20race%20%7B%20runnersCount%20distance%20date%20venueAbbr%20%7D%20%7D%20%7D%20standardTimeDifference%20jockeyUrl%20jockeyName%20trainerUrl%20trainerCode%20jockeyCode%20trainerName%20positionAt400%20positionAt400Abv%20positionAt800%20positionAt800Abv%20bettingFluctuationsPriceOpen%20bettingFluctuationsPriceMoveOne%20bettingFluctuationsPriceMoveTwo%20bonusMoney%20%7D%20%7D%20GetBettingData(meetCode%3A%20%24meetCode%20raceNumber%3A%20%24raceNumber)%20%7B%20exotics%20%7B%20poolStatusCode%20wageringProduct%20selections%20amount%20%7D%20%7D%20%7D%20%7D%20fragment%20RaceWithEntry%20on%20RaceEntryItem%20%7B%20position%20barrierNumber%20liveBarrierNumber%20prizeMoney%20scratched%20startingPrice%20odds%20%7B%20id%20providerCode%20oddsPlace%20oddsWin%20oddsIsFavouriteWin%20oddsIsMarketMover%20deepLinkWin%20deepLinkPlace%20deepLinkRace%20flucsWin%20%7B%20updateTime%20amount%20%7D%20%7D%20comment%20commentShort%20commentStewards%20raceEntryNumber%20apprenticeCanClaim%20apprenticeAllowedClaim%20weight%20margin%20winningTime%20finish%20finishAbv%20%7D&variables=%7B%22meetCode%22%3A%225190899%22%2C%22raceNumber%22%3A1%7D"

def find_oddswin(obj, out):
    if isinstance(obj, dict):
        # if we find a horse, capture name + oddsWin (if present)
        if "horseName" in obj:
            horse = obj.get("horseName")
            # find oddsWin inside this dict tree
            odds = find_key_recursive(obj, "oddsWin")
            if odds is not None:
                out.append((horse, odds))
        for v in obj.values():
            find_oddswin(v, out)
    elif isinstance(obj, list):
        for item in obj:
            find_oddswin(item, out)

def find_key_recursive(x, key):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == key:
                return v
            res = find_key_recursive(v, key)
            if res is not None:
                return res
    elif isinstance(x, list):
        for item in x:
            res = find_key_recursive(item, key)
            if res is not None:
                return res
    return None

r = requests.get(URL, timeout=30)
r.raise_for_status()
data = r.json()

found = []
find_oddswin(data, found)

# de-dupe by horse name
dedup = {}
for horse, odds in found:
    try:
        dedup[horse] = float(odds)
    except:
        pass

print("Found horses with oddsWin:", len(dedup))
for i, (horse, odds) in enumerate(list(dedup.items())[:15], start=1):
    print(f"{i}. {horse}: {odds}")
