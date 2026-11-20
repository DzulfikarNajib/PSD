"""AutoMatch home: a buyer-first entry point into saved vehicle listings."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import (
    load_combined_archive,
)
from src.styles import apply_theme
from src.ui import format_rupiah_compact, format_timestamp_wib, render_empty_state


DEFAULT_SEARCH_URL = "https://www.olx.co.id/mobil-bekas_c198/q-mobil"
HERO_IMAGE_DATA = base64.b64encode((Path(__file__).parent / "assets" / "hero-bmw.jpg").read_bytes()).decode("ascii")
# Static GeoJSON exported from Jakarta's official ``batas_kota_kab`` FeatureServer.
DKI_BOUNDARY_PATH = Path(__file__).parent / "assets" / "dki_kota.geojson"
BRAND_CARD_IMAGES = {
    "toyota": {
        "file": "Toyota_Corolla_(E180)_sedan_facelift_1X7A0306.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Toyota_Corolla_(E180)_sedan_facelift_1X7A0306.jpg",
        "credit": "Alexander Migl · CC BY-SA 4.0",
    },
    "mercedes-benz": {
        "file": "Mercedes-Benz_W211.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Mercedes-Benz_W211.jpg",
        "credit": "Kallerna · CC BY-SA 3.0",
    },
    "bmw": {
        "file": "BMW_X3_Facelift_front-1.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:BMW_X3_Facelift_front-1.jpg",
        "credit": "M 93 · CC BY-SA 3.0",
    },
    "honda": {
        "file": "Honda_Civic_2.2_i-DTEC_(front_quarter).jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Honda_Civic_2.2_i-DTEC_(front_quarter).jpg",
        "credit": "Overlaet · CC BY-SA 3.0",
    },
    "hyundai": {
        "file": "Hyundai_Tucson_(NX4)_1X7A0424.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Hyundai_Tucson_(NX4)_1X7A0424.jpg",
        "credit": "Alexander Migl · CC BY-SA 4.0",
    },
    "lexus": {
        "file": "2018_Lexus_RX_350_F_Sport_in_Sonic_Titanium,_front_left.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:2018_Lexus_RX_350_F_Sport_in_Sonic_Titanium,_front_left.jpg",
        "credit": "Ethan Llamas · CC BY-SA 4.0",
    },
    "mitsubishi": {
        "file": "Mitsubishi_Colt_(2023)_1X7A1809.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Mitsubishi_Colt_(2023)_1X7A1809.jpg",
        "credit": "Alexander Migl · CC BY-SA 4.0",
    },
    "mazda": {
        "file": "Mazda_3_(2019).jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Mazda_3_(2019).jpg",
        "credit": "Dennis Elzinga · CC BY 2.0",
    },
}


@st.cache_data(show_spinner=False)
def load_dki_boundaries() -> dict:
    """Load official DKI city boundaries used by the home choropleth."""
    return json.loads(DKI_BOUNDARY_PATH.read_text(encoding="utf-8"))


apply_theme()
archive = load_combined_archive()
preprocessing_audit = archive.attrs.get("preprocessing_audit", {})

st.markdown(
    f'<style>div[class*="st-key-home_hero"] {{ --automatch-hero-image: url("data:image/jpeg;base64,{HERO_IMAGE_DATA}"); }}</style>',
    unsafe_allow_html=True,
)

hero_count = int(preprocessing_audit.get("clean_rows", archive["listing_id"].nunique() if not archive.empty and "listing_id" in archive else len(archive)))

with st.container(key="home_hero"):
    st.caption("OVERVIEW MOBIL BEKAS DKI JAKARTA")
    st.markdown("# Ayo cari mobil kamu")
    st.markdown("### Temukan pilihan dari iklan mobil yang tersimpan di AutoMatch.")
    st.write("Data AutoMatch mencakup iklan mobil bekas dari DKI Jakarta. Iklan yang sama dihitung satu kali, dan peta di bawah menampilkan lima kota administrasi.")
    if st.button("Mulai cari mobil", icon=":material/search:", type="primary", key="home_start_search"):
        st.switch_page("pages/2_Find_Your_Car.py")

if archive.empty:
    render_empty_state(
        "Arsip mobil belum tersedia",
        "Dataset OLX atau snapshot yang tersimpan akan tampil di sini. AutoMatch tidak membuat data contoh.",
    )
else:
    archive = archive.copy()
    for column in ("price", "year"):
        if column in archive:
            archive[column] = pd.to_numeric(archive[column], errors="coerce")
    unique_count = archive["listing_id"].nunique() if "listing_id" in archive else len(archive)
    brands = archive["make"].dropna().astype(str).str.strip() if "make" in archive else pd.Series(dtype=str)
    fuels = archive["fuel_type"].fillna("Tidak dicantumkan").astype(str).str.strip() if "fuel_type" in archive else pd.Series(dtype=str)
    fuels = fuels.replace("", "Tidak dicantumkan").value_counts()
    clean_count = int(preprocessing_audit.get("clean_rows", unique_count))
    year_min, year_max = preprocessing_audit.get("year_min"), preprocessing_audit.get("year_max")
    year_range = f"{year_min}-{year_max}" if year_min is not None and year_max is not None else "-"
    latest_value = preprocessing_audit.get("latest_fetched_at")
    last_update = format_timestamp_wib(latest_value)
    st.caption(f"Dataset OLX aktif yang sudah dibersihkan · Tahun kendaraan {year_range} · Diperbarui {last_update}. Harga merupakan harga penawaran, bukan harga transaksi.")

    district_labels = {"jakarta selatan": "Jakarta Selatan", "jakarta timur": "Jakarta Timur", "jakarta barat": "Jakarta Barat", "jakarta pusat": "Jakarta Pusat", "jakarta utara": "Jakarta Utara"}
    if "location_normalized" in archive:
        district_counts = archive["location_normalized"].fillna("").astype(str).str.casefold().value_counts()
        region_code = {
            "jakarta pusat": "3171", "jakarta utara": "3172", "jakarta barat": "3173",
            "jakarta selatan": "3174", "jakarta timur": "3175",
        }
        regions = pd.DataFrame([
            {"Kode": region_code[key], "Wilayah": label, "Iklan tersimpan": int(district_counts.get(key, 0))}
            for key, label in district_labels.items()
        ])
        map_col, info_col = st.columns([1.6, 1], gap="medium")
        with map_col:
            with st.container(border=True):
                st.markdown("#### Temukan mobil di wilayah Jakarta")
                st.caption("Klik salah satu wilayah untuk melihat jumlah iklan tersimpan dan membuka hasil pencariannya.")
                boundaries = load_dki_boundaries()
                map_builder = getattr(px, "choropleth_map", None)
                map_style_argument = "map_style"
                if map_builder is None:
                    map_builder = px.choropleth_mapbox
                    map_style_argument = "mapbox_style"
                jakarta_center = {"lat": -6.2233, "lon": 106.8296}
                jakarta_zoom = 9.7
                map_fig = map_builder(
                    regions,
                    geojson=boundaries,
                    locations="Kode",
                    featureidkey="properties.kdpkab",
                    color="Iklan tersimpan",
                    hover_name="Wilayah",
                    hover_data={"Kode": False, "Iklan tersimpan": ":,.0f"},
                    color_continuous_scale=["#D9EFEB", "#72BDB3", "#008B8B", "#075985"],
                    range_color=(0, max(1, int(regions["Iklan tersimpan"].max()))),
                    opacity=0.9,
                    height=460,
                    center=jakarta_center,
                    zoom=jakarta_zoom,
                    **{map_style_argument: "white-bg"},
                )
                map_view_key = "map" if map_style_argument == "map_style" else "mapbox"
                map_fig.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    **{map_view_key: {"center": jakarta_center, "zoom": jakarta_zoom}},
                    coloraxis_colorbar=dict(
                        title="Jumlah iklan",
                        orientation="h",
                        thickness=10,
                        len=0.5,
                        x=0.5,
                        xanchor="center",
                        y=-0.08,
                        yanchor="top",
                        tickformat="~s",
                    ),
                    clickmode="event+select",
                )
                map_fig.update_traces(marker_line_color="#FFFFFF", marker_line_width=1.5)
                map_selection = st.plotly_chart(
                    map_fig,
                    width="stretch",
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "scrollZoom": True,
                        "modeBarButtonsToAdd": ["zoomInMap", "zoomOutMap", "resetViewMap"],
                    },
                    key="home_jakarta_choropleth",
                    on_select="rerun",
                    selection_mode="points",
                    alt="Peta choropleth lima kota administrasi Jakarta menurut jumlah iklan mobil tersimpan di AutoMatch",
                )
                st.caption("Warna lebih gelap berarti iklan tersimpan lebih banyak. Arahkan kursor untuk melihat angka. Peta mencakup lima kota administrasi Jakarta.")

        with info_col:
            selected_code = None
            selected_points = map_selection.selection.points if map_selection else []
            if selected_points:
                selected_point = selected_points[-1]
                selected_code = selected_point.get("location")
                if selected_code is None:
                    point_index = selected_point.get("point_index", selected_point.get("point_number"))
                    if point_index is not None and 0 <= int(point_index) < len(regions):
                        selected_code = regions.iloc[int(point_index)]["Kode"]

            with st.container(border=True, key="home_region_info_card"):
                if selected_code is not None:
                    selected_region = regions[regions["Kode"].astype(str).eq(str(selected_code))]
                    if not selected_region.empty:
                        row = selected_region.iloc[0]
                        selected_label = str(row["Wilayah"])
                        selected_count = int(row["Iklan tersimpan"])
                        st.caption(selected_label.upper())
                        st.markdown(f"## {selected_count:,}".replace(",", "."))
                        st.caption("iklan tersimpan di wilayah ini")
                        if st.button(f"Lihat mobil di {selected_label}", type="primary", key="home_selected_region_search", width="stretch"):
                            st.session_state["prefill_location"] = selected_label.casefold()
                            st.session_state["car_source_choice"] = "Arsip Penuh"
                            st.switch_page("pages/2_Find_Your_Car.py")
                else:
                    st.caption("DKI JAKARTA")
                    st.markdown(f"## {clean_count:,}".replace(",", "."))
                    st.caption("listing tersedia di 5 kota administrasi")
                    if st.button("Lihat semua mobil di Jakarta", type="primary", key="home_all_region_search", width="stretch"):
                        st.session_state.pop("prefill_location", None)
                        st.session_state["car_source_choice"] = "Arsip Penuh"
                        st.switch_page("pages/2_Find_Your_Car.py")

            with st.container(border=True, key="home_city_breakdown_card"):
                st.caption("SEBARAN 5 KOTA ADMINISTRASI")
                sorted_regions = regions.sort_values(by="Iklan tersimpan", ascending=False)
                max_regional = max(1, int(sorted_regions["Iklan tersimpan"].max()))
                for _, r_row in sorted_regions.iterrows():
                    w_name = str(r_row["Wilayah"])
                    w_count = int(r_row["Iklan tersimpan"])
                    pct = (w_count / clean_count * 100) if clean_count > 0 else 0
                    bar_w = int((w_count / max_regional) * 100)
                    is_active = (selected_code is not None and str(r_row["Kode"]) == str(selected_code))
                    active_cls = " home-city-row-active" if is_active else ""
                    st.markdown(
                        f"""
                        <div class="home-city-row{active_cls}">
                            <div class="home-city-header">
                                <span class="home-city-name">{w_name}</span>
                                <span class="home-city-count"><strong>{w_count:,}</strong> <span class="home-city-pct">({pct:.1f}%)</span></span>
                            </div>
                            <div class="home-city-bar-bg">
                                <div class="home-city-bar-fill" style="width: {bar_w}%;"></div>
                            </div>
                        </div>
                        """.replace(",", "."),
                        unsafe_allow_html=True,
                    )

    st.markdown("### Mulai dari bahan bakar")
    st.caption("Pilih bahan bakar untuk melihat merek dan model yang tersedia.")
    fuel_icons = {"Bensin": "local_gas_station", "Diesel": "oil_barrel", "Listrik": "electric_bolt", "Hybrid": "electric_car"}
    preferred_fuels = [label for label in ("Bensin", "Diesel", "Listrik") if label in fuels.index]
    remaining_fuels = [str(label) for label in fuels.index if label and label != "Tidak dicantumkan" and label not in preferred_fuels]
    fuel_items = [(label, int(fuels.get(label, 0))) for label in [*preferred_fuels, *remaining_fuels]]
    if fuel_items:
        fuel_cols = st.columns(min(4, len(fuel_items)), gap="medium")
        for idx, (fuel_label, fuel_count) in enumerate(fuel_items[:4]):
            with fuel_cols[idx]:
                with st.container(border=True, key=f"home_fuel_card_{idx}"):
                    st.markdown(
                        f"<div class='home-fuel-heading'><span class='material-symbols-rounded'>{fuel_icons.get(fuel_label, 'local_gas_station')}</span><strong>{fuel_label}</strong></div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{fuel_count:,}** iklan tersimpan".replace(",", "."))
                    if st.button("Lihat merek dan model", key=f"home_fuel_market_{idx}", width="stretch"):
                        st.session_state["market_focus_fuel"] = fuel_label
                        st.session_state["market_source_choice"] = "Arsip Penuh"
                        st.switch_page("pages/1_Explore_Market.py")
    else:
        st.caption("Kategori bahan bakar belum tersedia pada dataset ini.")

    st.markdown("### Pilih merek untuk menjelajahi modelnya")
    st.caption("Jumlah iklan menunjukkan ketersediaan di arsip AutoMatch, bukan penilaian kualitas atau rekomendasi mobil.")
    brand_counts = brands[brands.ne("")].value_counts()
    brand_cards = brand_counts.head(8)
    if not brand_cards.empty:
        brand_cols = st.columns(4, gap="medium")
        for idx, (make, count) in enumerate(brand_cards.items()):
            with brand_cols[idx % 4]:
                with st.container(border=True, key=f"home_brand_card_{idx}"):
                    brand_initials = "".join(part[0] for part in str(make).replace("-", " ").split()[:2]).upper()
                    photo_info = BRAND_CARD_IMAGES.get(str(make).casefold())
                    if photo_info:
                        photo_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{photo_info['file']}?width=900"
                        st.image(photo_url, width="stretch", caption=None)
                    else:
                        st.markdown(
                            f"<div class='home-brand-mark' aria-hidden='true'>{brand_initials}</div>",
                            unsafe_allow_html=True,
                        )
                    st.markdown(f"#### {make}")
                    st.caption(f"{int(count):,} iklan tersimpan".replace(",", "."))
                    if st.button("Lihat model", key=f"home_brand_market_{idx}", width="stretch"):
                        st.session_state["market_focus_make"] = str(make)
                        st.session_state["market_source_choice"] = "Arsip Penuh"
                        st.switch_page("pages/1_Explore_Market.py")
        with st.expander("Sumber dan kredit foto merek", expanded=False):
            for make, photo_info in BRAND_CARD_IMAGES.items():
                st.markdown(f"- **{make.title()}** — {photo_info['credit']} · [Sumber foto]({photo_info['page']})")
    if not brand_counts.empty:
        all_brands = sorted(brand_counts.index.astype(str), key=str.casefold)
        st.markdown("#### Cari merek lainnya")
        st.caption("Pilih merek di luar 8 merek terpopuler di atas untuk melihat ringkasan model dan membuka grafiknya.")
        other_brand = st.selectbox("Pilih merek lain", all_brands, key="home_brand_choice", label_visibility="collapsed")
        
        brand_df = archive[archive["make"].astype(str).str.casefold().eq(other_brand.casefold())] if "make" in archive else pd.DataFrame()
        brand_ads_count = int(brand_counts.get(other_brand, len(brand_df)))
        model_count = int(brand_df["model"].dropna().nunique()) if ("model" in brand_df and not brand_df.empty) else 0
        
        price_range_str = "-"
        if "price" in brand_df and not brand_df.empty:
            valid_prices = brand_df["price"].dropna()
            if not valid_prices.empty:
                min_p = valid_prices.min()
                max_p = valid_prices.max()
                price_range_str = f"{format_rupiah_compact(min_p)} – {format_rupiah_compact(max_p)}"

        with st.container(border=True, key="home_other_brand_card"):
            card_col1, card_col2, card_col3 = st.columns([1.5, 1.5, 2], vertical_alignment="center")
            with card_col1:
                st.caption("MEREK")
                st.markdown(f"### {other_brand}")
            with card_col2:
                st.caption("IKLAN & MODEL")
                st.markdown(f"**{brand_ads_count:,} iklan** · {model_count} model".replace(",", "."))
            with card_col3:
                st.caption("RENTANG HARGA PENAWARAN")
                st.markdown(f"**{price_range_str}**")
            
            if st.button(f"Buka grafik & jelajahi model {other_brand}", icon=":material/insights:", key="home_find_brand", type="primary", width="stretch"):
                st.session_state["market_focus_make"] = other_brand
                st.session_state["market_source_choice"] = "Arsip Penuh"
                st.switch_page("pages/1_Explore_Market.py")

