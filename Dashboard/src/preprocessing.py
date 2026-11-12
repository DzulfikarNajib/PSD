"""Parsing, validation, Jabodetabek filtering, and CSV persistence helpers."""

from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

DEFAULT_COLUMNS = [
    "listing_id", "make", "model", "variant", "price", "price_text", "year",
    "mileage_range", "mileage_km", "engine_capacity", "engine_cc", "fuel_type",
    "transmission", "body_type", "color", "location", "location_normalized",
    "image_url", "url", "posted_at", "seller_type", "fetched_at",
]
JABODETABEK_AREAS = ("jakarta pusat", "jakarta selatan", "jakarta timur", "jakarta barat", "jakarta utara", "bogor", "depok", "tangerang", "bekasi")
DKI_DISTRICTS = JABODETABEK_AREAS[:5]


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def parse_numeric(value) -> float:
    """Parse Indonesian formatted numbers (e.g. Rp 125.000.000)."""
    if pd.isna(value):
        return float("nan")
    text = str(value).strip().lower()
    matches = re.findall(r"\d+(?:[.,]\d+)*", text)
    if not matches:
        return float("nan")
    token = matches[0]
    if token.count(",") == 1 and len(token.rsplit(",", 1)[1]) <= 2:
        token = token.replace(".", "").replace(",", ".")
    else:
        token = token.replace(".", "").replace(",", "")
    return float(token)


def _range_values(value) -> list[float]:
    if pd.isna(value):
        return []
    text = str(value).lower()
    vals = []
    for token in re.findall(r"\d+(?:[.,]\d+)*", text):
        vals.append(parse_numeric(token))
    return vals


def parse_mileage_km(value) -> float:
    """Return exact km or range midpoint; ranges are represented by their midpoint."""
    values = _range_values(value)
    return sum(values[:2]) / min(len(values), 2) if values else float("nan")


def parse_engine_cc(value) -> float:
    """Convert engine capacity in liters to cc; otherwise preserve numeric cc."""
    if pd.isna(value):
        return float("nan")
    text = str(value).lower()
    token_match = re.search(r"\d+(?:[.,]\d+)*", text)
    if not token_match:
        return float("nan")
    token = token_match.group(0)
    if re.search(r"(?:\d\s*l\b|liter|litre)", text):
        number = float(token.replace(",", "."))
        return number * 1000
    return parse_numeric(token)


def normalize_location(value) -> str:
    """Normalize a location to a Jabodetabek area when it can be identified."""
    text = normalize_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    # Match satellite cities before generic regency/city labels; require whole words.
    for area in ("depok", "bekasi", "tangerang", "bogor", *JABODETABEK_AREAS[:5]):
        if re.search(rf"\b{re.escape(area)}\b", text):
            return area
    return text


def is_jabodetabek(value) -> bool:
    return normalize_location(value) in JABODETABEK_AREAS


def is_dki_jakarta(value) -> bool:
    return normalize_location(value) in DKI_DISTRICTS


def filter_dki_jakarta(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "location" not in df:
        return df.copy()
    result = df.copy()
    result["location_normalized"] = result["location"].map(normalize_location)
    return result[result["location_normalized"].isin(DKI_DISTRICTS)].copy()


def parse_api_response_to_dataframe(response: dict, fetched_at: str | None = None) -> pd.DataFrame:
    raw = response.get("raw") if isinstance(response, dict) else None
    if not isinstance(raw, list):
        raise ValueError("Respons API tidak memiliki daftar listing yang valid pada 'raw'.")
    timestamp = fetched_at or datetime.now(ZoneInfo("Asia/Jakarta")).isoformat(timespec="seconds")
    rows = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        row = {column: item.get(column) for column in DEFAULT_COLUMNS if column in item}
        # Keep all expected source fields, even when the API omits some of them.
        for column in DEFAULT_COLUMNS:
            row.setdefault(column, None)
        row["price"] = parse_numeric(row["price"])
        row["year"] = parse_numeric(row["year"])
        row["mileage_km"] = parse_mileage_km(row["mileage_range"])
        row["engine_cc"] = parse_engine_cc(row["engine_capacity"])
        row["location_normalized"] = normalize_location(row["location"])
        row["fetched_at"] = timestamp
        for column in ("listing_id", "make", "model", "variant", "fuel_type", "transmission", "body_type", "color", "location", "image_url", "url", "posted_at", "seller_type", "price_text", "mileage_range", "engine_capacity"):
            row[column] = normalize_text(row[column])
        rows.append(row)
    return pd.DataFrame(rows, columns=DEFAULT_COLUMNS)


def validate_listing_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=DEFAULT_COLUMNS)
    result = df.copy()
    for column in DEFAULT_COLUMNS:
        if column not in result:
            result[column] = pd.NA
    result = result[DEFAULT_COLUMNS]
    result["price"] = pd.to_numeric(result["price"], errors="coerce")
    result["year"] = pd.to_numeric(result["year"], errors="coerce")
    result["mileage_km"] = pd.to_numeric(result["mileage_km"], errors="coerce")
    result["engine_cc"] = pd.to_numeric(result["engine_cc"], errors="coerce")
    result["location_normalized"] = result["location"].map(normalize_location)
    result["listing_id"] = result["listing_id"].map(normalize_text)
    result = result[result["listing_id"].ne("") & result["price"].gt(0)]
    current_year = datetime.now(ZoneInfo("Asia/Jakarta")).year
    result = result[result["year"].between(1950, current_year + 1) | result["year"].isna()]
    result = result[result["mileage_km"].ge(0) | result["mileage_km"].isna()]
    return result.drop_duplicates(subset=["listing_id"], keep="first").reset_index(drop=True)


def filter_jabodetabek(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "location" not in df:
        return df.copy()
    result = df.copy()
    result["location_normalized"] = result["location"].map(normalize_location)
    return result[result["location_normalized"].isin(JABODETABEK_AREAS)].copy()


def save_dataframe_atomic(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(handle)
    try:
        df.to_csv(temp_name, index=False)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def append_history_snapshot(df: pd.DataFrame, history_path: str | Path) -> None:
    """Append snapshot rows atomically; same listing may recur at another timestamp."""
    if df.empty:
        return
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    incoming = df.reindex(columns=DEFAULT_COLUMNS)
    if path.exists() and path.stat().st_size:
        existing = pd.read_csv(path)
        combined = pd.concat([existing.reindex(columns=DEFAULT_COLUMNS), incoming], ignore_index=True)
    else:
        combined = incoming.copy()
    combined = combined.drop_duplicates(subset=["listing_id", "fetched_at"], keep="first")
    save_dataframe_atomic(combined, path)


def build_live_dataset_from_response(response: dict, fetched_at: str | None = None) -> pd.DataFrame:
    parsed = parse_api_response_to_dataframe(response, fetched_at=fetched_at)
    validated = validate_listing_dataframe(parsed)
    return filter_dki_jakarta(validated).reindex(columns=DEFAULT_COLUMNS)
