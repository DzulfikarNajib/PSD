"""Theme-aware styling for a calm, automotive-inspired buyer experience."""

import streamlit as st


CSS = """
<style>
:root {
    --dashboard-bg: var(--background-color, #f3f5f2);
    --dashboard-surface: var(--secondary-background-color, #ffffff);
    --dashboard-text: var(--text-color, #14283b);
    --dashboard-accent: var(--primary-color, #0b806b);
    --dashboard-muted: color-mix(in srgb, var(--dashboard-text) 78%, transparent);
    --dashboard-border: color-mix(in srgb, var(--dashboard-text) 12%, transparent);
}

.stApp {
    background: var(--dashboard-bg);
    color: var(--dashboard-text);
    font-family: Inter, "Segoe UI", system-ui, sans-serif;
}

[data-testid="stAppViewContainer"] { background: var(--dashboard-bg); }
[data-testid="stSidebar"] {
    background: var(--dashboard-surface);
    border-right: 1px solid var(--dashboard-border);
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    border-radius: 10px;
    padding: .45rem .6rem;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: color-mix(in srgb, var(--dashboard-accent) 9%, transparent);
}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: var(--dashboard-text); }

h1, h2, h3, h4 { letter-spacing: -0.025em; color: var(--dashboard-text); }
[data-testid="stCaptionContainer"] { color: var(--dashboard-muted); }
[data-testid="stAppViewContainer"] h1 { font-size: clamp(2.2rem, 4vw, 3.4rem); }

.stMetric {
    background: var(--dashboard-surface);
    border: 1px solid var(--dashboard-border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: 0 3px 14px color-mix(in srgb, var(--dashboard-text) 5%, transparent);
}
.stMetric label, .stMetric [data-testid="stMetricLabel"] { color: var(--dashboard-muted); }
.stMetric [data-testid="stMetricValue"] { color: var(--dashboard-text); }
.stMetric [data-testid="stMetricValue"] { font-size: clamp(1rem, 1.7vw, 1.55rem); overflow-wrap: anywhere; }

.card, [data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--dashboard-border);
    border-radius: 16px;
}
.card {
    background: var(--dashboard-surface);
    border: 1px solid var(--dashboard-border);
    padding: 1.1rem 1.25rem;
    box-shadow: 0 8px 28px color-mix(in srgb, var(--dashboard-text) 6%, transparent);
}
.car-price {
    color: var(--dashboard-accent);
    font-size: 1.45rem;
    font-weight: 750;
    letter-spacing: -.025em;
    margin: -.25rem 0 .2rem;
}
.car-photo-fallback {
    min-height: 190px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: .35rem;
    border-radius: 14px;
    color: #52665f;
    background: linear-gradient(145deg, #e9eee9, #d9e4df);
}
.car-photo-fallback span { font-size: 3.2rem; }
.car-photo-fallback small { font-size: .8rem; }
.kpi-box {
    background: var(--dashboard-surface);
    border: 1px solid var(--dashboard-border);
    border-top: 3px solid var(--dashboard-accent);
    border-radius: 14px;
    padding: 1rem;
}

.stButton > button, [data-testid="stLinkButton"] a {
    border-radius: 11px;
    font-weight: 650;
}
div.stAlert { border-radius: 12px; }
[data-testid="stDataFrame"] { border: 1px solid var(--dashboard-border); border-radius: 12px; }
[data-testid="stPlotlyChart"] { border-radius: 12px; }
@media (max-width: 700px) {
    .car-photo-fallback { min-height: 130px; }
    .car-price { font-size: 1.2rem; }
}
</style>
"""


def apply_theme() -> None:
    """Apply theme-aware CSS; page configuration belongs to app.py navigation."""
    st.markdown(CSS, unsafe_allow_html=True)
