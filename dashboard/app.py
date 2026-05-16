import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import sqlite3
st.title("🐎 JordyMac Racing Engine")
st.write("Last Updated:", datetime.now())
st_autorefresh(interval=30000, key="refresh")

race = st.sidebar.selectbox(
    "Choose Race",
    [
        "Pakenham Race 1",
        "Morphettville Race 3"
    ]
)

# DATABASE TABLES
table_names = {
    "Pakenham Race 1": "pakenham_r1",
    "Morphettville Race 3": "morphettville_r3"
}

selected_table = table_names[race]

# CONNECT TO DATABASE
conn = sqlite3.connect("database/racing.db")

query = f"SELECT * FROM {selected_table}"

df = pd.read_sql(query, conn)

conn.close()

# SEARCH FILTER
# PAGE HEADER
st.header(race)

# SEARCH
search = st.text_input(
    "Search Horse",
    key="horse_search"
)

# FILTER
overlay_only = st.checkbox(
    "Show Overlays Only",
    key="overlay_filter"
)

# SEARCH FILTER
if search:

    df = df[
        df["Horse"].str.contains(search, case=False)
    ]

# OVERLAY CHECK
df["Overlay"] = df["Fair Odds"] < df["Market Odds"]

# CONFIDENCE SCORE
df["Confidence"] = round(df["Rating"] / 10, 1)

# OVERLAY %
df["Overlay %"] = round(
    ((df["Market Odds"] - df["Fair Odds"]) / df["Fair Odds"]) * 100,
    1
)

# SORT RUNNERS
df = df.sort_values(
    by="Rating",
    ascending=False
)

# OVERLAY FILTER
if overlay_only:

    df = df[df["Overlay"] == True]

# COLOUR ROWS
def colour_rows(row):

    if row["Overlay"]:
        return ["background-color: lightgreen"] * len(row)

    else:
        return ["background-color: #ffcccc"] * len(row)

# STYLE TABLE
styled_df = df.style.apply(
    colour_rows,
    axis=1
)

# DISPLAY TABLE
st.dataframe(styled_df)

# TOP PICK
top_pick = df.iloc[0]

# VALUE PICK
value_rows = df[df["Overlay"] == True]

if len(value_rows) > 0:
    value_pick = value_rows.iloc[0]["Horse"]
else:
    value_pick = "None"

# FINAL CALL
st.subheader("FINAL CALL ⭐")
st.metric(
    label="BEST BET",
    value=top_pick["Horse"]
)
st.success(f"Top Pick: {top_pick['Horse']}")

st.info(f"Value Pick: {value_pick}")

st.write("Confidence: 8.5/10")

if top_pick["Rating"] >= 90:
    st.write("BET: YES ✅")
else:
    st.write("BET: NO ❌")