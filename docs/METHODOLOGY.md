# METHODOLOGY — Causal Pricing Decisions

> Dokumen ini menjelaskan **setiap estimator**, asumsinya, mengapa dipilih, dan
> bagaimana ia diverifikasi. Ditulis agar dapat diaudit oleh orang lain.

---

## 0. Pertanyaan kausal

**Pertanyaan:** "Apakah kebijakan diskon terarah kategori *menyebabkan* perubahan
laba kotor — dan berapa efeknya?"

**Masalah:** data observasi punya tren yang akan terjadi **dengan atau tanpa**
kebijakan. Membandingkan "sebelum vs sesudah" saja adalah korelasi, bukan kausal.

**Estimand:** efek rata-rata perlakuan pada unit terpilih (ATT):
`E[Y(1) − Y(0) | treated]`.

---

## 1. Difference-in-Differences (DiD)

**Rumus:**

```
DiD = (Ȳ_treated,post − Ȳ_treated,pre) − (Ȳ_control,post − Ȳ_control,pre)
```

**Asumsi:** *parallel trends* — tanpa kebijakan, treated & control akan bergerak
sejajar. Diuji secara empiris (lihat §2), **bukan** diandalkan.

**Implementasi:** `causal.did_estimate`.
**Kelemahan di sini:** arm tak seimbang (2 kategori perlakuan vs 16 kontrol),
sehingga DiD 2-grup menghasilkan estimasi yang lebih kecil & rapuh. Ini
**dilaporkan jujur**, bukan disembunyikan.

---

## 2. Event Study (uji asumsi parallel trends)

Memplot efek relatif per minggu, dinormalisasi ke minggu acuan pra-periode.
Bila pra-periode ≈ 0 (slope kecil, p besar), asumsi parallel trends wajar.

**Implementasi:** `causal.event_study`, `causal.parallel_trends_test`.

**Mengapa penting:** tanpa uji ini, DiD bisa mengaitkan tren yang sudah ada
dengan kebijakan — kesalahan kausal paling umum.

---

## 3. Synthetic Control

**Ide:** ketika satu (atau sedikit) unit diperlakukan, DiD 2-grup tak seimbang.
Synthetic control membangun **counterfactual** sebagai kombinasi berbobot dari
unit donor (belum-terpapar), dengan bobot dioptimalkan pada pra-periode:

```
synth_t = Σ w_i · donor_{i,t}         w_i ≥ 0, Σ w_i = 1
effect_t = treated_t − synth_t
```

**Kualitas fit:** diukur lewat `pre_gap_rmse` (selisih treated−synth di
pra-periode). Kecil = counterfactual cocok = estimasi lebih andal.

**Implementasi:** `causal.synthetic_control` (least-squares non-negatif).

**Peran di project ini:** **metode utama**, karena arm tak seimbang.

---

## 4. CUPED (variance reduction)

Menggunakan kovariat **pra-periode** untuk mengurangi varians tanpa bias:

```
Y_adj = Y − θ·(X − X̄),     θ = Cov(Y, X) / Var(X)
```

Di sini `X` = rata-rata metrik pra-periode per unit. Hasil: varians turun
**~33%** → interval kepercayaan lebih sempit → keputusan lebih presisi.

**Implementasi:** `causal.cuped_adjust`.

---

## 5. Inferensi: bootstrap & placebo

### Bootstrap block (pada unit)
CI dihitung dengan **resampling unit** (bukan baris), karena observasi dalam
satu unit berkorelasi. Ini standar yang benar untuk data panel.

**Implementasi:** `causal.did_bootstrap_ci`.

### Placebo / permutation test
Mengacak label perlakuan antar-kategori, mengulang DiD. p-value = proporsi
placebo ≥ efek nyata. Menguji apakah efek bisa muncul dari struktur kebetulan.

**Implementasi:** `causal.placebo_test`.

**Temuan jujur:** pada desain ini placebo **tidak signifikan** untuk DiD 2-grup
→ lampu kuning yang membuat kita berpindah ke synthetic control.

---

## 6. Sensitivity (lintas metrik)

Menghitung DiD pada `units_sold`, `revenue`, dan `gross_profit`. Bila arah
berbeda antar-metrik, kesimpulan **rapuh** dan tak boleh dijadikan "berhasil".

**Implementasi:** `causal.sensitivity`.

**Temuan:** unit naik, tetapi revenue & laba kotor turun → metrik keputusan
adalah **laba kotor**, dan arahnya negatif.

---

## 7. Verifikasi terhadap ground truth (pembeda utama)

Panel dibangun dari DGP terdokumentasi dengan efek **ditanam** (diketahui).
Kita menguji apakah estimator **memulihkannya**:

| Test | Yang diuji | Kriteria lulus |
|---|---|---|
| `test_did_memulihkan_efek_ditanam` | DiD tak bias | \|DiD − efek\| < 3 |
| `test_did_nol_saat_tak_ada_efek` | tak ada false positive | \|DiD\| < 2 |
| `test_parallel_trends_terdeteksi_benar` | uji asumsi akurat | `ok == True` |
| `test_bootstrap_ci_mengandung_estimasi_titik` | CI konsisten | titik ∈ CI |
| `test_synthetic_control_fit_baik` | kualitas fit | pre-gap kecil |
| `test_placebo_tidak_signifikan_tanpa_efek` | spesifisitas | tak menandai signifikan |

**Ini yang membedakan project ini dari "sekadar regresi".** Metodenya
dibuktikan benar pada data yang jawabannya kita ketahui.

---

## 8. Decision engine (spec → aksi)

Estimasi + CI dipetakan ke tier aksi (`src/decide.py`):

```
LAKUKAN   : efek > 0  DAN  CI tak lewati 0  DAN  material  DAN  guardrail aman
UJI ULANG : arah positif tapi bukti belum cukup
HENTIKAN  : efek negatif (rugi)  ATAU  guardrail margin dilanggar
```

Ambang di `config.DECISION` (dapat diaudit, bukan hard-coded di narasi).

---

## 9. Alur lengkap

```
ingest → aggregated DiD + event study → synthetic control
       → bootstrap CI + placebo + sensitivity + CUPED
       → decision engine → $ impact → marts + report → dashboard/tests
```

Satu perintah: `python src/run_pipeline.py`.
