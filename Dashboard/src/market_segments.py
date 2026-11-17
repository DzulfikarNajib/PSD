"""Unsupervised market segments for browsing saved car listings."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler

from src.preprocessing import MAX_ANALYSIS_PRICE, MIN_ANALYSIS_PRICE, split_financing_listings


def cluster_market_segments(
    listings: pd.DataFrame,
    n_clusters: int = 4,
    minimum_listings: int = 12,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Group similar listings by asking price and available vehicle specifications.

    Segment labels describe each group's median profile relative to the selected
    source. They are descriptive groups, not quality or affordability judgments.
    """
    segmented = listings.copy()
    segmented["market_segment"] = ""
    empty_summary = pd.DataFrame(
        columns=["market_segment", "profile", "listings", "median_price", "median_year", "median_mileage_km", "median_engine_cc"]
    )
    if listings.empty or "price" not in listings or n_clusters < 2:
        return segmented, empty_summary

    eligible, _ = split_financing_listings(listings)
    price = pd.to_numeric(eligible["price"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    rows = eligible.loc[price.between(MIN_ANALYSIS_PRICE, MAX_ANALYSIS_PRICE)].copy()
    if len(rows) < minimum_listings:
        return segmented, empty_summary

    price = pd.to_numeric(rows["price"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    features = pd.DataFrame(index=rows.index)
    features["log_price"] = np.log1p(price)

    for column, feature_name, transform in (
        ("year", "vehicle_year", lambda values: values),
        ("mileage_km", "log_mileage", lambda values: np.log1p(values.clip(lower=0))),
        ("engine_cc", "log_engine_cc", lambda values: np.log1p(values.clip(lower=0))),
    ):
        if column not in rows:
            continue
        values = pd.to_numeric(rows[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        if values.notna().sum() >= max(6, int(len(rows) * 0.25)) and values.nunique(dropna=True) > 1:
            features[feature_name] = transform(values)

    imputed = SimpleImputer(strategy="median").fit_transform(features)
    scaled = RobustScaler().fit_transform(imputed)
    distinct_profiles = np.unique(scaled, axis=0).shape[0]
    cluster_count = min(n_clusters, len(rows) // 6, distinct_profiles)
    if cluster_count < 2:
        return segmented, empty_summary

    cluster_ids = KMeans(n_clusters=cluster_count, random_state=42, n_init=10).fit_predict(scaled)
    rows["_cluster_id"] = cluster_ids

    def median_for(frame: pd.DataFrame, column: str) -> float:
        if column not in frame:
            return np.nan
        return float(pd.to_numeric(frame[column], errors="coerce").median())

    profile_columns = ("price", "year", "mileage_km", "engine_cc")
    relative_bands = {}
    for column in profile_columns:
        if column in rows:
            values = pd.to_numeric(rows[column], errors="coerce").dropna()
            relative_bands[column] = values.quantile([0.2, 0.8]).tolist() if not values.empty else []

    def describe_band(value: float, column: str, labels: tuple[str, str, str]) -> str | None:
        bounds = relative_bands.get(column, [])
        if pd.isna(value) or len(bounds) != 2:
            return None
        if value < bounds[0]:
            return labels[0]
        if value > bounds[1]:
            return labels[2]
        return labels[1]

    clusters = []
    for cluster_id, group in rows.groupby("_cluster_id"):
        clusters.append({
            "_cluster_id": int(cluster_id),
            "listings": len(group),
            "median_price": median_for(group, "price"),
            "median_year": median_for(group, "year"),
            "median_mileage_km": median_for(group, "mileage_km"),
            "median_engine_cc": median_for(group, "engine_cc"),
        })
    clusters.sort(key=lambda item: item["median_price"])

    labels_by_cluster = {}
    summary_rows = []
    for rank, cluster in enumerate(clusters, start=1):
        label_parts = [describe_band(cluster["median_price"], "price", ("harga relatif rendah", "harga menengah", "harga relatif tinggi"))]
        label_parts.extend([
            describe_band(cluster["median_year"], "year", ("mobil lebih lama", "tahun menengah", "mobil lebih baru")),
            describe_band(cluster["median_mileage_km"], "mileage_km", ("km rendah", "km menengah", "km tinggi")),
            describe_band(cluster["median_engine_cc"], "engine_cc", ("CC kecil", "CC menengah", "CC besar")),
        ])
        label_parts = [part for part in label_parts if part]

        label = f"Segmen {rank}"
        labels_by_cluster[cluster["_cluster_id"]] = label
        summary_rows.append({
            "market_segment": label,
            "profile": " · ".join(label_parts),
            "listings": cluster["listings"],
            "median_price": cluster["median_price"],
            "median_year": cluster["median_year"],
            "median_mileage_km": cluster["median_mileage_km"],
            "median_engine_cc": cluster["median_engine_cc"],
        })

    segmented.loc[rows.index, "market_segment"] = rows["_cluster_id"].map(labels_by_cluster).astype(str)
    return segmented, pd.DataFrame(summary_rows)
