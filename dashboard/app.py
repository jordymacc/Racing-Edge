import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import sqlite3
st.title("🐎 JordyMac Racing Engine")
st.write("Last Updated:", datetime.now())
st_autorefresh(interval=30000, key="refresh")

uploaded_file = st.file_uploader(
    "Upload Race CSV",
    type=["csv"]
)

if uploaded_file is not None:

    uploaded_df = pd.read_csv(uploaded_file)

    st.subheader("Uploaded Race CSV")

    st.dataframe(uploaded_df)
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
# STOP IF NO RUNNERS FOUND
if df.empty:

    st.warning("No runners found. Try changing the search or turning off overlay filter.")

    st.stop()
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
# DASHBOARD STATS
overlay_count = len(df[df["Overlay"] == True])

market_percentage = round(
    (100 / df["Market Odds"]).sum(),
    2
)

best_overlay = df.sort_values(
    by="Overlay %",
    ascending=False
).iloc[0]
# METRIC CARDS
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
    # BIG OVERLAY ALERT
if best_overlay["Overlay %"] >= 20:

    st.success(
        f"🔥 BIG OVERLAY FOUND: {best_overlay['Horse']} at {best_overlay['Market Odds']}"
    )

else:

    st.info("No major overlay above 20% in this race.")
    # DOWNLOAD ANALYSED RACE
csv_output = df.to_csv(index=False)

st.download_button(
    label="Download Analysed Race CSV",
    data=csv_output,
    file_name="analysed_race.csv",
    mime="text/csv"
)
# SIDEBAR STATS
st.sidebar.metric(
    "Overlays",
    overlay_count
)

st.sidebar.metric(
    "Market %",
    f"{market_percentage}%"
)
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