"""insights_content.py — konten Insight & Rekomendasi (Kesimpulan + Aksi + Risiko)."""
from insight import register

register(
    "kpi",
    kesimpulan=(
        "Kebijakan yang diuji adalah diskon terarah kategori selama 8 minggu. "
        "Metrik keputusan adalah LABO KOTOR — bukan unit terjual. Diskon memang "
        "menaikkan unit (elastisitas), tetapi biaya diskon menggerus margin "
        "lebih besar dari kenaikan volume, sehingga laba kotor TURUN."),
    rekomendasi=[
        "Nilai kebijakan harga dari LABA KOTOR, bukan unit/revenue — volume "
        "tinggi dengan margin rendah bisa menghancurkan profit.",
        "Sebelum meluncurkan diskon, hitung titik impas: kenaikan volume yang "
        "dibutuhkan agar laba kotor tidak turun.",
        "Pertimbangkan alternatif non-harga (bundling, loyalitas) yang tidak "
        "langsung menggerus margin.",
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
        "Jangan pakai DiD 2-grup sebagai dasar keputusan saat arm tak seimbang; "
        "naikkan ke synthetic control.",
        "Laporkan placebo test bersama estimasi — pembaca berhak tahu bila efek "
        "tak berbeda dari kebetulan.",
        "Seimbangkan jumlah unit perlakuan-kontrol di desain berikutnya.",
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
        "Selalu tunjukkan pra-periode; bila menyimpang, jangan klaim kausal.",
        "Perhatikan kapan efek muncul/menghilang (dinamika), bukan hanya rata-rata.",
        "Bila ada efek lanjutan setelah promo berakhir, itu sinyal pergeseran "
        "perilaku pelanggan.",
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
        "Jadikan synthetic control metode utama saat arm tak seimbang atau "
        "perlakuan tunggal.",
        "Periksa pre-gap RMSE sebagai bukti kualitas fit sebelum memakai hasil.",
        "Laporkan bobot donor teratas agar chain-of-reasoning dapat diaudit.",
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
        "Hentikan kebijakan diskon ini, atau rancang ulang dengan kedalaman/ "
        "lingkup yang lebih kecil dan uji ulang.",
        "Wajibkan ambang keputusan tertulis (min efek material, guardrail margin) "
        "sebelum kebijakan dijalankan.",
        "Terjemahkan setiap hasil ke nilai uang agar keputusan punya bobot.",
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
        "Tetapkan SATU metrik keputusan sebelum analisis; jangan pilih metrik "
        "setelah melihat hasil (p-hacking).",
        "Selalu laporkan guardrail metrics (margin) bersama metrik utama.",
        "Bila metode berbeda jauh, turunkan tingkat keyakinan & uji ulang.",
    ],
    risiko=(
        "Memilih metrik yang menguntungkan setelah melihat data (cherry-picking) "
        "adalah pelanggaran integritas analitik yang bisa menyesatkan "
        "stakeholder dan menghancurkan kepercayaan."),
    tingkat="tinggi",
)
