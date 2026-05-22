import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
import joblib
from pathlib import Path
from feature_engine import build_training_dataset

MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "winner_predictor.pkl"

def train_model():
    """Train ML model to predict race winners"""
    
    print("🤖 JordyMac ML Training Engine\n")
    print("=" * 60)
    
    # Load data
    print("📊 Loading training data...")
    df = build_training_dataset()
    
    if df is None or len(df) < 50:
        print("❌ Not enough data to train (need at least 50 samples)")
        return
    
    # Prepare features
    feature_cols = [
        'current_odds', 'opening_odds', 'odds_change_pct',
        'mean_odds', 'min_odds', 'max_odds', 'volatility',
        'market_rank', 'is_favorite', 'num_updates'
    ]
    
    X = df[feature_cols].copy()
    y = df['winner'].copy()
    
    # Handle any missing values
    X = X.fillna(0)
    
    print(f"✅ Dataset: {len(X)} horses, {y.sum()} winners ({y.mean()*100:.1f}% win rate)")
    print(f"✅ Features: {len(feature_cols)}")
    print()
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    print(f"📈 Training set: {len(X_train)} horses")
    print(f"📉 Test set: {len(X_test)} horses")
    print()
    
    # Train model
    print("🔧 Training Gradient Boosting Classifier...")
    
    model = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=4,
        random_state=42,
        verbose=0
    )
    
    model.fit(X_train, y_train)
    
    print("✅ Model trained!\n")
    
    # Evaluate
    print("=" * 60)
    print("📊 MODEL PERFORMANCE")
    print("=" * 60)
    
    # Training accuracy
    train_score = model.score(X_train, y_train)
    print(f"Training Accuracy: {train_score*100:.1f}%")
    
    # Test accuracy
    test_score = model.score(X_test, y_test)
    print(f"Test Accuracy: {test_score*100:.1f}%")
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # ROC AUC
    try:
        auc = roc_auc_score(y_test, y_pred_proba)
        print(f"ROC AUC Score: {auc:.3f}")
    except:
        print("ROC AUC: N/A (need more positive samples)")
    
    print()
    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Loser', 'Winner']))
    
    # Feature importance
    print("=" * 60)
    print("🔍 FEATURE IMPORTANCE")
    print("=" * 60)
    
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for i, row in importances.iterrows():
        bar_length = int(row['importance'] * 50)
        bar = '█' * bar_length
        print(f"{row['feature']:20s} {bar} {row['importance']:.3f}")
    
    print()
    
    # Save model
    print(f"💾 Saving model to {MODEL_PATH}...")
    joblib.dump({
        'model': model,
        'features': feature_cols,
        'version': '1.0',
        'trained_on': pd.Timestamp.now().isoformat()
    }, MODEL_PATH)
    
    print("✅ Model saved!")
    print()
    
    # Show some predictions
    print("=" * 60)
    print("🎯 SAMPLE PREDICTIONS")
    print("=" * 60)
    
    test_df = df.loc[X_test.index].copy()
    test_df['predicted_win_prob'] = y_pred_proba
    test_df = test_df.sort_values('predicted_win_prob', ascending=False)
    
    print("\nTop 10 predictions:")
    print(test_df[['horse_name', 'current_odds', 'is_favorite', 'predicted_win_prob', 'winner']].head(10).to_string(index=False))
    
    print()
    print("=" * 60)
    print("🎉 TRAINING COMPLETE!")
    print("=" * 60)
    print(f"Model ready at: {MODEL_PATH}")
    print()


if __name__ == "__main__":
    train_model()
