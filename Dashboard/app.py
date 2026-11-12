"""Application entry point with explicit, localized navigation labels."""

import streamlit as st

st.set_page_config(page_title="AutoMatch", page_icon="🚘", layout="wide")

pages = {
    "Pembelian": [
        st.Page("home.py", title="Beranda", icon=":material/home:", default=True),
        st.Page("pages/2_Find_Your_Car.py", title="Cari Mobil", icon=":material/directions_car:"),
        st.Page("pages/3_Price_Checker.py", title="Cek Harga Iklan", icon=":material/price_check:"),
    ],
    "Analisis proyek": [
        st.Page("pages/1_Explore_Market.py", title="Pahami Pasar", icon=":material/insights:"),
        st.Page("pages/4_Tentang_Proyek.py", title="Tentang Proyek", icon=":material/menu_book:"),
    ],
}

page = st.navigation(pages)
page.run()
