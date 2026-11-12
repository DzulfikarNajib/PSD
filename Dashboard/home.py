"""AutoMatch home: a buyer-first entry point into saved vehicle listings."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.api_handler import safe_refresh_snapshot
from src.data_loader import (
    get_last_updated_text,
    load_combined_archive,
)
from src.supabase_store import is_configured as supabase_is_configured
from src.styles import apply_theme
from src.ui import format_rupiah, render_empty_state


DEFAULT_SEARCH_URL = "https://www.olx.co.id/mobil-bekas_c198/q-mobil"
HERO_IMAGE = (
    "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2"
    "?auto=format&fit=crop&w=1600&q=85"
)


def _compact_rupiah(value: float) -> str:
    value = float(value)
    if value >= 1_000_000_000:
        return f"Rp {value / 1_000_000_000:.1f} M".replace(".0 M", " M").replace(".", ",")
    if value >= 1_000_000:
        return f"Rp {value / 1_000_000:.0f} jt" if value % 1_000_000 == 0 else f"Rp {value / 1_000_000:.1f} jt".replace(".", ",")
    return format_rupiah(value)


apply_theme()
archive = load_combined_archive()

with st.container(key="home_hero"):
    hero_copy, hero_visual = st.columns([1.05, 1.25], gap="large", vertical_alignment="center")
    with hero_copy:
        st.caption("PANDUAN MEMILIH MOBIL BEKAS")
        st.markdown("# AutoMatch")
        st.markdown("### Find the car that fits you.")
        st.write("Cari dan bandingkan mobil bekas berdasarkan kebutuhan serta anggaranmu. Pahami harga iklannya, lalu periksa langsung sebelum memutuskan.")
        if st.button("Mulai cari mobil", icon=":material/search:", type="primary", key="home_start_search"):
            st.switch_page("pages/2_Find_Your_Car.py")
        st.caption("Cari dari arsip tersimpan; pembaruan listing hanya saat refresh manual.")
    with hero_visual:
        st.image(
            HERO_IMAGE,
            caption="Ilustrasi · bukan listing jual AutoMatch",
            alt="Sedan kota berwarna pucat di lingkungan perkotaan, sebagai ilustrasi AutoMatch",
            width="stretch",
        )

st.markdown("## Pilihan di arsip AutoMatch")
if archive.empty:
    empty_metrics = st.columns(4)
    for col, label in zip(empty_metrics, ["Mobil unik", "Jumlah merek", "Median harga iklan", "Snapshot OLX terbaru"]):
        col.metric(label, "—", border=True)
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
    metric_cols[0].metric("🚘 Mobil unik", f"{unique_count:,}".replace(",", "."), border=True)
    metric_cols[1].metric("✦ Jumlah merek", f"{brands.nunique():,}".replace(",", "."), border=True)
    metric_cols[2].metric("◉ Median harga iklan", _compact_rupiah(prices.median()) if not prices.empty else "—", border=True)
    metric_cols[3].metric("◷ Snapshot OLX terbaru", last_update.split(",")[0] if not timestamps.empty else "—", border=True)
    if not prices.empty:
        median_price = prices.median()
        st.caption(f"Rentang harga iklan tersimpan: {_compact_rupiah(prices.min())} – {_compact_rupiah(prices.max())} · Median: {_compact_rupiah(median_price)}.")
    st.caption(
        f"Sumber: arsip Excel + snapshot OLX tersimpan · waktu snapshot OLX terbaru: {last_update}. "
        "Arsip penuh menghitung satu listing unik; iklan historis belum tentu masih aktif dan sampel bukan seluruh pasar."
    )

    st.markdown("### Apa yang tersedia untuk dicari?")
    brand_col, fuel_col = st.columns([1.2, 1], gap="large")
    with brand_col:
        with st.container(border=True):
            st.markdown("**Merek apa yang paling banyak punya pilihan?**")
            brand_counts = brands[brands.ne("")].value_counts().head(8)
            if not brand_counts.empty:
                plot_data = brand_counts.rename_axis("Merek").rename("Listing unik").reset_index()
                chart = px.bar(plot_data, x="Merek", y="Listing unik", text="Listing unik", color_discrete_sequence=["#19a7ad"])
                chart.update_layout(height=300, margin=dict(l=4, r=8, t=10, b=5), xaxis_title=None, yaxis_title=None, yaxis=dict(gridcolor="#e5eaed"), xaxis=dict(tickangle=-18))
                chart.update_traces(textposition="outside", cliponaxis=False, marker_line_width=0)
                st.plotly_chart(chart, width="stretch", config={"displayModeBar": False}, theme="streamlit", key="home_brands")
                st.caption(f"{brand_counts.index[0]} paling sering muncul di arsip ini ({brand_counts.iloc[0]} listing unik). Ini menunjukkan jumlah pilihan yang tersimpan, bukan rekomendasi kualitas.")
                popular = [make for make in ["BMW", "Toyota", "Honda", "Daihatsu", "Suzuki", "Mercedes-Benz"] if make.casefold() in {v.casefold() for v in brands.unique()}]
                if popular:
                    st.caption("Cari langsung berdasarkan merek yang tersedia:")
                    shortcut_cols = st.columns(min(len(popular), 3))
                    for idx, make in enumerate(popular):
                        with shortcut_cols[idx % len(shortcut_cols)]:
                            if st.button(make, key=f"home_brand_{idx}", use_container_width=True):
                                st.session_state["prefill_make"] = make
                                st.session_state["car_source_choice"] = "Arsip Penuh"
                                st.switch_page("pages/2_Find_Your_Car.py")
                choices = sorted(brands[brands.ne("")].unique())
                if choices:
                    other_brand = st.selectbox("Atau pilih merek lain", choices, key="home_brand_choice")
                    if st.button(f"Lihat {other_brand}", icon=":material/search:", key="home_find_brand"):
                        st.session_state["prefill_make"] = other_brand
                        st.session_state["car_source_choice"] = "Arsip Penuh"
                        st.switch_page("pages/2_Find_Your_Car.py")
            else:
                st.caption("Informasi merek belum tersedia di arsip ini.")
    with fuel_col:
        with st.container(border=True):
            st.markdown("**Jumlah listing berdasarkan bahan bakar**")
            if not fuels.empty:
                fuel_data = fuels.rename_axis("Bahan bakar").rename("Listing unik").reset_index()
                chart = px.pie(fuel_data, values="Listing unik", names="Bahan bakar", hole=.68, color_discrete_sequence=["#102748", "#109fa4", "#67c7c8", "#e4b76d", "#99a9b7"])
                chart.update_layout(height=300, margin=dict(l=0, r=0, t=4, b=0), legend=dict(orientation="v", x=1.0, y=.5), showlegend=True, annotations=[dict(text=f"{int(fuels.sum()):,}".replace(",", "."), x=.43, y=.5, font_size=20, showarrow=False)])
                chart.update_traces(textinfo="none", marker=dict(line=dict(color="white", width=3)))
                st.plotly_chart(chart, width="stretch", config={"displayModeBar": False}, theme="streamlit", key="home_fuels")
                st.caption("Jumlah listing per kategori bahan bakar pada arsip. Ketersediaan tidak menggambarkan seluruh pasar.")
                fuel_choices = sorted(fuels.index.astype(str))
                selected_fuel = st.selectbox("Pilih bahan bakar untuk dicari", fuel_choices, key="home_fuel_choice")
                if st.button(f"Lihat mobil {selected_fuel}", icon=":material/search:", key="home_find_fuel"):
                    st.session_state["prefill_fuel"] = selected_fuel
                    st.session_state["car_source_choice"] = "Arsip Penuh"
                    st.switch_page("pages/2_Find_Your_Car.py")
            else:
                st.caption("Data bahan bakar belum tersedia di arsip ini.")

st.markdown("### Mulai dari kebutuhanmu")
steps = st.columns(3, gap="medium")
steps[0].markdown("**01 · Cari**\n\nAtur budget dan spesifikasi di Cari Mobil.")
steps[1].markdown("**02 · Bandingkan**\n\nPilih dua atau tiga listing yang sesuai.")
steps[2].markdown("**03 · Periksa langsung**\n\nBuka iklan sumber dan verifikasi kondisi serta dokumennya.")

with st.expander("Perbarui listing OLX (manual)", expanded=st.session_state.pop("open_refresh_panel", False)):
    st.caption("Refresh memakai kredit API bersama. Hanya tombol di bawah yang mengirim permintaan; pencarian arsip tetap dapat digunakan tanpa refresh.")
    with st.form("refresh_listings_form"):
        search_url = st.text_input("URL pencarian OLX", value=DEFAULT_SEARCH_URL, key="refresh_search_url_jabodetabek_v1")
        max_pages = st.slider("Jumlah halaman (menggunakan kredit API)", min_value=1, max_value=5, value=1, step=1)
        refresh = st.form_submit_button("Refresh Listings", type="primary")
    st.caption("Aplikasi menyimpan listing yang lokasinya dapat dikenali sebagai lima wilayah DKI Jakarta. Hasil API bukan seluruh stok Jakarta. Snapshot baru ditambahkan ke arsip; kredit digunakan sesuai halaman yang berhasil diambil.")
    if refresh:
        try:
            with st.spinner("Mengambil snapshot dari Datawebot…"):
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
        st.write(f"Status: **{last_refresh.get('status', 'unknown')}** · Mentah: **{last_refresh.get('raw_count', '—')}** · Valid: **{last_refresh.get('validated_count', '—')}** · Tersimpan setelah filter DKI: **{last_refresh.get('filtered_count', 0)}**")
        if last_refresh.get("quality"):
            st.caption("Data invalid/kosong: " + " · ".join(f"{key.replace('_', ' ')}: {value}" for key, value in last_refresh["quality"].items()))
        st.caption(f"Kredit digunakan: {last_refresh.get('used_credits', '—')} · Sisa kredit: {last_refresh.get('remaining_credits', '—')} · Penyimpanan: {last_refresh.get('storage_backend', 'CSV lokal')}")
        st.caption(last_refresh.get("message", ""))
