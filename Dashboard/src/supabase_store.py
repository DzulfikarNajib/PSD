"""Optional durable snapshot storage backed by Supabase's PostgREST API."""

from __future__ import annotations

import os
import uuid
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
TABLE = "listing_snapshots"
FIELDS = [
    "snapshot_id", "fetched_at", "listing_id", "make", "model", "variant", "price", "year",
    "mileage_km", "engine_cc", "fuel_type", "transmission", "body_type", "color", "location",
    "location_normalized", "image_url", "url", "posted_at", "seller_type",
]


def _credentials():
    return os.getenv("SUPABASE_URL", "").rstrip("/"), os.getenv("SUPABASE_SECRET_KEY", "")


def is_configured() -> bool:
    url, key = _credentials()
    return bool(url and key)


def _headers(prefer=""):
    url, key = _credentials()
    if not url or not key:
        raise RuntimeError("Supabase belum dikonfigurasi. Atur SUPABASE_URL dan SUPABASE_SECRET_KEY di Secrets.")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    return f"{url}/rest/v1/{TABLE}", headers


def save_snapshot(data: pd.DataFrame) -> str:
    """Insert one complete refresh snapshot; duplicate listing IDs are removed."""
    snapshot_id = str(uuid.uuid4())
    rows = data.copy().drop_duplicates("listing_id", keep="first")
    timestamp = pd.to_datetime(rows["fetched_at"], errors="coerce")
    if timestamp.dt.tz is None:
        timestamp = timestamp.dt.tz_localize(ZoneInfo("Asia/Jakarta"))
    rows["fetched_at"] = timestamp.dt.tz_convert("UTC").astype(str)
    rows["snapshot_id"] = snapshot_id
    payload = rows.reindex(columns=FIELDS).astype(object).where(pd.notna(rows.reindex(columns=FIELDS)), None)
    records = payload.to_dict("records")
    for record in records:
        for key, value in record.items():
            if hasattr(value, "item"):
                record[key] = value.item()
    endpoint, headers = _headers("return=minimal")
    response = requests.post(endpoint, params={"on_conflict": "snapshot_id,listing_id"}, json=records, headers=headers, timeout=45)
    if not response.ok:
        raise RuntimeError(f"Gagal menyimpan snapshot ke Supabase (HTTP {response.status_code}): {response.text[:400]}")
    return snapshot_id


def _get(params):
    endpoint, headers = _headers()
    response = requests.get(endpoint, params=params, headers=headers, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Gagal membaca Supabase (HTTP {response.status_code}): {response.text[:400]}")
    return response.json()


def load_latest_snapshot() -> pd.DataFrame:
    latest = _get({"select": "snapshot_id,fetched_at", "order": "fetched_at.desc", "limit": "1"})
    if not latest:
        return pd.DataFrame()
    return pd.DataFrame(_get({"select": "*", "snapshot_id": f"eq.{latest[0]['snapshot_id']}", "order": "listing_id.asc"}))


def latest_timestamp():
    rows = _get({"select": "fetched_at", "order": "fetched_at.desc", "limit": "1"})
    return rows[0]["fetched_at"] if rows else None
