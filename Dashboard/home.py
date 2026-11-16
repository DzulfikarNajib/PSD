"""AutoMatch home: a buyer-first entry point into saved vehicle listings."""

from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from src.api_handler import safe_refresh_snapshot
from src.data_loader import (
    get_last_updated_text,
    load_combined_archive,
)
from src.styles import apply_theme
from src.ui import format_rupiah, render_empty_state


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
if archive.empty:
    empty_metrics = st.columns(4)
    for col, label in zip(empty_metrics, ["Mobil unik", "Jumlah merek", "Median harga iklan", "Snapshot OLX terbaru"]):
        col.metric(label, "-", border=True)
    render_empty_state(
        "Arsip mobil belum tersedia",
        "Dataset Excel atau snapshot OLX yang tersimpan akan tampil di sini. AutoMatch tidak membuat data contoh.",
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
    timestamps = pd.to_datetime(archive.get("fetched_at"), errors="coerce", utc=True).dropna() if "fetched_at" in archive else pd.Series(dtype="datetime64[ns, UTC]")
    last_update = get_last_updated_text() if not timestamps.empty else "Belum ada snapshot OLX"

    metric_cols = st.columns(4)
    metric_cols[0].metric("Mobil unik", f"{unique_count:,}".replace(",", "."), border=True)
    metric_cols[1].metric("Merek tersedia", f"{brands.nunique():,}".replace(",", "."), border=True)
    metric_cols[2].metric("Median harga iklan", _compact_rupiah(prices.median()) if not prices.empty else "-", border=True)
    metric_cols[3].metric("Snapshot OLX terbaru", last_update.split(",")[0] if not timestamps.empty else "-", border=True)
    if not prices.empty:
        median_price = prices.median()
        st.caption(f"Rentang harga iklan tersimpan: {_compact_rupiah(prices.min())} s/d {_compact_rupiah(prices.max())} · Median: {_compact_rupiah(median_price)}.")
    st.caption(f"Sumber: Excel dan snapshot OLX tersimpan. Snapshot OLX terbaru: {last_update}. Harga adalah harga penawaran; iklan arsip belum tentu masih aktif dan data tidak mewakili seluruh pasar.")

    st.markdown("### Mulai dari pilihan yang tersedia")
    st.caption("Beranda merangkum arsip. Buka Pahami Pasar untuk melihat distribusi dan perbandingan grafik secara lebih rinci.")
    brand_col, fuel_col = st.columns(2, gap="large")
    with brand_col:
        with st.container(border=True):
            st.markdown("#### Jelajahi berdasarkan merek")
            brand_counts = brands[brands.ne("")].value_counts()
            if not brand_counts.empty:
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
                            if st.button(make, key=f"home_brand_{idx}", use_container_width=True):
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
