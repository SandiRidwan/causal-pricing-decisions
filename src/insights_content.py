"""insights_content.py — konten Insight & Rekomendasi (v2: Aksi + Langkah + Metrik + Pemilik)."""
from insight import register

register(
    "kpi",
    kesimpulan=(
        "Kebijakan yang diuji adalah diskon terarah kategori selama 8 minggu. "
        "Metrik keputusan adalah LABO KOTOR — bukan unit terjual. Diskon memang "
        "menaikkan unit (elastisitas), tetapi biaya diskon menggerus margin "
        "lebih besar dari kenaikan volume, sehingga laba kotor TURUN."),
    rekomendasi=[
        {"aksi": "Nilai setiap kebijakan harga dari LABA KOTOR, bukan unit/revenue",
         "langkah": [
             "Tetapkan gross_profit sebagai metrik keputusan tunggal sebelum analisis dimulai.",
             "Hitung titik impas: kenaikan volume minimal yang dibutuhkan agar laba kotor tidak turun.",
             "Bandingkan setiap usulan diskon terhadap titik impas itu sebelum disetujui.",
         ],
         "metrik": "100% usulan harga disertai estimasi dampak laba kotor + titik impas",
         "pemilik": "Head of Pricing + tim analitik"},
        {"aksi": "Hitung titik impas diskon sebelum peluncuran",
         "langkah": [
             "Tentukan kedalaman diskon (mis. 15%) dan margin unit dasar (asumsi 30%).",
             "Hitung kenaikan volume yang dibutuhkan: Δ%unit ≥ diskon/(margin−diskon).",
             "Tolak usulan yang kenaikan volumenya tak realistis mencapai angka itu.",
         ],
         "metrik": "Tidak ada kebijakan diskon dirilis tanpa hitungan titik impas",
         "pemilik": "Tim analitik pricing"},
        {"aksi": "Pertimbangkan alternatif non-harga (bundling, loyalitas)",
         "langkah": [
             "Petakan kandidat alternatif: bundling, poin loyalitas, kupon terbatas.",
             "Uji A/B alternatif vs diskon langsung pada subset kategori.",
             "Pilih opsi dengan laba kotor tertinggi per rupiah insentif.",
         ],
         "metrik": "Laba kotor per unit insentif ≥ diskon langsung",
         "pemilik": "Tim marketing + analitik"},
    ],
    risiko=(
        "Mengejar kenaikan unit/revenue tanpa memeriksa laba kotor berisiko "
        "'menjual lebih banyak, untung lebih sedikit'. Pada skala besar, "
        "kebijakan seperti ini bisa menggerus profit tahunan secara serius."),
    tingkat="kritis",
)

register(
    "did",
    kesimpulan=(
        "Difference-in-Differences membandingkan perubahan laba kotor grup "
        "perlakuan terhadap kontrol. Namun karena arm TIDAK seimbang (2 kategori "
        "perlakuan vs 16 kontrol), DiD 2-grup menghasilkan estimasi kecil dan "
        "placebo test tidak signifikan — tanda bahwa estimasi ini RAPUH."),
    rekomendasi=[
        {"aksi": "Jangan pakai DiD 2-grup sebagai dasar keputusan saat arm tak seimbang",
         "langkah": [
             "Periksa rasio jumlah unit perlakuan:kontrol sebelum memilih metode.",
             "Bila rasio < 1:3, naikkan ke synthetic control atau DiD tersintesis.",
             "Laporkan metode terpilih beserta alasannya.",
         ],
         "metrik": "Rasio arm dilaporkan; metode sesuai saat rasio tak seimbang",
         "pemilik": "Tim causal inference"},
        {"aksi": "Laporkan placebo test bersama setiap estimasi",
         "langkah": [
             "Jalankan placebo/permutation test untuk setiap estimasi utama.",
             "Cantumkan p-value placebo di samping estimasi titik.",
             "Tandai 'rapuh' bila placebo tidak signifikan.",
         ],
         "metrik": "100% laporan estimasi menyertakan p-value placebo",
         "pemilik": "Tim analitik"},
        {"aksi": "Seimbangkan jumlah unit perlakuan-kontrol di desain berikutnya",
         "langkah": [
             "Rancang pemilihan kategori perlakuan dengan target rasio ≥ 1:3.",
             "Bila kendala operasional, gunakan metode matching/synthetic control sejak awal.",
             "Dokumentasikan pilihan desain.",
         ],
         "metrik": "Rasio arm ≥ 1:3 pada desain eksperimen berikutnya",
         "pemilik": "Tim eksperimen"},
    ],
    risiko=(
        "Mempercayai DiD 2-grup yang rapuh bisa menghasilkan keputusan kebijakan "
        "yang salah arah. Placebo yang gagal signifikan adalah lampu kuning."),
    tingkat="tinggi",
)

register(
    "event_study",
    kesimpulan=(
        "Event study memplot efek relatif per minggu. Pra-periode relatif datar "
        "(slope kecil, p besar) → asumsi PARALLEL TRENDS masuk akal, sehingga "
        "metode kausal (DiD/synthetic) layak dipakai. Pasca-intervensi, efek "
        "bergerak jelas ke arah negatif."),
    rekomendasi=[
        {"aksi": "Selalu tunjukkan pra-periode sebelum mengklaim kausal",
         "langkah": [
             "Plot efek relatif per periode dengan garis acuan 0.",
             "Hitung slope pra-periode dan p-value-nya.",
             "Batalkan klaim kausal bila pra-periode tidak datar.",
         ],
         "metrik": "|slope| pra-periode < 1,0 dan p > 0,05 sebelum klaim kausal",
         "pemilik": "Tim causal inference"},
        {"aksi": "Perhatikan dinamika efek, bukan hanya rata-rata",
         "langkah": [
             "Identifikasi kapan efek muncul & menghilang.",
             "Bandingkan efek awal vs akhir periode intervensi.",
             "Catat efek lanjutan setelah promo berakhir.",
         ],
         "metrik": "Profil per-minggu dilaporkan, bukan hanya efek agregat",
         "pemilik": "Tim analitik"},
        {"aksi": "Deteksi pergeseran perilaku pelanggan",
         "langkah": [
             "Periksa apakah efek bertahan setelah diskon berakhir.",
             "Bila bertahan, tandai sebagai perubahan perilaku (bukan efek sementara).",
             "Sesuaikan strategi retensi bila ditemukan.",
         ],
         "metrik": "Efek pasca-promo diukur dan dilaporkan",
         "pemilik": "Tim CRM + analitik"},
    ],
    risiko=(
        "Mengabaikan uji parallel trends berisiko mengaitkan perubahan yang "
        "sebenarnya akibat tren yang sudah ada dengan kebijakan — kesalahan "
        "kausal paling umum dan paling merugikan."),
    tingkat="sedang",
)

register(
    "synthetic",
    kesimpulan=(
        "Synthetic control membangun counterfactual dari kombinasi berbobot "
        "kategori donor, dioptimalkan pada pra-periode (pre-gap kecil = fit "
        "baik). Estimasi efek laba kotor dari metode ini paling dekat ke "
        "ground-truth, dan konsisten: kebijakan diskon MERUGIKAN laba kotor."),
    rekomendasi=[
        {"aksi": "Jadikan synthetic control metode utama saat arm tak seimbang",
         "langkah": [
             "Pilih minimal 3 kategori donor yang relevan & belum-terpapar.",
             "Optimalkan bobot pada pra-periode (minimalkan pre-gap).",
             "Pakai estimasi synthetic sebagai dasar keputusan bila fit baik.",
         ],
         "metrik": "pre_gap_rmse < |effect_abs| sebagai syarat fit layak",
         "pemilik": "Tim causal inference"},
        {"aksi": "Periksa pre-gap RMSE sebagai bukti kualitas fit",
         "langkah": [
             "Hitung RMSE selisih treated−synthetic di pra-periode.",
             "Tolak hasil bila pre-gap besar (counterfactual tak cocok).",
             "Cantumkan pre-gap di setiap laporan.",
         ],
         "metrik": "pre-gap RMSE dilaporkan & ambang fit ditetapkan",
         "pemilik": "Tim analitik"},
        {"aksi": "Laporkan bobot donor teratas untuk audit",
         "langkah": [
             "Tampilkan 5 donor dengan bobot terbesar.",
             "Dokumentasikan alasan donor dipilih.",
             "Tinjau kewajaran bobot bersama domain expert.",
         ],
         "metrik": "Bobot donor teratas terdokumentasi tiap analisis",
         "pemilik": "Tim analitik"},
    ],
    risiko=(
        "Synthetic control tetap butuh donor yang relevan. Bila donor tidak "
        "sebanding, counterfactual bisa bias — selalu laporkan pre-gap dan "
        "bandingkan dengan metode lain sebagai validasi silang."),
    tingkat="sedang",
)

register(
    "decision",
    kesimpulan=(
        "Decision engine menerjemahkan estimasi + CI ke tier aksi. Karena efek "
        "menurunkan laba kotor (negatif) dan CI tidak melewati nol pada metrik "
        "utama, keputusannya HENTIKAN. Nilai finansial dilaporkan sebagai "
        "rentang tahunan, bukan satu angka."),
    rekomendasi=[
        {"aksi": "Hentikan atau rancang ulang kebijakan diskon ini",
         "langkah": [
             "Batalkan peluncuran/perluasan diskon 15% kategori ini.",
             "Rancang ulang dengan kedalaman/lingkup lebih kecil (mis. 5%, kategori terbatas).",
             "Uji ulang versi yang lebih kecil sebelum diputuskan.",
         ],
         "metrik": "Kebijakan lama dihentikan; versi uji baru menghindari laba kotor < 0",
         "pemilik": "Head of Pricing"},
        {"aksi": "Wajibkan ambang keputusan tertulis sebelum kebijakan dijalankan",
         "langkah": [
             "Tetapkan min_effect_pct (mis. 2%) dan guardrail margin (mis. 20%).",
             "Syaratkan CI tak melewati nol untuk keputusan 'lanjutkan'.",
             "Sosialisasikan ambang ke seluruh tim pricing.",
         ],
         "metrik": "100% kebijakan harga punya ambang keputusan tertulis",
         "pemilik": "Manajemen pricing"},
        {"aksi": "Terjemahkan setiap hasil ke nilai uang",
         "langkah": [
             "Konversi efek mingguan ke tahunan (52/pekan observasi).",
             "Laporkan sebagai rentang dari CI, bukan titik tunggal.",
             "Sertakan asumsi eksplisit (margin, COGS).",
         ],
         "metrik": "Setiap keputusan harga disertai estimasi nilai tahunan (rentang)",
         "pemilik": "Tim analitik pricing"},
    ],
    risiko=(
        "Tanpa ambang & guardrail eksplisit, keputusan harga cenderung "
        "dipengaruhi tekanan komersial jangka pendek alih-alih bukti. Ini "
        "mengulang kesalahan yang mahal."),
    tingkat="kritis",
)

register(
    "robustness",
    kesimpulan=(
        "Uji ketahanan memeriksa konsistensi lintas metode (DiD vs synthetic) "
        "dan lintas metrik (unit/revenue/laba). Arah berbeda antar-metrik "
        "(unit naik, laba turun) adalah temuan PENTING: kesimpulan tergantung "
        "metrik yang dipilih — dan metrik keputusan adalah laba kotor."),
    rekomendasi=[
        {"aksi": "Tetapkan satu metrik keputusan sebelum analisis",
         "langkah": [
             "Sepakati metrik keputusan (laba kotor) sebelum melihat hasil.",
             "Dokumentasikan metrik pendukung (unit, revenue) secara terpisah.",
             "Larang pergantian metrik setelah hasil muncul.",
         ],
         "metrik": "Metrik keputusan ditetapkan di awal & tidak berubah",
         "pemilik": "Head of Analytics"},
        {"aksi": "Laporkan guardrail metrics bersama metrik utama",
         "langkah": [
             "Pilih guardrail (margin) yang tak boleh dilanggar.",
             "Pantau guardrail sepanjang periode intervensi.",
             "Hentikan kebijakan bila guardrail dilanggar.",
         ],
         "metrik": "Guardrail margin ≥ ambang di setiap periode",
         "pemilik": "Tim pricing"},
        {"aksi": "Turunkan keyakinan & uji ulang bila metode berbeda jauh",
         "langkah": [
             "Hitung selisih estimasi antar-metode.",
             "Bila sangat berbeda, turunkan tingkat keyakinan.",
             "Rancang uji tambahan sebelum keputusan final.",
         ],
         "metrik": "Keputusan ditunda bila ketidaksepakatan antar-metode tinggi",
         "pemilik": "Tim analitik"},
    ],
    risiko=(
        "Memilih metrik yang menguntungkan setelah melihat data (cherry-picking) "
        "adalah pelanggaran integritas analitik yang bisa menyesatkan "
        "stakeholder dan menghancurkan kepercayaan."),
    tingkat="tinggi",
)
