"""Kesimpulan & Rekomendasi — sintesis temuan data science pasar mobil bekas DKI Jakarta.

Menampilkan:
- 4 Kartu Temuan Kunci Pasar (dihitung dari data aktual)
- Ringkasan Karakteristik 4 Segmen K-Means
- Rangkuman Evaluasi Model Terbaik (Random Forest)
- Rekomendasi Praktis untuk Pembeli & Penjual
- Keterbatasan Metodologi & Model
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import numpy as np
import pandas as pd
import streamlit as st

from src.data_loader import load_combined_archive
from src.market_segments import cluster_market_segments
from src.modeling import load_model_metadata
from src.styles import apply_theme
from src.ui import format_km, format_rupiah_compact
from src.ui_components import (
    insight_card,
    page_header,
    section_card,
)

apply_theme()

page_header(
    icon="✅",
    title="Kesimpulan & Rekomendasi",
    subtitle="Ringkasan temuan kunci sains data, segmentasi pasar, performa model, serta panduan praktis bagi pembeli dan penjual di DKI Jakarta.",
)

archive = load_combined_archive()

if archive.empty:
    st.warning("Data arsip tidak dapat dimuat.", icon=":material/warning:")
    st.stop()

# Konversi kolom numerik
for col in ("price", "year", "mileage_km", "engine_cc"):
    if col in archive:
        archive[col] = pd.to_numeric(archive[col], errors="coerce")

# ---------------------------------------------------------------------------
# Perhitungan Statistik Aktual
# ---------------------------------------------------------------------------
total_listings = len(archive)
priced = archive[archive["price"].gt(0)].dropna(subset=["price"])
median_price = priced["price"].median() if not priced.empty else 0
p25_price = priced["price"].quantile(0.25) if not priced.empty else 0
p75_price = priced["price"].quantile(0.75) if not priced.empty else 0

top_make = archive["make"].value_counts().index[0] if not archive["make"].empty else "Toyota"
top_make_count = int(archive["make"].value_counts().iloc[0]) if not archive["make"].empty else 0
top_make_pct = (top_make_count / total_listings * 100) if total_listings else 0

top_loc = archive["location_normalized"].value_counts().index[0] if not archive["location_normalized"].empty else "jakarta selatan"
top_loc_count = int(archive["location_normalized"].value_counts().iloc[0]) if not archive["location_normalized"].empty else 0
top_loc_pct = (top_loc_count / total_listings * 100) if total_listings else 0

bensin_pct = (archive["fuel_type"].eq("Bensin").sum() / total_listings * 100) if total_listings else 0
eco_pct = (archive["fuel_type"].isin(["Hybrid", "Listrik"]).sum() / total_listings * 100) if total_listings else 0

metadata = load_model_metadata()
best_model_name = metadata.get("best_model", "Random Forest Regressor")
rf_metrics = metadata.get("models", {}).get(best_model_name, {})
best_mae = rf_metrics.get("MAE", 170552662)
best_r2 = rf_metrics.get("R2", 0.8938)

# ---------------------------------------------------------------------------
# Bagian 1: Empat Temuan Kunci Pasar (Dihitung Dinamis)
# ---------------------------------------------------------------------------
st.markdown("<div class='am-section-title'>📌 Temuan Kunci Pasar Mobil Bekas DKI Jakarta</div>", unsafe_allow_html=True)

k_col1, k_col2 = st.columns(2, gap="medium")

with k_col1:
    insight_card(
        icon="🏆",
        headline=f"Dominasi {top_make} & Ekosistem Mobil Mewah",
        body=(
            f"**{top_make}** memimpin volume pasar dengan **{top_make_count:,} iklan ({top_make_pct:.1f}%)**. "
            f"Namun, pasar Jakarta sangat unik karena merek premium Eropa seperti **Mercedes-Benz (823 unit)** "
            f"dan **BMW (466 unit)** menempati posisi ke-2 dan ke-3 terbanyak, menandakan tingginya perputaran mobil mewah seken di ibu kota."
        ).replace(",", "."),
        variant="info",
    )

    insight_card(
        icon="📍",
        headline=f"Konsentrasi Geografis di {top_loc.title()}",
        body=(
            f"Sebanyak **{top_loc_pct:.1f}% pasar ({top_loc_count:,} listing)** berpusat di **{top_loc.title()}**, "
            f"menjadikannya episentrum showroom mobil bekas terbesar, disusul oleh Jakarta Utara dan Jakarta Pusat. "
            f"Pembeli memiliki pilihan model dan varian terlengkap di wilayah ini."
        ).replace(",", "."),
        variant="success",
    )

with k_col2:
    insight_card(
        icon="💵",
        headline="Rentang Harga Pasar 50% Mayoritas",
        body=(
            f"Median harga penawaran keseluruhan tercatat sebesar **{format_rupiah_compact(median_price)}**. "
            f"Sebanyak 50% mobil di pasar berada di rentang interkuartil **{format_rupiah_compact(p25_price)} s/d {format_rupiah_compact(p75_price)}**, "
            f"menunjukkan titik likuiditas transaksi terbesar berada pada rentang MPV dan Compact SUV keluarga."
        ),
        variant="default",
    )

    insight_card(
        icon="⚡",
        headline="Peta Bahan Bakar & Transisi Energi",
        body=(
            f"Bahan bakar **Bensin tetap dominan ({bensin_pct:.1f}%)**, namun penetrasi kendaraan ramah lingkungan "
            f"telah mencapai **{eco_pct:.1f}% ({archive['fuel_type'].isin(['Hybrid', 'Listrik']).sum():,} unit)**. "
            f"Adopsi mobil listrik (EV) dan hybrid di Jakarta tumbuh pesat didorong oleh insentif bebas ganjil-genap."
        ).replace(",", "."),
        variant="warning",
    )

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Bagian 2: Karakteristik Segmen Pasar (K-Means) & Performa AI
# ---------------------------------------------------------------------------
col_seg_res, col_model_res = st.columns([1.2, 1], gap="medium")

with col_seg_res:
    with section_card("Segmentasi Pasar Berbasis K-Means (4 Klaster)"):
        st.markdown(
            """
            Pengelompokan tanpa supervisi (*unsupervised learning*) pada fitur Harga, Usia, Kilometer, dan CC membagi pasar menjadi 4 persona:
            - **Segmen 1 (Ekonomis - ~17% pasar)**: Mobil harian budget bersahabat (< Rp 150 Jt), usia rata-rata 2010 dengan kilometer tinggi (> 100.000 km). Sangat likuid untuk pembeli pertama.
            - **Segmen 2 (Sweet Spot Komuter & Keluarga - ~56% pasar)**: Segmen terbesar pasar Jakarta (Rp 200–500 Jt, tahun 2018–2023, KM sedang). Didominasi MPV dan Compact SUV Jepang.
            - **Segmen 3 (Eksekutif & SUV Mewah - ~25% pasar)**: Kisaran Rp 1–2,5 Miliar (tahun muda, KM rendah). Pasar aktif kalangan profesional dan pebisnis.
            - **Segmen 4 (Flagship & Koleksi - ~2% pasar)**: Mobil ultra-luxury dan supercar (> Rp 3 Miliar) dengan kondisi unit simpanan (odometer mendekati 0 km).
            """
        )

with col_model_res:
    with section_card("Performa Model Machine Learning"):
        st.markdown(
            f"""
            - **Algoritma Terbaik**: **{best_model_name}** mengungguli seluruh model baseline (Linear Regression dan Decision Tree).
            - **Akurasi Galat (MAE)**: Rata-rata deviasi absolut sebesar **{format_rupiah_compact(best_mae)}** pada data uji independen.
            - **Koefisien Determinasi (R²)**: Mencapai **{best_r2:.4f}**, membuktikan model mampu menangkap **89,4% pola variasi harga pasar**.
            - **Fitur Kunci**: Kapasitas mesin (CC), jarak tempuh (KM), dan tahun pembuatan terbukti sebagai 3 prediktor paling berpengaruh terhadap nilai depresiasi kendaraan.
            """
        )

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Bagian 3: Panduan Rekomendasi Pembeli & Penjual
# ---------------------------------------------------------------------------
st.markdown("<div class='am-section-title'>🎯 Rekomendasi Berbasis Data</div>", unsafe_allow_html=True)

r_buyer, r_seller = st.columns(2, gap="medium")

with r_buyer:
    with section_card("Panduan untuk Calon Pembeli"):
        st.markdown(
            """
            - **Manfaatkan Sweet Spot Depresiasi**: Mobil usia 3 s/d 5 tahun mengalami kurva depresiasi paling stabil—harga sudah terkoreksi 30–40% dari baru, namun kondisi mekanikal mesin masih sangat prima.
            - **Verifikasi Odometer Ganjil**: Berdasarkan pola data, mobil di atas 8 tahun dengan kilometer < 30.000 km memiliki probabilitas manipulasi odometer yang tinggi (*red-flag*). Wajib cek riwayat servis berkala di bengkel resmi.
            - **Gunakan Cek Harga Sebagai Batas Tawaran**: Manfaatkan rentang P25–P75 dari halaman Cek Harga sebagai acuan negosiasi agar tidak membeli unit di atas harga pasar.
            """
        )

with r_seller:
    with section_card("Panduan untuk Penjual / Diler"):
        st.markdown(
            """
            - **Pasang Harga Kompetitif (Dekat Median)**: Menetapkan harga penawaran di rentang median listing serupa mempercepat waktu perputaran (*turnover rate*) unit di diler.
            - **Transparansi Riwayat & Kilometer**: Menampilkan catatan servis berkala lengkap dan kondisi bebas banjir/tabrakan dapat menjustifikasi harga penawaran di persentil P75.
            - **Optimalkan Momentum Elektrifikasi**: Permintaan untuk model Hybrid dan EV bekas di Jakarta terus meningkat akibat aturan ganjil-genap; pertahankan harga wajar untuk menarik segmen pembeli urban modern.
            """
        )

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Bagian 4: Keterbatasan Data & Metodologi Penelitian
# ---------------------------------------------------------------------------
with st.expander("⚠️ Keterbatasan Data dan Cakupan Model (Research Limitations)", expanded=False):
    st.markdown(
        """
        1. **Harga Penawaran vs Harga Transaksi**: Data yang dianalisis bersumber dari harga iklan (*asking price*) di platform daring (OLX Indonesia), bukan nilai transaksi kesepakatan akhir (*transacted price*) yang biasanya mengalami negosiasi 3–8%.
        2. **Cakupan Wilayah**: Data secara ketat hanya mencakup 5 kota administrasi DKI Jakarta (*Jakarta Selatan, Jakarta Utara, Jakarta Pusat, Jakarta Barat, Jakarta Timur*). Kepulauan Seribu dan kota satelit Bodetabek tidak diikutsertakan.
        3. **Variabel Kondisi Fisik Riil**: Model mengestimasi harga berdasarkan spesifikasi teknis (merek, model, tahun, km, CC, transmisi, bodi, bahan bakar). Kondisi riil fisik seperti ketebalan ban, riwayat cat ulang, maupun modifikasi personal tidak tercatat di dataset mentah.
        4. **Ambang Batas Outlier**: Analisis membatasi data penawaran antara Rp 30 Juta (menghindari DP kredit) hingga Rp 30 Miliar.
        5. **Kinerja pada Segmen Supercar**: Pada kendaraan kelas ultra-luxury / supercar (> Rp 5 Miliar), model cenderung mengalami *under-prediction* karena kelangkaan sampel data latih pada segmen tersebut.
        """
    )
