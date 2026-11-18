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


def format_timestamp_wib(value) -> str:
    """Display a source timestamp in Jakarta local time."""
    if value is None or pd.isna(value):
        return "-"
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("Asia/Jakarta")
    else:
        timestamp = timestamp.tz_convert("Asia/Jakarta")
    return timestamp.strftime("%d %b %Y, %H:%M WIB")


def build_preprocessing_funnel(audit: dict) -> pd.DataFrame:
    """Build the dashboard's compact row-count funnel from preprocessing metadata."""
    return pd.DataFrame([
        {"Tahap": "Data mentah", "Listing tersisa": audit.get("raw_rows", 0), "Dibuang pada tahap ini": 0},
        {
            "Tahap": "Deduplikasi listing_id",
            "Listing tersisa": audit.get("after_dedup_rows", 0),
            "Dibuang pada tahap ini": audit.get("duplicate_rows_removed", 0) + audit.get("invalid_listing_id_rows", 0),
        },
        {
            "Tahap": "Filter wilayah DKI Jakarta",
            "Listing tersisa": audit.get("after_dki_rows", 0),
            "Dibuang pada tahap ini": audit.get("outside_dki_rows_removed", 0),
        },
        {
            "Tahap": "Penyaringan outlier harga",
            "Listing tersisa": audit.get("clean_rows", 0),
            "Dibuang pada tahap ini": audit.get("outlier_price_rows_removed", 0),
        },
        {"Tahap": "Data siap analisis & modeling", "Listing tersisa": audit.get("clean_rows", 0), "Dibuang pada tahap ini": 0},
    ])


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


def listing_data_context(data: pd.DataFrame) -> str:
    """Summarize listing count, snapshot age, and completeness of key specifications."""
    count = data["listing_id"].nunique() if "listing_id" in data else len(data)
    parts = [f"{count:,} listing unik".replace(",", ".")]
    excluded = int(data.attrs.get("excluded_financing_count", 0))
    if excluded:
        parts.append(f"{excluded:,} indikasi DP/kredit tidak disertakan dalam analisis".replace(",", "."))
    if "fetched_at" in data:
        timestamps = pd.to_datetime(data["fetched_at"], errors="coerce", utc=True).dropna()
        if not timestamps.empty:
            latest = timestamps.max()
            now = pd.Timestamp.now(tz="UTC")
            age_days = max(0, int((now - latest).total_seconds() // 86_400))
            captured = latest.tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M WIB")
            age_text = "hari ini" if age_days == 0 else f"{age_days} hari lalu"
            parts.append(f"snapshot terakhir {captured} ({age_text})")
        elif count:
            parts.append("tanggal pengambilan tidak tercatat")
    specs = []
    for column, label in (("engine_cc", "CC"), ("body_type", "tipe bodi"), ("variant", "varian")):
        if column in data and count:
            present = int(data[column].notna().sum())
            if data[column].dtype == object:
                present = int(data[column].fillna("").astype(str).str.strip().ne("").sum())
            specs.append(f"{label} {present}/{len(data)}")
    if specs:
        parts.append("kelengkapan: " + ", ".join(specs))
    return " · ".join(parts)


def render_data_source_status(data: pd.DataFrame | None = None) -> None:
    """Render one compact, consistent source summary card for a page."""
    import streamlit as st

    from src.data_loader import get_data_source_status

    status = get_data_source_status()
    mode = status.get("mode")
    labels = {"local": "Dataset tersimpan", "cloud": "Arsip cloud", "fallback": "Sumber cadangan"}
    count = 0 if data is None else (data["listing_id"].nunique() if "listing_id" in data else len(data))
    source_label = labels.get(mode, "Data AutoMatch")
    if data is not None and "data_source" in data:
        sources = data["data_source"].dropna().astype(str).unique()
        if len(sources) == 1:
            source_label = {
                "OLX Indonesia": "Dataset OLX bersih",
                "Arsip snapshot OLX": "Snapshot OLX",
            }.get(sources[0], sources[0])
    with st.container(border=True, key="data_source_summary"):
        left, right = st.columns([1, 2.3], vertical_alignment="center")
        with left:
            st.caption("SUMBER DATA")
            st.markdown(f"**{source_label}**")
            if data is not None:
                st.markdown(f"**{count:,} listing unik**".replace(",", "."))
        with right:
            message = status.get("message")
            if mode == "fallback":
                st.warning(message or "Sumber data cadangan sedang digunakan.", icon=":material/cloud_off:")
            elif message:
                st.caption(message)
            if data is not None:
                detail = listing_data_context(data)
                st.caption(detail)
