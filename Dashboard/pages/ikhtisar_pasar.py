"""Beranda - halaman pembuka dashboard analisis pasar mobil bekas DKI Jakarta.

Menampilkan Hero Banner, 4 KPI utama (Jumlah Iklan, Jumlah Merek, Jumlah Model,
dan Jenis Bahan Bakar), serta pengantar interaktif untuk menuju halaman
Eksplorasi Data atau langsung ke Cek Mobil dan Harga.
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
from src.styles import apply_theme
from src.ui import format_rupiah_compact
from src.ui_components import (
    get_lucide_icon,
    hero_banner,
    insight_card,
    kpi_card,
)

apply_theme()

hero_banner(
    title="AutoMatch",
    subtitle="Analisis Pasar Mobil Bekas di DKI Jakarta",
    description=(
        "Platform analitik berbasis sains data untuk memetakan sebaran pasar, "
        "memahami pola harga kendaraan, dan mengevaluasi kewajaran harga iklan mobil bekas secara objektif."
    ),
)

archive = load_combined_archive()

if archive.empty:
    st.warning("Belum ada data pasar mobil bekas yang tersedia.", icon=":material/warning:")
    st.stop()

# Konversi kolom numerik
for col in ("price", "year", "mileage_km", "engine_cc"):
    if col in archive:
        archive[col] = pd.to_numeric(archive[col], errors="coerce")

# Normalisasi lokasi 5 wilayah DKI Jakarta
archive["location_display"] = archive["location_normalized"].fillna("").astype(str).str.title()
dki_5 = ["Jakarta Selatan", "Jakarta Utara", "Jakarta Pusat", "Jakarta Barat", "Jakarta Timur"]
archive = archive[archive["location_display"].isin(dki_5)].copy()

priced = archive[archive["price"].gt(0)].dropna(subset=["price"])

# Hitung 4 KPI Utama sesuai spesifikasi Beranda
total_listings = int(archive["listing_id"].nunique() if "listing_id" in archive else len(archive))
total_makes = int(archive["make"].dropna().replace("", pd.NA).dropna().nunique()) if "make" in archive else 0
total_models = int(archive["model"].dropna().replace("", pd.NA).dropna().nunique()) if "model" in archive else 0

fuel_series = archive["fuel_type"].dropna().replace("", pd.NA).dropna()
fuel_counts = fuel_series.value_counts()
total_fuels = int(len(fuel_counts))
fuel_names_list = fuel_counts.index.tolist()
fuel_summary_text = " · ".join(fuel_names_list[:4]) if fuel_names_list else "-"

median_price = float(priced["price"].median()) if not priced.empty else 0.0
p25_price = float(priced["price"].quantile(0.25)) if not priced.empty else 0.0
p75_price = float(priced["price"].quantile(0.75)) if not priced.empty else 0.0
top_region = archive["location_display"].value_counts().index[0] if not archive["location_display"].empty else "Jakarta Selatan"
top_make = archive["make"].value_counts().index[0] if not archive["make"].empty else "Toyota"

# ---------------------------------------------------------------------------
# Baris 1: 4 Kartu KPI Mandiri (Iklan Tersedia, Merek, Model, Jenis Bahan Bakar)
# ---------------------------------------------------------------------------
kpi_cols = st.columns(4, gap="medium")

with kpi_cols[0]:
    kpi_card(
        label="Iklan Tersedia",
        value=f"{total_listings:,}".replace(",", "."),
        icon="car",
        subtext="Unit terverifikasi di 5 kota DKI Jakarta",
        help_text="Jumlah iklan mobil bekas unik yang dianalisis di wilayah DKI Jakarta.",
    )

with kpi_cols[1]:
    kpi_card(
        label="Total Merek",
        value=f"{total_makes:,}".replace(",", "."),
        icon="tag",
        subtext=f"Didominasi oleh {top_make} & pabrikan utama",
        help_text="Banyaknya merek kendaraan roda empat yang tersedia di pasar.",
    )

with kpi_cols[2]:
    kpi_card(
        label="Variasi Model",
        value=f"{total_models:,}".replace(",", "."),
        icon="layers",
        subtext="Dari City Car harian hingga SUV eksekutif",
        help_text="Jumlah model unik kendaraan lintas tipe bodi dan segmen.",
    )

with kpi_cols[3]:
    kpi_card(
        label="Jenis Bahan Bakar",
        value=f"{total_fuels} Jenis",
        icon="zap",
        subtext=fuel_summary_text,
        help_text="Kategori sistem bahan bakar dan penggerak kendaraan di pasar.",
    )

st.markdown("<div style='height: 26px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Baris 2: Pengantar & Call to Action ("Penasaran ada apa saja?")
# ---------------------------------------------------------------------------
with st.container(border=True):
    search_svg = get_lucide_icon("trending-up", size=22, color="#019F90")
    st.markdown(
        f"""
        <div style="display:flex; align-items:flex-start; gap:0.9rem; margin-bottom:0.85rem;">
            <div style="display:inline-flex; align-items:center; justify-content:center; width:2.5rem; height:2.5rem; border-radius:10px; background:#E6F7F5; flex-shrink:0; margin-top:0.1rem;">
                {search_svg}
            </div>
            <div>
                <div style="font-family:'Plus Jakarta Sans',Inter,sans-serif; font-size:1.3rem; font-weight:800; color:#0D1E38; letter-spacing:-0.02em; line-height:1.25;">
                    Penasaran Ada Mobil Apa Saja di Pasar DKI Jakarta?
                </div>
                <div style="font-size:0.9rem; color:#475569; margin-top:0.3rem; line-height:1.6;">
                    Dari <b>{total_listings:,} iklan</b> yang tersebar di 5 kota administrasi DKI Jakarta, separuh pasar berkumpul di kisaran harga
                    <b>{format_rupiah_compact(p25_price)} hingga {format_rupiah_compact(p75_price)}</b> (median <b>{format_rupiah_compact(median_price)}</b>).
                    Telusuri lebih dalam wilayah mana yang menyimpan stok terbanyak, merek apa yang paling mendominasi, serta bagaimana usia dan jarak tempuh membentuk harga jualnya.
                </div>
            </div>
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )

    hl_cols = st.columns(3, gap="medium")
    with hl_cols[0]:
        insight_card(
            icon="",
            headline="Peta Interaktif 5 Wilayah DKI",
            body=(
                f"Klik wilayah di peta (seperti <b>{top_region}</b>) untuk melakukan zoom otomatis "
                "dan melihat rincian jumlah iklan, model terlaris, serta bahan bakar dominan di tiap kota."
            ),
            variant="info",
        )
    with hl_cols[1]:
        insight_card(
            icon="",
            headline="Eksplorasi Merek, Harga & Depresiasi",
            body=(
                f"Amati distribusi harga pasar, popularitas <b>{total_makes} merek</b>, proporsi bahan bakar, "
                "serta simulasi pengaruh tahun pembuatan dan jarak tempuh (KM) terhadap harga."
            ),
            variant="success",
        )
    with hl_cols[2]:
        insight_card(
            icon="",
            headline="Cek Mobil & Harga Langsung ke OLX",
            body=(
                "Saring mobil sesuai budget Anda, lihat <b>foto asli iklan, spesifikasi detail, tautan langsung ke OLX</b>, "
                "sekaligus uji kewajaran harganya menggunakan model Machine Learning."
            ),
            variant="warning",
        )

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
    cta_c1, cta_c2, _ = st.columns([1.2, 1.2, 1.6], gap="small")
    with cta_c1:
        if st.button("Lanjut ke Eksplorasi Data Pasar", type="primary", use_container_width=True, key="btn_home_to_eda"):
            st.switch_page("pages/eksplorasi_data.py")
    with cta_c2:
        if st.button("Langsung ke Cek Mobil dan Harga", use_container_width=True, key="btn_home_to_cek"):
            st.switch_page("pages/cek_harga_iklan.py")
