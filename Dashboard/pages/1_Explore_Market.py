"""Buyer-oriented insights from saved listing data; never calls the paid API."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_history_data, load_live_data, load_combined_archive
from src.styles import apply_theme
from src.ui import format_rupiah, render_empty_state


apply_theme()
st.title("Pahami Pasar")
st.caption("Baca pilihan dan kisaran harga yang benar-benar tercatat di AutoMatch.")
st.info("Harga adalah harga penawaran. Grafik merangkum data yang terkumpul, bukan seluruh pasar atau harga transaksi.", icon=":material/info:")

history, live, archive = load_history_data(), load_live_data(), load_combined_archive()
if archive.empty and history.empty and live.empty:
    render_empty_state("Belum ada data untuk dianalisis", "Arsip dan snapshot akan tampil setelah dataset tersedia atau refresh manual berhasil. Tidak ada data contoh.")
    st.stop()

source_choice = st.radio(
    "Pilih data yang ingin dilihat",
    ["Arsip Penuh", "Listing Terbaru"],
    horizontal=True,
    key="market_source_choice",
    help="Arsip penuh memuat Excel dan snapshot OLX tersimpan. Listing terbaru hanya snapshot OLX paling baru.",
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

for field in ["price", "year", "mileage_km", "engine_cc"]:
    if field in source:
        source[field] = pd.to_numeric(source[field], errors="coerce")
priced = source.dropna(subset=["price"]).copy() if "price" in source else pd.DataFrame()
unique_count = source["listing_id"].nunique() if "listing_id" in source else len(source)
make_count = source["make"].nunique() if "make" in source else 0

if source_choice == "Listing Terbaru" and "fetched_at" in source:
    dates = pd.to_datetime(source["fetched_at"], errors="coerce", utc=True).dropna()
    updated = dates.max().tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M WIB") if not dates.empty else "Waktu tidak tercatat"
else:
    updated = "Tidak tersedia untuk semua arsip"

st.markdown("### Ringkasan pilihan")
kpis = st.columns(4, gap="small")
kpis[0].metric("Mobil unik", f"{unique_count:,}".replace(",", "."), border=True)
kpis[1].metric("Snapshot OLX", f"{snapshot_count:,}".replace(",", "."), border=True)
kpis[2].metric("Merek", f"{make_count:,}".replace(",", "."), border=True)
kpis[3].metric("Median harga iklan", format_rupiah(priced["price"].median()) if len(priced) else "—", border=True)
st.caption(f"Sumber: **{source_label}** · {len(source):,} baris tampilan · {unique_count:,} mobil unik".replace(",", "."))
if source_choice == "Arsip Penuh":
    origins = source.get("source_origins", pd.Series("", index=source.index)).fillna("")
    excel_count = int(origins.str.contains("Dataset Excel", regex=False).sum())
    olx_count = int(origins.str.contains("Arsip snapshot OLX", regex=False).sum())
    st.caption(f"{excel_count:,} mobil tercatat di dataset Excel · {olx_count:,} juga pernah muncul di snapshot OLX · angka sumber bisa tumpang tindih.".replace(",", "."))
    st.warning("Arsip mencakup iklan Excel dan snapshot lama. Iklan atau tautan arsip belum tentu masih aktif.", icon=":material/history:")
else:
    st.caption(f"Snapshot terakhir: {updated} · iklan terlihat saat diambil, tetapi bisa berubah atau sudah tidak aktif.")
if unique_count < 30:
    st.info("Sampelnya masih kecil. Baca angka sebagai data yang terkumpul, bukan perkiraan seluruh pasar.", icon=":material/info:")

with st.container(border=True):
    st.markdown("### Temuan singkat")
    top_make = source["make"].dropna().astype(str).value_counts() if "make" in source else pd.Series(dtype=int)
    top_fuel = source["fuel_type"].dropna().astype(str).value_counts() if "fuel_type" in source else pd.Series(dtype=int)
    insight_cols = st.columns(3)
    insight_cols[0].markdown(f"**Merek dengan listing terbanyak**\n\n{top_make.index[0] if len(top_make) else 'Belum tersedia'}" + (f" · {top_make.iloc[0]} mobil" if len(top_make) else ""))
    insight_cols[1].markdown(f"**Bahan bakar yang paling sering tercatat**\n\n{top_fuel.index[0] if len(top_fuel) else 'Belum tersedia'}" + (f" · {top_fuel.iloc[0]} mobil" if len(top_fuel) else ""))
    insight_cols[2].markdown(f"**Median harga penawaran**\n\n{format_rupiah(priced['price'].median()) if len(priced) else 'Belum tersedia'}")

TEAL = "#109FA4"
NAVY = "#102748"
MUTED = "#718096"
PALETTE = [TEAL, "#345B86", "#D9A441", "#7C6AA6", "#6C9B76", "#C87562"]


def finish_chart(fig, height=320):
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=16, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=NAVY, size=12),
        xaxis=dict(gridcolor="#E8EEF0", zerolinecolor="#E8EEF0"),
        yaxis=dict(gridcolor="#E8EEF0", zerolinecolor="#E8EEF0"),
        legend=dict(font=dict(color=NAVY)),
    )
    return fig


st.markdown("### Pilihan mobil seperti apa yang tersedia?")
brand_col, fuel_col = st.columns([1.2, .8], gap="medium")
with brand_col:
    with st.container(border=True):
        st.markdown("**Merek apa yang paling banyak punya pilihan?**")
        brands = source["make"].dropna().astype(str).value_counts().head(8) if "make" in source else pd.Series(dtype=int)
        if len(brands):
            brand_data = brands.rename_axis("Merek").rename("Jumlah mobil").reset_index()
            fig = px.bar(brand_data, x="Merek", y="Jumlah mobil", color_discrete_sequence=[TEAL], text="Jumlah mobil")
            fig.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=7)
            fig.update_xaxes(tickangle=-25, title=None, showgrid=False)
            fig.update_yaxes(title=None)
            st.plotly_chart(finish_chart(fig, 330), width="stretch", config={"displayModeBar": False}, key="market_brand_chart")
            st.caption(f"Di {source_label.lower()}, {brands.index[0]} paling sering muncul ({brands.iloc[0]} mobil unik). Banyaknya pilihan tidak otomatis berarti paling cocok.")
            link_cols = st.columns(min(4, len(brands)))
            for index, brand in enumerate(brands.index[:4]):
                with link_cols[index]:
                    if st.button(f"Lihat {brand}", key=f"market_brand_link_{index}", use_container_width=True):
                        st.session_state["prefill_make"] = brand
                        st.session_state["car_source_choice"] = source_choice
                        st.switch_page("pages/2_Find_Your_Car.py")
        else:
            st.caption("Informasi merek belum tersedia pada sumber ini.")
with fuel_col:
    with st.container(border=True):
        st.markdown("**Bahan bakar apa yang tersedia?**")
        fuels = source["fuel_type"].fillna("").astype(str).replace("", "Tidak dicantumkan").value_counts() if "fuel_type" in source else pd.Series(dtype=int)
        if len(fuels):
            fuel_data = fuels.rename_axis("Bahan bakar").rename("Jumlah mobil").reset_index()
            fig = px.pie(fuel_data, names="Bahan bakar", values="Jumlah mobil", hole=.66, color_discrete_sequence=PALETTE)
            fig.update_traces(textposition="inside", textinfo="percent", sort=False, marker=dict(line=dict(color="#FFFFFF", width=3)))
            fig.add_annotation(text=f"{unique_count:,}<br><span style='font-size:11px'>mobil unik</span>".replace(",", "."), x=.5, y=.5, showarrow=False, font=dict(size=18, color=NAVY))
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-.08, x=0, font=dict(size=11)))
            st.plotly_chart(finish_chart(fig, 330), width="stretch", config={"displayModeBar": False}, key="market_fuel_donut")
            st.caption("Bagian tiap warna adalah jumlah mobil pada sumber pilihan. Jenis bahan bakar yang tidak dicantumkan tetap dihitung terpisah.")
            fuel_options = [fuel for fuel in fuels.index if fuel != "Tidak dicantumkan"]
            if fuel_options:
                selected_fuel = st.selectbox("Lihat pilihan bahan bakar", fuel_options, key="market_fuel_shortcut")
                if st.button(f"Cari mobil {selected_fuel}", key="market_fuel_link", use_container_width=True):
                    st.session_state["prefill_fuel"] = selected_fuel
                    st.session_state["car_source_choice"] = source_choice
                    st.switch_page("pages/2_Find_Your_Car.py")
        else:
            st.caption("Informasi bahan bakar belum tersedia pada sumber ini.")

st.markdown("### Harga dan spesifikasi yang tercatat")
price_col, engine_col = st.columns(2, gap="medium")
with price_col:
    with st.container(border=True):
        st.markdown("**Di rentang berapa harga iklan terkumpul?**")
        if len(priced) >= 5:
            fig = px.histogram(priced, x="price", nbins=min(22, max(6, len(priced) // 3)), labels={"price": "Harga penawaran (Rp)", "count": "Jumlah mobil"})
            fig.update_traces(marker_color=TEAL, marker_line_color="#FFFFFF", marker_line_width=1)
            fig.add_vline(x=priced["price"].median(), line_dash="dash", line_color="#D9A441", annotation_text="Median")
            fig.update_xaxes(title="Harga iklan (Rp)", tickformat="~s")
            fig.update_yaxes(title="Jumlah mobil")
            st.plotly_chart(finish_chart(fig, 310), width="stretch", config={"displayModeBar": False}, key="market_price_histogram")
            q1, q3 = priced["price"].quantile([.25, .75])
            st.caption(f"Separuh iklan valid berada sekitar {format_rupiah(q1)}–{format_rupiah(q3)}. Nilai ekstrem bisa memperlebar rentang.")
        else:
            st.caption("Grafik menunggu setidaknya 5 harga iklan yang valid.")
with engine_col:
    with st.container(border=True):
        st.markdown("**Kapasitas mesin (CC) seperti apa yang sering muncul?**")
        engines = source.dropna(subset=["engine_cc"]) if "engine_cc" in source else pd.DataFrame()
        if len(engines) >= 5 and engines["engine_cc"].nunique() >= 3:
            fig = px.histogram(engines, x="engine_cc", nbins=min(18, max(6, len(engines) // 3)), labels={"engine_cc": "Kapasitas mesin (cc)", "count": "Jumlah mobil"})
            fig.update_traces(marker_color="#345B86", marker_line_color="#FFFFFF", marker_line_width=1)
            fig.update_xaxes(title="Kapasitas mesin (cc)")
            fig.update_yaxes(title="Jumlah mobil")
            st.plotly_chart(finish_chart(fig, 310), width="stretch", config={"displayModeBar": False}, key="market_engine_histogram")
            st.caption(f"CC tercatat pada {len(engines):,} dari {len(source):,} mobil. Rentang ini membantu membandingkan spesifikasi, bukan langsung menentukan biaya operasional.".replace(",", "."))
        else:
            st.caption("Grafik CC baru berguna setelah tersedia 5 nilai valid dari setidaknya 3 kapasitas berbeda.")

st.markdown("### Apakah tahun atau kilometer berkaitan dengan harga iklan?")
scatter_features = [("year", "Tahun kendaraan", "Tahun"), ("mileage_km", "Kilometer", "Kilometer")]
scatter_candidates = []
for key, title, axis in scatter_features:
    if key in priced:
        points = priced.dropna(subset=[key, "price"])
        if len(points) >= 10 and points[key].nunique() >= 4:
            scatter_candidates.append((key, title, axis, points))
if scatter_candidates:
    scatter_cols = st.columns(len(scatter_candidates), gap="medium")
    for idx, (key, title, axis, points) in enumerate(scatter_candidates):
        with scatter_cols[idx]:
            with st.container(border=True):
                st.markdown(f"**Harga iklan dibanding {title.lower()}**")
                fig = px.scatter(points, x=key, y="price", color="make" if "make" in points and points["make"].nunique() <= 7 else None,
                                 hover_data=[column for column in ["make", "model", "year", "mileage_km", "engine_cc"] if column in points],
                                 labels={key: axis, "price": "Harga penawaran (Rp)", "make": "Merek"}, opacity=.72,
                                 color_discrete_sequence=PALETTE)
                fig.update_yaxes(title="Harga iklan (Rp)", tickformat="~s")
                fig.update_xaxes(title=axis)
                st.plotly_chart(finish_chart(fig, 300), width="stretch", config={"displayModeBar": False}, key=f"market_scatter_{key}")
                corr = points[key].corr(points["price"])
                st.caption(f"{len(points):,} mobil memiliki kedua nilai. Korelasi linear sampel {corr:.2f}; hubungan ini deskriptif, bukan bukti sebab-akibat.".replace(",", "."))
else:
    st.info("Hubungan harga dengan tahun/kilometer belum ditampilkan: perlu sedikitnya 10 pasangan nilai dan 4 nilai fitur berbeda.", icon=":material/info:")

with st.container(border=True):
    st.markdown("**Bagaimana data listing berubah antar-refresh?**")
    st.caption("Grafik ini khusus snapshot OLX yang memiliki waktu pengambilan. Dataset Excel tidak memiliki tanggal, jadi tidak masuk ke tren.")
    h = history.copy()
    if not h.empty and "fetched_at" in h:
        h["price"] = pd.to_numeric(h.get("price"), errors="coerce")
        h["fetched_at"] = pd.to_datetime(h["fetched_at"], errors="coerce", utc=True)
        h = h.dropna(subset=["fetched_at"])
    if not h.empty and "snapshot_id" in h:
        trend = h.groupby("snapshot_id", dropna=False).agg(fetched_at=("fetched_at", "min"), median_asking_price=("price", "median"), unique_listings=("listing_id", "nunique")).reset_index()
        trend = trend.dropna(subset=["median_asking_price"]).sort_values("fetched_at")
    else:
        trend = pd.DataFrame()
    if len(trend) >= 2:
        trend["fetched_local"] = trend["fetched_at"].dt.tz_convert("Asia/Jakarta")
        fig = px.line(trend, x="fetched_local", y="median_asking_price", markers=True, hover_data=["unique_listings"], labels={"fetched_local": "Waktu snapshot", "median_asking_price": "Median harga penawaran (Rp)", "unique_listings": "Mobil unik dalam snapshot"})
        fig.update_traces(line_color=TEAL, line_width=3, marker_size=8)
        fig.update_yaxes(tickformat="~s", title="Harga iklan (Rp)")
        st.plotly_chart(finish_chart(fig, 300), width="stretch", config={"displayModeBar": False}, key="market_snapshot_trend")
        st.caption("Perubahan mencerminkan iklan yang terkumpul di tiap snapshot—bukan perubahan harga transaksi atau seluruh pasar.")
    else:
        st.caption("Belum cukup snapshot OLX bertanggal untuk membentuk tren. Perlu setidaknya dua snapshot berhasil.")

with st.expander("Tentang sumber dan batasan data"):
    st.write(f"Sumber yang dipilih: **{source_label}**. Angka halaman ini menghitung {unique_count:,} mobil unik dari {len(source):,} baris yang ditampilkan. Pada arsip penuh, kemunculan listing pada beberapa sumber atau snapshot diringkas menjadi satu mobil unik; jumlah snapshot dilaporkan terpisah.".replace(",", "."))
    st.write("Arsip Excel tidak memiliki tanggal pengambilan. Snapshot OLX menyimpan waktu saat refresh, tetapi iklan dapat berubah atau tidak aktif. Refresh tidak otomatis berjalan dan grafik bukan gambaran seluruh pasar Jabodetabek maupun nilai transaksi.")
