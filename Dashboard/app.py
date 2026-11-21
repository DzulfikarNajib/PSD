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

from src.styles import apply_theme

st.set_page_config(
    page_title="AutoMatch · Analisis Pasar Mobil Bekas DKI Jakarta",
    page_icon=str(ASSETS_DIR / "automatch-icon.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

# 5 main pages in sidebar + keep evaluasi_model registered for direct access
p_beranda = st.Page(
    "pages/ikhtisar_pasar.py",
    title="Beranda",
    url_path="beranda",
    icon=":material/home:",
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
    title="Data & Model",
    url_path="data-dan-model",
    icon=":material/tune:",
)
p_cek_harga = st.Page(
    "pages/cek_harga_iklan.py",
    title="Cek Mobil dan Harga",
    url_path="cek-mobil-dan-harga",
    icon=":material/search_check:",
)
p_kesimpulan = st.Page(
    "pages/kesimpulan.py",
    title="Kesimpulan & Rekomendasi",
    url_path="kesimpulan-rekomendasi",
    icon=":material/fact_check:",
)

pages_list = [p_beranda, p_eksplorasi, p_preproc, p_cek_harga, p_kesimpulan]

active_page = st.navigation(
    pages_list,
    position="hidden",
)

# Sidebar Branding & Clean Native Page Navigation
icon_path = ASSETS_DIR / "automatch-icon.png"
if icon_path.exists():
    icon_b64 = base64.b64encode(icon_path.read_bytes()).decode()
    brand_icon_html = f'<img src="data:image/png;base64,{icon_b64}" style="width:34px; height:34px; border-radius:8px; object-fit:contain;" alt="AutoMatch" />'
else:
    brand_icon_html = '<div class="am-sidebar-brand-icon">AM</div>'

nav_items = [
    (p_beranda, "Beranda", ":material/home:", "beranda"),
    (p_eksplorasi, "Eksplorasi Data", ":material/bar_chart:", "eksplorasi"),
    (p_preproc, "Data & Model", ":material/tune:", "data_model"),
    (p_cek_harga, "Cek Mobil dan Harga", ":material/search_check:", "cek_harga"),
    (p_kesimpulan, "Kesimpulan & Rekomendasi", ":material/fact_check:", "kesimpulan"),
]

with st.sidebar:
    # 1. Branding at the top of sidebar
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

    # 2. Clean native Streamlit page links with guaranteed active highlight on all pages (including Beranda /)
    for page_obj, label_text, icon_name, slug in nav_items:
        if active_page == page_obj:
            with st.container(key=f"nav_active_{slug}"):
                st.page_link(page_obj, label=label_text, icon=icon_name)
        else:
            st.page_link(page_obj, label=label_text, icon=icon_name)

# Top utility header above page content (matching master reference design)
st.markdown(
    '<div class="am-scope-pill"><svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#019F90" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px;"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg> DKI Jakarta &nbsp;·&nbsp; 5 Wilayah</div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)

active_page.run()
