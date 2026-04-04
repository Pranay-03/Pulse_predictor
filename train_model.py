"""
Train ML models for Project Pulse Predictor.
Generates synthetic training data, trains a RandomForest classifier (risk level)
and a RandomForest regressor (cost overrun %), then saves models to disk.

Usage:
    python train_model.py
"""

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_squared_error
import joblib

np.random.seed(42)
n_samples = 2000

print("=" * 60)
print("  Project Pulse Predictor - Model Training")
print("=" * 60)

# ── Generate Synthetic Training Data ──
print("\n[1/5] Generating synthetic project data...")

planned_cost = np.random.uniform(10000, 500000, n_samples)
planned_effort = np.random.uniform(100, 5000, n_samples)
resource_count = np.random.randint(2, 50, n_samples)
duration = np.random.randint(30, 365, n_samples)

# Overrun factors with realistic distribution
cost_overrun_factor = np.random.normal(1.0, 0.3, n_samples).clip(0.5, 3.0)
effort_overrun_factor = np.random.normal(1.0, 0.25, n_samples).clip(0.5, 2.5)

actual_cost = planned_cost * cost_overrun_factor
actual_effort = planned_effort * effort_overrun_factor

# ── Feature Engineering ──
print("[2/5] Computing engineered features...")

cost_variance = (actual_cost - planned_cost) / np.maximum(planned_cost, 1)
effort_variance = (actual_effort - planned_effort) / np.maximum(planned_effort, 1)
burn_rate = actual_cost / np.maximum(duration, 1)
resource_utilization = actual_effort / np.maximum(resource_count * duration, 1)

features = pd.DataFrame({
    "cost_variance": cost_variance,
    "effort_variance": effort_variance,
    "burn_rate": burn_rate,
    "resource_utilization": resource_utilization,
    "duration": duration,
    "resource_count": resource_count,
})

# Assign risk labels based on composite score
risk_score = (
    np.abs(cost_variance) * 0.4
    + np.abs(effort_variance) * 0.3
    + (resource_utilization > 1.0).astype(float) * 0.15
    + (burn_rate > np.percentile(burn_rate, 75)).astype(float) * 0.15
)

risk_labels = np.where(
    risk_score > 0.3, "High Risk",
    np.where(risk_score > 0.12, "Warning", "Safe")
)

cost_overrun_pct = ((actual_cost - planned_cost) / np.maximum(planned_cost, 1)) * 100

print(f"   Samples: {n_samples}")
print(f"   Safe: {(risk_labels == 'Safe').sum()}, Warning: {(risk_labels == 'Warning').sum()}, High Risk: {(risk_labels == 'High Risk').sum()}")

# ── Train/Test Split ──
print("[3/5] Splitting data (80/20)...")

X_train, X_test, y_cls_train, y_cls_test = train_test_split(
    features, risk_labels, test_size=0.2, random_state=42, stratify=risk_labels
)
_, _, y_reg_train, y_reg_test = train_test_split(
    features, cost_overrun_pct, test_size=0.2, random_state=42, stratify=risk_labels
)

# ── Train Models ──
print("[4/5] Training models...")

# Classification model
clf = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=42)
clf.fit(X_train, y_cls_train)

# Regression model
reg = RandomForestRegressor(n_estimators=150, max_depth=10, random_state=42)
reg.fit(X_train, y_reg_train)

# ── Evaluate ──
print("\n--- Classification Report ---")
print(classification_report(y_cls_test, clf.predict(X_test)))

reg_pred = reg.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_reg_test, reg_pred))
print(f"--- Regression RMSE: {rmse:.2f}% ---\n")

# ── Save Models ──
print("[5/5] Saving models...")

os.makedirs("models", exist_ok=True)
joblib.dump(clf, "models/risk_classifier.joblib")
joblib.dump(reg, "models/overrun_regressor.joblib")

print("   Saved: models/risk_classifier.joblib")
print("   Saved: models/overrun_regressor.joblib")
print("\n" + "=" * 60)
print("  Training complete! You can now run the application.")
print("=" * 60)
