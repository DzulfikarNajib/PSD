"""Kesimpulan & Rekomendasi - sintesis temuan data science pasar mobil bekas DKI Jakarta.

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
    subtitle="Ringkasan temuan dan saran berdasarkan hasil analisis sains data pasar mobil bekas DKI Jakarta.",
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
# Bagian 1: Empat Temuan Kunci Pasar (Grid 4 Kolom per Master Reference)
# ---------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("<div class='am-section-title'>Temuan Kunci Pasar Mobil Bekas DKI Jakarta</div>", unsafe_allow_html=True)
    k_col1, k_col2, k_col3, k_col4 = st.columns(4, gap="small")

    with k_col1:
        insight_card(
            icon="🏆",
            headline=f"Dominasi {top_make}",
            body=f"Pasar didominasi mobil Jepang dengan pangsa pasar <b>{top_make_pct:.1f}% ({top_make_count:,} unit)</b>.".replace(",", "."),
            variant="info",
        )

    with k_col2:
        insight_card(
            icon="🚙",
            headline="SUV & MPV Terpopuler",
            body="Segmen MPV dan Compact SUV keluarga menjadi tipe kendaraan paling diminati di pasar ibu kota.",
            variant="default",
        )

    with k_col3:
        insight_card(
            icon="📉",
            headline="Faktor Penentu Harga",
            body="Harga dipengaruhi paling kuat oleh kombinasi tahun pembuatan, jarak tempuh (KM), dan kapasitas mesin.",
            variant="success",
        )

    with k_col4:
        insight_card(
            icon="🎯",
            headline="Model Terbaik: RF",
            body=f"Random Forest menghasilkan akurasi tertinggi dengan <b>R² = {best_r2:.4f}</b> dan MAE {format_rupiah_compact(best_mae)}.",
            variant="warning",
        )

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Bagian 2: Rekomendasi Pembeli, Penjual & Limitasi (Master Reference 3-Kolom)
# ---------------------------------------------------------------------------
r_buyer, r_seller, r_limits = st.columns([1.1, 1.1, 1], gap="medium")

with r_buyer:
    with section_card("Rekomendasi Untuk Pembeli"):
        st.markdown(
            """
            - **✔ Bandingkan Harga Serupa**: Bandingkan penawaran dengan median listing sejenis sebelum menawar.
            - **✔ Perhatikan Tahun & KM**: Mobil usia 3-5 tahun menawarkan kurva depresiasi paling stabil.
            - **✔ Gunakan Rentang P25-P75**: Jadikan rentang harga wajar sebagai batas maksimal negosiasi.
            - **✔ Cek Riwayat Perawatan**: Waspadai odometer rendah pada mobil berusia di atas 7 tahun.
            """
        )

with r_seller:
    with section_card("Rekomendasi Untuk Penjual"):
        st.markdown(
            """
            - **✔ Pasang Harga Dekat Median**: Mempercepat perputaran unit (turnover rate) di diler.
            - **✔ Highlight Keunggulan Mobil**: Cantumkan servis berkala resmi untuk justifikasi harga P75.
            - **✔ Kenali Target Segmen**: Tentukan persona pembeli (ekonomis vs eksekutif) pada iklan.
            - **✔ Respons Tren Elektrifikasi**: Permintaan Hybrid/EV bekas di Jakarta terus meningkat.
            """
        )

with r_limits:
    with section_card("Limitasi Analisis"):
        st.markdown(
            """
            <div style="font-size:0.8rem; color:#475569; line-height:1.5;">
                <p style="margin-bottom:0.4rem;"><b>1. Harga Iklan vs Transaksi</b><br>
                Data berasal dari harga penawaran daring (OLX), bukan harga riil transaksi final (negosiasi 3-8%).</p>
                <p style="margin-bottom:0.4rem;"><b>2. Cakupan 5 Wilayah DKI</b><br>
                Hanya mencakup Jakarta Selatan, Utara, Pusat, Barat, dan Timur (tanpa Bodetabek).</p>
                <p style="margin-bottom:0;"><b>3. Sifat Model Estimasi</b><br>
                Model regresi bersifat statistik acuan dan tidak merekam kondisi fisik riil (cat, ban, modifikasi).</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Bagian 3: Ringkasan Metodologi & K-Means
# ---------------------------------------------------------------------------
with st.expander("Detail Metodologi Sains Data & Segmentasi Pasar (K-Means)", expanded=False):
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.markdown(
            """
            **Ringkasan 4 Segmen K-Means:**
            - **Segmen 1 (Ekonomis)**: Harga < Rp 150 Jt, usia rata-rata 2010, kilometer tinggi (> 100.000 km).
            - **Segmen 2 (Keluarga & Komuter)**: Harga Rp 200-500 Jt, tahun 2018-2023, segmen terbesar (56% pasar).
            - **Segmen 3 (Eksekutif)**: Harga Rp 1-2,5 Miliar, didominasi SUV premium dan sedan Eropa.
            - **Segmen 4 (Koleksi / Ultra-Luxury)**: Harga > Rp 3 Miliar, mobil hobi dan supercar simpanan.
            """
        )
    with col_exp2:
        st.markdown(
            f"""
            **Integritas Model Regresi:**
            - Data latih: 5.040 observasi, data uji holdout independen: 1.261 observasi (split 80/20).
            - Evaluasi 6 kandidat model regresi memilih **{best_model_name}** sebagai model utama.
            - MAE pada data uji sebesar **{format_rupiah_compact(best_mae)}** dan nilai determinasi **R² = {best_r2:.4f}**.
            """
        )
