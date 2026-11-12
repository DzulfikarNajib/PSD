import pandas as pd

from src.car_search import budget_summary, compare_listings, filter_listings


def sample_listings():
    return pd.DataFrame([
        {"listing_id": "a", "make": "Toyota", "model": "Avanza", "price": 150_000_000, "year": 2020, "mileage_km": 30000, "engine_cc": 1300, "transmission": "Automatic"},
        {"listing_id": "b", "make": "Toyota", "model": "Avanza", "price": 180_000_000, "year": 2022, "mileage_km": 20000, "engine_cc": 1500, "transmission": "Automatic"},
        {"listing_id": "c", "make": "Honda", "model": "Brio", "price": 120_000_000, "year": 2019, "mileage_km": 50000, "engine_cc": 1200, "transmission": "Manual"},
    ])


def test_search_filters_integrate_and_allow_missing_optional_data():
    result = filter_listings(sample_listings(), budget=(140_000_000, 190_000_000), make="Toyota", years=(2020, 2022), max_mileage=35_000, categories={"transmission": "Automatic"})
    assert result["listing_id"].tolist() == ["a", "b"]


def test_compare_and_budget_summary():
    df = sample_listings()
    comparison = compare_listings(df, ["a", "b"])
    assert comparison.loc["price"].tolist() == [150_000_000, 180_000_000]
    assert compare_listings(df, ["a"]).empty
    summary = budget_summary(df, [100_000_000, 150_000_000, 150_000_000])
    assert summary["listing_count"].tolist() == [0, 2]
