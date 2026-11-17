# Audit Follow-up AutoMatch

Tanggal: 17 November 2026  
Cakupan: implementasi temuan audit data, model, kartu listing, dan pengalaman halaman.

## Perbaikan

- Iklan di bawah Rp25 juta atau teksnya memuat petunjuk DP/angsuran dipisahkan dari tampilan analitis dan pelatihan model. CSV arsip mentah tidak diubah. Dataset training lokal kini berisi 4.165 listing; 216 baris ditandai untuk dikecualikan.
- Tiga algoritma diuji dengan target harga asli dan `log1p` pada holdout yang sama. Metrik tetap pada skala rupiah. Random Forest target asli terpilih dengan MAE sekitar Rp205,2 juta; transformasi log memperbaiki Linear Regression, tetapi tidak mengalahkan Random Forest.
- Prediksi plot Actual vs Predicted disimpan dari holdout sebelum model final dilatih ulang. Artefak baru memiliki 833 pasangan uji dan metadata validasi versi 3.
- Kartu mobil menghapus panel emoji besar dan menampilkan tipe bodi, tahun, dan segmen. Foto hanya memakai URL listing yang tersimpan; scraping gambar baru ditunda.
- Parameter lebar deprecated `use_container_width` diganti ke `width="stretch"` pada semua halaman.
- Filter pencarian dibuka saat halaman dimuat. Grafik harga per tahun memakai box plot dengan skala log. Beranda menampilkan grafik merek dan bahan bakar; Cek Harga memuat contoh arsip berlabel tanpa menghitung estimasi otomatis.
- Ringkasan proyek mencatat pembuangan indikasi DP/kredit, dan plot evaluasi memuat seluruh rentang holdout.

## Verifikasi

- `py_compile` untuk entrypoint dan modul halaman: lulus.
- Tes preprocessing: 9 lulus; tes modeling: 5 lulus; tes segmentasi dan pencarian: 6 lulus; tes halaman: 25 lulus.
- Estimasi model, validasi artefak, feature importance, dan 833 prediksi holdout berhasil dimuat.
- Server Streamlit lokal merespons HTTP 200 dan berkas logo tersedia. AppTest satu halaman tidak memberi output setelah 75 detik dan dihentikan; click-through interaktif belum terverifikasi.

## Batas

URL foto dapat tidak aktif karena berasal dari iklan OLX. Kesimpulan model hanya menggambarkan split holdout ini. Keberhasilan render pada Streamlit Cloud harus dikonfirmasi setelah deploy selesai.
