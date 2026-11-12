"""Search saved listings in a marketplace-style layout without paid API calls."""

import pandas as pd
import streamlit as st

from src.car_search import compare_listings, filter_listings
from src.data_loader import get_last_updated_text, load_combined_archive, load_live_data
from src.styles import apply_theme
from src.ui import format_km, format_rupiah, render_empty_state


apply_theme()
st.title("Cari Mobil")
st.caption("Temukan mobil dari data yang tersimpan, lalu bandingkan pilihan sebelum membuka iklan sumber.")

latest, archive = load_live_data(), load_combined_archive()
if latest.empty and archive.empty:
    render_empty_state("Belum ada data mobil", "Listing terbaru muncul setelah refresh manual; arsip penuh memerlukan dataset Excel atau snapshot OLX tersimpan.")
    st.stop()

source_choice = st.radio(
    "Sumber listing",
    ["Arsip Penuh", "Listing Terbaru"],
    horizontal=True,
    key="car_source_choice",
    help="Arsip penuh menggabungkan Excel dan seluruh snapshot OLX tersimpan. Listing terbaru hanya membaca snapshot terakhir.",
)
cars = archive.copy() if source_choice == "Arsip Penuh" else latest.copy()
if cars.empty:
    st.info("Belum ada data pada sumber ini. Pilih Arsip Penuh atau lakukan refresh manual untuk memperoleh listing terbaru.")
    st.stop()
for column in ("price", "year", "mileage_km", "engine_cc"):
    if column in cars:
        cars[column] = pd.to_numeric(cars[column], errors="coerce")

if source_choice == "Listing Terbaru":
    st.caption(f"Snapshot OLX terakhir: {get_last_updated_text()} · iklan yang tampil mungkin sudah berubah atau tidak aktif.")
else:
    origins = cars.get("source_origins", pd.Series("", index=cars.index)).fillna("")
    excel_count = int(origins.str.contains("Dataset Excel", regex=False).sum())
    olx_count = int(origins.str.contains("Arsip snapshot OLX", regex=False).sum())
    st.caption(f"Arsip Penuh · {cars['listing_id'].nunique():,} mobil unik · ditemukan di Excel {excel_count:,} · juga ditemukan di snapshot OLX {olx_count:,}. Sumber dapat tumpang tindih; iklan arsip mungkin sudah tidak aktif.".replace(",", "."))

brand_values = sorted(cars["make"].dropna().astype(str).unique()) if "make" in cars else []
pending_make = st.session_state.pop("prefill_make", None)
if pending_make in brand_values:
    st.session_state["filter_make"] = pending_make
    st.session_state["applied_car_filters"] = None
if st.session_state.get("filter_make", "Semua") not in ["Semua", *brand_values]:
    st.session_state["filter_make"] = "Semua"

model_values = sorted(cars["model"].dropna().astype(str).unique()) if "model" in cars else []
fuel_values = sorted(cars["fuel_type"].dropna().astype(str).unique()) if "fuel_type" in cars else []
pending_fuel = st.session_state.pop("prefill_fuel", None)
if pending_fuel in fuel_values:
    st.session_state["filter_fuel"] = pending_fuel
    st.session_state["applied_car_filters"] = None
transmission_values = sorted(cars["transmission"].dropna().astype(str).unique()) if "transmission" in cars else []
body_values = sorted(cars["body_type"].dropna().astype(str).unique()) if "body_type" in cars else []

def _reset_filters():
    st.session_state["filter_budget_min"] = 0
    st.session_state["filter_budget_max"] = budget_ceiling
    st.session_state["filter_make"] = "Semua"
    st.session_state["filter_model"] = "Semua"
    st.session_state["filter_years"] = (1950, pd.Timestamp.now().year + 1)
    st.session_state["filter_mileage"] = 2_000_000
    st.session_state["filter_engine"] = (0, 10_000)
    st.session_state["filter_fuel"] = "Semua"
    st.session_state["filter_transmission"] = "Semua"
    st.session_state["filter_body"] = "Semua"
    st.session_state["applied_car_filters"] = None


left, right = st.columns([.9, 2.1], gap="large", vertical_alignment="top")
with left:
    with st.container(border=True):
        st.markdown("#### Filter Pencarian")
        st.caption("Filter hanya memakai listing tersimpan; tidak mengirim permintaan API.")
        make_options = ["Semua", *brand_values]
        model_options = ["Semua", *model_values]
        if st.session_state.get("filter_model", "Semua") not in model_options:
            st.session_state["filter_model"] = "Semua"
        year_end = pd.Timestamp.now().year + 1
        if st.session_state.get("filter_years", (1950, year_end))[1] > year_end:
            st.session_state["filter_years"] = (1950, year_end)
        budget_ceiling = max(50_000_000_000, int(cars["price"].max()) if "price" in cars and cars["price"].notna().any() else 50_000_000_000)
        with st.form("car_filters_form"):
            budget_cols = st.columns(2)
            budget_min = budget_cols[0].number_input("Anggaran min (Rp)", 0, budget_ceiling, 0, step=5_000_000, key="filter_budget_min")
            budget_max = budget_cols[1].number_input("Anggaran maks (Rp)", 0, budget_ceiling, budget_ceiling, step=5_000_000, key="filter_budget_max")
            make = st.selectbox("Merek", make_options, key="filter_make")
            model = st.selectbox("Model", model_options, key="filter_model")
            years = st.slider("Tahun", 1950, year_end, (1950, year_end), key="filter_years")
            mileage = st.number_input("Kilometer maksimum", 0, 2_000_000, 2_000_000, step=5_000, key="filter_mileage")
            engine_range = st.slider("Kapasitas mesin (cc)", 0, 10_000, (0, 10_000), step=100, key="filter_engine")
            fuel = st.selectbox("Bahan bakar", ["Semua", *fuel_values], key="filter_fuel")
            transmission = st.selectbox("Transmisi", ["Semua", *transmission_values], key="filter_transmission")
            body = st.selectbox("Tipe bodi", ["Semua", *body_values], key="filter_body")
            apply_filters = st.form_submit_button("Terapkan Filter", type="primary", icon=":material/tune:", use_container_width=True)
        if apply_filters:
            st.session_state["applied_car_filters"] = {
                "budget": (int(budget_min), int(budget_max)),
                "make": None if make == "Semua" else make,
                "model": None if model == "Semua" else model,
                "years": years,
                "max_mileage": int(mileage),
                "engine_range": engine_range,
                "categories": {"fuel_type": fuel, "transmission": transmission, "body_type": body},
            }
        st.button("Reset filter", key="reset_car_filters", on_click=_reset_filters, use_container_width=True)

default_filters = {
    "budget": (0, budget_ceiling), "make": None, "model": None,
    "years": (1950, year_end), "max_mileage": 2_000_000,
    "engine_range": (0, 10_000), "categories": {},
}
active_filters = st.session_state.get("applied_car_filters") or default_filters
filtered = filter_listings(cars, **active_filters)

with right:
    query = st.text_input("Cari kata kunci", placeholder="Contoh: Avanza, SUV, Jakarta Selatan", key="car_search_query")
    if query.strip():
        searchable = [column for column in ["make", "model", "variant", "location", "location_normalized"] if column in filtered]
        mask = pd.Series(False, index=filtered.index)
        for column in searchable:
            mask |= filtered[column].fillna("").astype(str).str.contains(query.strip(), case=False, regex=False)
        filtered = filtered[mask]

    sort = st.selectbox("Urutkan", ["Harga terendah", "Harga tertinggi", "Tahun terbaru", "Kilometer terendah"], key="car_sort")
    sort_column, ascending = {"Harga terendah": ("price", True), "Harga tertinggi": ("price", False), "Tahun terbaru": ("year", False), "Kilometer terendah": ("mileage_km", True)}[sort]
    filtered = filtered.sort_values(sort_column, ascending=ascending, na_position="last")
    unique_matches = filtered["listing_id"].nunique() if "listing_id" in filtered else len(filtered)
    st.markdown(f"### {unique_matches:,} mobil cocok".replace(",", "."))
    st.caption(f"Sumber: {source_choice} · {len(cars):,} mobil unik tersedia sebelum filter.".replace(",", "."))
    if filtered.empty:
        st.info("Belum ada hasil yang cocok. Coba longgarkan anggaran, tahun, kilometer, atau filter spesifikasi.")
        st.stop()

    ids = filtered["listing_id"].astype(str).tolist() if "listing_id" in filtered else []
    label_map = {
        str(row["listing_id"]): f"{row.get('make', '')} {row.get('model', '')} · {int(row['year']) if pd.notna(row.get('year')) else '—'} · {format_rupiah(row.get('price'))}"
        for _, row in filtered.iterrows()
    }
    selected = st.multiselect("Pilih 2–3 mobil untuk dibandingkan", ids, max_selections=3, format_func=lambda value: label_map.get(value, value), key="car_compare_selection")
    button_cols = st.columns([1, 1, 2])
    with button_cols[0]:
        compare_clicked = st.button("Bandingkan Mobil", disabled=len(selected) < 2, icon=":material/compare:", key="car_compare_button", use_container_width=True)
    with button_cols[1]:
        check_clicked = st.button("Cek Harga Iklan", disabled=not selected, icon=":material/price_check:", key="car_check_price_button", use_container_width=True)
    if compare_clicked:
        st.session_state["show_car_comparison"] = True
    if len(selected) < 2:
        st.caption("Pilih dua atau tiga mobil untuk membuka perbandingan.")
    if st.session_state.get("show_car_comparison") and len(selected) >= 2:
        comparison = compare_listings(filtered, selected)
        if not comparison.empty:
            st.dataframe(comparison, width="stretch", alt="Tabel perbandingan spesifikasi mobil yang dipilih")
        st.caption("Harga dan spesifikasi listing membantu membandingkan informasi iklan; keduanya tidak menjamin kondisi kendaraan.")
    if check_clicked:
        chosen = filtered[filtered["listing_id"].astype(str).eq(selected[0])].iloc[0]
        fields = ["make", "model", "year", "mileage_km", "engine_cc", "fuel_type", "transmission", "body_type", "price"]
        st.session_state["price_checker_prefill"] = {key: (None if pd.isna(chosen.get(key)) else chosen.get(key)) for key in fields}
        st.switch_page("pages/3_Price_Checker.py")

    st.markdown("### Pilihan mobil")
    page_size = 9
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page_number = st.selectbox("Halaman hasil", list(range(1, total_pages + 1)), format_func=lambda value: f"Halaman {value} dari {total_pages}", key="car_results_page")
    st.caption(f"Menampilkan {min(page_size, max(0, len(filtered) - (page_number - 1) * page_size))} dari {unique_matches:,} hasil yang cocok.".replace(",", "."))
    page_rows = filtered.iloc[(page_number - 1) * page_size : page_number * page_size]
    result_cols = st.columns(3, gap="medium")
    for index, (_, row) in enumerate(page_rows.iterrows()):
        with result_cols[index % 3]:
            with st.container(border=True):
                image_url = row.get("image_url")
                if pd.notna(image_url) and str(image_url).startswith("http"):
                    st.image(str(image_url), alt=f"Foto {row.get('make', '')} {row.get('model', '')}", width="stretch")
                else:
                    st.markdown("<div class='car-photo-fallback'><span>🚘</span><small>Foto listing tidak tersedia</small></div>", unsafe_allow_html=True)
                st.markdown(f"#### {row.get('make') or 'Merek tidak dicantumkan'} {row.get('model') or ''}")
                st.markdown(f"<div class='car-price'>{format_rupiah(row.get('price'))}</div>", unsafe_allow_html=True)
                st.caption(str(row.get("variant") or "Varian tidak dicantumkan"))
                spec_rows = [
                    ("Tahun", f"{row.get('year'):.0f}" if pd.notna(row.get("year")) else "—"),
                    ("Kilometer", format_km(row.get("mileage_km"))),
                    ("CC", f"{row.get('engine_cc'):.0f}" if pd.notna(row.get("engine_cc")) else "—"),
                    ("Bahan bakar", str(row.get("fuel_type") or "—")),
                    ("Transmisi", str(row.get("transmission") or "—")),
                    ("Lokasi", str(row.get("location_normalized") or row.get("location") or "—")),
                ]
                for label, value in spec_rows:
                    st.markdown(f"<div class='listing-spec'><span>{label}</span><b>{value}</b></div>", unsafe_allow_html=True)
                origins = str(row.get("source_origins") or row.get("data_source") or source_choice)
                fetched = pd.to_datetime(row.get("fetched_at"), errors="coerce", utc=True)
                if pd.notna(fetched):
                    source_time = fetched.tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M WIB")
                elif "Dataset Excel" in origins:
                    source_time = "tanggal pengambilan tidak tersedia"
                else:
                    source_time = "waktu pengambilan tidak tersedia"
                st.caption(f"Sumber: {origins} · {source_time}")
                url = row.get("url")
                if pd.notna(url) and str(url).startswith("http"):
                    st.link_button("Buka iklan sumber", str(url), icon=":material/open_in_new:", use_container_width=True)

if source_choice == "Arsip Penuh":
    st.warning("Arsip bukan stok aktif. Dataset Excel tidak memiliki tanggal pengambilan; snapshot OLX menampilkan waktu refresh yang tercatat.")
else:
    st.caption("Listing terlihat saat snapshot terakhir diambil, tetapi status iklan dapat berubah. AutoMatch tidak memeriksa kondisi fisik atau dokumen kendaraan.")
