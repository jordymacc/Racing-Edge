import pandas as pd
import numpy as np

def clamp(x, min_val=40, max_val=98):
    return max(min_val, min(max_val, x))

def normalise(series):
    series = series.fillna(series.mean() if hasattr(series, "mean") else 0)
    if series.max() == series.min():
        return pd.Series([0.5] * len(series))
    return (series - series.min()) / (series.max() - series.min())

def calculate_bullet_price_v2(df):
    df = df.copy()

    # FORM POWER
    df["form_power"] = (
        df.get("combined_form", 50) / 100
    )

    # MARKET EDGE
    df["implied_prob"] = 1 / df["current_odds"]
    df["market_edge"] = (1 - df["implied_prob"]).clip(-1, 1)

    df["steam_bonus"] = 0
    if "odds_change_pct" in df.columns:
        df["steam_bonus"] = df["odds_change_pct"].apply(
            lambda x: 0.1 if x < -10 else (-0.1 if x > 10 else 0)
        )

    df["market_index"] = df["market_edge"] + df["steam_bonus"]

    # STABILITY
    if "volatility" in df.columns:
        df["stability_index"] = 1 - normalise(df["volatility"])
    else:
        df["stability_index"] = 0.5

    # CONNECTIONS
    df["connections_index"] = (
        df.get("jockey_win_rate", 0) * 0.5 +
        df.get("trainer_win_rate", 0) * 0.5
    ) / 100

    # FINAL PRICE
    df["bullet_price_v2"] = (
        df["form_power"] * 0.30 +
        df["market_index"] * 0.30 +
        df["stability_index"] * 0.15 +
        df["connections_index"] * 0.25
    ) * 100

    df["bullet_price_v2"] = df["bullet_price_v2"].apply(clamp)

    # FAIR ODDS
    df["fair_odds_v2"] = 100 / df["bullet_price_v2"]

    # OVERLAY
    df["overlay_v2"] = df["fair_odds_v2"] < df["current_odds"]

    return df
