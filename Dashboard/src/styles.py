"""Theme-aware styling for the AutoMatch dashboard (navy/teal sidebar layout)."""

import streamlit as st


COLORS = {
    "background": "#F8FAFC",
    "surface": "#FFFFFF",
    "navy": "#0B2A5B",
    "navy_dark": "#071B3A",
    "text": "#0F172A",
    "muted": "#475569",
    "accent": "#008B8B",
    "accent_hover": "#066B6B",
    "accent_light": "#E3F6F5",
    "border": "#E2E8F0",
    "grid": "#F1F5F9",
    "warning": "#F59E0B",
    "under_background": "#ECFDF5",
    "under_text": "#047857",
    "under_border": "#A7F3D0",
    "fair_background": "#F0FDFA",
    "fair_text": "#008B8B",
    "fair_border": "#99F6E4",
    "over_background": "#FEF2F2",
    "over_text": "#B91C1C",
    "over_border": "#FECACA",
}
CHART_PALETTE = (COLORS["accent"], "#0F766E", "#0369A1", COLORS["warning"], "#10B981", "#64748B")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,0,0&display=swap');
:root {
    --dashboard-bg: #F8FAFC;
    --dashboard-soft: #FFFFFF;
    --dashboard-surface: #FFFFFF;
    --dashboard-text: #0F172A;
    --dashboard-navy: #0B2A5B;
    --dashboard-navy-dark: #071B3A;
    --dashboard-accent: #008B8B;
    --dashboard-accent-hover: #066B6B;
    --dashboard-accent-light: #E3F6F5;
    --dashboard-muted: #475569;
    --dashboard-border: #E2E8F0;
    --status-under-background: #ECFDF5;
    --status-under-text: #047857;
    --status-under-border: #A7F3D0;
    --status-fair-background: #F0FDFA;
    --status-fair-text: #008B8B;
    --status-fair-border: #99F6E4;
    --status-over-background: #FEF2F2;
    --status-over-text: #B91C1C;
    --status-over-border: #FECACA;
}

.stApp {
    background: var(--dashboard-bg);
    color: var(--dashboard-text);
    font-family: Inter, "Segoe UI", system-ui, sans-serif;
}

[data-testid="stAppViewContainer"] { background: var(--dashboard-bg); }
[data-testid="stMainBlockContainer"] { max-width: 1480px; padding-top: 2.35rem; padding-bottom: 3rem; }

/* Keep data provenance visible while grouping it with the page it describes. */
div[class*="st-key-data_source_summary"] {
    margin: .35rem 0 1.15rem;
    border-color: var(--dashboard-border);
    background: #FFFFFF;
}
div[class*="st-key-data_source_summary"] [data-testid="stHorizontalBlock"] { align-items:center !important; }
div[class*="st-key-data_source_summary"] [data-testid="stCaptionContainer"] p { margin:0; }
div[class*="st-key-car_filter_panel"] { background:#FFFFFF; border-color:var(--dashboard-border); }
div[class*="st-key-car_source_picker"] { margin:.8rem 0; background:#FFFFFF; border-color:var(--dashboard-border); }
div[class*="st-key-car_compare_panel"] { margin:.5rem 0 1rem; background:#FFFFFF; border-color:var(--dashboard-border); }
div[class*="st-key-market_source_picker"],
div[class*="st-key-market_scope_picker"],
div[class*="st-key-price_source_picker"] { min-height:5.6rem; background:#FFFFFF; border-color:var(--dashboard-border); }

/* AutoMatch's original horizontal navigation, with one direct link per page. */
div[class*="st-key-automatch_topnav"] {
    position: relative;
    z-index: 5;
    margin: .15rem 0 1rem;
    padding: .35rem 1.2rem;
    border: 1px solid var(--dashboard-border);
    border-radius: 14px;
    background: rgba(255,255,255,.98);
    box-shadow: 0 2px 8px rgba(15,23,42,.03);
}
div[class*="st-key-automatch_topnav"] [data-testid="stHorizontalBlock"] {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    gap: .5rem;
    flex-wrap: nowrap !important;
}
div[class*="st-key-automatch_topnav"] [data-testid="stColumn"] {
    display: flex;
    align-items: center;
    flex: 1 1 auto !important;
    min-width: 0 !important;
}
div[class*="st-key-automatch_topnav"] [data-testid="stMarkdownContainer"] { margin:0; padding:0; }
div[class*="st-key-automatch_topnav"] [data-testid="stPageLink"] { width:100%; }
div[class*="st-key-automatch_topnav"] [data-testid="stPageLink"] a {
    min-height:2.5rem;
    display:flex;
    align-items:center;
    justify-content:center;
    width:100%;
    padding:.35rem .6rem;
    border-radius:8px;
    font-size:.84rem;
    font-weight:550;
    color:var(--dashboard-muted);
    text-decoration:none;
    white-space:nowrap;
    transition: all .15s ease;
}
div[class*="st-key-automatch_topnav"] [data-testid="stPageLink"] a:hover { color:var(--dashboard-accent); background:rgba(0,139,139,0.06); }
div[class*="st-key-nav_active_"] [data-testid="stPageLink"] a { color:var(--dashboard-accent) !important; font-weight:700 !important; background:rgba(0,139,139,0.08) !important; border-bottom:2px solid var(--dashboard-accent); }
.automatch-brand { display:flex; align-items:center; justify-content:flex-start; gap:.5rem; height:2.65rem; min-width:0; white-space:nowrap; }
.automatch-brand img { display:block; flex:0 0 auto; width:5.8rem; height:1.55rem; object-fit:contain; object-position:left center; }
.automatch-brand span { display:block; color:var(--dashboard-text); font-family:"Plus Jakarta Sans",Inter,sans-serif; font-size:.72rem; font-weight:650; line-height:1; letter-spacing:-.015em; }

/* Hero Banner */
div[class*="st-key-home_hero"] {
    position: relative;
    overflow: hidden;
    min-height: 410px;
    display: flex;
    align-items: center;
    background-color: #F8FAFC;
    background-image: linear-gradient(90deg, rgba(255,255,255,0.99) 0%, rgba(255,255,255,0.98) 50%, rgba(255,255,255,0.82) 62%, rgba(255,255,255,0.08) 100%), var(--automatch-hero-image);
    background-position: center, right center;
    background-repeat: no-repeat, no-repeat;
    background-size: cover, cover;
    border: 1px solid var(--dashboard-border);
    border-radius: 20px;
    padding: 2.4rem 2.8rem;
    box-shadow: 0 1px 5px rgba(15, 23, 42, .025);
}
div[class*="st-key-home_hero"] > div[data-testid="stVerticalBlock"] {
    max-width: none;
    width: 100%;
    text-align: left;
}
div[class*="st-key-home_hero"] [data-testid="stHorizontalBlock"] { align-items:center !important; gap:2rem; }
div[class*="st-key-home_region_profile_card"] { width:100%; min-width:0; padding:1.4rem 1.6rem; background:#FFFFFF; border-color:#DCE6EB; }
div[class*="st-key-home_region_profile_card"] h2 { margin:.1rem 0; font-size:2.2rem; color:var(--dashboard-text); }
div[class*="st-key-home_region_profile_card"] p { margin:.15rem 0; font-size:.9rem; }
div[class*="st-key-home_region_profile_card"] hr { margin:.8rem 0; border-color:#F1F5F9; }
div[class*="st-key-home_region_profile_card"] .stButton > button { margin-top:.3rem; }

div[class*="st-key-home_other_brand_card"] { padding:1.2rem 1.4rem; background:#FFFFFF; border-color:#DCE6EB; margin-top:.7rem; }
div[class*="st-key-home_other_brand_card"] h3 { margin:.1rem 0; font-size:1.45rem; color:var(--dashboard-text); }
div[class*="st-key-home_other_brand_card"] p { margin:.1rem 0; font-size:.92rem; color:var(--dashboard-text); }
div[class*="st-key-home_other_brand_card"] .stButton > button { margin-top:.85rem; }
div[class*="st-key-home_fuel_card_"] [data-testid="stVerticalBlockBorderWrapper"] { height:100%; min-height:9rem; background:linear-gradient(145deg,#FFFFFF 12%,#F0F8F7 100%); border-color:#D4E7E4; }
div[class*="st-key-home_fuel_card_"] [data-testid="stVerticalBlockBorderWrapper"] { padding:1rem; }
.home-fuel-heading { display:flex; align-items:center; gap:.7rem; min-height:2.7rem; margin:0 0 .55rem; color:#19364F; font-size:1.08rem; }
.home-fuel-heading .material-symbols-rounded { display:grid; place-items:center; width:2.65rem; height:2.65rem; flex:0 0 2.65rem; border-radius:50%; background:#E5F4F1; color:#008B8B; font-size:1.45rem; }
div[class*="st-key-home_fuel_card_"] [data-testid="stMarkdownContainer"] p { margin:.3rem 0 .7rem; }
div[class*="st-key-home_fuel_card_"] [data-testid="stButton"] > button { background:#FFFFFF; }
div[class*="st-key-home_brand_card_"] [data-testid="stVerticalBlockBorderWrapper"] { height:100%; min-height:11rem; background:linear-gradient(145deg,#FFFFFF 15%,#F5F9FB 100%); }
div[class*="st-key-home_brand_card_"] [data-testid="stImage"] img { width:100%; height:7.2rem; object-fit:contain; object-position:center; background:#F1F5F9; border-radius:10px; }
.home-brand-mark { display:grid; place-items:center; width:2.8rem; height:2.8rem; margin:0 0 .55rem; border-radius:50%; background:linear-gradient(145deg,#E5F4F1,#DCEAF3); border:1px solid #D6E9E6; color:#087F80; font-size:.95rem; font-weight:800; letter-spacing:.02em; }
div[class*="st-key-home_brand_card_"] h4 { margin:.15rem 0; }
div[class*="st-key-home_brand_card_"] [data-testid="stCaptionContainer"] { min-height:1.2rem; }
div[class*="st-key-home_hero"] [data-testid="stButton"] {
    width: auto;
    align-self: flex-start;
}
div[class*="st-key-home_hero"] [data-testid="stElementContainer"]:has([data-testid="stButton"]) {
    width: fit-content;
    align-self: flex-start;
}
div[class*="st-key-home_hero"] [data-testid="stButton"] > button { width: auto; }
div[class*="st-key-home_hero"] h1 {
    font-size: clamp(2.4rem, 4.5vw, 3.8rem);
    margin-bottom: .25rem;
    color: var(--dashboard-text);
    font-weight: 800;
}
div[class*="st-key-home_hero"] h3 {
    font-size: clamp(1.2rem, 2vw, 1.6rem);
    color: var(--dashboard-accent);
    font-weight: 700;
    margin-top: 0;
}
div[class*="st-key-home_hero"] [data-testid="stCaptionContainer"] p {
    color: var(--dashboard-muted);
    font-weight: 600;
    letter-spacing: .02em;
}
div[class*="st-key-home_hero"] p {
    color: var(--dashboard-muted);
    font-size: .95rem;
    line-height: 1.6;
}

div[class*="st-key-project_editorial_hero"] {
    background: #FFFFFF;
    border: 1px solid var(--dashboard-border);
    border-radius: 20px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.35rem;
}
.project-illustration { padding:.7rem; text-align:center; color: var(--dashboard-muted); font-size:.76rem; }
.project-illustration svg { display:block; width:100%; max-height:240px; }
.project-illustration span { display:block; margin-top:.3rem; }

/* AutoMatch Navy Sidebar (Master Reference Design) */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B2A5B 0%, #081D3F 65%, #05142E 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}
[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] {
    padding-top: 0.6rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
[data-testid="stSidebarHeader"] {
    display: none !important;
    height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}
[data-testid="stSidebarNav"] {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] {
    margin: 0.15rem 0 !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    display: flex !important;
    align-items: center !important;
    gap: 0.65rem !important;
    border-radius: 10px !important;
    padding: 0.58rem 0.85rem !important;
    color: #94A3B8 !important;
    font-family: "Plus Jakarta Sans", Inter, sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    transition: all 0.15s ease-in-out !important;
    border: 1px solid transparent !important;
    background: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: rgba(255, 255, 255, 0.06) !important;
    color: #FFFFFF !important;
}
/* Active Pill Highlight - only when clicked / active page */
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
    background: #008B8B !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(0, 139, 139, 0.35) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] span,
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] p {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:not([aria-current="page"]) span,
[data-testid="stSidebar"] [data-testid="stPageLink"] a:not([aria-current="page"]) p {
    color: #94A3B8 !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover:not([aria-current="page"]) span,
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover:not([aria-current="page"]) p {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a svg {
    fill: currentColor !important;
}
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #E2E8F0 !important;
}
.am-sidebar-brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.15rem 0.2rem 0.95rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 0.85rem;
}
.am-sidebar-brand-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.4rem;
    height: 2.4rem;
    border-radius: 8px;
    background: #008B8B;
    color: #FFFFFF;
    font-size: 1.25rem;
    box-shadow: 0 2px 6px rgba(0, 139, 139, 0.4);
}
.am-sidebar-brand-title {
    font-family: "Plus Jakarta Sans", Inter, sans-serif;
    font-weight: 800;
    font-size: 1.2rem;
    color: #FFFFFF !important;
    letter-spacing: -0.02em;
    line-height: 1.1;
}
.am-sidebar-brand-sub {
    font-size: 0.72rem;
    color: #94A3B8 !important;
    line-height: 1.2;
    margin-top: 0.1rem;
}
.am-sidebar-footer {
    padding: 1rem 0.5rem 0.5rem;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    margin-top: 2rem;
    font-size: 0.74rem;
    color: #64748B !important;
}

/* Page Header Component */
.am-page-header {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.35rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--dashboard-border);
}
.am-page-header-icon {
    font-size: 1.9rem;
    line-height: 1;
    padding: 0.35rem;
    border-radius: 10px;
    background: #F1F5F9;
}
.am-page-header-title {
    font-family: "Plus Jakarta Sans", Inter, sans-serif;
    font-size: 1.55rem;
    font-weight: 800;
    color: var(--dashboard-text);
    letter-spacing: -0.025em;
    line-height: 1.2;
}
.am-page-header-subtitle {
    font-size: 0.88rem;
    color: var(--dashboard-muted);
    margin-top: 0.2rem;
    line-height: 1.45;
}

/* Reusable Section Title & Insight Cards */
.am-section-title {
    font-family: "Plus Jakarta Sans", Inter, sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--dashboard-text);
    margin-bottom: 0.65rem;
    letter-spacing: -0.015em;
}
.am-insight-card {
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
    padding: 1rem 1.15rem;
    background: #FFFFFF;
    border: 1px solid var(--dashboard-border);
    border-radius: 14px;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}
.am-insight-icon {
    font-size: 1.35rem;
    line-height: 1;
    padding-top: 0.1rem;
}
.am-insight-headline {
    font-weight: 700;
    font-size: 0.92rem;
    color: var(--dashboard-text);
    margin-bottom: 0.2rem;
}
.am-insight-body {
    font-size: 0.84rem;
    color: var(--dashboard-muted);
    line-height: 1.5;
}
.am-insight-warning {
    border-left: 4px solid #F59E0B;
}
.am-insight-success {
    border-left: 4px solid #10B981;
}
.am-insight-info {
    border-left: 4px solid #008B8B;
}

/* Compact Hero Banner per Master Reference Design */
.am-hero-compact {
    position: relative;
    overflow: hidden;
    min-height: 145px;
    border-radius: 16px;
    border: 1px solid var(--dashboard-border);
    background-color: #FFFFFF;
    background-repeat: no-repeat;
    background-position: right center;
    background-size: contain;
    padding: 1.4rem 2rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.am-hero-compact-content {
    position: relative;
    z-index: 2;
    max-width: 580px;
}
.am-hero-compact-title {
    font-family: "Plus Jakarta Sans", Inter, sans-serif;
    font-size: 1.85rem;
    font-weight: 800;
    color: var(--dashboard-navy);
    letter-spacing: -0.025em;
    line-height: 1.15;
    margin-bottom: 0.25rem;
}
.am-hero-compact-subtitle {
    font-family: "Plus Jakarta Sans", Inter, sans-serif;
    font-size: 1.02rem;
    font-weight: 700;
    color: var(--dashboard-text);
    margin-bottom: 0.3rem;
}
.am-hero-compact-desc {
    font-size: 0.82rem;
    color: var(--dashboard-muted);
    line-height: 1.45;
}

/* Master Reference KPI Cards */
.am-kpi-card {
    background: #FFFFFF;
    border: 1px solid var(--dashboard-border);
    border-radius: 14px;
    padding: 0.85rem 1.05rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
    display: flex;
    align-items: center;
    gap: 0.85rem;
    min-height: 80px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.am-kpi-card:hover {
    box-shadow: 0 3px 8px rgba(15, 23, 42, 0.06);
}
.am-kpi-icon-badge {
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    flex-shrink: 0;
}
.am-kpi-badge-teal { background: #E3F6F5; color: #008B8B; }
.am-kpi-badge-navy { background: #E0E7FF; color: #0B2A5B; }
.am-kpi-badge-amber { background: #FEF3C7; color: #D97706; }
.am-kpi-badge-blue { background: #E0F2FE; color: #0284C7; }
.am-kpi-badge-green { background: #DCFCE7; color: #16A34A; }
.am-kpi-label {
    font-size: 0.74rem;
    font-weight: 600;
    color: var(--dashboard-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 0.15rem;
    line-height: 1.2;
}
.am-kpi-value {
    font-family: "Plus Jakarta Sans", Inter, sans-serif;
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--dashboard-text);
    line-height: 1.15;
    letter-spacing: -0.02em;
}

/* Streamlit Tab Overrides per Master Reference */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.5rem;
    border-bottom: 1px solid var(--dashboard-border);
    margin-bottom: 1.25rem;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    padding: 0.55rem 1.25rem !important;
    border-radius: 8px 8px 0 0 !important;
    font-family: "Plus Jakarta Sans", Inter, sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    color: var(--dashboard-muted) !important;
    border: none !important;
    background: transparent !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: var(--dashboard-accent) !important;
    border-bottom: 2px solid var(--dashboard-accent) !important;
    background: #FFFFFF !important;
}

/* Horizontal Filter Toolbar */
.am-filter-toolbar {
    background: #FFFFFF;
    border: 1px solid var(--dashboard-border);
    border-radius: 14px;
    padding: 0.45rem 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}

/* Segment Pill Selector */
.am-pill-group {
    display: inline-flex;
    background: #F1F5F9;
    padding: 0.25rem;
    border-radius: 999px;
    gap: 0.25rem;
}
.am-pill-btn {
    padding: 0.35rem 0.95rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    border: none;
    background: transparent;
    color: #475569;
    transition: all 0.15s ease;
}
.am-pill-btn.active {
    background: #008B8B;
    color: #FFFFFF;
    box-shadow: 0 2px 6px rgba(0, 139, 139, 0.3);
}

/* Coming Soon Placeholder */
.am-coming-soon {
    text-align: center;
    padding: 2.5rem 1.5rem;
    background: #FFFFFF;
    border: 1px dashed var(--dashboard-border);
    border-radius: 16px;
    margin: 1rem 0;
}
.am-coming-soon-icon {
    font-size: 2.2rem;
    margin-bottom: 0.6rem;
}
.am-coming-soon-title {
    font-family: "Plus Jakarta Sans", sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--dashboard-text);
    margin-bottom: 0.35rem;
}
.am-coming-soon-desc {
    font-size: 0.86rem;
    color: var(--dashboard-muted);
    max-width: 580px;
    margin: 0 auto 1rem;
    line-height: 1.5;
}
.am-coming-soon-badge {
    display: inline-block;
    padding: 0.28rem 0.75rem;
    border-radius: 999px;
    background: #E3F6F5;
    color: #008B8B;
    font-size: 0.76rem;
    font-weight: 600;
}

/* Top bar indicator pill */
.am-scope-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.75rem;
    background: #FFFFFF;
    border: 1px solid var(--dashboard-border);
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--dashboard-text);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

h1, h2, h3, h4 {
    letter-spacing: -0.025em;
    color: var(--dashboard-text);
    font-family: "Plus Jakarta Sans", Inter, "Segoe UI", system-ui, sans-serif;
}
[data-testid="stCaptionContainer"] { color: var(--dashboard-muted); }
[data-testid="stAppViewContainer"] h1 { font-size: clamp(2.1rem, 3.8vw, 3.2rem); }

/* KPI Metrics */
.stMetric {
    background: var(--dashboard-surface);
    border: 1px solid var(--dashboard-border) !important;
    border-radius: 14px !important;
    padding: .85rem 1rem !important;
    min-width: 0;
    box-shadow: 0 1px 3px rgba(15, 23, 42, .03) !important;
}
.stMetric label, .stMetric [data-testid="stMetricLabel"] { color: var(--dashboard-muted); }
.stMetric [data-testid="stMetricValue"] { color: var(--dashboard-text); font-weight: 700; font-size: clamp(1rem, 1.5vw, 1.4rem); line-height:1.2; white-space:normal; overflow:visible; text-overflow:clip; overflow-wrap:anywhere; }
.stMetric [data-testid="stMetricValue"] > div { font-size:inherit !important; line-height:inherit; white-space:normal !important; overflow:visible !important; text-overflow:clip !important; overflow-wrap:anywhere; }
[data-testid="stMetricLabel"] p { font-size: .84rem; font-weight: 500; white-space:normal; line-height:1.2; }

/* Cards & Containers (Anti-Slop Clean Elevation) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--dashboard-surface) !important;
    border: 1px solid var(--dashboard-border) !important;
    border-radius: 14px !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02) !important;
    padding: 1.15rem 1.25rem !important;
    margin-bottom: 0.75rem !important;
}
.card {
    background: var(--dashboard-surface);
    border: 1px solid var(--dashboard-border);
    border-radius: 14px;
    padding: 1.1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02);
}
[data-testid="stImage"] img { border-radius: 12px; aspect-ratio: 16 / 9; object-fit: cover; }
[data-testid="stImage"] figcaption { color: var(--dashboard-muted); font-size: .78rem; }

[data-testid="stPlotlyChart"] { padding: .4rem; border-radius: 14px; background: #FFFFFF; }
.stMarkdown p { line-height: 1.65; }
[data-testid="stCaptionContainer"] p { line-height: 1.5; }

/* Buttons & Inputs */
.stButton > button, [data-testid="stLinkButton"] a {
    min-height: 2.75rem;
    border-radius: 10px;
    font-weight: 600;
    font-size: .86rem;
    border: 1px solid var(--dashboard-border);
    transition: all .15s ease-in-out;
}
.stButton > button[kind="primary"] {
    background-color: var(--dashboard-accent);
    border-color: var(--dashboard-accent);
    color: #FFFFFF;
    box-shadow: 0 2px 6px rgba(0, 139, 139, 0.2);
}
.stButton > button[kind="primary"]:hover {
    background-color: var(--dashboard-accent-hover);
    border-color: var(--dashboard-accent-hover);
}
.stButton > button:hover {
    border-color: var(--dashboard-accent);
}
.stButton > button:active, [data-testid="stLinkButton"] a:active { transform: translateY(1px); }
.stButton > button:not(:disabled), [data-testid="stLinkButton"] a, [data-testid="stPageLink"] a { cursor: pointer; }
.stButton > button:focus-visible,
[data-testid="stPageLink"] a:focus-visible,
[data-testid="stLinkButton"] a:focus-visible {
    outline: 3px solid rgba(0, 139, 139, .38);
    outline-offset: 2px;
}

.car-price {
    color: var(--dashboard-accent);
    font-size: 1.45rem;
    font-weight: 750;
    letter-spacing: -.025em;
    margin: -.25rem 0 .2rem;
}
.listing-meta { display:flex; flex-wrap:wrap; gap:.35rem; margin:.15rem 0 .55rem; }
.listing-meta span { padding:.2rem .48rem; border:1px solid var(--dashboard-border); border-radius:.45rem; color:var(--dashboard-text); background:var(--dashboard-surface); font-size:.72rem; line-height:1.35; }
.listing-spec { display:flex; justify-content:space-between; gap:.5rem; padding:.25rem 0; border-bottom:1px solid #F1F5F9; font-size:.8rem; }
.listing-spec span { color: var(--dashboard-muted); }
.listing-spec b { color: var(--dashboard-text); font-weight: 600; text-align:right; }
.price-hero-value { color: var(--dashboard-accent); font-family:"Plus Jakarta Sans",sans-serif; font-size:clamp(1.65rem,2.7vw,2.3rem); font-weight:800; letter-spacing:-.03em; }
div[class*="st-key-price_analysis_hero"] [data-testid="stVerticalBlock"] { gap:.65rem; padding-bottom:.45rem; }
.price-result-status { margin:.1rem 0 .25rem; }

/* Status Badges */
.badge-underpriced {
    display: inline-block;
    padding: .3rem .8rem;
    border-radius: 999px;
    font-size: .82rem;
    font-weight: 700;
    background-color: var(--status-under-background);
    color: var(--status-under-text);
    border: 1px solid var(--status-under-border);
}
.badge-fair {
    display: inline-block;
    padding: .3rem .8rem;
    border-radius: 999px;
    font-size: .82rem;
    font-weight: 700;
    background-color: var(--status-fair-background);
    color: var(--status-fair-text);
    border: 1px solid var(--status-fair-border);
}
.badge-overpriced {
    display: inline-block;
    padding: .3rem .8rem;
    border-radius: 999px;
    font-size: .82rem;
    font-weight: 700;
    background-color: var(--status-over-background);
    color: var(--status-over-text);
    border: 1px solid var(--status-over-border);
}

div.stAlert { border-radius: 12px; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div { border-radius:10px; border-color: var(--dashboard-border); }
[data-testid="stRadio"] div[role="radiogroup"] { gap:.35rem; }
[data-testid="stRadio"] div[role="radiogroup"] label { background:#FFFFFF; border:1px solid var(--dashboard-border); border-radius:999px; padding:.35rem .8rem; }
[data-testid="stDataFrame"] { border: 1px solid var(--dashboard-border); border-radius: 12px; }

@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] { padding-top: 1.5rem; padding-bottom: 2rem; }
    div[class*="st-key-automatch_topnav"] { overflow-x:auto; margin:0 -1rem 1rem; padding:.4rem .75rem; }
    div[class*="st-key-automatch_topnav"] [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; min-width:920px; }
    .automatch-brand { gap:0; }
    .automatch-brand span { display:none; }
    div[class*="st-key-home_hero"] {
        min-height: 440px;
        align-items: flex-end;
        padding: 1.5rem;
        background-image: linear-gradient(0deg, rgba(255,255,255,0.99) 0%, rgba(255,255,255,0.98) 58%, rgba(255,255,255,0.12) 100%), var(--automatch-hero-image);
        background-position: center, center top;
        background-size: cover, cover;
    }
    div[class*="st-key-home_hero"] > div[data-testid="stVerticalBlock"] { max-width: 100%; }
    div[class*="st-key-home_hero"] [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; gap:.5rem; }
    div[class*="st-key-home_hero"] [data-testid="stColumn"] { min-width:100% !important; }
    .listing-meta { gap:.25rem; }
    .listing-meta span { font-size:.68rem; }
    .car-price { font-size: 1.2rem; }
    [data-testid="stMetricValue"] { font-size: 1.15rem !important; }
}
/* Suppress default bullet on custom icon lists (✔ ✓ markers) */
.stMarkdown ul { list-style: none; padding-left: 0; }
.stMarkdown ul li { padding-left: 0; }
.stMarkdown ul li::before { content: none; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; }
}
</style>
"""


def apply_theme() -> None:
    """Apply theme-aware CSS; page configuration belongs to app.py navigation."""
    st.markdown(CSS, unsafe_allow_html=True)
