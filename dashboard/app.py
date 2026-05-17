import os
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
# SYSTEM HEALTH CHECK
# -----------------------------
with st.expander("System Health Check 🛠️"):

    health_checks = []

    # Check app.py
    health_checks.append(
        {
            "Check": "dashboard/app.py exists",
            "Status": "✅ PASS" if os.path.exists("dashboard/app.py") else "❌ FAIL"
        }
    )

    # Check ratings_engine.py
    health_checks.append(
        {
            "Check": "dashboard/ratings_engine.py exists",
            "Status": "✅ PASS" if os.path.exists("dashboard/ratings_engine.py") else "❌ FAIL"
        }
    )

    # Check database
    health_checks.append(
        {
            "Check": "database/racing.db exists",
            "Status": "✅ PASS" if os.path.exists("database/racing.db") else "❌ FAIL"
        }
    )

    # Check database tables
    try:

        conn_check = sqlite3.connect("database/racing.db")

        table_check = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table'",
            conn_check
        )

        conn_check.close()

        health_checks.append(
            {
                "Check": "SQLite database opens",
                "Status": "✅ PASS"
            }
        )

        health_checks.append(
            {
                "Check": "Database table count",
                "Status": str(len(table_check))
            }
        )

    except Exception as error:

        health_checks.append(
            {
                "Check": "SQLite database opens",
                "Status": f"❌ FAIL: {error}"
            }
        )

    health_df = pd.DataFrame(health_checks)

    st.dataframe(health_df)

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
# MODEL WEIGHT CONTROLS
# -----------------------------
with st.sidebar.expander("Model Weights ⚖️"):

    market_weight = st.slider(
        "Market Weight",
        min_value=0,
        max_value=100,
        value=35,
        step=5,
        key="market_weight"
    )

    barrier_weight = st.slider(
        "Barrier Weight",
        min_value=0,
        max_value=100,
        value=15,
        step=5,
        key="barrier_weight"
    )

    weight_weight = st.slider(
        "Weight Carried Weight",
        min_value=0,
        max_value=100,
        value=10,
        step=5,
        key="weight_weight"
    )

    jockey_weight = st.slider(
        "Jockey Weight",
        min_value=0,
        max_value=100,
        value=15,
        step=5,
        key="jockey_weight"
    )

    trainer_weight = st.slider(
        "Trainer Weight",
        min_value=0,
        max_value=100,
        value=15,
        step=5,
        key="trainer_weight"
    )

    position_weight = st.slider(
        "File Order / Fallback Weight",
        min_value=0,
        max_value=100,
        value=10,
        step=5,
        key="position_weight"
    )

model_weights = {
    "market": market_weight,
    "barrier": barrier_weight,
    "weight": weight_weight,
    "jockey": jockey_weight,
    "trainer": trainer_weight,
    "position": position_weight
}


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

        mapped_df["Rating"] = create_basic_rating(
            df,
            weights=model_weights
        )

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
# MODEL SETTINGS DISPLAY
# -----------------------------
with st.expander("Current Model Settings 🧠"):

    st.write("These are the current weights being used by the automatic rating model.")

    weights_df = pd.DataFrame(
        {
            "Factor": [
                "Market",
                "Barrier",
                "Weight Carried",
                "Jockey",
                "Trainer",
                "File Order / Fallback"
            ],
            "Weight": [
                model_weights["market"],
                model_weights["barrier"],
                model_weights["weight"],
                model_weights["jockey"],
                model_weights["trainer"],
                model_weights["position"]
            ]
        }
    )

    st.dataframe(weights_df)


# -----------------------------
# WIN EXECUTION EXPLAINER
# -----------------------------
with st.expander("Win Execution Score 🧠"):

    st.write(
        "This score estimates how cleanly a runner can actually win. "
        "It currently uses market confidence, barrier/gate risk, weight carried, "
        "and overlay status where those columns are available."
    )

    execution_df = df[
        [
            "Horse",
            "Rating",
            "Confidence",
            "Win Execution",
            "Fair Odds",
            "Market Odds",
            "Overlay"
        ]
    ].sort_values(
        by="Win Execution",
        ascending=False
    )

    st.dataframe(execution_df)


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

best_execution = df.sort_values(
    by="Win Execution",
    ascending=False
).iloc[0]


col1, col2, col3, col4 = st.columns(4)

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

with col4:

    st.metric(
        "Best Execution",
        best_execution["Horse"]
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
# TOP 4 SELECTIONS
# -----------------------------
st.subheader("Top 4 Selections 🏆")

top_4 = df.head(4).reset_index(drop=True)

selection_cols = st.columns(4)

for i, col in enumerate(selection_cols):

    if i < len(top_4):

        runner = top_4.iloc[i]

        with col:

            st.metric(
                label=f"#{i + 1}",
                value=runner["Horse"]
            )

            st.write(f"Rating: {runner['Rating']}")
            st.write(f"Fair Odds: {runner['Fair Odds']}")
            st.write(f"Market Odds: {runner['Market Odds']}")
            st.write(f"Confidence: {runner['Confidence']}/10")
            st.write(f"Win Execution: {runner['Win Execution']}/10")

            if runner["Overlay"]:

                st.success("Overlay ✅")

            else:

                st.error("No Overlay ❌")


# -----------------------------
# RACE SUMMARY
# -----------------------------
st.subheader("Race Summary 📝")

top_pick_preview = df.iloc[0]

if overlay_count >= 2:

    race_summary = "This race has multiple overlay chances. The model sees possible market weakness."

elif top_pick_preview["Rating"] >= 90:

    race_summary = "The model has found a clear top-rated runner with strong win confidence."

elif market_percentage >= 120:

    race_summary = "This market looks high-overround or potentially compressed. Be careful forcing a bet."

else:

    race_summary = "This race looks moderate. Use the Top Pick and Value Pick carefully."

st.write(race_summary)


# -----------------------------
# BET / NO BET WARNING
# -----------------------------
st.subheader("Bet / No Bet Read 🚦")

if top_pick_preview["Confidence"] >= 9 and top_pick_preview["Win Execution"] >= 8:

    st.success("BET RACE ✅ Strong rating and strong win execution profile.")

elif top_pick_preview["Confidence"] >= 8 and top_pick_preview["Win Execution"] >= 7:

    st.info("WATCH / POSSIBLE BET 👀 Strong top pick, but check price and map carefully.")

elif overlay_count >= 1 and best_overlay["Overlay %"] >= 20:

    st.info("VALUE WATCH 💰 There is an overlay, but win execution still needs checking.")

else:

    st.warning("NO BET LEAN ❌ Confidence or win execution is not strong enough yet.")


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
# -----------------------------
# RESULTS TRACKER
# -----------------------------
st.subheader("Results Tracker 📈")

if os.path.exists("results.csv"):

    results_df = pd.read_csv("results.csv")

    st.dataframe(results_df)

    total_profit = results_df["Profit"].sum()

    total_staked = results_df["Stake"].sum()

    if total_staked > 0:

        roi = round((total_profit / total_staked) * 100, 2)

    else:

        roi = 0

    result_col1, result_col2, result_col3 = st.columns(3)

    with result_col1:

        st.metric(
            "Total Profit",
            f"{round(total_profit, 2)} units"
        )

    with result_col2:

        st.metric(
            "Total Staked",
            f"{round(total_staked, 2)} units"
        )

    with result_col3:

        st.metric(
            "ROI",
            f"{roi}%"
        )

    if total_profit > 0:

        st.success("Current results are profitable ✅")

    elif total_profit == 0:

        st.info("Results are break-even so far.")

    else:

        st.error("Current results are negative ❌")

else:

    st.info("No results.csv file found yet.")
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

st.write(
    f"Win Execution: {top_pick['Win Execution']}/10"
)

if top_pick["Rating"] >= 90 and top_pick["Win Execution"] >= 8:

    st.write("BET: YES ✅")

elif top_pick["Rating"] >= 85:

    st.write("BET: WATCH PRICE 👀")

else:

    st.write("BET: NO ❌")