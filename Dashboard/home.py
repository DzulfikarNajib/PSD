"""Buyer-oriented home page and manual OLX snapshot controls."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.api_handler import safe_refresh_snapshot
from src.data_loader import get_last_updated_text, load_live_data
from src.styles import apply_theme
from src.ui import format_rupiah

DEFAULT_SEARCH_URL = "https://www.olx.co.id/mobil-bekas_c198/q-mobil"


def format_rupiah_compact(value: float) -> str:
    """Short display format for KPI cards with limited horizontal space."""
    value = float(value)
    if value >= 1_000_000_000:
        number = value / 1_000_000_000
        return f"Rp{number:.1f} M".replace(".0 M", " M").replace(".", ",")
    if value >= 1_000_000:
        number = value / 1_000_000
        return f"Rp{number:.0f} jt" if number.is_integer() else f"Rp{number:.1f} jt".replace(".", ",")
    return format_rupiah(value)

apply_theme()

hero_left, hero_right = st.columns([1.55, 1], vertical_alignment="center")
with hero_left:
    st.caption("AUTOMATCH · USED CAR SEARCH & COMPARISON")
    st.markdown("# AutoMatch")
    st.subheader("Find the car that fits you.")
    st.write("Cari dan bandingkan mobil bekas berdasarkan kebutuhan serta anggaranmu. Pahami harga iklannya, lalu periksa langsung sebelum memutuskan.")
    if st.button("Mulai cari mobil", icon=":material/directions_car:", type="primary"):
        st.switch_page("pages/2_Find_Your_Car.py")
    st.page_link("pages/1_Explore_Market.py", label="Pahami pasar", icon=":material/insights:")
with hero_right:
    st.markdown(
        """
        <div class="card">
            <h4>Gunakan listing sebagai titik awal</h4>
            <p>Temukan pilihan, bandingkan harga iklan dengan mobil serupa, lalu periksa langsung sebelum membeli.</p>
            <ul>
                <li>Harga iklan bukan harga transaksi.</li>
                <li>Kondisi dan dokumen tidak diverifikasi dashboard.</li>
                <li>Listing dapat berubah sejak snapshot diambil.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

live = load_live_data()
st.markdown("---")
st.subheader("Pilihan yang tersimpan")
st.caption("Pencarian memakai snapshot ini dan tetap bisa digunakan saat kredit API habis. Data baru hanya diambil saat refresh manual.")

if live.empty:
    st.info("Belum ada listing tersimpan. Refresh manual dapat mengambil snapshot pertama.")
else:
    live = live.copy()
    for col in ["price", "year"]:
        if col in live:
            live[col] = pd.to_numeric(live[col], errors="coerce")
    listing_count = live["listing_id"].nunique() if "listing_id" in live else len(live)
    priced = live[live["price"].gt(0)] if "price" in live else pd.DataFrame()
    price_range = f"{format_rupiah_compact(priced['price'].min())} – {format_rupiah_compact(priced['price'].max())}" if not priced.empty else "Belum tersedia"
    metric_cols = st.columns(4)
    metric_cols[0].metric("Listing tersedia", listing_count, border=True)
    metric_cols[1].metric("Merek", live["make"].nunique(dropna=True) if "make" in live else 0, border=True)
    metric_cols[2].metric("Rentang harga iklan", price_range, border=True)
    metric_cols[3].metric("Median harga iklan", format_rupiah(priced["price"].median()) if not priced.empty else "-", border=True)
    st.caption(f"Terakhir diperbarui: {get_last_updated_text()} · Sumber: snapshot listing OLX tersimpan")

    st.markdown("**Listing menurut bahan bakar**")
    fuels = live["fuel_type"].fillna("Tidak dicantumkan").astype(str).replace("", "Tidak dicantumkan").value_counts() if "fuel_type" in live else pd.Series(dtype=int)
    if len(fuels):
        fuel_cols = st.columns(min(max(len(fuels), 1), 4))
        for idx, (fuel, count) in enumerate(fuels.items()):
            with fuel_cols[idx % len(fuel_cols)]:
                st.metric(str(fuel), int(count), border=True)
    else:
        st.caption("Informasi bahan bakar belum tersedia pada snapshot ini.")
    st.caption("Jumlah menunjukkan listing DKI Jakarta pada snapshot, bukan seluruh pasar.")

st.markdown("---")
st.subheader("Alur singkat")
step_cols = st.columns(3)
step_cols[0].markdown("**1 · Cari**\n\nAtur anggaran dan spesifikasi mobil.")
step_cols[1].markdown("**2 · Bandingkan**\n\nPilih dua atau tiga iklan dan cek harga pembanding.")
step_cols[2].markdown("**3 · Periksa**\n\nBuka iklan sumber, cek mobil dan dokumen langsung.")

with st.expander("Perbarui listing dari OLX (manual)"):
    with st.form("refresh_listings_form"):
        search_url = st.text_input("URL pencarian OLX", value=DEFAULT_SEARCH_URL, key="refresh_search_url_jabodetabek_v1")
        max_pages = st.slider("Jumlah halaman (menggunakan kredit API)", min_value=1, max_value=5, value=1, step=1)
        refresh = st.form_submit_button("Refresh Listings", type="primary")
    st.caption("Datawebot meminta pola URL pencarian umum; API mengambil hasil yang didukung endpoint, lalu aplikasi hanya menyimpan lima wilayah administratif DKI Jakarta. Hasilnya bukan seluruh listing DKI. Maksimal 5 halaman per request dan memakai kredit bersama. Refresh tetap manual dan mengganti snapshot terbaru.")
    if refresh:
        try:
            with st.spinner("Mengambil snapshot dari Datawebot…"):
                result = safe_refresh_snapshot(search_url, max_pages=max_pages)
            st.session_state["last_refresh"] = result
            if result["status"] == "success":
                st.success(result["message"])
            else:
                st.warning(result["message"])
        except Exception as exc:  # pragma: no cover - UI-level error handling
            st.session_state["last_refresh"] = {
                "status": "error", "message": str(exc), "live_count": 0,
                "filtered_count": 0, "last_successful_fetch": None,
                "used_credits": None, "remaining_credits": None,
            }
            st.error(f"Refresh gagal: {exc}")

last_refresh = st.session_state.get("last_refresh")
if last_refresh:
    with st.expander("Detail refresh terakhir"):
        st.write(f"Status: **{last_refresh.get('status', 'unknown')}** · Data mentah: **{last_refresh.get('raw_count', '—')}** · Valid: **{last_refresh.get('validated_count', '—')}** · Tersimpan setelah filter DKI: **{last_refresh.get('filtered_count', 0)}**")
        if last_refresh.get("quality"):
            st.caption("Data invalid/kosong: " + " · ".join(f"{key.replace('_', ' ')}: {value}" for key, value in last_refresh["quality"].items()))
        st.caption(f"Kredit digunakan: {last_refresh.get('used_credits', '—')} · Sisa kredit: {last_refresh.get('remaining_credits', '—')}")
        st.caption(last_refresh.get("message", ""))
