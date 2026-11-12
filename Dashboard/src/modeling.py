"""Validated listing-price regression workflow."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeRegressor

from src.preprocessing import is_dki_jakarta

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT_DIR / "models" / "best_model.joblib"
MODEL_METADATA_PATH = ROOT_DIR / "models" / "model_metrics.json"
MINIMUM_UNIQUE_LISTINGS = 100
MINIMUM_MAKES = 3
MINIMUM_MODELS = 5
NUMERIC_FEATURES = ["year", "mileage_km", "engine_cc"]
CATEGORICAL_FEATURES = ["make", "model", "transmission", "fuel_type", "body_type"]
FEATURES = CATEGORICAL_FEATURES[:2] + NUMERIC_FEATURES + CATEGORICAL_FEATURES[2:]


def prepare_model_data(df: pd.DataFrame) -> pd.DataFrame:
    """Use the latest valid observation per listing_id to prevent snapshot leakage."""
    required = ["listing_id", "price", *FEATURES, "location"]
    if df.empty or any(column not in df.columns for column in required):
        return pd.DataFrame(columns=required)
    prepared = df[required + (["fetched_at"] if "fetched_at" in df else [])].copy()
    prepared["price"] = pd.to_numeric(prepared["price"], errors="coerce")
    prepared = prepared.dropna(subset=["listing_id", "price"])
    prepared = prepared[prepared["location"].map(is_dki_jakarta)]
    if "fetched_at" in prepared:
        # UTC parsing sorts both legacy naive timestamps and newer offset-aware values safely.
        prepared["fetched_at"] = pd.to_datetime(prepared["fetched_at"], errors="coerce", utc=True)
        prepared = prepared.sort_values("fetched_at", na_position="first")
    prepared = prepared.drop_duplicates("listing_id", keep="last")
    prepared = prepared[prepared["price"] > 0]
    prepared["year"] = pd.to_numeric(prepared["year"], errors="coerce")
    prepared["mileage_km"] = pd.to_numeric(prepared["mileage_km"], errors="coerce")
    prepared["engine_cc"] = pd.to_numeric(prepared["engine_cc"], errors="coerce")
    prepared = prepared[prepared["year"].between(1950, pd.Timestamp.now().year + 1) | prepared["year"].isna()]
    prepared = prepared[prepared["mileage_km"].ge(0) | prepared["mileage_km"].isna()]
    return prepared.drop(columns=["fetched_at"], errors="ignore").reset_index(drop=True)


def load_model_metadata() -> dict:
    if not MODEL_METADATA_PATH.exists():
        return {}
    try:
        return json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def model_is_validated(metadata: dict) -> bool:
    """Reject legacy artifacts that lack the current data eligibility record."""
    return bool(
        metadata.get("status") == "ready"
        and metadata.get("validation_version") == 2
        and metadata.get("training_unique_listings", 0) >= MINIMUM_UNIQUE_LISTINGS
        and metadata.get("minimum_unique_listings") == MINIMUM_UNIQUE_LISTINGS
        and metadata.get("models")
    )


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), NUMERIC_FEATURES),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]), CATEGORICAL_FEATURES),
    ])


def training_eligibility(df: pd.DataFrame) -> tuple[bool, str, pd.DataFrame]:
    data = prepare_model_data(df)
    if len(data) < MINIMUM_UNIQUE_LISTINGS:
        return False, f"Diperlukan sedikitnya {MINIMUM_UNIQUE_LISTINGS} listing unik tervalidasi; saat ini {len(data)}.", data
    if data["make"].nunique(dropna=True) < MINIMUM_MAKES:
        return False, f"Diperlukan sedikitnya {MINIMUM_MAKES} merek yang beragam.", data
    if data["model"].nunique(dropna=True) < MINIMUM_MODELS:
        return False, f"Diperlukan sedikitnya {MINIMUM_MODELS} model kendaraan yang beragam.", data
    return True, "Data memenuhi kriteria minimum untuk evaluasi baseline.", data


def evaluate_regression_models(df: pd.DataFrame, model_path: str | Path | None = None, metadata_path: str | Path | None = None) -> dict:
    """Train/evaluate three baselines. This function is called only by explicit user action."""
    eligible, message, prepared = training_eligibility(df)
    if not eligible:
        return {"status": "insufficient_data", "message": message, "models": {}, "records": len(prepared)}
    X, y = prepared[FEATURES], prepared["price"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    estimators = {
        "Linear Regression": LinearRegression(),
        "Decision Tree Regressor": DecisionTreeRegressor(random_state=42, min_samples_leaf=3),
        "Random Forest Regressor": RandomForestRegressor(n_estimators=200, random_state=42, min_samples_leaf=2, n_jobs=-1),
    }
    results, pipelines = {}, {}
    for name, estimator in estimators.items():
        pipeline = Pipeline([("preprocessor", _preprocessor()), ("model", estimator)])
        pipeline.fit(X_train, y_train)
        predicted = pipeline.predict(X_test)
        results[name] = {
            "MAE": float(mean_absolute_error(y_test, predicted)),
            "RMSE": float(mean_squared_error(y_test, predicted) ** 0.5),
            "R2": float(r2_score(y_test, predicted)) if len(y_test) > 1 else None,
        }
        pipelines[name] = pipeline
    winner = min(results, key=lambda name: results[name]["MAE"])
    final_pipeline = Pipeline([("preprocessor", _preprocessor()), ("model", estimators[winner])])
    final_pipeline.fit(X, y)
    destination = Path(model_path) if model_path else MODEL_PATH
    metrics_destination = Path(metadata_path) if metadata_path else MODEL_METADATA_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    metrics_destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipeline, destination)
    metadata = {
        "status": "ready", "validation_version": 2,
        "best_model": winner, "best_model_path": str(destination),
        "models": results, "training_unique_listings": len(prepared),
        "minimum_unique_listings": MINIMUM_UNIQUE_LISTINGS,
        "selection_metric": "lowest holdout MAE", "target": "asking price",
    }
    metrics_destination.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return metadata


def predict_asking_price(features: dict, model_path: str | Path | None = None) -> float:
    """Load an existing validated pipeline and return its asking-price estimate."""
    path = Path(model_path) if model_path else MODEL_PATH
    metadata = load_model_metadata()
    if not path.exists() or not model_is_validated(metadata):
        raise FileNotFoundError("Model tervalidasi belum tersedia.")
    pipeline = joblib.load(path)
    row = pd.DataFrame([{column: features.get(column) for column in FEATURES}])
    return float(pipeline.predict(row)[0])


def get_feature_importance(model_path: str | Path | None = None) -> pd.DataFrame:
    """Return tree importances or absolute linear coefficients, not causal effects."""
    path = Path(model_path) if model_path else MODEL_PATH
    if not path.exists() or not model_is_validated(load_model_metadata()):
        return pd.DataFrame(columns=["feature", "importance"])
    pipeline = joblib.load(path)
    model = pipeline.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    elif hasattr(model, "coef_"):
        values = abs(model.coef_).ravel()
    else:
        return pd.DataFrame(columns=["feature", "importance"])
    names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    return pd.DataFrame({"feature": names, "importance": values}).sort_values("importance", ascending=False)
