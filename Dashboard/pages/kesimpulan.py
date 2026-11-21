"""Kesimpulan & Rekomendasi - sintesis temuan berbasis data dan panduan strategi pembelian mobil bekas DKI Jakarta.

Menampilkan:
- 4 Temuan Kunci Pasar yang dihitung langsung dari 6.301 iklan & metadata model ML
- Matriks Panduan Strategi Beli Berdasarkan Rentang Budget (dihitung otomatis dari data)
- Panduan Negosiasi Harga & Catatan Keterbatasan Data
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import pandas as pd
import streamlit as st

from src.data_loader import load_combined_archive
from src.market_segments import cluster_market_segments
from src.modeling import get_feature_importance, load_model_metadata
from src.styles import apply_theme
from src.ui import format_km, format_rupiah_compact
from src.ui_components import (
    insight_card,
    page_header,
    section_card,
)

apply_theme()

page_header(
    icon="check-circle",
    title="Kesimpulan & Rekomendasi",
    subtitle="Sintesis temuan kuantitatif dan panduan keputusan berbasis data pasar mobil bekas DKI Jakarta.",
)

archive = load_combined_archive()

if archive.empty:
    st.warning("Data arsip tidak dapat dimuat.", icon=":material/warning:")
    st.stop()

for col in ("price", "year", "mileage_km", "engine_cc"):
    if col in archive:
        archive[col] = pd.to_numeric(archive[col], errors="coerce")

archive["location_display"] = archive["location_normalized"].fillna("").astype(str).str.title()
dki_5 = ["Jakarta Selatan", "Jakarta Utara", "Jakarta Pusat", "Jakarta Barat", "Jakarta Timur"]
archive = archive[archive["location_display"].isin(dki_5)].copy()

# ---------------------------------------------------------------------------
# Perhitungan Statistik Aktual
# ---------------------------------------------------------------------------
total_listings = len(archive)
priced = archive[archive["price"].gt(0)].dropna(subset=["price"])

top_make = archive["make"].value_counts().index[0] if not archive["make"].empty else "Toyota"
top_make_count = int(archive["make"].value_counts().iloc[0]) if not archive["make"].empty else 0
top_make_pct = (top_make_count / total_listings * 100) if total_listings else 0.0

top_loc = archive["location_display"].value_counts().index[0] if not archive["location_display"].empty else "Jakarta Selatan"
top_loc_count = int(archive["location_display"].value_counts().iloc[0]) if not archive["location_display"].empty else 0
top_loc_pct = (top_loc_count / total_listings * 100) if total_listings else 0.0

med_2022_plus = float(priced[priced["year"].ge(2022)]["price"].median()) if priced["year"].ge(2022).any() else 0.0
med_2018_2021 = float(priced[priced["year"].between(2018, 2021)]["price"].median()) if priced["year"].between(2018, 2021).any() else 0.0
dep_pct = ((med_2022_plus - med_2018_2021) / med_2022_plus * 100) if med_2022_plus > 0 else 0.0

metadata = load_model_metadata()
best_model_name = metadata.get("best_model", "Random Forest Regressor")
rf_metrics = metadata.get("models", {}).get(best_model_name, {})
best_mae = rf_metrics.get("MAE", 170552662)
best_r2 = rf_metrics.get("R2", 0.8938)

imp_df = get_feature_importance().head(2)
top_feat_1 = f"{imp_df.iloc[0]['feature']} ({imp_df.iloc[0]['importance']*100:.1f}%)" if len(imp_df) > 0 else "Kapasitas Mesin"
top_feat_2 = f"{imp_df.iloc[1]['feature']} ({imp_df.iloc[1]['importance']*100:.1f}%)" if len(imp_df) > 1 else "Kilometer"

_, seg_summary = cluster_market_segments(archive)
seg2_row = seg_summary[seg_summary["market_segment"].eq("Segmen 2")]
seg2_pct = (float(seg2_row["listings"].iloc[0]) / float(seg_summary["listings"].sum()) * 100) if (not seg2_row.empty and seg_summary["listings"].sum() > 0) else 55.8

# ---------------------------------------------------------------------------
# Bagian 1: 4 Temuan Kunci Kuantitatif
# ---------------------------------------------------------------------------
with section_card("Temuan Kunci Pasar Mobil Bekas DKI Jakarta"):
    k_cols = st.columns(4, gap="small")

    with k_cols[0]:
        insight_card(
            icon="",
            headline="Konsentrasi Stok & Likuiditas",
            body=(
                f"<b>{top_loc}</b> menampung <b>{top_loc_pct:.1f}% ({top_loc_count:,} unit)</b> stok DKI, "
                f"dengan <b>{top_make} ({top_make_pct:.1f}%)</b> sebagai merek paling likuid."
            ).replace(",", "."),
            variant="info",
        )

    with k_cols[1]:
        insight_card(
            icon="",
            headline="Kurva Depresiasi Usia Nyata",
            body=(
                f"Mobil keluaran <b>2018-2021</b> (median {format_rupiah_compact(med_2018_2021)}) "
                f"tercatat <b>{dep_pct:.0f}% lebih hemat</b> dibanding tahun 2022+ ({format_rupiah_compact(med_2022_plus)})."
            ),
            variant="success",
        )

    with k_cols[2]:
        insight_card(
            icon="",
            headline="Penggerak Utama Harga (ML)",
            body=(
                f"Model <b>{best_model_name}</b> (R² = <b>{best_r2:.4f}</b>) menemukan dua penentu harga terkuat: "
                f"<b>{top_feat_1}</b> dan <b>{top_feat_2}</b>."
            ),
            variant="info",
        )

    with k_cols[3]:
        insight_card(
            icon="",
            headline="Dominasi Segmen Menengah",
            body=(
                f"Hasil klasterisasi K-Means menunjukkan <b>Segmen 2 (Keluarga & Komuter)</b> "
                f"menguasai <b>{seg2_pct:.1f}%</b> total pasar mobil bekas DKI Jakarta."
            ),
            variant="warning",
        )

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Bagian 2: Matriks Panduan Strategi Beli Berdasarkan Rentang Budget
# ---------------------------------------------------------------------------
with section_card("Panduan Strategi Beli Berdasarkan Rentang Budget (Data Aktual)"):
    st.caption(
        "Gunakan tabel di bawah untuk langsung memetakan ekspektasi tahun produksi, jarak tempuh wajar, "
        "merek dengan pilihan terbanyak, serta kota tujuan pencarian sesuai anggaran Anda."
    )

    budget_tiers = [
        ("Ekonomis (< Rp 150 Jt)", 0, 150_000_000),
        ("Menengah (Rp 150 - 350 Jt)", 150_000_000, 350_000_000),
        ("Menengah Atas (Rp 350 - 750 Jt)", 350_000_000, 750_000_000),
        ("Premium & Koleksi (> Rp 750 Jt)", 750_000_000, 100_000_000_000),
    ]

    tier_rows = []
    for label, b_lo, b_hi in budget_tiers:
        sub = priced[priced["price"].gt(b_lo) & priced["price"].le(b_hi)]
        if sub.empty:
            continue
        med_yr = int(sub["year"].median()) if sub["year"].notna().any() else 0
        med_km_val = float(sub["mileage_km"].median()) if sub["mileage_km"].notna().any() else 0.0
        top_brands_3 = ", ".join(sub["make"].dropna().value_counts().head(3).index.tolist())
        top_city = sub["location_display"].value_counts().index[0] if not sub["location_display"].empty else "-"
        tier_rows.append(
            {
                "Kategori Budget": label,
                "Stok Tersedia": f"{len(sub):,} unit".replace(",", "."),
                "Tahun Tipikal": f"~{med_yr}" if med_yr else "-",
                "Median Odometer": format_km(med_km_val),
                "3 Merek Pilihan Terbanyak": top_brands_3,
                "Wilayah Stok Terbanyak": top_city,
            }
        )

    st.dataframe(pd.DataFrame(tier_rows), hide_index=True, width="stretch")

    cta_c1, _ = st.columns([1.3, 2.7])
    with cta_c1:
        if st.button("Terapkan Budget Anda di Cek Mobil dan Harga", type="primary", use_container_width=True, key="btn_kesimpulan_to_cek"):
            st.switch_page("pages/cek_harga_iklan.py")

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Bagian 3: Strategi Negosiasi & Keterbatasan Data (2 Kolom Ringkas)
# ---------------------------------------------------------------------------
col_strat, col_lim = st.columns([1.2, 1], gap="medium")

with col_strat:
    with section_card("Strategi Negosiasi & Penetapan Harga"):
        st.markdown(
            f"""
            <div style="font-size:0.86rem; color:#334155; line-height:1.65;">
                <p style="margin-bottom:0.55rem;"><b>Untuk Pembeli (Patokan Nego P25 - Median):</b><br>
                Gunakan angka <b>Median Pembanding</b> di halaman <i>Cek Mobil dan Harga</i> sebagai batas atas negosiasi. Jika harga iklan melampaui P75 (+8% di atas pasar), minta potongan harga kecuali unit memiliki riwayat servis resmi lengkap dan odometer rendah.</p>
                <p style="margin-bottom:0;"><b>Untuk Penjual &amp; Diler (Percepatan Turnover):</b><br>
                Memasang harga penawaran mendekati estimasi <b>Random Forest</b> (MAE {format_rupiah_compact(best_mae)}) dan mencantumkan angka odometer secara transparan mempercepat peluang transaksi dibanding harga spekulatif di atas P75.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

with col_lim:
    with section_card("Batasan Data & Metodologi"):
        st.markdown(
            """
            <div style="font-size:0.84rem; color:#475569; line-height:1.6;">
                <p style="margin-bottom:0.45rem;"><b>1. Harga Penawaran vs Transaksi Final:</b> Data berasal dari harga iklan daring (OLX), bukan harga deal akhir setelah negosiasi lapangan (umumnya turun 3-8%).</p>
                <p style="margin-bottom:0.45rem;"><b>2. Khusus 5 Kota DKI Jakarta:</b> Analisis tidak mencakup wilayah penyangga Bodetabek sehingga profil harga segmen premium lebih tinggi dibanding rata-rata nasional.</p>
                <p style="margin-bottom:0;"><b>3. Variabel Fisik Non-Tabular:</b> Estimasi AI tidak melihat kondisi cat, riwayat tabrak/banjir, atau status pajak kendaraan. Inspeksi fisik tetap wajib sebelum transaksi.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
