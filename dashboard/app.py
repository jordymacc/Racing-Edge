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
    calculate_fair_odds,
    apply_v2_context_adjustments,
    apply_v23_template_scoring,
    apply_manual_speed_map,
)
from ratings_engine import (
    analyse_race,
    clean_number_column,
    create_basic_rating,
    calculate_fair_odds,
    apply_v2_context_adjustments,
    apply_v23_template_scoring,
    apply_manual_speed_map,
)
# -----------------------------
# SAFE APP COLUMN HELPER
# -----------------------------
def ensure_app_columns(dataframe):
    safe_df = dataframe.copy()

    default_values = {
        "Horse": "",
        "Rating": 0,
        "Confidence": 0,
        "Win Execution": 0,
        "Fair Odds": 0,
        "Market Odds": 0,
        "Overlay": False,
        "Overlay %": 0,
        "Bet Call": "NO BET ❌",
        "Model Notes": "No model notes available",
        "V2 Adjustment": 0,
        "Race Context": "",
        "Odds Source": "Uploaded / Database Odds",
        "Map Score": 5,
        "Recent Form Score": 5,
        "Track Suitability Score": 5,
        "Distance Suitability Score": 5,
        "V2.3 Template Score": 5,
        "Map Position": "Neutral",
        "Map Source": "CSV / Default",
    }

    for column, default_value in default_values.items():

        if column not in safe_df.columns:

            safe_df[column] = default_value

    return safe_df
# -----------------------------
# SAFE TABLE VIEW HELPER
# -----------------------------
def safe_view(dataframe, columns):
    """
    Safely selects columns for dashboard tables.
    If a column is missing, ensure_app_columns creates it first.
    """

    safe_df = ensure_app_columns(dataframe)

    for column in columns:

        if column not in safe_df.columns:

            safe_df[column] = ""

    return safe_df[columns]
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
# VERSION 2 RACE CONTEXT CONTROLS
# -----------------------------
with st.sidebar.expander("V2 Race Context 🧠"):

    track_condition = st.selectbox(
        "Track Condition",
        [
            "Good 3",
            "Good 4",
            "Soft 5",
            "Soft 6",
            "Soft 7",
            "Heavy 8",
            "Heavy 9",
            "Heavy 10"
        ],
        key="v2_track_condition"
    )

    race_distance = st.number_input(
        "Race Distance (metres)",
        min_value=800,
        max_value=4000,
        value=1200,
        step=100,
        key="v2_race_distance"
    )

    race_pressure = st.selectbox(
        "Race Pressure",
        [
            "Low",
            "Even",
            "High"
        ],
        key="v2_race_pressure"
    )

race_context = {
    "track_condition": track_condition,
    "distance": race_distance,
    "race_pressure": race_pressure
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
# VERSION 2 CSV TEMPLATE + VALIDATOR
# -----------------------------
with st.expander("Version 2 CSV Template + Upload Validator 📄"):

    st.write(
        "Download the clean race template, or inspect the uploaded CSV to see "
        "which columns are found, missing, or extra."
    )

    template_df = create_race_template()

    template_csv = template_df.to_csv(index=False)

    st.download_button(
        label="Download Version 2 Race Template CSV",
        data=template_csv,
        file_name="race_template_v2.csv",
        mime="text/csv",
        key="download_v2_race_template"
    )

    if uploaded_file is not None:

        st.write("### Uploaded CSV Column Validation")

        validation = validate_uploaded_csv(df)

        st.dataframe(
            validation["validation_table"],
            use_container_width=True
        )

        if len(validation["missing_columns"]) > 0:

            st.warning(
                f"Missing template columns: {validation['missing_columns']}"
            )

        else:

            st.success("Uploaded CSV matches the Version 2 template ✅")

        if len(validation["extra_columns"]) > 0:

            st.info(
                f"Extra columns found: {validation['extra_columns']}"
            )

        st.write("### Uploaded CSV Column Summary")

        column_summary = create_column_summary(df)

        st.dataframe(
            column_summary,
            use_container_width=True
        )

    else:

        st.info("Upload a CSV to see column validation.")

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
# VERSION 2 MANUAL LIVE ODDS UPDATER
# -----------------------------
with st.expander("Version 2 Manual Live Odds Updater 🔴"):

    st.write(
        "Edit the Market Odds below to reflect the latest prices you are seeing. "
        "Tick the apply box to push those odds into the model."
    )

    odds_editor_df = df[
        [
            "Horse",
            "Market Odds"
        ]
    ].copy()

    odds_editor_df["Market Odds"] = pd.to_numeric(
        odds_editor_df["Market Odds"],
        errors="coerce"
    ).fillna(0)

    edited_odds_df = st.data_editor(
        odds_editor_df,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="manual_live_odds_editor"
    )

    apply_manual_live_odds = st.checkbox(
        "Apply manual live odds to model",
        value=False,
        key="apply_manual_live_odds"
    )

    if apply_manual_live_odds:

        edited_odds_df["Market Odds"] = pd.to_numeric(
            edited_odds_df["Market Odds"],
            errors="coerce"
        ).fillna(0)

        odds_map = edited_odds_df.set_index("Horse")["Market Odds"].to_dict()

        df["Market Odds"] = df["Horse"].map(
            odds_map
        ).fillna(
            df["Market Odds"]
        )

        df["Odds Source"] = "Manual Live Odds"

        st.success("Manual live odds applied to the model ✅")

    else:

        df["Odds Source"] = "Uploaded / Database Odds"


# Apply Version 2 race context layer
df = apply_v2_context_adjustments(
    df,
    race_context
)
# -----------------------------
# VERSION 2.4 MANUAL SPEED MAP INPUT
# -----------------------------
with st.expander("Version 2.4 Manual Speed Map Input 🐎"):

    st.write(
        "Set each runner's expected race position. "
        "This feeds into the map score before the V2.3 template scoring runs."
    )

    if "Map Position" not in df.columns:
        df["Map Position"] = "Neutral"

    speed_map_editor_df = df[
        [
            "Horse",
            "Map Position"
        ]
    ].copy()

    speed_map_editor_df["Map Position"] = speed_map_editor_df["Map Position"].fillna("Neutral")

    edited_speed_map_df = st.data_editor(
        speed_map_editor_df,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="manual_speed_map_editor",
        column_config={
            "Map Position": st.column_config.SelectboxColumn(
                "Map Position",
                options=[
                    "Lead",
                    "On-speed",
                    "Handy",
                    "Midfield",
                    "Back",
                    "Wide",
                    "Neutral"
                ],
                required=True
            )
        }
    )

    apply_manual_map = st.checkbox(
        "Apply manual speed map to model",
        value=False,
        key="apply_manual_speed_map"
    )

    if apply_manual_map:

        df = apply_manual_speed_map(
            df,
            edited_speed_map_df
        )

        st.success("Manual speed map applied to model ✅")

    else:

        if "Map Source" not in df.columns:
            df["Map Source"] = "CSV / Default"
# Apply Version 2.3 clean-template scoring
df = apply_v23_template_scoring(df)

# Make sure all dashboard display columns exist
df = ensure_app_columns(df)

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
# VERSION 2.3 MODEL BREAKDOWN
# -----------------------------
with st.expander("Version 2.3 Template Scoring Breakdown 🧠"):

    st.write(
        "This shows how the uploaded clean-template fields are influencing the model."
    )

    v23_columns = [
        "Horse",
        "Rating",
        "V2.3 Template Score",
        "Map Position",
        "Map Source",
        "Map Score",
        "Recent Form Score",
        "Track Suitability Score",
        "Distance Suitability Score",
        "Fair Odds",
        "Market Odds",
        "Overlay",
        "Bet Call"
    ]

    v23_view = safe_view(
        df,
        v23_columns
    ).sort_values(
        by="V2.3 Template Score",
        ascending=False
    )

    st.dataframe(
        v23_view,
        use_container_width=True
    )
# -----------------------------
# CLEAN TABBED DASHBOARD
# -----------------------------
st.subheader("Race Dashboard Tabs 🧭")

# Make sure required dashboard columns exist
df = ensure_app_columns(df)

# Safety calculations
overlay_count = len(df[df["Overlay"] == True])

market_percentage = round(
    (100 / pd.to_numeric(df["Market Odds"], errors="coerce").replace(0, pd.NA)).sum(),
    2
)

top_pick_preview = df.sort_values(
    by="Rating",
    ascending=False
).iloc[0]

best_overlay = df.sort_values(
    by="Overlay %",
    ascending=False
).iloc[0]

best_execution = df.sort_values(
    by="Win Execution",
    ascending=False
).iloc[0]

overview_tab, ratings_tab, overlays_tab, execution_tab, downloads_tab = st.tabs(
    [
        "Overview 🏠",
        "Race Ratings 🐎",
        "Value / Overlays 💰",
        "Win Execution 🧠",
        "Downloads 📥"
    ]
)

with overview_tab:

    st.subheader("Overview 🏠")

    overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)

    with overview_col1:
        st.metric("Top Pick", top_pick_preview["Horse"])

    with overview_col2:
        st.metric("Top Rating", top_pick_preview["Rating"])

    with overview_col3:
        st.metric("Market %", f"{market_percentage}%")

    with overview_col4:
        st.metric("Overlay Count", overlay_count)

    st.write("### Quick Race Read")

    if top_pick_preview["Confidence"] >= 9 and top_pick_preview["Win Execution"] >= 8:
        st.success("Strong race profile ✅ The top pick has both a strong rating and strong win execution.")

    elif overlay_count >= 2:
        st.info("This race has multiple overlay chances 💰 The market may have missed something.")

    elif market_percentage >= 120:
        st.warning("High market percentage ⚠️ Be careful forcing a bet in a high-overround market.")

    else:
        st.info("Moderate race profile. Treat this as a watch race unless price is attractive.")

with ratings_tab:

    st.subheader("Race Ratings 🐎")

    ratings_columns = [
        "Horse",
        "Rating",
        "Confidence",
        "Win Execution",
        "Fair Odds",
        "Market Odds",
        "Odds Source",
        "Overlay",
        "Overlay %",
        "Bet Call",
        "Model Notes"
    ]

    ratings_view = safe_view(
        df,
        ratings_columns
    ).sort_values(
        by="Rating",
        ascending=False
    )

    st.dataframe(
        ratings_view,
        use_container_width=True
    )

    st.write("### Top 4 Rated")

    top_4_tab = ratings_view.head(4).reset_index(drop=True)

    top_cols = st.columns(4)

    for i, col in enumerate(top_cols):

        if i < len(top_4_tab):

            runner = top_4_tab.iloc[i]

            with col:

                st.metric(f"#{i + 1}", runner["Horse"])
                st.write(f"Rating: {runner['Rating']}")
                st.write(f"Confidence: {runner['Confidence']}/10")
                st.write(f"Win Execution: {runner['Win Execution']}/10")
                st.write(f"Call: {runner['Bet Call']}")
                st.write(runner["Model Notes"])

with overlays_tab:

    st.subheader("Value / Overlays 💰")

    overlay_df = df[df["Overlay"] == True].sort_values(
        by="Overlay %",
        ascending=False
    )

    overlay_columns = [
        "Horse",
        "Rating",
        "Fair Odds",
        "Market Odds",
        "Odds Source",
        "Overlay %",
        "Confidence",
        "Win Execution",
        "Bet Call",
        "Model Notes"
    ]

    if overlay_df.empty:

        st.warning("No overlays found in this race.")

    else:

        st.success(f"{len(overlay_df)} overlay runner(s) found ✅")

        st.dataframe(
            safe_view(
                overlay_df,
                overlay_columns
            ),
            use_container_width=True
        )

        st.metric("Best Overlay", best_overlay["Horse"])
        st.write(f"Best Overlay Price Gap: {best_overlay['Overlay %']}%")

with execution_tab:

    st.subheader("Win Execution 🧠")

    execution_columns = [
        "Horse",
        "Rating",
        "Confidence",
        "Win Execution",
        "Fair Odds",
        "Market Odds",
        "Overlay",
        "Bet Call",
        "Model Notes"
    ]

    execution_view = safe_view(
        df,
        execution_columns
    ).sort_values(
        by="Win Execution",
        ascending=False
    )

    st.dataframe(
        execution_view,
        use_container_width=True
    )

    st.metric("Best Win Execution", best_execution["Horse"])

    st.write(
        "Win Execution estimates how cleanly a runner can actually win. "
        "This early version uses market confidence, barrier/gate risk, weight carried, "
        "and overlay status where available."
    )

with downloads_tab:

    st.subheader("Downloads 📥")

    tab_csv_output = df.to_csv(index=False)

    st.download_button(
        label="Download Current Analysed Race CSV",
        data=tab_csv_output,
        file_name="current_analysed_race.csv",
        mime="text/csv",
        key="tab_download_current_race"
    )

    if st.button("Save Current Analysed Race to Database", key="tab_save_current_race"):

        conn = sqlite3.connect("database/racing.db")

        safe_table_name = race.lower().replace(" ", "_")

        df.to_sql(
            f"analysed_{safe_table_name}",
            conn,
            if_exists="replace",
            index=False
        )

        conn.close()

        st.success("Current analysed race saved to database ✅")
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
# VERSION 2 CONTEXT DISPLAY
# -----------------------------
with st.expander("Version 2 Race Context 🧠"):

    st.write("These race-level settings are now being applied to the model.")

    context_df = pd.DataFrame(
        [
            {
                "Track Condition": race_context["track_condition"],
                "Distance": race_context["distance"],
                "Race Pressure": race_context["race_pressure"]
            }
        ]
    )

    st.dataframe(context_df)

    v2_view = df[
        [
            "Horse",
            "Rating",
            "V2 Adjustment",
            "Race Context",
            "Win Execution",
            "Bet Call",
            "Model Notes"
        ]
    ].sort_values(
        by="Rating",
        ascending=False
    )

    st.dataframe(v2_view)

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


## -----------------------------
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

            if "Bet Call" in runner:
                st.write(f"Call: {runner['Bet Call']}")

            if "Model Notes" in runner:
                st.write(runner["Model Notes"])

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
# BET LOGGER + RESULTS TRACKER
# -----------------------------
st.subheader("Bet Logger + Results Tracker 📈")

results_file = "results.csv"

results_columns = [
    "Date",
    "Race",
    "Horse",
    "Bet Type",
    "Stake",
    "Odds",
    "Result",
    "Profit"
]

# Create results.csv if it does not exist
if not os.path.exists(results_file):

    empty_results = pd.DataFrame(
        columns=results_columns
    )

    empty_results.to_csv(
        results_file,
        index=False
    )


# Load existing results
results_df = pd.read_csv(results_file)


# BET ENTRY FORM
with st.form("bet_logger_form"):

    st.write("Add a new bet/result")

    bet_col1, bet_col2 = st.columns(2)

    with bet_col1:

        bet_date = st.text_input(
            "Date",
            value=datetime.now().strftime("%Y-%m-%d")
        )

        bet_race = st.text_input(
            "Race",
            value=race
        )

        bet_horse = st.text_input(
            "Horse"
        )

        bet_type = st.selectbox(
            "Bet Type",
            [
                "Win",
                "Place",
                "Each-Way",
                "No Bet",
                "Watch Only"
            ]
        )

    with bet_col2:

        bet_stake = st.number_input(
            "Stake / Units",
            min_value=0.0,
            value=1.0,
            step=0.25
        )

        bet_odds = st.number_input(
            "Odds",
            min_value=0.0,
            value=1.0,
            step=0.10
        )

        bet_result = st.selectbox(
            "Result",
            [
                "Pending",
                "Win",
                "Lose",
                "Place"
            ]
        )

        bet_profit = st.number_input(
            "Profit / Loss",
            value=0.0,
            step=0.25
        )

    submitted_bet = st.form_submit_button(
        "Save Bet"
    )


if submitted_bet:

    if bet_horse.strip() == "":

        st.warning("Please enter a horse name before saving.")

    else:

        new_bet = pd.DataFrame(
            [
                {
                    "Date": bet_date,
                    "Race": bet_race,
                    "Horse": bet_horse,
                    "Bet Type": bet_type,
                    "Stake": bet_stake,
                    "Odds": bet_odds,
                    "Result": bet_result,
                    "Profit": bet_profit
                }
            ]
        )

        results_df = pd.concat(
            [
                results_df,
                new_bet
            ],
            ignore_index=True
        )

        results_df.to_csv(
            results_file,
            index=False
        )

        st.success("Bet saved to results tracker ✅")


# RELOAD RESULTS AFTER SAVE
results_df = pd.read_csv(results_file)


# CLEAN NUMBER COLUMNS
if not results_df.empty:

    results_df["Stake"] = pd.to_numeric(
        results_df["Stake"],
        errors="coerce"
    ).fillna(0)

    results_df["Odds"] = pd.to_numeric(
        results_df["Odds"],
        errors="coerce"
    ).fillna(0)

    results_df["Profit"] = pd.to_numeric(
        results_df["Profit"],
        errors="coerce"
    ).fillna(0)


# DISPLAY RESULTS
st.write("### Saved Betting Results")

if results_df.empty:

    st.info("No bets saved yet.")

else:

    st.dataframe(results_df)

    total_profit = results_df["Profit"].sum()

    total_staked = results_df["Stake"].sum()

    if total_staked > 0:

        roi = round(
            (total_profit / total_staked) * 100,
            2
        )

    else:

        roi = 0

    result_col1, result_col2, result_col3, result_col4 = st.columns(4)

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

    with result_col4:

        st.metric(
            "Bets Logged",
            len(results_df)
        )

    if total_profit > 0:

        st.success("Current results are profitable ✅")

    elif total_profit == 0:

        st.info("Results are break-even so far.")

    else:

        st.error("Current results are negative ❌")


# DOWNLOAD RESULTS
results_csv = results_df.to_csv(index=False)

st.download_button(
    label="Download Results CSV",
    data=results_csv,
    file_name="results.csv",
    mime="text/csv",
    key="download_results_csv"
)