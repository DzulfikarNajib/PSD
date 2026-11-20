"""Load and persist the live and historical OLX datasets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from src.preprocessing import HIGH_PRICE_OUTLIER_REASON, enrich_engine_cc, is_dki_jakarta, normalize_timestamp_utc, parse_engine_cc, parse_mileage_km, preprocess_listing_dataset, split_financing_listings
from src.supabase_store import is_configured as supabase_is_configured
from src.supabase_store import latest_timestamp as supabase_latest_timestamp
from src.supabase_store import load_latest_snapshot
from src.supabase_store import load_snapshot_archive, load_excel_seed, load_dataset_seed

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LIVE_PATH = DATA_DIR / "olx_live.csv"
HISTORY_PATH = DATA_DIR / "olx_history.csv"
HISTORICAL_PATH = DATA_DIR / "PSD_DATA_MOBIL_JAKARTA_FULL.csv"
ACTIVE_DATASET_PATH = DATA_DIR / "olx_jakarta_mobil_bekas_full.csv"
DKI_CITIES = {"jakarta pusat", "jakarta selatan", "jakarta timur", "jakarta barat", "jakarta utara"}
_LAST_DATA_SOURCE_STATUS = {
    "mode": "local",
    "message": "Menggunakan data lokal yang tersimpan.",
}


def _set_data_source_status(mode: str, message: str) -> None:
    """Keep source status per Streamlit session, with a safe fallback outside the app."""
    global _LAST_DATA_SOURCE_STATUS
    _LAST_DATA_SOURCE_STATUS = {"mode": mode, "message": message}
    try:
        import streamlit as st

        st.session_state["automatch_data_source_status"] = dict(_LAST_DATA_SOURCE_STATUS)
    except Exception:
        pass


def get_data_source_status() -> dict:
    """Return the last archive-read status for the current user session."""
    try:
        import streamlit as st

        status = st.session_state.get("automatch_data_source_status")
        if isinstance(status, dict):
            return status
    except Exception:
        pass
    return dict(_LAST_DATA_SOURCE_STATUS)


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
    """Load the active OLX archive as clean, deduplicated DKI observations."""
    return load_historical_data_with_audit()[0]


def load_historical_data_with_audit() -> tuple[pd.DataFrame, dict]:
    """Load the active source and return both cleaned rows and their audit."""
    if ACTIVE_DATASET_PATH.exists():
        try:
            raw = pd.read_csv(ACTIVE_DATASET_PATH)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
            return pd.DataFrame(), {}
        data, audit = preprocess_listing_dataset(raw)
        data["data_source"] = "OLX Indonesia"
        audit["source"] = "OLX Indonesia - DKI Jakarta"
        data.attrs["preprocessing_audit"] = audit
        return data, audit

    if not HISTORICAL_PATH.exists():
        return pd.DataFrame(), {}
    try:
        raw = pd.read_csv(HISTORICAL_PATH)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return pd.DataFrame(), {}
    required = {"URL_Detail", "Harga_IDR", "Provinsi", "Kota_Kabupaten", "Merk", "Model", "Tahun", "Jarak_Tempuh"}
    if not required.issubset(raw.columns):
        return pd.DataFrame(), {}
    data = pd.DataFrame({
        "listing_id": raw["URL_Detail"].fillna("").astype(str).str.strip().str.split("?").str[0].str.rstrip("/").str.lower(),
        "make": raw["Merk"], "model": raw["Model"], "variant": raw["Judul"] if "Judul" in raw else "",
        "price": pd.to_numeric(raw["Harga_IDR"], errors="coerce"),
        "year": raw["Tahun"].map(lambda x: pd.to_numeric(str(x), errors="coerce") if str(x).strip().isdigit() else float("nan")),
        "mileage_km": raw["Jarak_Tempuh"].map(parse_mileage_km),
        "engine_cc": raw["Kapasitas_Mesin"].map(parse_engine_cc) if "Kapasitas_Mesin" in raw else float("nan"),
        "fuel_type": raw["Tipe_Bahan_Bakar"] if "Tipe_Bahan_Bakar" in raw else "",
        "transmission": raw["Transmisi"] if "Transmisi" in raw else "",
        "body_type": raw["Tipe_Bodi"] if "Tipe_Bodi" in raw else "",
        "location": raw["Kota_Kabupaten"], "province": raw["Provinsi"],
        "url": raw["URL_Detail"], "fetched_at": pd.NA,
    })
    data["image_url"] = ""
    data["color"] = ""
    data["seller_type"] = ""
    data["data_source"] = "Dataset Excel"
    data, audit = preprocess_listing_dataset(data)
    data["data_source"] = "Dataset Excel"
    audit["source"] = "Dataset Excel - DKI Jakarta"
    data.attrs["preprocessing_audit"] = audit
    return data, audit


def _listing_identity(frame: pd.DataFrame) -> pd.Series:
    url = frame.get("url", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    listing_id = frame.get("listing_id", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    identity = url.where(url.str.lower().str.startswith("http"), listing_id)
    return identity.str.split("?").str[0].str.rstrip("/").str.lower()


def _analytical_financing_filter(frame: pd.DataFrame) -> pd.DataFrame:
    """Exclude likely DP/credit offers from analytical views, leaving stored files intact."""
    normalized = frame.copy()
    if "fetched_at" in normalized:
        normalized["fetched_at"] = normalized["fetched_at"].map(normalize_timestamp_utc)
    eligible, flagged = split_financing_listings(normalized)
    return eligible


def _dki_scope(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the dashboard's DKI-only scope to any stored listing source."""
    if frame.empty:
        return frame.copy()
    location = frame.get("location", pd.Series("", index=frame.index)).fillna("").astype(str)
    normalized = frame.get("location_normalized", pd.Series("", index=frame.index)).fillna("").astype(str)
    location = location.where(location.str.strip().ne(""), normalized)
    return frame.loc[location.map(is_dki_jakarta)].copy()


@st.cache_data(show_spinner=False, ttl=3600)
def load_combined_archive() -> pd.DataFrame:
    """Load the active cleaned dataset; use legacy merging only as a fallback."""
    excel = load_historical_data()
    preprocessing_audit = excel.attrs.get("preprocessing_audit", {})
    local_excluded_financing_count = int(excel.attrs.get("excluded_financing_count", 0))

    # The migrated OLX dataset is the canonical analytical source. Keep older
    # Excel seeds and Supabase snapshots out of the full archive to avoid
    # silently inflating the cleaned 6.3k-row dataset with legacy records.
    if preprocessing_audit.get("source") == "OLX Indonesia - DKI Jakarta":
        archive = excel.copy()
        archive["source_origins"] = "OLX Indonesia"
        archive["observation_count"] = 1
        archive.attrs["excluded_financing_count"] = local_excluded_financing_count
        archive.attrs["excluded_outlier_price_count"] = int(excel.attrs.get("excluded_outlier_price_count", 0))
        archive.attrs["preprocessing_audit"] = preprocessing_audit
        _set_data_source_status(
            "local",
            "Menggunakan dataset OLX Indonesia yang sudah dibersihkan. Arsip Excel lama dan snapshot tersedia sebagai sumber terpisah.",
        )
        return archive.reset_index(drop=True)

    seeded, dataset_seed, snapshots = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    if supabase_is_configured():
        try:
            seeded, dataset_seed, snapshots = load_excel_seed(), load_dataset_seed(), load_snapshot_archive()
            if seeded.empty and dataset_seed.empty and snapshots.empty:
                _set_data_source_status("fallback", "Supabase belum berisi arsip. Menampilkan data lokal yang tersedia.")
            else:
                _set_data_source_status("cloud", "Arsip Supabase berhasil dibaca; dataset lokal ikut digabung bila tersedia.")
        except Exception:
            _set_data_source_status("fallback", "Supabase tidak dapat dibaca. Menampilkan salinan lokal bila tersedia; periksa koneksi dan konfigurasi database.")
    else:
        _set_data_source_status("local", "Menggunakan data lokal. Supabase belum dikonfigurasi untuk sesi ini.")
    if not seeded.empty:
        seeded["data_source"] = "Dataset Excel"
        excel = pd.concat([excel, seeded], ignore_index=True, sort=False)
    if not dataset_seed.empty:
        dataset_seed["data_source"] = "Dataset OLX Indonesia"
        excel = pd.concat([excel, dataset_seed], ignore_index=True, sort=False)
    if not snapshots.empty:
        snapshots["data_source"] = "Arsip snapshot OLX"
        snapshots = _dki_scope(snapshots)
    parts = [part for part in (excel, snapshots) if not part.empty]
    if not parts:
        return pd.DataFrame()
    combined = pd.concat(parts, ignore_index=True, sort=False)
    combined["_identity"] = _listing_identity(combined)
    combined = combined[combined["_identity"].ne("")].copy()
    combined["fetched_at"] = pd.to_datetime(combined.get("fetched_at"), errors="coerce", utc=True)
    is_olx = combined["data_source"].eq("Arsip snapshot OLX")
    snapshot_ids = combined.get("snapshot_id", pd.Series("", index=combined.index)).fillna("").astype(str)
    combined["_observation_identity"] = combined["_identity"] + "|" + combined["data_source"]
    combined.loc[is_olx, "_observation_identity"] = (
        combined.loc[is_olx, "_identity"] + "|" + snapshot_ids.loc[is_olx]
    )
    combined = combined.drop_duplicates("_observation_identity", keep="last")
    combined["_source_priority"] = combined["data_source"].eq("Arsip snapshot OLX").astype(int)
    combined = combined.sort_values(["fetched_at", "_source_priority"], na_position="first")
    combined["observation_count"] = combined.groupby("_identity")["_identity"].transform("size")
    origins = combined.groupby("_identity")["data_source"].agg(
        lambda values: " + ".join(sorted(set(values.dropna().astype(str))))
    )
    combined = combined.drop_duplicates("_identity", keep="last")
    combined["source_origins"] = combined["_identity"].map(origins)
    combined["listing_id"] = combined["_identity"]
    combined = combined.drop(columns=["_identity", "_observation_identity", "_source_priority"])
    combined, flagged = split_financing_listings(combined)
    if "financing_flag_reason" in flagged:
        flagged_financing = flagged["financing_flag_reason"].ne(HIGH_PRICE_OUTLIER_REASON)
        combined.attrs["excluded_financing_count"] = local_excluded_financing_count + int(flagged_financing.sum())
    else:
        combined.attrs["excluded_financing_count"] = local_excluded_financing_count
    combined.attrs["excluded_outlier_price_count"] = int(excel.attrs.get("excluded_outlier_price_count", 0)) + len(flagged)
    combined.attrs["preprocessing_audit"] = preprocessing_audit
    return combined.reset_index(drop=True)


def load_training_archive() -> pd.DataFrame:
    """Provide canonical cleaned data for training, with legacy merge fallback."""
    excel = load_historical_data()
    excluded_financing_count = int(excel.attrs.get("excluded_financing_count", 0))
    if excel.attrs.get("preprocessing_audit", {}).get("source") == "OLX Indonesia - DKI Jakarta":
        _set_data_source_status("local", "Pelatihan memakai dataset OLX Indonesia aktif yang sudah dibersihkan.")
        return excel
    if not supabase_is_configured():
        _set_data_source_status("local", "Menggunakan arsip lokal untuk evaluasi model. Supabase belum dikonfigurasi.")
        return excel
    try:
        seeded, dataset_seed, snapshots = load_excel_seed(), load_dataset_seed(), load_snapshot_archive()
    except Exception:
        _set_data_source_status("fallback", "Supabase tidak dapat dibaca. Pelatihan memakai arsip lokal yang tersedia.")
        return excel
    _set_data_source_status("cloud", "Arsip Supabase berhasil dibaca untuk evaluasi model.")
    pieces = [frame for frame in (excel, seeded, dataset_seed, snapshots) if not frame.empty]
    combined = pd.concat(pieces, ignore_index=True, sort=False) if pieces else excel
    combined.attrs["excluded_financing_count"] = excluded_financing_count
    combined.attrs["preprocessing_audit"] = excel.attrs.get("preprocessing_audit", {})
    if not combined.empty:
        combined["listing_id"] = _listing_identity(combined)
    return combined


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
                cloud_data["data_source"] = "Listing terbaru"
                _set_data_source_status("cloud", "Snapshot terbaru berhasil dibaca dari Supabase.")
                return _analytical_financing_filter(enrich_engine_cc(cloud_data)).reset_index(drop=True)
        except Exception:
            # Keep the saved local snapshot usable if the cloud database is temporarily unavailable.
            _set_data_source_status("fallback", "Supabase tidak dapat dibaca. Menampilkan snapshot lokal bila tersedia.")
        else:
            _set_data_source_status("fallback", "Belum ada snapshot di Supabase. Menampilkan snapshot lokal bila tersedia.")
    else:
        _set_data_source_status("local", "Menampilkan snapshot OLX lokal. Supabase belum dikonfigurasi.")
    ensure_data_files()
    try:
        df = pd.read_csv(LIVE_PATH)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return pd.DataFrame()
    if "location" in df:
        df = df[df["location"].map(is_dki_jakarta)].copy()
    return _analytical_financing_filter(enrich_engine_cc(df))


def load_history_data() -> pd.DataFrame:
    """Load the full historical observation archive."""
    if supabase_is_configured():
        try:
            observations = load_snapshot_archive()
            if not observations.empty:
                observations = _dki_scope(observations)
                observations["data_source"] = "Arsip snapshot OLX"
                _set_data_source_status("cloud", "Riwayat snapshot berhasil dibaca dari Supabase.")
                return _analytical_financing_filter(enrich_engine_cc(observations)).reset_index(drop=True)
        except Exception:
            _set_data_source_status("fallback", "Riwayat Supabase tidak dapat dibaca. Menampilkan riwayat lokal bila tersedia.")
        else:
            _set_data_source_status("fallback", "Riwayat Supabase belum tersedia. Menampilkan riwayat lokal bila ada.")
    else:
        _set_data_source_status("local", "Menampilkan riwayat OLX lokal. Supabase belum dikonfigurasi.")
    ensure_data_files()
    try:
        df = pd.read_csv(HISTORY_PATH)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return pd.DataFrame()
    return _analytical_financing_filter(enrich_engine_cc(_dki_scope(df))).reset_index(drop=True)


def get_last_updated_text() -> str:
    """Return the most recent available fetch timestamp or a default message."""
    if supabase_is_configured():
        try:
            timestamp = supabase_latest_timestamp()
            if timestamp:
                parsed = pd.to_datetime(timestamp, errors="coerce", utc=True)
                if pd.notna(parsed):
                    _set_data_source_status("cloud", "Waktu snapshot terbaru berhasil dibaca dari Supabase.")
                    return parsed.tz_convert(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")
        except Exception:
            _set_data_source_status("fallback", "Waktu snapshot Supabase tidak dapat dibaca. Waktu lokal ditampilkan bila tersedia.")
    df = load_history_data()
    if df.empty or "fetched_at" not in df.columns:
        return "Belum ada snapshot history."
    timestamps = pd.to_datetime(df["fetched_at"], errors="coerce", utc=True).dropna()
    if timestamps.empty:
        return "Belum ada snapshot history."
    return timestamps.max().tz_convert(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")
