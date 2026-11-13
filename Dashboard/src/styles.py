"""Theme-aware styling for a calm, automotive-inspired buyer experience."""

import streamlit as st


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
:root {
    --dashboard-bg: var(--background-color, #ffffff);
    --dashboard-surface: var(--secondary-background-color, #ffffff);
    --dashboard-text: var(--text-color, #102748);
    --dashboard-accent: var(--primary-color, #1778c8);
    --dashboard-muted: #52677d;
    --dashboard-border: #d9e5f2;
}

.stApp {
    background: var(--dashboard-bg);
    color: var(--dashboard-text);
    font-family: Inter, "Segoe UI", system-ui, sans-serif;
}

[data-testid="stAppViewContainer"] { background: var(--dashboard-bg); }
[data-testid="stMainBlockContainer"] { max-width: 1540px; padding-top: 4rem; padding-bottom: 4rem; }
div[class*="st-key-automatch_topnav"] {
    /* Keep this in document flow below Streamlit's fixed toolbar. A sticky bar
       can slide underneath that toolbar on Community Cloud. */
    position: relative;
    top: auto;
    z-index: 999;
    background: rgba(255, 255, 255, .98);
    border: 1px solid #dce6f1;
    border-radius: 18px;
    margin: 0 -1.5rem 1.35rem;
    padding: .28rem 1.3rem;
    box-shadow: 0 5px 20px rgba(16, 39, 72, .045);
    backdrop-filter: blur(14px);
}
div[class*="st-key-automatch_topnav"] [data-testid="stHorizontalBlock"] { gap: .4rem; align-items:center !important; }
div[class*="st-key-automatch_topnav"] [data-testid="stColumn"] { display:flex; align-items:center; }
div[class*="st-key-automatch_topnav"] [data-testid="stMarkdownContainer"] { margin:0; padding:0; }
div[class*="st-key-automatch_topnav"] [data-testid="stPageLink"] { min-width: max-content; }
div[class*="st-key-automatch_topnav"] [data-testid="stPageLink"] a {
    min-height: 2.65rem;
    display: flex;
    align-items: center;
    padding: .35rem .45rem;
    border-radius: 0;
    color: #41556c;
    font-size: .82rem;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
}
div[class*="st-key-automatch_topnav"] [data-testid="stPageLink"] a:hover { color: #087f86; background: transparent; }
div[class*="st-key-nav_active_"] [data-testid="stPageLink"] a {
    color: #087f86 !important;
    border-bottom: 2px solid #109fa4;
}
.automatch-brand {
    display:flex;
    align-items:center;
    justify-content:flex-start;
    gap:.8rem;
    height:2.65rem;
    min-width:0;
    white-space:nowrap;
}
.automatch-brand img {
    display:block;
    flex:0 0 auto;
    width:7rem;
    height:1.8rem;
    object-fit:contain;
    object-position:left center;
}
.automatch-brand span {
    display:block;
    color:#102748;
    font-family:"Plus Jakarta Sans",Inter,sans-serif;
    font-size:.9rem;
    font-weight:650;
    line-height:1;
    letter-spacing:-.015em;
}
div[class*="st-key-automatch_topnav"] .stButton > button { min-height:2.65rem; border-radius:999px; padding:.2rem .7rem; font-size:.78rem; white-space:nowrap; }
[data-testid="stAppViewContainer"] h1 { font-size: clamp(2rem, 3.7vw, 3.25rem); }
div[class*="st-key-home_hero"] {
    position: relative;
    overflow: hidden;
    min-height: 410px;
    display: flex;
    align-items: center;
    background-color: #dce8e5;
    background-image: linear-gradient(90deg, rgba(247,249,247,.98) 0%, rgba(247,249,247,.92) 36%, rgba(247,249,247,.42) 62%, rgba(247,249,247,.04) 100%), var(--automatch-hero-image);
    background-position: center, center 56%;
    background-size: cover;
    border: 1px solid #e5eaed;
    border-radius: 24px;
    padding: 2.3rem 2.5rem;
    box-shadow: 0 16px 40px rgba(16, 39, 72, .10);
}
div[class*="st-key-home_hero"] .home-hero-copy { max-width: 610px; }
div[class*="st-key-home_hero"] h1 { font-size: clamp(2.8rem, 5vw, 4.8rem); margin-bottom: .25rem; }
div[class*="st-key-home_hero"] [data-testid="stCaptionContainer"] { color: #536779; }

div[class*="st-key-project_editorial_hero"] {
    background: linear-gradient(110deg, #edf8f6, #fbfcfa 62%);
    border: 1px solid #e5eaed;
    border-radius: 22px;
    padding: 1.15rem 1.4rem;
    margin-bottom: 1.3rem;
}
.project-illustration { padding:.7rem; text-align:center; color:#718096; font-size:.76rem; }
.project-illustration svg { display:block; width:100%; max-height:250px; }
.project-illustration span { display:block; margin-top:.2rem; }
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

h1, h2, h3, h4 { letter-spacing: -0.03em; color: var(--dashboard-text); font-family: "Plus Jakarta Sans", Inter, "Segoe UI", system-ui, sans-serif; }
[data-testid="stCaptionContainer"] { color: var(--dashboard-muted); }
[data-testid="stAppViewContainer"] h1 { font-size: clamp(2.2rem, 4vw, 3.4rem); }

.stMetric {
    background: var(--dashboard-surface);
    border: 1px solid var(--dashboard-border);
    border-radius: 20px;
    padding: .8rem .95rem;
    box-shadow: 0 6px 20px rgba(29, 64, 108, .07);
}
.stMetric label, .stMetric [data-testid="stMetricLabel"] { color: var(--dashboard-muted); }
.stMetric [data-testid="stMetricValue"] { color: var(--dashboard-text); }
.stMetric [data-testid="stMetricValue"] { font-size: clamp(1rem, 1.7vw, 1.55rem); overflow-wrap: anywhere; }
[data-testid="stMetricLabel"] p { font-size: .82rem; }

.card, [data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--dashboard-border);
    border-radius: 22px;
}
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #fff;
    border: 1px solid #dce6f1;
    box-shadow: 0 8px 24px rgba(29, 64, 108, .075);
}
.card {
    background: var(--dashboard-surface);
    border: 1px solid var(--dashboard-border);
    padding: 1.1rem 1.25rem;
    box-shadow: 0 8px 28px color-mix(in srgb, var(--dashboard-text) 6%, transparent);
}
[data-testid="stImage"] img { border-radius: 17px; aspect-ratio: 16 / 9; object-fit: cover; }
[data-testid="stImage"] figcaption { color: var(--dashboard-muted); font-size: .78rem; }

[data-testid="stPlotlyChart"] { padding: .35rem; border-radius: 18px; background:#fff; }
.stMarkdown p { line-height: 1.65; }
.stButton > button[kind="primary"] { box-shadow: 0 7px 18px color-mix(in srgb, var(--dashboard-accent) 20%, transparent); }
.stButton > button:hover { transform: translateY(-1px); transition: transform .15s ease, box-shadow .15s ease; }
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
.listing-spec { display:flex; justify-content:space-between; gap:.5rem; padding:.2rem 0; border-bottom:1px solid #eef1f2; font-size:.79rem; }
.listing-spec span { color:#718096; }
.listing-spec b { color:#102748; font-weight:600; text-align:right; }
.price-hero-value { color:#109fa4; font-family:"Plus Jakarta Sans",sans-serif; font-size:clamp(1.65rem,2.7vw,2.3rem); font-weight:800; letter-spacing:-.045em; }
.kpi-box {
    background: var(--dashboard-surface);
    border: 1px solid var(--dashboard-border);
    border-top: 3px solid var(--dashboard-accent);
    border-radius: 14px;
    padding: 1rem;
}

.stButton > button, [data-testid="stLinkButton"] a {
    border-radius: 999px;
    font-weight: 650;
}
div.stAlert { border-radius: 12px; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div { border-radius:10px; border-color:#dce4e6; }
[data-testid="stRadio"] div[role="radiogroup"] { gap:.35rem; }
[data-testid="stRadio"] div[role="radiogroup"] label { background:#fff; border:1px solid #e5eaed; border-radius:999px; padding:.35rem .8rem; }
[data-testid="stDataFrame"] { border: 1px solid var(--dashboard-border); border-radius: 12px; }
[data-testid="stPlotlyChart"] { border-radius: 12px; }
@media (max-width: 700px) {
    [data-testid="stMainBlockContainer"] { padding-top: 3.5rem; }
    div[class*="st-key-automatch_topnav"] { overflow-x:auto; margin: 0 -1rem 1rem; padding:.4rem .75rem; }
    div[class*="st-key-home_hero"] { min-height: 470px; align-items:flex-end; padding:1.4rem; background-image:linear-gradient(0deg, rgba(247,249,247,.98) 0%, rgba(247,249,247,.91) 48%, rgba(247,249,247,.10) 100%), var(--automatch-hero-image); background-position:center, 58% top; }
    div[class*="st-key-home_hero"] .home-hero-copy { max-width:100%; }
    .automatch-brand { gap:0; }
    .automatch-brand span { display:none; }
    .car-photo-fallback { min-height: 130px; }
    .car-price { font-size: 1.2rem; }
    [data-testid="stMetricValue"] { font-size: 1.15rem !important; }
}
</style>
"""


def apply_theme() -> None:
    """Apply theme-aware CSS; page configuration belongs to app.py navigation."""
    st.markdown(CSS, unsafe_allow_html=True)
