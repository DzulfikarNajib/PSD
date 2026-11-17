"""Buyer-oriented insights from saved listing data; never calls the paid API."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_history_data, load_live_data, load_combined_archive
from src.styles import apply_theme
from src.ui import (
    format_rupiah,
    format_rupiah_compact,
    apply_rupiah_ticks,
    listing_data_context,
    render_data_source_status,
    render_empty_state,
)


apply_theme()
st.title("Pahami Pasar")
st.caption("Bandingkan komposisi kendaraan dan pola harga dari listing yang tersimpan.")
st.info("Semua angka harga adalah harga penawaran. Hasil menggambarkan arsip AutoMatch, bukan seluruh pasar atau harga transaksi.", icon=":material/info:")

history, live, archive = load_history_data(), load_live_data(), load_combined_archive()
if archive.empty and history.empty and live.empty:
    render_empty_state("Belum ada data untuk dianalisis", "Arsip dan snapshot akan tampil setelah dataset tersedia atau refresh manual berhasil. Tidak ada data contoh.")
    st.stop()

col_src, col_scope = st.columns([1, 1], gap="medium")
with col_src:
    source_choice = st.radio(
        "Pilih sumber data",
        ["Arsip Penuh", "Listing Terbaru"],
        horizontal=True,
        key="market_source_choice",
        help="Arsip penuh memuat Excel dan snapshot OLX tersimpan. Listing terbaru hanya membaca snapshot OLX paling baru.",
    )
if source_choice == "Arsip Penuh":
    source = archive.copy()
    source_label = "Arsip penuh (Excel + snapshot OLX tersimpan)"
    snapshot_count = history["snapshot_id"].nunique() if "snapshot_id" in history else 0
else:
    source = live.copy()
    source_label = "Snapshot OLX terbaru"
    snapshot_count = source["snapshot_id"].nunique() if "snapshot_id" in source else 0

if source.empty:
    st.info("Belum ada data di pilihan ini. Pilih Arsip Penuh atau lakukan refresh manual untuk memperoleh listing terbaru.")
    st.stop()
render_data_source_status()
st.caption(listing_data_context(source))

for field in ["price", "year", "mileage_km", "engine_cc"]:
    if field in source:
        source[field] = pd.to_numeric(source[field], errors="coerce")
priced = source.dropna(subset=["price"]).copy() if "price" in source else pd.DataFrame()
priced = priced[priced["price"] > 0]
unique_count = source["listing_id"].nunique() if "listing_id" in source else len(source)
make_count = source["make"].nunique() if "make" in source else 0

with col_scope:
    scope_choice = st.radio(
        "Rentang harga analisis",
        ["Pasar Umum (≤ Persentil 95)", "Semua Data"],
        horizontal=True,
        key="market_scope_choice",
        help="Pasar Umum mengecualikan harga di atas persentil ke-95. Pilihan ini membantu membaca sebaran utama tanpa menghapus data dari arsip.",
    )

if not priced.empty and scope_choice == "Pasar Umum (≤ Persentil 95)":
    p95 = priced["price"].quantile(0.95)
    filtered_priced = priced[priced["price"] <= p95].copy()
    scope_note = f"Grafik harga menampilkan {len(filtered_priced):,} listing sampai persentil ke-95 (maks. {format_rupiah_compact(p95)}); ringkasan sumber tetap memakai seluruh arsip."
else:
    filtered_priced = priced.copy()
    scope_note = f"Menampilkan seluruh {len(filtered_priced):,} listing bertarif valid termasuk mobil bernilai tinggi."

st.markdown("### Ringkasan Pilihan")
kpis = st.columns(4, gap="small")
kpis[0].metric("Mobil unik", f"{unique_count:,}".replace(",", "."), border=True)
kpis[1].metric("Snapshot OLX", f"{snapshot_count:,}".replace(",", "."), border=True)
kpis[2].metric("Merek tersedia", f"{make_count:,}".replace(",", "."), border=True)
kpis[3].metric("Median harga iklan", format_rupiah_compact(priced["price"].median()) if len(priced) else "-", border=True)
st.caption(f"Sumber: **{source_label}** · {len(source):,} baris · {unique_count:,} mobil unik. {scope_note}".replace(",", "."))

if not priced.empty:
    price_median = float(priced["price"].median())
    make_counts = source["make"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().value_counts()
    if not make_counts.empty:
        most_common_make = make_counts.index[0]
        make_share = int(round(make_counts.iloc[0] / unique_count * 100)) if unique_count else 0
        insight = (
            f"Median harga iklan pada sumber ini {format_rupiah_compact(price_median)}. "
            f"Merek terbanyak adalah {most_common_make} ({make_counts.iloc[0]:,} dari {unique_count:,} mobil unik, {make_share}%)."
        ).replace(",", ".")
    else:
        insight = f"Median harga iklan pada sumber ini {format_rupiah_compact(price_median)} dari {len(priced):,} listing dengan harga valid.".replace(",", ".")
    st.info(insight, title="Ringkasan sumber", icon=":material/insights:")

TEAL = "#008B8B"
DARK_TEAL = "#066B6B"
NAVY = "#0F172A"
SLATE = "#475569"
BORDER_COLOR = "#E2E8F0"
DONUT_PALETTE = ["#008B8B", "#0F766E", "#0369A1", "#F59E0B", "#10B981", "#64748B"]


def finish_chart(fig, height=320):
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=20, b=16),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Inter, sans-serif", color=NAVY, size=12),
        xaxis=dict(gridcolor="#F1F5F9", zerolinecolor=BORDER_COLOR),
        yaxis=dict(gridcolor="#F1F5F9", zerolinecolor=BORDER_COLOR),
        legend=dict(font=dict(color=NAVY, size=11)),
    )
    return fig


st.markdown("### Komposisi & Karakteristik Pasar")
comp_col1, comp_col2 = st.columns([1, 1.2], gap="large")

with comp_col1:
    with st.container(border=True):
        st.markdown("**Komposisi Bahan Bakar & Transmisi**")
        breakdown_type = st.radio("Pilih dimensi:", ["Bahan Bakar", "Transmisi"], horizontal=True, key="market_donut_type")
        col_name = "fuel_type" if breakdown_type == "Bahan Bakar" else "transmission"
        
        counts = source[col_name].fillna("Tidak dicantumkan").astype(str).replace("", "Tidak dicantumkan").value_counts()
        if not counts.empty:
            total_items = counts.sum()
            donut_fig = go.Figure(data=[go.Pie(
                labels=counts.index,
                values=counts.values,
                hole=0.6,
                marker=dict(colors=DONUT_PALETTE[:len(counts)], line=dict(color="#FFFFFF", width=2)),
                textinfo="percent",
                hoverinfo="label+value+percent",
                hovertemplate="%{label}: <b>%{value:,} mobil</b> (%{percent})<extra></extra>",
            )])
            donut_fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="#FFFFFF",
                font=dict(family="Inter, sans-serif", color=NAVY),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                annotations=[dict(text=f"<b>{total_items:,}</b><br><span style='font-size:11px;color:#64748B;'>Total</span>".replace(",", "."), x=0.5, y=0.5, font_size=16, showarrow=False)],
            )
            st.plotly_chart(donut_fig, use_container_width=True, config={"displayModeBar": False}, key="market_donut_chart")
            dominant_item = counts.index[0]
            st.caption(f"Kategori terbanyak: **{dominant_item}** mencakup {(counts.iloc[0]/total_items)*100:.1f}% dari listing.")
        else:
            st.caption("Data belum tersedia.")

with comp_col2:
    with st.container(border=True):
        st.markdown("**Perbandingan Median Harga Berdasarkan Transmisi**")
        trans_priced = filtered_priced.dropna(subset=["transmission", "price"]).copy()
        trans_priced = trans_priced[trans_priced["transmission"].ne("")]
        if len(trans_priced) >= 5 and trans_priced["transmission"].nunique() >= 2:
            trans_summary = trans_priced.groupby("transmission")["price"].agg(["median", "count"]).reset_index()
            trans_summary = trans_summary.sort_values("median", ascending=False)
            
            bar_trans = go.Figure(go.Bar(
                x=trans_summary["transmission"],
                y=trans_summary["median"],
                text=[format_rupiah_compact(v) for v in trans_summary["median"]],
                textposition="outside",
                cliponaxis=False,
                marker=dict(color=TEAL, cornerradius=6),
                hovertemplate="Transmisi %{x}<br>Median: <b>%{text}</b><extra></extra>",
            ))
            bar_trans.update_layout(
                height=300,
                margin=dict(l=16, r=16, t=20, b=16),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font=dict(family="Inter, sans-serif", color=NAVY, size=12),
                yaxis=dict(title=None, showgrid=True, gridcolor="#F1F5F9"),
                xaxis=dict(title=None, showgrid=False),
            )
            apply_rupiah_ticks(bar_trans, axis="y", min_val=0, max_val=float(trans_summary["median"].max()) * 1.25, n_ticks=5)
            st.plotly_chart(bar_trans, use_container_width=True, config={"displayModeBar": False}, key="market_trans_comparison")
            
            t_auto = trans_summary.loc[trans_summary["transmission"].str.contains("Otomatis|Automatic", case=False), "median"]
            t_man = trans_summary.loc[trans_summary["transmission"].str.contains("Manual", case=False), "median"]
            if not t_auto.empty and not t_man.empty:
                diff = float(t_auto.iloc[0]) - float(t_man.iloc[0])
                diff_pct = (diff / float(t_man.iloc[0])) * 100
                direction = "lebih tinggi" if diff > 0 else "lebih rendah" if diff < 0 else "sama"
                st.caption(f"Pada sampel ini, median penawaran otomatis {direction} {format_rupiah_compact(abs(diff))} ({abs(diff_pct):.1f}%) dibanding manual. Ini perbandingan deskriptif, bukan efek transmisi saja.")
        else:
            st.caption("Data transmisi belum cukup untuk perbandingan harga.")

st.markdown("### Sebaran Harga & Analisis Tahun")
price_hist_col, year_scatter_col = st.columns(2, gap="medium")

with price_hist_col:
    with st.container(border=True):
        st.markdown("**Distribusi Sebaran Harga Mobil**")
        if len(filtered_priced) >= 5:
            hist_min = float(filtered_priced["price"].min())
            hist_max = float(filtered_priced["price"].max())
            nbins = min(20, max(8, len(filtered_priced) // 15))
            
            fig_hist = px.histogram(
                filtered_priced,
                x="price",
                nbins=nbins,
                labels={"price": "Harga Iklan", "count": "Jumlah Mobil"},
                color_discrete_sequence=[TEAL],
            )
            fig_hist.update_traces(
                marker_line_color="#FFFFFF",
                marker_line_width=1,
                hovertemplate="Rentang: %{x}<br>Jumlah: %{y:,} mobil<extra></extra>",
            )
            median_val = float(filtered_priced["price"].median())
            fig_hist.add_vline(
                x=median_val,
                line_dash="dash",
                line_color="#F59E0B",
                annotation_text=f"Median ({format_rupiah_compact(median_val)})",
                annotation_position="top right",
                annotation_font=dict(size=11, color="#B45309"),
            )
            fig_hist.update_layout(
                xaxis=dict(title="Harga Iklan (Rp)"),
                yaxis=dict(title="Jumlah Mobil"),
            )
            apply_rupiah_ticks(fig_hist, axis="x", min_val=hist_min, max_val=hist_max, n_ticks=6)
            st.plotly_chart(finish_chart(fig_hist, 320), use_container_width=True, config={"displayModeBar": False}, key="market_hist_clean")
            
            q1, q3 = filtered_priced["price"].quantile([0.25, 0.75])
            st.caption(f"50% mobil pada rentang ini berada di kisaran **{format_rupiah_compact(q1)}** sampai **{format_rupiah_compact(q3)}**.")
        else:
            st.caption("Data harga valid belum mencukupi.")

with year_scatter_col:
    with st.container(border=True):
        st.markdown("**Korelasi Tahun Kendaraan terhadap Harga**")
        scatter_df = filtered_priced.dropna(subset=["year", "price"]).copy()
        if len(scatter_df) >= 10:
            fig_scat = px.scatter(
                scatter_df,
                x="year",
                y="price",
                color="make" if scatter_df["make"].nunique() <= 6 else None,
                labels={"year": "Tahun Kendaraan", "price": "Harga Iklan", "make": "Merek"},
                opacity=0.68,
                color_discrete_sequence=DONUT_PALETTE,
                hover_data=[c for c in ["make", "model", "mileage_km"] if c in scatter_df.columns],
            )
            fig_scat.update_traces(marker=dict(size=6))
            fig_scat.update_layout(
                xaxis=dict(title="Tahun Model"),
                yaxis=dict(title="Harga Iklan"),
            )
            y_min = float(scatter_df["price"].min())
            y_max = float(scatter_df["price"].max())
            apply_rupiah_ticks(fig_scat, axis="y", min_val=y_min, max_val=y_max, n_ticks=6)
            st.plotly_chart(finish_chart(fig_scat, 320), use_container_width=True, config={"displayModeBar": False}, key="market_scatter_year_clean")
            
            corr = scatter_df["year"].corr(scatter_df["price"])
            st.caption(f"Korelasi linear tahun dan harga pada {len(scatter_df):,} listing: **{corr:.2f}**. Nilai ini menunjukkan hubungan dalam sampel, bukan sebab-akibat.".replace(",", "."))
        else:
            st.caption("Data tahun dan harga belum mencukupi untuk scatter plot.")

st.markdown("### Spesifikasi Odometer & Kapasitas Mesin")
spec_cols = st.columns(2, gap="medium")
with spec_cols[0]:
    with st.container(border=True):
        st.markdown("**Sebaran Odometer (Kilometer)**")
        mileage = source.dropna(subset=["mileage_km"]).copy() if "mileage_km" in source else pd.DataFrame()
        if len(mileage) >= 5 and mileage["mileage_km"].nunique() >= 3:
            mileage["Rentang odometer"] = pd.cut(
                mileage["mileage_km"],
                bins=[-1, 25_000, 50_000, 100_000, 150_000, 250_000, float("inf")],
                labels=["≤ 25 rb km", "25 - 50 rb km", "50 - 100 rb km", "100 - 150 rb km", "150 - 250 rb km", "> 250 rb km"],
            )
            mileage_counts = mileage["Rentang odometer"].value_counts(sort=False).rename_axis("Rentang").rename("Jumlah").reset_index()
            fig_km = px.bar(mileage_counts, x="Rentang", y="Jumlah", color_discrete_sequence=[TEAL], text="Jumlah")
            fig_km.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=6)
            fig_km.update_xaxes(title=None, showgrid=False)
            fig_km.update_yaxes(title="Jumlah Mobil")
            st.plotly_chart(finish_chart(fig_km, 300), use_container_width=True, config={"displayModeBar": False}, key="market_km_chart")
            st.caption(f"Tercatat pada {len(mileage):,} mobil. Odometer perlu diverifikasi langsung saat inspeksi unit.".replace(",", "."))
        else:
            st.caption("Data kilometer belum mencukupi.")

with spec_cols[1]:
    with st.container(border=True):
        st.markdown("**Sebaran Kapasitas Mesin (CC)**")
        engines = source.dropna(subset=["engine_cc"]).copy() if "engine_cc" in source else pd.DataFrame()
        if len(engines) >= 5 and engines["engine_cc"].nunique() >= 3:
            engines["Rentang CC"] = pd.cut(
                engines["engine_cc"],
                bins=[0, 1000, 1500, 2000, 3000, float("inf")],
                labels=["≤ 1.000 cc", "1.001 - 1.500 cc", "1.501 - 2.000 cc", "2.001 - 3.000 cc", "> 3.000 cc"],
            )
            engine_counts = engines["Rentang CC"].value_counts(sort=False).rename_axis("Rentang").rename("Jumlah").reset_index()
            fig_cc = px.bar(engine_counts, x="Rentang", y="Jumlah", color_discrete_sequence=[TEAL], text="Jumlah")
            fig_cc.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=6)
            fig_cc.update_xaxes(title=None, showgrid=False)
            fig_cc.update_yaxes(title="Jumlah Mobil")
            st.plotly_chart(finish_chart(fig_cc, 300), use_container_width=True, config={"displayModeBar": False}, key="market_cc_chart")
            top_engine = engine_counts.sort_values("Jumlah", ascending=False).iloc[0]
            st.caption(f"Kapasitas tercatat pada {len(engines):,} listing. Rentang terbanyak: **{top_engine['Rentang']}**, {int(top_engine['Jumlah']):,} listing. Data ini tidak menunjukkan kecocokan untuk penggunaan tertentu.".replace(",", "."))
        else:
            st.caption("Data kapasitas mesin belum mencukupi.")

with st.expander("Tentang sumber dan batasan data"):
    st.write(f"Sumber data aktif: **{source_label}**. Angka merangkum {unique_count:,} mobil unik dari {len(source):,} baris data tersimpan.".replace(",", "."))
    st.write("Arsip Excel tidak memiliki tanggal pengambilan. Snapshot OLX menyimpan waktu saat refresh dijalankan. Seluruh grafik menunjukkan harga penawaran pengiklan, bukan kesepakatan transaksi riil di pasar.")
