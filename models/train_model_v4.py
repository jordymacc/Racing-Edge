import sqlite3
import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from xgboost import XGBClassifier

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'database', 'racing.db')

print("Loading data from database...")
conn = sqlite3.connect(DB_PATH)

odds_df = pd.read_sql_query("""
    SELECT DISTINCT
        o.race_name, o.horse_name, o.win_odds_racingcom,
        o.jockey_name, o.trainer_name,
        o.track_condition, o.track_condition_score,
        o.temperature, o.rainfall
    FROM odds_snapshots o
    WHERE o.win_odds_racingcom IS NOT NULL
""", conn)

results_df = pd.read_sql_query("""
    SELECT DISTINCT race_name, horse_name, winner, placed
    FROM historical_results
""", conn)

try:
    jockey_df = pd.read_sql_query("SELECT jockey_name, win_rate FROM jockey_stats", conn)
except:
    jockey_df = pd.DataFrame(columns=['jockey_name', 'win_rate'])

try:
    trainer_df = pd.read_sql_query("SELECT trainer_name, win_rate FROM trainer_stats", conn)
except:
    trainer_df = pd.DataFrame(columns=['trainer_name', 'win_rate'])

conn.close()

print(f"Odds snapshots: {len(odds_df)}")
print(f"Historical results: {len(results_df)}")

# Merge
df = odds_df.merge(results_df, on=['race_name', 'horse_name'], how='inner')
print(f"Merged records: {len(df)}")

if len(df) < 50:
    print("Not enough data yet. Try again in a few days.")
    exit()

# Add jockey/trainer stats
df = df.merge(jockey_df[['jockey_name', 'win_rate']], on='jockey_name', how='left')
df.rename(columns={'win_rate': 'jockey_win_rate'}, inplace=True)
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
df['track_condition_score'] = df['track_condition_score'].fillna(2)  # Default: Good
df['temperature'] = df['temperature'].fillna(df['temperature'].median())
df['rainfall'] = df['rainfall'].fillna(0)

# Encode track condition as dummy variables
df['is_good'] = (df['track_condition'] == 'Good').astype(int)
df['is_soft'] = (df['track_condition'] == 'Soft').astype(int)
df['is_heavy'] = (df['track_condition'] == 'Heavy').astype(int)
df['is_synth'] = (df['track_condition'] == 'Synth').astype(int)

# Feature engineering
df['implied_prob'] = 1 / df['win_odds_racingcom']
df['is_favorite'] = (df['win_odds_racingcom'] == df.groupby('race_name')['win_odds_racingcom'].transform('min')).astype(int)
df['market_rank'] = df.groupby('race_name')['win_odds_racingcom'].rank()
df['combined_form'] = df['jockey_win_rate'] * 0.5 + df['trainer_win_rate'] * 0.5
df['jockey_odds_interaction'] = df['jockey_win_rate'] * df['implied_prob']
df['trainer_odds_interaction'] = df['trainer_win_rate'] * df['implied_prob']
df['wet_track'] = ((df['track_condition_score'] >= 3) | (df['rainfall'] > 0)).astype(int)
df['temp_normalized'] = (df['temperature'] - df['temperature'].mean()) / (df['temperature'].std() + 1e-8)

FEATURES = [
    'win_odds_racingcom', 'implied_prob', 'is_favorite', 'market_rank',
    'jockey_win_rate', 'trainer_win_rate', 'combined_form',
    'jockey_odds_interaction', 'trainer_odds_interaction',
    'track_condition_score', 'is_good', 'is_soft', 'is_heavy', 'is_synth',
    'temperature', 'rainfall', 'wet_track', 'temp_normalized'
]

X = df[FEATURES].fillna(0)
y = df['winner'].fillna(0).astype(int)

print(f"\nTraining data: {len(X)} horses, {y.sum()} winners ({y.mean()*100:.1f}% win rate)")
print(f"Track conditions: Good={df['is_good'].sum()}, Soft={df['is_soft'].sum()}, Synth={df['is_synth'].sum()}")
print(f"Weather data: {df['temperature'].notna().sum()} with temp, {(df['rainfall']>0).sum()} with rain")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

gb  = GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42)
rf  = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
xgb = XGBClassifier(n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42, eval_metric='logloss')

ensemble = VotingClassifier(estimators=[('gb', gb), ('rf', rf), ('xgb', xgb)], voting='soft')
print("\nTraining v4 ensemble (GB + RF + XGBoost) with track + weather features...")
ensemble.fit(X_train, y_train)

y_pred = ensemble.predict(X_test)
y_prob = ensemble.predict_proba(X_test)[:, 1]
accuracy = accuracy_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_prob)

print(f"\n=== MODEL v4 RESULTS ===")
print(f"Accuracy:  {accuracy*100:.1f}%")
print(f"ROC AUC:   {roc_auc:.3f}")
print(f"New features: track condition + weather ({len(FEATURES)} total vs 9 before)")
print(f"(v3 model: 90.4% accuracy, ROC AUC 0.882)")

model_path = os.path.join(BASE_DIR, 'winner_predictor_v4.pkl')
with open(model_path, 'wb') as f:
    pickle.dump({'model': ensemble, 'features': FEATURES}, f)

print(f"\n✅ Model v4 saved to models/winner_predictor_v4.pkl")
