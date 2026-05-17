import pandas as pd


def clean_number_column(series):
    """
    Cleans messy number columns like:
    $3.50, 3.50, ' 3.50 ', commas, blanks, etc.
    """
    return pd.to_numeric(
        series
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False),
        errors="coerce"
    )


def create_basic_rating(df):
    """
    Temporary placeholder rating system.

    Runner 1 = 90
    Runner 2 = 87
    Runner 3 = 84
    etc.

    Later we will replace this with your real racing model.
    """
    ratings = []

    for i in range(len(df)):
        rating = max(40, 90 - (i * 3))
        ratings.append(rating)

    return ratings


def calculate_fair_odds(rating_series):
    """
    Converts rating into fair odds.

    Example:
    Rating 50 = $2.00
    Rating 25 = $4.00
    """
    return round(
        100 / rating_series,
        2
    )


def analyse_race(df):
    """
    Cleans race data, calculates:
    - Overlay
    - Confidence
    - Overlay %
    - Sorts by rating
    """
    df = df.copy()

    df["Horse"] = df["Horse"].astype(str)

    df["Rating"] = clean_number_column(df["Rating"])

    df["Fair Odds"] = clean_number_column(df["Fair Odds"])

    df["Market Odds"] = clean_number_column(df["Market Odds"])

    df = df.dropna(
        subset=[
            "Horse",
            "Rating",
            "Fair Odds",
            "Market Odds"
        ]
    )

    df = df[
        (df["Fair Odds"] > 0) &
        (df["Market Odds"] > 0)
    ]

    if df.empty:
        return df

    df["Overlay"] = df["Fair Odds"] < df["Market Odds"]

    df["Confidence"] = round(
        df["Rating"] / 10,
        1
    )

    df["Overlay %"] = round(
        ((df["Market Odds"] - df["Fair Odds"]) / df["Fair Odds"]) * 100,
        1
    )

    df = df.sort_values(
        by="Rating",
        ascending=False
    )

    return df