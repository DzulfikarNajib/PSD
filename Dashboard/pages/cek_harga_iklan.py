"""Cek Harga Iklan — analisis kewajaran harga iklan mobil bekas.

Menerima input listing (pilih dari dataset atau manual), menjalankan
estimasi model terbaik, dan menampilkan pembanding pasar serupa.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st

from src.styles import apply_theme
from src.ui_components import page_header, coming_soon_placeholder

apply_theme()

page_header(
    icon="💰",
    title="Cek Harga Iklan",
    subtitle="Analisis harga untuk mengetahui apakah harga yang ditawarkan sudah sesuai dengan pasar.",
)

st.info(
    "Halaman ini sedang diimplementasikan (Fase 7). Konten lengkap akan tersedia setelah implementasi selesai.",
    icon=":material/info:",
)

coming_soon_placeholder(
    page_name="Cek Harga Iklan",
    description="Tab Pilih Listing · Tab Input Manual · Estimasi model terbaik · Median pembanding · P25–P75 rentang · Selisih Rp & % · Status kewajaran · Penjelasan hasil",
    icon="💰",
)
