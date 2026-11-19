import pandas as pd

from src.car_search import assess_price_position, budget_summary, compare_listings, filter_listings


def sample_listings():
    return pd.DataFrame([
        {"listing_id": "a", "make": "Toyota", "model": "Avanza", "price": 150_000_000, "year": 2020, "mileage_km": 30000, "engine_cc": 1300, "transmission": "Automatic"},
        {"listing_id": "b", "make": "Toyota", "model": "Avanza", "price": 180_000_000, "year": 2022, "mileage_km": 20000, "engine_cc": 1500, "transmission": "Automatic"},
        {"listing_id": "c", "make": "Honda", "model": "Brio", "price": 120_000_000, "year": 2019, "mileage_km": 50000, "engine_cc": 1200, "transmission": "Manual"},
    ])


def test_search_filters_integrate_and_allow_missing_optional_data():
    result = filter_listings(sample_listings(), budget=(140_000_000, 190_000_000), make="Toyota", years=(2020, 2022), max_mileage=35_000, categories={"transmission": "Automatic"})
    assert result["listing_id"].tolist() == ["a", "b"]


def test_narrow_engine_filter_excludes_listings_without_cc():
    df = pd.concat([
        sample_listings(),
        pd.DataFrame([{"listing_id": "unknown", "engine_cc": None}]),
    ], ignore_index=True)

    all_engines = filter_listings(df, engine_range=(0, 10_000))
    large_engines = filter_listings(df, engine_range=(3_500, 6_800))

    assert "unknown" in all_engines["listing_id"].tolist()
    assert "unknown" not in large_engines["listing_id"].tolist()
    assert large_engines["listing_id"].empty


def test_compare_and_budget_summary():
    df = sample_listings()
    comparison = compare_listings(df, ["a", "b"])
    assert comparison.loc["price"].tolist() == [150_000_000, 180_000_000]
    assert compare_listings(df, ["a"]).empty
    summary = budget_summary(df, [100_000_000, 150_000_000, 150_000_000])
    assert summary["listing_count"].tolist() == [0, 2]


def test_price_position_withholds_label_for_fewer_than_five_comparables():
    result = assess_price_position(160_000_000, [150_000_000, 170_000_000])
    assert result["count"] == 2
    assert result["label"] is None


def test_price_position_labels_large_enough_comparable_sample():
    result = assess_price_position(130_000_000, [150_000_000] * 5)
    assert result["label"] == "Di bawah pembanding"
