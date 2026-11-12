"""Transparent listing comparables and opt-in asking-price model workflow."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.data_loader import get_last_updated_text, load_historical_data, load_live_data
from src.modeling import (FEATURES, MODEL_PATH, evaluate_regression_models,
                          get_feature_importance, load_model_metadata,
                          model_is_validated, predict_asking_price,
                          training_eligibility)
from src.styles import apply_theme
from src.ui import format_rupiah, render_empty_state

apply_theme()
st.title("Cek Harga Iklan")
st.caption("Bandingkan harga yang kamu temukan dengan iklan serupa yang tersimpan. Harga iklan bukan harga transaksi dan bukan penilaian kondisi kendaraan.")
st.info("Ada dua hal berbeda di halaman ini: **pembanding listing serupa** (ringkasan iklan nyata yang tersimpan) dan **estimasi model** (prediksi supervised learning yang hanya muncul jika data dan evaluasi memenuhi syarat).")
live, historical = load_live_data(), load_historical_data()
source_options = []
if not live.empty:
    source_options.append("Listing terbaru")
if not historical.empty:
    source_options.append("Arsip historis")
if len(source_options) > 1:
    comparison_source = st.radio("Bandingkan menggunakan", source_options, horizontal=True, key="price_comparison_source")
else:
    comparison_source = source_options[0] if source_options else "Listing terbaru"
comparison_data = live if comparison_source == "Listing terbaru" else historical
if comparison_source == "Listing terbaru":
    st.caption(f"Sumber pembanding: snapshot OLX · terakhir diperbarui {get_last_updated_text()}. Listing mungkin sudah tidak aktif.")
elif comparison_source == "Arsip historis":
    st.caption("Sumber pembanding: arsip historis DKI. Tanggal pengambilan tidak tersedia; iklan atau tautannya mungkin sudah tidak aktif.")

if not comparison_data.empty:
    comparison_data = comparison_data.copy()
    for col in ["price", "year", "mileage_km", "engine_cc"]:
        if col in comparison_data: comparison_data[col] = pd.to_numeric(comparison_data[col], errors="coerce")
    prefill = st.session_state.pop("price_checker_prefill", {})
    st.subheader("1 · Bandingkan dengan iklan serupa")
    makes = sorted(comparison_data["make"].dropna().astype(str).unique())
    if prefill.get("make") in makes:
        st.session_state["price_make"] = prefill["make"]
    if st.session_state.get("price_make") not in makes:
        st.session_state["price_make"] = makes[0]
    make = st.selectbox("Merek kendaraan", makes, key="price_make")
    models = sorted(comparison_data.loc[comparison_data["make"].astype(str).eq(make), "model"].dropna().astype(str).unique())
    if prefill.get("model") in models:
        st.session_state["price_model"] = prefill["model"]
    if st.session_state.get("price_model") not in models:
        st.session_state["price_model"] = models[0]
    model = st.selectbox("Model kendaraan", models, key="price_model")
    selected_model_rows = comparison_data[comparison_data["make"].astype(str).eq(make) & comparison_data["model"].astype(str).eq(model)]
    variant = st.text_input("Varian (opsional)")
    st.caption("Varian membantu konteks pembanding; v1 tidak memakai varian sebagai fitur model karena penamaan iklan belum konsisten.")
    years_data = comparison_data["year"].dropna()
    y_min = int(years_data.min()) if not years_data.empty else 1990
    y_max = max(int(years_data.max()) if not years_data.empty else y_min, y_min)
    year_default = min(y_max, max(y_min, 2020))
    year_value = int(prefill.get("year", year_default))
    year_value = min(max(year_value, max(1950, y_min - 20)), max(y_max + 5, y_min))
    st.session_state["price_year"] = year_value if prefill else st.session_state.get("price_year", year_default)
    year = st.number_input("Tahun kendaraan", min_value=max(1950, y_min - 20), max_value=max(y_max + 5, y_min), key="price_year")
    km_default = int(selected_model_rows["mileage_km"].median()) if selected_model_rows["mileage_km"].notna().any() else 50000
    st.session_state["price_mileage"] = int(prefill.get("mileage_km", st.session_state.get("price_mileage", km_default))) if prefill else st.session_state.get("price_mileage", km_default)
    mileage = st.number_input("Kilometer", min_value=0, max_value=1_000_000, key="price_mileage", step=5000)
    engine_default = int(selected_model_rows["engine_cc"].median()) if selected_model_rows["engine_cc"].notna().any() else 1300
    st.session_state["price_engine_cc"] = int(prefill.get("engine_cc", st.session_state.get("price_engine_cc", engine_default))) if prefill else st.session_state.get("price_engine_cc", engine_default)
    engine_cc = st.number_input("Kapasitas mesin (cc)", min_value=0, max_value=10000, key="price_engine_cc", step=100)
    left, right = st.columns(2)
    transmission_options = ["Semua", *sorted(comparison_data["transmission"].dropna().astype(str).unique())]
    fuel_options = ["Semua", *sorted(comparison_data["fuel_type"].dropna().astype(str).unique())]
    body_options = ["Semua", *sorted(comparison_data["body_type"].dropna().astype(str).unique())]
    if prefill.get("transmission") in transmission_options: st.session_state["price_transmission"] = prefill["transmission"]
    if prefill.get("fuel_type") in fuel_options: st.session_state["price_fuel"] = prefill["fuel_type"]
    if prefill.get("body_type") in body_options: st.session_state["price_body"] = prefill["body_type"]
    with left: transmission = st.selectbox("Transmisi", transmission_options, key="price_transmission")
    with right: fuel_type = st.selectbox("Bahan bakar", fuel_options, key="price_fuel")
    body_type = st.selectbox("Tipe bodi", body_options, key="price_body")
    ask_price_max = max(50_000_000_000, int(comparison_data["price"].max()) if comparison_data["price"].notna().any() else 0)
    ask_default = int(prefill.get("price", 150_000_000)) if prefill else 150_000_000
    if prefill:
        st.session_state["price_asking"] = min(max(ask_default, 0), ask_price_max)
    elif "price_asking" not in st.session_state:
        st.session_state["price_asking"] = min(150_000_000, ask_price_max)
    ask_price = st.number_input("Harga iklan yang ingin diperiksa (Rp)", min_value=0, max_value=ask_price_max, key="price_asking", step=5_000_000)

    # Transparent comparator window: exact make/model, +/-2 years and +/-40% km (at least 20,000 km).
    comps = selected_model_rows[selected_model_rows["year"].between(year - 2, year + 2)]
    comps = comps[comps["mileage_km"].between(max(0, mileage - max(20_000, mileage * .4)), mileage + max(20_000, mileage * .4)) | comps["mileage_km"].isna()]
    comps = comps[(comps["engine_cc"].between(engine_cc * .7, engine_cc * 1.3)) | comps["engine_cc"].isna()] if engine_cc else comps
    for col, value in [("transmission", transmission), ("fuel_type", fuel_type), ("body_type", body_type)]:
        if value != "Semua": comps = comps[comps[col].astype(str).eq(value)]
    comps = comps.dropna(subset=["price"])
    variant_applied = False
    if variant.strip() and "variant" in comps:
        variant_matches = comps[comps["variant"].fillna("").astype(str).str.contains(variant.strip(), case=False, regex=False)]
        if len(variant_matches) >= 3:
            comps, variant_applied = variant_matches, True
    variant_note = "Varian dicocokkan sebagian." if variant_applied else ("Varian tidak membatasi hasil karena terlalu sedikit kecocokan; pembanding model yang lebih luas digunakan." if variant.strip() else "")
    st.caption("Kriteria: merek/model sama; tahun ±2; kilometer ±40% (minimal rentang ±20.000 km); kapasitas mesin ±30% jika diisi; kategori opsional dicocokkan persis. " + variant_note)
    if len(comps) < 3:
        st.warning(f"Hanya {len(comps)} listing pembanding dari sumber yang dipilih; referensi mungkin kurang stabil.")
    if comps.empty:
        st.info("Belum ada listing pembanding yang memenuhi kriteria.")
    else:
        median = comps["price"].median()
        delta = ask_price - median
        cols = st.columns(4)
        cols[0].metric("Median pembanding", format_rupiah(median))
        cols[1].metric("Rentang listing", f"{format_rupiah(comps['price'].min())} – {format_rupiah(comps['price'].max())}")
        cols[2].metric("Jumlah pembanding", len(comps))
        cols[3].metric("Selisih dari median", f"{format_rupiah(delta)} ({delta / median * 100:+.1f}%)" if median else "-")
        fields = [c for c in ["make", "model", "variant", "year", "price", "mileage_km", "engine_cc", "transmission", "fuel_type", "body_type", "location"] if c in comps]
        st.dataframe(comps[fields].head(20), width="stretch")
else:
    st.info("Belum ada data untuk sumber pembanding yang dipilih. Model dan metrik tersimpan tetap dapat dilihat di bawah.")

st.markdown("---")
st.subheader("2 · Estimasi harga iklan berbasis model")
metadata = load_model_metadata()
eligible, eligibility_message, model_data = training_eligibility(historical)
if not eligible:
    st.info(f"Model belum dilatih: {eligibility_message} Pengumpulan data dan validasi masih diperlukan.")
else:
    st.write(f"Tersedia {len(model_data):,} listing historis unik DKI yang memenuhi kriteria minimum.".replace(",", "."))
if st.button("Latih dan evaluasi model", disabled=not eligible, help="Menggunakan riwayat tersimpan; tidak memanggil API."):
    with st.spinner("Melatih dan mengevaluasi tiga model pada dataset historis…"):
        result = evaluate_regression_models(historical)
    if result.get("status") == "ready":
        st.success(f"Evaluasi selesai. Model terpilih berdasarkan holdout MAE: {result['best_model']}.")
        metadata = result
    else:
        st.warning(result.get("message", "Model belum dapat dilatih."))

metadata = load_model_metadata() or metadata
if Path(MODEL_PATH).exists() and model_is_validated(metadata):
    st.caption(f"Model tersimpan: {metadata.get('best_model')} · {metadata.get('training_unique_listings', 'n/a')} listing unik · dipilih berdasarkan MAE holdout terendah.")
    if metadata.get("models"):
        st.dataframe(pd.DataFrame([{"Model": n, **m} for n, m in metadata["models"].items()]), hide_index=True, width="stretch")
    if not comparison_data.empty:
        prediction_inputs = {
            "make": make, "model": model, "year": year, "mileage_km": mileage,
            "engine_cc": engine_cc,
            "transmission": transmission if transmission != "Semua" else (selected_model_rows["transmission"].mode().iloc[0] if selected_model_rows["transmission"].notna().any() else ""),
            "fuel_type": fuel_type if fuel_type != "Semua" else (selected_model_rows["fuel_type"].mode().iloc[0] if selected_model_rows["fuel_type"].notna().any() else ""),
            "body_type": body_type if body_type != "Semua" else (selected_model_rows["body_type"].mode().iloc[0] if selected_model_rows["body_type"].notna().any() else ""),
        }
        if st.button("Tampilkan estimasi model"):
            try:
                estimate = predict_asking_price(prediction_inputs)
                st.metric("Estimasi model", format_rupiah(estimate))
            except (ValueError, FileNotFoundError, OSError) as exc:
                st.error(f"Prediksi tidak tersedia: {exc}")
    importance = get_feature_importance()
    if not importance.empty:
        st.markdown("**Feature importance (asosiasi, bukan sebab-akibat)**")
        st.dataframe(importance.head(15), hide_index=True, width="stretch")
    st.caption("Prediksi merupakan referensi analitis harga iklan, bukan jaminan harga transaksi atau rekomendasi kelayakan kendaraan.")
else:
    st.info("Prediksi tidak ditampilkan: model belum memiliki metadata validasi versi saat ini atau belum memenuhi ambang data.")
