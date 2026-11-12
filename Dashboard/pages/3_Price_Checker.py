"""Two-column asking-price context calculator with explicit model evaluation."""

from pathlib import Path

import pandas as pd
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
from src.ui import format_rupiah


def _number(value, default=0):
    parsed = pd.to_numeric(value, errors="coerce")
    return default if pd.isna(parsed) else float(parsed)


def _format_number(value, suffix=""):
    number = _number(value, default=None)
    return "—" if number is None else f"{number:,.0f}".replace(",", ".") + suffix


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
st.caption("Masukkan harga dan detail mobil. AutoMatch membandingkan iklan serupa dan menampilkan estimasi model jika model tervalidasi tersedia.")
st.caption("Hasil adalah konteks harga penawaran, bukan taksiran harga transaksi, pemeriksaan kondisi, atau rekomendasi membeli.")

live = load_live_data()
archive = load_combined_archive()
training_data = load_training_archive()
source = st.radio(
    "Sumber pembanding",
    ["Arsip Penuh", "Listing Terbaru"],
    horizontal=True,
    key="price_comparison_source",
    help="Sumber ini mengubah pembanding listing. Model tetap memakai arsip historis tervalidasi.",
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
                    year_text = str(int(year)) if pd.notna(year) else "tahun —"
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
                st.session_state["price_checker_prefill"] = {key: (None if pd.isna(chosen.get(key)) else chosen.get(key)) for key in fields}

            if option_ids:
                st.selectbox(
                    "Cari listing tersimpan",
                    option_ids,
                    index=None,
                    placeholder="Cari merek, model, tahun, harga…",
                    format_func=lambda value: labels.get(value, value),
                    key=selector_key,
                    on_change=apply_saved_listing,
                    help="Memilih listing akan mengisi spesifikasi pada formulir. Harga tetap dapat diubah.",
                )
            else:
                st.caption("Belum ada listing pada sumber ini. Spesifikasi dapat dimasukkan secara manual.")

            prefill = st.session_state.pop("price_checker_prefill", {})
            if prefill.get("make") in makes:
                st.session_state["calculator_make"] = prefill["make"]
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
                model = st.selectbox("Model", available_models, index=available_models.index(default_model))
                st.caption("Varian iklan belum dipakai oleh model karena penamaannya tidak konsisten.")
                model_rows = input_data[input_data["make"].fillna("").astype(str).eq(make) & input_data["model"].fillna("").astype(str).eq(model)]
                years_available = input_data.get("year", pd.Series(dtype=float)).dropna()
                min_year = max(1950, int(years_available.min()) if not years_available.empty else 1990)
                max_year = max(min_year, int(years_available.max()) if not years_available.empty else pd.Timestamp.now().year)
                year_value = int(_number(prefill.get("year", 2020), 2020))
                year = st.number_input("Tahun kendaraan", min_value=min_year, max_value=max(max_year, year_value), value=min(max(year_value, min_year), max(max_year, year_value)), step=1)
                km_default = int(model_rows["mileage_km"].median()) if "mileage_km" in model_rows and model_rows["mileage_km"].notna().any() else 50_000
                mileage = st.number_input("Kilometer", 0, 1_000_000, int(_number(prefill.get("mileage_km", km_default), km_default)), step=5_000)
                cc_default = int(model_rows["engine_cc"].median()) if "engine_cc" in model_rows and model_rows["engine_cc"].notna().any() else 1_300
                engine_cc = st.number_input("Kapasitas mesin (cc)", 0, 10_000, int(_number(prefill.get("engine_cc", cc_default), cc_default)), step=100)
                cat_a, cat_b = st.columns(2)
                transmission_options = ["Semua", *sorted(input_data.get("transmission", pd.Series(dtype=str)).dropna().astype(str).unique())]
                fuel_options = ["Semua", *sorted(input_data.get("fuel_type", pd.Series(dtype=str)).dropna().astype(str).unique())]
                body_options = ["Semua", *sorted(input_data.get("body_type", pd.Series(dtype=str)).dropna().astype(str).unique())]
                with cat_a:
                    trans_default = prefill.get("transmission") if prefill.get("transmission") in transmission_options else "Semua"
                    transmission = st.selectbox("Transmisi", transmission_options, index=transmission_options.index(trans_default))
                    fuel_default = prefill.get("fuel_type") if prefill.get("fuel_type") in fuel_options else "Semua"
                    fuel_type = st.selectbox("Bahan bakar", fuel_options, index=fuel_options.index(fuel_default))
                with cat_b:
                    body_default = prefill.get("body_type") if prefill.get("body_type") in body_options else "Semua"
                    body_type = st.selectbox("Tipe bodi", body_options, index=body_options.index(body_default))
                    price_max = max(50_000_000_000, int(_number(input_data.get("price", pd.Series(dtype=float)).max(), 0)))
                    asking_default = int(_number(prefill.get("price", 150_000_000), 150_000_000))
                asking_price = st.number_input("Harga iklan yang ingin dicek (Rp)", 1, price_max, min(max(asking_default, 1), price_max), step=5_000_000)
                submitted = st.form_submit_button("Cek harga", type="primary", icon=":material/price_check:", use_container_width=True)

            features = {
                "make": make, "model": model, "year": int(year), "mileage_km": int(mileage), "engine_cc": int(engine_cc),
                "transmission": transmission, "fuel_type": fuel_type, "body_type": body_type,
            }
            if submitted:
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
        st.markdown("### Hasil analisis harga")
        st.caption("Tiga referensi berbeda agar mudah dibaca: harga iklan, pembanding listing, dan estimasi model.")
        result = st.session_state.get("price_calculation_result")
        if result and result.get("source") != source:
            st.info("Sumber pembanding berubah. Tekan Cek harga lagi untuk menghitung hasil dengan sumber yang dipilih.")
        elif not result:
            with st.container(border=True):
                st.markdown("#### Mulai pengecekan")
                st.write("Pilih listing tersimpan atau isi detail mobil di sebelah kiri, lalu tekan **Cek harga**.")
                st.metric("Harga iklan", "—")
                st.metric("Pembanding serupa", "—")
                if not model_is_validated(load_model_metadata()):
                    st.caption("Estimasi model belum tersedia. Perbandingan listing tetap dapat digunakan.")
        else:
            asking = float(result["asking_price"])
            peers = result["peers"]
            estimate = result["estimate"]
            with st.container(border=True):
                st.markdown("#### Harga iklan yang dimasukkan")
                st.markdown(f"<div class='price-hero-value'>{format_rupiah(asking)}</div>", unsafe_allow_html=True)
            result_cols = st.columns(2, gap="small")
            with result_cols[0]:
                with st.container(border=True):
                    st.markdown("**Listing serupa**")
                    if peers.empty:
                        st.metric("Jumlah pembanding", "0")
                        st.caption(f"Tidak ada listing dari {source} yang cocok dengan rentang spesifikasi ini.")
                    else:
                        median = float(peers["price"].median())
                        low, high = float(peers["price"].min()), float(peers["price"].max())
                        st.metric("Median pembanding", format_rupiah(median))
                        st.caption(f"Rentang: {format_rupiah(low)} – {format_rupiah(high)} · {len(peers):,} listing".replace(",", "."))
                        st.caption(f"Harga masukan {_delta_text(asking, median)} dari median pembanding.")
            with result_cols[1]:
                with st.container(border=True):
                    st.markdown("**Estimasi model regresi**")
                    if estimate is None:
                        st.metric("Estimasi harga iklan", "—")
                        st.caption("Model belum dilatih atau belum lolos kriteria validasi. Angka prediksi tidak ditampilkan.")
                    else:
                        st.metric("Estimasi harga iklan", format_rupiah(estimate))
                        st.caption(f"Harga masukan {_delta_text(asking, estimate)} dari estimasi model.")
            if not peers.empty:
                if estimate is not None:
                    st.success(f"Dalam sumber pembanding yang dipilih, ada {len(peers):,} listing serupa. Harga yang dimasukkan {_delta_text(asking, median)}; estimasi model berbeda dan berasal dari arsip historis.".replace(",", "."))
                with st.expander(f"Lihat {len(peers):,} listing yang menjadi pembanding".replace(",", ".")):
                    st.dataframe(_comparable_table(peers.head(30)), hide_index=True, width="stretch", alt="Detail listing yang dipakai sebagai pembanding harga")
            st.caption("Pembanding mengikuti sumber yang dipilih. Model memakai arsip gabungan yang tervalidasi. Keduanya hanya merujuk harga iklan, bukan harga transaksi atau kondisi kendaraan.")

with st.expander("Metode dan evaluasi model"):
    st.write("Model ini memakai **supervised learning berupa regresi**: spesifikasi kendaraan menjadi masukan dan harga iklan historis menjadi target. Model diuji pada data holdout yang tidak dipakai ketika melatih model.")
    eligible, eligibility_message, model_data = training_eligibility(training_data)
    st.caption(f"Data latihan: {len(model_data):,} listing unik tervalidasi. {eligibility_message}".replace(",", "."))
    if st.button("Latih dan evaluasi model", disabled=not eligible, help="Menggunakan arsip Excel dan snapshot OLX tersimpan. Tidak memanggil Datawebot."):
        with st.spinner("Melatih dan membandingkan tiga model regresi…"):
            training_result = evaluate_regression_models(training_data)
        if training_result.get("status") == "ready":
            st.success(f"Evaluasi selesai. Model dengan MAE terendah: {training_result['best_model']}.")
        else:
            st.warning(training_result.get("message", "Model belum dapat dilatih."))
    metadata = load_model_metadata()
    trained_count = int(metadata.get("training_unique_listings", 0) or 0)
    if model_is_validated(metadata) and len(model_data) > trained_count:
        st.warning(f"Arsip memiliki {len(model_data):,} listing yang layak, sedangkan model terakhir dilatih dengan {trained_count:,}. Refresh tidak melatih ulang model; latih kembali secara manual untuk memasukkan data baru.".replace(",", "."))
    if metadata.get("models"):
        model_table = pd.DataFrame([{"Model": name, **metrics} for name, metrics in metadata["models"].items()])
        for column in ("MAE", "RMSE"):
            if column in model_table:
                model_table[column] = model_table[column].map(format_rupiah)
        if "R2" in model_table:
            model_table["R2"] = model_table["R2"].map(lambda value: f"{value:.3f}" if pd.notna(value) else "—")
        st.dataframe(model_table, hide_index=True, width="stretch", alt="Perbandingan metrik tiga model regresi harga iklan")
        st.caption("MAE adalah rata-rata selisih absolut prediksi; RMSE lebih peka pada kesalahan besar; R² merangkum variasi harga yang dijelaskan pada data uji. Metrik tidak menjamin akurasi untuk setiap mobil.")
    else:
        st.info("Evaluasi model belum tersimpan. Pelatihan hanya dapat dilakukan lewat tombol di atas setelah kriteria data minimum terpenuhi.")
    if Path(MODEL_PATH).exists() and model_is_validated(metadata):
        importance = get_feature_importance().head(15).rename(columns={"feature": "Fitur", "importance": "Skor relatif"})
        if not importance.empty:
            st.caption("Skor feature importance membantu menjelaskan fitur yang digunakan model. Nilai ini bukan persentase perubahan harga dan bukan sebab-akibat.")
            st.dataframe(importance, hide_index=True, width="stretch", alt="Skor relatif fitur pada model regresi")
        st.caption(f"Model aktif: {metadata.get('best_model', '—')} · {metadata.get('training_unique_listings', 0):,} listing unik saat pelatihan. Target: harga iklan historis, bukan harga transaksi.".replace(",", "."))
    else:
        st.info("Prediksi tidak ditampilkan sampai model dan evaluasinya tersedia serta lolos validasi.")
