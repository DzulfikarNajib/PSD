"""Eksplorasi Data - pemetaan wilayah interaktif dan analisis pola harga mobil bekas DKI Jakarta.

Menampilkan:
1. Peta Sebaran Iklan DKI Jakarta (klik wilayah untuk auto-zoom & rincian merek, model, BBM, + link ke Cek Mobil dan Harga)
2. Grafik Sebaran Harga Iklan + Insight Data
3. Grafik Top Merek Terpopuler (interaktif menuju Cek Mobil dan Harga) + Insight Data
4. Grafik Proporsi Bahan Bakar + Insight Data
5. Grafik Tahun vs Harga & Jarak Tempuh vs Harga (1 kartu dengan pemilih variabel + garis tren median) + Insight Data
"""

from __future__ import annotations

import json
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
from src.ui import format_km, format_rupiah_compact
from src.ui_components import (
    apply_chart_theme,
    get_lucide_icon,
    insight_card,
    kpi_card,
    page_header,
    section_card,
)

apply_theme()

page_header(
    icon="trending-up",
    title="Eksplorasi Data Pasar",
    subtitle="Telusuri peta sebaran iklan di 5 wilayah DKI Jakarta, distribusi harga, merek terpopuler, bahan bakar, serta kurva depresiasi kendaraan.",
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

# Muat GeoJSON resmi 5 Kota DKI Jakarta (DPMPTSP DKI batas_kota_kab, tanpa Kep. Seribu)
geojson_path = APP_DIR / "assets" / "dki_kota.geojson"
if geojson_path.exists():
    raw_geojson = json.loads(geojson_path.read_text(encoding="utf-8"))
    dki_geojson = {
        "type": "FeatureCollection",
        "features": [
            f for f in raw_geojson.get("features", [])
            if str(f.get("properties", {}).get("kdpkab", "")) != "3101"
        ],
    }
else:
    dki_geojson = {"type": "FeatureCollection", "features": []}

if "eda_selected_region" not in st.session_state:
    st.session_state["eda_selected_region"] = "Semua Wilayah DKI"

# ---------------------------------------------------------------------------
# PETA SEBARAN IKLAN DI WILAYAH DKI JAKARTA (Klik & Auto-Zoom)
# ---------------------------------------------------------------------------
with section_card("Peta Sebaran Iklan Mobil Bekas di Wilayah DKI Jakarta"):
    st.caption(
        "Klik langsung wilayah pada peta atau pilih nama kota di bawah untuk melakukan **zoom otomatis** "
        "dan melihat profil spesifik jumlah iklan, merek, model terpopuler, serta bahan bakar dominan."
    )

    region_options = ["Semua Wilayah DKI"] + dki_5
    reg_ctrl_c1, reg_ctrl_c2 = st.columns([3, 1], vertical_alignment="center")
    with reg_ctrl_c1:
        chosen_reg_pill = st.radio(
            "Fokus Wilayah:",
            region_options,
            index=region_options.index(st.session_state["eda_selected_region"])
            if st.session_state["eda_selected_region"] in region_options
            else 0,
            horizontal=True,
            label_visibility="collapsed",
            key="eda_region_radio",
        )
        if chosen_reg_pill != st.session_state["eda_selected_region"]:
            st.session_state["eda_selected_region"] = chosen_reg_pill
            st.rerun()

    with reg_ctrl_c2:
        if st.session_state["eda_selected_region"] != "Semua Wilayah DKI":
            if st.button("Reset Zoom (Semua DKI)", use_container_width=True, key="btn_reset_map_zoom"):
                st.session_state["eda_selected_region"] = "Semua Wilayah DKI"
                st.rerun()

    active_region = st.session_state["eda_selected_region"]

    # Agregasi statistik per wilayah untuk peta
    reg_agg = (
        archive.groupby("location_display")
        .agg(
            listing_count=("listing_id", "count"),
            make_count=("make", "nunique"),
            model_count=("model", "nunique"),
            median_price=("price", "median"),
            top_fuel=("fuel_type", lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else "-"),
            top_model=("model", lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else "-"),
        )
        .reindex(dki_5)
        .reset_index()
    )
    reg_agg.columns = ["region", "listing_count", "make_count", "model_count", "median_price", "top_fuel", "top_model"]
    reg_agg["region_upper"] = reg_agg["region"].str.upper()
    reg_agg["listing_count"] = reg_agg["listing_count"].fillna(0).astype(int)
    reg_agg["median_price_str"] = reg_agg["median_price"].fillna(0).map(format_rupiah_compact)

    # Koordinat titik tengah label wilayah DKI (disesuaikan poligon resmi DPMPTSP)
    centers = {
        "Jakarta Utara": (-6.128, 106.890),
        "Jakarta Barat": (-6.168, 106.752),
        "Jakarta Pusat": (-6.182, 106.835),
        "Jakarta Timur": (-6.250, 106.905),
        "Jakarta Selatan": (-6.275, 106.810),
    }
    reg_agg["lat"] = reg_agg["region"].map(lambda r: centers.get(r, (-6.2, 106.84))[0])
    reg_agg["lon"] = reg_agg["region"].map(lambda r: centers.get(r, (-6.2, 106.84))[1])

    map_col, detail_col = st.columns([1.25, 1], gap="medium")

    with map_col:
        # Filter GeoJSON jika 1 wilayah dipilih agar fitbounds otomatis zoom-in ke wilayah tersebut
        if active_region != "Semua Wilayah DKI":
            active_geojson = {
                "type": "FeatureCollection",
                "features": [
                    f for f in dki_geojson.get("features", [])
                    if str(f.get("properties", {}).get("wadmkk", "")).upper() == active_region.upper()
                ],
            }
            plot_reg_df = reg_agg[reg_agg["region"].eq(active_region)].copy()
        else:
            active_geojson = dki_geojson
            plot_reg_df = reg_agg.copy()

        fig_map = go.Figure()

        # Choropleth SVG menggunakan batas resmi DPMPTSP DKI (tajam, akurat, 100% bebas WebGL)
        fig_map.add_trace(
            go.Choropleth(
                geojson=active_geojson,
                locations=plot_reg_df["region_upper"],
                z=plot_reg_df["listing_count"],
                featureidkey="properties.wadmkk",
                colorscale=[
                    [0.0, "#D9F2EE"],
                    [0.35, "#72C8BC"],
                    [0.7, "#019F90"],
                    [1.0, "#006B61"],
                ],
                zmin=0,
                zmax=int(reg_agg["listing_count"].max()),
                marker_line_color="#FFFFFF",
                marker_line_width=2.0,
                showscale=True,
                colorbar=dict(
                    title=dict(text="Jumlah Iklan", font=dict(size=10, color="#475569")),
                    orientation="h",
                    thickness=10,
                    len=0.55,
                    x=0.5,
                    xanchor="center",
                    y=-0.04,
                    yanchor="top",
                    tickfont=dict(size=10, color="#475569"),
                ),
                customdata=np.stack(
                    [
                        plot_reg_df["region"],
                        plot_reg_df["make_count"],
                        plot_reg_df["model_count"],
                        plot_reg_df["top_model"],
                        plot_reg_df["top_fuel"],
                        plot_reg_df["median_price_str"],
                    ],
                    axis=-1,
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Jumlah Iklan: <b>%{z:,} unit</b><br>"
                    "Variasi: <b>%{customdata[1]} Merek · %{customdata[2]} Model</b><br>"
                    "Model Terbanyak: <b>%{customdata[3]}</b><br>"
                    "BBM Dominan: <b>%{customdata[4]}</b><br>"
                    "Median Harga: <b>%{customdata[5]}</b><extra></extra>"
                ),
            )
        )

        # Label kota & jumlah iklan dengan kontras adaptif (putih pada poligon gelap, navy pada terang)
        dark_mask = plot_reg_df["listing_count"] >= (reg_agg["listing_count"].max() * 0.55)
        for subset_df, txt_color in [
            (plot_reg_df[~dark_mask], "#0D1E38"),
            (plot_reg_df[dark_mask], "#FFFFFF"),
        ]:
            if not subset_df.empty:
                fig_map.add_trace(
                    go.Scattergeo(
                        lat=subset_df["lat"],
                        lon=subset_df["lon"],
                        text=[
                            f"<b>{r}</b><br>{c:,} iklan".replace(",", ".")
                            for r, c in zip(subset_df["region"], subset_df["listing_count"])
                        ],
                        mode="text",
                        textposition="middle center",
                        textfont=dict(family="Plus Jakarta Sans, Inter, sans-serif", size=11, color=txt_color),
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )

        fig_map.update_geos(
            fitbounds="locations",
            visible=False,
            projection_type="mercator",
            bgcolor="#FFFFFF",
        )
        fig_map.update_layout(
            height=410,
            margin=dict(l=0, r=0, t=4, b=28),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            dragmode="pan",
        )

        map_event = st.plotly_chart(
            fig_map,
            width="stretch",
            key="chart_dki_choropleth_map",
            on_select="rerun",
            selection_mode="points",
            config={"scrollZoom": True, "displayModeBar": True, "displaylogo": False},
        )

        # Tangkap klik wilayah dari peta
        if map_event and hasattr(map_event, "selection") and map_event.selection:
            pts = map_event.selection.get("points", [])
            if pts:
                clicked_loc = str(pts[0].get("location", "")).title()
                if clicked_loc in dki_5 and clicked_loc != st.session_state["eda_selected_region"]:
                    st.session_state["eda_selected_region"] = clicked_loc
                    st.rerun()

    # Panel Kanan: Detail Spesifik Wilayah yang Diklik
    with detail_col:
        if active_region == "Semua Wilayah DKI":
            reg_df = archive.copy()
            reg_title = "Semua Wilayah DKI Jakarta (5 Kota)"
        else:
            reg_df = archive[archive["location_display"].eq(active_region)].copy()
            reg_title = active_region

        reg_total = len(reg_df)
        reg_share = (reg_total / len(archive) * 100) if len(archive) else 0.0
        reg_makes = int(reg_df["make"].dropna().nunique())
        reg_models = int(reg_df["model"].dropna().nunique())
        reg_med_price = float(reg_df[reg_df["price"].gt(0)]["price"].median()) if not reg_df.empty else 0.0

        top_fuel_s = reg_df["fuel_type"].dropna().value_counts()
        reg_top_fuel = top_fuel_s.index[0] if not top_fuel_s.empty else "-"
        reg_top_fuel_pct = (top_fuel_s.iloc[0] / reg_total * 100) if (not top_fuel_s.empty and reg_total) else 0.0

        top_models_s = (
            reg_df.assign(full_model=reg_df["make"].fillna("") + " " + reg_df["model"].fillna(""))
            ["full_model"]
            .str.strip()
            .value_counts()
            .head(4)
        )
        top_models_badges = "".join(
            [
                f'<div style="display:flex;justify-content:space-between;padding:0.28rem 0;border-bottom:1px solid #F1F5F9;font-size:0.8rem;">'
                f'<span style="color:#0D1E38;font-weight:600;">{m_name}</span>'
                f'<span style="color:#019F90;font-weight:700;">{m_cnt:,} unit</span></div>'.replace(",", ".")
                for m_name, m_cnt in top_models_s.items()
            ]
        )

        pin_svg = get_lucide_icon("map-pin", size=18, color="#019F90")
        st.markdown(
            f"""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:1rem 1.15rem;">
                <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.55rem;">
                    <span style="display:inline-flex;align-items:center;justify-content:center;width:2rem;height:2rem;border-radius:8px;background:#E6F7F5;">{pin_svg}</span>
                    <div>
                        <div style="font-size:0.72rem; color:#64748B; font-weight:600; text-transform:uppercase;">Profil Wilayah Terpilih</div>
                        <div style="font-size:1.05rem; font-weight:800; color:#0D1E38;">{reg_title}</div>
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.55rem; margin-bottom:0.75rem;">
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:0.55rem 0.7rem;">
                        <div style="font-size:0.72rem; color:#64748B;">Jumlah Iklan</div>
                        <div style="font-size:1.15rem; font-weight:800; color:#019F90;">{reg_total:,} Unit</div>
                        <div style="font-size:0.7rem; color:#64748B;">{reg_share:.1f}% pangsa DKI</div>
                    </div>
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:0.55rem 0.7rem;">
                        <div style="font-size:0.72rem; color:#64748B;">Merek &amp; Model</div>
                        <div style="font-size:1.15rem; font-weight:800; color:#0D1E38;">{reg_makes} Merek</div>
                        <div style="font-size:0.7rem; color:#64748B;">{reg_models} model tersedia</div>
                    </div>
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:0.55rem 0.7rem;">
                        <div style="font-size:0.72rem; color:#64748B;">BBM Terbanyak</div>
                        <div style="font-size:1.02rem; font-weight:800; color:#0D1E38;">{reg_top_fuel}</div>
                        <div style="font-size:0.7rem; color:#64748B;">{reg_top_fuel_pct:.1f}% unit wilayah ini</div>
                    </div>
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:0.55rem 0.7rem;">
                        <div style="font-size:0.72rem; color:#64748B;">Median Harga</div>
                        <div style="font-size:1.02rem; font-weight:800; color:#0D1E38;">{format_rupiah_compact(reg_med_price)}</div>
                        <div style="font-size:0.7rem; color:#64748B;">Harga tengah pasar</div>
                    </div>
                </div>
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:0.6rem 0.8rem; margin-bottom:0.65rem;">
                    <div style="font-size:0.73rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:0.25rem;">Model Mobil Terbanyak di {reg_title}</div>
                    {top_models_badges}
                </div>
            </div>
            """.replace(",", "."),
            unsafe_allow_html=True,
        )

        btn_label_reg = (
            f"Lihat & Cek Harga Mobil di {active_region}"
            if active_region != "Semua Wilayah DKI"
            else "Lihat & Cek Harga Mobil Seluruh DKI Jakarta"
        )
        if st.button(btn_label_reg, type="primary", use_container_width=True, key="btn_map_to_cek"):
            st.session_state["prefill_cek_region"] = (
                active_region if active_region != "Semua Wilayah DKI" else "Semua Wilayah"
            )
            st.switch_page("pages/cek_harga_iklan.py")

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# Data yang digunakan pada grafik di bawah mengikuti wilayah yang sedang dipilih (atau seluruh DKI)
filtered = (
    archive[archive["location_display"].eq(active_region)].copy()
    if active_region != "Semua Wilayah DKI"
    else archive.copy()
)
scope_label = active_region if active_region != "Semua Wilayah DKI" else "DKI Jakarta"

# ---------------------------------------------------------------------------
# Baris 2: (2) Grafik Sebaran Harga & (3) Grafik Top Merek (Interaktif ke Cek Harga)
# ---------------------------------------------------------------------------
row2_c1, row2_c2 = st.columns(2, gap="medium")

# 2. Grafik Sebaran Harga
with row2_c1:
    with section_card(f"Sebaran Harga Iklan ({scope_label})"):
        priced_f = filtered[filtered["price"].gt(0)].dropna(subset=["price"]).copy()

        mode_scope = st.radio(
            "Cakupan Harga",
            ["<= Persentil 95 (Pasar Umum)", "Semua Data"],
            horizontal=True,
            label_visibility="collapsed",
            key="eda_price_scope",
        )

        if not priced_f.empty:
            p95_val = float(priced_f["price"].quantile(0.95))
            p25_val = float(priced_f["price"].quantile(0.25))
            p75_val = float(priced_f["price"].quantile(0.75))
            med_val = float(priced_f["price"].median())

            if "95" in mode_scope:
                plot_prices = priced_f[priced_f["price"].le(p95_val)]["price"]
            else:
                plot_prices = priced_f["price"]

            plot_prices_jt = plot_prices / 1_000_000
            median_jt = plot_prices_jt.median()

            fig_hist = go.Figure()
            fig_hist.add_trace(
                go.Histogram(
                    x=plot_prices_jt,
                    nbinsx=28,
                    marker=dict(color="#019F90", line=dict(color="#007A6E", width=1)),
                    hovertemplate="Rentang: Rp %{x:.0f} Jt<br>Frekuensi: <b>%{y:,} iklan</b><extra></extra>",
                )
            )
            fig_hist.add_vline(
                x=median_jt,
                line_dash="dash",
                line_color="#F59E0B",
                line_width=2.2,
                annotation_text=f"  Median: Rp {median_jt:.0f} Jt",
                annotation_position="top right",
                annotation_font=dict(size=11, color="#D97706"),
            )
            apply_chart_theme(fig_hist)
            fig_hist.update_layout(
                height=275,
                margin=dict(l=10, r=16, t=18, b=10),
                xaxis=dict(title="Harga Penawaran (Juta Rp)", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="Jumlah Iklan", showgrid=True, gridcolor="#F1F5F9"),
            )
            st.plotly_chart(fig_hist, width="stretch", config={"displayModeBar": False}, key="chart_eda_hist")

            under_300_pct = float((priced_f["price"].le(300_000_000)).mean() * 100)
            insight_card(
                icon="banknote",
                headline=f"Insight Harga: 50% Mobil Berada di {format_rupiah_compact(p25_val)} - {format_rupiah_compact(p75_val)}",
                body=(
                    f"Nilai tengah harga di {scope_label} adalah <b>{format_rupiah_compact(med_val)}</b>. "
                    f"Sebanyak <b>{under_300_pct:.1f}% iklan</b> ditawarkan di bawah Rp 300 Juta, menjadikannya "
                    "segmen paling likuid untuk pembeli mobil keluarga dan komuter harian."
                ),
                variant="info",
            )
        else:
            st.caption("Data harga tidak tersedia.")

# 3. Grafik Top Merek (Klik langsung ke Cek Mobil dan Harga)
with row2_c2:
    with section_card(f"Top Merek Terpopuler ({scope_label})"):
        top_makes_df = (
            filtered.groupby("make")
            .agg(count=("listing_id", "count"), median_price=("price", "median"))
            .sort_values("count", ascending=False)
            .head(7)
            .reset_index()
        )
        top_makes_plot = top_makes_df.sort_values("count", ascending=True).copy()
        max_cnt = float(top_makes_plot["count"].max()) if not top_makes_plot.empty else 100.0

        fig_f_makes = go.Figure(
            go.Bar(
                x=top_makes_plot["count"],
                y=top_makes_plot["make"],
                orientation="h",
                marker=dict(color="#019F90", cornerradius=5),
                text=[
                    f"{cnt:,} unit (Median {format_rupiah_compact(mp)})".replace(",", ".")
                    for cnt, mp in zip(top_makes_plot["count"], top_makes_plot["median_price"])
                ],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="Merek: <b>%{y}</b><br>Jumlah Iklan: <b>%{x:,} unit</b><extra></extra>",
            )
        )
        apply_chart_theme(fig_f_makes)
        fig_f_makes.update_layout(
            height=245,
            margin=dict(l=10, r=90, t=10, b=10),
            xaxis=dict(title=None, showgrid=True, gridcolor="#F1F5F9", range=[0, max_cnt * 1.48]),
            yaxis=dict(title=None, showgrid=False, tickfont=dict(size=12, color="#0D1E38")),
        )
        brand_event = st.plotly_chart(
            fig_f_makes,
            width="stretch",
            config={"displayModeBar": False},
            key="chart_eda_makes",
            on_select="rerun",
            selection_mode="points",
        )

        # Jika user klik batang merek di chart, langsung arahkan ke Cek Mobil dan Harga
        if brand_event and hasattr(brand_event, "selection") and brand_event.selection:
            b_pts = brand_event.selection.get("points", [])
            if b_pts:
                clicked_make = b_pts[0].get("y")
                if clicked_make:
                    st.session_state["prefill_cek_make"] = str(clicked_make)
                    st.session_state["prefill_cek_region"] = (
                        active_region if active_region != "Semua Wilayah DKI" else "Semua Wilayah"
                    )
                    st.switch_page("pages/cek_harga_iklan.py")

        # Pemilih cepat merek untuk menuju Cek Mobil dan Harga
        mk_c1, mk_c2 = st.columns([1.2, 1.3], vertical_alignment="center")
        with mk_c1:
            quick_make = st.selectbox(
                "Pilih Merek Diminati:",
                top_makes_df["make"].tolist(),
                index=0,
                label_visibility="collapsed",
                key="eda_quick_make_sel",
            )
        with mk_c2:
            if st.button(f"Cek Mobil {quick_make} & Harganya", type="primary", use_container_width=True, key="btn_make_to_cek"):
                st.session_state["prefill_cek_make"] = quick_make
                st.session_state["prefill_cek_region"] = (
                    active_region if active_region != "Semua Wilayah DKI" else "Semua Wilayah"
                )
                st.switch_page("pages/cek_harga_iklan.py")

        if not top_makes_df.empty:
            lead_make = top_makes_df.iloc[0]["make"]
            lead_cnt = int(top_makes_df.iloc[0]["count"])
            lead_pct = (lead_cnt / len(filtered) * 100) if len(filtered) else 0.0
            lead_med = float(top_makes_df.iloc[0]["median_price"])
            insight_card(
                icon="tag",
                headline=f"Insight Merek: {lead_make} Memimpin ({lead_pct:.1f}% Pasar)",
                body=(
                    f"<b>{lead_make}</b> memiliki ketersediaan tertinggi ({lead_cnt:,} unit, median <b>{format_rupiah_compact(lead_med)}</b>). "
                    "Klik batang merek di grafik atau tombol di atas untuk langsung menyaring daftar mobilnya."
                ).replace(",", "."),
                variant="success",
            )

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Baris 3: (4) Proporsi Bahan Bakar & (5) Tahun / Jarak Tempuh vs Harga (1 Card Toggle)
# ---------------------------------------------------------------------------
row3_c1, row3_c2 = st.columns(2, gap="medium")

# 4. Grafik Proporsi Bahan Bakar
with row3_c1:
    with section_card(f"Proporsi Bahan Bakar ({scope_label})"):
        fuel_df = (
            filtered.groupby("fuel_type")
            .agg(count=("listing_id", "count"), median_price=("price", "median"))
            .sort_values("count", ascending=False)
            .reset_index()
        )
        fuel_df.columns = ["fuel", "count", "median_price"]
        total_f_units = int(fuel_df["count"].sum()) if not fuel_df.empty else 1
        fuel_df["pct"] = fuel_df["count"] / total_f_units * 100

        # Hanya tampilkan teks % pada slice >= 5% agar irisan tipis tidak pernah bertumpuk
        slice_texts = [f"{p:.1f}%" if p >= 5.0 else "" for p in fuel_df["pct"]]
        legend_labels = [
            f"{r['fuel']} ({r['count']:,} unit · {r['pct']:.1f}%)".replace(",", ".")
            for _, r in fuel_df.iterrows()
        ]

        fuel_colors = ["#019F90", "#0D1E38", "#00B8A9", "#F59E0B"]
        fig_fuel = go.Figure(
            go.Pie(
                labels=legend_labels,
                values=fuel_df["count"],
                hole=0.62,
                marker=dict(colors=fuel_colors, line=dict(color="#FFFFFF", width=2.5)),
                text=slice_texts,
                textinfo="text",
                textposition="inside",
                insidetextorientation="horizontal",
                textfont=dict(size=11, color="#FFFFFF", family="Inter, sans-serif"),
                hovertemplate="<b>%{label}</b><extra></extra>",
            )
        )
        apply_chart_theme(fig_fuel)
        fig_fuel.update_layout(
            height=290,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            annotations=[
                dict(
                    text=f"<b>{total_f_units:,}</b><br><span style='font-size:11px;color:#64748B;'>Total Unit</span>".replace(",", "."),
                    x=0.5,
                    y=0.5,
                    font=dict(size=16, color="#0D1E38", family="Plus Jakarta Sans, sans-serif"),
                    showarrow=False,
                )
            ],
            legend=dict(
                orientation="v",
                x=1.0,
                y=0.5,
                xanchor="left",
                yanchor="middle",
                font=dict(size=11, color="#334155"),
            ),
        )
        st.plotly_chart(fig_fuel, width="stretch", config={"displayModeBar": False}, key="chart_eda_fuel")

        bensin_row = fuel_df[fuel_df["fuel"].eq("Bensin")]
        bensin_pct = float(bensin_row["pct"].iloc[0]) if not bensin_row.empty else 0.0
        eco_df = fuel_df[fuel_df["fuel"].isin(["Hybrid", "Listrik"])]
        eco_units = int(eco_df["count"].sum()) if not eco_df.empty else 0
        eco_pct = float(eco_df["pct"].sum()) if not eco_df.empty else 0.0
        bensin_med = float(bensin_row["median_price"].iloc[0]) if not bensin_row.empty else 0.0

        insight_card(
            icon="zap",
            headline=f"Insight BBM: Bensin {bensin_pct:.1f}% vs Elektrifikasi {eco_units:,} Unit".replace(",", "."),
            body=(
                f"Mesin <b>Bensin</b> masih mendominasi dengan median harga ekonomis <b>{format_rupiah_compact(bensin_med)}</b>. "
                f"Namun, unit <b>Hybrid & Listrik</b> telah menyumbang <b>{eco_units:,} iklan ({eco_pct:.1f}%)</b> "
                "bagi pembeli yang mengincar efisiensi BBM dan bebas ganjil-genap."
            ).replace(",", "."),
            variant="warning",
        )

# 5. Grafik Tahun vs Harga & Jarak Tempuh vs Harga (1 Card dengan Pemilih Variabel)
with row3_c2:
    with section_card(f"Pengaruh Usia & Jarak Tempuh terhadap Harga ({scope_label})"):
        var_choice = st.radio(
            "Pilih Variabel Pembanding:",
            ["Tahun Pembuatan vs Harga", "Jarak Tempuh (KM) vs Harga"],
            horizontal=True,
            label_visibility="collapsed",
            key="eda_scatter_var_toggle",
        )

        if "Tahun" in var_choice:
            pair_df = filtered.dropna(subset=["year", "price"]).copy()
            pair_df = pair_df[pair_df["price"].gt(0) & pair_df["year"].between(2000, 2026)]
            p95_y = float(pair_df["price"].quantile(0.95)) if not pair_df.empty else 1_000_000_000
            pair_df = pair_df[pair_df["price"].le(p95_y)]

            if not pair_df.empty:
                pair_df["price_jt"] = pair_df["price"] / 1_000_000
                trend_df = (
                    pair_df.groupby("year")["price_jt"]
                    .median()
                    .reset_index()
                    .sort_values("year")
                )
                sample_df = pair_df.sample(min(900, len(pair_df)), random_state=42)

                fig_rel = px.scatter(
                    sample_df,
                    x="year",
                    y="price_jt",
                    color_discrete_sequence=["#019F90"],
                    render_mode="svg",
                    labels={"year": "Tahun Pembuatan", "price_jt": "Harga (Juta Rp)"},
                    hover_data={"make": True, "model": True, "year": True, "price_jt": ":.0f"},
                )
                fig_rel.update_traces(marker=dict(size=5, opacity=0.45), name="Listing")
                fig_rel.add_trace(
                    go.Scatter(
                        x=trend_df["year"],
                        y=trend_df["price_jt"],
                        mode="lines+markers",
                        name="Median Harga per Tahun",
                        line=dict(color="#0D1E38", width=2.5),
                        marker=dict(size=6, color="#F59E0B"),
                        hovertemplate="Tahun %{x}<br>Median: <b>Rp %{y:.0f} Jt</b><extra></extra>",
                    )
                )
                apply_chart_theme(fig_rel)
                fig_rel.update_layout(
                    height=250,
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=10)),
                    xaxis=dict(title="Tahun Pembuatan", showgrid=True, gridcolor="#F1F5F9"),
                    yaxis=dict(title="Harga (Juta Rp)", showgrid=True, gridcolor="#F1F5F9"),
                )
                st.plotly_chart(fig_rel, width="stretch", config={"displayModeBar": False}, key="chart_eda_rel_year")

                med_new = float(pair_df[pair_df["year"].ge(2022)]["price"].median()) if pair_df["year"].ge(2022).any() else 0.0
                med_mid = float(pair_df[pair_df["year"].between(2018, 2021)]["price"].median()) if pair_df["year"].between(2018, 2021).any() else 0.0
                save_pct = ((med_new - med_mid) / med_new * 100) if med_new > 0 else 0.0

                insight_card(
                    icon="calendar",
                    headline=f"Insight Usia: Mobil Tahun 2018-2021 Lebih Hemat {save_pct:.0f}%",
                    body=(
                        f"Median harga mobil tahun 2022 ke atas mencapai <b>{format_rupiah_compact(med_new)}</b>, "
                        f"sedangkan keluaran <b>2018-2021</b> turun ke <b>{format_rupiah_compact(med_mid)}</b>. "
                        "Rentang usia 3-6 tahun ini adalah titik paling bernilai untuk menghindari depresiasi awal."
                    ),
                    variant="info",
                )
            else:
                st.caption("Data tahun dan harga tidak tersedia.")

        else:
            pair_km = filtered.dropna(subset=["mileage_km", "price"]).copy()
            pair_km = pair_km[pair_km["price"].gt(0) & pair_km["mileage_km"].between(0, 220_000)]
            p95_k = float(pair_km["price"].quantile(0.95)) if not pair_km.empty else 1_000_000_000
            pair_km = pair_km[pair_km["price"].le(p95_k)]

            if not pair_km.empty:
                pair_km["price_jt"] = pair_km["price"] / 1_000_000
                pair_km["km_rb"] = pair_km["mileage_km"] / 1_000
                pair_km["km_bin"] = (pair_km["km_rb"] // 20) * 20 + 10
                trend_km = (
                    pair_km.groupby("km_bin")["price_jt"]
                    .median()
                    .reset_index()
                    .sort_values("km_bin")
                )
                sample_km = pair_km.sample(min(900, len(pair_km)), random_state=42)

                fig_km = px.scatter(
                    sample_km,
                    x="km_rb",
                    y="price_jt",
                    color_discrete_sequence=["#00B8A9"],
                    render_mode="svg",
                    labels={"km_rb": "Jarak Tempuh (Ribu KM)", "price_jt": "Harga (Juta Rp)"},
                    hover_data={"make": True, "model": True, "km_rb": ":.0f", "price_jt": ":.0f"},
                )
                fig_km.update_traces(marker=dict(size=5, opacity=0.45), name="Listing")
                fig_km.add_trace(
                    go.Scatter(
                        x=trend_km["km_bin"],
                        y=trend_km["price_jt"],
                        mode="lines+markers",
                        name="Median Harga per 20rb KM",
                        line=dict(color="#0D1E38", width=2.5),
                        marker=dict(size=6, color="#F59E0B"),
                        hovertemplate="Odometer ~%{x:.0f} rb km<br>Median: <b>Rp %{y:.0f} Jt</b><extra></extra>",
                    )
                )
                apply_chart_theme(fig_km)
                fig_km.update_layout(
                    height=250,
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=10)),
                    xaxis=dict(title="Jarak Tempuh (Ribu KM)", showgrid=True, gridcolor="#F1F5F9"),
                    yaxis=dict(title="Harga (Juta Rp)", showgrid=True, gridcolor="#F1F5F9"),
                )
                st.plotly_chart(fig_km, width="stretch", config={"displayModeBar": False}, key="chart_eda_rel_km")

                med_km_all = float(pair_km["mileage_km"].median())
                low_km_med = float(pair_km[pair_km["mileage_km"].le(50_000)]["price"].median()) if pair_km["mileage_km"].le(50_000).any() else 0.0
                high_km_med = float(pair_km[pair_km["mileage_km"].gt(100_000)]["price"].median()) if pair_km["mileage_km"].gt(100_000).any() else 0.0

                insight_card(
                    icon="gauge",
                    headline=f"Insight Odometer: Median Pasar {format_km(med_km_all)}",
                    body=(
                        f"Mobil dengan jarak tempuh di bawah 50.000 km memiliki median harga <b>{format_rupiah_compact(low_km_med)}</b>, "
                        f"dan turun menjadi <b>{format_rupiah_compact(high_km_med)}</b> setelah melewati 100.000 km. "
                        "Incar unit di kisaran 40.000-70.000 km untuk keseimbangan harga dan kondisi mekanis."
                    ),
                    variant="success",
                )
            else:
                st.caption("Data jarak tempuh dan harga tidak tersedia.")
