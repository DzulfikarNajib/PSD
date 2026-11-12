"""Buyer-oriented analysis of saved OLX listing snapshots."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import load_historical_data, load_history_data, load_live_data, load_combined_archive
from src.styles import apply_theme
from src.ui import format_rupiah, render_empty_state

apply_theme()
st.title("Pahami pilihan yang tersedia")
st.caption("Ringkasan ini membaca iklan OLX yang tersimpan. Harga adalah harga penawaran, bukan harga transaksi.")

history, live, excel, historical = load_history_data(), load_live_data(), load_historical_data(), load_combined_archive()
if historical.empty and history.empty and live.empty:
    render_empty_state("Belum ada snapshot", "Listing akan muncul setelah tombol refresh manual digunakan. Tidak ada data contoh.")
    st.stop()

if not historical.empty:
    source = historical.copy()
    source_label = "arsip gabungan dataset Excel + snapshot OLX"
    snapshots = history["snapshot_id"].nunique() if "snapshot_id" in history else 0
elif not live.empty:
    source = live.copy()
    source_label = "snapshot live DKI Jakarta"
    snapshots = 1
else:
    source = history.copy()
    source_label = "riwayat pengamatan"
    snapshots = source["fetched_at"].nunique(dropna=True) if "fetched_at" in source else 0

for field in ["price", "year", "mileage_km", "engine_cc"]:
    if field in source:
        source[field] = pd.to_numeric(source[field], errors="coerce")
priced = source.dropna(subset=["price"]).copy() if "price" in source else pd.DataFrame()
unique_count = source["listing_id"].nunique() if "listing_id" in source else len(source)
timestamp = "Belum tercatat"
if "fetched_at" in source:
    dates = pd.to_datetime(source["fetched_at"], errors="coerce", utc=True).dropna()
    if not dates.empty:
        timestamp = dates.max().tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M WIB")

with st.container(horizontal=True):
    st.metric("Listing tersimpan", unique_count, border=True)
    st.metric("Merek tersedia", source["make"].nunique() if "make" in source else 0, border=True)
    st.metric("Jenis bahan bakar", source["fuel_type"].nunique() if "fuel_type" in source else 0, border=True)
    st.metric("Median harga iklan", format_rupiah(priced["price"].median()) if not priced.empty else "-", border=True)
st.caption(f"Sumber: {source_label} · {len(source):,} baris · listing unik {unique_count:,}".replace(",", "."))
if not historical.empty:
    origins = source.get("source_origins", pd.Series("", index=source.index)).fillna("")
    excel_count = int(origins.str.contains("Dataset Excel", regex=False).sum())
    olx_count = int(origins.str.contains("Arsip snapshot OLX", regex=False).sum())
    st.caption(f"Tercatat di Excel: {excel_count:,} listing unik · tercatat di snapshot OLX: {olx_count:,} listing unik · {snapshots:,} snapshot OLX. Hitungan sumber bisa tumpang tindih; pengulangan antar-snapshot tetap dihitung satu mobil unik.".replace(",", "."))
if not historical.empty:
    st.caption("Dataset historis digunakan untuk analisis. Listing pada file ini belum tentu masih aktif; data didominasi DKI Jakarta.")
if unique_count < 30:
    st.info("Sampel listing masih kecil. Gunakan angka dan grafik sebagai gambaran data yang terkumpul, bukan seluruh pasar DKI Jakarta.", icon=":material/info:")

st.subheader("Gambaran harga yang teramati")
if len(priced) >= 5:
    q1, median, q3 = priced["price"].quantile([.25, .5, .75])
    price_metrics = st.columns(3)
    price_metrics[0].metric("Harga terendah", format_rupiah(priced["price"].min()), border=True)
    price_metrics[1].metric("Median penawaran", format_rupiah(median), border=True)
    price_metrics[2].metric("Harga tertinggi", format_rupiah(priced["price"].max()), border=True)
    st.caption(f"Separuh listing berharga valid berada pada kisaran {format_rupiah(q1)}–{format_rupiah(q3)}. Ini ringkasan sampel yang terkumpul, bukan acuan pasti harga transaksi.")
else:
    st.info("Belum cukup harga valid untuk merangkum kisaran harga.")

st.subheader("Apa yang tersedia di snapshot ini?")
brand_col, fuel_col = st.columns(2)
with brand_col:
    with st.container(border=True):
        st.markdown("**Merek apa yang paling banyak punya pilihan?**")
        brands = source["make"].dropna().astype(str).value_counts().head(10) if "make" in source else pd.Series(dtype=int)
        if len(brands):
            brand_data = brands.rename_axis("Merek").rename("Jumlah listing").reset_index()
            fig = px.bar(brand_data, x="Jumlah listing", y="Merek", orientation="h", color_discrete_sequence=["#0b806b"])
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=12, b=10), yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, theme="streamlit", key="brand_counts")
            st.caption(f"Pilihan terbanyak di data ini: {brands.index[0]} ({brands.iloc[0]} listing). Banyak listing tidak otomatis berarti paling cocok untukmu.")
        else:
            st.caption("Informasi merek belum tersedia.")
with fuel_col:
    with st.container(border=True):
        st.markdown("**Pilihan bahan bakarnya apa saja?**")
        fuels = source["fuel_type"].dropna().astype(str).value_counts() if "fuel_type" in source else pd.Series(dtype=int)
        if len(fuels):
            fuel_data = fuels.rename_axis("Bahan bakar").rename("Jumlah listing").reset_index()
            fig = px.bar(fuel_data, x="Jumlah listing", y="Bahan bakar", orientation="h", color="Bahan bakar",
                         color_discrete_sequence=["#0b806b", "#d08c48", "#4f7894", "#8e6b9b"])
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=12, b=10), yaxis={"categoryorder": "total ascending"}, showlegend=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, theme="streamlit", key="fuel_counts")
            st.caption("Komposisi ini membantu menyaring tipe kendaraan; ketersediaan pada sampel tidak mewakili seluruh pasar.")
        else:
            st.caption("Informasi bahan bakar belum tersedia.")

st.markdown("**Mau melihat listing tertentu?**")
quick_cols = st.columns(2)
brand_options = sorted(source["make"].dropna().astype(str).unique()) if "make" in source else []
fuel_options = sorted(source["fuel_type"].dropna().astype(str).unique()) if "fuel_type" in source else []
with quick_cols[0]:
    if brand_options:
        chosen_make = st.selectbox("Pilih merek", brand_options, key="market_quick_make")
        if st.button(f"Lihat listing {chosen_make}", key="market_open_make", icon=":material/directions_car:"):
            st.session_state["prefill_make"] = chosen_make
            st.switch_page("pages/2_Find_Your_Car.py")
with quick_cols[1]:
    if fuel_options:
        chosen_fuel = st.selectbox("Pilih bahan bakar", fuel_options, key="market_quick_fuel")
        if st.button(f"Lihat mobil {chosen_fuel}", key="market_open_fuel", icon=":material/directions_car:"):
            st.session_state["prefill_fuel"] = chosen_fuel
            st.switch_page("pages/2_Find_Your_Car.py")

price_col, engine_col = st.columns(2)
with price_col:
    with st.container(border=True):
        st.markdown("**Di rentang harga mana iklan terkumpul?**")
        if len(priced) >= 5:
            fig = px.histogram(priced, x="price", nbins=min(20, max(5, len(priced) // 2)), labels={"price": "Harga penawaran (Rp)", "count": "Jumlah listing"})
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=15, b=10), showlegend=False)
            fig.update_traces(marker_color="#0b806b")
            fig.add_vline(x=priced["price"].median(), line_dash="dash", line_color="#c27a31", annotation_text="Median")
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, theme="streamlit", key="price_distribution")
            st.caption("Gunakan sebaran untuk melihat kelompok harga dan outlier. Harga listing belum tentu sama dengan harga deal.")
        else:
            st.caption("Sebaran harga baru ditampilkan setelah tersedia minimal 5 harga valid.")
with engine_col:
    with st.container(border=True):
        st.markdown("**Berapa kapasitas mesin yang ditemukan?**")
        engines = source.dropna(subset=["engine_cc"]) if "engine_cc" in source else pd.DataFrame()
        if len(engines) >= 5 and engines["engine_cc"].nunique() >= 3:
            fig = px.histogram(engines, x="engine_cc", nbins=min(15, max(5, len(engines) // 2)), labels={"engine_cc": "Kapasitas mesin (cc)", "count": "Jumlah listing"})
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=15, b=10), showlegend=False)
            fig.update_traces(marker_color="#0b806b")
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, theme="streamlit", key="engine_distribution")
            st.caption(f"CC tersedia pada {len(engines)} dari {len(source)} baris. Cocokkan kapasitas dengan kebutuhan dan biaya operasional yang kamu pertimbangkan.")
        else:
            st.caption("Grafik CC menunggu setidaknya 5 nilai valid dan 3 kapasitas berbeda.")

st.subheader("Apakah tahun atau kilometer terlihat terkait dengan harga?")
feature_options = [("year", "Tahun kendaraan"), ("mileage_km", "Kilometer"), ("engine_cc", "Kapasitas mesin (cc)")]
feature_options = [(key, label) for key, label in feature_options if key in priced and priced[key].notna().sum() >= 10 and priced[key].nunique() >= 4]
if len(priced) >= 10 and feature_options:
    feature, feature_label = st.selectbox("Bandingkan harga dengan", feature_options, format_func=lambda item: item[1])
    points = priced.dropna(subset=[feature, "price"])
    fig = px.scatter(points, x=feature, y="price", color="make" if "make" in points and points["make"].nunique() <= 8 else None,
                     hover_data=[c for c in ["make", "model", "year", "mileage_km", "engine_cc"] if c in points],
                     labels={feature: feature_label, "price": "Harga penawaran (Rp)", "make": "Merek"}, opacity=.78,
                     color_discrete_sequence=["#0b806b", "#d08c48", "#4f7894", "#8e6b9b"])
    fig.update_layout(height=370, margin=dict(l=10, r=10, t=15, b=10), legend_title_text="Merek")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, theme="streamlit", key="feature_price_scatter")
    corr = points[feature].corr(points["price"])
    st.caption(f"Ada {len(points)} listing dengan kedua nilai. Korelasi linear pada sampel ini {corr:.2f}; ini pola deskriptif, bukan bukti sebab-akibat atau penentu kondisi mobil.")
else:
    st.info("Hubungan harga dengan tahun, kilometer, atau CC belum ditampilkan karena jumlah/kualitas nilai yang berpasangan belum cukup (minimal 10 listing dan 4 nilai fitur berbeda).")

st.subheader("Perubahan data dari waktu ke waktu")
if not history.empty and "fetched_at" in history and history["fetched_at"].nunique(dropna=True) >= 2:
    h = history.copy()
    h["price"] = pd.to_numeric(h.get("price"), errors="coerce")
    h["fetched_at"] = pd.to_datetime(h["fetched_at"], errors="coerce")
    trend = h.dropna(subset=["fetched_at"]).groupby("fetched_at").agg(median_asking_price=("price", "median"), unique_listings=("listing_id", "nunique")).reset_index()
    fig = px.line(trend, x="fetched_at", y="median_asking_price", markers=True, hover_data=["unique_listings"], labels={"fetched_at": "Waktu snapshot", "median_asking_price": "Median harga penawaran (Rp)", "unique_listings": "Listing unik"})
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, theme="streamlit", key="snapshot_trend")
    st.caption("Perubahan ini hanya membandingkan snapshot live yang tersimpan, bukan tren transaksi seluruh pasar.")
else:
    st.caption("Belum ada tren waktu: perlu sedikitnya dua snapshot. Data tidak diperbarui otomatis.")

with st.expander("Tentang data dan keterbatasan"):
    st.write(f"Analisis menggunakan **{source_label}**: {len(source)} baris dan {unique_count} listing unik. Harga merupakan harga penawaran yang tercantum pada iklan. Refresh hanya dilakukan manual; jika tidak ada refresh, listing bisa sudah berubah atau tidak tersedia. Kondisi kendaraan dan keabsahan dokumen tidak diverifikasi.")
