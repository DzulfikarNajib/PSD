"""Render each AutoMatch page through Streamlit's in-process AppTest runner."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest
from streamlit.testing.v1 import AppTest


os.environ["AUTOMATCH_OFFLINE"] = "1"
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_SECRET_KEY", "")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.mark.parametrize(
    "page_path",
    [
        None,
        "pages/1_Explore_Market.py",
        "pages/2_Find_Your_Car.py",
        "pages/3_Price_Checker.py",
        "pages/4_Tentang_Proyek.py",
    ],
    ids=["beranda", "pahami-pasar", "cari-mobil", "cek-harga", "tentang-proyek"],
)
def test_app_pages_render_without_exceptions(page_path):
    app = AppTest.from_file(ROOT / "app.py", default_timeout=60).run()
    if page_path is not None:
        app.switch_page(page_path).run()

    assert not app.exception, "\n".join(str(error.value) for error in app.exception)
    assert app.title or app.header or app.subheader or app.markdown
