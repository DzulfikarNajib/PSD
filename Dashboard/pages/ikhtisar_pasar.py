"""Ikhtisar Pasar — ringkasan pasar mobil bekas DKI Jakarta.

Halaman ini menampilkan KPI utama, distribusi wilayah, komposisi bahan bakar,
dan top merek berdasarkan data aktual dari arsip OLX.
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
    icon="🏠",
    title="Ikhtisar Pasar",
    subtitle="Ringkasan pasar mobil bekas DKI Jakarta — KPI, distribusi wilayah, komposisi bahan bakar, dan merek teratas.",
)

st.info(
    "Halaman ini sedang diimplementasikan (Fase 3). Konten lengkap akan tersedia setelah implementasi selesai.",
    icon=":material/info:",
)

coming_soon_placeholder(
    page_name="Ikhtisar Pasar",
    description="KPI listing unik, jumlah merek, median harga, rentang tahun · Top 5 merek · Distribusi 5 wilayah DKI · Komposisi bahan bakar · Insight cards terhitung dari data",
    icon="📊",
)
