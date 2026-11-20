"""Preprocessing & Segmentasi — alur pembersihan data dan segmentasi pasar K-Means.

Tab Preprocessing: funnel pembersihan, checklist langkah, missing values.
Tab Segmentasi: scatter PCA 2D hasil clustering, profil segmen terhitung.
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
    icon="⚙️",
    title="Preprocessing & Segmentasi",
    subtitle="Menyiapkan data dan mengelompokkan pasar mobil bekas menggunakan K-Means.",
)

tab_prep, tab_seg = st.tabs(["🧹 Preprocessing", "🗂️ Segmentasi Pasar (Unsupervised)"])

with tab_prep:
    st.info(
        "Tab ini sedang diimplementasikan (Fase 6). Konten lengkap akan tersedia setelah implementasi selesai.",
        icon=":material/info:",
    )
    coming_soon_placeholder(
        page_name="Preprocessing",
        description="Funnel pembersihan data · Checklist 7 langkah dengan angka nyata · Missing values per kolom · Penjelasan feature engineering",
        icon="🧹",
    )

with tab_seg:
    st.info(
        "Tab ini sedang diimplementasikan (Fase 6). Konten lengkap akan tersedia setelah implementasi selesai.",
        icon=":material/info:",
    )
    coming_soon_placeholder(
        page_name="Segmentasi Pasar",
        description="Scatter PCA 2D (warna per segmen K-Means) · Profil segmen terhitung · Catatan metodologi clustering",
        icon="🗂️",
    )
