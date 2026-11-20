"""Reusable UI components for the AutoMatch dashboard redesign.

All components are pure rendering functions; no Streamlit session-state
mutations happen here. Data is computed by the caller and passed in.
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go


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
# Page header
# ---------------------------------------------------------------------------

def page_header(icon: str, title: str, subtitle: str) -> None:
    """Render a consistent page header with icon, title, and subtitle."""
    st.markdown(
        f"""
        <div class="am-page-header">
            <div class="am-page-header-icon">{icon}</div>
            <div>
                <div class="am-page-header-title">{title}</div>
                <div class="am-page-header-subtitle">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# KPI card
# ---------------------------------------------------------------------------

def kpi_card(label: str, value: str, icon: str = "", help_text: str = "") -> None:
    """Render a single KPI card using st.metric for accessibility."""
    st.metric(label=f"{icon} {label}".strip() if icon else label, value=value, help=help_text or None)


def kpi_row(cards: list[dict]) -> None:
    """Render a row of KPI cards.

    Each dict: {"label": str, "value": str, "icon": str, "help": str}
    """
    cols = st.columns(len(cards), gap="small")
    for col, card in zip(cols, cards):
        with col:
            kpi_card(
                label=card.get("label", ""),
                value=card.get("value", "—"),
                icon=card.get("icon", ""),
                help_text=card.get("help", ""),
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
    """Render a single insight card.

    variant: "default" | "warning" | "success" | "info"
    """
    variant_classes = {
        "default": "am-insight-card",
        "warning": "am-insight-card am-insight-warning",
        "success": "am-insight-card am-insight-success",
        "info": "am-insight-card am-insight-info",
    }
    css_class = variant_classes.get(variant, "am-insight-card")
    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="am-insight-icon">{icon}</div>
            <div>
                <div class="am-insight-headline">{headline}</div>
                <div class="am-insight-body">{body}</div>
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
# Plotly chart theme
# ---------------------------------------------------------------------------

def chart_theme() -> dict:
    """Return a consistent Plotly layout dict for all AutoMatch charts."""
    return dict(
        font=dict(family="Inter, 'Segoe UI', system-ui, sans-serif", color=TEXT, size=12),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        margin=dict(l=16, r=16, t=36, b=16),
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
