"""Editorial overview for the seven data-science project requirements."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_combined_archive, load_historical_data, load_history_data, load_training_archive
from src.modeling import (
    load_model_metadata,
    model_is_validated,
    training_eligibility,
    get_test_predictions,
)
from src.styles import apply_theme
from src.ui import format_rupiah, format_rupiah_compact, apply_rupiah_ticks


apply_theme()
excel = load_historical_data()
archive = load_combined_archive()
history = load_history_data()
training_data = load_training_archive()
eligible, eligibility_message, model_data = training_eligibility(training_data)
prices = pd.to_numeric(excel.get("price", pd.Series(dtype=float)), errors="coerce").dropna()
snapshot_count = history["snapshot_id"].nunique() if "snapshot_id" in history else 0
unique_archive_count = archive["listing_id"].nunique() if "listing_id" in archive else len(archive)

with st.container(key="project_editorial_hero"):
    intro_visual, intro_copy = st.columns([.8, 1.8], gap="large", vertical_alignment="center")
    with intro_visual:
        st.markdown(
            """<div class="project-illustration"><svg viewBox="0 0 520 330" role="img" aria-label="Ilustrasi laptop dengan tampilan analisis AutoMatch"><defs><linearGradient id="screen" x1="0" x2="1"><stop stop-color="#e5f7f5"/><stop offset="1" stop-color="#f7faf9"/></linearGradient></defs><ellipse cx="266" cy="292" rx="205" ry="17" fill="#dbe5e3"/><rect x="96" y="27" width="328" height="225" rx="17" fill="#173654"/><rect x="108" y="39" width="304" height="199" rx="9" fill="url(#screen)"/><rect x="124" y="54" width="83" height="168" rx="8" fill="#fff"/><rect x="219" y="54" width="178" height="35" rx="8" fill="#fff"/><rect x="219" y="99" width="84" height="123" rx="8" fill="#fff"/><rect x="313" y="99" width="84" height="123" rx="8" fill="#fff"/><path d="M242 78h104M242 68h68" stroke="#008b8b" stroke-width="5" stroke-linecap="round"/><path d="M236 199v-34h13v34m8 0v-51h13v51m8 0v-64h13v64" fill="#008b8b"/><path d="M324 194c14-44 24-20 34-43s19-13 29-31" fill="none" stroke="#008b8b" stroke-width="5" stroke-linecap="round"/><path d="M73 253h374l39 26H35l38-26Z" fill="#9fb7c2"/><path d="M84 258h352l24 15H60l24-15Z" fill="#d8e5e8"/><rect x="227" y="258" width="67" height="5" rx="3" fill="#a6bbc3"/><path d="M163 145h35l-5-11a4 4 0 0 0-4-3h-17a5 5 0 0 0-5 3l-4 11Z" fill="#102748"/><circle cx="173" cy="146" r="4" fill="#008b8b"/><circle cx="190" cy="146" r="4" fill="#008b8b"/></svg><span>Eksplorasi data dan pemodelan machine learning</span></div>""",
            unsafe_allow_html=True,
        )
    with intro_copy:
        st.caption("PENGANTAR SAINS DATA · PROYEK APLIKASI")
        st.title("Tentang Proyek")
        st.markdown("### Dari data iklan menuju pilihan yang lebih terarah.")
        st.write("AutoMatch membantu calon pembeli menyaring mobil bekas, membandingkan iklan, dan memahami konteks harga penawaran. Halaman ini merangkum sumber data, metode, temuan, serta batasannya.")
        if st.button("Jelajahi arsip mobil", icon=":material/directions_car:", type="primary", key="project_go_search"):
            st.switch_page("pages/2_Find_Your_Car.py")

st.markdown("### Ringkasan Data")
metrics = st.columns(4)
metrics[0].metric("Excel DKI", f"{len(excel):,}".replace(",", "."), border=True)
metrics[1].metric("Mobil unik di arsip penuh", f"{unique_archive_count:,}".replace(",", "."), border=True)
metrics[2].metric("Snapshot OLX tersimpan", f"{snapshot_count:,}".replace(",", "."), border=True)
metrics[3].metric("Data layak untuk model", f"{len(model_data):,}".replace(",", "."), border=True)
st.caption("Arsip penuh menghitung satu baris per listing unik; jumlah snapshot menghitung pengambilan OLX yang terpisah. Dataset Excel tidak memiliki tanggal pengambilan.")
if not prices.empty:
    st.caption(f"Dataset Excel: rentang harga penawaran {format_rupiah_compact(prices.min())} s/d {format_rupiah_compact(prices.max())} (Median: {format_rupiah_compact(prices.median())}).")

st.markdown("### Tujuh Komponen Metodologi Sains Data")
cards = [
    ("1. Project Overview", "Membantu calon pembeli menyaring pilihan, membandingkan iklan, dan memahami konteks harga. Aplikasi memberi konteks awal; keputusan tetap memerlukan inspeksi fisik dan dokumen resmi."),
    ("2. Data Overview", f"Excel menyumbang {len(excel):,} listing DKI tervalidasi; snapshot OLX baru mencatat waktu pengambilan. Arsip penuh merangkum mobil unik, snapshot menghitung observasi berkala.".replace(",", ".")),
    ("3. Exploratory Data Analysis", "Pahami Pasar merangkum tren merek, bahan bakar, harga, transmisi, dan hubungan harga dengan tahun/odometer. Analisis deskriptif memberikan gambaran pasar penawaran."),
    ("4. Data Preprocessing", "Kolom dinormalisasi, harga dan spesifikasi divalidasi, serta URL dipakai untuk deduplikasi. Cakupan dibatasi pada lima kota administrasi DKI Jakarta."),
    ("5. Modeling (Supervised Regression)", "Tiga algoritma regresi (Linear Regression, Decision Tree, Random Forest) dibandingkan pada data holdout (test set 20%) menggunakan metrik MAE, RMSE, dan R²."),
    ("6. Key Insights", "Merek populer seperti Toyota dan Honda mendominasi ketersediaan unit. Mobil transmisi otomatis memiliki premi harga rata-rata lebih tinggi dibanding transmisi manual."),
    ("7. Kesimpulan & Rekomendasi", "Gunakan filter dan kalkulator harga sebagai titik awal penawaran. Selalu periksa kondisi mesin, riwayat servis, dan keaslian surat sebelum melakukan transaksi."),
]
for start, size in ((0, 4), (4, 3)):
    grid = st.columns(size, gap="small")
    for col, (heading, body) in zip(grid, cards[start : start + size]):
        with col:
            with st.container(border=True, key=f"project_card_{start}_{heading.split('.')[0].strip()}"):
                st.markdown(f"#### {heading}")
                st.caption(body)

st.markdown("### Evaluasi Metodologi & Kinerja Model")
metadata = load_model_metadata()

if metadata.get("models"):
    eval_col1, eval_col2 = st.columns([1, 1], gap="large")
    with eval_col1:
        with st.container(border=True):
            st.markdown("#### Perbandingan Evaluasi Algoritma")
            st.write("Tiga algoritma regresi dievaluasi secara serempak pada test set independen (holdout 20%):")
            
            table_rows = []
            for name, metrics in metadata["models"].items():
                is_best = (name == metadata.get("best_model"))
                table_rows.append({
                    "Algoritma": f"{name} (Model Terbaik)" if is_best else f"{name} (Baseline)" if "Linear" in name else name,
                    "MAE (Rp)": format_rupiah(metrics.get("MAE")),
                    "RMSE (Rp)": format_rupiah(metrics.get("RMSE")),
                    "R² Score": f"{metrics.get('R2', 0):.4f}" if metrics.get("R2") is not None else "-",
                })
            comp_df = pd.DataFrame(table_rows)
            st.dataframe(comp_df, hide_index=True, width="stretch")
            
            best_model_name = metadata.get("best_model", "Random Forest Regressor")
            best_r2 = metadata.get("models", {}).get(best_model_name, {}).get("R2", 0)
            best_mae = metadata.get("models", {}).get(best_model_name, {}).get("MAE", 0)
            st.success(f"**Model Pilihan:** `{best_model_name}` terpilih karena menghasilkan MAE terendah ({format_rupiah_compact(best_mae)}) dan R² sebesar {best_r2:.4f}, mengungguli Linear Regression baseline.")

    with eval_col2:
        with st.container(border=True):
            st.markdown("#### Grafik Actual vs Predicted (Data Test)")
            test_preds = get_test_predictions()
            if not test_preds.empty:
                max_bound = max(test_preds["actual"].quantile(0.98), test_preds["predicted"].quantile(0.98))
                
                fig_scatter = go.Figure()
                fig_scatter.add_trace(go.Scatter(
                    x=test_preds["actual"],
                    y=test_preds["predicted"],
                    mode="markers",
                    marker=dict(color="#008B8B", size=6, opacity=0.6),
                    name="Data Uji (Test)",
                    hovertemplate="Aktual: Rp %{x:,.0f}<br>Prediksi: Rp %{y:,.0f}<extra></extra>",
                ))
                # Garis diagonal ideal
                fig_scatter.add_trace(go.Scatter(
                    x=[0, max_bound],
                    y=[0, max_bound],
                    mode="lines",
                    line=dict(color="#F59E0B", dash="dash", width=2),
                    name="Prediksi Ideal (y = x)",
                ))
                fig_scatter.update_layout(
                    height=300,
                    margin=dict(l=16, r=16, t=20, b=16),
                    paper_bgcolor="#FFFFFF",
                    plot_bgcolor="#FFFFFF",
                    font=dict(family="Inter, sans-serif", color="#0F172A", size=11),
                    xaxis=dict(title="Harga Aktual (Rp)", range=[0, max_bound], gridcolor="#F1F5F9"),
                    yaxis=dict(title="Harga Prediksi (Rp)", range=[0, max_bound], gridcolor="#F1F5F9"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                apply_rupiah_ticks(fig_scatter, axis="x", min_val=0, max_val=float(max_bound), n_ticks=5)
                apply_rupiah_ticks(fig_scatter, axis="y", min_val=0, max_val=float(max_bound), n_ticks=5)
                st.plotly_chart(fig_scatter, use_container_width=True, config={"displayModeBar": False}, key="project_actual_vs_predicted")
                st.caption(f"Scatter plot menunjukkan kedekatan nilai prediksi dengan harga aktual pada {len(test_preds):,} sampel data uji. Titik yang mendekati garis oranye menunjukkan prediksi akurat.")
            else:
                st.caption("Grafik data uji belum tersedia.")

st.markdown("### Status Model & Kriteria Validasi")
if eligible:
    st.success(f"Tersedia {len(model_data):,} listing unik yang memenuhi kriteria minimum data. {eligibility_message}".replace(",", "."))
else:
    st.info(f"Prediksi belum layak ditampilkan: {eligibility_message} Saat ini ada {len(model_data):,} listing unik yang lolos preprocessing.".replace(",", "."))
st.caption("Gerbang validasi: minimal 100 listing unik, 3 merek, dan 5 model berbeda. Target pemodelan adalah harga penawaran iklan historis DKI Jakarta.")

with st.expander("Alur Penggunaan Aplikasi AutoMatch"):
    st.markdown("**Beranda → Cari Mobil → Bandingkan Listing → Cek Harga Iklan → Buka Iklan Sumber.** Halaman Pahami Pasar dapat diakses kapan saja untuk membaca tren agregat pasar.")
