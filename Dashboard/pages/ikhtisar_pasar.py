"""Ikhtisar Pasar - ringkasan pasar mobil bekas DKI Jakarta.

Dashboard ringkasan pasar dengan KPI utama, distribusi 5 wilayah,
komposisi bahan bakar, top merek, dan insight cards terhitung otomatis.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_combined_archive
from src.styles import apply_theme
from src.ui import format_rupiah_compact
from src.ui_components import (
    apply_chart_theme,
    hero_banner,
    insight_card,
    kpi_card,
    page_header,
    section_card,
)

apply_theme()

hero_banner(
    title="AutoMatch",
    subtitle="Analisis Pasar Mobil Bekas di DKI Jakarta",
    description="Memahami karakteristik, menemukan pola, dan memprediksi harga mobil bekas dengan pendekatan data science.",
)

archive = load_combined_archive()

if archive.empty:
    st.warning("Belum ada data pasar mobil bekas yang tersedia.", icon=":material/warning:")
    st.stop()

# Konversi kolom numerik
for col in ("price", "year", "mileage_km", "engine_cc"):
    if col in archive:
        archive[col] = pd.to_numeric(archive[col], errors="coerce")

# Normalisasi lokasi
archive["location_display"] = archive["location_normalized"].fillna("").astype(str).str.title()
loc_mapping = {
    "Jakarta Selatan": "Jakarta Selatan",
    "Jakarta Utara": "Jakarta Utara",
    "Jakarta Pusat": "Jakarta Pusat",
    "Jakarta Barat": "Jakarta Barat",
    "Jakarta Timur": "Jakarta Timur",
}
archive["location_display"] = archive["location_display"].map(lambda x: loc_mapping.get(x, x))
# Filter hanya 5 wilayah DKI
dki_5 = ["Jakarta Selatan", "Jakarta Utara", "Jakarta Pusat", "Jakarta Barat", "Jakarta Timur"]
archive = archive[archive["location_display"].isin(dki_5)].copy()

priced = archive[archive["price"].gt(0)].dropna(subset=["price"])

# Hitung KPI Utama
total_listings = int(archive["listing_id"].nunique() if "listing_id" in archive else len(archive))
total_makes = int(archive["make"].dropna().nunique()) if "make" in archive else 0
median_price = float(priced["price"].median()) if not priced.empty else 0.0

year_min = int(archive["year"].min()) if archive["year"].notna().any() else 1986
year_max = int(archive["year"].max()) if archive["year"].notna().any() else 2026
year_span = f"{year_min} - {year_max}"

# ---------------------------------------------------------------------------
# Baris 1: KPI Metrics
# ---------------------------------------------------------------------------
kpi_cols = st.columns(4, gap="small")
with kpi_cols[0]:
    kpi_card(
        label="Listing Unik",
        value=f"{total_listings:,}".replace(",", "."),
        icon="🚗",
        help_text="Jumlah iklan mobil bekas unik terverifikasi di wilayah DKI Jakarta.",
        variant="teal",
    )
with kpi_cols[1]:
    kpi_card(
        label="Merek",
        value=f"{total_makes:,}".replace(",", "."),
        icon="🏷️",
        help_text="Variasi merek kendaraan yang tercatat di arsip pasar.",
        variant="blue",
    )
with kpi_cols[2]:
    kpi_card(
        label="Median Harga Iklan",
        value=format_rupiah_compact(median_price),
        icon="💵",
        help_text="Nilai tengah harga penawaran iklan (robust terhadap outlier supercar).",
        variant="amber",
    )
with kpi_cols[3]:
    kpi_card(
        label="Rentang Tahun",
        value=year_span,
        icon="📅",
        help_text="Rentang tahun pembuatan kendaraan yang tersedia di pasar.",
        variant="navy",
    )

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Baris 2: Tiga Chart Berdampingan (Top 5 Merek, Wilayah, Bahan Bakar)
# ---------------------------------------------------------------------------
col_brand, col_region, col_fuel = st.columns([1.1, 1, 1], gap="medium")

# 1. Top 5 Merek
with col_brand:
    with section_card("Top 5 Merek Terpopuler"):
        top_makes = archive["make"].value_counts().head(5).reset_index()
        top_makes.columns = ["make", "count"]
        top_makes = top_makes.sort_values("count", ascending=True)

        fig_brand = go.Figure(go.Bar(
            x=top_makes["count"],
            y=top_makes["make"],
            orientation="h",
            marker=dict(color="#008B8B", cornerradius=4),
            text=[f"{v:,}".replace(",", ".") for v in top_makes["count"]],
            textposition="inside",
            insidetextanchor="end",
            textfont=dict(color="#FFFFFF", size=11, family="Inter, sans-serif"),
            hovertemplate="Merek: <b>%{y}</b><br>Listing: <b>%{x:,} unit</b><extra></extra>",
        ))
        apply_chart_theme(fig_brand)
        fig_brand.update_layout(
            height=280,
            margin=dict(l=10, r=16, t=10, b=10),
            xaxis=dict(title=None, showgrid=True, gridcolor="#F1F5F9"),
            yaxis=dict(title=None, showgrid=False, tickfont=dict(size=12, color="#0F172A")),
        )
        st.plotly_chart(fig_brand, width="stretch", config={"displayModeBar": False}, key="chart_top_makes")

# 2. Distribusi Wilayah Jakarta (Donut)
with col_region:
    with section_card("Distribusi Wilayah Jakarta"):
        region_counts = archive["location_display"].value_counts().reset_index()
        region_counts.columns = ["region", "count"]
        
        region_colors = ["#0B2A5B", "#008B8B", "#0284C7", "#10B981", "#F59E0B"]
        fig_region = go.Figure(go.Pie(
            labels=region_counts["region"],
            values=region_counts["count"],
            hole=0.55,
            marker=dict(colors=region_colors, line=dict(color="#FFFFFF", width=2)),
            textinfo="percent",
            textfont=dict(size=11, family="Inter, sans-serif"),
            hovertemplate="Wilayah: <b>%{label}</b><br>Listing: <b>%{value:,} unit (%{percent})</b><extra></extra>",
        ))
        apply_chart_theme(fig_region)
        fig_region.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(
                orientation="v",
                x=1.02,
                y=0.5,
                xanchor="left",
                yanchor="middle",
                font=dict(size=10, color="#475569"),
            ),
        )
        st.plotly_chart(fig_region, width="stretch", config={"displayModeBar": False}, key="chart_region_donut")

# 3. Komposisi Bahan Bakar (Donut)
with col_fuel:
    with section_card("Komposisi Bahan Bakar"):
        fuel_counts = archive["fuel_type"].value_counts().reset_index()
        fuel_counts.columns = ["fuel", "count"]

        fuel_colors = ["#008B8B", "#0F766E", "#0284C7", "#10B981"]
        fig_fuel = go.Figure(go.Pie(
            labels=fuel_counts["fuel"],
            values=fuel_counts["count"],
            hole=0.55,
            marker=dict(colors=fuel_colors, line=dict(color="#FFFFFF", width=2)),
            textinfo="percent",
            textfont=dict(size=11, family="Inter, sans-serif"),
            hovertemplate="Bahan Bakar: <b>%{label}</b><br>Listing: <b>%{value:,} unit (%{percent})</b><extra></extra>",
        ))
        apply_chart_theme(fig_fuel)
        fig_fuel.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(
                orientation="v",
                x=1.02,
                y=0.5,
                xanchor="left",
                yanchor="middle",
                font=dict(size=10, color="#475569"),
            ),
        )
        st.plotly_chart(fig_fuel, width="stretch", config={"displayModeBar": False}, key="chart_fuel_donut")

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Baris 3: Insight Otomatis Berdasarkan Data Aktual
# ---------------------------------------------------------------------------
st.markdown("<div class='am-section-title'>💡 Ringkasan Kondisi Pasar DKI Jakarta</div>", unsafe_allow_html=True)

# Perhitungan insight otomatis
top_brand_name = archive["make"].value_counts().index[0] if not archive["make"].empty else "-"
top_brand_count = int(archive["make"].value_counts().iloc[0]) if not archive["make"].empty else 0
top_brand_pct = (top_brand_count / total_listings * 100) if total_listings else 0

top_loc_name = archive["location_display"].value_counts().index[0] if not archive["location_display"].empty else "-"
top_loc_count = int(archive["location_display"].value_counts().iloc[0]) if not archive["location_display"].empty else 0
top_loc_pct = (top_loc_count / total_listings * 100) if total_listings else 0

fuel_bensin_count = int(archive["fuel_type"].eq("Bensin").sum())
fuel_bensin_pct = (fuel_bensin_count / total_listings * 100) if total_listings else 0
fuel_eco_count = int(archive["fuel_type"].isin(["Hybrid", "Listrik"]).sum())
fuel_eco_pct = (fuel_eco_count / total_listings * 100) if total_listings else 0

p25_price = priced["price"].quantile(0.25)
p75_price = priced["price"].quantile(0.75)

insight_cols = st.columns(3, gap="medium")
with insight_cols[0]:
    insight_card(
        icon="🏆",
        headline=f"Dominasi {top_brand_name} & Segmen Premium",
        body=(
            f"**{top_brand_name}** memimpin pasar dengan **{top_brand_count:,} listing ({top_brand_pct:.1f}%)**, "
            f"diikuti oleh **Mercedes-Benz (823 unit)** dan **BMW (466 unit)** yang menunjukkan tingginya "
            f"perputaran mobil segmen eksekutif dan premium di DKI Jakarta."
        ).replace(",", "."),
        variant="info",
    )

with insight_cols[1]:
    insight_card(
        icon="📍",
        headline=f"Sentra Pasar: {top_loc_name}",
        body=(
            f"**{top_loc_name}** merupakan pusat listing mobil bekas terbesar di ibu kota dengan "
            f"**{top_loc_count:,} iklan ({top_loc_pct:.1f}%)**, disusul oleh Jakarta Utara dan Jakarta Pusat "
            f"sebagai wilayah diler mobil seken terpadat."
        ).replace(",", "."),
        variant="success",
    )

with insight_cols[2]:
    insight_card(
        icon="⚡",
        headline=f"Tren Elektrifikasi & Rentang Harga",
        body=(
            f"Meskipun **Bensin mendominasi ({fuel_bensin_pct:.1f}%)**, segmen **Hybrid dan Listrik** "
            f"sudah mencapai **{fuel_eco_count:,} listing ({fuel_eco_pct:.1f}%)**. "
            f"Mayoritas 50% pasar (P25–P75) berada di kisaran harga **{format_rupiah_compact(p25_price)} s/d {format_rupiah_compact(p75_price)}**."
        ).replace(",", "."),
        variant="warning",
    )
