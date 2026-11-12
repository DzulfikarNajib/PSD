"""Editorial overview for the seven data-science project requirements."""

import pandas as pd
import streamlit as st

from src.data_loader import load_combined_archive, load_historical_data, load_history_data, load_training_archive
from src.modeling import training_eligibility
from src.styles import apply_theme
from src.ui import format_rupiah


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
            """<div class="project-illustration"><svg viewBox="0 0 520 330" role="img" aria-label="Ilustrasi laptop dengan tampilan analisis AutoMatch"><defs><linearGradient id="screen" x1="0" x2="1"><stop stop-color="#e5f7f5"/><stop offset="1" stop-color="#f7faf9"/></linearGradient></defs><ellipse cx="266" cy="292" rx="205" ry="17" fill="#dbe5e3"/><rect x="96" y="27" width="328" height="225" rx="17" fill="#173654"/><rect x="108" y="39" width="304" height="199" rx="9" fill="url(#screen)"/><rect x="124" y="54" width="83" height="168" rx="8" fill="#fff"/><rect x="219" y="54" width="178" height="35" rx="8" fill="#fff"/><rect x="219" y="99" width="84" height="123" rx="8" fill="#fff"/><rect x="313" y="99" width="84" height="123" rx="8" fill="#fff"/><path d="M242 78h104M242 68h68" stroke="#109fa4" stroke-width="5" stroke-linecap="round"/><path d="M236 199v-34h13v34m8 0v-51h13v51m8 0v-64h13v64" fill="#36b7bb"/><path d="M324 194c14-44 24-20 34-43s19-13 29-31" fill="none" stroke="#109fa4" stroke-width="5" stroke-linecap="round"/><path d="M73 253h374l39 26H35l38-26Z" fill="#9fb7c2"/><path d="M84 258h352l24 15H60l24-15Z" fill="#d8e5e8"/><rect x="227" y="258" width="67" height="5" rx="3" fill="#a6bbc3"/><path d="M163 145h35l-5-11a4 4 0 0 0-4-3h-17a5 5 0 0 0-5 3l-4 11Z" fill="#102748"/><circle cx="173" cy="146" r="4" fill="#109fa4"/><circle cx="190" cy="146" r="4" fill="#109fa4"/></svg><span>Eksplorasi data · ilustrasi</span></div>""",
            unsafe_allow_html=True,
        )
    with intro_copy:
        st.caption("PENGANTAR SAINS DATA · PROYEK APLIKASI")
        st.title("Tentang Proyek")
        st.markdown("### Dari data iklan menuju pilihan yang lebih terarah.")
        st.write("AutoMatch membantu calon pembeli menyaring mobil bekas, membandingkan iklan, dan memahami konteks harga penawaran. Halaman ini merangkum sumber data, metode, temuan, serta batasannya.")
        if st.button("Jelajahi arsip mobil", icon=":material/directions_car:", type="primary", key="project_go_search"):
            st.switch_page("pages/2_Find_Your_Car.py")

st.markdown("### Ringkasan data")
metrics = st.columns(4)
metrics[0].metric("Excel DKI", f"{len(excel):,}".replace(",", "."), border=True)
metrics[1].metric("Mobil unik di arsip penuh", f"{unique_archive_count:,}".replace(",", "."), border=True)
metrics[2].metric("Snapshot OLX tersimpan", f"{snapshot_count:,}".replace(",", "."), border=True)
metrics[3].metric("Data layak untuk model", f"{len(model_data):,}".replace(",", "."), border=True)
st.caption("Arsip penuh menghitung satu baris per listing unik; jumlah snapshot menghitung pengambilan OLX yang terpisah. Dataset Excel tidak memiliki tanggal pengambilan.")
if not prices.empty:
    st.caption(f"Dataset Excel: rentang harga penawaran {format_rupiah(prices.min())}–{format_rupiah(prices.max())}; median {format_rupiah(prices.median())}.")

st.markdown("### Tujuh komponen tugas")
cards = [
    ("1 · Project overview", "Membantu calon pembeli menyaring pilihan, membandingkan iklan, dan memahami konteks harga. Aplikasi memberi konteks awal; keputusan tetap perlu inspeksi dan verifikasi dokumen."),
    ("2 · Data overview", f"Excel menyumbang {len(excel):,} listing DKI tervalidasi; snapshot OLX baru mencatat waktu pengambilan. Arsip penuh menghitung mobil unik, snapshot menghitung observasi. Excel tidak memiliki tanggal dan iklannya mungkin sudah tidak aktif.".replace(",", ".")),
    ("3 · Exploratory data analysis", "Pahami Pasar merangkum merek, bahan bakar, harga, CC, dan hubungan harga dengan fitur jika datanya cukup. Tren hanya memakai snapshot OLX bertanggal; ia menggambarkan perubahan iklan terkumpul, bukan harga transaksi."),
    ("4 · Data preprocessing", "Kolom dinormalisasi, harga dan spesifikasi divalidasi, lalu URL dipakai untuk deduplikasi. Cakupan hanya lima kota administrasi DKI; Kepulauan Seribu dan wilayah luar DKI dikeluarkan."),
    ("5 · Modeling", "Supervised learning berupa regresi mempelajari harga iklan dari fitur mobil. Tiga regresor dibandingkan pada data holdout dengan MAE, RMSE, dan R². EDA bukan unsupervised learning; refresh tidak melatih ulang model."),
    ("6 · Key insights", "Ringkasan menunjukkan pola yang ada di arsip. Merek yang sering muncul berarti pilihannya lebih banyak pada data ini—bukan berarti mobilnya lebih baik. Sampel bukan seluruh pasar Jakarta."),
    ("7 · Kesimpulan dan rekomendasi", "Gunakan filter dan pembanding sebagai titik awal. Periksa kondisi fisik, riwayat servis, dokumen, dan status iklan langsung; jangan putuskan kelayakan dari harga atau prediksi saja."),
]
for start, size in ((0, 4), (4, 3)):
    grid = st.columns(size, gap="small")
    for col, (heading, body) in zip(grid, cards[start : start + size]):
        with col:
            with st.container(border=True, key=f"project_card_{start}_{heading.split(' · ')[0].replace(' ', '_')}"):
                st.markdown(f"#### {heading}")
                st.caption(body)

st.markdown("### Status model")
if eligible:
    st.success(f"Tersedia {len(model_data):,} listing unik yang memenuhi gerbang minimum data. {eligibility_message} Pelatihan tetap dimulai manual dari Cek Harga Iklan.".replace(",", "."))
else:
    st.info(f"Prediksi belum layak ditampilkan: {eligibility_message} Saat ini ada {len(model_data):,} listing unik yang lolos preprocessing. Pencarian dan EDA tetap dapat digunakan.".replace(",", "."))
st.caption("Gerbang saat ini: minimal 100 listing unik, 3 merek, dan 5 model. Memenuhi gerbang bukan jaminan akurasi. Targetnya harga iklan historis DKI, bukan harga transaksi atau gambaran otomatis seluruh pasar.")

with st.expander("Alur penggunaan"):
    st.markdown("**Beranda → Cari Mobil → Bandingkan Listing → Cek Harga Iklan → Buka iklan sumber.** Pahami Pasar adalah jalur tambahan untuk membaca pola data.")
