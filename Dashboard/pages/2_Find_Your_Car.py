"""Search saved listings in a marketplace-style layout without paid API calls."""

from html import escape

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.car_search import compare_listings, filter_listings
from src.data_loader import load_combined_archive
from src.market_segments import cluster_market_segments
from src.styles import apply_theme
from src.ui import (
    format_km,
    format_rupiah,
    format_rupiah_compact,
    render_data_source_status,
    render_empty_state,
)


@st.cache_data(show_spinner=False)
def _cluster_cached(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return cluster_market_segments(frame)


apply_theme()
st.title("Cari Mobil")
st.caption("Saring arsip berdasarkan anggaran dan spesifikasi. Bandingkan listing, lalu buka sumber iklan untuk memeriksa detailnya.")

archive = load_combined_archive()
if archive.empty:
    render_empty_state("Belum ada data mobil", "Dataset bersih OLX belum tersedia. Tidak ada data contoh yang ditampilkan.")
    st.stop()

cars = archive.copy()
for column in ("price", "year", "mileage_km", "engine_cc"):
    if column in cars:
        cars[column] = pd.to_numeric(cars[column], errors="coerce")
cars, segment_summary = _cluster_cached(cars)

render_data_source_status()

segment_expanded = st.session_state.get("car_market_segment_filter", "Semua segmen") != "Semua segmen"
with st.expander("Segmen Pasar · K-Means (Unsupervised Learning)", expanded=segment_expanded):
    st.caption("Sistem mengelompokkan mobil ke dalam klaster karakteristik pasar (K-Means) berdasarkan kombinasi Harga, Tahun, Kilometer, dan Kapasitas Mesin. Gunakan dropdown filter di panel kiri untuk menyaring mobil per klaster persona.")
    if segment_summary.empty:
        st.info("Belum cukup listing dengan harga valid untuk membentuk kelompok karakteristik.")
        segment_options = ["Semua segmen"]
    else:
        kmeans_col1, kmeans_col2 = st.columns([1.3, 1], gap="medium")
        with kmeans_col1:
            st.markdown("**Visualisasi Sebaran Klaster Pasar**")
            scatter_data = cars.dropna(subset=["year", "price"]).copy()
            scatter_data = scatter_data[scatter_data["market_segment"].astype(str).ne("") & scatter_data["price"].between(20_000_000, 2_000_000_000)]
            if len(scatter_data) > 2500:
                scatter_data = scatter_data.sample(2500, random_state=42)
            scatter_data["Harga_Juta"] = scatter_data["price"] / 1_000_000
            
            fig_km = px.scatter(
                scatter_data,
                x="year",
                y="Harga_Juta",
                color="market_segment",
                color_discrete_sequence=["#008B8B", "#0284C7", "#F59E0B", "#10B981", "#64748B"],
                hover_name="title" if "title" in scatter_data else "make",
                hover_data={"year": True, "Harga_Juta": ":.1f", "market_segment": True},
                render_mode="webgl",
                labels={"year": "Tahun Kendaraan", "Harga_Juta": "Harga Penawaran (Juta Rp)", "market_segment": "Segmen Pasar"},
            )
            fig_km.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                height=340,
                legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center", font=dict(size=10)),
                xaxis=dict(title="Tahun Kendaraan", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="Harga (Juta Rp)", showgrid=True, gridcolor="#F1F5F9"),
            )
            fig_km.update_traces(marker=dict(size=5, opacity=0.75))
            st.plotly_chart(fig_km, width="stretch", config={"displayModeBar": False}, key="kmeans_scatter_webgl")

        with kmeans_col2:
            st.markdown("**Profil Ringkasan Persona Segmen**")
            segment_display = segment_summary.rename(columns={
                "market_segment": "Segmen",
                "profile": "Karakteristik",
                "listings": "Unit",
                "median_price": "Median harga",
                "median_year": "Tahun",
                "median_mileage_km": "Median km",
            }).copy()
            segment_display["Median harga"] = segment_display["Median harga"].map(format_rupiah_compact)
            segment_display["Tahun"] = segment_display["Tahun"].map(lambda value: f"{value:.0f}" if pd.notna(value) else "-")
            segment_display["Median km"] = segment_display["Median km"].map(format_km)
            cols_to_show = [col for col in ["Segmen", "Unit", "Median harga", "Tahun", "Median km"] if col in segment_display.columns]
            st.dataframe(
                segment_display[cols_to_show],
                hide_index=True,
                width="stretch",
                column_config={
                    "Segmen": st.column_config.TextColumn("Segmen", width="medium"),
                    "Unit": st.column_config.NumberColumn("Unit", width="small"),
                },
                key="kmeans_segment_table",
            )
        segment_options = ["Semua segmen", *segment_summary["market_segment"].tolist()]

if st.session_state.get("car_market_segment_filter", "Semua segmen") not in segment_options:
    st.session_state["car_market_segment_filter"] = "Semua segmen"

brand_values = sorted(cars["make"].dropna().astype(str).unique()) if "make" in cars else []
pending_make = st.session_state.pop("prefill_make", None)
pending_model = st.session_state.pop("prefill_model", None)
pending_location = st.session_state.pop("prefill_location", None)
if pending_make in brand_values:
    st.session_state["filter_make"] = pending_make
    st.session_state["applied_car_filters"] = None
if st.session_state.get("filter_make", "Semua") not in ["Semua", *brand_values]:
    st.session_state["filter_make"] = "Semua"

model_values = sorted(cars["model"].dropna().astype(str).unique()) if "model" in cars else []
if pending_model in model_values:
    st.session_state["filter_model"] = pending_model
    st.session_state["applied_car_filters"] = None
fuel_values = sorted(cars["fuel_type"].dropna().astype(str).unique()) if "fuel_type" in cars else []
pending_fuel = st.session_state.pop("prefill_fuel", None)
if pending_fuel in fuel_values:
    st.session_state["filter_fuel"] = pending_fuel
    st.session_state["applied_car_filters"] = None
transmission_values = sorted(cars["transmission"].dropna().astype(str).unique()) if "transmission" in cars else []
body_values = sorted(cars["body_type"].dropna().astype(str).unique()) if "body_type" in cars else []
location_values = sorted(cars.get("location_normalized", pd.Series(dtype=str)).dropna().astype(str).unique(), key=str.casefold)
if pending_location in location_values:
    st.session_state["filter_location"] = pending_location
    st.session_state["applied_car_filters"] = None

budget_ceiling = max(50_000_000_000, int(cars["price"].max()) if "price" in cars and cars["price"].notna().any() else 50_000_000_000)
budget_ceiling_jt = max(50_000, budget_ceiling // 1_000_000)

# A click-through from the market explorer should arrive with results already
# narrowed, while leaving the corresponding controls visible and editable.
prefill_filters = {
    "make": pending_make if pending_make in brand_values else None,
    "model": pending_model if pending_model in model_values else None,
    "fuel_type": pending_fuel if pending_fuel in fuel_values else None,
    "location": pending_location if pending_location in location_values else None,
}
if any(prefill_filters.values()):
    st.session_state["applied_car_filters"] = {
        "budget": (0, budget_ceiling), "make": prefill_filters["make"], "model": prefill_filters["model"],
        "years": (1950, pd.Timestamp.now().year + 1), "max_mileage": 2_000_000,
        "engine_range": (0, 10_000),
        "categories": {"fuel_type": prefill_filters["fuel_type"] or "Semua"},
        "location": prefill_filters["location"] or "Semua wilayah",
    }


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
    st.session_state["filter_location"] = "Semua wilayah"
    st.session_state["applied_car_filters"] = None


filter_column, results_column = st.columns([.3, .7], gap="large", vertical_alignment="top")
with filter_column:
    with st.container(border=True, key="car_filter_panel"):
        st.markdown("#### Filter Pencarian")
        st.caption("Filter bekerja pada data yang sudah tersimpan dan tidak mengambil data baru dari OLX.")
        selected_market_segment = st.selectbox(
            "Segmen pasar",
            segment_options,
            key="car_market_segment_filter",
            help="Segmen dibentuk dari harga, tahun, kilometer, dan CC. Labelnya relatif terhadap data, bukan kelas kualitas.",
        )
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
            st.caption("Listing tanpa CC tetap disertakan saat rentang penuh; setelah rentang CC dipersempit, listing tanpa nilai CC dikeluarkan dari hasil.")
            fuel = st.selectbox("Bahan bakar", ["Semua", *fuel_values], key="filter_fuel")
            transmission = st.selectbox("Transmisi", ["Semua", *transmission_values], key="filter_transmission")
            body = st.selectbox("Tipe bodi", ["Semua", *body_values], key="filter_body")
            location_options = ["Semua wilayah", *location_values]
            if st.session_state.get("filter_location") not in location_options:
                st.session_state["filter_location"] = "Semua wilayah"
            location = st.selectbox("Wilayah", location_options, key="filter_location")
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
                "location": location,
            }
        st.button("Reset filter", key="reset_car_filters", on_click=_reset_filters, width="stretch")

default_filters = {
    "budget": (0, budget_ceiling), "make": None, "model": None,
    "years": (1950, year_end), "max_mileage": 2_000_000,
    "engine_range": (0, 10_000), "categories": {},
}
active_filters = st.session_state.get("applied_car_filters") or default_filters
filtered = filter_listings(cars, **{key: value for key, value in active_filters.items() if key != "location"})
active_location = active_filters.get("location", "Semua wilayah")
if active_location != "Semua wilayah" and "location_normalized" in filtered:
    filtered = filtered[filtered["location_normalized"].fillna("").astype(str).str.casefold().eq(str(active_location).casefold())]
if selected_market_segment != "Semua segmen":
    filtered = filtered[filtered["market_segment"].eq(selected_market_segment)]

with results_column:
    query_column, sort_column_ui = st.columns([1.6, 1], gap="small", vertical_alignment="bottom")
    query = query_column.text_input("Cari mobil", placeholder="Contoh: Avanza, SUV, Jakarta Selatan", key="car_search_query")
    if query.strip():
        searchable = [column for column in ["make", "model", "variant", "location", "location_normalized"] if column in filtered]
        mask = pd.Series(False, index=filtered.index)
        for column in searchable:
            mask |= filtered[column].fillna("").astype(str).str.contains(query.strip(), case=False, regex=False)
        filtered = filtered[mask]

    sort = sort_column_ui.selectbox("Urutkan", ["Harga terendah", "Harga tertinggi", "Tahun terbaru", "Kilometer terendah"], key="car_sort")
    sort_column, ascending = {"Harga terendah": ("price", True), "Harga tertinggi": ("price", False), "Tahun terbaru": ("year", False), "Kilometer terendah": ("mileage_km", True)}[sort]
    filtered = filtered.sort_values(sort_column, ascending=ascending, na_position="last")
    unique_matches = filtered["listing_id"].nunique() if "listing_id" in filtered else len(filtered)
    st.markdown(f"### {unique_matches:,} mobil cocok".replace(",", "."))
    st.caption(f"Menampilkan hasil dari {len(cars):,} listing pada sumber {source_choice.lower()}.".replace(",", "."))
    if filtered.empty:
        st.info("Belum ada hasil yang cocok. Coba perlebar rentang anggaran, tahun, kilometer, atau filter spesifikasi.")
        st.stop()

    ids = filtered["listing_id"].astype(str).tolist() if "listing_id" in filtered else []
    label_map = {
        str(row["listing_id"]): f"{row.get('make', '')} {row.get('model', '')} · {int(row['year']) if pd.notna(row.get('year')) else '-'} · {format_rupiah(row.get('price'))}"
        for _, row in filtered.iterrows()
    }
    with st.container(border=True, key="car_compare_panel"):
        st.markdown("#### Bandingkan pilihan atau cek harga")
        st.caption("Bandingkan = lihat spesifikasi beberapa listing berdampingan. Cek harga = nilai satu iklan terhadap listing serupa dan estimasi model.")
        selected = st.multiselect("Pilih iklan tertentu (1 untuk cek harga, 2–3 untuk bandingkan)", ids, max_selections=3, format_func=lambda value: label_map.get(value, value), key="car_compare_selection")
        button_cols = st.columns([1, 1], gap="small")
        with button_cols[0]:
            compare_clicked = st.button("Bandingkan", disabled=len(selected) < 2, icon=":material/compare:", key="car_compare_button", width="stretch")
        with button_cols[1]:
            check_clicked = st.button("Cek harga", disabled=not selected, icon=":material/price_check:", key="car_check_price_button", width="stretch")
    if compare_clicked:
        st.session_state["show_car_comparison"] = True
    if len(selected) < 2:
        st.caption("Model dari Pahami Pasar sudah menjadi filter hasil. Pilih iklan tertentu di sini: satu untuk Cek harga, atau dua sampai tiga untuk Bandingkan.")
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
                    f"<div class='listing-meta'><span>{escape(body_type)}</span><span>{escape(year_label)}</span><span>{escape(segment_label)}</span></div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"#### {row.get('make') or 'Merek tidak dicantumkan'} {row.get('model') or ''}")
                st.markdown(f"<div class='car-price'>{format_rupiah(row.get('price'))}</div>", unsafe_allow_html=True)
                location_value = row.get("location_normalized")
                if pd.isna(location_value) or not str(location_value).strip():
                    location_value = row.get("location")
                if pd.isna(location_value) or not str(location_value).strip():
                    location_value = "-"
                st.markdown(
                    f"<div class='listing-spec'><span>Kilometer</span><b>{format_km(row.get('mileage_km'))}</b></div>"
                    f"<div class='listing-spec'><span>Lokasi</span><b>{escape(str(location_value))}</b></div>",
                    unsafe_allow_html=True,
                )
                with st.expander("Spesifikasi dan sumber iklan"):
                    variant_value = row.get("variant")
                    st.caption(str(variant_value) if pd.notna(variant_value) and str(variant_value).strip() else "Varian tidak dicantumkan")
                    spec_rows = [
                        (
                            "CC",
                            ("≈ " if bool(row.get("engine_cc_inferred", False)) else "")
                            + f"{row.get('engine_cc'):.0f}"
                            if pd.notna(row.get("engine_cc")) else "-",
                        ),
                        ("Bahan bakar", str(row.get("fuel_type")) if pd.notna(row.get("fuel_type")) and str(row.get("fuel_type")).strip() else "-"),
                        ("Transmisi", str(row.get("transmission")) if pd.notna(row.get("transmission")) and str(row.get("transmission")).strip() else "-"),
                    ]
                    for label, value in spec_rows:
                        st.markdown(f"<div class='listing-spec'><span>{label}</span><b>{escape(value)}</b></div>", unsafe_allow_html=True)
                    if bool(row.get("engine_cc_inferred", False)):
                        st.caption("≈ berarti CC diperkirakan dari angka kapasitas di awal varian iklan.")
                    origins = str(row.get("source_origins") or row.get("data_source") or source_choice)
                    fetched = pd.to_datetime(row.get("fetched_at"), errors="coerce", utc=True)
                    if pd.notna(fetched):
                        source_time = fetched.tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M WIB")
                    else:
                        source_time = "waktu pengambilan tidak tersedia"
                    st.caption(f"Sumber: {origins} · {source_time}")
                    url = row.get("url")
                    if pd.notna(url) and str(url).startswith("http"):
                        st.link_button("Buka iklan sumber", str(url), icon=":material/open_in_new:", width="stretch")

if source_choice == "Arsip Penuh":
    st.warning("Dataset ini sudah dibersihkan untuk analisis, tetapi bukan stok aktif. Iklan dapat berubah atau tidak aktif; snapshot terbaru tersedia pada pilihan Listing Terbaru.")
else:
    st.caption("Listing terlihat saat snapshot terakhir diambil, tetapi status iklan dapat berubah. AutoMatch tidak memeriksa kondisi fisik atau dokumen kendaraan.")
