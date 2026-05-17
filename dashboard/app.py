import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh


# -----------------------------
# PAGE SETUP
# -----------------------------
st.title("🐎 JordyMac Racing Engine")

st.write("Last Updated:", datetime.now())

st_autorefresh(interval=30000, key="refresh")


# -----------------------------
# CSV UPLOADER
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload Race CSV",
    type=["csv"],
    key="race_csv_uploader"
)


# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("Race Selector")

race = st.sidebar.selectbox(
    "Choose Race",
    [
        "Pakenham Race 1",
        "Morphettville Race 3"
    ],
    key="race_selector"
)


# -----------------------------
# DATABASE TABLES
# -----------------------------
table_names = {
    "Pakenham Race 1": "pakenham_r1",
    "Morphettville Race 3": "morphettville_r3"
}


# -----------------------------
# HELPER FUNCTION: CLEAN ODDS
# -----------------------------
def clean_number_column(series):
    return pd.to_numeric(
        series
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False),
        errors="coerce"
    )


# -----------------------------
# LOAD DATA
# -----------------------------
if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    st.success("Uploaded CSV is now being used for this race ✅")

else:

    selected_table = table_names[race]

    try:

        conn = sqlite3.connect("database/racing.db")

        query = f"SELECT * FROM {selected_table}"

        df = pd.read_sql(query, conn)

        conn.close()

    except Exception as error:

        st.error("Could not load the database race table.")

        st.write(error)

        st.stop()


# -----------------------------
# PAGE HEADER
# -----------------------------
st.header(race)


# -----------------------------
# COLUMN MAPPING
# -----------------------------
required_columns = [
    "Horse",
    "Rating",
    "Fair Odds",
    "Market Odds"
]

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns and uploaded_file is not None:

    st.warning("Your uploaded CSV needs mapping before analysis.")

    st.write("Preview of uploaded file:")

    st.dataframe(df.head())

    available_columns = list(df.columns)

    auto_option = "Create Automatically / Not In File"

    options = [auto_option] + available_columns

    horse_col = st.selectbox(
        "Which column contains horse names?",
        available_columns,
        key="map_horse_col"
    )

    rating_col = st.selectbox(
        "Which column contains your rating?",
        options,
        key="map_rating_col"
    )

    fair_odds_col = st.selectbox(
        "Which column contains fair odds / my price?",
        options,
        key="map_fair_odds_col"
    )

    market_odds_col = st.selectbox(
        "Which column contains market odds / live odds?",
        options,
        key="map_market_odds_col"
    )

    mapped_df = pd.DataFrame()

    # Horse name
    mapped_df["Horse"] = df[horse_col].astype(str)

    # Rating
    if rating_col == auto_option:

        mapped_df["Rating"] = [
            max(40, 90 - (i * 3)) for i in range(len(df))
        ]

    else:

        mapped_df["Rating"] = clean_number_column(df[rating_col])

    # Fair Odds / My Price
    if fair_odds_col == auto_option:

        mapped_df["Fair Odds"] = round(
            100 / mapped_df["Rating"],
            2
        )

    else:

        mapped_df["Fair Odds"] = clean_number_column(df[fair_odds_col])

    # Market Odds / Live Odds
    if market_odds_col == auto_option:

        mapped_df["Market Odds"] = mapped_df["Fair Odds"]

    else:

        mapped_df["Market Odds"] = clean_number_column(df[market_odds_col])

    df = mapped_df


# -----------------------------
# FINAL REQUIRED COLUMN CHECK
# -----------------------------
missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:

    st.error(
        f"Still missing required columns: {missing_columns}"
    )

    st.stop()


# -----------------------------
# CLEAN FINAL DATA
# -----------------------------
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

    st.warning("No valid runners found after cleaning the data.")

    st.stop()


# -----------------------------
# SEARCH + FILTERS
# -----------------------------
search = st.text_input(
    "Search Horse",
    key="horse_search"
)

overlay_only = st.checkbox(
    "Show Overlays Only",
    key="overlay_filter"
)


# -----------------------------
# SEARCH FILTER
# -----------------------------
if search:

    df = df[
        df["Horse"].str.contains(search, case=False, na=False)
    ]


# -----------------------------
# OVERLAY CHECK
# -----------------------------
df["Overlay"] = df["Fair Odds"] < df["Market Odds"]


# -----------------------------
# CONFIDENCE SCORE
# -----------------------------
df["Confidence"] = round(
    df["Rating"] / 10,
    1
)


# -----------------------------
# OVERLAY %
# -----------------------------
df["Overlay %"] = round(
    ((df["Market Odds"] - df["Fair Odds"]) / df["Fair Odds"]) * 100,
    1
)


# -----------------------------
# SORT RUNNERS
# -----------------------------
df = df.sort_values(
    by="Rating",
    ascending=False
)


# -----------------------------
# OVERLAY FILTER
# -----------------------------
if overlay_only:

    df = df[
        df["Overlay"] == True
    ]


# -----------------------------
# STOP IF NO RUNNERS FOUND
# -----------------------------
if df.empty:

    st.warning(
        "No runners found. Try changing the search or turning off overlay filter."
    )

    st.stop()


# -----------------------------
# COLOUR ROWS
# -----------------------------
def colour_rows(row):

    if row["Overlay"]:

        return ["background-color: lightgreen"] * len(row)

    else:

        return ["background-color: #ffcccc"] * len(row)


# -----------------------------
# DISPLAY TABLE
# -----------------------------
styled_df = df.style.apply(
    colour_rows,
    axis=1
)

st.dataframe(styled_df)


# -----------------------------
# DASHBOARD STATS
# -----------------------------
overlay_count = len(
    df[df["Overlay"] == True]
)

market_percentage = round(
    (100 / df["Market Odds"]).sum(),
    2
)

best_overlay = df.sort_values(
    by="Overlay %",
    ascending=False
).iloc[0]


# -----------------------------
# METRIC CARDS
# -----------------------------
col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Overlay Count",
        overlay_count
    )

with col2:

    st.metric(
        "Market %",
        f"{market_percentage}%"
    )

with col3:

    st.metric(
        "Best Overlay",
        best_overlay["Horse"]
    )


# -----------------------------
# BIG OVERLAY ALERT
# -----------------------------
if best_overlay["Overlay %"] >= 20:

    st.success(
        f"🔥 BIG OVERLAY FOUND: {best_overlay['Horse']} at {best_overlay['Market Odds']}"
    )

else:

    st.info(
        "No major overlay above 20% in this race."
    )


# -----------------------------
# DOWNLOAD ANALYSED RACE
# -----------------------------
csv_output = df.to_csv(index=False)

st.download_button(
    label="Download Analysed Race CSV",
    data=csv_output,
    file_name="analysed_race.csv",
    mime="text/csv"
)


# -----------------------------
# SIDEBAR STATS
# -----------------------------
st.sidebar.metric(
    "Overlays",
    overlay_count
)

st.sidebar.metric(
    "Market %",
    f"{market_percentage}%"
)


# -----------------------------
# TOP PICK
# -----------------------------
top_pick = df.iloc[0]


# -----------------------------
# VALUE PICK
# -----------------------------
value_rows = df[
    df["Overlay"] == True
]

if len(value_rows) > 0:

    value_pick = value_rows.iloc[0]["Horse"]

else:

    value_pick = "None"


# -----------------------------
# FINAL CALL
# -----------------------------
st.subheader("FINAL CALL ⭐")

st.metric(
    label="BEST BET",
    value=top_pick["Horse"]
)

st.success(
    f"Top Pick: {top_pick['Horse']}"
)

st.info(
    f"Value Pick: {value_pick}"
)

st.write(
    f"Confidence: {top_pick['Confidence']}/10"
)

if top_pick["Rating"] >= 90:

    st.write("BET: YES ✅")

else:

    st.write("BET: NO ❌")