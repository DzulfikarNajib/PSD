"""Kesimpulan & Rekomendasi — ringkasan temuan dan saran berdasarkan hasil analisis.

Semua insight dihitung dari data aktual. Tidak ada teks hardcode dari mockup.
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
    icon="✅",
    title="Kesimpulan & Rekomendasi",
    subtitle="Ringkasan temuan dan saran berdasarkan hasil analisis pasar mobil bekas DKI Jakarta.",
)

st.info(
    "Halaman ini sedang diimplementasikan (Fase 8). Konten lengkap akan tersedia setelah implementasi selesai.",
    icon=":material/info:",
)

coming_soon_placeholder(
    page_name="Kesimpulan & Rekomendasi",
    description="4 insight cards terhitung dari data · Rekomendasi untuk pembeli · Rekomendasi untuk penjual · Keterbatasan penelitian",
    icon="✅",
)
