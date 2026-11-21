"""Cek Mobil dan Harga - pencarian mobil bekas sesuai budget sekaligus evaluasi kewajaran harga AI.

Fitur:
- Filter terintegrasi dari Peta Wilayah & Top Merek (prefill otomatis)
- Pencarian mobil sesuai rentang budget, wilayah DKI, merek, tipe bodi, dan kata kunci
- Kartu Detail Iklan Lengkap: Foto mobil dari OLX (dengan fallback aman), Spesifikasi Utama & Detail,
  serta Tombol Tautan Langsung ke Iklan OLX
- Estimasi Machine Learning (Random Forest Regressor), Median Pasar Sejenis (P25-P75),
  dan Barometer Deviasi Posisi Harga
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

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
    get_lucide_icon,
    page_header,
    price_deviation_barometer,
    section_card,
)

apply_theme()

page_header(
    icon="search",
    title="Cek Mobil dan Harga",
    subtitle="Cari mobil bekas sesuai budget dan wilayah Anda, lihat foto serta spesifikasi iklan lengkap dengan tautan langsung ke OLX, sekaligus uji kewajaran harganya.",
)

archive = load_combined_archive()

if archive.empty:
    st.warning("Data arsip tidak dapat dimuat.", icon=":material/warning:")
    st.stop()

# Konversi tipe kolom
for col in ("price", "year", "mileage_km", "engine_cc"):
    if col in archive:
        archive[col] = pd.to_numeric(archive[col], errors="coerce")

archive["location_display"] = archive["location_normalized"].fillna("").astype(str).str.title()
dki_5 = ["Jakarta Selatan", "Jakarta Utara", "Jakarta Pusat", "Jakarta Barat", "Jakarta Timur"]
archive = archive[archive["location_display"].isin(dki_5)].copy()

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
        peers = peers[
            peers["mileage_km"].between(max(0, target_km - km_win), target_km + km_win)
            | peers["mileage_km"].isna()
        ]

    target_cc = features.get("engine_cc", 0)
    if target_cc and target_cc > 0 and "engine_cc" in peers:
        peers = peers[
            peers["engine_cc"].between(target_cc * 0.7, target_cc * 1.3)
            | peers["engine_cc"].isna()
        ]

    for cat_col in ("transmission", "fuel_type"):
        cat_val = features.get(cat_col, "Semua")
        if cat_val and cat_val != "Semua" and cat_col in peers:
            peers = peers[peers[cat_col].fillna("").astype(str).eq(cat_val)]

    return peers.dropna(subset=["price"]).reset_index(drop=True)


def _row_to_feature_dict(row: pd.Series) -> dict:
    yr_val = int(row.get("year", 2020)) if pd.notna(row.get("year")) else 2020
    mk_str = str(row.get("make", "Toyota")).strip()
    md_str = str(row.get("model", "Avanza")).strip()
    var_str = str(row.get("variant", "")).strip() if pd.notna(row.get("variant")) else ""
    title_parts = [p for p in (mk_str, md_str, var_str) if p]
    full_title = " ".join(title_parts) + f" ({yr_val})"
    return {
        "listing_id": str(row.get("listing_id", "-")),
        "make": mk_str,
        "model": md_str,
        "variant": var_str if var_str else "-",
        "year": yr_val,
        "mileage_km": float(row.get("mileage_km", 40000)) if pd.notna(row.get("mileage_km")) else 40000.0,
        "mileage_range": str(row.get("mileage_range", "")).strip() or "-",
        "engine_cc": float(row.get("engine_cc", 1500)) if pd.notna(row.get("engine_cc")) else 1500.0,
        "transmission": str(row.get("transmission", "Automatic")) if pd.notna(row.get("transmission")) else "Automatic",
        "fuel_type": str(row.get("fuel_type", "Bensin")) if pd.notna(row.get("fuel_type")) else "Bensin",
        "body_type": str(row.get("body_type", "MPV")) if pd.notna(row.get("body_type")) and str(row.get("body_type")).strip() else "MPV",
        "color": str(row.get("color", "-")) if pd.notna(row.get("color")) and str(row.get("color")).strip() else "-",
        "location": str(row.get("location_display", "-")) if pd.notna(row.get("location_display")) else "-",
        "seller_type": str(row.get("seller_type", "Diler / Individu")) if pd.notna(row.get("seller_type")) and str(row.get("seller_type")).strip() else "Penjual Terverifikasi",
        "posted_at": str(row.get("posted_at", "-"))[:10] if pd.notna(row.get("posted_at")) else "-",
        "image_url": str(row.get("image_url", "")).strip() if pd.notna(row.get("image_url")) else "",
        "url": str(row.get("url", "")).strip() if pd.notna(row.get("url")) else "",
        "asking_price": float(row.get("price", 180000000)),
        "listing_title": full_title,
        "is_archive_listing": True,
    }


# Tangkap prefill dari halaman Eksplorasi Data (klik Peta atau klik Top Merek)
if "prefill_cek_region" in st.session_state:
    st.session_state["cek_region_sel"] = st.session_state.pop("prefill_cek_region")
    st.session_state["cek_input_mode"] = "Cari Mobil Sesuai Budget"

if "prefill_cek_make" in st.session_state:
    st.session_state["cek_make_sel"] = st.session_state.pop("prefill_cek_make")
    st.session_state["cek_budget_slider"] = (30, 1500)
    st.session_state["cek_input_mode"] = "Cari Mobil Sesuai Budget"

# Inisialisasi default dari baris nyata pertama di archive
if "check_selected_features" not in st.session_state:
    first_valid = archive.dropna(subset=["price", "image_url", "url"])
    if not first_valid.empty:
        st.session_state["check_selected_features"] = _row_to_feature_dict(first_valid.iloc[0])
    else:
        st.session_state["check_selected_features"] = _row_to_feature_dict(archive.iloc[0])


# ===========================================================================
# LAYOUT 2-KOLOM SPLIT SCREEN
# ===========================================================================
col_input, col_result = st.columns([1, 1.48], gap="medium")

# ---------------------------------------------------------------------------
# KOLOM KIRI: Filter Pencarian Mobil Sesuai Budget / Input Manual
# ---------------------------------------------------------------------------
with col_input:
    with section_card("Cari Mobil & Pilih Spesifikasi"):
        input_mode = st.radio(
            "Metode Input",
            ["Cari Mobil Sesuai Budget", "Input Spesifikasi Manual"],
            horizontal=True,
            label_visibility="collapsed",
            key="cek_input_mode",
        )

        if input_mode == "Cari Mobil Sesuai Budget":
            # 1. Filter Rentang Anggaran (Budget Range Slider)
            budget_sel = st.slider(
                "Rentang Budget (Juta Rp)",
                min_value=30,
                max_value=2000,
                value=st.session_state.get("cek_budget_slider", (80, 450)),
                step=10,
                key="cek_budget_slider",
            )
            b_min, b_max = budget_sel[0] * 1_000_000, budget_sel[1] * 1_000_000

            # 2. Filter Wilayah DKI Jakarta & Merek
            c_reg, c_make = st.columns(2)
            with c_reg:
                reg_list = ["Semua Wilayah"] + dki_5
                cur_reg = st.session_state.get("cek_region_sel", "Semua Wilayah")
                reg_idx = reg_list.index(cur_reg) if cur_reg in reg_list else 0
                saved_reg_choice = st.selectbox("Wilayah DKI", reg_list, index=reg_idx, key="cek_region_sel")

            with c_make:
                saved_make_list = ["Semua Merek"] + sorted(archive["make"].dropna().unique().tolist())
                cur_mk = st.session_state.get("cek_make_sel", "Semua Merek")
                mk_idx = saved_make_list.index(cur_mk) if cur_mk in saved_make_list else 0
                saved_make_choice = st.selectbox("Merek", saved_make_list, index=mk_idx, key="cek_make_sel")

            # 3. Filter Tipe Bodi & Kata Kunci Model
            c_body, c_kw = st.columns([1, 1.15])
            with c_body:
                body_types_avail = ["Semua Bodi"] + sorted(
                    [b for b in archive["body_type"].dropna().unique().tolist() if str(b).strip()]
                )
                saved_body_choice = st.selectbox("Tipe Bodi", body_types_avail, index=0, key="cek_body_sel")
            with c_kw:
                search_kw = st.text_input(
                    "Model / Varian",
                    placeholder="Contoh: Avanza, Brio...",
                    key="cek_search_kw",
                )

            # Saring data sesuai kriteria budget, wilayah & spek
            pool = archive.dropna(subset=["price"]).copy()
            pool = pool[pool["price"].between(b_min, b_max)]
            if saved_reg_choice != "Semua Wilayah":
                pool = pool[pool["location_display"].eq(saved_reg_choice)]
            if saved_make_choice != "Semua Merek":
                pool = pool[pool["make"].eq(saved_make_choice)]
            if saved_body_choice != "Semua Bodi":
                pool = pool[pool["body_type"].eq(saved_body_choice)]
            if search_kw.strip():
                kw = search_kw.strip().casefold()
                pool = pool[
                    pool["model"].fillna("").astype(str).str.casefold().str.contains(kw)
                    | pool["variant"].fillna("").astype(str).str.casefold().str.contains(kw)
                ]

            st.caption(
                f"Ditemukan **{len(pool):,}** iklan mobil di **{saved_reg_choice}** "
                f"(Budget Rp {budget_sel[0]} - {budget_sel[1]} Jt).".replace(",", ".")
            )

            if not pool.empty:
                pool_disp = pool.head(35).copy().reset_index(drop=True)
                pool_disp["option_label"] = (
                    pool_disp["make"].astype(str)
                    + " "
                    + pool_disp["model"].astype(str)
                    + " ("
                    + pool_disp["year"].fillna(0).astype(int).astype(str)
                    + ") - "
                    + pool_disp["price"].map(format_rupiah_compact)
                    + " · "
                    + pool_disp["location_display"].astype(str)
                )

                selected_option = st.selectbox(
                    "Pilih mobil dari daftar hasil pencarian:",
                    pool_disp["option_label"].tolist(),
                    index=0,
                    key="cek_saved_choice",
                )

                chosen_row = pool_disp[pool_disp["option_label"].eq(selected_option)].iloc[0]
                chosen_feat = _row_to_feature_dict(chosen_row)

                # Sinkronkan langsung pilihan dropdown agar foto, spesifikasi, link OLX & barometer di kanan otomatis tampil
                if st.session_state["check_selected_features"].get("listing_id") != chosen_feat["listing_id"]:
                    st.session_state["check_selected_features"] = chosen_feat

                item_price = float(chosen_row.get("price", 0))
                item_make = chosen_row.get("make", "")
                item_model = chosen_row.get("model", "")
                peers_sample = archive[
                    archive["make"].fillna("").str.casefold().eq(str(item_make).casefold())
                    & archive["model"].fillna("").str.casefold().eq(str(item_model).casefold())
                ]
                peers_med = float(peers_sample["price"].median()) if not peers_sample.empty else item_price
                quick_diff = ((item_price - peers_med) / peers_med) * 100 if peers_med > 0 else 0.0

                if abs(quick_diff) <= 8.0:
                    q_badge = '<span style="background:#E6F7F5;color:#019F90;font-weight:700;font-size:0.75rem;padding:0.2rem 0.6rem;border-radius:999px;">● Harga Wajar</span>'
                elif quick_diff < -8.0:
                    q_badge = '<span style="background:#ECFDF5;color:#047857;font-weight:700;font-size:0.75rem;padding:0.2rem 0.6rem;border-radius:999px;">● Good Deal (-{:.1f}%)</span>'.format(abs(quick_diff))
                else:
                    q_badge = '<span style="background:#FEF3C7;color:#B45309;font-weight:700;font-size:0.75rem;padding:0.2rem 0.6rem;border-radius:999px;">● Di Atas Pasar (+{:.1f}%)</span>'.format(quick_diff)

                st.markdown(
                    f"""
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:0.7rem 0.85rem; margin:0.35rem 0;">
                        <div style="display:flex; justify-content:space-between; align-items:center; gap:0.4rem;">
                            <div style="font-size:0.82rem; font-weight:700; color:#0D1E38;">{chosen_feat['listing_title']}</div>
                            <div>{q_badge}</div>
                        </div>
                        <div style="font-size:0.75rem; color:#475569; margin-top:0.25rem;">
                            Harga: <b>{format_rupiah(item_price)}</b> · KM: <b>{format_km(chosen_feat['mileage_km'])}</b> · Lokasi: <b>{chosen_feat['location']}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("Tidak ada listing yang sesuai budget dan filter Anda. Coba perluas rentang budget atau pilih 'Semua Wilayah'.")

        else:
            # Input Manual Form (untuk simulasi mobil di luar daftar)
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
                        "listing_id": "Simulasi Manual",
                        "make": m_make,
                        "model": m_model,
                        "variant": "-",
                        "year": m_year,
                        "mileage_km": m_km,
                        "mileage_range": format_km(m_km),
                        "engine_cc": m_cc,
                        "transmission": m_trans,
                        "fuel_type": m_fuel,
                        "body_type": m_body,
                        "color": "-",
                        "location": "DKI Jakarta",
                        "seller_type": "Simulasi Pengguna",
                        "posted_at": "-",
                        "image_url": "",
                        "url": "",
                        "asking_price": m_price,
                        "listing_title": f"{m_make} {m_model} {m_trans} ({m_year})",
                        "is_archive_listing": False,
                    }
                    st.rerun()


# ---------------------------------------------------------------------------
# KOLOM KANAN: Foto Iklan, Spesifikasi Detail, Link OLX & Barometer Harga AI
# ---------------------------------------------------------------------------
cur_feat = st.session_state["check_selected_features"]
asking_price = float(cur_feat["asking_price"])

ml_estimate = None
if has_valid_model:
    try:
        ml_estimate = predict_asking_price(cur_feat)
    except Exception:
        ml_estimate = None

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

ref_price = comp_median if comp_median is not None else ml_estimate

if ref_price:
    delta_rp = asking_price - ref_price
    delta_pct = (delta_rp / ref_price) * 100
else:
    delta_rp = 0.0
    delta_pct = 0.0

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
    with section_card("Detail Iklan Mobil & Analisis Kewajaran Harga"):
        # 1. Header Judul, Harga & Badge Kewajaran
        h_left, h_right = st.columns([1.35, 1], vertical_alignment="center")
        with h_left:
            st.caption("KENDARAAN YANG DIANALISIS")
            st.markdown(f"#### {cur_feat.get('listing_title', 'Spesifikasi Kendaraan')}")
            st.markdown(
                f"<div style='font-size:1.85rem; font-weight:800; color:#0D1E38; line-height:1.1; margin-top:0.15rem;'>"
                f"{format_rupiah(asking_price)}</div>",
                unsafe_allow_html=True,
            )
        with h_right:
            st.markdown(
                f"""
                <div style="text-align:right;">
                    <span class="{badge_style}" style="font-size:0.9rem; padding:0.4rem 1rem;">● {status_label}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='margin:0.75rem 0; border-color:#F1F5F9;'>", unsafe_allow_html=True)

        # 2. Foto Iklan Mobil + Spesifikasi Utama & Detail + Tombol Link OLX
        img_col, spec_col = st.columns([1, 1.25], gap="medium")

        with img_col:
            img_url = str(cur_feat.get("image_url", "")).strip()
            olx_url = str(cur_feat.get("url", "")).strip()
            safe_title = html.escape(str(cur_feat.get("listing_title", "Mobil Bekas")))

            if img_url and img_url.startswith("http"):
                st.markdown(
                    f"""
                    <div style="position:relative; width:100%; height:205px; border-radius:12px; overflow:hidden; border:1px solid #E2E8F0; background:#F1F5F9; display:flex; align-items:center; justify-content:center;">
                        <img src="{html.escape(img_url)}" alt="{safe_title}"
                             style="width:100%; height:100%; object-fit:cover; display:block;"
                             onerror="this.style.display='none'; this.parentElement.querySelector('.am-img-fallback').style.display='flex';" />
                        <div class="am-img-fallback" style="display:none; flex-direction:column; align-items:center; justify-content:center; padding:1rem; text-align:center; color:#64748B; font-size:0.78rem;">
                            {get_lucide_icon('car', size=36, color='#019F90')}
                            <span style="margin-top:0.4rem; font-weight:600; color:#0D1E38;">{safe_title}</span>
                            <span style="font-size:0.7rem; color:#64748B;">Foto iklan OLX sudah kedaluwarsa</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div style="width:100%; height:205px; border-radius:12px; border:1px dashed #CBD5E1; background:#F8FAFC; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1rem; text-align:center;">
                        {get_lucide_icon('car', size=36, color='#019F90')}
                        <div style="margin-top:0.45rem; font-size:0.84rem; font-weight:700; color:#0D1E38;">{safe_title}</div>
                        <div style="font-size:0.74rem; color:#64748B;">Simulasi Spesifikasi Kustom</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Tombol Link Langsung ke Iklan OLX
            if olx_url and olx_url.startswith("http"):
                ext_svg = get_lucide_icon("arrow-up-right", size=16, color="#FFFFFF")
                st.markdown(
                    f"""
                    <a href="{html.escape(olx_url)}" target="_blank" rel="noopener noreferrer"
                       style="display:flex; align-items:center; justify-content:center; gap:0.45rem; width:100%; margin-top:0.65rem; padding:0.6rem 1rem; background:#019F90; color:#FFFFFF; font-family:'Plus Jakarta Sans',Inter,sans-serif; font-size:0.84rem; font-weight:700; border-radius:10px; text-decoration:none; border:1px solid #008276;">
                        <span>Buka Iklan Asli di OLX</span>
                        {ext_svg}
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Tautan OLX tersedia saat Anda memilih mobil dari daftar arsip iklan.")

        with spec_col:
            cc_val = int(cur_feat.get("engine_cc", 0)) if cur_feat.get("engine_cc") else 0
            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:0.75rem 0.95rem;">
                    <div style="font-size:0.73rem; font-weight:700; color:#019F90; text-transform:uppercase; letter-spacing:0.03em; margin-bottom:0.35rem;">
                        Spesifikasi Utama &amp; Detail Iklan
                    </div>
                    <div class="listing-spec"><span>Merek &amp; Model</span><b>{cur_feat.get('make', '-')} {cur_feat.get('model', '-')}</b></div>
                    <div class="listing-spec"><span>Varian</span><b>{cur_feat.get('variant', '-')}</b></div>
                    <div class="listing-spec"><span>Tahun &amp; Transmisi</span><b>{cur_feat.get('year', '-')} · {cur_feat.get('transmission', '-')}</b></div>
                    <div class="listing-spec"><span>Jarak Tempuh (KM)</span><b>{format_km(cur_feat.get('mileage_km', 0))}</b></div>
                    <div class="listing-spec"><span>Kapasitas Mesin &amp; BBM</span><b>{cc_val:,} cc · {cur_feat.get('fuel_type', '-')}</b></div>
                    <div class="listing-spec"><span>Tipe Bodi &amp; Warna</span><b>{cur_feat.get('body_type', '-')} · {cur_feat.get('color', '-')}</b></div>
                    <div class="listing-spec" style="border-bottom:none;"><span>Lokasi &amp; Penjual</span><b>{cur_feat.get('location', '-')} ({cur_feat.get('seller_type', '-')})</b></div>
                </div>
                """.replace(",", "."),
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='margin:0.8rem 0; border-color:#F1F5F9;'>", unsafe_allow_html=True)

        # 3. Dua Kolom: Kiri Metrik Pilar AI & Pasar, Kanan Barometer Deviasi
        res_sub1, res_sub2 = st.columns([1.1, 1], gap="medium")

        with res_sub1:
            if ml_estimate:
                est_diff_rp = asking_price - ml_estimate
                est_diff_pct = (est_diff_rp / ml_estimate) * 100
                diff_sign = "+" if est_diff_rp > 0 else ""
                st.markdown(
                    f"""
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:0.65rem 0.85rem; margin-bottom:0.55rem;">
                        <div style="font-size:0.72rem; color:#475569; font-weight:600; text-transform:uppercase;">Estimasi Model Machine Learning</div>
                        <div style="font-size:1.15rem; font-weight:800; color:#019F90; margin:0.1rem 0;">{format_rupiah(ml_estimate)}</div>
                        <div style="font-size:0.76rem; color:#475569;">
                            Selisih vs AI: <b>{diff_sign}{format_rupiah(est_diff_rp)} ({diff_sign}{est_diff_pct:.1f}%)</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if comp_median is not None:
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:0.65rem 0.85rem;">
                        <div style="font-size:0.72rem; color:#64748B; font-weight:600; text-transform:uppercase;">Median Listing Serupa ({n_comps} unit)</div>
                        <div style="font-size:1.15rem; font-weight:800; color:#0D1E38; margin:0.1rem 0;">{format_rupiah(comp_median)}</div>
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
            fig_barometer = price_deviation_barometer(
                asking_price=asking_price,
                median_price=comp_median if comp_median else (ml_estimate or asking_price),
                p25=comp_p25,
                p75=comp_p75,
            )
            st.plotly_chart(fig_barometer, width="stretch", config={"displayModeBar": False}, key="chart_cek_gauge")

        st.markdown("<hr style='margin:0.65rem 0; border-color:#F1F5F9;'>", unsafe_allow_html=True)
        if status_label == "Harga Wajar":
            explanation_text = (
                f"Harga iklan <b>{format_rupiah(asking_price)}</b> berada di dalam rentang wajar pasar Jakarta. "
                f"Selisih harga ({delta_pct:+.1f}%) konsisten dengan pola penawaran {n_comps} mobil sejenis "
                f"di rentang P25-P75 ({format_rupiah_compact(comp_p25 or 0)} s/d {format_rupiah_compact(comp_p75 or 0)})."
            )
        elif status_label == "Di Bawah Kisaran Pasar":
            explanation_text = (
                f"Harga penawaran <b>{format_rupiah(asking_price)}</b> berada <b>{abs(delta_pct):.1f}% di bawah</b> acuan pasar. "
                f"Ini merupakan peluang menarik (<i>good deal</i>), namun pastikan memeriksa kelengkapan dokumen dan riwayat fisik kendaraan."
            )
        else:
            explanation_text = (
                f"Harga penawaran <b>{format_rupiah(asking_price)}</b> berada <b>+{abs(delta_pct):.1f}% di atas</b> median pasar. "
                f"Anda memiliki ruang negosiasi menuju kisaran <b>{format_rupiah_compact(ref_price or asking_price)}</b> kecuali kondisi mobil sangat istimewa."
            )

        info_svg = get_lucide_icon("info", size=15, color="#019F90")
        st.markdown(
            f"<div style='font-size:0.83rem; color:#334155; line-height:1.55; background:#F8FAFC; padding:0.65rem 0.9rem; border-radius:8px; border-left:3px solid #019F90; display:flex; align-items:flex-start; gap:0.5rem;'>"
            f"<span style='flex-shrink:0; margin-top:2px;'>{info_svg}</span><span>{explanation_text}</span></div>",
            unsafe_allow_html=True,
        )

    # Tabel Pembanding Serupa
    if not comparables.empty:
        with st.expander(f"Lihat Daftar {min(10, len(comparables))} Listing Pembanding Sejenis", expanded=False):
            disp_c = comparables.head(10).copy()
            disp_c["Harga"] = disp_c["price"].map(format_rupiah)
            disp_c["Kilometer"] = disp_c["mileage_km"].map(format_km)
            disp_c["Tahun"] = disp_c["year"].fillna(0).astype(int).astype(str)
            cols_to_show = [
                c for c in ["make", "model", "variant", "Tahun", "Kilometer", "transmission", "location_display", "Harga"]
                if c in disp_c.columns
            ]
            st.dataframe(
                disp_c[cols_to_show].rename(
                    columns={
                        "make": "Merek",
                        "model": "Model",
                        "variant": "Varian",
                        "transmission": "Transmisi",
                        "location_display": "Wilayah",
                    }
                ),
                hide_index=True,
                width="stretch",
            )
