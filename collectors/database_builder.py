import sqlite3
import pandas as pd

# CONNECT TO DATABASE
conn = sqlite3.connect("database/racing.db")

# LOAD FIRST CSV
df1 = pd.read_csv("race_files/pakenham_r1.csv")

# SAVE FIRST TABLE
df1.to_sql(
    "pakenham_r1",
    conn,
    if_exists="replace",
    index=False
)

# LOAD SECOND CSV
df2 = pd.read_csv("race_files/morphettville_r3.csv")

# SAVE SECOND TABLE
df2.to_sql(
    "morphettville_r3",
    conn,
    if_exists="replace",
    index=False
)

print("DATABASE UPDATED ✅")

conn.close()