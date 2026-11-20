"""Preprocessing & Segmentasi — alur penyiapan data dan segmentasi pasar K-Means.

Tab 1: Preprocessing
- Funnel Kualitas Data (Data Mentah s/d Data Siap)
- Langkah-langkah Preprocessing aktual dengan metrik nyata
- Analisis Missing Values per kolom kunci

Tab 2: Segmentasi Pasar (Unsupervised Learning)
- Visualisasi Proyeksi 2D PCA dari Klaster K-Means (4 segmen)
- Profil Karakteristik & Distribusi Tiap Segmen
- Kartu Profil Persona Dinamis
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

from src.data_loader import load_combined_archive, load_historical_data_with_audit
from src.market_segments import cluster_market_segments
from src.styles import apply_theme
from src.ui import build_preprocessing_funnel, format_km, format_rupiah_compact
from src.ui_components import (
    apply_chart_theme,
    insight_card,
    kpi_card,
    page_header,
    section_card,
)

apply_theme()

page_header(
    icon="⚙️",
    title="Preprocessing & Segmentasi",
    subtitle="Transparansi pipa rekayasa data dan pengelompokan segmen pasar mobil bekas dengan algoritma K-Means.",
)

archive, audit = load_historical_data_with_audit()

if archive.empty:
    st.warning("Data arsip tidak dapat dimuat.", icon=":material/warning:")
    st.stop()

tab_prep, tab_seg = st.tabs(["🧹 Preprocessing & Kualitas Data", "🗂️ Segmentasi Pasar (K-Means)"])

# ===========================================================================
# TAB 1: PREPROCESSING & KUALITAS DATA
# ===========================================================================
with tab_prep:
    # 1. Ringkasan Funnel Kualitas Data
    col_funnel_tbl, col_funnel_viz = st.columns([1.1, 1], gap="medium")
    
    with col_funnel_tbl:
        with section_card("Funnel Pembersihan Data"):
            funnel_df = build_preprocessing_funnel(audit)
            
            # Format tampilan tabel funnel
            disp_funnel = funnel_df.copy()
            disp_funnel["Listing tersisa"] = disp_funnel["Listing tersisa"].map(lambda x: f"{x:,}".replace(",", "."))
            disp_funnel["Dibuang pada tahap ini"] = disp_funnel["Dibuang pada tahap ini"].map(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "-")
            disp_funnel = disp_funnel.rename(columns={
                "Tahap": "Tahapan Pipeline",
                "Listing tersisa": "Observasi Tersisa",
                "Dibuang pada tahap ini": "Data Dieliminasi",
            })
            st.dataframe(disp_funnel, hide_index=True, width="stretch")
            
            raw_n = audit.get("raw_rows", 10563)
            clean_n = audit.get("clean_rows", len(archive))
            eff_pct = (clean_n / raw_n * 100) if raw_n else 0
            st.caption(f"Retensi data bersih: **{clean_n:,} dari {raw_n:,} listing ({eff_pct:.1f}%)** siap untuk analisis dan pelatihan model Machine Learning.".replace(",", "."))

    with col_funnel_viz:
        with section_card("Visualisasi Retensi Observasi"):
            fig_funnel = go.Figure(go.Bar(
                x=funnel_df["Listing tersisa"],
                y=funnel_df["Tahap"],
                orientation="h",
                marker=dict(
                    color=["#0B2A5B", "#08376E", "#008B8B", "#066B6B", "#10B981"],
                    cornerradius=4,
                ),
                text=[f"{v:,}".replace(",", ".") for v in funnel_df["Listing tersisa"]],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(color="#FFFFFF", size=10, family="Inter, sans-serif"),
                hovertemplate="Tahap: <b>%{y}</b><br>Tersisa: <b>%{x:,}</b><extra></extra>",
            ))
            apply_chart_theme(fig_funnel)
            fig_funnel.update_layout(
                height=250,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title=None, showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title=None, showgrid=False, autorange="reversed"),
            )
            st.plotly_chart(fig_funnel, width="stretch", config={"displayModeBar": False}, key="chart_funnel_bar")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 2. Langkah-langkah Preprocessing & Missing Values
    col_steps, col_missing = st.columns([1.2, 1], gap="medium")
    
    with col_steps:
        with section_card("Aturan & Langkah Pembersihan Aktual"):
            st.markdown(
                f"""
                - **Filter Wilayah DKI Jakarta**: Membatasi cakupan hanya pada 5 kota administrasi (*Jakarta Selatan, Utara, Pusat, Barat, Timur*). **{audit.get('outside_dki_rows_removed', 851):,} listing** di luar DKI Jakarta dieliminasi.
                - **Deduplikasi Listing**: Menghapus duplikat iklan snapshot berulang berdasarkan `listing_id` kanonis. Sebanyak **{audit.get('duplicate_rows_removed', 3352):,} baris** duplikat dibersihkan.
                - **Penyaringan Outlier Harga**: Menyingkirkan indikasi uang muka (TDP/angsuran) dengan harga **< Rp 30 Juta ({audit.get('low_price_rows_removed', 57):,} unit)** serta harga ekstrem **> Rp 30 Miliar ({audit.get('high_price_rows_removed', 2):,} unit)**.
                - **Rekayasa Fitur Odometer (`mileage_km`)**: Mengonversi rentang teks OLX (misal *20.000–25.000 km*) menjadi titik tengah numerik (*22.500 km*).
                - **Inferensi Kapasitas Mesin (`engine_cc`)**: Mengisi nilai CC kosong dari angka liter pada varian judul iklan (misal *1.5 G* $\\to$ *1.500 cc*). Sebanyak **{audit.get('engine_cc_from_variant_rows', 217):,} nilai** berhasil diperkirakan (ditandai $\\approx$).
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

            fig_miss = go.Figure(go.Bar(
                x=miss_df["Kosong (%)"],
                y=miss_df["Fitur"],
                orientation="h",
                marker=dict(color="#008B8B", cornerradius=4),
                text=[f"{v:.1f}%" for v in miss_df["Kosong (%)"]],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="Fitur: <b>%{y}</b><br>Nilai Kosong: <b>%{x:.2f}%</b><extra></extra>",
            ))
            apply_chart_theme(fig_miss)
            fig_miss.update_layout(
                height=260,
                margin=dict(l=10, r=40, t=10, b=10),
                xaxis=dict(title="Persentase Kosong (%)", range=[0, max(12, miss_df['Kosong (%)'].max() * 1.25)], showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title=None, showgrid=False),
            )
            st.plotly_chart(fig_miss, width="stretch", config={"displayModeBar": False}, key="chart_missing_bar")


# ===========================================================================
# TAB 2: SEGMENTASI PASAR (K-MEANS)
# ===========================================================================
with tab_seg:
    @st.cache_data(show_spinner=False)
    def _get_clustering_artifacts(df: pd.DataFrame):
        segmented_data, summary_data = cluster_market_segments(df)
        
        # Hitung PCA 2D untuk visualisasi
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

    # 1. Visualisasi PCA 2D
    with col_pca:
        with section_card("Visualisasi Segmentasi Pasar dengan PCA 2D"):
            # Sampling untuk fluid rendering WebGL
            plot_pca = pca_df.sample(min(2500, len(pca_df)), random_state=42) if len(pca_df) > 2500 else pca_df
            
            fig_pca = px.scatter(
                plot_pca,
                x="pca_1",
                y="pca_2",
                color="market_segment",
                color_discrete_sequence=["#008B8B", "#0284C7", "#F59E0B", "#10B981"],
                render_mode="webgl",
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

    # 2. Tabel Profil Segmen
    with col_prof:
        with section_card("Profil Statistik Tiap Segmen"):
            disp_summary = summary.copy()
            total_clustered = disp_summary["listings"].sum()
            disp_summary["Pangsa (%)"] = (disp_summary["listings"] / total_clustered * 100).map(lambda x: f"{x:.1f}%")
            disp_summary["Median Harga"] = disp_summary["median_price"].map(format_rupiah_compact)
            disp_summary["Tahun"] = disp_summary["median_year"].map(lambda x: f"{x:.0f}" if pd.notna(x) else "-")
            disp_summary["Median KM"] = disp_summary["median_mileage_km"].map(format_km)
            
            show_summary = disp_summary[[
                "market_segment", "listings", "Pangsa (%)", "Median Harga", "Tahun", "Median KM"
            ]].rename(columns={
                "market_segment": "Segmen",
                "listings": "Unit",
            })
            
            st.dataframe(show_summary, hide_index=True, width="stretch")

            # Profil Persona Terhitung
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            for _, s_row in summary.iterrows():
                s_name = s_row["market_segment"]
                s_unit = int(s_row["listings"])
                s_pct = (s_unit / total_clustered * 100) if total_clustered else 0
                s_price = format_rupiah_compact(s_row["median_price"])
                s_yr = int(s_row["median_year"]) if pd.notna(s_row["median_year"]) else "-"
                s_km = format_km(s_row["median_mileage_km"])
                
                # Nama deskriptif sesuai urutan median harga
                if s_name == "Segmen 1":
                    persona_title = "Segmen 1 — Ekonomis & Komuter Entry"
                    persona_desc = f"Harga: < Rp 150 Jt · Tahun: ~{s_yr} · KM: {s_km} ({s_unit:,} unit, {s_pct:.1f}% pasar)".replace(",", ".")
                elif s_name == "Segmen 2":
                    persona_title = "Segmen 2 — Sweet Spot Keluarga & Komuter"
                    persona_desc = f"Harga: Rp 200–500 Jt · Tahun: ~{s_yr} · KM: {s_km} ({s_unit:,} unit, {s_pct:.1f}% pasar)".replace(",", ".")
                elif s_name == "Segmen 3":
                    persona_title = "Segmen 3 — Eksekutif & SUV Premium"
                    persona_desc = f"Harga: Rp 1–2,5 M · Tahun: ~{s_yr} · KM: {s_km} ({s_unit:,} unit, {s_pct:.1f}% pasar)".replace(",", ".")
                else:
                    persona_title = "Segmen 4 — Flagship, Supercar & Koleksi"
                    persona_desc = f"Harga: > Rp 3 M · Tahun: ~{s_yr} · KM: {s_km} ({s_unit:,} unit, {s_pct:.1f}% pasar)".replace(",", ".")

                st.markdown(
                    f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:0.6rem 0.85rem; margin-bottom:0.45rem;">
                        <div style="font-size:0.84rem; font-weight:700; color:#0B2A5B;">{persona_title}</div>
                        <div style="font-size:0.77rem; color:#475569;">{persona_desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
