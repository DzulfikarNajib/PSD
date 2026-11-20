"""Cek Harga Iklan - evaluasi nilai penawaran mobil bekas berbasis AI & Pembanding Pasar.

Fitur:
- Layout 2-Kolom Split Screen (Input di kiri, Hasil & Visualisasi di kanan)
- Estimasi Machine Learning terintegrasi (Random Forest Regressor)
- Analisis Pembanding Sejenis (Median, P25, P75)
- Barometer Deviasi Posisi Harga (pengganti gauge kesesuaian)
- Status Kewajaran Harga (Di Bawah Pasar, Wajar, Di Atas Pasar)
- Penjelasan hasil berbasis data
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
from src.modeling import (
    load_model_metadata,
    model_is_validated,
    predict_asking_price,
)
from src.styles import apply_theme
from src.ui import format_km, format_rupiah, format_rupiah_compact
from src.ui_components import (
    insight_card,
    kpi_card,
    page_header,
    price_deviation_barometer,
    section_card,
    status_badge,
)

apply_theme()

page_header(
    icon="🔍",
    title="Cek Harga Iklan",
    subtitle="Analisis kewajaran harga penawaran mobil bekas di DKI Jakarta berdasarkan perbandingan pasar dan model Machine Learning.",
)

archive = load_combined_archive()

if archive.empty:
    st.warning("Data arsip tidak dapat dimuat.", icon=":material/warning:")
    st.stop()

# Konversi tipe kolom
for col in ("price", "year", "mileage_km", "engine_cc"):
    if col in archive:
        archive[col] = pd.to_numeric(archive[col], errors="coerce")

metadata = load_model_metadata()
has_valid_model = model_is_validated(metadata)


# ---------------------------------------------------------------------------
# Fungsi Pencocokan Listing Sejenis (Comparables Finder)
# ---------------------------------------------------------------------------
def find_comparables(data: pd.DataFrame, features: dict) -> pd.DataFrame:
    if data.empty:
        return data.copy()
    rows = data.copy()

    make_match = str(features.get("make", "")).strip().casefold()
    model_match = str(features.get("model", "")).strip().casefold()

    peers = rows[
        rows["make"].fillna("").astype(str).str.casefold().eq(make_match)
        & rows["model"].fillna("").astype(str).str.casefold().eq(model_match)
    ].copy()

    target_year = features.get("year", 2020)
    if target_year:
        peers = peers[peers["year"].between(target_year - 2, target_year + 2)]

    target_km = features.get("mileage_km", 0)
    if target_km and target_km > 0 and "mileage_km" in peers:
        km_win = max(20_000, target_km * 0.4)
        peers = peers[peers["mileage_km"].between(max(0, target_km - km_win), target_km + km_win) | peers["mileage_km"].isna()]

    target_cc = features.get("engine_cc", 0)
    if target_cc and target_cc > 0 and "engine_cc" in peers:
        peers = peers[peers["engine_cc"].between(target_cc * 0.7, target_cc * 1.3) | peers["engine_cc"].isna()]

    for cat_col in ("transmission", "fuel_type"):
        cat_val = features.get(cat_col, "Semua")
        if cat_val and cat_val != "Semua" and cat_col in peers:
            peers = peers[peers[cat_col].fillna("").astype(str).eq(cat_val)]

    return peers.dropna(subset=["price"]).reset_index(drop=True)


# Inisialisasi session state untuk form input
if "check_selected_features" not in st.session_state:
    st.session_state["check_selected_features"] = {
        "make": "Toyota",
        "model": "Avanza",
        "year": 2020,
        "mileage_km": 45000,
        "engine_cc": 1300,
        "transmission": "Manual",
        "fuel_type": "Bensin",
        "body_type": "MPV",
        "asking_price": 180000000,
        "listing_title": "Toyota Avanza 1.3 G Manual 2020",
    }


# ===========================================================================
# LAYOUT 2-KOLOM SPLIT SCREEN (MASTER REFERENCE DESIGN)
# ===========================================================================
col_input, col_result = st.columns([1, 1.45], gap="medium")

# ---------------------------------------------------------------------------
# KOLOM KIRI: Form Input / Pemilih Listing
# ---------------------------------------------------------------------------
with col_input:
    with section_card("Pilih Listing / Spesifikasi"):
        input_mode = st.radio(
            "Metode Input",
            ["Pilih Listing Tersimpan", "Input Manual"],
            horizontal=True,
            label_visibility="collapsed",
            key="cek_input_mode",
        )

        if input_mode == "Pilih Listing Tersimpan":
            search_kw = st.text_input(
                "Cari Listing (Model / Varian)",
                placeholder="Contoh: Avanza, Brio, Innova...",
                key="cek_search_kw",
            )
            c_make, c_yr = st.columns(2)
            with c_make:
                saved_make_list = ["Semua Merek"] + sorted(archive["make"].dropna().unique().tolist())
                saved_make_choice = st.selectbox("Merek", saved_make_list, index=0, key="cek_make_sel")
            with c_yr:
                saved_year_min = int(archive["year"].min()) if archive["year"].notna().any() else 2000
                saved_year_max = int(archive["year"].max()) if archive["year"].notna().any() else 2026
                saved_yr_sel = st.slider("Tahun Min", min_value=saved_year_min, max_value=saved_year_max, value=2015, key="cek_yr_sel")

            pool = archive.dropna(subset=["price"]).copy()
            pool = pool[pool["year"].ge(saved_yr_sel)]
            if saved_make_choice != "Semua Merek":
                pool = pool[pool["make"].eq(saved_make_choice)]
            if search_kw.strip():
                kw = search_kw.strip().casefold()
                pool = pool[
                    pool["model"].fillna("").astype(str).str.casefold().str.contains(kw)
                    | pool["variant"].fillna("").astype(str).str.casefold().str.contains(kw)
                ]

            st.caption(f"Tersedia **{len(pool):,}** listing cocok.")

            if not pool.empty:
                pool_disp = pool.head(30).copy().reset_index(drop=True)
                pool_disp["option_label"] = (
                    pool_disp["make"].astype(str) + " " +
                    pool_disp["model"].astype(str) + " (" +
                    pool_disp["year"].fillna(0).astype(int).astype(str) + ") - " +
                    pool_disp["price"].map(format_rupiah_compact) + " · " +
                    pool_disp["mileage_km"].map(format_km)
                )

                selected_option = st.selectbox(
                    "Pilih mobil dari arsip:",
                    pool_disp["option_label"].tolist(),
                    index=0,
                    key="cek_saved_choice",
                )

                chosen_row = pool_disp[pool_disp["option_label"].eq(selected_option)].iloc[0]

                if st.button("Analisis Listing Ini", type="primary", use_container_width=True, key="btn_apply_saved"):
                    st.session_state["check_selected_features"] = {
                        "make": str(chosen_row.get("make", "Toyota")),
                        "model": str(chosen_row.get("model", "Avanza")),
                        "year": int(chosen_row.get("year", 2020)) if pd.notna(chosen_row.get("year")) else 2020,
                        "mileage_km": float(chosen_row.get("mileage_km", 40000)) if pd.notna(chosen_row.get("mileage_km")) else 40000,
                        "engine_cc": float(chosen_row.get("engine_cc", 1500)) if pd.notna(chosen_row.get("engine_cc")) else 1500,
                        "transmission": str(chosen_row.get("transmission", "Automatic")),
                        "fuel_type": str(chosen_row.get("fuel_type", "Bensin")),
                        "body_type": str(chosen_row.get("body_type", "MPV")),
                        "asking_price": float(chosen_row.get("price", 180000000)),
                        "listing_title": f"{chosen_row.get('make', '')} {chosen_row.get('model', '')} ({int(chosen_row.get('year', 2020))})",
                    }
                    st.rerun()
            else:
                st.info("Tidak ada listing yang sesuai kata kunci.")

        else:
            # Input Manual Form
            with st.form("manual_check_form"):
                m_c1, m_c2 = st.columns(2)
                with m_c1:
                    all_m_makes = sorted(archive["make"].dropna().unique().tolist())
                    def_make = st.session_state["check_selected_features"].get("make", "Toyota")
                    make_idx = all_m_makes.index(def_make) if def_make in all_m_makes else 0
                    m_make = st.selectbox("Merek", all_m_makes, index=make_idx)

                    sub_models = sorted(archive[archive["make"].eq(m_make)]["model"].dropna().unique().tolist())
                    def_model = st.session_state["check_selected_features"].get("model", "Avanza")
                    model_idx = sub_models.index(def_model) if def_model in sub_models else 0
                    m_model = st.selectbox("Model", sub_models if sub_models else ["Lainnya"], index=model_idx)

                    m_year = st.number_input(
                        "Tahun",
                        min_value=1990,
                        max_value=2026,
                        value=int(st.session_state["check_selected_features"].get("year", 2020)),
                    )
                    m_km = st.number_input(
                        "Kilometer",
                        min_value=0,
                        max_value=500000,
                        value=int(st.session_state["check_selected_features"].get("mileage_km", 45000)),
                        step=5000,
                    )

                with m_c2:
                    m_cc = st.number_input(
                        "Mesin (CC)",
                        min_value=600,
                        max_value=7000,
                        value=int(st.session_state["check_selected_features"].get("engine_cc", 1300)),
                        step=100,
                    )
                    trans_opts = ["Automatic", "Manual"]
                    def_trans = st.session_state["check_selected_features"].get("transmission", "Manual")
                    t_idx = trans_opts.index(def_trans) if def_trans in trans_opts else 0
                    m_trans = st.selectbox("Transmisi", trans_opts, index=t_idx)

                    fuel_opts = ["Bensin", "Diesel", "Hybrid", "Listrik"]
                    def_fuel = st.session_state["check_selected_features"].get("fuel_type", "Bensin")
                    f_idx = fuel_opts.index(def_fuel) if def_fuel in fuel_opts else 0
                    m_fuel = st.selectbox("Bahan Bakar", fuel_opts, index=f_idx)

                    body_opts = ["MPV", "SUV", "Sedan", "Hatchback", "Van", "Wagon"]
                    def_body = st.session_state["check_selected_features"].get("body_type", "MPV")
                    b_idx = body_opts.index(def_body) if def_body in body_opts else 0
                    m_body = st.selectbox("Tipe Bodi", body_opts, index=b_idx)

                m_price = st.number_input(
                    "Harga Iklan Penawaran (Rp)",
                    min_value=30000000,
                    max_value=30000000000,
                    value=int(st.session_state["check_selected_features"].get("asking_price", 180000000)),
                    step=5000000,
                )

                submit_manual = st.form_submit_button("Analisis Harga Penawaran", type="primary", use_container_width=True)
                if submit_manual:
                    st.session_state["check_selected_features"] = {
                        "make": m_make,
                        "model": m_model,
                        "year": m_year,
                        "mileage_km": m_km,
                        "engine_cc": m_cc,
                        "transmission": m_trans,
                        "fuel_type": m_fuel,
                        "body_type": m_body,
                        "asking_price": m_price,
                        "listing_title": f"{m_make} {m_model} {m_trans} ({m_year})",
                    }
                    st.rerun()


# ---------------------------------------------------------------------------
# KOLOM KANAN: Hasil Evaluasi & Visualisasi
# ---------------------------------------------------------------------------
cur_feat = st.session_state["check_selected_features"]
asking_price = float(cur_feat["asking_price"])

# Estimasi Model Machine Learning
ml_estimate = None
if has_valid_model:
    try:
        ml_estimate = predict_asking_price(cur_feat)
    except Exception:
        ml_estimate = None

# Pembanding Pasar Listing Sejenis
comparables = find_comparables(archive, cur_feat)
n_comps = len(comparables)

if not comparables.empty:
    comp_median = float(comparables["price"].median())
    comp_p25 = float(comparables["price"].quantile(0.25))
    comp_p75 = float(comparables["price"].quantile(0.75))
else:
    comp_median = None
    comp_p25 = None
    comp_p75 = None

# Hitung Selisih & Status
ref_price = comp_median if comp_median is not None else ml_estimate

if ref_price:
    delta_rp = asking_price - ref_price
    delta_pct = (delta_rp / ref_price) * 100
else:
    delta_rp = 0
    delta_pct = 0

# Tentukan Status Kewajaran
if comp_p25 is not None and comp_p75 is not None:
    if asking_price < comp_p25 and (ml_estimate is None or asking_price < ml_estimate * 0.92):
        status_label = "Di Bawah Kisaran Pasar"
        badge_style = "badge-underpriced"
    elif asking_price > comp_p75 and (ml_estimate is None or asking_price > ml_estimate * 1.08):
        status_label = "Di Atas Kisaran Pasar"
        badge_style = "badge-overpriced"
    else:
        status_label = "Harga Wajar"
        badge_style = "badge-fair"
elif ml_estimate:
    if delta_pct < -8.0:
        status_label = "Di Bawah Kisaran Pasar"
        badge_style = "badge-underpriced"
    elif delta_pct > 8.0:
        status_label = "Di Atas Kisaran Pasar"
        badge_style = "badge-overpriced"
    else:
        status_label = "Harga Wajar"
        badge_style = "badge-fair"
else:
    status_label = "Data Tidak Mencukupi"
    badge_style = "badge-fair"

with col_result:
    with section_card("Hasil Analisis Kewajaran Harga"):
        # Header Hasil: Judul Kendaraan, Harga Iklan, dan Badge Status
        h_left, h_right = st.columns([1.3, 1], vertical_alignment="center")
        with h_left:
            st.caption("KENDARAAN YANG DIANALISIS")
            st.markdown(f"#### {cur_feat.get('listing_title', 'Spesifikasi Kendaraan')}")
            st.markdown(
                f"<div style='font-size:1.8rem; font-weight:800; color:#0B2A5B; line-height:1.1; margin-top:0.2rem;'>"
                f"{format_rupiah(asking_price)}</div>",
                unsafe_allow_html=True,
            )
        with h_right:
            st.markdown(
                f"""
                <div style="text-align:right;">
                    <span class="{badge_style}" style="font-size:0.92rem; padding:0.4rem 1rem;">● {status_label}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='margin:0.75rem 0; border-color:#F1F5F9;'>", unsafe_allow_html=True)

        # Dua Kolom: Kiri Metrik Pilar, Kanan Barometer Deviasi
        res_sub1, res_sub2 = st.columns([1.1, 1], gap="medium")

        with res_sub1:
            # 1. Estimasi Model AI
            if ml_estimate:
                est_diff_rp = asking_price - ml_estimate
                est_diff_pct = (est_diff_rp / ml_estimate) * 100
                diff_sign = "+" if est_diff_rp > 0 else ""
                st.markdown(
                    f"""
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:0.65rem 0.85rem; margin-bottom:0.55rem;">
                        <div style="font-size:0.72rem; color:#475569; font-weight:600; text-transform:uppercase;">Estimasi Model Machine Learning</div>
                        <div style="font-size:1.15rem; font-weight:800; color:#008B8B; margin:0.1rem 0;">{format_rupiah(ml_estimate)}</div>
                        <div style="font-size:0.76rem; color:#475569;">
                            Selisih AI: <b>{diff_sign}{format_rupiah(est_diff_rp)} ({diff_sign}{est_diff_pct:.1f}%)</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # 2. Median Pembanding Serupa
            if comp_median is not None:
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:0.65rem 0.85rem;">
                        <div style="font-size:0.72rem; color:#64748B; font-weight:600; text-transform:uppercase;">Median Listing Serupa ({n_comps} unit)</div>
                        <div style="font-size:1.15rem; font-weight:800; color:#0F172A; margin:0.1rem 0;">{format_rupiah(comp_median)}</div>
                        <div style="font-size:0.76rem; color:#475569;">
                            Rentang P25-P75: <b>{format_rupiah_compact(comp_p25)} - {format_rupiah_compact(comp_p75)}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Belum ada listing pembanding serupa di pasar.")

        with res_sub2:
            # Barometer Gauge
            fig_barometer = price_deviation_barometer(
                asking_price=asking_price,
                median_price=comp_median if comp_median else (ml_estimate or asking_price),
                p25=comp_p25,
                p75=comp_p75,
            )
            st.plotly_chart(fig_barometer, width="stretch", config={"displayModeBar": False}, key="chart_cek_gauge")

        # Penjelasan Hasil Otomatis
        st.markdown("<hr style='margin:0.65rem 0; border-color:#F1F5F9;'>", unsafe_allow_html=True)
        if status_label == "Harga Wajar":
            explanation_text = (
                f"Harga iklan <b>{format_rupiah(asking_price)}</b> berada di dalam rentang wajar pasar Jakarta. "
                f"Selisih harga ({delta_pct:+.1f}%) konsisten dengan pola penawaran {n_comps} mobil sejenis "
                f"di rentang P25-P75 ({format_rupiah_compact(comp_p25 or 0)} s/d {format_rupiah_compact(comp_p75 or 0)})."
            )
        elif status_label == "Di Bawah Kisaran Pasar":
            explanation_text = (
                f"Harga iklan <b>{format_rupiah(asking_price)}</b> berada <b>di bawah rata-rata pasar</b> ({delta_pct:+.1f}% vs referensi). "
                f"Ini merupakan penawaran menarik (good deal), namun pembeli disarankan memeriksa kelengkapan dokumen "
                f"dan riwayat servis berkala sebelum transaksi."
            )
        else:
            explanation_text = (
                f"Harga iklan <b>{format_rupiah(asking_price)}</b> berada <b>di atas rata-rata pasar</b> ({delta_pct:+.1f}% vs referensi). "
                f"Penawaran ini tergolong premium, kecuali unit memiliki modifikasi bernilai tinggi atau kondisi istimewa."
            )

        st.markdown(
            f"""
            <div style="display:flex; align-items:flex-start; gap:0.5rem; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:0.65rem 0.85rem;">
                <span style="font-size:1.1rem; line-height:1;">ℹ️</span>
                <div style="font-size:0.8rem; color:#334155; line-height:1.45;">{explanation_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Tabel Sampel Listing Pembanding Serupa (Bawah)
# ---------------------------------------------------------------------------
if not comparables.empty:
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    with st.expander(f"Lihat {n_comps} Listing Pembanding Serupa di Pasar Jakarta", expanded=False):
        c_show = comparables.head(10)[[
            "make", "model", "variant", "year", "price", "mileage_km", "transmission", "location_normalized"
        ]].copy()

        c_show["price"] = c_show["price"].map(format_rupiah)
        c_show["mileage_km"] = c_show["mileage_km"].map(format_km)
        c_show["year"] = c_show["year"].map(lambda x: f"{x:.0f}" if pd.notna(x) else "-")
        c_show["location_normalized"] = c_show["location_normalized"].str.title()

        c_show = c_show.rename(columns={
            "make": "Merek",
            "model": "Model",
            "variant": "Varian",
            "year": "Tahun",
            "price": "Harga Iklan",
            "mileage_km": "Kilometer",
            "transmission": "Transmisi",
            "location_normalized": "Wilayah",
        })
        st.dataframe(c_show, hide_index=True, width="stretch")
