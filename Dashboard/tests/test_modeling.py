import pandas as pd

from src.modeling import (evaluate_regression_models, model_is_validated,
                          prepare_model_data, training_eligibility)


def make_listing_df(rows: int = 120):
    records = []
    for idx in range(rows):
        records.append(
            {
                "listing_id": f"L{idx}",
                "location": "Jakarta Selatan",
                "make": ["Toyota", "Honda", "Suzuki", "Daihatsu"][idx % 4],
                "model": ["Avanza", "Brio", "Ertiga", "Xenia", "Agya", "Jazz"][idx % 6],
                "year": 2018 + (idx % 7),
                "mileage_km": 20000 + idx * 1500,
                "engine_cc": 1300 + (idx % 4) * 100,
                "transmission": "Manual" if idx % 2 == 0 else "Automatic",
                "fuel_type": "Bensin",
                "body_type": "MPV" if idx % 2 == 0 else "Hatchback",
                "price": 120000000 + idx * 7500000,
            }
        )
    return pd.DataFrame(records)


def test_model_training_on_reasonable_data(tmp_path):
    df = make_listing_df()
    result = evaluate_regression_models(df, tmp_path / "model.joblib", tmp_path / "metrics.json")
    assert result["status"] == "ready"
    assert model_is_validated(result)
    assert set(result["models"]).issuperset({"Linear Regression", "Decision Tree Regressor", "Random Forest Regressor"})


def test_repeated_listing_snapshots_use_latest_observation():
    df = make_listing_df(120)
    repeated = pd.concat([df, df.iloc[[0]].assign(price=999_000_000, fetched_at="2026-11-06T10:00:00+07:00")], ignore_index=True)
    repeated.loc[0, "fetched_at"] = "2026-11-05T10:00:00+07:00"
    prepared = prepare_model_data(repeated)
    assert len(prepared) == 120
    assert prepared.loc[prepared["listing_id"].eq("L0"), "price"].iloc[0] == 999_000_000


def test_insufficient_data_does_not_create_model(tmp_path):
    result = evaluate_regression_models(make_listing_df(30), tmp_path / "model.joblib", tmp_path / "metrics.json")
    assert result["status"] == "insufficient_data"
    assert not (tmp_path / "model.joblib").exists()


def test_legacy_ready_metadata_is_not_treated_as_validated():
    assert not model_is_validated({"status": "ready", "models": {"Linear Regression": {"R2": 1.0}}})
