import os

os.environ["AUTOMATCH_OFFLINE"] = "1"

from src.data_loader import load_historical_data_with_audit
from src.market_segments import cluster_market_segments
from src.modeling import training_eligibility
from src.preprocessing import MAX_ANALYSIS_PRICE, MIN_ANALYSIS_PRICE, DKI_DISTRICTS, normalize_timestamp_utc
from src.ui import build_preprocessing_funnel, format_timestamp_wib


def test_active_olx_dataset_is_cleaned_and_audited():
    data, audit = load_historical_data_with_audit()

    assert audit["raw_rows"] == 10_563
    assert audit["duplicate_rows_removed"] == 3_352
    assert audit["after_dedup_rows"] == 7_211
    assert audit["after_dki_rows"] == 6_360
    assert audit["low_price_rows_removed"] == 57
    assert audit["high_price_rows_removed"] == 2
    assert audit["clean_rows"] == 6_301
    assert audit["clean_rows"] == len(data)
    assert data["listing_id"].is_unique
    assert data["location_normalized"].isin(DKI_DISTRICTS).all()
    assert data["price"].between(MIN_ANALYSIS_PRICE, MAX_ANALYSIS_PRICE).all()
    assert audit["latest_fetched_at"]
    assert "missing_value_pct" in audit

    funnel = build_preprocessing_funnel(audit)
    assert funnel.iloc[0]["Listing tersisa"] == 10_563
    assert funnel.iloc[-1]["Listing tersisa"] == 6_301


def test_clean_dataset_is_eligible_for_model_and_market_segments():
    data, _ = load_historical_data_with_audit()
    eligible, _, prepared = training_eligibility(data)
    assert eligible
    assert len(prepared) > 100

    segmented, summary = cluster_market_segments(data)
    assert segmented["market_segment"].ne("").any()
    assert not summary.empty


def test_missing_engine_capacity_on_electric_cars_stays_missing():
    data, _ = load_historical_data_with_audit()
    electric = data["fuel_type"].astype(str).str.casefold().eq("listrik")
    assert data.loc[electric, "engine_cc"].isna().any()


def test_naive_capture_time_is_treated_as_jakarta_time():
    utc = normalize_timestamp_utc("2026-11-17 19:56:57")
    assert utc == "2026-11-17T12:56:57+00:00"
    assert format_timestamp_wib(utc) == "17 Nov 2026, 19:56 WIB"
