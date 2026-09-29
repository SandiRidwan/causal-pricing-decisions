# SPEC — Causal Pricing Decisions

> Kontrak yang dapat diaudit: metrik, ambang keputusan, skema output.
> Semua nilai hidup di [`src/config.py`](../src/config.py) — satu sumber kebenaran.

---

## 1. Kebijakan yang diuji

| Parameter | Nilai | Sumber |
|---|---|---|
| Nama | Diskon Terarah Kategori | `POLICY.name` |
| Kedalaman diskon | 15% | `POLICY.discount_pct` |
| Durasi | 8 minggu | `POLICY.duration_weeks` |
| Periode pra | 12 minggu | `POLICY.pre_weeks` |
| Periode pasca | 12 minggu | `POLICY.post_weeks` |

---

## 2. Spesifikasi metrik

| Metrik | Tipe | Peran | Arah |
|---|---|---|---|
| `units_sold` | hitung | utama (diagnostik) | lebih tinggi lebih baik |
| `revenue` | uang | sekunder | lebih tinggi lebih baik |
| `gross_profit` | uang | **UTAMA (keputusan)** | lebih tinggi lebih baik |
| `margin_pct` | rasio | **penjaga (guardrail)** | jangan < ambang |

> **Aturan emas:** metrik keputusan ditetapkan **sebelum** analisis. Memilih
> metrik setelah melihat hasil (cherry-picking) dilarang.

---

## 3. Ambang keputusan

| Ambang | Nilai | Alasan |
|---|---|---|
| `min_periods_pre` | 8 | cukup titik untuk menguji parallel trends |
| `min_periods_post` | 6 | cukup titik untuk estimasi stabil |
| `min_donor_units` | 3 | minimal donor untuk synthetic control |
| `guardrail_margin_floor` | 0.20 | margin tak boleh < 20% |
| `payback_weeks_max` | 12 | investasi diskon harus balik ≤ 12 minggu |
| `ci_must_exclude_zero` | true | "berhasil" wajib CI tak lewati 0 |
| `min_effect_pct` | 2.0 | efek di bawah ini tak dianggap material |

---

## 4. Kontrak output (kolom)

Panel harus memuat (urutan tak wajib):

```
policy, unit_id, category, period, week,
is_treated, is_post, price, units_sold, revenue,
gross_profit, discount_pct
```

Divalidasi oleh `tests/test_data_quality.py::test_kontrak_kolom`.

---

## 5. Tier keputusan (kontrak aksi)

| Tier | Syarat | Arti |
|---|---|---|
| 🟢 **LAKUKAN** | efek > 0 AND CI∌0 AND material AND guardrail OK | lanjutkan |
| 🟡 **UJI ULANG** | arah positif tapi CI meragukan / tak material | perlu bukti lebih |
| 🔴 **HENTIKAN** | efek < 0 ATAU guardrail dilanggar | stop / rancang ulang |

Setiap tier **wajib** disertai `reasons` (justifikasi) — divalidasi
`tests/test_decision_spec.py` dan `src/spec_audit.py`.

---

## 6. Pelaporan nilai finansial

```
annual_effect = weekly_effect × (52 / weeks_observed)
dilaporkan sebagai RENTANG [low, high] dari CI bootstrap — bukan titik tunggal
```

Alasan: satu angka memberi kesan presisi palsu. Rentang jujur soal ketidakpastian.

---

## 7. Audit kepatuhan spec

`python src/spec_audit.py` memeriksa:

1. Semua bagian laporan ada (did, synthetic_control, bootstrap, placebo,
   sensitivity, decision, ground_truth).
2. Tier valid + justifikasi ada.
3. Metrik keputusan terdefinisi.
4. CI tidak terbalik (low ≤ high).
5. Ground truth dilaporkan (transparansi).
6. Ambang keputusan terdefinisi.

Keluar dengan status ≠ 0 bila ada pelanggaran (aman untuk CI).
