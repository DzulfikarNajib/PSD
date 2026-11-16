"""Reusable UI helpers for the dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd


def format_rupiah(value) -> str:
    """Format an integer-like value as Indonesian Rupiah."""
    if pd.isna(value):
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"Rp {number:,.0f}".replace(",", ".")


def format_rupiah_compact(value) -> str:
    """Format Rupiah compactly as Rp ... Jt or Rp ... M."""
    if pd.isna(value):
        return "-"
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    if val >= 1_000_000_000:
        m = val / 1_000_000_000
        return f"Rp {m:.1f} M".replace(".0 M", " M").replace(".", ",")
    if val >= 1_000_000:
        jt = val / 1_000_000
        return f"Rp {jt:.0f} Jt" if jt % 1 == 0 else f"Rp {jt:.1f} Jt".replace(".", ",")
    return f"Rp {val:,.0f}".replace(",", ".")


def format_km(value) -> str:
    """Format kilometer value to a local-friendly string."""
    if pd.isna(value):
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,.0f} km".replace(",", ".")


def apply_rupiah_ticks(fig, axis="x", min_val=None, max_val=None, n_ticks=6):
    """Ensure Plotly axis uses human-readable Rupiah labels instead of G/M SI prefixes."""
    if min_val is None or max_val is None or min_val >= max_val:
        return
    vals = np.linspace(min_val, max_val, n_ticks)
    step = (max_val - min_val) / (n_ticks - 1)
    if step > 500_000_000:
        round_base = 500_000_000
    elif step > 100_000_000:
        round_base = 100_000_000
    elif step > 50_000_000:
        round_base = 50_000_000
    elif step > 10_000_000:
        round_base = 10_000_000
    else:
        round_base = 1_000_000
    vals = np.unique(np.round(vals / round_base) * round_base)
    vals = [v for v in vals if min_val <= v <= max_val]
    if len(vals) < 2:
        vals = [min_val, max_val]
    labels = [format_rupiah_compact(v) for v in vals]
    if axis == "x":
        fig.update_xaxes(tickmode="array", tickvals=vals, ticktext=labels)
    else:
        fig.update_yaxes(tickmode="array", tickvals=vals, ticktext=labels)


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
