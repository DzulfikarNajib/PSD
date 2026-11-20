"""Two-column asking-price context calculator with explicit model evaluation."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_combined_archive, load_training_archive
from src.car_search import assess_price_position
from src.modeling import (
    MODEL_PATH,
    evaluate_regression_models,
    get_feature_importance,
    load_model_metadata,
    model_is_validated,
    predict_asking_price,
    training_eligibility,
)
from src.styles import apply_theme
from src.preprocessing import MAX_ANALYSIS_PRICE, MIN_ANALYSIS_PRICE
from src.ui import (
    format_rupiah,
    format_rupiah_compact,
    render_data_source_status,
)


def _number(value, default=0):
    parsed = pd.to_numeric(value, errors="coerce")
    return default if pd.isna(parsed) else float(parsed)


def _format_number(value, suffix=""):
    number = _number(value, default=None)
    return "-" if number is None else f"{number:,.0f}".replace(",", ".") + suffix


def _find_comparables(data, features):
    """Find same make/model listings in a transparent specification window."""
    if data.empty:
        return data.copy()
    rows = data.copy()
    for column in ("price", "year", "mileage_km", "engine_cc"):
        if column in rows:
            rows[column] = pd.to_numeric(rows[column], errors="coerce")
    required = {"make", "model", "price", "year"}
    if not required.issubset(rows.columns):
        return rows.iloc[0:0].copy()
    peers = rows[
        rows["make"].fillna("").astype(str).str.casefold().eq(str(features["make"]).casefold())
        & rows["model"].fillna("").astype(str).str.casefold().eq(str(features["model"]).casefold())
    ].copy()
    peers = peers[peers["year"].between(features["year"] - 2, features["year"] + 2)]
    if "mileage_km" in peers and features["mileage_km"] > 0:
        km_window = max(20_000, features["mileage_km"] * 0.4)
        peers = peers[peers["mileage_km"].between(max(0, features["mileage_km"] - km_window), features["mileage_km"] + km_window) | peers["mileage_km"].isna()]
    if "engine_cc" in peers and features["engine_cc"] > 0:
        peers = peers[peers["engine_cc"].between(features["engine_cc"] * 0.7, features["engine_cc"] * 1.3) | peers["engine_cc"].isna()]
    for column in ("transmission", "fuel_type", "body_type"):
        selected = features.get(column, "Semua")
        if selected != "Semua" and column in peers:
            peers = peers[peers[column].fillna("").astype(str).eq(selected)]
    return peers.dropna(subset=["price"]).reset_index(drop=True)


def _comparable_table(data):
    labels = {
        "make": "Merek", "model": "Model", "variant": "Varian", "year": "Tahun",
        "price": "Harga iklan", "mileage_km": "Kilometer", "engine_cc": "CC",
        "transmission": "Transmisi", "fuel_type": "Bahan bakar", "body_type": "Tipe bodi",
        "location": "Lokasi", "location_normalized": "Wilayah", "url": "Tautan iklan",
    }
    columns = [column for column in labels if column in data.columns]
    display = data[columns].copy().reset_index(drop=True)
    for column in display:
        if column in {"price", "mileage_km", "engine_cc", "year"}:
            display[column] = display[column].map(lambda value: _format_number(value))
        else:
            display[column] = display[column].fillna("").astype(str)
    return display.rename(columns=labels)


def _delta_text(value, reference):
    if reference is None or reference == 0:
        return "Belum dapat dihitung"
    difference = value - reference
    percent = difference / reference * 100
    direction = "di atas" if difference > 0 else "di bawah" if difference < 0 else "sama dengan"
    return f"{format_rupiah(abs(difference))} ({abs(percent):.1f}%) {direction} referensi"


apply_theme()
st.title("Cek Harga Iklan")

with st.container(border=True):
    st.markdown("### Evaluasi Nilai Penawaran Iklan Mobil")
    st.markdown(
        "Ketahui posisi harga iklan mobil yang kamu temukan di marketplace—apakah penawaran tersebut **di bawah pasar (good deal)**, **wajar**, atau **kemahalan (di atas pasar)**. "
        "Evaluasi menggabungkan perbandingan median mobil sejenis dan estimasi algoritma Machine Learning.",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    guide_cols = st.columns(3, gap="medium")
    with guide_cols[0]:
        with st.container(border=True):
            st.markdown(
                "<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
                "<span style='background:#008B8B;color:#FFFFFF;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;'>1</span>"
                "<b style='color:#0F172A;font-size:14px;'>Pilih / Input Spek</b>"
                "</div>"
                "<span style='color:#475569;font-size:12.5px;line-height:1.4;'>Pilih mobil contoh dari database arsip atau masukkan spesifikasi iklan yang sedang kamu taksir.</span>",
                unsafe_allow_html=True,
            )
    with guide_cols[1]:
        with st.container(border=True):
            st.markdown(
                "<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
                "<span style='background:#008B8B;color:#FFFFFF;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;'>2</span>"
                "<b style='color:#0F172A;font-size:14px;'>Evaluasi Ganda</b>"
                "</div>"
                "<span style='color:#475569;font-size:12.5px;line-height:1.4;'>Sistem otomatis membandingkan dengan <b>median listing serupa di OLX</b> dan <b>prediksi model Machine Learning</b>.</span>",
                unsafe_allow_html=True,
            )
    with guide_cols[2]:
        with st.container(border=True):
            st.markdown(
                "<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
                "<span style='background:#008B8B;color:#FFFFFF;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;'>3</span>"
                "<b style='color:#0F172A;font-size:14px;'>Baca Status Harga</b>"
                "</div>"
                "<div style='font-size:12.5px;line-height:1.45;color:#475569;'>"
                "🟢 <b>Di Bawah:</b> Potensi good deal<br>"
                "🔵 <b>Wajar:</b> Standar pasar Jakarta<br>"
                "🔴 <b>Di Atas:</b> Bahan tawar-menawar"
                "</div>",
                unsafe_allow_html=True,
            )

with st.expander("Ringkasan Fitur & Transformasi Model"):
    st.write("Target model adalah harga penawaran (price). Prediktornya: merek, model, tahun, kilometer, kapasitas mesin, transmisi, bahan bakar, dan tipe bodi.")
    st.caption("Kolom kategori diubah dengan one-hot encoding. Nilai numerik kosong, termasuk CC yang tidak dicantumkan pada sebagian EV, diisi median dari data latih.")
    st.write(
        f"Iklan di bawah {format_rupiah(MIN_ANALYSIS_PRICE)} atau di atas {format_rupiah(MAX_ANALYSIS_PRICE)}, serta teks indikasi pembiayaan, dikeluarkan sebelum pelatihan. Kandidat dibandingkan pada target harga asli dan log1p."
    )
    st.caption("Evaluasi memakai pembagian acak 80% latih dan 20% uji (random_state 42). Model dipilih berdasarkan MAE terendah pada data uji; MAE dan RMSE bukan jaminan untuk listing baru.")

prefill = st.session_state.pop("price_checker_prefill", {})
auto_check_prefill = bool(prefill.pop("_auto_calculate", False))
prefill.pop("_comparison_source", None)
if prefill:
    prefill_widgets = {
        "calculator_make": "make",
        "calculator_model": "model",
        "calculator_year": "year",
        "calculator_mileage": "mileage_km",
        "calculator_engine_cc": "engine_cc",
        "calculator_transmission": "transmission",
        "calculator_fuel_type": "fuel_type",
        "calculator_body_type": "body_type",
        "calculator_asking_price": "price",
    }
    for widget_key, field in prefill_widgets.items():
        st.session_state.pop(widget_key, None)
        if prefill.get(field) is not None:
            st.session_state[widget_key] = prefill[field]
    st.session_state.pop("price_calculation_result", None)

archive = load_combined_archive()
training_data = load_training_archive()
comparison_data = archive.copy()
# Sumber data status dipindahkan ke footnote metodologi di bagian bawah halaman
input_data = comparison_data if not comparison_data.empty else training_data.copy()
for column in ("price", "year", "mileage_km", "engine_cc"):
    if column in input_data:
        input_data[column] = pd.to_numeric(input_data[column], errors="coerce")
makes = sorted(input_data.get("make", pd.Series(dtype=str)).dropna().astype(str).unique())
price_example = st.session_state.get("price_example_record")
if not prefill and not st.session_state.get("price_example_initialized") and not st.session_state.get("price_calculation_result") and not input_data.empty:
    sample_rows = input_data.copy()
    sample_rows["make_key"] = sample_rows["make"].fillna("").astype(str).str.casefold()
    sample_rows["model_key"] = sample_rows["model"].fillna("").astype(str).str.casefold()
    sample = sample_rows[sample_rows["make_key"].eq("toyota") & sample_rows["model_key"].eq("avanza")]
    if sample.empty:
        sample = sample_rows[sample_rows["make_key"].eq("honda") & sample_rows["model_key"].str.contains("brio", regex=False)]
    if sample.empty:
        sample = sample_rows
    sample = sample.sort_values("fetched_at", na_position="last") if "fetched_at" in sample else sample
    chosen_example = sample.iloc[0]
    example_fields = ["make", "model", "year", "mileage_km", "engine_cc", "fuel_type", "transmission", "body_type", "price"]
    price_example = {key: (None if pd.isna(chosen_example.get(key)) else chosen_example.get(key)) for key in example_fields}
    st.session_state["price_example_record"] = price_example
    st.session_state["price_example_initialized"] = True
    for widget_key, field in {
        "calculator_make": "make", "calculator_model": "model", "calculator_year": "year",
        "calculator_mileage": "mileage_km", "calculator_engine_cc": "engine_cc",
        "calculator_fuel_type": "fuel_type", "calculator_transmission": "transmission",
        "calculator_body_type": "body_type", "calculator_asking_price": "price",
    }.items():
        if price_example.get(field) is not None:
            st.session_state[widget_key] = price_example[field]
if input_data.empty or not makes:
    st.info("Belum ada data spesifikasi untuk kalkulator. Impor dataset atau simpan snapshot sebelum memakai kalkulator.")
else:
    form_col, result_col = st.columns([.95, 1.25], gap="large", vertical_alignment="top")
    with form_col:
        with st.container(border=True):
            st.markdown("#### Pilih listing atau isi manual")
            option_ids, labels = [], {}
            if not comparison_data.empty and "listing_id" in comparison_data:
                selectable = comparison_data.drop_duplicates("listing_id", keep="last")
                for _, row in selectable.iterrows():
                    listing_id = str(row.get("listing_id", ""))
                    if not listing_id:
                        continue
                    option_ids.append(listing_id)
                    year = pd.to_numeric(row.get("year"), errors="coerce")
                    year_text = str(int(year)) if pd.notna(year) else "tahun -"
                    labels[listing_id] = f"{row.get('make', 'Mobil')} {row.get('model', '')} · {year_text} · {format_rupiah(row.get('price'))}"
            selector_key = "saved_price_listing_archive"

            def apply_saved_listing():
                selected_id = st.session_state.get(selector_key)
                if not selected_id:
                    return
                chosen_rows = comparison_data[comparison_data["listing_id"].astype(str).eq(str(selected_id))]
                if chosen_rows.empty:
                    return
                chosen = chosen_rows.iloc[0]
                fields = ["make", "model", "year", "mileage_km", "engine_cc", "fuel_type", "transmission", "body_type", "price"]
                st.session_state["price_checker_prefill"] = {
                    **{key: (None if pd.isna(chosen.get(key)) else chosen.get(key)) for key in fields},
                    "_auto_calculate": True,
                }

            if option_ids:
                st.selectbox(
                    "Cari listing tersimpan",
                    option_ids,
                    index=None,
                    placeholder="Cari merek, model, tahun, harga...",
                    format_func=lambda value: labels.get(value, value),
                    key=selector_key,
                    on_change=apply_saved_listing,
                    help="Memilih listing akan mengisi spesifikasi pada formulir. Harga tetap dapat diubah.",
                )
            else:
                st.caption("Belum ada listing pada sumber ini. Spesifikasi dapat dimasukkan secara manual.")

            if st.session_state.get("calculator_make") not in makes:
                st.session_state["calculator_make"] = makes[0]
            start_make = st.session_state["calculator_make"]
            start_models = sorted(input_data.loc[input_data["make"].astype(str).eq(start_make), "model"].dropna().astype(str).unique())
            start_models = start_models or sorted(input_data["model"].dropna().astype(str).unique())

            with st.form("price_calculator"):
                make = st.selectbox("Merek", makes, key="calculator_make")
                available_models = sorted(input_data.loc[input_data["make"].astype(str).eq(make), "model"].dropna().astype(str).unique())
                available_models = available_models or start_models
                default_model = prefill.get("model") if prefill.get("model") in available_models else available_models[0]
                if st.session_state.get("calculator_model") not in available_models:
                    st.session_state["calculator_model"] = default_model
                model = st.selectbox("Model", available_models, key="calculator_model")
                model_rows = input_data[input_data["make"].fillna("").astype(str).eq(make) & input_data["model"].fillna("").astype(str).eq(model)]
                years_available = input_data.get("year", pd.Series(dtype=float)).dropna()
                min_year = max(1950, int(years_available.min()) if not years_available.empty else 1990)
                max_year = max(min_year, int(years_available.max()) if not years_available.empty else pd.Timestamp.now().year)
                year_value = int(_number(prefill.get("year", 2020), 2020))
                max_year = max(max_year, year_value)
                if "calculator_year" not in st.session_state:
                    st.session_state["calculator_year"] = min(max(year_value, min_year), max_year)
                else:
                    st.session_state["calculator_year"] = min(max(int(st.session_state["calculator_year"]), min_year), max_year)
                year = st.number_input("Tahun kendaraan", min_value=min_year, max_value=max_year, step=1, key="calculator_year")
                km_default = int(model_rows["mileage_km"].median()) if "mileage_km" in model_rows and model_rows["mileage_km"].notna().any() else 50_000
                cc_default = int(model_rows["engine_cc"].median()) if "engine_cc" in model_rows and model_rows["engine_cc"].notna().any() else 1_300
                if "calculator_mileage" not in st.session_state:
                    st.session_state["calculator_mileage"] = int(_number(prefill.get("mileage_km", km_default), km_default))
                if "calculator_engine_cc" not in st.session_state:
                    st.session_state["calculator_engine_cc"] = int(_number(prefill.get("engine_cc", cc_default), cc_default))
                st.session_state["calculator_mileage"] = min(max(int(st.session_state["calculator_mileage"]), 0), 1_000_000)
                st.session_state["calculator_engine_cc"] = min(max(int(st.session_state["calculator_engine_cc"]), 0), 10_000)
                mileage = st.number_input("Kilometer", 0, 1_000_000, step=5_000, key="calculator_mileage")
                engine_cc = st.number_input("Kapasitas mesin (cc)", 0, 10_000, step=100, key="calculator_engine_cc")
                cat_a, cat_b = st.columns(2)
                transmission_options = ["Semua", *sorted(input_data.get("transmission", pd.Series(dtype=str)).dropna().astype(str).unique())]
                fuel_options = ["Semua", *sorted(input_data.get("fuel_type", pd.Series(dtype=str)).dropna().astype(str).unique())]
                body_options = ["Semua", *sorted(input_data.get("body_type", pd.Series(dtype=str)).dropna().astype(str).unique())]
                with cat_a:
                    trans_default = prefill.get("transmission") if prefill.get("transmission") in transmission_options else "Semua"
                    if st.session_state.get("calculator_transmission") not in transmission_options:
                        st.session_state["calculator_transmission"] = trans_default
                    transmission = st.selectbox("Transmisi", transmission_options, key="calculator_transmission")
                    fuel_default = prefill.get("fuel_type") if prefill.get("fuel_type") in fuel_options else "Semua"
                    if st.session_state.get("calculator_fuel_type") not in fuel_options:
                        st.session_state["calculator_fuel_type"] = fuel_default
                    fuel_type = st.selectbox("Bahan bakar", fuel_options, key="calculator_fuel_type")
                with cat_b:
                    body_default = prefill.get("body_type") if prefill.get("body_type") in body_options else "Semua"
                    if st.session_state.get("calculator_body_type") not in body_options:
                        st.session_state["calculator_body_type"] = body_default
                    body_type = st.selectbox("Tipe bodi", body_options, key="calculator_body_type")
                    price_max = max(50_000_000_000, int(_number(input_data.get("price", pd.Series(dtype=float)).max(), 0)))
                    asking_default = int(_number(prefill.get("price", 150_000_000), 150_000_000))
                if "calculator_asking_price" not in st.session_state:
                    st.session_state["calculator_asking_price"] = min(max(asking_default, 1), price_max)
                else:
                    st.session_state["calculator_asking_price"] = min(max(int(st.session_state["calculator_asking_price"]), 1), price_max)
                asking_price = st.number_input("Harga iklan yang ingin dicek (Rp)", 1, price_max, step=5_000_000, key="calculator_asking_price")
                submitted = st.form_submit_button("Cek harga", type="primary", icon=":material/price_check:", width="stretch")

            features = {
                "make": make, "model": model, "year": int(year), "mileage_km": int(mileage), "engine_cc": int(engine_cc),
                "transmission": transmission, "fuel_type": fuel_type, "body_type": body_type,
            }
            if submitted or auto_check_prefill:
                peers = _find_comparables(comparison_data, features)
                estimate, model_message = None, None
                metadata = load_model_metadata()
                if Path(MODEL_PATH).exists() and model_is_validated(metadata):
                    model_features = dict(features)
                    for category in ("transmission", "fuel_type", "body_type"):
                        if model_features[category] == "Semua":
                            mode = model_rows[category].dropna().astype(str).mode() if category in model_rows else pd.Series(dtype=str)
                            model_features[category] = mode.iloc[0] if not mode.empty else ""
                    try:
                        estimate = predict_asking_price(model_features)
                    except (ValueError, FileNotFoundError, OSError) as exc:
                        model_message = str(exc)
                st.session_state["price_calculation_result"] = {"asking_price": int(asking_price), "estimate": estimate, "peers": peers}

    with result_col:
        st.markdown("### Hasil Analisis Harga")
        result = st.session_state.get("price_calculation_result")
        metadata = load_model_metadata()
        best_model_name = metadata.get("best_model", "Random Forest Regressor")
        best_mae = float(metadata.get("models", {}).get(best_model_name, {}).get("MAE", 0))

        if not result:
            with st.container(border=True):
                st.markdown("#### Contoh dari arsip tersimpan")
                st.write("Form di sebelah kiri sudah diisi dengan contoh mobil dari arsip. Contoh ini belum dinilai sebagai iklan pengguna.")
                if price_example:
                    st.markdown(f"**{price_example.get('make', '')} {price_example.get('model', '')} · {int(_number(price_example.get('year'), 0))}**")
                    st.metric("Harga pada contoh", format_rupiah(price_example.get("price")))
                    sample_features = {
                        key: price_example.get(key) for key in ("make", "model", "year", "mileage_km", "engine_cc", "fuel_type", "transmission", "body_type")
                    }
                    if sample_features.get("year") is not None:
                        sample_features["year"] = int(_number(sample_features["year"], 0))
                        sample_features["mileage_km"] = _number(sample_features.get("mileage_km"))
                        sample_features["engine_cc"] = _number(sample_features.get("engine_cc"))
                        sample_peers = _find_comparables(comparison_data, sample_features)
                        st.metric("Pembanding serupa", f"{len(sample_peers):,}".replace(",", "."))
                    st.caption("Tekan **Cek harga** untuk menghitung estimasi dan membandingkan contoh ini. Pilih listing atau ubah form untuk menganalisis mobil lain.")
                else:
                    st.write("Pilih listing tersimpan atau isi detail mobil di sebelah kiri, lalu tekan tombol **Cek harga**.")
                    st.metric("Harga iklan", "-")
                    st.metric("Pembanding serupa", "-")
                if not model_is_validated(metadata):
                    st.caption("Estimasi model belum tersedia. Perbandingan listing tetap dapat digunakan.")
        else:
            asking = float(result["asking_price"])
            # Old Streamlit session state can outlive a deploy and may contain
            # a result created before the peers field was added.
            peers = result.get("peers")
            if not isinstance(peers, pd.DataFrame):
                peers = pd.DataFrame(columns=["price"])
            estimate = result["estimate"]

            price_position = assess_price_position(asking, peers["price"] if not peers.empty else [])
            badge_html = ""
            kesimpulan_text = ""
            badge_cls = ""
            badge_label = ""

            if price_position["median"] is not None:
                ref_median = price_position["median"]
                diff_pct = price_position["difference_pct"] * 100
                diff_nominal = abs(asking - ref_median)
                if price_position["label"] == "Di bawah pembanding":
                    badge_cls = "badge-underpriced"
                    badge_label = price_position["label"]
                    kesimpulan_text = f"Harga iklan **{abs(diff_pct):.1f}%** ({format_rupiah_compact(diff_nominal)}) di bawah median {price_position['count']} listing serupa yang tersedia. Ini indikasi relatif terhadap harga iklan, bukan bukti kondisi atau kualitas unit."
                elif price_position["label"] == "Di atas pembanding":
                    badge_cls = "badge-overpriced"
                    badge_label = price_position["label"]
                    kesimpulan_text = f"Harga iklan **{diff_pct:.1f}%** ({format_rupiah_compact(diff_nominal)}) di atas median {price_position['count']} listing serupa yang tersedia. Ini indikasi relatif terhadap harga iklan, bukan nilai transaksi."
                elif price_position["label"]:
                    badge_cls = "badge-fair"
                    badge_label = price_position["label"]
                    kesimpulan_text = f"Harga iklan berjarak **{abs(diff_pct):.1f}%** dari median {price_position['count']} listing serupa. Batas ±8% adalah ambang indikatif AutoMatch, bukan rentang statistik atau harga transaksi."
                else:
                    kesimpulan_text = f"Tersedia {price_position['count']} pembanding. Belum cukup untuk memberi indikasi posisi harga; median pembandingnya {format_rupiah_compact(ref_median)}."
                if price_position["label"]:
                    badge_html = f"<div class='price-result-status'><span class='{badge_cls}'>{badge_label}</span></div>"

            with st.container(border=True, key="price_analysis_hero"):
                st.markdown("#### Harga Iklan yang Dianalisis")
                st.markdown(f"<div class='price-hero-value'>{format_rupiah(asking)}</div>", unsafe_allow_html=True)
                if badge_html:
                    st.markdown(badge_html, unsafe_allow_html=True)

            result_cols = st.columns(2, gap="small")
            with result_cols[0]:
                with st.container(border=True):
                    st.markdown("**Listing Serupa**")
                    if peers.empty:
                        st.metric("Jumlah pembanding", "0")
                        st.caption("Tidak ada listing serupa yang cocok di arsip. Status harga pasar tidak ditampilkan; gunakan estimasi model sebagai konteks umum saja.")
                    else:
                        median = float(peers["price"].median())
                        low, high = float(peers["price"].min()), float(peers["price"].max())
                        st.metric("Median listing serupa", format_rupiah(median))
                        st.caption(f"Rentang pembanding: {format_rupiah_compact(low)} s/d {format_rupiah_compact(high)} · {len(peers):,} listing".replace(",", "."))
                        st.caption(f"Harga input: {_delta_text(asking, median)}.")
                        st.caption("Label indikatif hanya muncul bila ada sedikitnya 5 pembanding dan memakai ambang ±8% dari median.")

            with result_cols[1]:
                with st.container(border=True):
                    st.markdown("**Estimasi Model Machine Learning**")
                    if estimate is None:
                        st.metric("Estimasi Model", "-")
                        st.caption("Model belum dilatih atau belum lolos validasi.")
                    else:
                        st.metric("Estimasi Model", format_rupiah(estimate))
                        model_gap = asking - estimate
                        model_gap_pct = (model_gap / estimate * 100) if estimate else 0.0
                        model_direction = "di atas" if model_gap > 0 else "di bawah" if model_gap < 0 else "sama dengan"
                        st.caption(
                            f"Harga input {format_rupiah(abs(model_gap))} ({abs(model_gap_pct):.1f}%) {model_direction} estimasi model."
                        )
                        if best_mae > 0:
                            st.caption(
                                f"MAE uji: {format_rupiah_compact(best_mae)} rata-rata selisih prediksi per listing. "
                                "Ini ukuran evaluasi model, bukan rentang harga mobil ini."
                            )

            if kesimpulan_text:
                with st.container(border=True):
                    st.markdown("**Kesimpulan Singkat**")
                    st.write(kesimpulan_text)

            if not peers.empty:
                with st.expander(f"Lihat {len(peers):,} listing yang menjadi pembanding".replace(",", ".")):
                    st.dataframe(_comparable_table(peers.head(30)), hide_index=True, width="stretch", alt="Detail listing yang dipakai sebagai pembanding harga")
            action_cols = st.columns(2, gap="small")
            with action_cols[0]:
                if st.button("Kembali ke Cari Mobil", icon=":material/directions_car:", key="price_back_to_search", width="stretch"):
                    st.switch_page("pages/2_Find_Your_Car.py")
            with action_cols[1]:
                source_urls = peers.get("url", pd.Series(dtype=str)).dropna().astype(str)
                source_urls = source_urls[source_urls.str.startswith("http")]
                if len(source_urls):
                    st.link_button("Buka iklan pembanding", source_urls.iloc[0], icon=":material/open_in_new:", width="stretch")

st.markdown("")
with st.expander("Metodologi & Bukti Evaluasi Model AI (Machine Learning)", expanded=False):
    st.write("Model prediksi menggunakan pendekatan **Supervised Learning (Regresi)** yang dilatih berdasarkan spesifikasi kendaraan untuk memprediksi harga penawaran wajar.")
    st.caption("Cek Harga memakai spesifikasi 1 iklan, lalu membandingkan harganya dengan iklan serupa dan—jika model lolos kriteria validasi—menampilkan estimasi regresi Machine Learning.")
    eligible, eligibility_message, model_data = training_eligibility(training_data)
    st.caption(f"Dataset pelatihan: {len(model_data):,} listing unik tervalidasi. {eligibility_message}".replace(",", "."))
    
    col_train, col_status = st.columns([1, 2])
    with col_train:
        if st.button("Latih & Evaluasi Ulang Model", disabled=not eligible, help="Menggunakan arsip tersimpan tanpa panggilan API luar."):
            try:
                with st.spinner("Melatih dan membandingkan model regresi..."):
                    training_result = evaluate_regression_models(training_data)
            except OSError as exc:
                if getattr(exc, "errno", None) == 28:
                    st.error("Model tidak dapat disimpan karena ruang disk perangkat penuh. Kosongkan ruang, lalu jalankan evaluasi ulang.")
                    st.stop()
                raise
            if training_result.get("status") == "ready":
                st.success(f"Pelatihan selesai! Model terbaik: {training_result['best_model']}.")
                st.rerun()
            else:
                st.warning(training_result.get("message", "Model belum dapat dilatih."))

    metadata = load_model_metadata()
    if metadata.get("models") and model_is_validated(metadata):
        st.markdown("#### Perbandingan Model Baseline vs Model Utama")
        model_table = pd.DataFrame([{"Model": name, **metrics} for name, metrics in metadata["models"].items()])
        for column in ("MAE", "RMSE"):
            if column in model_table:
                model_table[column] = model_table[column].map(format_rupiah)
        if "R2" in model_table:
            model_table["R2"] = model_table["R2"].map(lambda value: f"{value:.4f}" if pd.notna(value) else "-")
        st.dataframe(model_table, hide_index=True, width="stretch", alt="Perbandingan metrik evaluasi model regresi")
        st.caption("Cara membaca: MAE = rata-rata besar selisih harga prediksi; RMSE memberi bobot lebih besar pada kesalahan yang besar; R² menunjukkan seberapa banyak variasi harga pada data uji yang dijelaskan model. Umumnya MAE/RMSE lebih kecil dan R² lebih besar lebih baik. Metrik ini menilai model pada data uji, bukan jaminan harga satu mobil.")
    elif metadata.get("models"):
        st.warning("Metrik yang tersimpan berasal dari model lama dan disembunyikan sampai pelatihan ulang tervalidasi.")

    if Path(MODEL_PATH).exists() and model_is_validated(metadata):
        st.markdown("#### Feature Importance Model Terbaik")
        importance = get_feature_importance().head(10)
        if not importance.empty:
            importance_plot = importance.iloc[::-1]  # Urutkan dari terbawah ke teratas untuk bar horizontal
            fig_imp = go.Figure(go.Bar(
                x=importance_plot["importance"],
                y=importance_plot["feature"],
                orientation="h",
                marker=dict(color="#008B8B", cornerradius=5),
                text=[f"{v:.3f}" for v in importance_plot["importance"]],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="Fitur: <b>%{y}</b><br>Tingkat Pengaruh: <b>%{x:.4f}</b><extra></extra>",
            ))
            fig_imp.update_layout(
                height=340,
                margin=dict(l=10, r=40, t=10, b=10),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font=dict(family="Inter, sans-serif", color="#0F172A", size=12),
                xaxis=dict(title="Skor kepentingan fitur (relatif)", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title=None, showgrid=False),
            )
            st.plotly_chart(fig_imp, width="stretch", config={"displayModeBar": False}, key="price_feature_importance_plot")
            st.caption(f"Model aktif: **{metadata.get('best_model', '-')}** ({metadata.get('training_unique_listings', 0):,} listing training). Pada model pohon, skor berasal dari kontribusi fitur pada pemisahan cabang dan dapat memberi bobot lebih besar pada fitur numerik yang punya banyak kemungkinan ambang. Skor ini relatif, bukan persentase harga atau bukti sebab-akibat.")
    else:
        st.info("Model belum dilatih atau belum lolos kriteria minimum validasi.")

st.markdown("")
with st.expander("Catatan Metodologi & Sumber Data"):
    st.write(f"Estimasi dan perbandingan listing memakai **Dataset OLX aktif yang telah dibersihkan** ({len(input_data):,} unit).".replace(",", "."))
    st.write("Model prediksi dilatih pada fitur spesifikasi (merek, model, tahun, kilometer, kapasitas mesin, transmisi, bahan bakar, dan tipe bodi). Estimasi berfungsi sebagai pembanding konteks awal, bukan jaminan nilai pasar mutlak atau pengganti inspeksi fisik kendaraan.")
