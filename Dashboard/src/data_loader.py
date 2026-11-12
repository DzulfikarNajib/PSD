"""Load and persist the live and historical OLX datasets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd

from src.preprocessing import is_dki_jakarta, parse_mileage_km
from src.supabase_store import is_configured as supabase_is_configured
from src.supabase_store import latest_timestamp as supabase_latest_timestamp
from src.supabase_store import load_latest_snapshot

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LIVE_PATH = DATA_DIR / "olx_live.csv"
HISTORY_PATH = DATA_DIR / "olx_history.csv"
HISTORICAL_PATH = DATA_DIR / "PSD_DATA_MOBIL_JAKARTA_FULL.csv"
DKI_CITIES = {"jakarta pusat", "jakarta selatan", "jakarta timur", "jakarta barat", "jakarta utara"}


def _parse_engine_band(value) -> float:
    """Convert source engine-capacity bands into representative cc midpoints."""
    import re
    if pd.isna(value):
        return float("nan")
    text = str(value).lower().replace(".", "").replace(",", "")
    nums = [int(n) for n in re.findall(r"\d+", text)]
    if "<" in text and nums:
        return nums[0] / 2
    if ">" in text and len(nums) >= 2:
        return (nums[0] + nums[1]) / 2
    if ">" in text and nums:
        return nums[0] * 1.25
    return sum(nums[:2]) / min(len(nums), 2) if nums else float("nan")


def load_historical_data() -> pd.DataFrame:
    """Load the supplied Excel-derived dataset as clean, DKI-only observations."""
    if not HISTORICAL_PATH.exists():
        return pd.DataFrame()
    try:
        raw = pd.read_csv(HISTORICAL_PATH)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return pd.DataFrame()
    required = {"URL_Detail", "Harga_IDR", "Provinsi", "Kota_Kabupaten", "Merk", "Model", "Tahun", "Jarak_Tempuh"}
    if not required.issubset(raw.columns):
        return pd.DataFrame()
    data = pd.DataFrame({
        "listing_id": raw["URL_Detail"].fillna("").astype(str).str.strip().str.split("?").str[0].str.rstrip("/").str.lower(),
        "make": raw["Merk"], "model": raw["Model"], "variant": raw["Judul"] if "Judul" in raw else "",
        "price": pd.to_numeric(raw["Harga_IDR"], errors="coerce"),
        "year": raw["Tahun"].map(lambda x: pd.to_numeric(str(x), errors="coerce") if str(x).strip().isdigit() else float("nan")),
        "mileage_km": raw["Jarak_Tempuh"].map(parse_mileage_km),
        "engine_cc": raw["Kapasitas_Mesin"].map(_parse_engine_band) if "Kapasitas_Mesin" in raw else float("nan"),
        "fuel_type": raw["Tipe_Bahan_Bakar"] if "Tipe_Bahan_Bakar" in raw else "",
        "transmission": raw["Transmisi"] if "Transmisi" in raw else "",
        "body_type": raw["Tipe_Bodi"] if "Tipe_Bodi" in raw else "",
        "location": raw["Kota_Kabupaten"], "province": raw["Provinsi"],
        "url": raw["URL_Detail"], "fetched_at": pd.NA,
    })
    data["location"] = data["location"].fillna("").astype(str).str.strip()
    data["province"] = data["province"].fillna("").astype(str).str.strip().str.lower()
    data = data[data["province"].isin({"jakarta d.k.i.", "dki jakarta", "daerah khusus ibukota jakarta"})]
    data = data[data["location"].str.lower().isin(DKI_CITIES)]
    data = data[data["listing_id"].ne("") & data["price"].ge(1_000_000)]
    data = data.drop_duplicates("listing_id", keep="first")
    for col in ("make", "model", "variant", "fuel_type", "transmission", "body_type"):
        if col in data:
            data[col] = data[col].fillna("").astype(str).str.strip()
    data["location_normalized"] = data["location"].str.lower()
    data["image_url"] = ""
    data["color"] = ""
    data["seller_type"] = ""
    return data.reset_index(drop=True)


def ensure_data_files() -> None:
    """Ensure the data directory and CSV files exist with a safe header row."""
    DATA_DIR.mkdir(exist_ok=True)
    for csv_path in (LIVE_PATH, HISTORY_PATH):
        if not csv_path.exists():
            csv_path.write_text(
                "listing_id,make,model,variant,price,price_text,year,mileage_range,mileage_km,engine_capacity,engine_cc,fuel_type,transmission,body_type,color,location,location_normalized,image_url,url,posted_at,seller_type,fetched_at\n",
                encoding="utf-8",
            )


def load_live_data() -> pd.DataFrame:
    """Load the latest valid DKI Jakarta listings."""
    if supabase_is_configured():
        try:
            cloud_data = load_latest_snapshot()
            if not cloud_data.empty:
                if "location" in cloud_data:
                    cloud_data = cloud_data[cloud_data["location"].map(is_dki_jakarta)].copy()
                return cloud_data.reset_index(drop=True)
        except Exception:
            # Keep the saved local snapshot usable if the cloud database is temporarily unavailable.
            pass
    ensure_data_files()
    try:
        df = pd.read_csv(LIVE_PATH)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return pd.DataFrame()
    if "location" in df:
        df = df[df["location"].map(is_dki_jakarta)].copy()
    return df


def load_history_data() -> pd.DataFrame:
    """Load the full historical observation archive."""
    ensure_data_files()
    try:
        df = pd.read_csv(HISTORY_PATH)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return pd.DataFrame()
    return df


def get_last_updated_text() -> str:
    """Return the most recent available fetch timestamp or a default message."""
    if supabase_is_configured():
        try:
            timestamp = supabase_latest_timestamp()
            if timestamp:
                parsed = pd.to_datetime(timestamp, errors="coerce", utc=True)
                if pd.notna(parsed):
                    return parsed.tz_convert(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")
        except Exception:
            pass
    df = load_history_data()
    if df.empty or "fetched_at" not in df.columns:
        return "Belum ada snapshot history."
    timestamps = pd.to_datetime(df["fetched_at"], errors="coerce", utc=True).dropna()
    if timestamps.empty:
        return "Belum ada snapshot history."
    return timestamps.max().tz_convert(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")
