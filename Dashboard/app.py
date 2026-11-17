"""AutoMatch application shell with a compact, persistent top navigation."""

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
    position="top",
)

st.logo("assets/automatch-logo.png", size="medium")

active_page.run()
