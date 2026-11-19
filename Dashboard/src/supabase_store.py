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
ACTIVE_DATASET_SNAPSHOT = "00000000-0000-0000-0000-000000000003"
INTEGER_FIELDS = ("price", "year", "mileage_km", "engine_cc")


def _credentials():
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    # Accept either the project root or the REST base URL. All request helpers
    # append /rest/v1/{table}, so retaining that suffix would create an invalid path.
    while url.lower().endswith("/rest/v1"):
        url = url[:-8].rstrip("/")
    return url, os.getenv("SUPABASE_SECRET_KEY", "").strip()


def is_configured() -> bool:
    if os.getenv("AUTOMATCH_OFFLINE") == "1":
        return False
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


def _records_for_insert(data: pd.DataFrame) -> list[dict]:
    """Serialize numeric columns as PostgreSQL integers where the table expects them."""
    rows = data.copy()
    for column in INTEGER_FIELDS:
        if column in rows:
            values = pd.to_numeric(rows[column], errors="coerce").round()
            rows[column] = values.astype("Int64")
    payload = rows.reindex(columns=FIELDS).astype(object).where(lambda frame: pd.notna(frame), None)
    records = payload.to_dict("records")
    for record in records:
        for key, value in record.items():
            if hasattr(value, "item"):
                record[key] = value.item()
    return records


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
    records = _records_for_insert(rows)
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


def load_dataset_seed() -> pd.DataFrame:
    """Read the active, cleaned OLX dataset imported as a stable seed."""
    rows, offset = [], 0
    while True:
        batch = _get({"select": "*", "data_source": "eq.olx_dataset", "order": "listing_id.asc"}, offset=offset)
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
    records = _records_for_insert(rows)
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


def import_dataset_seed(
    data: pd.DataFrame,
    snapshot_id: str = ACTIVE_DATASET_SNAPSHOT,
) -> int:
    """Upsert the current cleaned OLX dataset under a seed snapshot ID."""
    rows = data.copy().drop_duplicates("listing_id", keep="first")
    rows["snapshot_id"] = snapshot_id
    rows["data_source"] = "olx_dataset"
    records = _records_for_insert(rows)
    endpoint, headers = _headers("resolution=merge-duplicates,return=representation")
    inserted = 0
    for start in range(0, len(records), 500):
        response = requests.post(
            endpoint, params={"on_conflict": "snapshot_id,listing_id"}, json=records[start:start + 500],
            headers=headers, timeout=60,
        )
        if not response.ok:
            raise RuntimeError(f"Gagal mengimpor dataset OLX ke Supabase (HTTP {response.status_code}): {response.text[:400]}")
        inserted += len(response.json()) if response.content else 0
    return inserted


def replace_dataset_seed(data: pd.DataFrame) -> dict[str, int]:
    """Publish the new clean dataset, then remove only superseded seed rows.

    Refresh snapshots (``olx_refresh``) are retained. The new dataset is fully
    upserted before deleting the old Excel seed and older dataset seed IDs.
    """
    if data.empty or "listing_id" not in data:
        raise ValueError("Dataset bersih kosong atau tidak memiliki listing_id.")
    listing_ids = data["listing_id"].fillna("").astype(str).str.strip()
    if listing_ids.eq("").any():
        raise ValueError("Dataset bersih masih memiliki listing_id kosong.")

    # A fresh seed ID makes every run a full replacement, so records removed
    # from the source CSV cannot linger in the active dataset after an upsert.
    new_snapshot_id = str(uuid.uuid4())
    expected_rows = int(listing_ids.nunique())
    synced = import_dataset_seed(data, snapshot_id=new_snapshot_id)
    if synced != expected_rows:
        raise RuntimeError(
            f"Sinkronisasi seed tidak lengkap ({synced}/{expected_rows} baris terkonfirmasi); "
            "seed lama dipertahankan."
        )

    endpoint, headers = _headers("return=minimal")

    def count_rows(params: dict[str, str]) -> int:
        count_headers = dict(headers)
        count_headers["Prefer"] = "count=exact"
        count_headers["Range-Unit"] = "items"
        count_headers["Range"] = "0-0"
        response = requests.get(
            endpoint, params={"select": "listing_id", **params},
            headers=count_headers, timeout=60,
        )
        if not response.ok:
            raise RuntimeError(
                f"Gagal memeriksa seed lama di Supabase (HTTP {response.status_code}): "
                f"{response.text[:400]}"
            )
        content_range = response.headers.get("Content-Range", "")
        total = content_range.rsplit("/", 1)[-1]
        if total.isdigit():
            return int(total)
        raise RuntimeError("Supabase tidak mengembalikan jumlah baris seed lama yang valid.")

    old_dataset_filter = {
        "data_source": "eq.olx_dataset",
        "snapshot_id": f"neq.{new_snapshot_id}",
    }
    old_dataset_missing_id_filter = {
        "data_source": "eq.olx_dataset",
        "snapshot_id": "is.null",
    }
    old_excel_filter = {"data_source": "eq.excel_scrape"}
    old_dataset_count = (
        count_rows(old_dataset_filter) + count_rows(old_dataset_missing_id_filter)
    )
    old_excel_count = count_rows(old_excel_filter)

    def delete_rows(params: dict[str, str]) -> int:
        response = requests.delete(endpoint, params=params, headers=headers, timeout=60)
        if not response.ok:
            raise RuntimeError(f"Gagal membersihkan seed lama di Supabase (HTTP {response.status_code}): {response.text[:400]}")
        return len(response.json()) if response.content else 0

    delete_rows(old_dataset_filter)
    delete_rows(old_dataset_missing_id_filter)
    delete_rows(old_excel_filter)
    remaining_old_dataset = count_rows(old_dataset_filter)
    remaining_old_dataset += count_rows(old_dataset_missing_id_filter)
    remaining_old_excel = count_rows(old_excel_filter)
    active_seed_count = count_rows({
        "data_source": "eq.olx_dataset",
        "snapshot_id": f"eq.{new_snapshot_id}",
    })
    if remaining_old_dataset or remaining_old_excel or active_seed_count != expected_rows:
        raise RuntimeError(
            "Verifikasi penggantian seed Supabase gagal: seed lama masih tersisa atau "
            f"jumlah seed baru tidak cocok ({active_seed_count}/{expected_rows})."
        )
    return {
        "dataset_rows_synced": synced,
        "old_dataset_rows_removed": old_dataset_count,
        "old_excel_rows_removed": old_excel_count,
    }


def latest_timestamp():
    rows = _get({"select": "fetched_at", "data_source": "eq.olx_refresh", "order": "fetched_at.desc.nullslast", "limit": "1"})
    return rows[0]["fetched_at"] if rows else None
