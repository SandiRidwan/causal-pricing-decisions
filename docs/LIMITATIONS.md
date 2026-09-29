# LIMITATIONS — Causal Pricing Decisions

> Kejujuran adalah bagian dari analisis. Dokumen ini menyebut apa yang **tidak**
> bisa disimpulkan project, dan mengapa.

---

## 1. Panel harga-waktu adalah SIMULASI TERKONTROL

**Yang benar:** panel mingguan dibangun dari **katalog ritel NYATA** (Morrisons,
11.208 produk — harga, promo, rating nyata) yang diberi mekanisme promo
**eksplisit dan diketahui**.

**Yang TIDAK benar (jika disalahpahami):** ini **bukan** harga pasar nyata yang
diobservasi mingguan. Efeknya **ditanam**, bukan muncul dari pasar.

**Mengapa begitu (disengaja):** untuk **membuktikan estimator benar**, kita butuh
data dengan efek yang diketahui (ground truth). Data pasar nyata tidak memberi
itu. Ini praktik standar ekonometrika (Monte-Carlo study). Panel diberi label
"controlled" agar tak pernah disalahartikan.

**Konsekuensi:** angka efek (−8.9% DiD, −36% synth) memvalidasi **metode**, bukan
mengklaim efek di pasar nyata.

---

## 2. Biaya (COGS) DIASUMSIKAN, tidak nyata

Laba kotor dihitung dengan asumsi **margin kotor 30%**
(`config.ASSUMED_GROSS_MARGIN`). Angka ini memengaruhi besaran efek laba kotor
secara langsung. Dengan COGS nyata, hasil bisa berbeda.

**Implikasi:** arah & metodologi valid; **besaran** laba bergantung pada asumsi ini.

---

## 3. Confounding tak teramati

Model tidak memodelkan faktor yang di dunia nyata memengaruhi permintaan
bersamaan dengan harga: promosi kompetitor, perubahan musim nyata, gangguan
pasokan, efek kanibalisasi antar-kategori, efek halo. Semua ini bisa
membiaskan estimasi pada data nyata.

---

## 4. Batasan metode

| Metode | Batasan |
|---|---|
| DiD | arm tak seimbang → estimasi rapuh (dilaporkan) |
| Parallel trends | diuji pada pra-periode, tak menjamin pasca-periode |
| Synthetic control | butuh donor relevan; bobot bisa overfit bila donor sedikit |
| Bootstrap CI | mengasumsikan unit exchangeable |
| Placebo | daya uji terbatas bila jumlah kategori sedikit |

---

## 5. Generalisasi

- Satu kebijakan (diskon 15%, 2 kategori, 8 minggu). Efek **tidak otomatis**
  berlaku untuk kedalaman diskon, kategori, atau durasi lain.
- Elastisitas ditanam konstan; di pasar nyata elastisitas bervariasi per produk.
- Struktur pasar UK (Morrisons); ritel lain bisa berbeda.

---

## 6. Batas klaim keputusan

Keputusan **HENTIKAN** di project ini valid **di dalam model**. Di perusahaan
nyata, keputusan harga juga mempertimbangkan: strategi akuisisi pelanggan,
efek jangka panjang (brand), kendala kontrak pemasok, dan tujuan strategis lain
yang tak ada di data. **Analisis menyarankan, bisnis memutuskan.**

---

## 7. Bukan saran

Project ini **edukasional**. Bukan saran investasi, harga, atau komersial.
Implementasi nyata memerlukan data COGS asli, konteks pasar, dan validasi di
lingkungan produksi.

---

## 8. Yang bisa dipercaya dari project ini

✅ Metodologi kausal benar & teruji (21 test, term. verifikasi ground-truth).
✅ Kerangka keputusan eksplisit, dapat diaudit, tanpa overclaim.
✅ Pipeline end-to-end reproducible (satu perintah, seed tetap).
✅ Kejujuran tentang asumsi & batas.

❌ Klaim tentang efek harga di pasar UK nyata.
❌ Angka laba absolut tanpa penggantian asumsi COGS.
