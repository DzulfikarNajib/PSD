"""Evaluasi Model - perbandingan performa model regresi harga mobil bekas.

Menampilkan:
- Seleksi model utama: Linear Regression vs Random Forest
- Metrik performa kunci: MAE, RMSE, R²
- Grafik Actual vs Predicted (Data Uji 20%)
- Residual Plot (Galat Prediksi vs Nilai Prediksi)
- Feature Importance (Tingkat Pengaruh Fitur)
- Tabel Perbandingan 6 Kandidat Model & Opsi Pelatihan Ulang
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_training_archive
from src.modeling import (
    evaluate_regression_models,
    get_feature_importance,
    load_model_metadata,
    model_is_validated,
    training_eligibility,
)
from src.styles import apply_theme
from src.ui import apply_rupiah_ticks, format_rupiah, format_rupiah_compact
from src.ui_components import (
    apply_chart_theme,
    insight_card,
    kpi_card,
    page_header,
    section_card,
)

apply_theme()

page_header(
    icon="activity",
    title="Evaluasi Model",
    subtitle="Membandingkan akurasi estimasi harga mobil bekas antara model parametrik (Linear Regression) dan non-parametrik (Random Forest).",
)

metadata = load_model_metadata()

if not metadata or not metadata.get("models"):
    st.warning("Metadata model regresi belum tersedia. Silakan lakukan pelatihan model.", icon=":material/warning:")
    st.stop()

models_dict = metadata.get("models", {})
best_model_name = metadata.get("best_model", "Random Forest Regressor")

# ---------------------------------------------------------------------------
# Baris 1: Kontrol Model & KPI Metrics
# ---------------------------------------------------------------------------
ctrl_col, badge_col = st.columns([2, 1], vertical_alignment="center")

with ctrl_col:
    selected_model_view = st.radio(
        "Pilih Model untuk Ditinjau:",
        ["Random Forest Regressor", "Linear Regression"],
        horizontal=True,
        index=0,
    )

with badge_col:
    if selected_model_view == best_model_name:
        st.markdown(
            '<div style="text-align:right;"><span style="display:inline-flex;align-items:center;gap:0.4rem;background:#2563EB;color:#FFFFFF;border-radius:999px;padding:0.38rem 1rem;font-size:0.82rem;font-weight:700;letter-spacing:0.01em;box-shadow:0 2px 6px rgba(37,99,235,0.3);">Model Terbaik Terpilih</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align:right;"><span style="display:inline-flex;align-items:center;background:#F1F5F9;color:#475569;border-radius:999px;padding:0.38rem 1rem;font-size:0.82rem;font-weight:600;">Model Baseline</span></div>',
            unsafe_allow_html=True,
        )

# Ambil metrik model terpilih
model_metrics = models_dict.get(selected_model_view, {})
mae_val = model_metrics.get("MAE", 0)
rmse_val = model_metrics.get("RMSE", 0)
r2_val = model_metrics.get("R2", 0)

with st.container(border=True):
    st.markdown(f"<div class='am-section-title'>Metrik Evaluasi Model: {selected_model_view}</div>", unsafe_allow_html=True)
    kpi_cols = st.columns(3, gap="medium")
    with kpi_cols[0]:
        kpi_card(
            label="MAE (Mean Absolute Error)",
            value=format_rupiah_compact(mae_val),
            icon="gauge",
            help_text=f"Rata-rata besar kesalahan absolut prediksi: {format_rupiah(mae_val)}.",
        )
    with kpi_cols[1]:
        kpi_card(
            label="RMSE (Root Mean Squared Error)",
            value=format_rupiah_compact(rmse_val),
            icon="bar-chart-2",
            help_text=f"Akar rata-rata kuadrat kesalahan: {format_rupiah(rmse_val)} (memberi penalti lebih berat pada galat besar).",
        )
    with kpi_cols[2]:
        kpi_card(
            label="R\u00b2 Score (Koefisien Determinasi)",
            value=f"{r2_val:.4f}" if pd.notna(r2_val) else "-",
            icon="target",
            help_text=f"Menjelaskan {r2_val*100:.1f}% variasi harga pasar pada data uji.",
        )

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Baris 2: Visualisasi (Actual vs Predicted, Residual Plot, Feature Importance)
# ---------------------------------------------------------------------------
col_scatter, col_residual, col_imp = st.columns([1.1, 1.1, 1], gap="medium")

# Ambil holdout predictions (20% data uji = 1.261 observasi)
holdout_list = metadata.get("holdout_predictions", [])
holdout_df = pd.DataFrame(holdout_list) if isinstance(holdout_list, list) and holdout_list else pd.DataFrame()

# 1. Actual vs Predicted
with col_scatter:
    with section_card("Actual vs Predicted"):
        if not holdout_df.empty and "actual" in holdout_df and "predicted" in holdout_df:
            # Skala dalam miliar untuk kenyamanan pembacaan
            act_m = holdout_df["actual"] / 1_000_000_000
            pred_m = holdout_df["predicted"] / 1_000_000_000
            max_val = max(float(act_m.quantile(0.99)), float(pred_m.quantile(0.99))) * 1.05

            fig_avp = go.Figure()
            fig_avp.add_trace(go.Scatter(
                x=act_m,
                y=pred_m,
                mode="markers",
                marker=dict(color="#2563EB", size=5, opacity=0.55),
                name="Data Uji",
                hovertemplate="Aktual: Rp %{x:.2f} M<br>Prediksi: Rp %{y:.2f} M<extra></extra>",
            ))
            # Garis diagonal ideal y = x
            fig_avp.add_trace(go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode="lines",
                line=dict(color="#1E40AF", dash="dash", width=2),
                name="Ideal (y = x)",
            ))
            apply_chart_theme(fig_avp)
            fig_avp.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True,
                legend=dict(orientation="h", y=1.1, x=1, xanchor="right", font=dict(size=10)),
                xaxis=dict(title="Harga Aktual (Miliar Rp)", range=[0, max_val], showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="Harga Prediksi (Miliar Rp)", range=[0, max_val], showgrid=True, gridcolor="#F1F5F9"),
            )
            st.plotly_chart(fig_avp, width="stretch", config={"displayModeBar": False}, key="chart_eval_avp")
        else:
            st.caption("Data pengujian tidak tersedia.")

# 2. Residual Plot
with col_residual:
    with section_card("Residual Plot"):
        if not holdout_df.empty and "actual" in holdout_df and "predicted" in holdout_df:
            residuals = holdout_df["actual"] - holdout_df["predicted"]
            res_jt = residuals / 1_000_000
            pred_jt = holdout_df["predicted"] / 1_000_000

            fig_res = go.Figure()
            fig_res.add_trace(go.Scatter(
                x=pred_jt,
                y=res_jt,
                mode="markers",
                marker=dict(color="#3B82F6", size=5, opacity=0.5),
                name="Residual",
                hovertemplate="Prediksi: Rp %{x:.0f} Jt<br>Galat: Rp %{y:.0f} Jt<extra></extra>",
            ))
            # Garis referensi 0
            fig_res.add_hline(
                y=0,
                line_color="#B91C1C",
                line_width=1.5,
                line_dash="solid",
            )
            apply_chart_theme(fig_res)
            fig_res.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Harga Prediksi (Juta Rp)", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="Residual (Aktual - Prediksi)", showgrid=True, gridcolor="#F1F5F9"),
            )
            st.plotly_chart(fig_res, width="stretch", config={"displayModeBar": False}, key="chart_eval_res")
        else:
            st.caption("Data residual tidak tersedia.")

# 3. Feature Importance
with col_imp:
    with section_card("Feature Importance"):
        imp_df = get_feature_importance().head(8)
        if not imp_df.empty:
            # Urutkan untuk bar horizontal ke atas
            plot_imp = imp_df.iloc[::-1]
            max_imp = float(plot_imp["importance"].max()) if not plot_imp.empty else 0.5

            fig_imp = go.Figure(go.Bar(
                x=plot_imp["importance"],
                y=plot_imp["feature"],
                orientation="h",
                marker=dict(color="#2563EB", cornerradius=4),
                text=[f"{v:.3f}" for v in plot_imp["importance"]],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="Fitur: <b>%{y}</b><br>Importance: <b>%{x:.4f}</b><extra></extra>",
            ))
            apply_chart_theme(fig_imp)
            fig_imp.update_layout(
                height=280,
                margin=dict(l=10, r=50, t=10, b=10),
                xaxis=dict(title=None, showgrid=True, gridcolor="#F1F5F9", range=[0, max_imp * 1.3]),
                yaxis=dict(title=None, showgrid=False, tickfont=dict(size=10), automargin=True),
            )
            st.plotly_chart(fig_imp, width="stretch", config={"displayModeBar": False}, key="chart_eval_imp")
        else:
            st.caption("Feature importance tidak tersedia untuk model ini.")

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Baris 3: Tabel Perbandingan Semua Kandidat Model & Penjelasan
# ---------------------------------------------------------------------------
col_tbl, col_exp = st.columns([1.5, 1], gap="medium")

with col_tbl:
    with section_card("Perbandingan 6 Kandidat Model Regresi"):
        rows_comp = []
        for name, m in models_dict.items():
            rows_comp.append({
                "Model": name,
                "MAE": format_rupiah(m.get("MAE", 0)),
                "RMSE": format_rupiah(m.get("RMSE", 0)),
                "R²": f"{m.get('R2', 0):.4f}",
                "Target": m.get("target_transform", "asli"),
                "_is_best": name == best_model_name,
            })
        
        comp_df = pd.DataFrame(rows_comp)
        st.dataframe(comp_df[["Model", "MAE", "RMSE", "R²", "Target"]], hide_index=True, width="stretch")
        st.caption(
            f"**Model terpilih: {best_model_name}** dipilih secara otomatis berdasarkan kriteria "
            f"**MAE terendah ({format_rupiah_compact(models_dict.get(best_model_name, {}).get('MAE', 0))})** pada data holdout test 20% (1.261 unit)."
        )

with col_exp:
    with section_card("Interpretasi Metrik Evaluasi"):
        st.markdown(
            """
            - **MAE (Mean Absolute Error)**: Mengukur rata-rata deviasi harga taksiran terhadap harga riil penawaran. Random Forest menghasilkan MAE terendah (~Rp 170 Jt).
            - **RMSE (Root Mean Squared Error)**: Lebih sensitif terhadap pencilan (mobil mewah/koleksi). Penurunan drastis dari Linear Regression (Rp 1,08 M) ke Random Forest (Rp 587 Jt) membuktikan ketahanan model pohon terhadap non-linearitas.
            - **R² Score = 0,8938**: Model mampu menjelaskan **89,4% variasi harga mobil bekas** di DKI Jakarta hanya dari 8 fitur spesifikasi dasar.
            """
        )

# ---------------------------------------------------------------------------
# Pelatihan Ulang (Expander Terisolasi)
# ---------------------------------------------------------------------------
with st.expander("Opsi Pemeliharaan: Latih & Evaluasi Ulang Model", expanded=False):
    training_data = load_training_archive()
    eligible, eligibility_message, model_data = training_eligibility(training_data)
    
    st.write(f"Basis data latih: **{len(model_data):,} listing unik tervalidasi**. {eligibility_message}")
    if st.button("Jalankan Evaluasi Ulang Model", disabled=not eligible, type="primary"):
        with st.spinner("Melatih dan membandingkan 6 kandidat model regresi..."):
            res = evaluate_regression_models(training_data)
            if res.get("status") == "ready":
                st.success(f"Pelatihan ulang berhasil! Model terbaik: {res.get('best_model')}")
                st.rerun()
            else:
                st.error(res.get("message", "Pelatihan ulang gagal."))
