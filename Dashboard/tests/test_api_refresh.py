from unittest.mock import Mock, patch

import pytest
import requests

from src.api_handler import build_payload, safe_refresh_snapshot


def test_build_payload_uses_search_endpoint():
    payload = build_payload("https://www.olx.co.id/mobil-bekas_c198/q-toyota-avanza", max_pages=1)
    assert payload["capability"] == "endpoint"
    assert payload["endpoint"] == "olx.search_items"
    assert payload["url"].startswith("https://www.olx.co.id/")


def test_api_validation_error_body_is_reported(monkeypatch):
    from src.api_handler import fetch_datawebot

    monkeypatch.setenv("DATAWEBOT_API_KEY", "test-key")
    response = Mock()
    response.status_code = 422
    response.json.return_value = {"error": {"code": "invalid_input", "message": "Unsupported search URL"}}
    response.raise_for_status.side_effect = requests.HTTPError("422 Client Error", response=response)

    with patch("src.api_handler.requests.post", return_value=response):
        with pytest.raises(RuntimeError, match="Unsupported search URL"):
            fetch_datawebot("https://www.olx.co.id/jakarta-dki_g2000007/mobil-bekas_c198/q-mobil", max_pages=1)


def test_safe_refresh_snapshot_persists_valid_response(tmp_path):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "meta": {"usage": {"used": 5, "remaining": 95}},
        "raw": [
            {
                "listing_id": "abc-1",
                "make": "Toyota",
                "model": "Agya",
                "variant": "1.0 E",
                "price": 130000000,
                "price_text": "Rp 130.000.000",
                "year": 2020,
                "mileage_range": "30.000 - 40.000 km",
                "engine_capacity": "1.0 L",
                "fuel_type": "Bensin",
                "transmission": "Manual",
                "body_type": "Hatchback",
                "color": "Putih",
                "location": "Jakarta Selatan",
                "image_url": "https://example.com/a.jpg",
                "url": "https://example.com/iklan",
                "posted_at": "2024-01-02",
                "seller_type": "Private",
            }
        ],
    }

    with patch("src.api_handler.requests.post", return_value=mock_response):
        result = safe_refresh_snapshot("https://www.olx.co.id/mobil-bekas_c198/q-toyota-agya", max_pages=1, live_path=tmp_path / "olx_live.csv", history_path=tmp_path / "olx_history.csv")

    assert result["status"] == "success"
    assert result["live_count"] == 1
    assert result["filtered_count"] == 1
    assert result["raw_count"] == 1
    assert result["validated_count"] == 1
    assert (tmp_path / "olx_live.csv").exists()
    assert (tmp_path / "olx_history.csv").exists()


def test_empty_or_failed_refresh_does_not_replace_previous_csvs(tmp_path, monkeypatch):
    from src import api_handler

    live = tmp_path / "live.csv"
    history = tmp_path / "history.csv"
    live.write_text("old-live", encoding="utf-8")
    history.write_text("old-history", encoding="utf-8")
    monkeypatch.setattr(api_handler, "fetch_datawebot", lambda **kwargs: {"raw": []})
    result = safe_refresh_snapshot("https://www.olx.co.id/search", live_path=live, history_path=history)
    assert result["status"] == "empty"
    assert live.read_text(encoding="utf-8") == "old-live"
    assert history.read_text(encoding="utf-8") == "old-history"

    def fail(**kwargs):
        raise RuntimeError("offline")
    monkeypatch.setattr(api_handler, "fetch_datawebot", fail)
    try:
        safe_refresh_snapshot("https://www.olx.co.id/search", live_path=live, history_path=history)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected the mocked API error")
    assert live.read_text(encoding="utf-8") == "old-live"
    assert history.read_text(encoding="utf-8") == "old-history"
