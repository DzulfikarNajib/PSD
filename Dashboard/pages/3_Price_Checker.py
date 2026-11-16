"""Two-column asking-price context calculator with explicit model evaluation."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import get_last_updated_text, load_combined_archive, load_live_data, load_training_archive
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
from src.ui import format_rupiah, format_rupiah_compact


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
st.caption("Bandingkan harga iklan dengan listing serupa dan, bila tersedia, estimasi model.")
st.caption("Harga iklan dan estimasi adalah konteks awal. Keduanya bukan harga transaksi pasti dan tidak menggantikan pemeriksaan kondisi mobil.")

prefill = st.session_state.pop("price_checker_prefill", {})
auto_check_prefill = bool(prefill.pop("_auto_calculate", False))
prefill_source = prefill.pop("_comparison_source", None)
if prefill:
    if prefill_source in {"Arsip Penuh", "Listing Terbaru"}:
        st.session_state["price_comparison_source"] = prefill_source
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

live = load_live_data()
archive = load_combined_archive()
training_data = load_training_archive()
source = st.radio(
    "Sumber pembanding",
    ["Arsip Penuh", "Listing Terbaru"],
    horizontal=True,
    key="price_comparison_source",
    help="Sumber ini mengubah data pembanding listing serupa. Model machine learning tetap menggunakan arsip historis tervalidasi.",
)
comparison_data = live.copy() if source == "Listing Terbaru" else archive.copy()
if source == "Listing Terbaru":
    st.caption(f"Snapshot OLX terakhir: {get_last_updated_text()} · listing dapat berubah atau sudah tidak aktif saat dibuka.")
else:
    st.caption(f"Arsip Penuh · Excel + snapshot OLX tersimpan · {len(comparison_data):,} mobil unik. Arsip Excel tidak memiliki tanggal pengambilan dan tautannya mungkin sudah tidak aktif.".replace(",", "."))

input_data = comparison_data if not comparison_data.empty else training_data.copy()
for column in ("price", "year", "mileage_km", "engine_cc"):
    if column in input_data:
        input_data[column] = pd.to_numeric(input_data[column], errors="coerce")
makes = sorted(input_data.get("make", pd.Series(dtype=str)).dropna().astype(str).unique())
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
            selector_key = f"saved_price_listing_{'latest' if source == 'Listing Terbaru' else 'archive'}"

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
                    "_comparison_source": source,
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
                submitted = st.form_submit_button("Cek harga", type="primary", icon=":material/price_check:", use_container_width=True)

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
                st.session_state["price_calculation_result"] = {"source": source, "asking_price": int(asking_price), "estimate": estimate, "peers": peers}

    with result_col:
        st.markdown("### Hasil Analisis Harga")
        result = st.session_state.get("price_calculation_result")
        metadata = load_model_metadata()
        best_model_name = metadata.get("best_model", "Random Forest Regressor")
        best_mae = float(metadata.get("models", {}).get(best_model_name, {}).get("MAE", 0))

        if result and result.get("source") != source:
            st.info("Sumber pembanding berubah. Tekan Cek harga lagi untuk menghitung hasil dengan sumber yang dipilih.")
        elif not result:
            with st.container(border=True):
                st.markdown("#### Mulai Pengecekan")
                st.write("Pilih listing tersimpan atau isi detail mobil di sebelah kiri, lalu tekan tombol **Cek harga**.")
                st.metric("Harga iklan", "-")
                st.metric("Pembanding serupa", "-")
                if not model_is_validated(metadata):
                    st.caption("Estimasi model belum tersedia. Perbandingan listing tetap dapat digunakan.")
        else:
            asking = float(result["asking_price"])
            peers = result["peers"]
            estimate = result["estimate"]

            # Hitung Status Badge (Underpriced, Harga Wajar, Overpriced)
            ref_median = float(peers["price"].median()) if not peers.empty else None
            badge_html = ""
            kesimpulan_text = ""

            if ref_median and ref_median > 0:
                diff_pct = ((asking - ref_median) / ref_median) * 100
                diff_nominal = abs(asking - ref_median)
                if diff_pct < -8.0:
                    badge_cls = "badge-underpriced"
                    badge_label = "Underpriced"
                    kesimpulan_text = f"Harga iklan **{abs(diff_pct):.1f}%** ({format_rupiah_compact(diff_nominal)}) di bawah median listing serupa yang tersedia. Periksa kondisi unit dan dokumennya sebelum menilai penawaran."
                elif diff_pct > 8.0:
                    badge_cls = "badge-overpriced"
                    badge_label = "Overpriced"
                    kesimpulan_text = f"Harga iklan **{diff_pct:.1f}%** ({format_rupiah_compact(diff_nominal)}) di atas median listing serupa yang tersedia. Gunakan detail pembanding saat menilai ruang negosiasi."
                else:
                    badge_cls = "badge-fair"
                    badge_label = "Harga Wajar"
                    kesimpulan_text = f"Harga iklan berjarak **{abs(diff_pct):.1f}%** dari median listing serupa yang tersedia, masih dalam batas pembanding ±8% yang dipakai AutoMatch."
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
                        st.caption(f"Tidak ada listing {source.lower()} yang cocok. Status harga pasar tidak ditampilkan; gunakan estimasi model sebagai konteks umum saja.")
                    else:
                        median = float(peers["price"].median())
                        low, high = float(peers["price"].min()), float(peers["price"].max())
                        st.metric("Median listing serupa", format_rupiah(median))
                        st.caption(f"Rentang pembanding: {format_rupiah_compact(low)} s/d {format_rupiah_compact(high)} · {len(peers):,} listing".replace(",", "."))
                        st.caption(f"Harga input: {_delta_text(asking, median)}.")

            with result_cols[1]:
                with st.container(border=True):
                    st.markdown("**Estimasi Model Machine Learning**")
                    if estimate is None:
                        st.metric("Estimasi Model", "-")
                        st.caption("Model belum dilatih atau belum lolos validasi.")
                    else:
                        st.metric("Estimasi Model", format_rupiah(estimate))
                        if best_mae > 0:
                            wajar_min = max(0.0, estimate - best_mae)
                            wajar_max = estimate + best_mae
                            st.caption("**Rentang acuan model (prediksi ± MAE):**")
                            st.caption(f"{format_rupiah_compact(wajar_min)} s/d {format_rupiah_compact(wajar_max)}. MAE {format_rupiah_compact(best_mae)} adalah rata-rata galat absolut pada evaluasi, bukan jaminan rentang harga unit ini.")
                        else:
                            st.caption(f"Harga input: {_delta_text(asking, estimate)}.")

            if kesimpulan_text:
                with st.container(border=True):
                    st.markdown("**Kesimpulan Singkat**")
                    st.write(kesimpulan_text)

            if not peers.empty:
                with st.expander(f"Lihat {len(peers):,} listing yang menjadi pembanding".replace(",", ".")):
                    st.dataframe(_comparable_table(peers.head(30)), hide_index=True, width="stretch", alt="Detail listing yang dipakai sebagai pembanding harga")

st.markdown("### Metode & Evaluasi Model Regresi")
with st.container(border=True):
    st.write("Model prediksi menggunakan pendekatan **Supervised Learning (Regresi)** yang dilatih berdasarkan spesifikasi kendaraan untuk memprediksi harga penawaran.")
    eligible, eligibility_message, model_data = training_eligibility(training_data)
    st.caption(f"Dataset pelatihan: {len(model_data):,} listing unik tervalidasi. {eligibility_message}".replace(",", "."))
    
    col_train, col_status = st.columns([1, 2])
    with col_train:
        if st.button("Latih & Evaluasi Ulang Model", disabled=not eligible, help="Menggunakan arsip tersimpan tanpa panggilan API luar."):
            with st.spinner("Melatih dan membandingkan model regresi..."):
                training_result = evaluate_regression_models(training_data)
            if training_result.get("status") == "ready":
                st.success(f"Pelatihan selesai! Model terbaik: {training_result['best_model']}.")
                st.rerun()
            else:
                st.warning(training_result.get("message", "Model belum dapat dilatih."))

    metadata = load_model_metadata()
    if metadata.get("models"):
        st.markdown("#### Perbandingan Model Baseline vs Model Utama")
        model_table = pd.DataFrame([{"Model": name, **metrics} for name, metrics in metadata["models"].items()])
        for column in ("MAE", "RMSE"):
            if column in model_table:
                model_table[column] = model_table[column].map(format_rupiah)
        if "R2" in model_table:
            model_table["R2"] = model_table["R2"].map(lambda value: f"{value:.4f}" if pd.notna(value) else "-")
        st.dataframe(model_table, hide_index=True, width="stretch", alt="Perbandingan metrik evaluasi model regresi")
        st.caption("Keterangan: MAE mengukur rata-rata kesalahan absolut, RMSE memberi penalti lebih besar pada kesalahan ekstrem, dan R² menunjukkan proporsi variasi harga yang mampu dijelaskan model.")

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
                xaxis=dict(title="Skor Kepentingan Relatif (Gini Importance)", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title=None, showgrid=False),
            )
            st.plotly_chart(fig_imp, use_container_width=True, config={"displayModeBar": False}, key="price_feature_importance_plot")
            st.caption(f"Model aktif: **{metadata.get('best_model', '-')}** ({metadata.get('training_unique_listings', 0):,} data training). Grafik menunjukkan fitur yang paling berpengaruh dalam penentuan estimasi harga.")
    else:
        st.info("Model belum dilatih atau belum lolos kriteria minimum validasi.")
