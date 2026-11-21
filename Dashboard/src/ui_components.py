"""Reusable UI components for the AutoMatch dashboard redesign.

All components are pure rendering functions; no Streamlit session-state
mutations happen here. Data is computed by the caller and passed in.
"""

from __future__ import annotations

import base64
import contextlib
from pathlib import Path
import re
import streamlit as st
import plotly.graph_objects as go

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


# ---------------------------------------------------------------------------
# Design tokens (mirror src/styles.py COLORS for Plotly use)
# ---------------------------------------------------------------------------

NAVY = "#0D1E38"
TEAL = "#019F90"
TEAL_DARK = "#008276"
TEAL_LIGHT = "#E6F7F5"
TEAL_100 = "#CCFBF1"
MUTED = "#475569"
TEXT = "#0D1E38"
BORDER = "#E2E8F0"
BG = "#F8FAFC"
WHITE = "#FFFFFF"

CHART_COLORS = ["#019F90", "#0D1E38", "#00B8A9", "#007A6E", "#38D9A9", "#63E6BE", "#0F766E", "#155E75"]


# ---------------------------------------------------------------------------
# Lucide SVG Icon System (outline, stroke-width 1.75, fill none, 24x24)
# ---------------------------------------------------------------------------

_LUCIDE_PATHS: dict[str, str] = {
    "car": (
        '<path d="M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1l3-4h8l3 4h1a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-2"/>'
        '<circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/>'
    ),
    "tag": (
        '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/>'
        '<circle cx="7.5" cy="7.5" r="1.5"/>'
    ),
    "banknote": (
        '<rect width="20" height="12" x="2" y="6" rx="2"/>'
        '<circle cx="12" cy="12" r="2"/>'
        '<path d="M6 12h.01M18 12h.01"/>'
    ),
    "calendar": (
        '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>'
        '<line x1="16" x2="16" y1="2" y2="6"/>'
        '<line x1="8" x2="8" y1="2" y2="6"/>'
        '<line x1="3" x2="21" y1="10" y2="10"/>'
    ),
    "trending-up": (
        '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
        '<polyline points="16 7 22 7 22 13"/>'
    ),
    "bar-chart-2": (
        '<line x1="18" x2="18" y1="20" y2="10"/>'
        '<line x1="12" x2="12" y1="20" y2="4"/>'
        '<line x1="6" x2="6" y1="20" y2="14"/>'
    ),
    "search": (
        '<circle cx="11" cy="11" r="8"/>'
        '<path d="m21 21-4.35-4.35"/>'
    ),
    "check-circle": (
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/>'
    ),
    "settings": (
        '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "award": (
        '<circle cx="12" cy="8" r="6"/>'
        '<path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>'
    ),
    "map-pin": (
        '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>'
        '<circle cx="12" cy="10" r="3"/>'
    ),
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "activity": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "target": (
        '<circle cx="12" cy="12" r="10"/>'
        '<circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2"/>'
    ),
    "cpu": (
        '<rect width="16" height="16" x="4" y="4" rx="2"/>'
        '<rect width="6" height="6" x="9" y="9" rx="1"/>'
        '<path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M12 16v-4"/>'
        '<path d="M12 8h.01"/>'
    ),
    "trophy": (
        '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>'
        '<path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>'
        '<path d="M4 22h16"/>'
        '<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
        '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>'
        '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>'
    ),
    "pie-chart": (
        '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/>'
        '<path d="M22 12A10 10 0 0 0 12 2v10z"/>'
    ),
    "gauge": (
        '<path d="m12 14 4-4"/>'
        '<path d="M3.34 19a10 10 0 1 1 17.32 0"/>'
    ),
    "arrow-up-right": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    "arrow-down-right": '<path d="M7 7h10v10"/><path d="m17 7-10 10"/>',
    "minus": '<path d="M5 12h14"/>',
    "layers": (
        '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/>'
        '<path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/>'
        '<path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>'
    ),
    "git-branch": (
        '<line x1="6" x2="6" y1="3" y2="15"/>'
        '<circle cx="18" cy="6" r="3"/>'
        '<circle cx="6" cy="18" r="3"/>'
        '<path d="M18 9a9 9 0 0 1-9 9"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
        '<path d="M3 5V19a9 3 0 0 0 18 0V5"/>'
        '<path d="M3 12a9 3 0 0 0 18 0"/>'
    ),
    "layout-dashboard": (
        '<rect width="7" height="9" x="3" y="3" rx="1"/>'
        '<rect width="7" height="5" x="14" y="3" rx="1"/>'
        '<rect width="7" height="9" x="14" y="12" rx="1"/>'
        '<rect width="7" height="5" x="3" y="16" rx="1"/>'
    ),
    "sliders": (
        '<line x1="4" x2="4" y1="21" y2="14"/>'
        '<line x1="4" x2="4" y1="6" y2="3"/>'
        '<line x1="12" x2="12" y1="21" y2="12"/>'
        '<line x1="12" x2="12" y1="6" y2="3"/>'
        '<line x1="20" x2="20" y1="21" y2="16"/>'
        '<line x1="20" x2="20" y1="10" y2="3"/>'
        '<line x1="1" x2="7" y1="14" y2="14"/>'
        '<line x1="9" x2="15" y1="12" y2="12"/>'
        '<line x1="17" x2="23" y1="16" y2="16"/>'
    ),
}


def get_lucide_icon(name: str, size: int = 16, color: str = "#64748B") -> str:
    """Return an inline SVG string for a Lucide icon.

    Args:
        name:  Lucide icon slug, e.g. "car", "bar-chart-2", "search".
        size:  Width and height in pixels (default 16).
        color: Stroke colour (default slate-500 #64748B).

    Returns:
        A self-contained ``<svg>`` HTML string.
    """
    path_data = _LUCIDE_PATHS.get(name, _LUCIDE_PATHS["minus"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        f'style="display:inline-block;vertical-align:middle;flex-shrink:0;">'
        f'{path_data}</svg>'
    )


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
        bg_style = f"background-image: linear-gradient(90deg, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.92) 40%, rgba(255,255,255,0.50) 70%, rgba(255,255,255,0.15) 100%), url('data:image/jpeg;base64,{b64}');"

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
    """Render a consistent page header with a Lucide SVG icon.

    icon:  A Lucide icon slug (e.g. 'bar-chart-2') or empty string to omit.
    """
    icon_html = ""
    if icon:
        svg = get_lucide_icon(icon, size=20, color=TEAL)
        icon_html = (
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:2.2rem;height:2.2rem;border-radius:8px;background:#E6F7F5;flex-shrink:0;">'
            f'{svg}</span>'
        )
    st.markdown(
        f"""
        <div class="am-page-header">
            {icon_html}
            <div>
                <div class="am-page-header-title">{title}</div>
                <div class="am-page-header-subtitle">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# KPI card  (Chronicle / Shadcn flat style)
# ---------------------------------------------------------------------------

def kpi_card(
    label: str,
    value: str,
    icon: str = "",
    help_text: str = "",
    variant: str = "default",
    subtext: str = "",
) -> None:
    """Render a Chronicle-style flat KPI card with thematic Lucide icon badge.

    icon:    Lucide icon slug (e.g. 'car', 'banknote'). Empty string to omit.
    subtext: Optional secondary caption below the main value.
    """
    icon_badge_html = ""
    if icon:
        svg = get_lucide_icon(icon, size=18, color=TEAL)
        icon_badge_html = (
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:2.1rem;height:2.1rem;border-radius:8px;background:#E6F7F5;flex-shrink:0;">{svg}</span>'
        )

    title_attr = f'title="{help_text}"' if help_text else ""
    sub_html = f'<div style="font-size:0.75rem;color:#64748B;margin-top:0.2rem;line-height:1.35;">{subtext}</div>' if subtext else ""

    st.markdown(
        f"""
        <div class="am-kpi-card" {title_attr}>
            <div style="display:flex;align-items:center;justify-content:space-between;gap:0.5rem;">
                <div class="am-kpi-label">{label}</div>
                {icon_badge_html}
            </div>
            <div class="am-kpi-value">{value}</div>
            {sub_html}
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
                variant=card.get("variant", "default"),
                subtext=card.get("subtext", ""),
            )


# ---------------------------------------------------------------------------
# Section card
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def section_card(title: str = "", key: str = ""):
    """Return a bordered container that wraps both the section title and content inside one card."""
    with st.container(border=True, key=key if key else None):
        if title:
            st.markdown(f"<div class='am-section-title'>{title}</div>", unsafe_allow_html=True)
        yield


# ---------------------------------------------------------------------------
# Insight card
# ---------------------------------------------------------------------------

def insight_card(icon: str, headline: str, body: str, variant: str = "default") -> None:
    """Render a single insight card with a Lucide SVG icon.

    icon:    Lucide icon slug (e.g. 'trophy', 'map-pin', 'zap').
    variant: 'default' | 'warning' | 'success' | 'info'
    """
    variant_classes = {
        "default": "am-insight-card",
        "warning": "am-insight-card am-insight-warning",
        "success": "am-insight-card am-insight-success",
        "info": "am-insight-card am-insight-info",
    }
    css_class = variant_classes.get(variant, "am-insight-card")
    body_html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", body)

    icon_color_map = {
        "default": "#475569",
        "warning": "#D97706",
        "success": "#059669",
        "info": TEAL,
    }
    icon_color = icon_color_map.get(variant, "#475569")
    icon_svg = get_lucide_icon(icon, size=18, color=icon_color) if icon else ""

    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="am-insight-icon">{icon_svg}</div>
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

def coming_soon_placeholder(page_name: str, description: str, icon: str = "layers") -> None:
    """Render a placeholder card for a page not yet implemented.

    icon: Lucide icon slug.
    """
    icon_svg = get_lucide_icon(icon, size=32, color="#94A3B8")
    st.markdown(
        f"""
        <div class="am-coming-soon">
            <div class="am-coming-soon-icon">{icon_svg}</div>
            <div class="am-coming-soon-title">{page_name}</div>
            <div class="am-coming-soon-desc">{description}</div>
            <div class="am-coming-soon-badge">Fase implementasi berikutnya</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
