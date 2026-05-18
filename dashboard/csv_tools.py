import pandas as pd


REQUIRED_TEMPLATE_COLUMNS = [
    "Horse",
    "Barrier",
    "Weight",
    "Jockey",
    "Trainer",
    "Market Odds",
    "Jockey Rating",
    "Trainer Rating",
    "Map Position",
    "Recent Form",
    "Track Suitability",
    "Distance Suitability"
]


def create_race_template():
    """
    Creates a clean Version 2 race upload template.
    """

    return pd.DataFrame(columns=REQUIRED_TEMPLATE_COLUMNS)


def validate_uploaded_csv(df):
    """
    Checks uploaded CSV against the Version 2 template.
    """

    found_columns = list(df.columns)

    missing_columns = [
        col for col in REQUIRED_TEMPLATE_COLUMNS
        if col not in found_columns
    ]

    extra_columns = [
        col for col in found_columns
        if col not in REQUIRED_TEMPLATE_COLUMNS
    ]

    validation_rows = []

    for col in REQUIRED_TEMPLATE_COLUMNS:

        validation_rows.append(
            {
                "Column": col,
                "Status": "✅ Found" if col in found_columns else "❌ Missing"
            }
        )

    return {
        "found_columns": found_columns,
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "validation_table": pd.DataFrame(validation_rows)
    }


def create_column_summary(df):
    """
    Shows simple information about each uploaded column.
    """

    rows = []

    for col in df.columns:

        rows.append(
            {
                "Column": col,
                "Non-empty Rows": df[col].notna().sum(),
                "Blank Rows": df[col].isna().sum(),
                "Example Value": df[col].dropna().iloc[0] if df[col].notna().sum() > 0 else ""
            }
        )

    return pd.DataFrame(rows)