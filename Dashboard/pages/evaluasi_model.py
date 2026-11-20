"""Evaluasi Model — perbandingan performa model regresi harga mobil.

Menampilkan toggle LR/RF, KPI MAE/RMSE/R², Actual vs Predicted,
Residual Plot, Feature Importance, dan tabel perbandingan semua kandidat.
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
    icon="📐",
    title="Evaluasi Model",
    subtitle="Membandingkan performa model regresi harga mobil — Linear Regression vs Random Forest.",
)

st.info(
    "Halaman ini sedang diimplementasikan (Fase 5). Konten lengkap akan tersedia setelah implementasi selesai.",
    icon=":material/info:",
)

coming_soon_placeholder(
    page_name="Evaluasi Model",
    description="Toggle Linear Regression / Random Forest · KPI MAE, RMSE, R² · Actual vs Predicted · Residual Plot · Feature Importance · Tabel perbandingan 6 kandidat · Badge model terpilih",
    icon="📐",
)
