"""Search saved listings in a marketplace-style layout without paid API calls."""

import pandas as pd
import streamlit as st

from src.car_search import compare_listings, filter_listings
from src.data_loader import get_last_updated_text, load_combined_archive, load_live_data
from src.market_segments import cluster_market_segments
from src.styles import apply_theme
from src.ui import (
    format_km,
    format_rupiah,
    format_rupiah_compact,
    listing_data_context,
    render_data_source_status,
    render_empty_state,
)


@st.cache_data(show_spinner=False)
def _cluster_cached(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return cluster_market_segments(frame)


apply_theme()
st.title("Cari Mobil")
st.caption("Saring arsip berdasarkan anggaran dan spesifikasi. Bandingkan listing, lalu buka sumber iklan untuk memeriksa detailnya.")

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
cars, segment_summary = _cluster_cached(cars)

if source_choice == "Listing Terbaru":
    st.caption(f"Snapshot OLX terakhir: {get_last_updated_text()}. Status dan isi iklan dapat berubah sejak pengambilan data.")
else:
    origins = cars.get("source_origins", pd.Series("", index=cars.index)).fillna("")
    dataset_count = int(origins.str.contains("OLX Indonesia", regex=False).sum())
    legacy_excel_count = int(origins.str.contains("Dataset Excel", regex=False).sum())
    olx_count = int(origins.str.contains("Arsip snapshot OLX", regex=False).sum())
    st.caption(f"Arsip Penuh · {cars['listing_id'].nunique():,} mobil unik · dataset OLX aktif: {dataset_count:,} · arsip Excel lama: {legacy_excel_count:,} · snapshot OLX: {olx_count:,}. Sumber dapat tumpang tindih dan iklan arsip mungkin sudah tidak aktif.".replace(",", "."))
render_data_source_status()
st.caption(listing_data_context(cars))

segment_expanded = st.session_state.get("car_market_segment_filter", "Semua segmen") != "Semua segmen"
with st.expander("Segmen pasar · K-Means", expanded=segment_expanded):
    st.caption("K-Means mengelompokkan harga, tahun, kilometer, dan CC. Profil kelompok relatif pada sumber yang dipilih, bukan penilaian kualitas mobil.")
    if segment_summary.empty:
        st.info("Belum cukup listing dengan harga valid untuk membentuk kelompok karakteristik.")
        segment_options = ["Semua segmen"]
    else:
        segment_display = segment_summary.rename(columns={
            "market_segment": "Segmen",
            "profile": "Profil relatif",
            "listings": "Jumlah listing",
            "median_price": "Median harga",
            "median_year": "Median tahun",
            "median_mileage_km": "Median kilometer",
            "median_engine_cc": "Median CC",
        }).copy()
        segment_display["Median harga"] = segment_display["Median harga"].map(format_rupiah_compact)
        segment_display["Median tahun"] = segment_display["Median tahun"].map(lambda value: f"{value:.0f}" if pd.notna(value) else "-")
        segment_display["Median kilometer"] = segment_display["Median kilometer"].map(format_km)
        segment_display["Median CC"] = segment_display["Median CC"].map(lambda value: f"{value:.0f} cc" if pd.notna(value) else "-")
        st.dataframe(segment_display, hide_index=True, width="stretch", alt="Ringkasan kelompok listing berdasarkan harga, tahun, kilometer, dan CC")
        segment_options = ["Semua segmen", *segment_summary["market_segment"].tolist()]

    if st.session_state.get("car_market_segment_filter", "Semua segmen") not in segment_options:
        st.session_state["car_market_segment_filter"] = "Semua segmen"
    selected_market_segment = st.selectbox(
        "Saring menurut segmen",
        segment_options,
        key="car_market_segment_filter",
        help="Segmen dibentuk dari harga, tahun, kilometer, dan CC dalam sumber aktif. Labelnya relatif terhadap data, bukan kelas kualitas.",
    )

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

budget_ceiling = max(50_000_000_000, int(cars["price"].max()) if "price" in cars and cars["price"].notna().any() else 50_000_000_000)
budget_ceiling_jt = max(50_000, budget_ceiling // 1_000_000)


def _reset_filters():
    st.session_state["filter_budget_min_jt"] = 0
    st.session_state["filter_budget_max_jt"] = budget_ceiling_jt
    st.session_state["filter_make"] = "Semua"
    st.session_state["filter_model"] = "Semua"
    st.session_state["filter_years"] = (1950, pd.Timestamp.now().year + 1)
    st.session_state["filter_mileage_rb"] = 2_000
    st.session_state["filter_engine"] = (0, 10_000)
    st.session_state["filter_fuel"] = "Semua"
    st.session_state["filter_transmission"] = "Semua"
    st.session_state["filter_body"] = "Semua"
    st.session_state["applied_car_filters"] = None


left = st.expander("Filter pencarian", expanded=True)
right = st.container()
with left:
    with st.container(border=True):
        st.markdown("#### Filter Pencarian")
        st.caption("Filter bekerja pada data yang sudah tersimpan dan tidak mengambil data baru dari OLX.")
        make_options = ["Semua", *brand_values]
        model_options = ["Semua", *model_values]
        if st.session_state.get("filter_model", "Semua") not in model_options:
            st.session_state["filter_model"] = "Semua"
        year_end = pd.Timestamp.now().year + 1
        if st.session_state.get("filter_years", (1950, year_end))[1] > year_end:
            st.session_state["filter_years"] = (1950, year_end)

        with st.form("car_filters_form"):
            st.markdown("**Anggaran (Juta Rp)**")
            budget_cols = st.columns(2)
            budget_min_jt = budget_cols[0].number_input("Min (Jt)", min_value=0, max_value=budget_ceiling_jt, value=st.session_state.get("filter_budget_min_jt", 0), step=5, key="filter_budget_min_jt")
            budget_max_jt = budget_cols[1].number_input("Maks (Jt)", min_value=0, max_value=budget_ceiling_jt, value=st.session_state.get("filter_budget_max_jt", budget_ceiling_jt), step=5, key="filter_budget_max_jt")
            budget_cols[0].caption(f"Nominal: **{format_rupiah(budget_min_jt * 1_000_000)}**")
            budget_cols[1].caption(f"Nominal: **{format_rupiah(budget_max_jt * 1_000_000)}**")

            make = st.selectbox("Merek", make_options, key="filter_make")
            model = st.selectbox("Model", model_options, key="filter_model")
            years = st.slider("Tahun", 1950, year_end, st.session_state.get("filter_years", (1950, year_end)), key="filter_years")

            mileage_rb = st.number_input("Kilometer maksimum (Ribu km)", min_value=0, max_value=2_000, value=st.session_state.get("filter_mileage_rb", 2_000), step=5, key="filter_mileage_rb")
            st.caption(f"Nominal odometer: **{format_km(mileage_rb * 1_000)}**")

            engine_range = st.slider("Kapasitas mesin (cc)", 0, 10_000, (0, 10_000), step=100, key="filter_engine")
            fuel = st.selectbox("Bahan bakar", ["Semua", *fuel_values], key="filter_fuel")
            transmission = st.selectbox("Transmisi", ["Semua", *transmission_values], key="filter_transmission")
            body = st.selectbox("Tipe bodi", ["Semua", *body_values], key="filter_body")
            apply_filters = st.form_submit_button("Terapkan Filter", type="primary", icon=":material/tune:", width="stretch")

        if apply_filters:
            st.session_state["applied_car_filters"] = {
                "budget": (int(budget_min_jt * 1_000_000), int(budget_max_jt * 1_000_000)),
                "make": None if make == "Semua" else make,
                "model": None if model == "Semua" else model,
                "years": years,
                "max_mileage": int(mileage_rb * 1_000),
                "engine_range": engine_range,
                "categories": {"fuel_type": fuel, "transmission": transmission, "body_type": body},
            }
        st.button("Reset filter", key="reset_car_filters", on_click=_reset_filters, width="stretch")

default_filters = {
    "budget": (0, budget_ceiling), "make": None, "model": None,
    "years": (1950, year_end), "max_mileage": 2_000_000,
    "engine_range": (0, 10_000), "categories": {},
}
active_filters = st.session_state.get("applied_car_filters") or default_filters
filtered = filter_listings(cars, **active_filters)
if selected_market_segment != "Semua segmen":
    filtered = filtered[filtered["market_segment"].eq(selected_market_segment)]

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
        st.info("Belum ada hasil yang cocok. Coba perlebar rentang anggaran, tahun, kilometer, atau filter spesifikasi.")
        st.stop()

    ids = filtered["listing_id"].astype(str).tolist() if "listing_id" in filtered else []
    label_map = {
        str(row["listing_id"]): f"{row.get('make', '')} {row.get('model', '')} · {int(row['year']) if pd.notna(row.get('year')) else '-'} · {format_rupiah(row.get('price'))}"
        for _, row in filtered.iterrows()
    }
    selected = st.multiselect("Pilih 2 - 3 mobil untuk dibandingkan", ids, max_selections=3, format_func=lambda value: label_map.get(value, value), key="car_compare_selection")
    button_cols = st.columns([1, 1, 2])
    with button_cols[0]:
        compare_clicked = st.button("Bandingkan Mobil", disabled=len(selected) < 2, icon=":material/compare:", key="car_compare_button", width="stretch")
    with button_cols[1]:
        check_clicked = st.button("Cek Harga Iklan", disabled=not selected, icon=":material/price_check:", key="car_check_price_button", width="stretch")
    if compare_clicked:
        st.session_state["show_car_comparison"] = True
    if len(selected) < 2:
        st.caption("Pilih dua atau tiga mobil untuk membuka perbandingan spesifikasi.")
    if st.session_state.get("show_car_comparison") and len(selected) >= 2:
        comparison = compare_listings(filtered, selected)
        if not comparison.empty:
            st.dataframe(comparison, width="stretch", alt="Tabel perbandingan spesifikasi mobil yang dipilih")
        st.caption("Harga dan spesifikasi listing membantu membandingkan informasi iklan; keduanya tidak menjamin kondisi kendaraan.")
    if check_clicked:
        chosen = filtered[filtered["listing_id"].astype(str).eq(selected[0])].iloc[0]
        fields = ["make", "model", "year", "mileage_km", "engine_cc", "fuel_type", "transmission", "body_type", "price"]
        st.session_state["price_checker_prefill"] = {
            **{key: (None if pd.isna(chosen.get(key)) else chosen.get(key)) for key in fields},
            "_comparison_source": source_choice,
            "_auto_calculate": True,
        }
        st.switch_page("pages/3_Price_Checker.py")

    st.markdown("### Pilihan Mobil")
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
                if pd.notna(image_url) and str(image_url).startswith(("http://", "https://")):
                    try:
                        st.image(str(image_url), alt=f"Foto {row.get('make', '')} {row.get('model', '')}", width="stretch")
                    except Exception:
                        st.caption("Foto sumber tidak dapat dimuat")
                body_value = row.get("body_type")
                body_type = str(body_value) if pd.notna(body_value) and str(body_value).strip() else "Tipe bodi -"
                year_label = f"{row.get('year'):.0f}" if pd.notna(row.get("year")) else "Tahun -"
                segment_value = row.get("market_segment")
                segment_label = str(segment_value) if pd.notna(segment_value) and str(segment_value).strip() else "Segmen belum tersedia"
                st.markdown(
                    f"<div class='listing-meta'><span>{body_type}</span><span>{year_label}</span><span>{segment_label}</span></div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"#### {row.get('make') or 'Merek tidak dicantumkan'} {row.get('model') or ''}")
                st.markdown(f"<div class='car-price'>{format_rupiah(row.get('price'))}</div>", unsafe_allow_html=True)
                st.caption(str(row.get("variant") or "Varian tidak dicantumkan"))
                spec_rows = [
                    ("Tahun", f"{row.get('year'):.0f}" if pd.notna(row.get("year")) else "-"),
                    ("Kilometer", format_km(row.get("mileage_km"))),
                    ("CC", f"{row.get('engine_cc'):.0f}" if pd.notna(row.get("engine_cc")) else "-"),
                    ("Bahan bakar", str(row.get("fuel_type") or "-")),
                    ("Transmisi", str(row.get("transmission") or "-")),
                    ("Lokasi", str(row.get("location_normalized") or row.get("location") or "-")),
                ]
                for label, value in spec_rows:
                    st.markdown(f"<div class='listing-spec'><span>{label}</span><b>{value}</b></div>", unsafe_allow_html=True)
                origins = str(row.get("source_origins") or row.get("data_source") or source_choice)
                fetched = pd.to_datetime(row.get("fetched_at"), errors="coerce", utc=True)
                if pd.notna(fetched):
                    source_time = fetched.tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M WIB")
                elif "Dataset Excel" in origins:
                    source_time = "tanggal pengambilan arsip lama tidak tersedia"
                else:
                    source_time = "waktu pengambilan tidak tersedia"
                st.caption(f"Sumber: {origins} · {source_time}")
                url = row.get("url")
                if pd.notna(url) and str(url).startswith("http"):
                    st.link_button("Buka iklan sumber", str(url), icon=":material/open_in_new:", width="stretch")

if source_choice == "Arsip Penuh":
    st.warning("Arsip bukan stok aktif. Dataset OLX dan snapshot mencatat waktu pengambilan, tetapi iklan dapat berubah atau tidak aktif. Hanya arsip Excel lama yang tidak memiliki tanggal pengambilan.")
else:
    st.caption("Listing terlihat saat snapshot terakhir diambil, tetapi status iklan dapat berubah. AutoMatch tidak memeriksa kondisi fisik atau dokumen kendaraan.")
