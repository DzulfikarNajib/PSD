"""Help buyers search and compare the latest saved DKI Jakarta listings."""

import pandas as pd
import streamlit as st

from src.car_search import compare_listings, filter_listings
from src.data_loader import get_last_updated_text, load_historical_data, load_live_data
from src.styles import apply_theme
from src.ui import format_km, format_rupiah, render_empty_state

apply_theme()
st.title("Temukan mobil yang cocok")
latest, archive = load_live_data(), load_historical_data()
if latest.empty and archive.empty:
    render_empty_state("Belum ada data mobil", "Listing terbaru muncul setelah refresh manual; arsip historis memerlukan dataset Excel di folder data.")
    st.stop()
source_choice = st.radio("Pilih sumber mobil", ["Listing terbaru", "Arsip historis"], horizontal=True, key="car_source_choice")
if source_choice == "Listing terbaru":
    cars = latest.copy()
    st.caption(f"Snapshot OLX terakhir: {get_last_updated_text()}. Listing terlihat saat refresh dan belum tentu masih aktif.")
else:
    cars = archive.copy()
    st.caption(f"Arsip dataset historis · {len(cars):,} listing DKI. Tanggal pengambilan tidak tersedia; iklan atau tautan mungkin sudah tidak aktif.".replace(",", "."))
if cars.empty:
    st.info("Belum ada data pada sumber ini. Pilih sumber lainnya atau perbarui listing secara manual dari Beranda.")
    st.stop()
for col in ["price", "year", "mileage_km", "engine_cc"]:
    if col in cars:
        cars[col] = pd.to_numeric(cars[col], errors="coerce")

with st.sidebar:
    st.subheader("Kebutuhan mobil")
    st.caption("Filter hanya membaca data tersimpan; tidak memakai kredit API.")
    price_max = int(cars["price"].max()) if cars["price"].notna().any() else 1_000_000_000
    budget_max = max(price_max, 50_000_000_000, 10_000_000)
    budget = st.slider("Anggaran (Rp)", 0, budget_max, (0, budget_max), step=5_000_000, format="Rp %d")
    brand_values = sorted(cars["make"].dropna().astype(str).unique()) if "make" in cars else []
    pending_make = st.session_state.pop("prefill_make", None)
    if pending_make in brand_values:
        st.session_state["search_make"] = pending_make
    brand = st.selectbox("Merek", ["Semua", *brand_values], key="search_make")
    subset = cars if brand == "Semua" else cars[cars["make"].astype(str).eq(brand)]
    model_values = sorted(subset["model"].dropna().astype(str).unique()) if "model" in subset else []
    model = st.selectbox("Model", ["Semua", *model_values])
    year_low = int(cars["year"].min()) if cars["year"].notna().any() else 1990
    year_high = int(cars["year"].max()) if cars["year"].notna().any() else pd.Timestamp.now().year
    year_high = max(year_high, year_low + 1)
    years = st.slider("Tahun", year_low, year_high, (year_low, year_high))
    mileage_default = int(cars["mileage_km"].max()) if cars["mileage_km"].notna().any() else 300_000
    mileage_limit = st.number_input("Kilometer maksimum", 0, max(mileage_default, 1), min(150_000, max(mileage_default, 1)), step=5_000)
    cc_max = int(cars["engine_cc"].max()) if cars["engine_cc"].notna().any() else 6_000
    cc_max = max(cc_max, 100)
    engine_range = st.slider("Kapasitas mesin (cc)", 0, cc_max, (0, cc_max), step=100)
    def select_category(column, label):
        options = sorted(cars[column].dropna().astype(str).unique()) if column in cars else []
        key = {"fuel_type": "search_fuel", "transmission": "search_transmission", "body_type": "search_body"}.get(column, f"search_{column}")
        if column == "fuel_type":
            pending_fuel = st.session_state.pop("prefill_fuel", None)
            if pending_fuel in options:
                st.session_state[key] = pending_fuel
        return st.selectbox(label, ["Semua", *options], key=key)
    fuel = select_category("fuel_type", "Bahan bakar")
    transmission = select_category("transmission", "Transmisi")
    body = select_category("body_type", "Tipe bodi")

filtered = filter_listings(
    cars, budget=budget, make=None if brand == "Semua" else brand,
    model=None if model == "Semua" else model, years=years,
    max_mileage=mileage_limit, engine_range=engine_range,
    categories={"fuel_type": fuel, "transmission": transmission, "body_type": body},
)
query = st.text_input("Cari kata kunci", placeholder="Contoh: Avanza, SUV, Jakarta Selatan")
if query.strip():
    searchable = [c for c in ["make", "model", "variant", "location", "location_normalized"] if c in filtered]
    if searchable:
        mask = pd.Series(False, index=filtered.index)
        for column in searchable:
            mask |= filtered[column].fillna("").astype(str).str.contains(query.strip(), case=False, regex=False)
        filtered = filtered[mask]

sort = st.selectbox("Urutkan hasil", ["Harga terendah", "Harga tertinggi", "Tahun terbaru", "Kilometer terendah"])
sort_col, ascending = {"Harga terendah": ("price", True), "Harga tertinggi": ("price", False), "Tahun terbaru": ("year", False), "Kilometer terendah": ("mileage_km", True)}[sort]
filtered = filtered.sort_values(sort_col, ascending=ascending, na_position="last")
unique_matches = filtered["listing_id"].nunique() if "listing_id" in filtered else len(filtered)
st.markdown(f"### {unique_matches} mobil cocok")
st.caption(f"Sumber: {source_choice} · {len(cars):,} baris sebelum filter.".replace(",", "."))
if filtered.empty:
    st.info("Belum ada hasil yang cocok. Coba longgarkan anggaran, rentang tahun, atau filter spesifikasi.")
    st.stop()

ids = filtered["listing_id"].astype(str).tolist() if "listing_id" in filtered else []
if ids:
    label_map = {}
    for _, row in filtered.iterrows():
        label_map[str(row["listing_id"])] = f"{row.get('make', '')} {row.get('model', '')} · {row.get('year', 'tahun -')} · {format_rupiah(row.get('price'))}"
    selected = st.multiselect("Pilih 2–3 mobil untuk dibandingkan", ids, max_selections=3, format_func=lambda value: label_map.get(value, value))
    if len(selected) >= 2:
        comparison = compare_listings(filtered, selected)
        st.subheader("Perbandingan mobil")
        if not comparison.empty:
            st.dataframe(comparison, width="stretch", alt="Tabel perbandingan spesifikasi mobil yang dipilih")
        st.caption("Selisih harga/spesifikasi tidak menjamin kondisi kendaraan. Periksa langsung dan minta riwayat servis serta dokumen.")
        price_check_id = st.selectbox("Pilih salah satu untuk cek konteks harganya", selected, format_func=lambda value: label_map.get(value, value), key="selected_price_check")
        if st.button("Lanjut ke Cek Harga Iklan", icon=":material/price_check:"):
            chosen = filtered[filtered["listing_id"].astype(str).eq(price_check_id)].iloc[0]
            prefill_fields = ["make", "model", "year", "mileage_km", "engine_cc", "fuel_type", "transmission", "body_type", "price"]
            st.session_state["price_checker_prefill"] = {
                key: (None if pd.isna(chosen.get(key)) else chosen.get(key)) for key in prefill_fields
            }
            st.switch_page("pages/3_Price_Checker.py")
    elif selected:
        st.caption("Pilih satu mobil lagi untuk melihat perbandingan.")

st.subheader("Iklan yang sesuai")
for _, row in filtered.head(30).iterrows():
    with st.container(border=True):
        photo, details = st.columns([1, 2.5], vertical_alignment="center")
        image_url = row.get("image_url")
        with photo:
            if pd.notna(image_url) and str(image_url).startswith("http"):
                st.image(str(image_url), caption="Foto dari iklan OLX", width="stretch")
            else:
                st.markdown("<div class='car-photo-fallback'><span>🚘</span><small>Foto tidak tersedia</small></div>", unsafe_allow_html=True)
        with details:
            st.markdown(f"#### {row.get('make') or 'Merek tidak dicantumkan'} {row.get('model') or ''}")
            st.markdown(f"<div class='car-price'>{format_rupiah(row.get('price'))}</div>", unsafe_allow_html=True)
            st.caption(str(row.get("variant") or "Varian tidak dicantumkan"))
            spec_cols = st.columns(3)
            spec_values = [
                ("Tahun", f"{row.get('year'):.0f}" if pd.notna(row.get("year")) else "-") ,
                ("Kilometer", format_km(row.get("mileage_km"))),
                ("Bahan bakar", str(row.get("fuel_type") or "-")),
                ("Transmisi", str(row.get("transmission") or "-")),
                ("Mesin", f"{row.get('engine_cc'):.0f} cc" if pd.notna(row.get("engine_cc")) else "-"),
                ("Lokasi", str(row.get("location_normalized") or row.get("location") or "-")),
            ]
            for idx, (label, value) in enumerate(spec_values):
                with spec_cols[idx % 3]:
                    st.caption(label)
                    st.write(value)
            url = row.get("url")
            if pd.notna(url) and str(url).startswith("http"):
                st.link_button("Lihat iklan dan hubungi penjual", str(url), icon=":material/open_in_new:")
            else:
                st.caption("Tautan sumber tidak tersedia pada data ini.")

if source_choice == "Arsip historis":
    st.warning("Hasil ini adalah referensi arsip, bukan stok aktif. Tanggal pengambilan tidak tersedia dan sebagian tautan mungkin sudah tidak berfungsi.")
else:
    st.caption("Listing terlihat pada snapshot terakhir, tetapi ketersediaan dapat berubah. Dashboard tidak memeriksa kondisi fisik, status dokumen, atau harga transaksi.")
