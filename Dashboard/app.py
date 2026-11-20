"""AutoMatch application shell with a navy sidebar navigation (6 pages)."""

import base64
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

# Streamlit Cloud can start this nested app with the repository root as its
# working directory. Put this app's package directory first so `src.*` cannot
# resolve to an unrelated installed package named `src`.
app_directory = str(APP_DIR)
if app_directory in sys.path:
    sys.path.remove(app_directory)
sys.path.insert(0, app_directory)

loaded_src = sys.modules.get("src")
if loaded_src is not None:
    loaded_paths = [Path(path).resolve() for path in getattr(loaded_src, "__path__", [])]
    local_src = (APP_DIR / "src").resolve()
    if local_src not in loaded_paths:
        for module_name in tuple(sys.modules):
            if module_name == "src" or module_name.startswith("src."):
                sys.modules.pop(module_name, None)

import streamlit as st
from streamlit_option_menu import option_menu

from src.styles import apply_theme

st.set_page_config(
    page_title="AutoMatch · Analisis Pasar Mobil Bekas DKI Jakarta",
    page_icon=str(ASSETS_DIR / "automatch-icon.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

# 6 pages per Master Reference Design (AutoMatch Redesign Blueprint)
p_ikhtisar = st.Page(
    "pages/ikhtisar_pasar.py",
    title="Ikhtisar Pasar",
    url_path="ikhtisar-pasar",
    icon=":material/dashboard:",
    default=True,
)
p_eksplorasi = st.Page(
    "pages/eksplorasi_data.py",
    title="Eksplorasi Data",
    url_path="eksplorasi-data",
    icon=":material/bar_chart:",
)
p_preproc = st.Page(
    "pages/preprocessing_segmentasi.py",
    title="Preprocessing & Segmentasi",
    url_path="preprocessing-segmentasi",
    icon=":material/tune:",
)
p_evaluasi = st.Page(
    "pages/evaluasi_model.py",
    title="Evaluasi Model",
    url_path="evaluasi-model",
    icon=":material/query_stats:",
)
p_cek_harga = st.Page(
    "pages/cek_harga_iklan.py",
    title="Cek Harga Iklan",
    url_path="cek-harga-iklan",
    icon=":material/search_check:",
)
p_kesimpulan = st.Page(
    "pages/kesimpulan.py",
    title="Kesimpulan & Rekomendasi",
    url_path="kesimpulan-rekomendasi",
    icon=":material/fact_check:",
)

pages_list = [p_ikhtisar, p_eksplorasi, p_preproc, p_evaluasi, p_cek_harga, p_kesimpulan]
page_map = {p.title: p for p in pages_list}

active_page = st.navigation(
    pages_list,
    position="hidden",
)

# Sidebar Branding & Option Menu Navigation
icon_path = ASSETS_DIR / "automatch-icon.png"
if icon_path.exists():
    icon_b64 = base64.b64encode(icon_path.read_bytes()).decode()
    brand_icon_html = f'<img src="data:image/png;base64,{icon_b64}" style="width:34px; height:34px; border-radius:8px; object-fit:contain;" alt="AutoMatch" />'
else:
    brand_icon_html = '<div class="am-sidebar-brand-icon">AM</div>'

with st.sidebar:
    # 1. Branding at the very top of sidebar
    st.markdown(
        f"""
        <div class="am-sidebar-brand">
            <div style="flex-shrink:0;">{brand_icon_html}</div>
            <div>
                <div class="am-sidebar-brand-title">AutoMatch</div>
                <div class="am-sidebar-brand-sub">Analisis Pasar Mobil DKI Jakarta</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Polished option menu navigation
    page_names = [p.title for p in pages_list]
    page_icons = [
        "speedometer2",
        "bar-chart-line",
        "sliders",
        "graph-up-arrow",
        "search",
        "check2-circle",
    ]

    curr_idx = 0
    for idx, p in enumerate(pages_list):
        if p == active_page:
            curr_idx = idx
            break

    selected = option_menu(
        menu_title=None,
        options=page_names,
        icons=page_icons,
        default_index=curr_idx,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#94A3B8", "font-size": "15px"},
            "nav-link": {
                "font-size": "0.88rem",
                "text-align": "left",
                "margin": "3px 0",
                "color": "#CBD5E1",
                "border-radius": "10px",
                "font-family": "'Plus Jakarta Sans', Inter, sans-serif",
                "font-weight": "500",
                "--hover-color": "rgba(255, 255, 255, 0.08)",
            },
            "nav-link-selected": {
                "background-color": "#008B8B",
                "color": "#FFFFFF",
                "font-weight": "700",
                "box-shadow": "0 2px 8px rgba(0, 139, 139, 0.35)",
            },
        },
    )

    if selected in page_map and page_map[selected] != active_page:
        st.switch_page(page_map[selected])

    st.markdown(
        """
        <div class="am-sidebar-footer">
            <div>Sains Data · STA1381</div>
            <div style="color:#64748B; margin-top:2px;">Institut Pertanian Bogor</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Top utility header above page content (matching master reference design)
top_cols = st.columns([8, 2], vertical_alignment="center")
with top_cols[0]:
    st.markdown(
        '<div class="am-scope-pill"><span style="color:#008B8B;">📍</span> DKI Jakarta &nbsp;·&nbsp; 5 Wilayah</div>',
        unsafe_allow_html=True,
    )
with top_cols[1]:
    st.markdown(
        '<div style="text-align:right; font-size:0.78rem; color:#64748B;">☀️ Mode Terang</div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)

active_page.run()
