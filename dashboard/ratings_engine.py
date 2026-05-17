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


def find_column(df, possible_names):
    """
    Finds the first matching column from a list of possible names.
    This lets us handle messy racing CSVs with different headers.
    """
    lower_columns = {
        str(col).lower().strip(): col for col in df.columns
    }

    for name in possible_names:
        clean_name = name.lower().strip()

        if clean_name in lower_columns:
            return lower_columns[clean_name]

    return None


def normalise_score(series, higher_is_better=True):
    """
    Converts a numeric column into a 0-10 score.
    """
    series = clean_number_column(series)

    if series.dropna().empty:
        return pd.Series([5] * len(series))

    min_value = series.min()
    max_value = series.max()

    if min_value == max_value:
        return pd.Series([5] * len(series))

    score = ((series - min_value) / (max_value - min_value)) * 10

    if not higher_is_better:
        score = 10 - score

    return score.fillna(5)


def create_basic_rating(df):
    """
    Basic JordyMac model v1.

    This tries to use:
    - Market odds / price
    - Barrier / BP
    - Weight / WT
    - Jockey rating / JRat
    - Trainer rating / TRat

    If columns are missing, it uses neutral scores.
    """
    df = df.copy()

    odds_col = find_column(
        df,
        [
            "Market Odds",
            "Odds",
            "Price",
            "Win Odds",
            "Fixed Odds",
            "Live Odds"
        ]
    )

    barrier_col = find_column(
        df,
        [
            "Barrier",
            "BP",
            "Bar",
            "Gate"
        ]
    )

    weight_col = find_column(
        df,
        [
            "Weight",
            "WT",
            "Wgt"
        ]
    )

    jockey_rating_col = find_column(
        df,
        [
            "JRat",
            "Jockey Rating",
            "Jockey Rating Score",
            "Jockey Score"
        ]
    )

    trainer_rating_col = find_column(
        df,
        [
            "TRat",
            "Trainer Rating",
            "Trainer Rating Score",
            "Trainer Score"
        ]
    )

    # MARKET SCORE
    # Shorter odds usually indicate market respect.
    if odds_col is not None:
        market_score = normalise_score(
            df[odds_col],
            higher_is_better=False
        )
    else:
        market_score = pd.Series([5] * len(df))

    # BARRIER SCORE
    # Early simple rule: lower barriers get a small edge.
    if barrier_col is not None:
        barrier_score = normalise_score(
            df[barrier_col],
            higher_is_better=False
        )
    else:
        barrier_score = pd.Series([5] * len(df))

    # WEIGHT SCORE
    # Lower weight gets a small edge.
    if weight_col is not None:
        weight_score = normalise_score(
            df[weight_col],
            higher_is_better=False
        )
    else:
        weight_score = pd.Series([5] * len(df))

    # JOCKEY SCORE
    if jockey_rating_col is not None:
        jockey_score = normalise_score(
            df[jockey_rating_col],
            higher_is_better=True
        )
    else:
        jockey_score = pd.Series([5] * len(df))

    # TRAINER SCORE
    if trainer_rating_col is not None:
        trainer_score = normalise_score(
            df[trainer_rating_col],
            higher_is_better=True
        )
    else:
        trainer_score = pd.Series([5] * len(df))

    # POSITION SCORE
    # Small fallback based on file order.
    position_score = pd.Series(
        [max(1, 10 - (i * 0.6)) for i in range(len(df))]
    )

    # WEIGHTED MODEL
    rating = (
        (market_score * 0.35) +
        (barrier_score * 0.15) +
        (weight_score * 0.10) +
        (jockey_score * 0.15) +
        (trainer_score * 0.15) +
        (position_score * 0.10)
    )

    # Convert 0-10 model into rating scale roughly 40-95
    final_rating = 40 + (rating * 5.5)

    final_rating = final_rating.clip(
        lower=40,
        upper=95
    )

    return final_rating.round(1)


def calculate_fair_odds(rating_series):
    """
    Converts rating into a rough fair odds estimate.

    Better rating = shorter price.
    """
    rating_series = clean_number_column(rating_series)

    fair_odds = 100 / rating_series

    return fair_odds.round(2)


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