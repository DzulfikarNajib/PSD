"""Explain the seven data-science project components and current limitations."""

import pandas as pd
import streamlit as st

from src.data_loader import load_historical_data, load_history_data, load_live_data
from src.modeling import training_eligibility
from src.styles import apply_theme
from src.ui import format_rupiah

apply_theme()
live, history, historical = load_live_data(), load_history_data(), load_historical_data()
st.title("Tentang Proyek")
st.caption("Metode, sumber data, dan batasan AutoMatch untuk proyek Pengantar Sains Data.")

prices = pd.to_numeric(historical.get("price", pd.Series(dtype=float)), errors="coerce").dropna()
listing_count = historical["listing_id"].nunique() if not historical.empty else (live["listing_id"].nunique() if not live.empty and "listing_id" in live else len(live))
snapshot_count = history["fetched_at"].nunique(dropna=True) if not history.empty and "fetched_at" in history else 0
eligible, eligibility_message, model_data = training_eligibility(historical)

st.header("1. Project overview")
st.write("Proyek ini membantu calon pembeli mobil bekas mempersempit pencarian dan memahami konteks harga iklan. Tujuannya adalah mendukung eksplorasi serta perbandingan awal, bukan menggantikan inspeksi kendaraan atau pemeriksaan dokumen.")

st.header("2. Data overview")
st.write("EDA dan modeling memakai dataset historis PSD_DATA_MOBIL_JAKARTA_FULL.xlsx yang tersedia di data/; snapshot OLX melalui Datawebot dipisahkan untuk pencarian listing terbaru. Cakupan analisis dibatasi pada Jakarta Pusat, Selatan, Timur, Barat, dan Utara. Kepulauan Seribu serta daerah lain dikeluarkan.")
overview = st.columns(4)
overview[0].metric("Listing historis DKI", listing_count, border=True)
overview[1].metric("Listing live terbaru", len(live), border=True)
overview[2].metric("Snapshot live", snapshot_count, border=True)
overview[3].metric("Kolom harga valid", len(prices), border=True)
if not prices.empty:
    st.caption(f"Harga pada dataset historis: {format_rupiah(prices.min())} sampai {format_rupiah(prices.max())}; median {format_rupiah(prices.median())}.")
st.caption("Dataset historis didominasi listing DKI dan tidak mewakili seluruh pasar. Harga adalah harga penawaran, bukan harga transaksi.")

st.header("3. Exploratory data analysis")
st.write("Halaman Pahami Pasar merangkum jumlah listing menurut merek dan bahan bakar, sebaran harga dan kapasitas mesin, hubungan deskriptif antara harga dengan tahun/kilometer/CC, serta perubahan antar-snapshot jika tersedia. Grafik hubungan tidak membuktikan sebab-akibat. Tren waktu memerlukan setidaknya dua snapshot.")

st.header("4. Data preprocessing")
st.write("Kolom sumber dipetakan ke skema analisis. Harga harus minimal Rp1 juta; tahun yang bukan angka pasti diperlakukan kosong, rentang kilometer diringkas dengan titik tengah, dan kapasitas mesin berbentuk rentang diringkas ke titik tengah. URL detail dinormalisasi menjadi listing_id dan duplikasi URL dihapus. Hanya lima kota administrasi DKI dipakai; Kepulauan Seribu dan wilayah luar DKI dikeluarkan.")

st.header("5. Modeling")
st.write("Metode yang digunakan adalah **supervised learning berupa regresi** pada dataset historis. Targetnya harga iklan; fitur mencakup merek, model, tahun, kilometer, CC, transmisi, bahan bakar, dan tipe bodi. Tiga regresor dibandingkan memakai holdout 80/20 dengan MAE, RMSE, dan R²; pilihan berdasarkan MAE terendah.")
st.write("Proyek ini tidak memakai unsupervised learning. EDA dan pengelompokan deskriptif pada grafik bukan model unsupervised.")
if eligible:
    st.success(f"Data riwayat saat ini memenuhi gerbang minimum model: {len(model_data)} listing unik. Evaluasi/pelatihan tetap hanya berjalan setelah tombol eksplisit di halaman Cek Harga Iklan ditekan.")
else:
    st.info(f"Prediksi belum layak ditampilkan: {eligibility_message} Saat ini terhitung {len(model_data)} listing unik yang memenuhi preprocessing. Grafik dan perbandingan listing tetap bisa dipakai.")
st.caption("Ambang minimum proyek: 100 listing unik, minimal 3 merek, dan 5 model. Lolos ambang bukan jaminan model akurat; metrik holdout tetap perlu diperiksa.")

st.header("6. Key insights")
if historical.empty:
    st.info("Dataset historis belum tersedia, jadi insight EDA belum tersedia. Aplikasi tidak membuat data contoh.")
else:
    insight_data = historical
    insight_cols = st.columns(3)
    if "make" in insight_data and insight_data["make"].notna().any():
        top_make = insight_data["make"].value_counts().index[0]
        insight_cols[0].metric("Merek paling sering muncul", str(top_make), int(insight_data["make"].eq(top_make).sum()), border=True)
    if "fuel_type" in insight_data and insight_data["fuel_type"].notna().any():
        top_fuel = insight_data["fuel_type"].value_counts().index[0]
        insight_cols[1].metric("Bahan bakar paling sering", str(top_fuel), int(insight_data["fuel_type"].eq(top_fuel).sum()), border=True)
    insight_cols[2].metric("Median harga penawaran", format_rupiah(prices.median()) if not prices.empty else "-", border=True)
    st.caption(f"Insight dihitung dari {listing_count} listing historis DKI; iklan historis belum tentu masih aktif.")

st.header("7. Kesimpulan dan rekomendasi")
st.write("Gunakan filter untuk menyusun shortlist, bandingkan dua atau tiga listing, dan pakai median listing serupa sebagai konteks awal. Sebelum membeli, periksa kendaraan secara langsung, verifikasi dokumen, dan minta riwayat servis serta kecelakaan. Jangan menyimpulkan kualitas kendaraan dari harga atau spesifikasi iklan saja.")

with st.expander("Alur pemakaian dashboard"):
    st.markdown("**Beranda → Cari Mobil → Bandingkan Listing → Cek Harga Iklan → Buka iklan OLX.** Pahami Pasar adalah jalur tambahan untuk membaca distribusi dan insight, bukan langkah wajib untuk mencari kendaraan.")
