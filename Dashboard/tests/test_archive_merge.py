from unittest.mock import Mock, patch

import pandas as pd

from src import data_loader, supabase_store


def _listing(listing_id, price, fetched_at, url):
    return {
        "listing_id": listing_id, "url": url, "make": "Toyota", "model": "Avanza",
        "price": price, "year": 2020, "mileage_km": 40000, "engine_cc": 1500,
        "transmission": "Automatic", "fuel_type": "Bensin", "body_type": "MPV",
        "location": "Jakarta Selatan", "fetched_at": fetched_at,
    }


def test_combined_archive_prefers_latest_url_match_and_counts_observations(monkeypatch):
    excel = pd.DataFrame([_listing("excel-id", 200_000_000, None, "https://olx.test/car/1/?from=excel")])
    snapshots = pd.DataFrame([
        _listing("api-id-1", 195_000_000, "2026-11-10T02:00:00Z", "https://olx.test/car/1/?ref=refresh"),
        _listing("api-id-2", 190_000_000, "2026-11-11T02:00:00Z", "https://olx.test/car/1/"),
        _listing("api-id-3", 100_000_000, "2026-11-11T02:00:00Z", "https://olx.test/car/2/"),
    ])
    monkeypatch.setattr(data_loader, "load_historical_data", lambda: excel.copy())
    monkeypatch.setattr(data_loader, "supabase_is_configured", lambda: True)
    monkeypatch.setattr(data_loader, "load_excel_seed", lambda: excel.copy())
    monkeypatch.setattr(data_loader, "load_snapshot_archive", lambda: snapshots.copy())

    combined = data_loader.load_combined_archive()

    assert len(combined) == 2
    first = combined[combined["url"].str.contains("/car/1")].iloc[0]
    assert first["price"] == 190_000_000
    assert first["observation_count"] == 3
    assert first["data_source"] == "Arsip snapshot OLX"
    assert first["source_origins"] == "Arsip snapshot OLX + Dataset Excel"


def test_excel_seed_import_is_repeatable_and_has_no_capture_date(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.test")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-only-key")
    response = Mock(ok=True, content=b"[]")
    response.json.return_value = []
    frame = pd.DataFrame([_listing("listing-1", 150_000_000.0, None, "https://olx.test/car/1")])
    frame["year"] = 2020.0
    frame["mileage_km"] = 12500.0
    frame["engine_cc"] = 2500.0

    with patch("src.supabase_store.requests.post", return_value=response) as post:
        supabase_store.import_excel_seed(frame)
        supabase_store.import_excel_seed(frame)

    assert post.call_count == 2
    for call in post.call_args_list:
        record = call.kwargs["json"][0]
        assert record["snapshot_id"] == supabase_store.EXCEL_SEED_SNAPSHOT
        assert record["fetched_at"] is None
        assert call.kwargs["params"]["on_conflict"] == "snapshot_id,listing_id"
        for field in ("price", "year", "mileage_km", "engine_cc"):
            assert isinstance(record[field], int)


def test_supabase_rest_url_is_normalized_when_rest_suffix_is_in_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.test/rest/v1/rest/v1/")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-only-key")

    endpoint, _ = supabase_store._headers()

    assert endpoint == "https://project.test/rest/v1/listing_snapshots"
