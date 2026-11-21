"""Data & Model - halaman terpadu pipa preprocessing, segmentasi K-Means, dan evaluasi model regresi.

Menampilkan secara berurutan dalam 1 halaman tanpa tab:
1. Pipa Pembersihan & Kualitas Data (Preprocessing Funnel & Missing Values)
2. Segmentasi Pasar Mobil Bekas (K-Means Clustering & Proyeksi PCA 2D)
3. Evaluasi & Performa Model Prediksi Harga (Random Forest Regressor, Actual vs Predicted,
   Residual Plot, Feature Importance, dan Perbandingan 6 Kandidat Model)
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from src.data_loader import load_historical_data_with_audit, load_training_archive
from src.market_segments import cluster_market_segments
from src.modeling import (
    evaluate_regression_models,
    get_feature_importance,
    load_model_metadata,
    training_eligibility,
)
from src.styles import apply_theme
from src.ui import (
    build_preprocessing_funnel,
    format_km,
    format_rupiah,
    format_rupiah_compact,
)
from src.ui_components import (
    apply_chart_theme,
    kpi_card,
    page_header,
    section_card,
)

apply_theme()

page_header(
    icon="settings",
    title="Data & Model",
    subtitle=(
        "Transparansi penuh pipa pembersihan data (preprocessing), pengelompokan segmen pasar (K-Means), "
        "dan evaluasi akurasi model Machine Learning dalam satu alur terpadu."
    ),
)

archive, audit = load_historical_data_with_audit()

if archive.empty:
    st.warning("Data arsip tidak dapat dimuat.", icon=":material/warning:")
    st.stop()

# ===========================================================================
# BAGIAN 1: PREPROCESSING & KUALITAS DATA
# ===========================================================================
st.markdown(
    "<div style='font-family:\"Plus Jakarta Sans\",Inter,sans-serif;font-size:1.25rem;font-weight:800;color:#0D1E38;margin:0.2rem 0 0.75rem;'>"
    "1. Pipa Pembersihan & Kualitas Data (Preprocessing)</div>",
    unsafe_allow_html=True,
)

col_funnel_tbl, col_funnel_viz = st.columns([1.1, 1], gap="medium")
funnel_df = build_preprocessing_funnel(audit)

with col_funnel_tbl:
    with section_card("Audit Tahap Pembersihan Data"):
        disp_funnel = funnel_df.copy()
        disp_funnel["Listing tersisa"] = disp_funnel["Listing tersisa"].map(lambda x: f"{int(x):,}".replace(",", "."))
        disp_funnel["Baris dihapus"] = disp_funnel["Baris dihapus"].map(lambda x: f"{int(x):,}".replace(",", "."))
        st.dataframe(disp_funnel, hide_index=True, width="stretch")

        raw_n = audit.get("raw_rows", 10563)
        clean_n = audit.get("clean_rows", len(archive))
        eff_pct = (clean_n / raw_n * 100) if raw_n else 0
        st.caption(
            f"Retensi data bersih: **{clean_n:,} dari {raw_n:,} listing ({eff_pct:.1f}%)** "
            "siap untuk analisis dan pelatihan model Machine Learning.".replace(",", ".")
        )

with col_funnel_viz:
    with section_card("Visualisasi Retensi Observasi"):
        max_funnel = float(funnel_df["Listing tersisa"].max()) if not funnel_df.empty else 1000.0
        fig_funnel = go.Figure(
            go.Bar(
                x=funnel_df["Listing tersisa"],
                y=funnel_df["Tahap"],
                orientation="h",
                marker=dict(
                    color=["#0D1E38", "#007A6E", "#019F90", "#00B8A9", "#38D9A9"],
                    cornerradius=4,
                ),
                text=[f"{v:,}".replace(",", ".") for v in funnel_df["Listing tersisa"]],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(color="#FFFFFF", size=10, family="Inter, sans-serif"),
                hovertemplate="Tahap: <b>%{y}</b><br>Tersisa: <b>%{x:,}</b><extra></extra>",
            )
        )
        apply_chart_theme(fig_funnel)
        fig_funnel.update_layout(
            height=250,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(title=None, showgrid=True, gridcolor="#F1F5F9", range=[0, max_funnel * 1.18]),
            yaxis=dict(title=None, showgrid=False, autorange="reversed"),
        )
        st.plotly_chart(fig_funnel, width="stretch", config={"displayModeBar": False}, key="chart_funnel_bar")

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

col_steps, col_missing = st.columns([1.2, 1], gap="medium")

with col_steps:
    with section_card("Aturan & Langkah Pembersihan Aktual"):
        st.markdown(
            f"""
            - **Filter Wilayah DKI Jakarta**: Membatasi cakupan hanya pada 5 kota administrasi (*Jakarta Selatan, Utara, Pusat, Barat, Timur*). **{audit.get('outside_dki_rows_removed', 851):,} listing** di luar DKI Jakarta dieliminasi.
            - **Deduplikasi Listing**: Menghapus duplikat iklan snapshot berulang berdasarkan `listing_id` kanonis. Sebanyak **{audit.get('duplicate_rows_removed', 3352):,} baris** duplikat dibersihkan.
            - **Penyaringan Outlier Harga**: Menyingkirkan indikasi uang muka (TDP/angsuran) dengan harga **< Rp 30 Juta ({audit.get('low_price_rows_removed', 57):,} unit)** serta harga ekstrem **> Rp 30 Miliar ({audit.get('high_price_rows_removed', 2):,} unit)**.
            - **Rekayasa Fitur Odometer (`mileage_km`)**: Mengonversi rentang teks OLX (misal *20.000-25.000 km*) menjadi titik tengah numerik (*22.500 km*).
            - **Inferensi Kapasitas Mesin (`engine_cc`)**: Mengisi nilai CC kosong dari angka liter pada varian judul iklan (misal *1.5 G* menjadi *1.500 cc*). Sebanyak **{audit.get('engine_cc_from_variant_rows', 217):,} nilai** berhasil diperkirakan.
            """.replace(",", ".")
        )

with col_missing:
    with section_card("Proporsi Kolom Kosong (Missing Values %)"):
        key_cols = {
            "body_type": "Tipe Bodi",
            "engine_cc": "Kapasitas Mesin",
            "variant": "Varian Iklan",
            "year": "Tahun Kendaraan",
            "fuel_type": "Bahan Bakar",
            "transmission": "Transmisi",
            "mileage_km": "Kilometer",
            "price": "Harga",
        }
        miss_pct = []
        for col, lbl in key_cols.items():
            if col in archive:
                pct = (archive[col].isna() | archive[col].eq("")).mean() * 100
            else:
                pct = 0.0
            miss_pct.append({"Fitur": lbl, "Kosong (%)": pct})

        miss_df = pd.DataFrame(miss_pct).sort_values("Kosong (%)", ascending=True)

        fig_miss = go.Figure(
            go.Bar(
                x=miss_df["Kosong (%)"],
                y=miss_df["Fitur"],
                orientation="h",
                marker=dict(color="#019F90", cornerradius=4),
                text=[f"{v:.1f}%" for v in miss_df["Kosong (%)"]],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="Fitur: <b>%{y}</b><br>Nilai Kosong: <b>%{x:.2f}%</b><extra></extra>",
            )
        )
        apply_chart_theme(fig_miss)
        fig_miss.update_layout(
            height=260,
            margin=dict(l=10, r=40, t=10, b=10),
            xaxis=dict(
                title="Persentase Kosong (%)",
                range=[0, max(12, miss_df["Kosong (%)"].max() * 1.25)],
                showgrid=True,
                gridcolor="#F1F5F9",
            ),
            yaxis=dict(title=None, showgrid=False),
        )
        st.plotly_chart(fig_miss, width="stretch", config={"displayModeBar": False}, key="chart_missing_bar")

st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

# ===========================================================================
# BAGIAN 2: SEGMENTASI PASAR (K-MEANS CLUSTERING)
# ===========================================================================
st.markdown(
    "<div style='font-family:\"Plus Jakarta Sans\",Inter,sans-serif;font-size:1.25rem;font-weight:800;color:#0D1E38;margin:0.2rem 0 0.75rem;'>"
    "2. Segmentasi Pasar Mobil Bekas (K-Means Clustering)</div>",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def _get_clustering_artifacts(df: pd.DataFrame):
    segmented_data, summary_data = cluster_market_segments(df)

    valid_rows = segmented_data[segmented_data["market_segment"].ne("")].copy()
    feat = pd.DataFrame(index=valid_rows.index)
    feat["log_price"] = np.log1p(pd.to_numeric(valid_rows["price"], errors="coerce"))
    feat["year"] = pd.to_numeric(valid_rows["year"], errors="coerce")
    feat["log_km"] = np.log1p(pd.to_numeric(valid_rows["mileage_km"], errors="coerce").clip(lower=0))
    feat["log_cc"] = np.log1p(pd.to_numeric(valid_rows["engine_cc"], errors="coerce").clip(lower=0))

    imputed = SimpleImputer(strategy="median").fit_transform(feat)
    scaled = StandardScaler().fit_transform(imputed)

    pca_model = PCA(n_components=2, random_state=42)
    pca_coords = pca_model.fit_transform(scaled)

    valid_rows["pca_1"] = pca_coords[:, 0]
    valid_rows["pca_2"] = pca_coords[:, 1]

    return segmented_data, summary_data, valid_rows, pca_model.explained_variance_ratio_


segmented, summary, pca_df, exp_var = _get_clustering_artifacts(archive)

col_pca, col_prof = st.columns([1.2, 1], gap="medium")

with col_pca:
    with section_card("Visualisasi Segmentasi Pasar dengan PCA 2D"):
        plot_pca = pca_df.sample(min(1000, len(pca_df)), random_state=42) if len(pca_df) > 1000 else pca_df

        fig_pca = px.scatter(
            plot_pca,
            x="pca_1",
            y="pca_2",
            color="market_segment",
            color_discrete_sequence=["#019F90", "#0D1E38", "#00B8A9", "#F59E0B"],
            render_mode="svg",
            labels={
                "pca_1": f"Principal Component 1 ({exp_var[0]*100:.1f}% varians)",
                "pca_2": f"Principal Component 2 ({exp_var[1]*100:.1f}% varians)",
                "market_segment": "Segmen",
            },
            hover_data={"make": True, "model": True, "year": True, "pca_1": False, "pca_2": False},
        )
        apply_chart_theme(fig_pca)
        fig_pca.update_traces(marker=dict(size=5, opacity=0.7))
        fig_pca.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center", font=dict(size=10)),
            xaxis=dict(title=f"PCA-1 ({exp_var[0]*100:.1f}%)", showgrid=True, gridcolor="#F1F5F9"),
            yaxis=dict(title=f"PCA-2 ({exp_var[1]*100:.1f}%)", showgrid=True, gridcolor="#F1F5F9"),
        )
        st.plotly_chart(fig_pca, width="stretch", config={"displayModeBar": False}, key="chart_pca_scatter")
        st.caption(
            f"Proyeksi PCA 2D mereduksi 4 dimensi fitur (Harga, Tahun, Odometer, CC) dengan total varians terjelaskan "
            f"**{(exp_var[0]+exp_var[1])*100:.1f}%**. Pengelompokan warna murni berasal dari algoritma K-Means (Unsupervised Learning)."
        )

with col_prof:
    with section_card("Profil Statistik Tiap Segmen"):
        disp_summary = summary.copy()
        total_clustered = disp_summary["listings"].sum()
        disp_summary["Pangsa (%)"] = (disp_summary["listings"] / total_clustered * 100).map(lambda x: f"{x:.1f}%")
        disp_summary["Median Harga"] = disp_summary["median_price"].map(format_rupiah_compact)
        disp_summary["Tahun"] = disp_summary["median_year"].map(lambda x: f"{x:.0f}" if pd.notna(x) else "-")
        disp_summary["Median KM"] = disp_summary["median_mileage_km"].map(format_km)

        show_summary = disp_summary[
            ["market_segment", "listings", "Pangsa (%)", "Median Harga", "Tahun", "Median KM"]
        ].rename(columns={"market_segment": "Segmen", "listings": "Unit"})

        st.dataframe(show_summary, hide_index=True, width="stretch")

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        for _, s_row in summary.iterrows():
            s_name = s_row["market_segment"]
            s_unit = int(s_row["listings"])
            s_pct = (s_unit / total_clustered * 100) if total_clustered else 0
            s_yr = int(s_row["median_year"]) if pd.notna(s_row["median_year"]) else "-"
            s_km = format_km(s_row["median_mileage_km"])

            if s_name == "Segmen 1":
                persona_title = "Segmen 1 - Ekonomis & Komuter Entry"
                persona_desc = f"Harga: < Rp 150 Jt · Tahun: ~{s_yr} · KM: {s_km} ({s_unit:,} unit, {s_pct:.1f}% pasar)".replace(",", ".")
            elif s_name == "Segmen 2":
                persona_title = "Segmen 2 - Sweet Spot Keluarga & Komuter"
                persona_desc = f"Harga: Rp 200-500 Jt · Tahun: ~{s_yr} · KM: {s_km} ({s_unit:,} unit, {s_pct:.1f}% pasar)".replace(",", ".")
            elif s_name == "Segmen 3":
                persona_title = "Segmen 3 - Eksekutif & SUV Premium"
                persona_desc = f"Harga: Rp 1-2,5 M · Tahun: ~{s_yr} · KM: {s_km} ({s_unit:,} unit, {s_pct:.1f}% pasar)".replace(",", ".")
            else:
                persona_title = "Segmen 4 - Flagship, Supercar & Koleksi"
                persona_desc = f"Harga: > Rp 3 M · Tahun: ~{s_yr} · KM: {s_km} ({s_unit:,} unit, {s_pct:.1f}% pasar)".replace(",", ".")

            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:0.55rem 0.85rem; margin-bottom:0.4rem;">
                    <div style="font-size:0.84rem; font-weight:700; color:#0D1E38;">{persona_title}</div>
                    <div style="font-size:0.77rem; color:#475569;">{persona_desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

# ===========================================================================
# BAGIAN 3: EVALUASI MODEL PREDIKSI HARGA (MACHINE LEARNING)
# ===========================================================================
st.markdown(
    "<div style='font-family:\"Plus Jakarta Sans\",Inter,sans-serif;font-size:1.25rem;font-weight:800;color:#0D1E38;margin:0.2rem 0 0.75rem;'>"
    "3. Evaluasi Model Prediksi Harga (Machine Learning)</div>",
    unsafe_allow_html=True,
)

metadata = load_model_metadata()
models_dict = metadata.get("models", {}) if metadata else {}
best_model_name = metadata.get("best_model", "Random Forest Regressor") if metadata else "Random Forest Regressor"

if models_dict:
    model_metrics = models_dict.get(best_model_name, {})
    mae_val = model_metrics.get("MAE", 0)
    rmse_val = model_metrics.get("RMSE", 0)
    r2_val = model_metrics.get("R2", 0)

    hdr_c1, hdr_c2 = st.columns([2.2, 1], vertical_alignment="center")
    with hdr_c1:
        st.caption(
            f"Menampilkan metrik performa model utama **{best_model_name}** pada data uji holdout independen (20% data = 1.261 unit)."
        )
    with hdr_c2:
        st.markdown(
            f'<div style="text-align:right;"><span style="display:inline-flex;align-items:center;gap:0.4rem;background:#019F90;color:#FFFFFF;border-radius:999px;padding:0.35rem 0.95rem;font-size:0.8rem;font-weight:700;">Model Terbaik: {best_model_name}</span></div>',
            unsafe_allow_html=True,
        )

    kpi_cols = st.columns(3, gap="medium")
    with kpi_cols[0]:
        kpi_card(
            label="MAE (Mean Absolute Error)",
            value=format_rupiah_compact(mae_val),
            icon="gauge",
            subtext=f"Rata-rata deviasi absolut: {format_rupiah(mae_val)}",
            help_text=f"Rata-rata besar kesalahan absolut prediksi: {format_rupiah(mae_val)}.",
        )
    with kpi_cols[1]:
        kpi_card(
            label="RMSE (Root Mean Squared Error)",
            value=format_rupiah_compact(rmse_val),
            icon="bar-chart-2",
            subtext="Ketahanan terhadap outlier mobil mewah",
            help_text=f"Akar rata-rata kuadrat kesalahan: {format_rupiah(rmse_val)}.",
        )
    with kpi_cols[2]:
        kpi_card(
            label="R\u00b2 Score (Koefisien Determinasi)",
            value=f"{r2_val:.4f}" if pd.notna(r2_val) else "-",
            icon="target",
            subtext=f"Menjelaskan {r2_val*100:.1f}% variasi harga pasar",
            help_text=f"Menjelaskan {r2_val*100:.1f}% variasi harga pasar pada data uji.",
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    holdout_list = metadata.get("holdout_predictions", [])
    holdout_df = pd.DataFrame(holdout_list) if isinstance(holdout_list, list) and holdout_list else pd.DataFrame()

    col_scatter, col_residual = st.columns(2, gap="medium")

    with col_scatter:
        with section_card("Actual vs Predicted (Data Uji 20%)"):
            if not holdout_df.empty and "actual" in holdout_df and "predicted" in holdout_df:
                act_m = holdout_df["actual"] / 1_000_000_000
                pred_m = holdout_df["predicted"] / 1_000_000_000
                max_val = max(float(act_m.quantile(0.99)), float(pred_m.quantile(0.99))) * 1.05

                fig_avp = go.Figure()
                fig_avp.add_trace(
                    go.Scatter(
                        x=act_m,
                        y=pred_m,
                        mode="markers",
                        marker=dict(color="#019F90", size=5, opacity=0.55),
                        name="Data Uji",
                        hovertemplate="Aktual: Rp %{x:.2f} M<br>Prediksi: Rp %{y:.2f} M<extra></extra>",
                    )
                )
                fig_avp.add_trace(
                    go.Scatter(
                        x=[0, max_val],
                        y=[0, max_val],
                        mode="lines",
                        line=dict(color="#0D1E38", dash="dash", width=2),
                        name="Ideal (y = x)",
                    )
                )
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

    with col_residual:
        with section_card("Residual Plot (Sebaran Galat Prediksi)"):
            if not holdout_df.empty and "actual" in holdout_df and "predicted" in holdout_df:
                residuals = holdout_df["actual"] - holdout_df["predicted"]
                res_jt = residuals / 1_000_000
                pred_jt = holdout_df["predicted"] / 1_000_000

                fig_res = go.Figure()
                fig_res.add_trace(
                    go.Scatter(
                        x=pred_jt,
                        y=res_jt,
                        mode="markers",
                        marker=dict(color="#00B8A9", size=5, opacity=0.5),
                        name="Residual",
                        hovertemplate="Prediksi: Rp %{x:.0f} Jt<br>Galat: Rp %{y:.0f} Jt<extra></extra>",
                    )
                )
                fig_res.add_hline(y=0, line_color="#B91C1C", line_width=1.5, line_dash="solid")
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

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    col_imp, col_tbl = st.columns([1.05, 1.35], gap="medium")

    with col_imp:
        with section_card("Feature Importance (Faktor Penentu Harga)"):
            imp_df = get_feature_importance().head(8)
            if not imp_df.empty:
                plot_imp = imp_df.iloc[::-1]
                max_imp = float(plot_imp["importance"].max()) if not plot_imp.empty else 0.5

                fig_imp = go.Figure(
                    go.Bar(
                        x=plot_imp["importance"],
                        y=plot_imp["feature"],
                        orientation="h",
                        marker=dict(color="#019F90", cornerradius=4),
                        text=[f"{v:.3f}" for v in plot_imp["importance"]],
                        textposition="outside",
                        cliponaxis=False,
                        hovertemplate="Fitur: <b>%{y}</b><br>Importance: <b>%{x:.4f}</b><extra></extra>",
                    )
                )
                apply_chart_theme(fig_imp)
                fig_imp.update_layout(
                    height=280,
                    margin=dict(l=10, r=50, t=10, b=10),
                    xaxis=dict(title=None, showgrid=True, gridcolor="#F1F5F9", range=[0, max_imp * 1.3]),
                    yaxis=dict(title=None, showgrid=False, tickfont=dict(size=10), automargin=True),
                )
                st.plotly_chart(fig_imp, width="stretch", config={"displayModeBar": False}, key="chart_eval_imp")
            else:
                st.caption("Feature importance tidak tersedia.")

    with col_tbl:
        with section_card("Perbandingan 6 Kandidat Model Regresi"):
            rows_comp = []
            for name, m in models_dict.items():
                rows_comp.append(
                    {
                        "Model": name,
                        "MAE": format_rupiah(m.get("MAE", 0)),
                        "RMSE": format_rupiah(m.get("RMSE", 0)),
                        "R²": f"{m.get('R2', 0):.4f}",
                        "Transformasi Target": m.get("target_transform", "asli"),
                    }
                )

            comp_df = pd.DataFrame(rows_comp)
            st.dataframe(comp_df, hide_index=True, width="stretch")
            st.caption(
                f"**{best_model_name}** unggul signifikan dibanding model parametrik Linear Regression karena mampu "
                f"menangkap interaksi non-linear antara kapasitas mesin (CC), usia kendaraan, dan depresiasi merek mewah."
            )

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
else:
    st.warning("Metadata model regresi belum tersedia.", icon=":material/warning:")
