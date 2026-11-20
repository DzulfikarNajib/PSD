"""Unit tests for AutoMatch redesigned 6 pages and UI components."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

os.environ["AUTOMATCH_OFFLINE"] = "1"
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_SECRET_KEY", "")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_ui_components_status_badge():
    from src.ui_components import status_badge
    
    under = status_badge("Di Bawah Kisaran Pasar")
    assert "badge-underpriced" in under
    assert "Di Bawah Kisaran Pasar" in under
    
    fair = status_badge("Harga Wajar")
    assert "badge-fair" in fair
    
    over = status_badge("Di Atas Kisaran Pasar")
    assert "badge-overpriced" in over


def test_ui_components_chart_theme():
    import plotly.graph_objects as go
    from src.ui_components import apply_chart_theme, chart_theme
    
    theme = chart_theme()
    assert "paper_bgcolor" in theme
    assert theme["paper_bgcolor"] == "#FFFFFF"
    assert "colorway" in theme
    
    fig = go.Figure(go.Bar(x=[1, 2], y=[10, 20]))
    apply_chart_theme(fig)
    assert fig.layout.paper_bgcolor == "#FFFFFF"


def test_model_predictions_on_sample_car():
    from src.modeling import load_model_metadata, model_is_validated, predict_asking_price
    
    meta = load_model_metadata()
    if meta.get("status") == "ready" and model_is_validated(meta):
        sample = {
            "make": "Toyota", "model": "Avanza", "year": 2020,
            "mileage_km": 40000, "engine_cc": 1300,
            "transmission": "Manual", "fuel_type": "Bensin", "body_type": "MPV"
        }
        pred = predict_asking_price(sample)
        assert isinstance(pred, (int, float))
        assert 50_000_000 <= pred <= 500_000_000


def test_holdout_predictions_residuals():
    from src.modeling import load_model_metadata
    
    meta = load_model_metadata()
    preds = meta.get("holdout_predictions")
    if preds:
        assert len(preds) > 100
        df_p = pd.DataFrame(preds)
        assert "actual" in df_p.columns
        assert "predicted" in df_p.columns
        residuals = df_p["actual"] - df_p["predicted"]
        assert len(residuals) == len(df_p)


def test_six_pages_exist():
    page_files = [
        ROOT / "pages" / "ikhtisar_pasar.py",
        ROOT / "pages" / "eksplorasi_data.py",
        ROOT / "pages" / "preprocessing_segmentasi.py",
        ROOT / "pages" / "evaluasi_model.py",
        ROOT / "pages" / "cek_harga_iklan.py",
        ROOT / "pages" / "kesimpulan.py",
    ]
    for p in page_files:
        assert p.exists(), f"File {p.name} does not exist!"


def test_price_deviation_barometer():
    from src.ui_components import price_deviation_barometer
    
    # Fair price (asking == median)
    fig_fair = price_deviation_barometer(asking_price=200_000_000, median_price=200_000_000)
    assert fig_fair is not None
    assert fig_fair.data[0].value == 50.0  # Normalized center
    assert "Harga Wajar" in fig_fair.data[0].title.text

    # Underpriced (-20% deviation)
    fig_under = price_deviation_barometer(asking_price=160_000_000, median_price=200_000_000)
    assert "Di Bawah Pasar" in fig_under.data[0].title.text

    # Overpriced (+20% deviation)
    fig_over = price_deviation_barometer(asking_price=240_000_000, median_price=200_000_000)
    assert "Di Atas Pasar" in fig_over.data[0].title.text


def test_zero_em_dash_in_redesign_pages():
    page_files = [
        ROOT / "pages" / "ikhtisar_pasar.py",
        ROOT / "pages" / "eksplorasi_data.py",
        ROOT / "pages" / "preprocessing_segmentasi.py",
        ROOT / "pages" / "evaluasi_model.py",
        ROOT / "pages" / "cek_harga_iklan.py",
        ROOT / "pages" / "kesimpulan.py",
    ]
    for p in page_files:
        content = p.read_text(encoding="utf-8")
        assert "—" not in content, f"Em dash found in {p.name}! Anti-slop rule R-02 violated."


def test_anti_slop_linter_full_pass():
    from scripts.anti_slop_linter import run_anti_slop_audit
    
    exit_code = run_anti_slop_audit(root_dir=ROOT, strict=True)
    assert exit_code == 0, "Anti-Slop Linter found violations in active project files!"


