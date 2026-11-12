"""Reusable UI helpers for the dashboard."""

from __future__ import annotations

import pandas as pd


def format_rupiah(value) -> str:
    """Format an integer-like value as Indonesian Rupiah."""
    if pd.isna(value):
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"Rp {number:,.0f}"


def format_km(value) -> str:
    """Format kilometer value to a local-friendly string."""
    if pd.isna(value):
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,.0f} km"


def build_kpi_card(label: str, value: str, delta: str | None = None) -> None:
    """Render a compact KPI card using Streamlit layout primitives."""
    import streamlit as st

    with st.container():
        st.markdown('<div class="kpi-box">', unsafe_allow_html=True)
        st.caption(label)
        st.markdown(f"<h3>{value}</h3>", unsafe_allow_html=True)
        if delta:
            st.caption(delta)
        st.markdown('</div>', unsafe_allow_html=True)


def render_empty_state(title: str, message: str) -> None:
    """Render a friendly empty-state block."""
    import streamlit as st

    st.info(f"**{title}**\n\n{message}")
