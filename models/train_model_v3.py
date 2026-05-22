import sqlite3
import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import LabelEncoder

# XGBoost
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("XGBoost not installed, using 2-model ensemble")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'database', 'racing.db')

print("Loading data from database...")
conn = sqlite3.connect(DB_PATH)

# Get odds snapshots with jockey/trainer stats
odds_df = pd.read_sql_query("""
    SELECT DISTINCT
        o.race_name,
        o.horse_name,
        o.win_odds_racingcom,
        o.jockey_name,
        o.trainer_name
    FROM odds_snapshots o
    WHERE o.win_odds_racingcom IS NOT NULL
""", conn)

# Get historical results
results_df = pd.read_sql_query("""
    SELECT DISTINCT race_name, horse_name, winner, placed
    FROM historical_results
""", conn)

# Get jockey stats
try:
    jockey_df = pd.read_sql_query("SELECT jockey_name, win_rate FROM jockey_stats", conn)
except:
    jockey_df = pd.DataFrame(columns=['jockey_name', 'win_rate'])

# Get trainer stats
try:
    trainer_df = pd.read_sql_query("SELECT trainer_name, win_rate FROM trainer_stats", conn)
except:
    trainer_df = pd.DataFrame(columns=['trainer_name', 'win_rate'])

conn.close()

print(f"Odds snapshots: {len(odds_df)}")
print(f"Historical results: {len(results_df)}")

# Merge odds with results
df = odds_df.merge(results_df, on=['race_name', 'horse_name'], how='inner')
print(f"Merged records: {len(df)}")

if len(df) < 50:
    print("Not enough merged data yet. Let the system collect more data and try again.")
    exit()

# Add jockey stats
df = df.merge(jockey_df[['jockey_name', 'win_rate']], on='jockey_name', how='left')
df.rename(columns={'win_rate': 'jockey_win_rate'}, inplace=True)

# Add trainer stats
df = df.merge(trainer_df[['trainer_name', 'win_rate']], on='trainer_name', how='left')
df.rename(columns={'win_rate': 'trainer_win_rate'}, inplace=True)

# Clean odds
df['win_odds_racingcom'] = df['win_odds_racingcom'].astype(str).str.replace('$', '').str.strip()
df['win_odds_racingcom'] = pd.to_numeric(df['win_odds_racingcom'], errors='coerce')
df = df.dropna(subset=['win_odds_racingcom'])
df = df[df['win_odds_racingcom'] > 1.0]

# Fill missing stats
df['jockey_win_rate'] = df['jockey_win_rate'].fillna(df['jockey_win_rate'].median())
df['trainer_win_rate'] = df['trainer_win_rate'].fillna(df['trainer_win_rate'].median())

# Feature engineering
df['implied_prob'] = 1 / df['win_odds_racingcom']
df['is_favorite'] = (df['win_odds_racingcom'] == df.groupby('race_name')['win_odds_racingcom'].transform('min')).astype(int)
df['market_rank'] = df.groupby('race_name')['win_odds_racingcom'].rank()
df['combined_form'] = df['jockey_win_rate'] * 0.5 + df['trainer_win_rate'] * 0.5
df['jockey_odds_interaction'] = df['jockey_win_rate'] * df['implied_prob']
df['trainer_odds_interaction'] = df['trainer_win_rate'] * df['implied_prob']

# Features
FEATURES = [
    'win_odds_racingcom', 'implied_prob', 'is_favorite', 'market_rank',
    'jockey_win_rate', 'trainer_win_rate', 'combined_form',
    'jockey_odds_interaction', 'trainer_odds_interaction'
]

X = df[FEATURES].fillna(0)
y = df['winner'].fillna(0).astype(int)

print(f"\nTraining data: {len(X)} horses, {y.sum()} winners ({y.mean()*100:.1f}% win rate)")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Build ensemble
gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42)
rf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)

if XGBOOST_AVAILABLE:
    xgb = XGBClassifier(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42, eval_metric='logloss')
    estimators = [('gb', gb), ('rf', rf), ('xgb', xgb)]
    print("\nBuilding 3-model ensemble (GB + RF + XGBoost)...")
else:
    estimators = [('gb', gb), ('rf', rf)]
    print("\nBuilding 2-model ensemble (GB + RF)...")

ensemble = VotingClassifier(estimators=estimators, voting='soft')
ensemble.fit(X_train, y_train)

# Evaluate
y_pred = ensemble.predict(X_test)
y_prob = ensemble.predict_proba(X_test)[:, 1]
accuracy = accuracy_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_prob)

print(f"\n=== ENSEMBLE MODEL RESULTS ===")
print(f"Accuracy:  {accuracy*100:.1f}%")
print(f"ROC AUC:   {roc_auc:.3f}")
print(f"(Previous model: 85.7% accuracy, ROC AUC 0.793)")

# Save model
model_path = os.path.join(BASE_DIR, 'winner_predictor_v3.pkl')
with open(model_path, 'wb') as f:
    pickle.dump({'model': ensemble, 'features': FEATURES}, f)

print(f"\n✅ Ensemble model saved to models/winner_predictor_v3.pkl")
