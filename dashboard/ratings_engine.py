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


def create_basic_rating(df, weights=None):
    """
    Basic JordyMac model v2.

    Uses adjustable weights from the Streamlit sidebar.

    Inputs it tries to use:
    - Market odds / price
    - Barrier / BP
    - Weight / WT
    - Jockey rating / JRat
    - Trainer rating / TRat
    - File order fallback
    """

    df = df.copy()

    if weights is None:

        weights = {
            "market": 35,
            "barrier": 15,
            "weight": 10,
            "jockey": 15,
            "trainer": 15,
            "position": 10
        }

    total_weight = sum(weights.values())

    if total_weight == 0:

        total_weight = 1

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

    if odds_col is not None:

        market_score = normalise_score(
            df[odds_col],
            higher_is_better=False
        )

    else:

        market_score = pd.Series([5] * len(df))

    if barrier_col is not None:

        barrier_score = normalise_score(
            df[barrier_col],
            higher_is_better=False
        )

    else:

        barrier_score = pd.Series([5] * len(df))

    if weight_col is not None:

        weight_score = normalise_score(
            df[weight_col],
            higher_is_better=False
        )

    else:

        weight_score = pd.Series([5] * len(df))

    if jockey_rating_col is not None:

        jockey_score = normalise_score(
            df[jockey_rating_col],
            higher_is_better=True
        )

    else:

        jockey_score = pd.Series([5] * len(df))

    if trainer_rating_col is not None:

        trainer_score = normalise_score(
            df[trainer_rating_col],
            higher_is_better=True
        )

    else:

        trainer_score = pd.Series([5] * len(df))

    position_score = pd.Series(
        [max(1, 10 - (i * 0.6)) for i in range(len(df))]
    )

    rating = (
        (market_score * weights["market"]) +
        (barrier_score * weights["barrier"]) +
        (weight_score * weights["weight"]) +
        (jockey_score * weights["jockey"]) +
        (trainer_score * weights["trainer"]) +
        (position_score * weights["position"])
    ) / total_weight

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


def calculate_win_execution_score(df):
    """
    Win Execution Score /10.

    Early version uses:
    - Market Odds
    - Barrier / BP if available
    - Weight / WT if available
    - Overlay status if available
    """

    score = pd.Series([5.0] * len(df))

    market_col = find_column(
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

    if market_col is not None:

        market_odds = clean_number_column(df[market_col])

        score = score + market_odds.apply(
            lambda x:
            1.5 if x <= 4
            else 1.0 if x <= 8
            else 0.3 if x <= 15
            else -0.5
        )

    if barrier_col is not None:

        barrier = clean_number_column(df[barrier_col])

        score = score + barrier.apply(
            lambda x:
            1.0 if x <= 6
            else 0.3 if x <= 10
            else -0.8
        )

    if weight_col is not None:

        weight = clean_number_column(df[weight_col])

        average_weight = weight.mean()

        score = score + weight.apply(
            lambda x:
            0.8 if x < average_weight
            else 0.2 if x == average_weight
            else -0.5
        )

    if "Overlay" in df.columns:

        score = score + df["Overlay"].apply(
            lambda x: 0.5 if x else 0
        )

    score = score.clip(
        lower=1,
        upper=10
    )

    return score.round(1)


def create_model_note(row):
    """
    Creates a simple written explanation for each runner.
    """

    rating = row.get("Rating", 0)
    fair_odds = row.get("Fair Odds", 0)
    market_odds = row.get("Market Odds", 0)
    overlay = row.get("Overlay", False)
    overlay_percent = row.get("Overlay %", 0)
    win_execution = row.get("Win Execution", 0)

    notes = []

    if rating >= 90:
        notes.append("Elite rating profile")
    elif rating >= 85:
        notes.append("Strong rating profile")
    elif rating >= 75:
        notes.append("Competitive rating")
    else:
        notes.append("Lower rating profile")

    if win_execution >= 8:
        notes.append("strong win execution")
    elif win_execution >= 7:
        notes.append("solid win execution")
    elif win_execution >= 6:
        notes.append("some execution risk")
    else:
        notes.append("high execution risk")

    if overlay and overlay_percent >= 20:
        notes.append("clear market overlay")
    elif overlay:
        notes.append("minor overlay")
    else:
        notes.append("not an overlay at current price")

    if market_odds <= fair_odds:
        notes.append("price looks tight")
    else:
        notes.append("price gives some room")

    return " + ".join(notes)


def create_bet_call(row):
    """
    Creates a simple betting call for each runner.
    """

    rating = row.get("Rating", 0)
    overlay = row.get("Overlay", False)
    overlay_percent = row.get("Overlay %", 0)
    win_execution = row.get("Win Execution", 0)

    if rating >= 90 and win_execution >= 8:
        return "WIN CONFIDENCE BET ✅"

    if rating >= 85 and win_execution >= 7 and overlay:
        return "BACK IF PRICE HOLDS ✅"

    if overlay and overlay_percent >= 20 and win_execution >= 6.5:
        return "VALUE WATCH 💰"

    if rating >= 85 and win_execution < 7:
        return "TOP PICK BUT EXECUTION RISK ⚠️"

    if overlay and win_execution < 6:
        return "PLACE / WATCH ONLY 👀"

    return "NO BET ❌"


def analyse_race(df):
    """
    Cleans race data, calculates:
    - Overlay
    - Confidence
    - Overlay %
    - Win Execution
    - Model Notes
    - Bet Call
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

    df["Win Execution"] = calculate_win_execution_score(df)

    df["Model Notes"] = df.apply(
        create_model_note,
        axis=1
    )

    df["Bet Call"] = df.apply(
        create_bet_call,
        axis=1
    )

    df = df.sort_values(
        by="Rating",
        ascending=False
    )

    return df
# -----------------------------
# VERSION 2 CONTEXT ADJUSTMENTS
# -----------------------------
def apply_v2_context_adjustments(df, race_context):
    """
    Version 2 race context layer.

    Uses race-level inputs:
    - Track condition
    - Distance
    - Race pressure

    Then adjusts:
    - Rating
    - Fair Odds
    - Overlay
    - Confidence
    - Model Notes
    - Bet Call
    """

    df = df.copy()

    track_condition = race_context.get("track_condition", "Good 4")
    distance = race_context.get("distance", 1200)
    race_pressure = race_context.get("race_pressure", "Even")

    df["V2 Adjustment"] = 0.0
    df["Race Context"] = f"{track_condition} | {distance}m | {race_pressure} pressure"

    # Make sure key columns exist
    if "Win Execution" not in df.columns:
        df["Win Execution"] = 5.0

    if "Model Notes" not in df.columns:
        df["Model Notes"] = "No model notes available"

    # -----------------------------
    # RACE PRESSURE LOGIC
    # -----------------------------
    if race_pressure == "High":

        df["V2 Adjustment"] = df["V2 Adjustment"] + df["Win Execution"].apply(
            lambda x:
            1.0 if x >= 8
            else 0.3 if x >= 7
            else -1.5 if x < 6
            else -0.5
        )

        df["Model Notes"] = df["Model Notes"] + " + High-pressure race: execution matters more"

    elif race_pressure == "Low":

        df["V2 Adjustment"] = df["V2 Adjustment"] + df["Win Execution"].apply(
            lambda x:
            0.5 if x >= 7
            else 0
        )

        df["Model Notes"] = df["Model Notes"] + " + Low-pressure race: tactical position may help"

    else:

        df["Model Notes"] = df["Model Notes"] + " + Even-pressure race profile"

    # -----------------------------
    # DISTANCE LOGIC
    # -----------------------------
    if distance >= 1800:

        df["V2 Adjustment"] = df["V2 Adjustment"] + df["Win Execution"].apply(
            lambda x:
            0.7 if x >= 8
            else -1.0 if x < 6
            else 0
        )

        df["Model Notes"] = df["Model Notes"] + " + Staying race: stamina/execution upgraded"

    elif distance <= 1200:

        df["V2 Adjustment"] = df["V2 Adjustment"] + df["Win Execution"].apply(
            lambda x:
            0.5 if x >= 8
            else -0.8 if x < 6
            else 0
        )

        df["Model Notes"] = df["Model Notes"] + " + Sprint race: clean run and tactical speed important"

    else:

        df["Model Notes"] = df["Model Notes"] + " + Middle-distance race profile"

    # -----------------------------
    # TRACK CONDITION LOGIC
    # -----------------------------
    if "Heavy" in track_condition:

        df["V2 Adjustment"] = df["V2 Adjustment"] + df["Win Execution"].apply(
            lambda x:
            0.5 if x >= 8
            else -1.2 if x < 6
            else -0.3
        )

        df["Model Notes"] = df["Model Notes"] + " + Heavy track: extra risk for poor execution profiles"

    elif "Soft" in track_condition:

        df["V2 Adjustment"] = df["V2 Adjustment"] + df["Win Execution"].apply(
            lambda x:
            0.3 if x >= 8
            else -0.6 if x < 6
            else 0
        )

        df["Model Notes"] = df["Model Notes"] + " + Soft track: wet-track suitability should be checked"

    else:

        df["V2 Adjustment"] = df["V2 Adjustment"] + df["Win Execution"].apply(
            lambda x:
            0.3 if x >= 8
            else 0
        )

        df["Model Notes"] = df["Model Notes"] + " + Good-track race profile"

    # -----------------------------
    # APPLY ADJUSTMENTS
    # -----------------------------
    df["Rating"] = (
        df["Rating"] + df["V2 Adjustment"]
    ).clip(
        lower=40,
        upper=95
    ).round(1)

    df["Confidence"] = round(
        df["Rating"] / 10,
        1
    )

    df["Fair Odds"] = round(
        100 / df["Rating"],
        2
    )

    df["Overlay"] = df["Fair Odds"] < df["Market Odds"]

    df["Overlay %"] = round(
        ((df["Market Odds"] - df["Fair Odds"]) / df["Fair Odds"]) * 100,
        1
    )

    df["Bet Call"] = df.apply(
        create_bet_call,
        axis=1
    )

    df = df.sort_values(
        by="Rating",
        ascending=False
    )

    return df
# -----------------------------
# VERSION 2.3 MODEL INPUT SCORING
# -----------------------------
def score_text_factor(value):
    """
    Converts simple text ratings into numeric scores.
    """

    value = str(value).lower().strip()

    if value in ["excellent", "elite", "very strong", "strong", "yes"]:
        return 10

    if value in ["good", "positive", "suited"]:
        return 8

    if value in ["fair", "neutral", "average", "ok"]:
        return 5

    if value in ["poor", "negative", "unsuited", "no"]:
        return 2

    return 5


def score_map_position(value):
    """
    Scores map position.
    """

    value = str(value).lower().strip()

    if value in ["lead", "leader", "on speed", "on-speed", "box seat"]:
        return 9

    if value in ["handy", "forward", "stalk", "stalking"]:
        return 8

    if value in ["midfield", "cover"]:
        return 6

    if value in ["back", "rear", "wide", "wide no cover"]:
        return 3

    return 5


def apply_v23_template_scoring(df):
    """
    Adds Version 2.3 scoring from clean template fields:
    - Map Position
    - Recent Form
    - Track Suitability
    - Distance Suitability
    """

    df = df.copy()

    if "Map Position" in df.columns:
        df["Map Score"] = df["Map Position"].apply(score_map_position)
    else:
        df["Map Score"] = 5

    if "Recent Form" in df.columns:
        df["Recent Form Score"] = df["Recent Form"].apply(score_text_factor)
    else:
        df["Recent Form Score"] = 5

    if "Track Suitability" in df.columns:
        df["Track Suitability Score"] = df["Track Suitability"].apply(score_text_factor)
    else:
        df["Track Suitability Score"] = 5

    if "Distance Suitability" in df.columns:
        df["Distance Suitability Score"] = df["Distance Suitability"].apply(score_text_factor)
    else:
        df["Distance Suitability Score"] = 5

    df["V2.3 Template Score"] = round(
        (
            (df["Map Score"] * 0.30) +
            (df["Recent Form Score"] * 0.30) +
            (df["Track Suitability Score"] * 0.20) +
            (df["Distance Suitability Score"] * 0.20)
        ),
        1
    )

    df["Rating"] = (
        df["Rating"] + ((df["V2.3 Template Score"] - 5) * 1.5)
    ).clip(
        lower=40,
        upper=95
    ).round(1)

    df["Confidence"] = round(
        df["Rating"] / 10,
        1
    )

    df["Fair Odds"] = round(
        100 / df["Rating"],
        2
    )

    df["Overlay"] = df["Fair Odds"] < df["Market Odds"]

    df["Overlay %"] = round(
        ((df["Market Odds"] - df["Fair Odds"]) / df["Fair Odds"]) * 100,
        1
    )

    df["Model Notes"] = (
        df["Model Notes"]
        + " + V2.3 template score applied: "
        + df["V2.3 Template Score"].astype(str)
    )

    df["Bet Call"] = df.apply(
        create_bet_call,
        axis=1
    )

    df = df.sort_values(
        by="Rating",
        ascending=False
    )

    return df
# -----------------------------
# VERSION 2.4 MANUAL SPEED MAP
# -----------------------------
def apply_manual_speed_map(df, speed_map_df):
    """
    Applies manually edited speed-map positions to the race dataframe.

    This updates:
    - Map Position
    - Map Source
    """

    df = df.copy()

    if speed_map_df is None or speed_map_df.empty:
        return df

    if "Horse" not in speed_map_df.columns or "Map Position" not in speed_map_df.columns:
        return df

    speed_map = speed_map_df.set_index("Horse")["Map Position"].to_dict()

    df["Map Position"] = df["Horse"].map(speed_map).fillna(
        df["Map Position"] if "Map Position" in df.columns else "Neutral"
    )

    df["Map Source"] = "Manual Speed Map"

    return df