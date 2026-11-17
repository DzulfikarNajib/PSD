import pandas as pd

from src.market_segments import cluster_market_segments


def _segmented_listings():
    profiles = [
        (120_000_000, 2014, 180_000, 1_000),
        (240_000_000, 2018, 100_000, 1_300),
        (480_000_000, 2020, 60_000, 1_800),
        (960_000_000, 2023, 20_000, 2_500),
    ]
    rows = []
    for group, profile in enumerate(profiles):
        for offset in range(8):
            price, year, mileage, engine_cc = profile
            rows.append({
                "listing_id": f"g{group}-{offset}",
                "price": price + offset * 1_000_000,
                "year": year,
                "mileage_km": mileage + offset * 500,
                "engine_cc": engine_cc,
            })
    return pd.DataFrame(rows)


def test_unsupervised_segments_create_profiles_and_keep_all_listings():
    segmented, summary = cluster_market_segments(_segmented_listings())

    assert segmented["market_segment"].ne("").all()
    assert summary["market_segment"].nunique() >= 2
    assert summary["listings"].sum() == len(segmented)
    assert summary["profile"].str.contains("harga ").all()
    assert summary["median_year"].notna().all()
    assert summary["median_mileage_km"].notna().all()


def test_unsupervised_segments_wait_for_minimum_listing_count():
    listings = _segmented_listings().head(8)
    segmented, summary = cluster_market_segments(listings)

    assert segmented["market_segment"].eq("").all()
    assert summary.empty
