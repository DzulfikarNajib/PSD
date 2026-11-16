# AutoMatch Design System & Guidelines (DESIGN.md)

## 1. Identitas Visual & Prinsip
AutoMatch adalah dashboard analitik pasar mobil bekas berbasis sains data untuk calon pembeli di Jabodetabek. Desain dashboard mengutamakan kejelasan informasi, keterbacaan data, integritas metodologis, dan kenyamanan visual.

- **Filosofi:** Fungsional, jujur, berbasis bukti data nyata, bebas basa-basi generik AI.
- **Tone & Karakter:** Profesional, tenang, percaya diri, dan mudah dipahami pengguna awam.
- **Liveliness Dials:** ENERGY 1 (Calm), RHYTHM 2 (Balanced), MOTION 1 (Minimal & Functional).

---

## 2. Palet Warna (Color Palette)
- **Primary Teal:** `#008B8B` (warna aksen utama, tombol aksi primer, sorotan metrik penting, garis fokus).
- **Secondary Teal / Dark Accent:** `#066B6B` (state hover/active untuk tombol primer).
- **Background Utama:** `#F8FAFC` (latar belakang canvas halaman yang bersih dan sejuk).
- **Surface / Card Background:** `#FFFFFF` (permukaan kartu metrik, form, dan panel visualisasi).
- **Borders & Dividers:** `#E2E8F0` (border halus 1px solid di sekeliling kartu dan tabel, tanpa drop-shadow tebal).
- **Text Utama (Heading & Body):** `#0F172A` (Slate 900, kontras tinggi dan tajam).
- **Text Muted / Caption:** `#475569` (Slate 600, kontras memenuhi standar WCAG AA > 4.5:1).
- **Status Badges:**
  - *Underpriced:* Background `#ECFDF5`, Teks `#047857`, Border `#A7F3D0` (Hijau ramah).
  - *Harga Wajar / Fair:* Background `#F0FDF4`, Teks `#008B8B`, Border `#99F6E4` (Teal konsisten).
  - *Overpriced:* Background `#FEF2F2`, Teks `#B91C1C`, Border `#FECACA` (Merah peringatan).

---

## 3. Tipografi & Copywriting (Anti-Slop)
- **Font Family:** `Inter`, `Plus Jakarta Sans`, sans-serif sistem modern.
- **Hirarki Tipografi:**
  - Judul Halaman (H1): 2.2rem - 2.8rem, bold, letter-spacing -0.025em.
  - Subheading / Section Header (H2-H3): 1.25rem - 1.5rem, semi-bold.
  - Label & Body: 0.875rem - 1rem, regular/medium, line-height 1.6.
  - Caption & Metrik Sekunder: 0.75rem - 0.8125rem.
- **Copywriting Rules:**
  - **Larangan Em Dash (Rule R-02):** Dilarang keras menggunakan karakter em dash (`—`). Gunakan koma, titik, titik dua, tanda hubung biasa (`-`), atau tanda kurung `()`.
  - **Tanpa Basa-Basi Generik:** Hindari kata klise seperti "AI Powered", "Revolutionary", "Next-gen", "Cutting-edge".
  - **Emoji Terukur:** Tidak menggunakan emoji berlebihan atau dekoratif semata. Gunakan icon material resmi Streamlit (`:material/...:`) yang relevan.

---

## 4. Hero Banner (Layout & Kontras)
- **Tata Letak:** Teks informasi berada di sebelah kiri (`text-align: left`), dengan lebar maksimum container terkontrol (`max-width: 580px`).
- **Gradasi Pelindung Kontras:** Menggunakan layer `linear-gradient(90deg, rgba(248, 250, 252, 0.98) 0%, rgba(248, 250, 252, 0.92) 48%, rgba(248, 250, 252, 0.35) 75%, rgba(248, 250, 252, 0.0) 100%)` di atas gambar mobil latar belakang.
- **Tujuan Kontras:** Menjamin teks judul, deskripsi, dan tombol CTA utama memiliki kontras sempurna terhadap latar belakang, serta tidak menabrak objek mobil di sisi kanan banner pada resolusi desktop maupun layar kecil.

---

## 5. Aturan Visualisasi Data (Plotly Charts)
- **Format Sumbu Harga:**
  - Seluruh sumbu harga Rupiah wajib memakai satuan manusiawi yang ringkas:
    - `Rp <nilai> Jt` untuk nominal juta (misal `Rp 150 Jt`).
    - `Rp <nilai> M` untuk nominal miliar (misal `Rp 1,2 M`).
  - **Dilarang Keras** memunculkan format SI prefix bawaan Plotly (`5G`, `10G`, dsb) yang membingungkan audiens lokal Indonesia.
- **Pembersihan Outlier:**
  - Sediakan filter pemisahan antara "Semua Data" vs "Pasar Umum (≤ Persentil 95)" agar histogram dan scatter plot tidak terdistorsi menjadi gepeng oleh mobil ultra-mewah (outlier).
- **Desain Grafik:**
  - Background grafik transparan atau `#FFFFFF` murni menyatu dengan card surface.
  - Gridline tipis `#F1F5F9`, bar radius rounded 6px, palette warna selaras dengan tema utama AutoMatch.
