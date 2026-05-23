import pandas as pd
import numpy as np


# -----------------------------
# 1. BLENDED PROBABILITY
# -----------------------------
def blended_probability(df):
    """
    Combines ML + market + ratings into a single probability view.
    """

    ml = df.get("predicted_win_prob", 0.0)

    market_prob = 1 / df.get("current_odds", 1.0)

    rating_prob = 1 / df.get("fair_odds", 1.0)

    # weighted blend (can tune later)
    prob = (
        (ml * 0.5) +
        (market_prob * 0.25) +
        (rating_prob * 0.25)
    )

    return prob.clip(0.01, 0.95)


# -----------------------------
# 2. FAIR PRICE ENGINE (YOUR "BULLET PRICE")
# -----------------------------
def fair_price(df):
    prob = blended_probability(df)
    return (1 / prob).round(2)


# -----------------------------
# 3. EDGE CALCULATION
# -----------------------------
def calculate_edge(df):
    fair = fair_price(df)
    market = df["current_odds"]

    return ((fair - market) / market) * 100


# -----------------------------
# 4. RACE INTELLIGENCE SCORING
# -----------------------------
def intelligence_score(df):
    score = (
        df["predicted_win_prob"] * 40 +
        (1 / df["current_odds"]) * 25 +
        (df.get("is_favorite", 0)) * 10 +
        (df.get("jockey_win_rate", 0) / 100) * 10 +
        (df.get("trainer_win_rate", 0) / 100) * 10
    )

    return score


# -----------------------------
# 5. BETTING DECISION ENGINE
# -----------------------------
def betting_signal(df):
    edge = calculate_edge(df)

    signals = []

    for e in edge:
        if e >= 25:
            signals.append("🔥 STRONG OVERLAY")
        elif e >= 10:
            signals.append("⚡ VALUE BET")
        elif e <= -15:
            signals.append("❌ UNDERLAY FAVOURITE")
        elif e <= -5:
            signals.append("⚠️ AVOID")
        else:
            signals.append("—")

    return signals


# -----------------------------
# 6. MAIN ENGINE OUTPUT
# -----------------------------
def run_race_intelligence(df):
    df = df.copy()

    df["Blended Prob"] = blended_probability(df)
    df["Fair Odds"] = fair_price(df)
    df["Edge %"] = calculate_edge(df)
    df["Intelligence Score"] = intelligence_score(df)
    df["Bet Signal"] = betting_signal(df)

    df = df.sort_values("Intelligence Score", ascending=False)

    return df