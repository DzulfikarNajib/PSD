"""Pure helpers for searching and comparing the latest listing snapshot."""

from __future__ import annotations

import pandas as pd


def filter_listings(
    df: pd.DataFrame,
    budget: tuple[float, float] | None = None,
    make: str | None = None,
    model: str | None = None,
    years: tuple[float, float] | None = None,
    max_mileage: float | None = None,
    engine_range: tuple[float, float] | None = None,
    categories: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Return rows satisfying provided filters; missing optional values stay eligible."""
    result = df.copy()
    numeric_filters = [("price", budget), ("year", years), ("engine_cc", engine_range)]
    for column, bounds in numeric_filters:
        if bounds is not None and column in result:
            numeric = pd.to_numeric(result[column], errors="coerce")
            result = result[numeric.between(bounds[0], bounds[1]) | numeric.isna()]
    if max_mileage is not None and "mileage_km" in result:
        mileage = pd.to_numeric(result["mileage_km"], errors="coerce")
        result = result[mileage.le(max_mileage) | mileage.isna()]
    for column, value in [("make", make), ("model", model)]:
        if value and column in result:
            result = result[result[column].astype(str).eq(value)]
    for column, value in (categories or {}).items():
        if value and value != "Semua" and column in result:
            result = result[result[column].astype(str).eq(value)]
    return result.copy()


def compare_listings(df: pd.DataFrame, listing_ids: list[str]) -> pd.DataFrame:
    """Build an attribute-by-listing table for two or three selected IDs."""
    if not 2 <= len(listing_ids) <= 3:
        return pd.DataFrame()
    fields = ["make", "model", "variant", "price", "year", "mileage_km", "transmission", "fuel_type", "engine_cc", "body_type", "location"]
    available = [field for field in fields if field in df]
    if "listing_id" not in df:
        return pd.DataFrame()
    selected = df[df["listing_id"].astype(str).isin([str(value) for value in listing_ids])]
    if selected["listing_id"].astype(str).nunique() < 2:
        return pd.DataFrame()
    return selected.set_index("listing_id")[available].T


def budget_summary(df: pd.DataFrame, thresholds: list[int]) -> pd.DataFrame:
    """Count live listings at or below each Rp threshold."""
    if "price" not in df:
        return pd.DataFrame(columns=["budget_rp", "listing_count"])
    prices = pd.to_numeric(df["price"], errors="coerce")
    return pd.DataFrame([{"budget_rp": int(limit), "listing_count": int(prices.le(limit).sum())} for limit in sorted(set(thresholds))])
