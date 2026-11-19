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
JABODETABEK_AREAS = ("jakarta pusat", "jakarta selatan", "jakarta timur", "jakarta barat", "jakarta utara", "kepulauan seribu", "bogor", "depok", "tangerang", "bekasi")
DKI_DISTRICTS = (*JABODETABEK_AREAS[:5], "kepulauan seribu")
MIN_ANALYSIS_PRICE = 30_000_000
FINANCING_PRICE_FLOOR = MIN_ANALYSIS_PRICE
MAX_ANALYSIS_PRICE = 30_000_000_000
HIGH_PRICE_OUTLIER_REASON = "Harga di atas Rp30 miliar, periksa kemungkinan salah input"
FINANCING_TEXT_PATTERN = re.compile(r"\b(?:dp|tdp|uang\s+muka|angsuran|cicilan|over\s*kredit|overkredit)\b", re.IGNORECASE)


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
    range_match = re.search(r"(\d+(?:[.,]\d+)*)\s*(?:-|s/d|sampai)\s*(\d+(?:[.,]\d+)*)", text)

    def to_cc(token: str) -> float:
        decimal_match = re.fullmatch(r"\d+[.,](\d{1,2})", token)
        number = float(token.replace(",", ".")) if decimal_match else parse_numeric(token)
        explicit_cc = re.search(r"\b(?:cc|cm3|cm³)\b", text)
        if re.search(r"\b(?:l|liter|litre)\b", text) or (decimal_match and number <= 8 and not explicit_cc):
            return number * 1000
        return number

    if range_match:
        lower, upper = (to_cc(token) for token in range_match.groups())
        return (lower + upper) / 2
    token_match = re.search(r"\d+(?:[.,]\d+)*", text)
    if not token_match:
        return float("nan")
    return to_cc(token_match.group(0))


def parse_engine_cc_from_variant(value) -> float:
    """Infer liters from a leading displacement token such as ``2.0 Bensin-MT``.

    OLX sometimes leaves ``engine_capacity`` empty but prefixes the variant with
    the engine size. Only accept a leading decimal displacement in a plausible
    liter range; arbitrary numbers later in a title are too ambiguous.
    """
    if pd.isna(value):
        return float("nan")
    match = re.match(r"^\s*(\d+[.,]\d{1,2})(?=\s|$)", str(value))
    if not match:
        return float("nan")
    liters = float(match.group(1).replace(",", "."))
    if not 0.5 <= liters <= 8:
        return float("nan")
    return liters * 1000


def enrich_engine_cc(data: pd.DataFrame) -> pd.DataFrame:
    """Fill missing engine sizes from capacity bands or explicit variant prefixes.

    A leading value such as ``2.0 Bensin-MT`` is treated as an approximate
    2.0-liter displacement. EVs remain missing because they have no combustion
    engine displacement.
    """
    if data.empty:
        return data.copy()
    result = data.copy()
    current = pd.to_numeric(result.get("engine_cc", pd.Series(float("nan"), index=result.index)), errors="coerce")
    capacity = result.get("engine_capacity", pd.Series("", index=result.index)).map(parse_engine_cc)
    current = current.where(current.notna(), capacity)
    is_electric = result.get("fuel_type", pd.Series("", index=result.index)).fillna("").astype(str).str.casefold().isin({"listrik", "electric", "ev", "bev"})
    variant = result.get("variant", pd.Series("", index=result.index)).map(parse_engine_cc_from_variant)
    inferred = current.isna() & ~is_electric & variant.notna()
    result["engine_cc"] = current.where(~inferred, variant)
    previous = result.get("engine_cc_inferred", pd.Series(False, index=result.index)).fillna(False).astype(bool)
    result["engine_cc_inferred"] = previous | inferred
    return result


def normalize_location(value) -> str:
    """Normalize a location to a Jabodetabek area when it can be identified."""
    text = normalize_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    # Match satellite cities before generic regency/city labels; require whole words.
    for area in ("kepulauan seribu", "depok", "bekasi", "tangerang", "bogor", *JABODETABEK_AREAS[:5]):
        if re.search(rf"\b{re.escape(area)}\b", text):
            return area
    return text


def _normalize_category(value, aliases: dict[str, str]) -> str:
    text = normalize_text(value)
    return aliases.get(text.casefold(), text)


def _timestamp_for_sort(values: pd.Series) -> pd.Series:
    """Parse mixed source timestamps consistently for choosing the latest row."""
    return pd.to_datetime(values, errors="coerce", utc=True)


def _latest_local_timestamp(values: pd.Series):
    timestamps = []
    for value in values.dropna():
        try:
            timestamp = pd.Timestamp(value)
        except (TypeError, ValueError):
            continue
        if pd.isna(timestamp):
            continue
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("Asia/Jakarta")
        else:
            timestamp = timestamp.tz_convert("Asia/Jakarta")
        timestamps.append(timestamp)
    return max(timestamps) if timestamps else None


def normalize_timestamp_utc(value):
    """Interpret naive source timestamps as Jakarta time and serialize as UTC."""
    if pd.isna(value) or not str(value).strip():
        return pd.NA
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return pd.NA
    if pd.isna(timestamp):
        return pd.NA
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("Asia/Jakarta")
    else:
        timestamp = timestamp.tz_convert("Asia/Jakarta")
    return timestamp.tz_convert("UTC").isoformat()


def preprocess_listing_dataset(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Normalize, deduplicate, scope to DKI, and remove non-comparable prices.

    Returns the cleaned listings and a stage-by-stage audit dictionary. Price
    values below Rp30 million are excluded as likely down-payment offers, while
    values above Rp30 billion are treated as probable entry errors. The latter
    threshold keeps the observed Rp22 billion luxury listings in this source.
    """
    raw_count = int(len(raw))
    data = raw.copy()
    for column in DEFAULT_COLUMNS:
        if column not in data:
            data[column] = pd.NA

    data["listing_id"] = data["listing_id"].map(normalize_text)
    valid_ids = data["listing_id"].ne("")
    invalid_id_count = int((~valid_ids).sum())
    identified = data.loc[valid_ids].copy()
    duplicate_count = int(len(identified) - identified["listing_id"].nunique())
    identified["_fetched_sort"] = _timestamp_for_sort(identified["fetched_at"])
    identified = identified.sort_values("_fetched_sort", kind="mergesort", na_position="first")
    deduped = identified.drop_duplicates("listing_id", keep="last").drop(columns="_fetched_sort")

    location = deduped["location"].map(normalize_text)
    location = location.where(location.ne(""), deduped["location_normalized"].map(normalize_text))
    deduped["location"] = location
    deduped["location_normalized"] = location.map(normalize_location)
    dki = deduped[deduped["location_normalized"].isin(DKI_DISTRICTS)].copy()
    outside_dki_count = int(len(deduped) - len(dki))

    for column in ("price", "year", "mileage_km", "engine_cc"):
        dki[column] = pd.to_numeric(dki[column], errors="coerce")
    dki["mileage_km"] = dki["mileage_km"].where(
        dki["mileage_km"].notna(), dki["mileage_range"].map(parse_mileage_km)
    )
    dki = enrich_engine_cc(dki)

    seller_aliases = {"dealer": "Diler", "diler": "Diler", "individu": "Individu", "perorangan": "Individu", "private": "Individu"}
    fuel_aliases = {"petrol": "Bensin", "gasoline": "Bensin", "bensin": "Bensin", "diesel": "Diesel", "hybrid": "Hybrid", "electric": "Listrik", "listrik": "Listrik"}
    transmission_aliases = {"automatic": "Automatic", "otomatis": "Automatic", "auto": "Automatic", "manual": "Manual"}
    dki["seller_type"] = dki["seller_type"].map(lambda value: _normalize_category(value, seller_aliases))
    dki["fuel_type"] = dki["fuel_type"].map(lambda value: _normalize_category(value, fuel_aliases))
    dki["transmission"] = dki["transmission"].map(lambda value: _normalize_category(value, transmission_aliases))
    for column in ("make", "model", "variant", "body_type", "color", "url", "image_url", "price_text", "mileage_range", "engine_capacity", "posted_at", "fetched_at"):
        dki[column] = dki[column].map(normalize_text)
    dki["fetched_at"] = dki["fetched_at"].map(normalize_timestamp_utc)

    price = dki["price"]
    invalid_price = ~price.map(lambda value: pd.notna(value) and value > 0 and value < float("inf"))
    low_price = price.lt(MIN_ANALYSIS_PRICE)
    high_price = price.gt(MAX_ANALYSIS_PRICE)
    text = dki[["variant", "price_text"]].fillna("").astype(str).agg(" ".join, axis=1)
    financing_terms = text.str.contains(FINANCING_TEXT_PATTERN)
    remove_price = invalid_price | low_price | high_price | financing_terms
    outlier_low = int(low_price.sum())
    outlier_high = int(high_price.sum())
    financing_count = int((financing_terms & ~low_price & ~high_price & ~invalid_price).sum())
    financing_excluded_count = int((low_price | (financing_terms & ~high_price)).sum())
    outlier_price_count = int(remove_price.sum())
    clean = dki.loc[~remove_price].copy()
    clean = clean.reindex(columns=DEFAULT_COLUMNS + [c for c in clean.columns if c not in DEFAULT_COLUMNS])

    years = pd.to_numeric(clean["year"], errors="coerce").dropna()
    latest_fetched = _latest_local_timestamp(clean["fetched_at"])
    missing_masks = {
        column: (clean[column].isna() | clean[column].astype("string").str.strip().eq(""))
        for column in clean.columns
    }
    total_cells = int(clean.shape[0] * clean.shape[1])
    missing_cells = sum(int(mask.sum()) for mask in missing_masks.values())
    missing_by_column = {
        column: round(float(mask.mean() * 100), 2)
        for column, mask in missing_masks.items() if len(clean)
    }
    audit = {
        "raw_rows": raw_count,
        "invalid_listing_id_rows": invalid_id_count,
        "duplicate_rows_removed": duplicate_count,
        "after_dedup_rows": int(len(deduped)),
        "outside_dki_rows_removed": outside_dki_count,
        "after_dki_rows": int(len(dki)),
        "low_price_rows_removed": outlier_low,
        "high_price_rows_removed": outlier_high,
        "financing_text_rows_removed": financing_count,
        "financing_rows_removed": financing_excluded_count,
        "outlier_price_rows_removed": outlier_price_count,
        "clean_rows": int(len(clean)),
        "engine_cc_from_variant_rows": int(clean.get("engine_cc_inferred", pd.Series(False, index=clean.index)).sum()),
        "engine_cc_available_rows": int(pd.to_numeric(clean["engine_cc"], errors="coerce").notna().sum()),
        "year_min": int(years.min()) if not years.empty else None,
        "year_max": int(years.max()) if not years.empty else None,
        "latest_fetched_at": latest_fetched.isoformat() if latest_fetched is not None else None,
        "missing_value_pct": round(missing_cells / total_cells * 100, 2) if total_cells else 0.0,
        "missing_by_column_pct": missing_by_column,
        "highest_kept_price": float(clean["price"].max()) if not clean.empty else None,
        "price_min": MIN_ANALYSIS_PRICE,
        "price_max": MAX_ANALYSIS_PRICE,
        "source": "OLX Indonesia - DKI Jakarta",
    }
    clean.attrs["preprocessing_audit"] = audit
    clean.attrs["excluded_financing_count"] = financing_excluded_count
    clean.attrs["excluded_outlier_price_count"] = outlier_price_count
    return clean.reset_index(drop=True), audit


def is_jabodetabek(value) -> bool:
    return normalize_location(value) in JABODETABEK_AREAS


def is_dki_jakarta(value) -> bool:
    return normalize_location(value) in DKI_DISTRICTS


def split_financing_listings(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate likely DP/credit ads and impossible prices from analytical views."""
    if df.empty:
        return df.copy(), df.copy()
    rows = df.copy()
    price = pd.to_numeric(rows.get("price", pd.Series(index=rows.index, dtype=float)), errors="coerce")
    low_price = price.lt(FINANCING_PRICE_FLOOR)
    high_price = price.gt(MAX_ANALYSIS_PRICE)
    text = pd.Series("", index=rows.index, dtype=str)
    for column in ("variant", "price_text", "title", "judul", "description", "deskripsi"):
        if column in rows:
            text = text.str.cat(rows[column].fillna("").astype(str), sep=" ")
    financing_terms = text.str.contains(FINANCING_TEXT_PATTERN)
    rows["financing_flag_reason"] = ""
    rows.loc[low_price, "financing_flag_reason"] = "Harga di bawah Rp30 juta, indikasi DP"
    rows.loc[high_price, "financing_flag_reason"] = HIGH_PRICE_OUTLIER_REASON
    rows.loc[financing_terms & low_price, "financing_flag_reason"] = "Harga rendah dan teks pembiayaan"
    rows.loc[financing_terms & ~low_price & ~high_price, "financing_flag_reason"] = "Teks pembiayaan"
    flagged = rows[rows["financing_flag_reason"].ne("")].copy()
    eligible = rows[rows["financing_flag_reason"].eq("")].drop(columns="financing_flag_reason")
    eligible.attrs["excluded_financing_count"] = int(
        flagged["financing_flag_reason"].ne(HIGH_PRICE_OUTLIER_REASON).sum()
    )
    eligible.attrs["excluded_outlier_price_count"] = len(flagged)
    return eligible, flagged


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
