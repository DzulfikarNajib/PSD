"""AutoMatch application shell with a compact, persistent top navigation."""

import base64
from pathlib import Path

import streamlit as st

from src.styles import apply_theme


st.set_page_config(page_title="AutoMatch", page_icon="assets/automatch-icon.png", layout="wide")
apply_theme()

home_page = st.Page("home.py", title="Beranda", url_path="beranda", icon=":material/home:", default=True)
search_page = st.Page("pages/2_Find_Your_Car.py", title="Cari Mobil", url_path="cari-mobil", icon=":material/directions_car:")
price_page = st.Page("pages/3_Price_Checker.py", title="Cek Harga Iklan", url_path="cek-harga-iklan", icon=":material/price_check:")
market_page = st.Page("pages/1_Explore_Market.py", title="Pahami Pasar", url_path="pahami-pasar", icon=":material/insights:")
project_page = st.Page("pages/4_Tentang_Proyek.py", title="Tentang Proyek", url_path="tentang-proyek", icon=":material/menu_book:")

active_page = st.navigation(
    {
        "Pembelian": [home_page, search_page, price_page],
        "Analisis": [market_page, project_page],
    },
    position="hidden",
)

logo_data = base64.b64encode((Path(__file__).parent / "assets" / "automatch-logo.png").read_bytes()).decode("ascii")

with st.container(key="automatch_topnav"):
    nav = st.columns([2.22, .68, .98, .87, 1.16, 1.18, .62], gap="small", vertical_alignment="center")
    with nav[0]:
        st.markdown(
            f'<div class="automatch-brand"><img src="data:image/png;base64,{logo_data}" alt="AutoMatch" /><span>Find the car that fits you.</span></div>',
            unsafe_allow_html=True,
        )

    page_links = [
        (nav[1], home_page, "Beranda", ":material/home:", "beranda"),
        (nav[2], market_page, "Pahami Pasar", ":material/insights:", "pasar"),
        (nav[3], search_page, "Cari Mobil", ":material/search:", "cari"),
        (nav[4], price_page, "Cek Harga Iklan", ":material/price_check:", "harga"),
        (nav[5], project_page, "Tentang Proyek", ":material/menu_book:", "proyek"),
    ]
    for column, page, label, icon, slug in page_links:
        is_active = active_page.title == label
        with column:
            with st.container(key=f"nav_active_{slug}" if is_active else f"nav_{slug}"):
                st.page_link(page, label=label, icon=icon, help=label)
    with nav[6]:
        if st.button("Refresh", icon=":material/refresh:", help="Buka panel refresh manual. Tombol ini tidak mengambil data.", key="nav_open_refresh"):
            st.session_state["open_refresh_panel"] = True
            st.switch_page("home.py")

active_page.run()
