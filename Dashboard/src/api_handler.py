"""Datawebot API helper functions.

This module is intentionally safe to import without making any network requests.
The actual API call is triggered only by an explicit refresh action from the UI.
"""

from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

from src.data_loader import HISTORY_PATH, LIVE_PATH
from src.preprocessing import (append_history_snapshot, filter_dki_jakarta,
                               parse_api_response_to_dataframe, save_dataframe_atomic,
                               validate_listing_dataframe)
from src.supabase_store import is_configured as supabase_is_configured
from src.supabase_store import save_snapshot as save_supabase_snapshot

load_dotenv()

API_URL = "https://api.datawebot.com/v1/requests"
DATAWEBOT_API_KEY_ENV = "DATAWEBOT_API_KEY"


def get_api_key() -> str | None:
    """Read the API key from the environment without exposing it in code."""
    return os.getenv(DATAWEBOT_API_KEY_ENV)


def build_payload(search_url: str, max_pages: int = 1) -> Dict[str, Any]:
    """Build a Datawebot request body for OLX search endpoint."""
    return {
        "capability": "endpoint",
        "endpoint": "olx.search_items",
        "url": search_url,
        "max_pages": max_pages,
        "format": "raw",
    }


def _extract_usage_meta(meta: Any) -> Dict[str, Any]:
    """Extract credit-related values when the API metadata includes them."""
    if not isinstance(meta, dict):
        return {}
    usage = meta.get("usage", {})
    if not isinstance(usage, dict):
        return {}
    return {
        "used": usage.get("used"),
        "remaining": usage.get("remaining"),
        "total": usage.get("total"),
    }


def fetch_datawebot(search_url: str, max_pages: int = 1) -> Dict[str, Any]:
    """Fetch raw listing payload from Datawebot API with strict validation."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError("DATAWEBOT_API_KEY is missing. Add it to your .env file.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=build_payload(search_url, max_pages=max_pages),
            timeout=90,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        try:
            error_body = response.json()
        except ValueError:
            error_body = response.text[:500]
        if isinstance(error_body, (dict, list)):
            detail = json.dumps(error_body, ensure_ascii=False, default=str)
        else:
            detail = str(error_body)
        raise RuntimeError(f"API menolak request (HTTP {response.status_code}): {detail[:500]}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("The API returned invalid JSON and could not be parsed.") from exc

    if not isinstance(payload, dict):
        raise ValueError("The API returned an invalid JSON structure.")
    if "raw" not in payload:
        raise ValueError("The API response does not contain the required 'raw' key.")
    return payload


def safe_refresh_snapshot(
    search_url: str,
    max_pages: int = 1,
    live_path: str | Path | None = None,
    history_path: str | Path | None = None,
) -> Dict[str, Any]:
    """Fetch a single-page OLX search, validate/clean the data, and persist the result.

    This is the user-triggered refresh path and will not run automatically during rerenders.
    """
    live_path = Path(live_path) if live_path else LIVE_PATH
    history_path = Path(history_path) if history_path else HISTORY_PATH

    response = fetch_datawebot(search_url=search_url, max_pages=max_pages)
    meta = response.get("meta", {}) if isinstance(response, dict) else {}
    usage_meta = _extract_usage_meta(meta)

    fetched_at = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M:%S")
    parsed = parse_api_response_to_dataframe(response, fetched_at=fetched_at)
    price_values = pd.to_numeric(parsed.get("price"), errors="coerce")
    year_values = pd.to_numeric(parsed.get("year"), errors="coerce")
    mileage_values = pd.to_numeric(parsed.get("mileage_km"), errors="coerce")
    current_year = datetime.now(ZoneInfo("Asia/Jakarta")).year
    quality = {
        "invalid_or_missing_price": int((price_values.isna() | price_values.le(0)).sum()),
        "invalid_year": int((year_values.notna() & ~year_values.between(1950, current_year + 1)).sum()),
        "invalid_mileage": int((mileage_values.notna() & mileage_values.lt(0)).sum()),
        "missing_listing_id": int(parsed["listing_id"].fillna("").astype(str).str.strip().eq("").sum()),
    }
    validated = validate_listing_dataframe(parsed)
    df = filter_dki_jakarta(validated)

    if df.empty:
        return {
            "status": "empty",
            "message": "API merespons, tetapi tidak ada listing valid berlokasi DKI Jakarta pada hasil yang diterima.",
            "raw_count": len(response.get("raw", [])),
            "validated_count": len(validated),
            "live_count": 0,
            "filtered_count": 0,
            "quality": quality,
            "last_successful_fetch": None,
            "used_credits": usage_meta.get("used"),
            "remaining_credits": usage_meta.get("remaining"),
        }

    # Keep the last good pair of CSVs if either persistence step fails.
    previous_live = live_path.read_bytes() if live_path.exists() else None
    previous_history = history_path.read_bytes() if history_path.exists() else None
    try:
        append_history_snapshot(df, history_path)
        save_dataframe_atomic(df, live_path)
        if supabase_is_configured():
            save_supabase_snapshot(df)
    except Exception:
        for path, previous in ((live_path, previous_live), (history_path, previous_history)):
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = path.with_suffix(path.suffix + ".rollback")
                temp_path.write_bytes(previous)
                os.replace(temp_path, path)
        raise

    return {
        "status": "success",
        "message": f"Refresh berhasil. {len(df)} listing valid DKI Jakarta tersimpan.",
        "live_count": int(len(df)),
        "raw_count": len(response.get("raw", [])),
        "validated_count": int(len(validated)),
        "filtered_count": int(len(df)),
        "quality": quality,
        "last_successful_fetch": fetched_at,
        "used_credits": usage_meta.get("used"),
        "remaining_credits": usage_meta.get("remaining"),
        "storage_backend": "Supabase + CSV lokal" if supabase_is_configured() else "CSV lokal",
    }
