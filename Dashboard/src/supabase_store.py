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
    "location_normalized", "image_url", "url", "posted_at", "seller_type", "data_source",
]
EXCEL_SEED_SNAPSHOT = "00000000-0000-0000-0000-000000000001"


def _credentials():
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    # Accept either the project root or the REST base URL. All request helpers
    # append /rest/v1/{table}, so retaining that suffix would create an invalid path.
    if url.lower().endswith("/rest/v1"):
        url = url[:-8].rstrip("/")
    return url, os.getenv("SUPABASE_SECRET_KEY", "").strip()


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
    rows["data_source"] = "olx_refresh"
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


def _get(params, offset=0, limit=1000):
    endpoint, headers = _headers()
    headers["Range-Unit"] = "items"
    headers["Range"] = f"{offset}-{offset + limit - 1}"
    response = requests.get(endpoint, params=params, headers=headers, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Gagal membaca Supabase (HTTP {response.status_code}): {response.text[:400]}")
    return response.json()


def load_latest_snapshot() -> pd.DataFrame:
    latest = _get({"select": "snapshot_id,fetched_at", "data_source": "eq.olx_refresh", "order": "fetched_at.desc.nullslast", "limit": "1"})
    if not latest:
        return pd.DataFrame()
    return pd.DataFrame(_get({"select": "*", "snapshot_id": f"eq.{latest[0]['snapshot_id']}", "order": "listing_id.asc"}))


def load_snapshot_archive() -> pd.DataFrame:
    """Read all saved OLX observations in bounded pages; never calls the paid source."""
    rows, offset = [], 0
    while True:
        batch = _get({
        "select": "*", "data_source": "eq.olx_refresh",
            "order": "fetched_at.asc,listing_id.asc",
        }, offset=offset)
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += len(batch)
    return pd.DataFrame(rows)


def load_excel_seed() -> pd.DataFrame:
    """Read the idempotently imported Excel archive, if present."""
    rows, offset = [], 0
    while True:
        batch = _get({"select": "*", "data_source": "eq.excel_scrape", "order": "listing_id.asc"}, offset=offset)
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += len(batch)
    return pd.DataFrame(rows)


def import_excel_seed(data: pd.DataFrame) -> int:
    """Idempotently seed Excel rows; a stable snapshot ID prevents duplicate imports."""
    rows = data.copy().drop_duplicates("listing_id", keep="first")
    rows["snapshot_id"] = EXCEL_SEED_SNAPSHOT
    rows["fetched_at"] = None
    rows["data_source"] = "excel_scrape"
    payload = rows.reindex(columns=FIELDS).astype(object).where(pd.notna(rows.reindex(columns=FIELDS)), None)
    records = payload.to_dict("records")
    for record in records:
        for key, value in record.items():
            if hasattr(value, "item"):
                record[key] = value.item()
    endpoint, headers = _headers("resolution=ignore-duplicates,return=representation")
    inserted = 0
    for start in range(0, len(records), 500):
        response = requests.post(
            endpoint, params={"on_conflict": "snapshot_id,listing_id"}, json=records[start:start + 500],
            headers=headers, timeout=60,
        )
        if not response.ok:
            raise RuntimeError(f"Gagal mengimpor arsip Excel ke Supabase (HTTP {response.status_code}): {response.text[:400]}")
        inserted += len(response.json()) if response.content else 0
    return inserted


def latest_timestamp():
    rows = _get({"select": "fetched_at", "data_source": "eq.olx_refresh", "order": "fetched_at.desc.nullslast", "limit": "1"})
    return rows[0]["fetched_at"] if rows else None
