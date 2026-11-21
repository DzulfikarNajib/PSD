"""Eksplorasi Data - analisis distribusi dan hubungan antarvariabel.

Menampilkan visualisasi multivariat dan bivariat:
- Filter interaktif (Wilayah, Merek, Tahun, Bahan Bakar, Tipe Bodi)
- Distribusi Harga (dengan opsi <= 95% pasar vs Seluruh Data)
- Top Merek & Harga per Tipe Kendaraan
- Tahun vs Harga & Kilometer vs Harga (Scatter)
- Listing per Wilayah (5 wilayah DKI)
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
from src.ui import apply_rupiah_ticks, format_rupiah_compact
from src.ui_components import (
    apply_chart_theme,
    insight_card,
    page_header,
    section_card,
)

apply_theme()

page_header(
    icon="trending-up",
    title="Eksplorasi Data",
    subtitle="Menemukan pola dan hubungan antarvariabel pada data mobil bekas di DKI Jakarta.",
)

archive = load_combined_archive()

if archive.empty:
    st.warning("Belum ada data pasar mobil bekas yang tersedia.", icon=":material/warning:")
    st.stop()

# Konversi dan normalisasi data
for col in ("price", "year", "mileage_km", "engine_cc"):
    if col in archive:
        archive[col] = pd.to_numeric(archive[col], errors="coerce")

archive["location_display"] = archive["location_normalized"].fillna("").astype(str).str.title()
dki_5 = ["Jakarta Selatan", "Jakarta Utara", "Jakarta Pusat", "Jakarta Barat", "Jakarta Timur"]
archive = archive[archive["location_display"].isin(dki_5)].copy()

# ---------------------------------------------------------------------------
# Filter Bar Terpadu (Atas)
# ---------------------------------------------------------------------------
with st.container(border=True):
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.2, 1.2, 1.4, 1.1, 1.1])
    
    with f_col1:
        region_options = ["Semua Wilayah"] + sorted(archive["location_display"].dropna().unique().tolist())
        selected_region = st.selectbox("Wilayah", region_options, index=0)
        
    with f_col2:
        makes_available = sorted(archive["make"].dropna().unique().tolist())
        make_options = ["Semua Merek"] + makes_available
        selected_make = st.selectbox("Merek", make_options, index=0)
        
    with f_col3:
        y_min = int(archive["year"].min()) if archive["year"].notna().any() else 1990
        y_max = int(archive["year"].max()) if archive["year"].notna().any() else 2026
        selected_years = st.slider("Rentang Tahun", min_value=y_min, max_value=y_max, value=(y_min, y_max))
        
    with f_col4:
        fuels_available = sorted(archive["fuel_type"].dropna().unique().tolist())
        fuel_options = ["Semua BBM"] + fuels_available
        selected_fuel = st.selectbox("Bahan Bakar", fuel_options, index=0)
        
    with f_col5:
        bodies_available = sorted(archive["body_type"].dropna().replace("", pd.NA).dropna().unique().tolist())
        body_options = ["Semua Bodi"] + bodies_available
        selected_body = st.selectbox("Tipe Bodi", body_options, index=0)

# Terapkan filter
filtered = archive.copy()
if selected_region != "Semua Wilayah":
    filtered = filtered[filtered["location_display"].eq(selected_region)]
if selected_make != "Semua Merek":
    filtered = filtered[filtered["make"].eq(selected_make)]
filtered = filtered[filtered["year"].between(selected_years[0], selected_years[1]) | filtered["year"].isna()]
if selected_fuel != "Semua BBM":
    filtered = filtered[filtered["fuel_type"].eq(selected_fuel)]
if selected_body != "Semua Bodi":
    filtered = filtered[filtered["body_type"].eq(selected_body)]

st.caption(f"Menampilkan **{len(filtered):,}** dari total {len(archive):,} listing terfilter.")

if filtered.empty:
    st.info("Tidak ada mobil yang cocok dengan kombinasi filter yang dipilih.")
    st.stop()

# ---------------------------------------------------------------------------
# Baris 1: Distribusi Harga, Top Merek, Harga per Tipe Bodi
# ---------------------------------------------------------------------------
r1_c1, r1_c2, r1_c3 = st.columns([1.2, 1, 1], gap="medium")

# 1. Distribusi Harga dengan Toggle P95 / Semua
with r1_c1:
    with section_card("Distribusi Harga Iklan"):
        priced_f = filtered[filtered["price"].gt(0)].dropna(subset=["price"]).copy()
        
        mode_scope = st.radio(
            "Cakupan",
            ["≤ Persentil 95 (Pasar Umum)", "Semua Data"],
            horizontal=True,
            label_visibility="collapsed",
            key="eda_price_scope",
        )
        
        if not priced_f.empty:
            if "95" in mode_scope:
                p95 = priced_f["price"].quantile(0.95)
                plot_prices = priced_f[priced_f["price"].le(p95)]["price"]
            else:
                plot_prices = priced_f["price"]

            plot_prices_jt = plot_prices / 1_000_000
            median_jt = plot_prices_jt.median()

            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=plot_prices_jt,
                nbinsx=30,
                marker=dict(color="#019F90", line=dict(color="#007A6E", width=1)),
                hovertemplate="Rentang: Rp %{x:.0f} Jt<br>Frekuensi: <b>%{y:,} listing</b><extra></extra>",
            ))
            fig_hist.add_vline(
                x=median_jt,
                line_dash="dash",
                line_color="#F59E0B",
                line_width=2,
                annotation_text=f"  Median: Rp {median_jt:.0f} Jt",
                annotation_position="top left",
                annotation_font=dict(size=10, color="#D97706"),
                annotation_xanchor="left",
            )
            apply_chart_theme(fig_hist)
            fig_hist.update_layout(
                height=260,
                margin=dict(l=10, r=16, t=20, b=10),
                xaxis=dict(title="Harga (Juta Rp)", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="Jumlah Iklan", showgrid=True, gridcolor="#F1F5F9"),
            )
            st.plotly_chart(fig_hist, width="stretch", config={"displayModeBar": False}, key="chart_eda_hist")
        else:
            st.caption("Data harga tidak tersedia.")

# 2. Top Merek pada Filter Ini
with r1_c2:
    with section_card("Top Merek"):
        top_f_makes = filtered["make"].value_counts().head(5).reset_index()
        top_f_makes.columns = ["make", "count"]
        top_f_makes = top_f_makes.sort_values("count", ascending=True)
        max_cnt = float(top_f_makes["count"].max()) if not top_f_makes.empty else 100.0

        fig_f_makes = go.Figure(go.Bar(
            x=top_f_makes["count"],
            y=top_f_makes["make"],
            orientation="h",
            marker=dict(color="#019F90", cornerradius=4),
            text=[f"{v:,}".replace(",", ".") for v in top_f_makes["count"]],
            textposition="auto",
            hovertemplate="Merek: <b>%{y}</b><br>Listing: <b>%{x:,}</b><extra></extra>",
        ))
        apply_chart_theme(fig_f_makes)
        fig_f_makes.update_layout(
            height=295,
            margin=dict(l=10, r=20, t=10, b=10),
            xaxis=dict(title=None, showgrid=True, gridcolor="#F1F5F9", range=[0, max_cnt * 1.2]),
            yaxis=dict(title=None, showgrid=False),
        )
        st.plotly_chart(fig_f_makes, width="stretch", config={"displayModeBar": False}, key="chart_eda_makes")

# 3. Median Harga per Tipe Bodi (horizontal bar agar label tidak terpotong)
with r1_c3:
    with section_card("Harga per Tipe Mobil"):
        body_data = filtered.dropna(subset=["body_type", "price"])
        body_data = body_data[body_data["body_type"].ne("") & body_data["price"].gt(0)]
        
        if not body_data.empty:
            body_median = body_data.groupby("body_type")["price"].median().reset_index()
            body_median["price_jt"] = body_median["price"] / 1_000_000
            body_median = body_median.sort_values("price_jt", ascending=True).head(6)
            max_body = float(body_median["price_jt"].max()) if not body_median.empty else 100.0

            fig_body = go.Figure(go.Bar(
                x=body_median["price_jt"],
                y=body_median["body_type"],
                orientation="h",
                marker=dict(color="#00B8A9", cornerradius=4),
                text=[f"Rp {v:.0f} Jt" for v in body_median["price_jt"]],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="Tipe: <b>%{y}</b><br>Median: <b>Rp %{x:.1f} Jt</b><extra></extra>",
            ))
            apply_chart_theme(fig_body)
            fig_body.update_layout(
                height=295,
                margin=dict(l=10, r=60, t=10, b=10),
                xaxis=dict(title="Median Harga (Jt Rp)", showgrid=True, gridcolor="#F1F5F9", range=[0, max_body * 1.3]),
                yaxis=dict(title=None, showgrid=False, tickfont=dict(size=11)),
            )
            st.plotly_chart(fig_body, width="stretch", config={"displayModeBar": False}, key="chart_eda_body")
        else:
            st.caption("Data tipe bodi tidak tersedia.")

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Baris 2: Tahun vs Harga, KM vs Harga, Listing per Wilayah
# ---------------------------------------------------------------------------
r2_c1, r2_c2, r2_c3 = st.columns([1.1, 1.1, 1], gap="medium")

# 1. Tahun Kendaraan vs Harga (Scatter)
with r2_c1:
    with section_card("Tahun vs Harga"):
        pair_year = filtered.dropna(subset=["year", "price"]).copy()
        pair_year = pair_year[pair_year["price"].gt(0) & pair_year["year"].ge(1990)]
        
        if len(pair_year) > 1000:
            pair_year = pair_year.sample(1000, random_state=42)
            
        if not pair_year.empty:
            pair_year["price_jt"] = pair_year["price"] / 1_000_000
            fig_yvsp = px.scatter(
                pair_year,
                x="year",
                y="price_jt",
                color_discrete_sequence=["#019F90"],
                render_mode="svg",
                labels={"year": "Tahun", "price_jt": "Harga (Jt)"},
                hover_data={"make": True, "model": True, "year": True, "price_jt": ":.1f"},
            )
            apply_chart_theme(fig_yvsp)
            fig_yvsp.update_traces(marker=dict(size=5, opacity=0.55))
            fig_yvsp.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Tahun Pembuatan", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="Harga (Juta Rp)", showgrid=True, gridcolor="#F1F5F9"),
            )
            st.plotly_chart(fig_yvsp, width="stretch", config={"displayModeBar": False}, key="chart_eda_year_price")
        else:
            st.caption("Data tahun dan harga tidak tersedia.")

# 2. KM vs Harga (Scatter)
with r2_c2:
    with section_card("KM vs Harga"):
        pair_km = filtered.dropna(subset=["mileage_km", "price"]).copy()
        pair_km = pair_km[pair_km["price"].gt(0) & pair_km["mileage_km"].ge(0) & pair_km["mileage_km"].le(250_000)]
        
        if len(pair_km) > 1000:
            pair_km = pair_km.sample(1000, random_state=42)
            
        if not pair_km.empty:
            pair_km["price_jt"] = pair_km["price"] / 1_000_000
            pair_km["km_rb"] = pair_km["mileage_km"] / 1_000
            
            fig_kmvsp = px.scatter(
                pair_km,
                x="km_rb",
                y="price_jt",
                color_discrete_sequence=["#00B8A9"],
                render_mode="svg",
                labels={"km_rb": "Kilometer (Ribu)", "price_jt": "Harga (Jt)"},
                hover_data={"make": True, "model": True, "km_rb": ":.0f", "price_jt": ":.1f"},
            )
            apply_chart_theme(fig_kmvsp)
            fig_kmvsp.update_traces(marker=dict(size=5, opacity=0.55))
            fig_kmvsp.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Kilometer (Ribu km)", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="Harga (Juta Rp)", showgrid=True, gridcolor="#F1F5F9"),
            )
            st.plotly_chart(fig_kmvsp, width="stretch", config={"displayModeBar": False}, key="chart_eda_km_price")
        else:
            st.caption("Data kilometer dan harga tidak tersedia.")

# 3. Listing per Wilayah
with r2_c3:
    with section_card("Listing per Wilayah"):
        loc_dist = filtered["location_display"].value_counts().reset_index()
        loc_dist.columns = ["Wilayah", "Listing"]
        loc_dist = loc_dist.sort_values("Listing", ascending=False)
        max_loc = float(loc_dist["Listing"].max()) if not loc_dist.empty else 100.0

        fig_loc = go.Figure(go.Bar(
            x=loc_dist["Wilayah"],
            y=loc_dist["Listing"],
            marker=dict(color="#0D1E38", cornerradius=4),
            text=[f"{v:,}".replace(",", ".") for v in loc_dist["Listing"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="Wilayah: <b>%{x}</b><br>Listing: <b>%{y:,}</b><extra></extra>",
        ))
        apply_chart_theme(fig_loc)
        fig_loc.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(title=None, tickangle=-15, showgrid=False),
            yaxis=dict(title="Jumlah Listing", showgrid=True, gridcolor="#F1F5F9", range=[0, max_loc * 1.25]),
        )
        st.plotly_chart(fig_loc, width="stretch", config={"displayModeBar": False}, key="chart_eda_region_bar")

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Baris 3: Key Insights Eksplorasi & Rekomendasi Pencarian
# ---------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("<div class='am-section-title'>Key Insights & Panduan Rekomendasi Mobil Bekas</div>", unsafe_allow_html=True)
    ins_cols = st.columns(3, gap="medium")
    with ins_cols[0]:
        insight_card(
            icon="trending-up",
            headline="Sweet Spot Depresiasi (Usia 3-5 Tahun)",
            body=(
                "Mobil bekas berusia <b>3 hingga 5 tahun</b> mengalami pelandaian kurva depresiasi paling signifikan. "
                "Harga pasar telah terdiskon <b>30%-45% dari harga baru</b>, sementara kondisi mesin dan komponen vital "
                "masih berada pada performa optimal."
            ),
            variant="success",
        )
    with ins_cols[1]:
        insight_card(
            icon="gauge",
            headline="Ambang Batas Jarak Tempuh Sehat",
            body=(
                "Untuk penggunaan harian di Jabodetabek, median kilometer berada di kisaran <b>45.000 km</b> (~10.000-12.000 km/tahun). "
                "Unit dengan odometer di bawah <b>60.000 km</b> dan riwayat servis resmi menawarkan rasio keandalan tertinggi."
            ),
            variant="info",
        )
    with ins_cols[2]:
        insight_card(
            icon="search",
            headline="Rekomendasi Lanjut ke Cek Harga",
            body=(
                "Gunakan wawasan harga di atas saat mencari unit idaman. Lanjutkan ke menu <b>Cek Harga Iklan</b> "
                "untuk menyaring mobil sesuai budget dan memverifikasi kewajaran harga penawaran secara langsung."
            ),
            variant="warning",
        )
