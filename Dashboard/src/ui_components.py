"""Reusable UI components for the AutoMatch dashboard redesign.

All components are pure rendering functions; no Streamlit session-state
mutations happen here. Data is computed by the caller and passed in.
"""

from __future__ import annotations

import base64
from pathlib import Path
import re
import streamlit as st
import plotly.graph_objects as go

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


# ---------------------------------------------------------------------------
# Design tokens (mirror src/styles.py COLORS for Plotly use)
# ---------------------------------------------------------------------------

NAVY = "#0B2A5B"
TEAL = "#008B8B"
TEAL_DARK = "#066B6B"
TEAL_LIGHT = "#E3F6F5"
TEAL_100 = "#CCEFEE"
MUTED = "#475569"
TEXT = "#0F172A"
BORDER = "#E2E8F0"
BG = "#F8FAFC"
WHITE = "#FFFFFF"

CHART_COLORS = [TEAL, "#0F766E", "#0369A1", "#F59E0B", "#10B981", "#64748B", "#7C3AED", "#EA580C"]


# ---------------------------------------------------------------------------
# Hero banner (Master Reference Design)
# ---------------------------------------------------------------------------

def hero_banner(
    title: str = "AutoMatch",
    subtitle: str = "Analisis Pasar Mobil Bekas di DKI Jakarta",
    description: str = "Memahami karakteristik, menemukan pola, dan memprediksi harga mobil bekas dengan pendekatan data science.",
    image_filename: str = "hero-bmw.jpg",
) -> None:
    """Render a compact visual hero banner matching the master reference design."""
    img_path = ASSETS_DIR / image_filename
    bg_style = ""
    if img_path.exists():
        b64 = base64.b64encode(img_path.read_bytes()).decode()
        bg_style = f"background-image: linear-gradient(90deg, #FFFFFF 0%, rgba(255,255,255,0.96) 42%, rgba(255,255,255,0.55) 65%, rgba(255,255,255,0.0) 100%), url('data:image/jpeg;base64,{b64}');"

    st.markdown(
        f"""
        <div class="am-hero-compact" style="{bg_style}">
            <div class="am-hero-compact-content">
                <div class="am-hero-compact-title">{title}</div>
                <div class="am-hero-compact-subtitle">{subtitle}</div>
                <div class="am-hero-compact-desc">{description}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

def page_header(icon: str, title: str, subtitle: str) -> None:
    """Render a consistent page header with icon merged directly into the title string."""
    icon_prefix = f"{icon} " if icon else ""
    st.markdown(
        f"""
        <div class="am-page-header">
            <div>
                <div class="am-page-header-title">{icon_prefix}{title}</div>
                <div class="am-page-header-subtitle">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# KPI card
# ---------------------------------------------------------------------------

def kpi_card(
    label: str,
    value: str,
    icon: str = "",
    help_text: str = "",
    variant: str = "teal",
) -> None:
    """Render a single KPI card matching the master reference design."""
    badge_classes = {
        "teal": "am-kpi-badge-teal",
        "navy": "am-kpi-badge-navy",
        "amber": "am-kpi-badge-amber",
        "blue": "am-kpi-badge-blue",
        "green": "am-kpi-badge-green",
    }
    badge_cls = badge_classes.get(variant, "am-kpi-badge-teal")
    icon_html = f'<div class="am-kpi-icon-badge {badge_cls}">{icon}</div>' if icon else ""
    title_attr = f'title="{help_text}"' if help_text else ""

    st.markdown(
        f"""
        <div class="am-kpi-card" {title_attr}>
            {icon_html}
            <div>
                <div class="am-kpi-label">{label}</div>
                <div class="am-kpi-value">{value}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(cards: list[dict]) -> None:
    """Render a row of KPI cards.

    Each dict: {"label": str, "value": str, "icon": str, "help": str, "variant": str}
    """
    cols = st.columns(len(cards), gap="small")
    for col, card in zip(cols, cards):
        with col:
            kpi_card(
                label=card.get("label", ""),
                value=card.get("value", "-"),
                icon=card.get("icon", ""),
                help_text=card.get("help", ""),
                variant=card.get("variant", "teal"),
            )


# ---------------------------------------------------------------------------
# Section card
# ---------------------------------------------------------------------------

def section_card(title: str = "", key: str = "") -> "contextlib._GeneratorContextManager":
    """Return a bordered container to wrap a chart or section.

    Usage:
        with section_card("Judul"):
            st.plotly_chart(fig)
    """
    if title:
        st.markdown(f"<div class='am-section-title'>{title}</div>", unsafe_allow_html=True)
    return st.container(border=True, key=key if key else None)


# ---------------------------------------------------------------------------
# Insight card
# ---------------------------------------------------------------------------

def insight_card(icon: str, headline: str, body: str, variant: str = "default") -> None:
    """Render a single insight card with automatic markdown **bold** to <b>bold</b> conversion.

    variant: "default" | "warning" | "success" | "info"
    """
    variant_classes = {
        "default": "am-insight-card",
        "warning": "am-insight-card am-insight-warning",
        "success": "am-insight-card am-insight-success",
        "info": "am-insight-card am-insight-info",
    }
    css_class = variant_classes.get(variant, "am-insight-card")
    body_html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", body)
    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="am-insight-icon">{icon}</div>
            <div>
                <div class="am-insight-headline">{headline}</div>
                <div class="am-insight-body">{body_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Status badge (Cek Harga)
# ---------------------------------------------------------------------------

def status_badge(status: str) -> str:
    """Return HTML for a price status badge.

    status: "Di Bawah Kisaran Pasar" | "Harga Wajar" | "Di Atas Kisaran Pasar"
    """
    if "bawah" in status.lower():
        return f'<span class="badge-underpriced">{status}</span>'
    if "atas" in status.lower():
        return f'<span class="badge-overpriced">{status}</span>'
    return f'<span class="badge-fair">{status}</span>'


# ---------------------------------------------------------------------------
# Price Deviation Barometer (Cek Harga Gauge)
# ---------------------------------------------------------------------------

def price_deviation_barometer(
    asking_price: float,
    median_price: float,
    p25: float | None = None,
    p75: float | None = None,
) -> go.Figure:
    """Return a half-donut gauge showing asking price position relative to market.

    Provides the visual balance of the master reference gauge while strictly
    adhering to statistically sound market deviation metrics (anti-slop).
    """
    if median_price <= 0:
        pct_diff = 0.0
    else:
        pct_diff = ((asking_price - median_price) / median_price) * 100

    # Normalize to a 0-100 gauge scale where 50 is exact median,
    # 25 is -15% (underpriced), 75 is +15% (overpriced)
    gauge_val = max(5.0, min(95.0, 50.0 + (pct_diff * 1.67)))

    if abs(pct_diff) <= 8.0:
        bar_color = TEAL
        status_text = "Harga Wajar"
    elif pct_diff < -8.0:
        bar_color = "#10B981"
        status_text = "Di Bawah Pasar"
    else:
        bar_color = "#F59E0B"
        status_text = "Di Atas Pasar"

    sign_prefix = "+" if pct_diff > 0 else ""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=gauge_val,
        number={
            "suffix": "%",
            "font": {"size": 26, "family": "Plus Jakarta Sans, sans-serif", "color": TEXT},
            "valueformat": ".0f",
        },
        title={
            "text": f"<b>{status_text}</b><br><span style='font-size:0.82rem; color:{bar_color}; font-weight:700;'>{sign_prefix}{pct_diff:.1f}% vs median</span>",
            "font": {"size": 13, "family": "Inter, sans-serif", "color": TEXT},
        },
        gauge={
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": bar_color, "thickness": 0.28},
            "bgcolor": "#F1F5F9",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 35], "color": "#E6F4EA"},
                {"range": [35, 65], "color": "#E3F6F5"},
                {"range": [65, 100], "color": "#FEF3C7"},
            ],
            "threshold": {
                "line": {"color": NAVY, "width": 3},
                "thickness": 0.75,
                "value": gauge_val,
            },
        },
    ))
    fig.update_layout(
        height=180,
        margin=dict(l=15, r=15, t=10, b=10),
        paper_bgcolor=WHITE,
        font=dict(family="Inter, sans-serif"),
    )
    return fig


# ---------------------------------------------------------------------------
# Plotly chart theme
# ---------------------------------------------------------------------------

def chart_theme() -> dict:
    """Return a consistent Plotly layout dict for all AutoMatch charts."""
    return dict(
        font=dict(family="Inter, 'Segoe UI', system-ui, sans-serif", color=TEXT, size=12),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        margin=dict(l=12, r=12, t=16, b=12),
        colorway=CHART_COLORS,
        xaxis=dict(
            gridcolor="#F1F5F9",
            linecolor=BORDER,
            tickfont=dict(size=11, color=MUTED),
            title_font=dict(size=12, color=MUTED),
        ),
        yaxis=dict(
            gridcolor="#F1F5F9",
            linecolor=BORDER,
            tickfont=dict(size=11, color=MUTED),
            title_font=dict(size=12, color=MUTED),
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=BORDER,
            borderwidth=1,
            font=dict(size=11),
        ),
        hoverlabel=dict(
            bgcolor=WHITE,
            bordercolor=BORDER,
            font=dict(family="Inter, sans-serif", size=12, color=TEXT),
        ),
    )


def apply_chart_theme(fig: go.Figure) -> go.Figure:
    """Apply the AutoMatch chart theme to an existing Plotly figure."""
    fig.update_layout(**chart_theme())
    return fig


# ---------------------------------------------------------------------------
# Coming-soon placeholder (used in Fase 1 for pages not yet implemented)
# ---------------------------------------------------------------------------

def coming_soon_placeholder(page_name: str, description: str, icon: str = "🚧") -> None:
    """Render a placeholder card for a page not yet implemented."""
    st.markdown(
        f"""
        <div class="am-coming-soon">
            <div class="am-coming-soon-icon">{icon}</div>
            <div class="am-coming-soon-title">{page_name}</div>
            <div class="am-coming-soon-desc">{description}</div>
            <div class="am-coming-soon-badge">Fase implementasi berikutnya</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
