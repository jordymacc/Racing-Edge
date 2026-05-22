import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib
from pathlib import Path
from feature_engine_v2 import build_training_dataset
from jockey_trainer_stats import calculate_jockey_stats, calculate_trainer_stats

MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "winner_predictor_v2.pkl"

def train_model_v2():
    """Train enhanced ML model with jockey/trainer features"""
    
    print("🤖 JordyMac ML Training Engine v2.0")
    print("=" * 60)
    print("✨ NEW: Jockey & Trainer Win Rates Added!\n")
    
    # Rebuild jockey/trainer stats first
    print("📊 Updating jockey/trainer statistics...")
    calculate_jockey_stats()
    calculate_trainer_stats()
    print()
    
    # Load data
    print("📊 Loading enhanced training data...")
    df = build_training_dataset()
    
    if df is None or len(df) < 50:
        print("❌ Not enough data to train")
        return
    
    # Enhanced feature set
    feature_cols = [
        # Original odds features
        'current_odds', 'opening_odds', 'odds_change_pct',
        'mean_odds', 'min_odds', 'max_odds', 'volatility',
        'market_rank', 'is_favorite', 'num_updates',
        
        # NEW: Jockey/Trainer features
        'jockey_win_rate', 'trainer_win_rate', 'combined_form'
    ]
    
    X = df[feature_cols].fillna(0)
    y = df['winner']
    
    print(f"✅ Dataset: {len(X)} horses, {y.sum()} winners")
    print(f"✅ Features: {len(feature_cols)} (was 10, now {len(feature_cols)}!)\n")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    # Train
    print("🔧 Training Enhanced Model...")
    model = GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    print("✅ Model trained!\n")
    
    # Evaluate
    print("=" * 60)
    print("📊 MODEL PERFORMANCE v2.0")
    print("=" * 60)
    
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"Training Accuracy:  {train_score*100:.1f}%")
    print(f"Test Accuracy:      {test_score*100:.1f}%")
    
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    try:
        auc = roc_auc_score(y_test, y_pred_proba)
        print(f"ROC AUC Score:      {auc:.3f}")
    except:
        pass
    
    print()
    print(classification_report(y_test, y_pred, target_names=['Loser', 'Winner']))
    
    # Feature importance
    print("=" * 60)
    print("🔍 FEATURE IMPORTANCE")
    print("=" * 60)
    
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for _, row in importances.iterrows():
        bar_length = int(row['importance'] * 50)
        bar = '█' * bar_length
        new_tag = " ⭐ NEW" if row['feature'] in ['jockey_win_rate', 'trainer_win_rate', 'combined_form'] else ""
        print(f"{row['feature']:20s} {bar} {row['importance']:.3f}{new_tag}")
    
    # Save model
    print(f"\n💾 Saving enhanced model...")
    joblib.dump({
        'model': model,
        'features': feature_cols,
        'version': '2.0',
        'trained_on': pd.Timestamp.now().isoformat()
    }, MODEL_PATH)
    
    print(f"✅ Model v2 saved to {MODEL_PATH}!")
    
    # Compare with v1
    try:
        v1_data = joblib.load(MODEL_DIR / "winner_predictor.pkl")
        print(f"\n📈 IMPROVEMENT vs v1.0:")
        print(f"   v1 features: 10")
        print(f"   v2 features: {len(feature_cols)}")
        print(f"   v2 uses real jockey/trainer win rates!")
    except:
        pass
    
    print("\n🎉 TRAINING v2 COMPLETE!")
    return model

if __name__ == "__main__":
    train_model_v2()
