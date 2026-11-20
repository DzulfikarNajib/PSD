"""Buyer-oriented insights from saved listing data; never calls the paid API."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_combined_archive, load_historical_data_with_audit
from src.styles import apply_theme
from src.ui import (
    format_rupiah,
    format_rupiah_compact,
    apply_rupiah_ticks,
    render_data_source_status,
    render_empty_state,
)


apply_theme()
st.title("Pahami Pasar")
st.caption("Cari tahu merek dan model yang tersedia, lalu bandingkan harga iklan serta spesifikasinya sebelum membuat shortlist.")
st.info("Semua angka harga adalah harga penawaran. Hasil menggambarkan arsip AutoMatch, bukan seluruh pasar atau harga transaksi.", icon=":material/info:")

archive = load_combined_archive()
if archive.empty:
    render_empty_state("Belum ada data untuk dianalisis", "Arsip dan snapshot akan tampil setelah dataset tersedia. Tidak ada data contoh.")
    st.stop()

source = archive.copy()
source_label = "Dataset OLX aktif yang sudah dibersihkan"
render_data_source_status()

# Accept focused paths from Beranda while keeping all filters editable here.
market_makes = sorted(source.get("make", pd.Series(dtype=str)).dropna().astype(str).unique(), key=str.casefold)
market_fuels = sorted(source.get("fuel_type", pd.Series(dtype=str)).dropna().astype(str).unique(), key=str.casefold)
incoming_make = st.session_state.pop("market_focus_make", None)
incoming_fuel = st.session_state.pop("market_focus_fuel", None)
if incoming_make in market_makes:
    st.session_state["market_make_choice"] = incoming_make
if incoming_fuel in market_fuels:
    st.session_state["market_fuel_choice"] = incoming_fuel
if st.session_state.get("market_make_choice", "Semua merek") not in ["Semua merek", *market_makes]:
    st.session_state["market_make_choice"] = "Semua merek"
if st.session_state.get("market_fuel_choice", "Semua bahan bakar") not in ["Semua bahan bakar", *market_fuels]:
    st.session_state["market_fuel_choice"] = "Semua bahan bakar"
with st.container(border=True, key="market_explorer_filters"):
    st.markdown("#### Telusuri merek, model, atau bahan bakar")
    st.caption("Pilih kategori untuk melihat model yang tersedia, lalu periksa harga penawaran dan spesifikasi pada sampel tersebut.")
    focus_a, focus_b = st.columns(2)
    chosen_make = focus_a.selectbox("Merek", ["Semua merek", *market_makes], key="market_make_choice")
    chosen_fuel = focus_b.selectbox("Bahan bakar", ["Semua bahan bakar", *market_fuels], key="market_fuel_choice")
explore = source.copy()
if chosen_make != "Semua merek":
    explore = explore[explore["make"].fillna("").astype(str).eq(chosen_make)]
if chosen_fuel != "Semua bahan bakar":
    explore = explore[explore["fuel_type"].fillna("").astype(str).eq(chosen_fuel)]
explore["price"] = pd.to_numeric(explore.get("price"), errors="coerce")
explore["year"] = pd.to_numeric(explore.get("year"), errors="coerce")
explore["mileage_km"] = pd.to_numeric(explore.get("mileage_km"), errors="coerce")
explore["engine_cc"] = pd.to_numeric(explore.get("engine_cc"), errors="coerce")
explore["_cc_available"] = explore["engine_cc"].notna()
explore["_cc_inferred"] = explore.get("engine_cc_inferred", pd.Series(False, index=explore.index)).fillna(False).astype(bool) & explore["_cc_available"]
explore["_make_group"] = explore.get("make", pd.Series("Tidak dicantumkan", index=explore.index)).fillna("Tidak dicantumkan").astype(str)
model_stats = explore.groupby(["_make_group", "model"], dropna=True).agg(
    listings=("listing_id", "nunique") if "listing_id" in explore else ("model", "size"),
    median_price=("price", "median"), median_year=("year", "median"),
    median_km=("mileage_km", "median"), median_cc=("engine_cc", "median"),
    cc_reported=("_cc_available", "sum"), cc_inferred=("_cc_inferred", "sum"),
).reset_index().sort_values("listings", ascending=False)
model_stats["model"] = model_stats["model"].astype(str)
model_stats["model_key"] = model_stats["_make_group"].astype(str) + " · " + model_stats["model"]
if not model_stats.empty:
    with st.container(border=True, key="market_model_explorer"):
        label_bits = [chosen_make if chosen_make != "Semua merek" else "semua merek"]
        if chosen_fuel != "Semua bahan bakar":
            label_bits.append(chosen_fuel.lower())
        st.markdown(f"#### Model tersedia untuk {' · '.join(label_bits)}")
        model_plot = model_stats.head(12).sort_values("listings")
        model_fig = px.bar(model_plot, x="listings", y="model_key", orientation="h", color_discrete_sequence=["#008B8B"],
                           hover_data={"median_price": ":,.0f", "median_year": ":.0f", "median_km": ":,.0f", "listings": True})
        model_fig.update_layout(height=max(300, min(520, 30 * len(model_plot) + 90)), margin=dict(l=8, r=12, t=12, b=8), showlegend=False, xaxis_title="Listing unik", yaxis_title=None)
        model_fig.update_traces(marker_cornerradius=6, hovertemplate="%{y}<br>%{x:,} listing<extra></extra>")
        st.plotly_chart(model_fig, width="stretch", config={"displayModeBar": False}, key="market_models_by_make")
        st.caption("Grafik menunjukkan model dengan listing terbanyak pada filter ini. Ini mengukur ketersediaan iklan dalam arsip, bukan popularitas seluruh Jakarta.")
        available_model_names = model_stats["model_key"].tolist()
        if st.session_state.get("market_model_choice") not in available_model_names:
            st.session_state["market_model_choice"] = available_model_names[0]
        selected_model_key = st.selectbox("Pilih model untuk melihat spesifikasi", available_model_names, key="market_model_choice")
        selected_stat = model_stats[model_stats["model_key"].eq(selected_model_key)].iloc[0]
        selected_model = str(selected_stat["model"])
        selected_make = str(selected_stat["_make_group"])
        selected_rows = explore[explore["model"].astype(str).eq(selected_model) & explore["_make_group"].eq(selected_make)]
        spec_kpis = st.columns(4)
        spec_kpis[0].metric("Listing model", f"{int(selected_stat['listings']):,}".replace(",", "."), border=True)
        spec_kpis[1].metric("Median harga iklan", format_rupiah_compact(selected_stat["median_price"]) if pd.notna(selected_stat["median_price"]) else "-", border=True)
        spec_kpis[2].metric("Median kilometer", f"{selected_stat['median_km']:,.0f} km".replace(",", ".") if pd.notna(selected_stat["median_km"]) else "-", border=True)
        spec_kpis[3].metric("Median kapasitas mesin", f"{selected_stat['median_cc']:,.0f} cc".replace(",", ".") if pd.notna(selected_stat["median_cc"]) else "Belum dicantumkan", border=True)
        cc_coverage = int(selected_stat["cc_reported"])
        inferred_cc_count = int(selected_stat["cc_inferred"])
        explicit_cc_count = max(0, cc_coverage - inferred_cc_count)
        st.caption(f"CC ada pada {cc_coverage:,} dari {int(selected_stat['listings']):,} listing: {explicit_cc_count:,} tercatat pada kapasitas mesin, {inferred_cc_count:,} diperkirakan dari varian (ditandai ≈). CC kosong tidak dianggap nol.".replace(",", "."))
        if len(selected_rows) >= 10 and selected_rows["price"].notna().sum() >= 10 and selected_rows["mileage_km"].notna().sum() >= 10:
            pair = selected_rows.dropna(subset=["price", "mileage_km"])
            rho = pair["price"].corr(pair["mileage_km"], method="spearman")
            if pd.notna(rho):
                direction = "cenderung lebih rendah" if rho < -0.15 else "cenderung lebih tinggi" if rho > 0.15 else "belum menunjukkan hubungan yang kuat"
                st.info(f"Pada {len(pair):,} listing {selected_model} dengan harga dan kilometer tercatat, harga penawaran {direction} saat kilometer berubah (korelasi peringkat {rho:.2f}). Gunakan ini sebagai petunjuk membandingkan iklan, lalu cek kondisi unit secara langsung.".replace(",", "."), icon=":material/lightbulb:")
            else:
                st.caption("Sampel belum cukup untuk merangkum hubungan harga dan kilometer.")
        else:
            st.caption("Perlu sedikitnya 10 listing dengan harga dan kilometer tercatat untuk menampilkan petunjuk hubungan yang lebih masuk akal.")
        if st.button("Cari listing model ini", icon=":material/directions_car:", type="primary", key="market_go_search"):
            st.session_state["prefill_make"] = selected_make
            st.session_state["prefill_model"] = selected_model
            st.session_state["prefill_fuel"] = chosen_fuel if chosen_fuel != "Semua bahan bakar" else None
            st.switch_page("pages/2_Find_Your_Car.py")
else:
    st.info("Belum ada kombinasi merek dan bahan bakar dengan model tercatat pada pilihan sumber ini.")
active_data, preprocessing_audit = load_historical_data_with_audit()
with st.expander("Lihat Sampel Data & Statistik Deskriptif"):
    if active_data.empty:
        st.caption("Dataset bersih belum tersedia.")
    else:
        sample_columns = [
            column for column in ("listing_id", "make", "model", "year", "price", "mileage_km", "engine_cc", "engine_cc_inferred", "location_normalized")
            if column in active_data
        ]
        sample = active_data[sample_columns].head(8).copy()
        sample = sample.rename(columns={
            "listing_id": "ID Listing", "make": "Merek", "model": "Model", "year": "Tahun",
            "price": "Harga (Rp)", "mileage_km": "Kilometer", "engine_cc": "CC", "engine_cc_inferred": "CC perkiraan", "location_normalized": "Wilayah",
        })
        st.dataframe(sample, hide_index=True, width="stretch")

        numeric_columns = [column for column in ("price", "year", "mileage_km", "engine_cc") if column in active_data]
        stats = active_data[numeric_columns].apply(pd.to_numeric, errors="coerce").agg(["count", "mean", "median", "min", "max"]).T.astype(object)
        stats = stats.rename(index={"price": "Harga (Rp)", "year": "Tahun", "mileage_km": "Kilometer", "engine_cc": "CC"})
        for column in stats.index:
            is_price = column == "Harga (Rp)"
            stats.loc[column] = [
                f"{value:,.0f}".replace(",", ".") if row == "count" else (
                    format_rupiah(value) if is_price and pd.notna(value) else (f"{value:,.0f}".replace(",", ".") if pd.notna(value) else "-")
                )
                for row, value in stats.loc[column].items()
            ]
        st.markdown("**Statistik fitur numerik**")
        st.dataframe(stats, width="stretch")
        st.caption(
            f"Sel kosong keseluruhan setelah pembersihan: {preprocessing_audit.get('missing_value_pct', 0):.2f}%. Sebagian nilai CC diperoleh dari varian iklan dan ditandai pada kolom CC perkiraan."
        )

for field in ["price", "year", "mileage_km", "engine_cc"]:
    if field in source:
        source[field] = pd.to_numeric(source[field], errors="coerce")
priced = source.dropna(subset=["price"]).copy() if "price" in source else pd.DataFrame()
priced = priced[priced["price"] > 0]
unique_count = source["listing_id"].nunique() if "listing_id" in source else len(source)
make_count = source["make"].nunique() if "make" in source else 0

with st.container(border=True, key="market_scope_picker"):
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
year_min = int(source["year"].min()) if "year" in source and source["year"].notna().any() else 2000
year_max = int(source["year"].max()) if "year" in source and source["year"].notna().any() else 2024
year_span = f"{year_min}–{year_max}" if year_min != year_max else str(year_min)
kpis = st.columns(4, gap="small")
kpis[0].metric("Listing unik", f"{unique_count:,}".replace(",", "."), help="Jumlah iklan berbeda setelah listing duplikat dibersihkan.", border=True)
kpis[1].metric("Rentang tahun", year_span, help="Rentang tahun produksi mobil pada dataset aktif.", border=True)
kpis[2].metric("Merek tersedia", f"{make_count:,}".replace(",", "."), help="Jumlah nama merek berbeda pada sumber data terpilih.", border=True)
kpis[3].metric("Median harga iklan", format_rupiah_compact(priced["price"].median()) if len(priced) else "-", help="Nilai tengah harga penawaran pada iklan dengan harga valid; bukan harga transaksi.", border=True)
st.caption("Cara membaca: jumlah menunjukkan cakupan iklan tersimpan; median adalah titik tengah harga sehingga tidak mudah ditarik naik oleh beberapa mobil yang sangat mahal.")
with st.container(border=True, key="market_scope_summary"):
    st.caption(f"Rentang analisis: {scope_note}".replace(",", "."))

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
            st.plotly_chart(donut_fig, width="stretch", config={"displayModeBar": False}, key="market_donut_chart")
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
            st.plotly_chart(bar_trans, width="stretch", config={"displayModeBar": False}, key="market_trans_comparison")
            
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
            st.plotly_chart(finish_chart(fig_hist, 320), width="stretch", config={"displayModeBar": False}, key="market_hist_clean")
            
            q1, q3 = filtered_priced["price"].quantile([0.25, 0.75])
            st.caption(f"50% mobil pada rentang ini berada di kisaran **{format_rupiah_compact(q1)}** sampai **{format_rupiah_compact(q3)}**.")
        else:
            st.caption("Data harga valid belum mencukupi.")

with year_scatter_col:
    with st.container(border=True):
        st.markdown("**Median dan kuartil harga per tahun**")
        scatter_df = filtered_priced.dropna(subset=["year", "price"]).copy()
        if len(scatter_df) >= 10:
            fig_scat = px.box(
                scatter_df,
                x="year",
                y="price",
                points=False,
                labels={"year": "Tahun Kendaraan", "price": "Harga Iklan"},
                color_discrete_sequence=[TEAL],
            )
            fig_scat.update_traces(
                hovertemplate="Tahun %{x}<br>Rentang kuartil: %{y}<extra></extra>",
                line=dict(color=DARK_TEAL),
                fillcolor="rgba(0,139,139,0.2)",
            )
            fig_scat.update_layout(
                xaxis=dict(title="Tahun Model", type="linear"),
                yaxis=dict(title="Harga Iklan", type="log"),
            )
            st.plotly_chart(finish_chart(fig_scat, 380), width="stretch", config={"displayModeBar": False}, key="market_price_year_box")
            st.caption(f"Kotak menunjukkan rentang kuartil harga iklan per tahun; sumbu harga memakai skala log agar rentang nilai lebih terbaca. Sampel berisi {len(scatter_df):,} listing.".replace(",", "."))
        else:
            st.caption("Data tahun dan harga belum cukup untuk membentuk box plot.")

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
            st.plotly_chart(finish_chart(fig_km, 300), width="stretch", config={"displayModeBar": False}, key="market_km_chart")
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
            st.plotly_chart(finish_chart(fig_cc, 300), width="stretch", config={"displayModeBar": False}, key="market_cc_chart")
            top_engine = engine_counts.sort_values("Jumlah", ascending=False).iloc[0]
            st.caption(f"Kapasitas tercatat pada {len(engines):,} listing. Rentang terbanyak: **{top_engine['Rentang']}**, {int(top_engine['Jumlah']):,} listing. Data ini tidak menunjukkan kecocokan untuk penggunaan tertentu.".replace(",", "."))
        else:
            st.caption("Data kapasitas mesin belum mencukupi.")

# ---------------------------------------------------------
# Dynamic Key Insights & Rekomendasi Pasar (Analitik Aktif)
# ---------------------------------------------------------
st.markdown("### Temuan Kunci Pasar & Rekomendasi")
st.caption("Insight dihitung secara dinamis dari data yang sedang aktif, memberikan ringkasan pasar yang objektif bagi calon pembeli.")

ins_df = explore if len(explore) >= 10 else source

# 1. Depresiasi & Sweet Spot Usia
years_valid = ins_df["year"].dropna()
prices_valid = ins_df["price"].dropna()
if len(years_valid) >= 5 and len(prices_valid) >= 5:
    median_recent = ins_df[ins_df["year"].ge(2020)]["price"].median()
    median_older = ins_df[ins_df["year"].between(2015, 2019)]["price"].median()
    if pd.notna(median_recent) and pd.notna(median_older) and median_recent > 0:
        deprec_pct = max(0, int(round((median_recent - median_older) / median_recent * 100)))
        sweet_spot_desc = f"Mobil usia 5–9 tahun (2015–2019) mengalami penurunan harga median ~{deprec_pct}% dibanding unit baru (≥2020), menjadikannya sweet spot rasio harga-ke-nilai."
    else:
        sweet_spot_desc = "Penurunan harga paling curam terjadi pada 3–4 tahun pertama; membeli mobil usia 5–7 tahun meminimalkan kerugian depresiasi."
else:
    sweet_spot_desc = "Penurunan harga paling curam terjadi pada 3–4 tahun pertama masa pemakaian unit."

# 2. Segmen Terlikuid Mesin
engines_valid = ins_df["engine_cc"].dropna()
if not engines_valid.empty:
    mid_cc_share = (engines_valid.between(1001, 1500).sum() / len(engines_valid)) * 100
    liquid_desc = f"Sebanyak {mid_cc_share:.1f}% unit di sampel ini bermesin 1.001–1.500 cc. Kapasitas ini paling likuid dengan perputaran unit cepat dan ketersediaan onderdil melimpah."
else:
    liquid_desc = "Kapasitas mesin 1.000–1.500 cc mendominasi perputaran iklan di DKI Jakarta dengan likuiditas suku cadang paling terjamin."

# 3. Rasio Odometer Riil
km_valid = ins_df["mileage_km"].dropna()
if not km_valid.empty and not years_valid.empty:
    curr_yr = 2024
    annual_kms = (km_valid / (curr_yr - years_valid).clip(lower=1)).dropna()
    med_annual_km = int(annual_kms.median()) if not annual_kms.empty else 15000
    odo_desc = f"Rata-rata penggunaan normal Jakarta di sampel ini adalah ~{med_annual_km:,} km/tahun. Waspadai unit usia >5 tahun dengan odometer jauh di bawah standar tanpa riwayat servis bengkel resmi.".replace(",", ".")
else:
    odo_desc = "Penggunaan normal mobil harian berkisar 15.000–20.000 km/tahun. Periksa kecocokan odometer dengan kondisi pedal dan setir."

insight_cols = st.columns(3, gap="medium")
with insight_cols[0]:
    with st.container(border=True):
        st.caption("SWEET SPOT DEPRESIASI")
        st.markdown("#### Usia 5–7 Tahun")
        st.write(sweet_spot_desc)

with insight_cols[1]:
    with st.container(border=True):
        st.caption("SEGMEN TERLIKUID")
        st.markdown("#### Mesin 1.001–1.500 cc")
        st.write(liquid_desc)

with insight_cols[2]:
    with st.container(border=True):
        st.caption("INSPEKSI ODOMETER")
        st.markdown("#### Rasio Jarak Tempuh")
        st.write(odo_desc)

if st.button("Cari mobil berdasarkan insight ini →", type="primary", key="market_to_search_cta"):
    st.switch_page("pages/2_Find_Your_Car.py")

st.markdown("")

with st.expander("Tentang sumber dan batasan data"):
    st.write(f"Sumber data aktif: **{source_label}**. Angka merangkum {unique_count:,} mobil unik dari {len(source):,} baris data tersimpan.".replace(",", "."))
    st.write("Dataset OLX aktif sudah melalui preprocessing dan menjadi sumber grafik pasar. Seluruh grafik menunjukkan harga penawaran pengiklan, bukan kesepakatan transaksi riil di pasar.")
