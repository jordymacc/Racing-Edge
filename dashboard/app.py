import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from ratings_engine import (
    analyse_race,
    clean_number_column,
    create_basic_rating,
    calculate_fair_odds
)


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

    mapped_df["Horse"] = df[horse_col].astype(str)

    if rating_col == auto_option:

        mapped_df["Rating"] = create_basic_rating(df)

    else:

        mapped_df["Rating"] = clean_number_column(df[rating_col])

    if fair_odds_col == auto_option:

        mapped_df["Fair Odds"] = calculate_fair_odds(mapped_df["Rating"])

    else:

        mapped_df["Fair Odds"] = clean_number_column(df[fair_odds_col])

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
# ANALYSE RACE
# -----------------------------
df = analyse_race(df)

if df.empty:

    st.warning("No valid runners found after analysing the data.")

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


if search:

    df = df[
        df["Horse"].str.contains(search, case=False, na=False)
    ]


if overlay_only:

    df = df[
        df["Overlay"] == True
    ]


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
# SAVE ANALYSED RACE TO DATABASE
# -----------------------------
if st.button("Save Analysed Race to Database"):

    conn = sqlite3.connect("database/racing.db")

    safe_table_name = race.lower().replace(" ", "_")

    df.to_sql(
        f"analysed_{safe_table_name}",
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()

    st.success("Analysed race saved to database ✅")

# -----------------------------
# VIEW SAVED ANALYSED RACES
# -----------------------------
st.subheader("Saved Analysed Races 🗄️")

try:

    conn = sqlite3.connect("database/racing.db")

    saved_tables = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'analysed_%'",
        conn
    )

    if saved_tables.empty:

        st.info("No analysed races saved yet.")

    else:

        saved_race_table = st.selectbox(
            "Choose a saved analysed race",
            saved_tables["name"].tolist(),
            key="saved_race_selector"
        )

        saved_df = pd.read_sql(
            f"SELECT * FROM {saved_race_table}",
            conn
        )

        st.dataframe(saved_df)

        saved_csv = saved_df.to_csv(index=False)

        st.download_button(
            label="Download Saved Race CSV",
            data=saved_csv,
            file_name=f"{saved_race_table}.csv",
            mime="text/csv",
            key="download_saved_race"
        )

    conn.close()

except Exception as error:

    st.warning("Could not load saved analysed races yet.")

    st.write(error)
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