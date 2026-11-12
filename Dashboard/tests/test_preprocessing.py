import pandas as pd

from src.preprocessing import (append_history_snapshot, build_live_dataset_from_response,
                               filter_jabodetabek, parse_api_response_to_dataframe,
                               parse_engine_cc, parse_mileage_km, save_dataframe_atomic)


def test_parse_api_response_to_dataframe():
    payload = {
        "raw": [
            {
                "listing_id": "1",
                "make": "Toyota",
                "model": "Avanza",
                "variant": "1.3 E",
                "price": 180000000,
                "price_text": "Rp 180.000.000",
                "year": 2019,
                "mileage_range": "45.000 - 55.000 km",
                "engine_capacity": "1.3 L",
                "fuel_type": "Bensin",
                "transmission": "Manual",
                "body_type": "MPV",
                "color": "Hitam",
                "location": "Jakarta Selatan",
                "image_url": "https://example.com/image.jpg",
                "url": "https://example.com/listing",
                "posted_at": "2024-01-01",
                "seller_type": "Private",
            }
        ]
    }
    df = parse_api_response_to_dataframe(payload, fetched_at="2024-01-02 12:00:00")
    assert not df.empty
    assert "price" in df.columns
    assert "mileage_km" in df.columns
    assert "engine_cc" in df.columns
    assert df["price"].iloc[0] == 180000000


def test_filter_jabodetabek():
    df = pd.DataFrame(
        {
            "location": [
                "Jakarta Selatan",
                "Jakarta Pusat",
                "Bekasi",
                "Depok",
                "Tangerang Selatan",
                "Bogor Barat",
                "Bandung",
            ]
        }
    )
    filtered = filter_jabodetabek(df)
    assert len(filtered) == 6
    assert "Bandung" not in filtered["location"].tolist()


def test_empty_dataframe_is_safe():
    df = pd.DataFrame()
    filtered = filter_jabodetabek(df)
    assert filtered.empty


def test_range_conversions_are_documented_midpoints():
    assert parse_mileage_km("20.000 - 30.000 km") == 25000
    assert parse_engine_cc("1.5 L") == 1500


def test_location_filter_normalizes_jabodetabek_and_excludes_outside():
    df = pd.DataFrame({"location": ["Jakarta Selatan, DKI Jakarta", "Kota Jakarta Utara", "Depok", "Kabupaten Bekasi", "Tangerang Selatan", "Bogor Barat", "Bandung"]})
    filtered = filter_jabodetabek(df)
    assert filtered["location_normalized"].tolist() == ["jakarta selatan", "jakarta utara", "depok", "bekasi", "tangerang", "bogor"]


def test_csv_roundtrip_and_history_deduplicates_same_snapshot(tmp_path):
    df = build_live_dataset_from_response({"raw": [{"listing_id": "id-1", "price": 100000000, "year": 2020, "location": "Jakarta Selatan"}]}, fetched_at="2026-11-06T12:00:00+07:00")
    live_path, history_path = tmp_path / "live.csv", tmp_path / "history.csv"
    save_dataframe_atomic(df, live_path)
    append_history_snapshot(df, history_path)
    append_history_snapshot(df, history_path)
    assert len(pd.read_csv(live_path)) == 1
    assert len(pd.read_csv(history_path)) == 1


def test_missing_listing_id_or_invalid_price_is_rejected():
    payload = {"raw": [{"price": 10, "location": "Jakarta Selatan"}, {"listing_id": "bad", "price": 0, "location": "Jakarta Selatan"}]}
    assert build_live_dataset_from_response(payload).empty
