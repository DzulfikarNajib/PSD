"""AutoMatch home: a buyer-first entry point into saved vehicle listings."""

from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.api_handler import safe_refresh_snapshot
from src.data_loader import (
    load_combined_archive,
)
from src.styles import apply_theme
from src.ui import format_rupiah, format_timestamp_wib, render_data_source_status, render_empty_state


DEFAULT_SEARCH_URL = "https://www.olx.co.id/mobil-bekas_c198/q-mobil"
HERO_IMAGE_DATA = base64.b64encode((Path(__file__).parent / "assets" / "hero-bmw.jpg").read_bytes()).decode("ascii")


def _compact_rupiah(value: float) -> str:
    value = float(value)
    if value >= 1_000_000_000:
        return f"Rp {value / 1_000_000_000:.1f} M".replace(".0 M", " M").replace(".", ",")
    if value >= 1_000_000:
        return f"Rp {value / 1_000_000:.0f} Jt" if value % 1_000_000 == 0 else f"Rp {value / 1_000_000:.1f} Jt".replace(".", ",")
    return format_rupiah(value)


apply_theme()
archive = load_combined_archive()
preprocessing_audit = archive.attrs.get("preprocessing_audit", {})

st.markdown(
    f'<style>div[class*="st-key-home_hero"] {{ --automatch-hero-image: url("data:image/jpeg;base64,{HERO_IMAGE_DATA}"); }}</style>',
    unsafe_allow_html=True,
)

with st.container(key="home_hero"):
    st.caption("PANDUAN MEMILIH MOBIL BEKAS")
    st.markdown("# AutoMatch")
    st.markdown("### Temukan mobil yang sesuai kebutuhanmu.")
    st.write("Saring pilihan menurut anggaran dan spesifikasi, bandingkan harga penawaran, lalu periksa kondisi mobil sebelum memutuskan.")
    if st.button("Mulai cari mobil", icon=":material/search:", type="primary", key="home_start_search"):
        st.switch_page("pages/2_Find_Your_Car.py")
    st.caption("Data berasal dari arsip tersimpan. Listing OLX hanya diperbarui saat kamu menjalankan refresh manual.")

st.markdown("## Ringkasan arsip mobil")
render_data_source_status()
if archive.empty:
    empty_metrics = st.columns(4)
    empty_metrics[0].metric("Sumber data", "OLX · DKI Jakarta", border=True)
    empty_metrics[1].metric("Listing bersih", "-", border=True)
    empty_metrics[2].metric("Rentang tahun", "-", border=True)
    empty_metrics[3].metric("Pembaruan terakhir", "-", border=True)
    render_empty_state(
        "Arsip mobil belum tersedia",
        "Dataset OLX atau snapshot yang tersimpan akan tampil di sini. AutoMatch tidak membuat data contoh.",
    )
else:
    archive = archive.copy()
    for column in ("price", "year"):
        if column in archive:
            archive[column] = pd.to_numeric(archive[column], errors="coerce")
    unique_count = archive["listing_id"].nunique() if "listing_id" in archive else len(archive)
    brands = archive["make"].dropna().astype(str).str.strip() if "make" in archive else pd.Series(dtype=str)
    prices = archive.loc[archive["price"].gt(0), "price"] if "price" in archive else pd.Series(dtype=float)
    fuels = archive["fuel_type"].fillna("Tidak dicantumkan").astype(str).str.strip() if "fuel_type" in archive else pd.Series(dtype=str)
    fuels = fuels.replace("", "Tidak dicantumkan").value_counts()
    metric_cols = st.columns(4)
    clean_count = int(preprocessing_audit.get("clean_rows", unique_count))
    year_min, year_max = preprocessing_audit.get("year_min"), preprocessing_audit.get("year_max")
    year_range = f"{year_min}-{year_max}" if year_min is not None and year_max is not None else "-"
    latest_value = preprocessing_audit.get("latest_fetched_at")
    last_update = format_timestamp_wib(latest_value)
    metric_cols[0].metric("Sumber data", "OLX · DKI Jakarta", border=True)
    metric_cols[1].metric("Total listing bersih", f"{clean_count:,}".replace(",", "."), border=True)
    metric_cols[2].metric("Rentang tahun produksi", year_range, border=True)
    metric_cols[3].metric("Pembaruan terakhir", last_update, border=True)
    st.caption("Sumber: OLX Indonesia, DKI Jakarta. Jumlah listing berasal dari data yang sudah diproses; harga adalah harga penawaran dan iklan arsip belum tentu masih aktif.")

    st.markdown("### Mulai dari pilihan yang tersedia")
    st.caption("Beranda merangkum arsip. Buka Pahami Pasar untuk melihat distribusi dan perbandingan grafik secara lebih rinci.")
    brand_col, fuel_col = st.columns(2, gap="large")
    with brand_col:
        with st.container(border=True):
            st.markdown("#### Jelajahi berdasarkan merek")
            brand_counts = brands[brands.ne("")].value_counts()
            if not brand_counts.empty:
                top_brands = brand_counts.head(6).sort_values()
                brand_fig = px.bar(
                    x=top_brands.values,
                    y=top_brands.index,
                    orientation="h",
                    labels={"x": "Listing unik", "y": "Merek"},
                    color_discrete_sequence=["#008B8B"],
                )
                brand_fig.update_layout(height=250, margin=dict(l=8, r=8, t=8, b=8), showlegend=False, xaxis_title=None, yaxis_title=None)
                st.plotly_chart(brand_fig, width="stretch", config={"displayModeBar": False}, key="home_top_brands")
                lead_make = str(brand_counts.index[0])
                lead_count = int(brand_counts.iloc[0])
                st.metric("Merek dengan listing terbanyak", lead_make, border=True)
                st.caption(f"{lead_count:,} listing unik dalam arsip. Jumlah listing menunjukkan ketersediaan data, bukan kualitas atau rekomendasi mobil.".replace(",", "."))
                popular = [make for make in ["BMW", "Toyota", "Honda", "Daihatsu", "Suzuki", "Mercedes-Benz"] if make.casefold() in {v.casefold() for v in brands.unique()}]
                if popular:
                    st.markdown("**Merek populer**")
                    shortcut_cols = st.columns(min(len(popular), 3), gap="small")
                    for idx, make in enumerate(popular):
                        with shortcut_cols[idx % len(shortcut_cols)]:
                            if st.button(make, key=f"home_brand_{idx}", width="stretch"):
                                st.session_state["prefill_make"] = make
                                st.session_state["car_source_choice"] = "Arsip Penuh"
                                st.switch_page("pages/2_Find_Your_Car.py")
                choices = sorted(brands[brands.ne("")].unique(), key=str.casefold)
                if choices:
                    other_brand = st.selectbox("Pilih merek lain", choices, key="home_brand_choice")
                    if st.button(f"Lihat {other_brand}", icon=":material/search:", key="home_find_brand"):
                        st.session_state["prefill_make"] = other_brand
                        st.session_state["car_source_choice"] = "Arsip Penuh"
                        st.switch_page("pages/2_Find_Your_Car.py")
            else:
                st.caption("Informasi merek belum tersedia di arsip ini.")
    with fuel_col:
        with st.container(border=True):
            st.markdown("#### Jelajahi berdasarkan bahan bakar")
            if not fuels.empty:
                fuel_fig = px.pie(
                    names=fuels.head(6).index,
                    values=fuels.head(6).values,
                    hole=.56,
                    color_discrete_sequence=["#008B8B", "#0F766E", "#0369A1", "#F59E0B", "#10B981", "#64748B"],
                )
                fuel_fig.update_traces(textinfo="percent", hovertemplate="%{label}: %{value} listing (%{percent})<extra></extra>")
                fuel_fig.update_layout(height=250, margin=dict(l=8, r=8, t=8, b=8), legend=dict(orientation="h", y=-.08))
                st.plotly_chart(fuel_fig, width="stretch", config={"displayModeBar": False}, key="home_fuel_mix")
                dominant_fuel = str(fuels.index[0])
                dominant_count = int(fuels.iloc[0])
                st.metric("Bahan bakar paling sering dicatat", dominant_fuel, border=True)
                st.caption(f"{dominant_count:,} listing unik memiliki kategori bahan bakar ini. Ketersediaan hanya menggambarkan arsip tersimpan.".replace(",", "."))
                fuel_choices = sorted(fuels.items(), key=lambda item: str(item[0]).casefold())
                fuel_choice = st.selectbox("Pilih bahan bakar", [str(fuel) for fuel, _ in fuel_choices], key="home_fuel_choice")
                fuel_count = int(fuels.get(fuel_choice, 0))
                st.caption(f"{fuel_count:,} mobil unik tercatat dalam kategori ini.".replace(",", "."))
                if st.button("Lihat listing", icon=":material/search:", key="home_find_fuel"):
                    st.session_state["prefill_fuel"] = fuel_choice
                    st.session_state["car_source_choice"] = "Arsip Penuh"
                    st.switch_page("pages/2_Find_Your_Car.py")
            else:
                st.caption("Data bahan bakar belum tersedia di arsip ini.")

with st.expander("Perbarui listing OLX (manual)", expanded=st.session_state.pop("open_refresh_panel", False)):
    st.caption("Refresh mengirim permintaan ke OLX melalui API dan memakai kredit bersama. Arsip yang tersimpan tetap bisa dicari tanpa refresh.")
    with st.form("refresh_listings_form"):
        search_url = st.text_input("URL pencarian OLX", value=DEFAULT_SEARCH_URL, key="refresh_search_url_jabodetabek_v1")
        max_pages = st.slider("Jumlah halaman (menggunakan kredit API)", min_value=1, max_value=5, value=1, step=1)
        refresh = st.form_submit_button("Refresh Listings", type="primary")
    st.caption("Hanya listing yang lokasinya dapat dikenali di lima wilayah DKI Jakarta yang disimpan. Hasil API bukan seluruh stok Jakarta. Refresh menambahkan snapshot baru ke arsip.")
    if refresh:
        try:
            with st.spinner("Mengambil snapshot dari Datawebot..."):
                result = safe_refresh_snapshot(search_url, max_pages=max_pages)
            st.session_state["last_refresh"] = result
            if result["status"] == "success":
                st.success(result["message"])
            else:
                st.warning(result["message"])
        except Exception as exc:  # UI boundary
            st.session_state["last_refresh"] = {"status": "error", "message": str(exc), "live_count": 0, "filtered_count": 0, "last_successful_fetch": None, "used_credits": None, "remaining_credits": None}
            st.error(f"Refresh gagal: {exc}")

last_refresh = st.session_state.get("last_refresh")
if last_refresh:
    with st.expander("Detail refresh terakhir"):
        st.write(f"Status: **{last_refresh.get('status', 'unknown')}** · Mentah: **{last_refresh.get('raw_count', '-')}** · Valid: **{last_refresh.get('validated_count', '-')}** · Tersimpan setelah filter DKI: **{last_refresh.get('filtered_count', 0)}**")
        if last_refresh.get("quality"):
            st.caption("Data invalid/kosong: " + " · ".join(f"{key.replace('_', ' ')}: {value}" for key, value in last_refresh["quality"].items()))
        st.caption(f"Kredit digunakan: {last_refresh.get('used_credits', '-')} · Sisa kredit: {last_refresh.get('remaining_credits', '-')} · Penyimpanan: {last_refresh.get('storage_backend', 'CSV lokal')}")
        st.caption(last_refresh.get("message", ""))
