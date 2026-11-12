"""Calculator for comparing an asking price with peers and a validated model."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.data_loader import (get_last_updated_text, load_historical_data, load_live_data,
                             load_combined_archive, load_training_archive)
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
        peers = peers[
            peers["mileage_km"].between(max(0, features["mileage_km"] - km_window), features["mileage_km"] + km_window)
            | peers["mileage_km"].isna()
        ]
    if "engine_cc" in peers and features["engine_cc"] > 0:
        peers = peers[
            peers["engine_cc"].between(features["engine_cc"] * 0.7, features["engine_cc"] * 1.3)
            | peers["engine_cc"].isna()
        ]
    for column in ("transmission", "fuel_type", "body_type"):
        selected = features.get(column, "Semua")
        if selected != "Semua" and column in peers:
            peers = peers[peers[column].fillna("").astype(str).eq(selected)]
    return peers.dropna(subset=["price"]).reset_index(drop=True)


def _comparable_table(data):
    """Build a display-only table with fixed string columns for Arrow safety."""
    labels = {
        "make": "Merek", "model": "Model", "variant": "Varian", "year": "Tahun",
        "price": "Harga iklan", "mileage_km": "Kilometer", "engine_cc": "Kapasitas mesin (cc)",
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
st.write("Masukkan spesifikasi mobil dan harga yang tercantum di iklan. AutoMatch akan membandingkannya dengan iklan serupa dan, jika tersedia, estimasi dari model historis.")
st.caption("Harga yang ditampilkan adalah harga penawaran. Hasil bukan taksiran harga transaksi, pemeriksaan kondisi kendaraan, atau rekomendasi membeli.")

live = load_live_data()
excel_archive = load_historical_data()
archive = load_combined_archive()
training_data = load_training_archive()
source = st.radio(
    "Sumber pembanding listing",
    ["Listing terbaru", "Arsip gabungan", "Dataset Excel"],
    horizontal=True,
    key="price_comparison_source",
    help="Sumber ini hanya mengubah pembanding listing; model tetap dilatih dari arsip historis DKI.",
)
comparison_data = live.copy() if source == "Listing terbaru" else excel_archive.copy() if source == "Dataset Excel" else archive.copy()
if source == "Listing terbaru":
    st.caption(f"Pembanding dari snapshot OLX · terakhir diperbarui {get_last_updated_text()}. Listing dapat berubah atau sudah tidak aktif saat dibuka.")
elif source == "Dataset Excel":
    st.caption(f"Pembanding dari dataset Excel · {len(comparison_data):,} listing. Tanggal pengambilan tidak tersedia; tautan mungkin sudah tidak aktif.".replace(",", "."))
else:
    st.caption(f"Pembanding dari arsip gabungan · {len(comparison_data):,} listing unik. Iklan arsip mungkin sudah tidak aktif.".replace(",", "."))

# Use archive specifications to keep the calculator usable if a live snapshot is empty.
input_data = comparison_data if not comparison_data.empty else training_data
for column in ("price", "year", "mileage_km", "engine_cc"):
    if column in input_data:
        input_data[column] = pd.to_numeric(input_data[column], errors="coerce")
makes = sorted(input_data.get("make", pd.Series(dtype=str)).dropna().astype(str).unique())
if input_data.empty or not makes:
    st.info("Belum ada data spesifikasi untuk kalkulator. Tambahkan arsip historis atau simpan snapshot listing terlebih dahulu.")
else:
    prefill = st.session_state.pop("price_checker_prefill", {})
    if prefill.get("make") in makes:
        st.session_state["calculator_make"] = prefill["make"]
    initial_make = st.session_state.get("calculator_make", makes[0])
    if initial_make not in makes:
        initial_make = makes[0]
    models = sorted(input_data.loc[input_data["make"].astype(str).eq(initial_make), "model"].dropna().astype(str).unique())
    if not models:
        models = sorted(input_data["model"].dropna().astype(str).unique())

    with st.form("price_calculator"):
        st.subheader("Detail mobil")
        make = st.selectbox("Merek", makes, key="calculator_make")
        available_models = sorted(input_data.loc[input_data["make"].astype(str).eq(make), "model"].dropna().astype(str).unique())
        if not available_models:
            available_models = models
        default_model = prefill.get("model") if prefill.get("model") in available_models else available_models[0]
        model_index = available_models.index(default_model)
        model = st.selectbox("Model", available_models, index=model_index)
        st.caption("Varian iklan tidak digunakan karena penamaannya belum konsisten.")

        model_rows = input_data[
            input_data["make"].fillna("").astype(str).eq(make)
            & input_data["model"].fillna("").astype(str).eq(model)
        ]
        years = input_data.get("year", pd.Series(dtype=float)).dropna()
        min_year = max(1950, int(years.min()) if not years.empty else 1990)
        max_year = max(min_year, int(years.max()) if not years.empty else pd.Timestamp.now().year)
        entered_year = int(_number(prefill.get("year", 2020), 2020))
        year = st.number_input("Tahun kendaraan", min_value=min_year, max_value=max(max_year, entered_year), value=min(max(entered_year, min_year), max(max_year, entered_year)), step=1)
        km_default = int(model_rows["mileage_km"].median()) if "mileage_km" in model_rows and model_rows["mileage_km"].notna().any() else 50_000
        mileage = st.number_input("Kilometer", min_value=0, max_value=1_000_000, value=int(_number(prefill.get("mileage_km", km_default), km_default)), step=5_000)
        cc_default = int(model_rows["engine_cc"].median()) if "engine_cc" in model_rows and model_rows["engine_cc"].notna().any() else 1_300
        engine_cc = st.number_input("Kapasitas mesin (cc)", min_value=0, max_value=10_000, value=int(_number(prefill.get("engine_cc", cc_default), cc_default)), step=100)

        col_a, col_b = st.columns(2)
        transmission_values = sorted(input_data.get("transmission", pd.Series(dtype=str)).dropna().astype(str).unique())
        fuel_values = sorted(input_data.get("fuel_type", pd.Series(dtype=str)).dropna().astype(str).unique())
        body_values = sorted(input_data.get("body_type", pd.Series(dtype=str)).dropna().astype(str).unique())
        transmission_options = ["Semua", *transmission_values]
        fuel_options = ["Semua", *fuel_values]
        body_options = ["Semua", *body_values]
        with col_a:
            transmission_default = prefill.get("transmission") if prefill.get("transmission") in transmission_options else "Semua"
            transmission = st.selectbox("Transmisi", transmission_options, index=transmission_options.index(transmission_default))
        with col_b:
            fuel_default = prefill.get("fuel_type") if prefill.get("fuel_type") in fuel_options else "Semua"
            fuel_type = st.selectbox("Bahan bakar", fuel_options, index=fuel_options.index(fuel_default))
        body_default = prefill.get("body_type") if prefill.get("body_type") in body_options else "Semua"
        body_type = st.selectbox("Tipe bodi", body_options, index=body_options.index(body_default))
        price_max = max(50_000_000_000, int(_number(input_data.get("price", pd.Series(dtype=float)).max(), 0)))
        asking_default = int(_number(prefill.get("price", 150_000_000), 150_000_000))
        asking_price = st.number_input("Harga iklan yang ingin dicek (Rp)", min_value=1, max_value=price_max, value=min(max(asking_default, 1), price_max), step=5_000_000)
        submitted = st.form_submit_button("Cek harga", type="primary", icon=":material/price_check:")

    feature_values = {
        "make": make, "model": model, "year": int(year), "mileage_km": int(mileage),
        "engine_cc": int(engine_cc), "transmission": transmission, "fuel_type": fuel_type, "body_type": body_type,
    }
    if submitted:
        peers = _find_comparables(comparison_data, feature_values)
        estimate = None
        metadata = load_model_metadata()
        if Path(MODEL_PATH).exists() and model_is_validated(metadata):
            model_features = dict(feature_values)
            for category in ("transmission", "fuel_type", "body_type"):
                if model_features[category] == "Semua":
                    mode = model_rows[category].dropna().astype(str).mode() if category in model_rows else pd.Series(dtype=str)
                    model_features[category] = mode.iloc[0] if not mode.empty else ""
            try:
                estimate = predict_asking_price(model_features)
            except (ValueError, FileNotFoundError, OSError) as exc:
                st.session_state["price_calculation_error"] = str(exc)
            else:
                st.session_state.pop("price_calculation_error", None)
        st.session_state["price_calculation_result"] = {
            "source": source,
            "asking_price": int(asking_price),
            "estimate": estimate,
            "peers": peers,
        }

    result = st.session_state.get("price_calculation_result")
    if result and result.get("source") != source:
        st.info("Sumber pembanding berubah. Tekan **Cek harga** lagi untuk menghitung ulang dengan sumber yang dipilih.")
    elif result:
        st.markdown("---")
        st.subheader("Hasil pengecekan")
        st.metric("Harga iklan yang dimasukkan", format_rupiah(result["asking_price"]))
        peers = result["peers"]
        estimate = result["estimate"]
        if estimate is None:
            st.info("Estimasi model belum tersedia karena model belum dilatih atau belum lolos kriteria validasi. Hasil pembanding listing tetap dapat digunakan.")
        else:
            st.metric("Estimasi harga dari model", format_rupiah(estimate), delta=_delta_text(result["asking_price"], estimate), delta_color="off")
            st.caption("Model regresi menggunakan dataset historis DKI Jakarta untuk memperkirakan harga iklan. Ini bukan harga transaksi.")
        if peers.empty:
            st.info(f"Tidak ada listing pembanding yang memenuhi kriteria dari sumber **{source}**. Coba ubah spesifikasi atau pilih sumber lain.")
        else:
            median = float(peers["price"].median())
            low, high = float(peers["price"].min()), float(peers["price"].max())
            metrics = st.columns(4)
            metrics[0].metric("Median listing serupa", format_rupiah(median))
            metrics[1].metric("Rentang harga listing", f"{format_rupiah(low)} – {format_rupiah(high)}")
            metrics[2].metric("Jumlah pembanding", f"{len(peers):,}".replace(",", "."))
            metrics[3].metric("Selisih dari median", _delta_text(result["asking_price"], median), delta_color="off")
            st.caption(f"Pembanding ini berasal dari **{source}** saja. Hasil model di atas menggunakan arsip historis tersendiri; kedua sumber tidak digabungkan.")
            st.dataframe(_comparable_table(peers.head(20)), hide_index=True, width="stretch", alt="Detail listing yang dipakai sebagai pembanding harga")
        st.caption("Angka hanya membantu memberi konteks pada harga yang tercantum. Periksa kondisi kendaraan, riwayat servis, dokumen, dan ketersediaan iklan secara langsung.")

with st.expander("Metode dan evaluasi model"):
    st.write("Model menggunakan **supervised learning (regresi)**: spesifikasi kendaraan menjadi masukan, sedangkan harga iklan historis menjadi target yang dipelajari. Data evaluasi ditahan dari proses pelatihan untuk mengukur kemampuan model pada data yang belum dilihat.")
    eligible, eligibility_message, model_data = training_eligibility(training_data)
    st.caption(f"Data latihan: {len(model_data):,} listing historis unik yang lolos validasi. {eligibility_message}".replace(",", "."))
    if st.button("Latih dan evaluasi model", disabled=not eligible, help="Menggunakan arsip Excel dan snapshot OLX tersimpan; tidak memanggil API."):
        with st.spinner("Melatih tiga model regresi dan mengevaluasi data uji…"):
            training_result = evaluate_regression_models(training_data)
        if training_result.get("status") == "ready":
            st.success(f"Evaluasi selesai. Model dengan MAE terendah: {training_result['best_model']}.")
        else:
            st.warning(training_result.get("message", "Model belum dapat dilatih."))
    metadata = load_model_metadata()
    trained_count = int(metadata.get("training_unique_listings", 0) or 0)
    if model_is_validated(metadata) and len(model_data) > trained_count:
        st.warning(
            f"Arsip kini berisi {len(model_data):,} listing unik yang layak, sedangkan model terakhir dilatih dengan {trained_count:,}. "
            "Refresh tidak melatih ulang model; tekan tombol di atas untuk memasukkan data baru.".replace(",", ".")
        )
    if metadata.get("models"):
        model_table = pd.DataFrame([{"Model": name, **metrics} for name, metrics in metadata["models"].items()])
        for column in ("MAE", "RMSE"):
            if column in model_table:
                model_table[column] = model_table[column].map(format_rupiah)
        if "R2" in model_table:
            model_table["R2"] = model_table["R2"].map(lambda value: f"{value:.3f}" if pd.notna(value) else "—")
        st.dataframe(model_table, hide_index=True, width="stretch", alt="Perbandingan metrik evaluasi tiga model regresi harga iklan")
        st.caption("MAE: rata-rata besar selisih absolut prediksi dan harga aktual pada data uji. RMSE: ukuran kesalahan yang lebih sensitif pada selisih besar. R²: proporsi variasi target yang dijelaskan model pada data uji; mendekati 1 lebih baik, tetapi bukan jaminan akurasi untuk setiap mobil.")
    else:
        st.info("Evaluasi model belum tersimpan. Latih model setelah kriteria data minimum terpenuhi.")
    if Path(MODEL_PATH).exists() and model_is_validated(metadata):
        importance = get_feature_importance()
        if not importance.empty:
            importance = importance.head(15).rename(columns={"feature": "Fitur", "importance": "Skor relatif"})
            st.caption("Informasi untuk laporan: skor relatif menunjukkan fitur yang sering dipakai model. Ini bukan persentase perubahan harga dan bukan bukti sebab-akibat.")
            st.dataframe(importance, hide_index=True, width="stretch", alt="Urutan skor relatif fitur pada model regresi")
        st.caption(f"Model aktif: {metadata.get('best_model', '—')} · {metadata.get('training_unique_listings', 0):,} listing unik saat pelatihan. Target model adalah harga iklan historis, bukan harga transaksi.".replace(",", "."))
    else:
        st.info("Prediksi tidak ditampilkan sampai model dan evaluasinya tersedia serta lolos kriteria validasi.")
