"""Eksplorasi Data — analisis distribusi dan hubungan antarvariabel.

Menampilkan distribusi harga, top merek, harga per tipe mobil, scatter Tahun/KM vs Harga,
dan listing per wilayah dengan filter global (Wilayah, Merek, Tahun, Bahan Bakar).
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
    icon="📈",
    title="Eksplorasi Data",
    subtitle="Memahami pola dan hubungan antarvariabel pada data mobil bekas DKI Jakarta.",
)

st.info(
    "Halaman ini sedang diimplementasikan (Fase 4). Konten lengkap akan tersedia setelah implementasi selesai.",
    icon=":material/info:",
)

coming_soon_placeholder(
    page_name="Eksplorasi Data",
    description="Filter bar (Wilayah · Merek · Tahun · Bahan Bakar) · Distribusi harga · Top 5 merek · Harga per tipe mobil · Tahun vs Harga · KM vs Harga · Listing per wilayah",
    icon="🔍",
)
