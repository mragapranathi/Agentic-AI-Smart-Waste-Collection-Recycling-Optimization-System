import os
import json
import joblib
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from ml.training.dataset import generate_synthetic_training_data
from ml.evaluation.metrics import calculate_metrics

def train_forecasting_pipeline(output_dir: str = "ml/models", n_samples: int = 6000):
    os.makedirs(output_dir, exist_ok=True)
    print(f"Generating synthetic training dataset ({n_samples} samples)...")
    df = generate_synthetic_training_data(n_samples=n_samples)

    # Save dataset copy
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/forecast_training_dataset.csv", index=False)

    feature_cols = [
        "current_fill_percent",
        "prev_fill_percent",
        "fill_change",
        "hour_of_day",
        "day_of_week",
        "waste_type",
        "capacity_liters",
        "time_since_collection_hours",
        "historical_growth_rate"
    ]
    target_col = "future_fill_percent"

    X = df[feature_cols]
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Preprocessing
    categorical_features = ["waste_type"]
    numeric_features = [c for c in feature_cols if c not in categorical_features]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("num", "passthrough", numeric_features)
        ]
    )

    # 1. Baseline Model: Linear Regression
    print("Training Baseline Model (LinearRegression)...")
    baseline_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", LinearRegression())
    ])
    baseline_pipeline.fit(X_train, y_train)
    y_pred_baseline = baseline_pipeline.predict(X_test)
    baseline_metrics = calculate_metrics(y_test, y_pred_baseline)
    print(f"Baseline Metrics: MAE={baseline_metrics['mae']}, RMSE={baseline_metrics['rmse']}, MAPE={baseline_metrics['mape']}%")

    # 2. Production Model: RandomForestRegressor
    print("Training Production ML Model (RandomForestRegressor)...")
    rf_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1))
    ])
    rf_pipeline.fit(X_train, y_train)
    y_pred_rf = rf_pipeline.predict(X_test)
    rf_metrics = calculate_metrics(y_test, y_pred_rf)
    print(f"RandomForest Metrics: MAE={rf_metrics['mae']}, RMSE={rf_metrics['rmse']}, MAPE={rf_metrics['mape']}%")

    # Persist ML model
    model_path = os.path.join(output_dir, "forecasting_model.joblib")
    baseline_path = os.path.join(output_dir, "baseline_model.joblib")
    joblib.dump(rf_pipeline, model_path)
    joblib.dump(baseline_pipeline, baseline_path)

    metadata = {
        "model_name": "RandomForestRegressor",
        "model_version": "v1.0.0",
        "trained_at": datetime.utcnow().isoformat(),
        "dataset_samples": n_samples,
        "features": feature_cols,
        "categorical_features": categorical_features,
        "target": target_col,
        "metrics": {
            "ml_model": rf_metrics,
            "baseline_model": baseline_metrics
        },
        "hyperparameters": {
            "n_estimators": 100,
            "max_depth": 12,
            "random_state": 42
        }
    }

    metadata_path = os.path.join(output_dir, "model_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Model successfully saved to {model_path}")
    print(f"Metadata written to {metadata_path}")
    return metadata

if __name__ == "__main__":
    train_forecasting_pipeline()
