"""Cek Harga Iklan — evaluasi nilai penawaran mobil bekas berbasis AI & Pembanding Pasar.

Fitur:
- 2 metode input: Pilih Listing Tersimpan vs Input Manual Spesifikasi
- Estimasi Machine Learning terintegrasi (Random Forest Regressor)
- Analisis Pembanding Sejenis (Median, P25, P75)
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
# Panduan 3 Langkah Ringkas
# ---------------------------------------------------------------------------
with st.container(border=True):
    step_cols = st.columns(3, gap="medium")
    with step_cols[0]:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.25rem;">
                <span style="background:#008B8B; color:#FFFFFF; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700;">1</span>
                <strong style="color:#0B2A5B; font-size:0.9rem;">Pilih / Masukkan Mobil</strong>
            </div>
            <div style="font-size:0.78rem; color:#475569;">Pilih dari arsip iklan OLX atau ketik spesifikasi mobil secara manual.</div>
            """,
            unsafe_allow_html=True,
        )
    with step_cols[1]:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.25rem;">
                <span style="background:#008B8B; color:#FFFFFF; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700;">2</span>
                <strong style="color:#0B2A5B; font-size:0.9rem;">Analisis Otomatis</strong>
            </div>
            <div style="font-size:0.78rem; color:#475569;">Sistem mencocokkan listing sejenis dan menghitung estimasi Machine Learning.</div>
            """,
            unsafe_allow_html=True,
        )
    with step_cols[2]:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.25rem;">
                <span style="background:#008B8B; color:#FFFFFF; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700;">3</span>
                <strong style="color:#0B2A5B; font-size:0.9rem;">Baca Status Kewajaran</strong>
            </div>
            <div style="font-size:0.78rem; color:#475569;">Ketahui posisi harga: di bawah pasar, wajar, atau kemahalan (di atas pasar).</div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)


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
        "asking_price": 165000000,
        "listing_title": "Toyota Avanza 1.3 G Manual 2020",
    }

# ---------------------------------------------------------------------------
# Dua Tab Metode Input
# ---------------------------------------------------------------------------
tab_saved, tab_manual = st.tabs(["📋 Pilih Listing Tersimpan", "✏️ Input Manual Spesifikasi"])

# 1. Pilih Listing Tersimpan
with tab_saved:
    c_search, c_make, c_yr = st.columns([2, 1.2, 1.2])
    with c_search:
        search_kw = st.text_input("Cari Kata Kunci (Model / Varian)", placeholder="Contoh: Avanza, Brio, Innova, CR-V...")
    with c_make:
        saved_make_list = ["Semua Merek"] + sorted(archive["make"].dropna().unique().tolist())
        saved_make_choice = st.selectbox("Filter Merek", saved_make_list, index=0, key="saved_make_sel")
    with c_yr:
        saved_year_min = int(archive["year"].min()) if archive["year"].notna().any() else 2000
        saved_year_max = int(archive["year"].max()) if archive["year"].notna().any() else 2026
        saved_yr_sel = st.slider("Tahun Minimal", min_value=saved_year_min, max_value=saved_year_max, value=2015, key="saved_yr_slider")

    # Filter data listing tersimpan
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

    st.caption(f"Tersedia {len(pool):,} listing yang cocok. Pilih satu mobil di bawah:")
    
    if not pool.empty:
        # Tampilkan tabel ringkas dengan selectbox
        pool_disp = pool.head(25).copy().reset_index(drop=True)
        pool_disp["option_label"] = (
            pool_disp["make"].astype(str) + " " +
            pool_disp["model"].astype(str) + " (" +
            pool_disp["year"].fillna(0).astype(int).astype(str) + ") — " +
            pool_disp["price"].map(format_rupiah) + " · " +
            pool_disp["mileage_km"].map(format_km)
        )
        
        selected_option = st.selectbox(
            "Pilih mobil untuk dianalisis:",
            pool_disp["option_label"].tolist(),
            index=0,
            key="saved_listing_choice",
        )
        
        chosen_row = pool_disp[pool_disp["option_label"].eq(selected_option)].iloc[0]
        
        if st.button("Terapkan & Analisis Listing Ini", type="primary", key="btn_apply_saved"):
            st.session_state["check_selected_features"] = {
                "make": str(chosen_row.get("make", "Toyota")),
                "model": str(chosen_row.get("model", "Avanza")),
                "year": int(chosen_row.get("year", 2020)) if pd.notna(chosen_row.get("year")) else 2020,
                "mileage_km": float(chosen_row.get("mileage_km", 40000)) if pd.notna(chosen_row.get("mileage_km")) else 40000,
                "engine_cc": float(chosen_row.get("engine_cc", 1500)) if pd.notna(chosen_row.get("engine_cc")) else 1500,
                "transmission": str(chosen_row.get("transmission", "Automatic")),
                "fuel_type": str(chosen_row.get("fuel_type", "Bensin")),
                "body_type": str(chosen_row.get("body_type", "MPV")),
                "asking_price": float(chosen_row.get("price", 150000000)),
                "listing_title": f"{chosen_row.get('make', '')} {chosen_row.get('model', '')} {chosen_row.get('variant', '')} ({int(chosen_row.get('year', 2020))})",
            }
            st.rerun()
    else:
        st.info("Tidak ada listing yang sesuai dengan kata kunci pencarian.")


# 2. Input Manual Spesifikasi
with tab_manual:
    with st.form("manual_input_form"):
        f_c1, f_c2, f_c3 = st.columns(3)
        
        with f_c1:
            all_m_makes = sorted(archive["make"].dropna().unique().tolist())
            def_make = st.session_state["check_selected_features"].get("make", "Toyota")
            make_idx = all_m_makes.index(def_make) if def_make in all_m_makes else 0
            m_make = st.selectbox("Merek", all_m_makes, index=make_idx)
            
            # Model options sesuai merek
            sub_models = sorted(archive[archive["make"].eq(m_make)]["model"].dropna().unique().tolist())
            def_model = st.session_state["check_selected_features"].get("model", "Avanza")
            model_idx = sub_models.index(def_model) if def_model in sub_models else 0
            m_model = st.selectbox("Model", sub_models if sub_models else ["Lainnya"], index=model_idx)
            
            m_year = st.number_input("Tahun Kendaraan", min_value=1990, max_value=2026, value=int(st.session_state["check_selected_features"].get("year", 2020)))

        with f_c2:
            m_km = st.number_input("Kilometer (Odometer)", min_value=0, max_value=500000, value=int(st.session_state["check_selected_features"].get("mileage_km", 45000)), step=5000)
            m_cc = st.number_input("Kapasitas Mesin (CC)", min_value=600, max_value=7000, value=int(st.session_state["check_selected_features"].get("engine_cc", 1300)), step=100)
            
            trans_opts = ["Automatic", "Manual"]
            def_trans = st.session_state["check_selected_features"].get("transmission", "Manual")
            t_idx = trans_opts.index(def_trans) if def_trans in trans_opts else 0
            m_trans = st.selectbox("Transmisi", trans_opts, index=t_idx)

        with f_c3:
            fuel_opts = ["Bensin", "Diesel", "Hybrid", "Listrik"]
            def_fuel = st.session_state["check_selected_features"].get("fuel_type", "Bensin")
            f_idx = fuel_opts.index(def_fuel) if def_fuel in fuel_opts else 0
            m_fuel = st.selectbox("Bahan Bakar", fuel_opts, index=f_idx)
            
            body_opts = ["MPV", "SUV", "Sedan", "Hatchback", "Van", "Wagon"]
            def_body = st.session_state["check_selected_features"].get("body_type", "MPV")
            b_idx = body_opts.index(def_body) if def_body in body_opts else 0
            m_body = st.selectbox("Tipe Bodi", body_opts, index=b_idx)
            
            m_price = st.number_input("Harga Iklan Penawaran (Rp)", min_value=30000000, max_value=30000000000, value=int(st.session_state["check_selected_features"].get("asking_price", 165000000)), step=5000000)

        submit_manual = st.form_submit_button("Analisis Harga Penawaran Ini", type="primary", use_container_width=True)
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

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)


# ===========================================================================
# HASIL ANALISIS KEWAJARAN HARGA
# ===========================================================================
cur_feat = st.session_state["check_selected_features"]
asking_price = float(cur_feat["asking_price"])

# 1. Estimasi Model Machine Learning
ml_estimate = None
if has_valid_model:
    try:
        ml_estimate = predict_asking_price(cur_feat)
    except Exception:
        ml_estimate = None

# 2. Pembanding Pasar Listing Sejenis
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

# 3. Hitung Selisih & Status Kewajaran
ref_price = comp_median if comp_median is not None else ml_estimate

if ref_price:
    delta_rp = asking_price - ref_price
    delta_pct = (delta_rp / ref_price) * 100
else:
    delta_rp = 0
    delta_pct = 0

# Tentukan Status
if comp_p25 is not None and comp_p75 is not None:
    if asking_price < comp_p25 and (ml_estimate is None or asking_price < ml_estimate * 0.92):
        status_label = "Di Bawah Kisaran Pasar"
        badge_style = "badge-underpriced"
        status_variant = "success"
    elif asking_price > comp_p75 and (ml_estimate is None or asking_price > ml_estimate * 1.08):
        status_label = "Di Atas Kisaran Pasar"
        badge_style = "badge-overpriced"
        status_variant = "warning"
    else:
        status_label = "Harga Wajar"
        badge_style = "badge-fair"
        status_variant = "info"
elif ml_estimate:
    if delta_pct < -8.0:
        status_label = "Di Bawah Kisaran Pasar"
        badge_style = "badge-underpriced"
        status_variant = "success"
    elif delta_pct > 8.0:
        status_label = "Di Atas Kisaran Pasar"
        badge_style = "badge-overpriced"
        status_variant = "warning"
    else:
        status_label = "Harga Wajar"
        badge_style = "badge-fair"
        status_variant = "info"
else:
    status_label = "Data Tidak Mencukupi"
    badge_style = "badge-fair"
    status_variant = "default"

# ---------------------------------------------------------------------------
# Card Hasil Evaluasi Harga
# ---------------------------------------------------------------------------
st.markdown("<div class='am-section-title'>📊 Hasil Evaluasi Kewajaran Harga</div>", unsafe_allow_html=True)

with st.container(border=True):
    res_col1, res_col2 = st.columns([1.2, 1], gap="large")
    
    with res_col1:
        st.caption("KENDARAAN YANG DIANALISIS")
        st.markdown(f"### {cur_feat.get('listing_title', 'Spesifikasi Kendaraan')}")
        
        st.caption("HARGA IKLAN PENAWARAN")
        st.markdown(f"<div style='font-size:2rem; font-weight:800; color:#0B2A5B; line-height:1.2; margin-bottom:0.75rem;'>{format_rupiah(asking_price)}</div>", unsafe_allow_html=True)

        # Estimasi Model & Selisih
        if ml_estimate:
            est_diff_rp = asking_price - ml_estimate
            est_diff_pct = (est_diff_rp / ml_estimate) * 100
            diff_sign = "+" if est_diff_rp > 0 else ""
            
            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:0.85rem 1rem;">
                    <div style="font-size:0.78rem; color:#475569; font-weight:600;">ESTIMASI MODEL MACHINE LEARNING</div>
                    <div style="font-size:1.3rem; font-weight:700; color:#008B8B; margin:0.15rem 0;">{format_rupiah(ml_estimate)}</div>
                    <div style="font-size:0.82rem; color:#475569;">
                        Selisih terhadap estimasi AI: <b>{diff_sign}{format_rupiah(est_diff_rp)} ({diff_sign}{est_diff_pct:.1f}%)</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Estimasi model Machine Learning belum tersedia untuk kombinasi fitur ini.")

    with res_col2:
        st.caption("STATUS KEWAJARAN HARGA")
        st.markdown(
            f"""
            <div style="margin: 0.35rem 0 1rem;">
                <span class="{badge_style}" style="font-size:1rem; padding:0.45rem 1.1rem;">● {status_label}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Statistik Pembanding Listing Sejenis
        if comp_median is not None:
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:0.85rem 1rem; margin-bottom:0.65rem;">
                    <div style="font-size:0.76rem; color:#64748B; font-weight:600;">MEDIAN LISTING SERUPA ({n_comps} unit)</div>
                    <div style="font-size:1.15rem; font-weight:700; color:#0F172A;">{format_rupiah(comp_median)}</div>
                    <div style="font-size:0.8rem; color:#475569; margin-top:0.2rem;">
                        Rentang Wajar (P25–P75): <b>{format_rupiah_compact(comp_p25)} – {format_rupiah_compact(comp_p75)}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("Belum ada listing serupa yang memenuhi rentang toleransi tahun & spesifikasi.")

    # Penjelasan Otomatis
    st.markdown("<hr style='margin:0.8rem 0; border-color:#F1F5F9;'>", unsafe_allow_html=True)
    
    if status_label == "Harga Wajar":
        explanation_text = (
            f"Harga iklan **{format_rupiah(asking_price)}** berada di dalam rentang wajar pasar Jakarta. "
            f"Selisih harga ({delta_pct:+.1f}%) konsisten dengan pola penawaran {n_comps} mobil sejenis "
            f"di rentang P25–P75 ({format_rupiah_compact(comp_p25 or 0)} – {format_rupiah_compact(comp_p75 or 0)})."
        )
    elif status_label == "Di Bawah Kisaran Pasar":
        explanation_text = (
            f"Harga iklan **{format_rupiah(asking_price)}** berada **di bawah rata-rata pasar** ({delta_pct:+.1f}% vs referensi). "
            f"Ini merupakan penawaran menarik (*good deal*), namun pembeli disarankan memeriksa kelengkapan surat-surat, "
            f"riwayat servis, serta potensi biaya perbaikan fisik sebelum transaksi."
        )
    else:
        explanation_text = (
            f"Harga iklan **{format_rupiah(asking_price)}** berada **di atas rata-rata pasar** ({delta_pct:+.1f}% vs referensi). "
            f"Penawaran ini tergolong premium, kecuali unit memiliki modifikasi bernilai tinggi, kilometer sangat rendah, "
            f"atau catatan perawatan istimewa dari diler resmi."
        )

    st.markdown(
        f"""
        <div style="display:flex; align-items:flex-start; gap:0.65rem;">
            <span style="font-size:1.2rem; line-height:1;">💡</span>
            <div style="font-size:0.84rem; color:#334155; line-height:1.5;">{explanation_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Tabel Sampel Listing Pembanding (Expandable)
# ---------------------------------------------------------------------------
if not comparables.empty:
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
