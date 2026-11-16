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


def test_price_checker_uses_selected_listing_and_replaces_old_result():
    app = AppTest.from_file(ROOT / "app.py", default_timeout=60).run()
    app.session_state["price_calculation_result"] = {
        "source": "Arsip Penuh",
        "asking_price": 150_000_000,
        "estimate": 204_659_401,
    }
    app.session_state["price_checker_prefill"] = {
        "make": "BMW",
        "model": "520i",
        "year": 2023,
        "mileage_km": 2_500,
        "engine_cc": 2_500,
        "fuel_type": "Bensin",
        "transmission": "Automatic",
        "body_type": "Sedan",
        "price": 775_000_000,
        "_comparison_source": "Arsip Penuh",
        "_auto_calculate": True,
    }

    app.switch_page("pages/3_Price_Checker.py").run()

    result = app.session_state["price_calculation_result"]
    assert not app.exception, "\n".join(str(error.value) for error in app.exception)
    assert app.session_state["calculator_model"] == "520i"
    assert app.session_state["calculator_year"] == 2023
    assert app.session_state["calculator_asking_price"] == 775_000_000
    assert result["asking_price"] == 775_000_000
    assert result["estimate"] > 700_000_000
    assert len(result["peers"]) > 0


def test_saved_price_listing_fills_form_and_replaces_previous_result():
    app = AppTest.from_file(ROOT / "app.py", default_timeout=60).run()
    app.session_state["price_calculation_result"] = {
        "source": "Arsip Penuh",
        "asking_price": 150_000_000,
        "estimate": 2_080_315_692,
    }
    app.switch_page("pages/3_Price_Checker.py").run()

    selector = next(widget for widget in app.selectbox if widget.key == "saved_price_listing_archive")
    selected_label = next(
        option for option in selector.options
        if str(option).startswith("Honda HR-V · 2017 · ")
    )
    selector.select(selected_label).run()

    selected_price = int(str(selected_label).split(" · ")[-1].replace("Rp", "").replace(".", "").strip())
    assert not app.exception, "\n".join(str(error.value) for error in app.exception)
    assert app.session_state["calculator_make"] == "Honda"
    assert app.session_state["calculator_model"] == "HR-V"
    assert app.session_state["calculator_year"] == 2017
    assert app.session_state["calculator_asking_price"] == selected_price
    assert app.session_state["price_calculation_result"]["asking_price"] == selected_price
