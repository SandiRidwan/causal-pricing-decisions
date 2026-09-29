"""
decide.py — DECISION ENGINE: dari estimasi kausal → keputusan bernilai uang.

Menjawab pertanyaan yang jarang dijawab analis:
  "Berapa nilai uang dari kebijakan ini, dan apa kita harus melanjutkan?"

Menggabungkan:
  · estimasi efek (DiD / Synthetic Control) + interval kepercayaan
  · terjemahan ke nilai finansial tahunan (dengan rentang, bukan titik)
  · pemetaan ke TIER AKSI (lanjutkan / uji ulang / hentikan) via ambang spec
  · penjaga (guardrail): margin tidak boleh jatuh di bawah ambang
  · justifikasi yang dapat diaudit (setiap angka punya sumber)

PRINSIP: bila CI melewati nol ATAU efek tak material ATAU penjaga dilanggar,
keputusan TIDAK boleh "lanjutkan". Tidak ada overclaim.
"""

from __future__ import annotations

from config import DECISION


def annualized_value(effect_abs: float, ci_low: float, ci_high: float,
                     weeks_observed: int, n_units: int) -> dict:
    """
    Terjemahkan efek tahunan (per unit-panjang) ke nilai finansial.
    Rentang (CI) dipertahankan — bukan angka tunggal yang menyesatkan.
    """
    weeks_per_year = 52.0
    scale = weeks_per_year / max(weeks_observed, 1)
    return {
        "annual_effect_point": effect_abs * scale,
        "annual_effect_low": ci_low * scale,
        "annual_effect_high": ci_high * scale,
        "scale_factor": scale,
        "note": "Nilai tahunan = efek mingguan × (52/minggu observasi).",
    }


def decide(effect_abs: float, ci_low: float, ci_high: float,
           effect_pct: float, margin_after: float | None = None,
           method: str = "DiD") -> dict:
    """
    Petakan estimasi + CI ke TIER AKSI dengan justifikasi eksplisit.

    Tier:
      LAKUKAN     → efek positif, CI tak melewati 0, material, penjaga aman
      UJI ULANG   → arah positif tapi CI meragukan / data kurang
      HENTIKAN    → efek negatif (merugi) ATAU penjaga dilanggar
    """
    reasons = []
    excludes_zero = ci_low > 0 or ci_high < 0
    positive = effect_abs > 0
    material = abs(effect_pct) >= DECISION["min_effect_pct"]
    guard_ok = True
    if margin_after is not None:
        guard_ok = margin_after >= DECISION["guardrail_margin_floor"]
        if not guard_ok:
            reasons.append(
                f"Penjaga margin dilanggar: margin {margin_after:.1%} < ambang "
                f"{DECISION['guardrail_margin_floor']:.0%}.")

    if not excludes_zero:
        reasons.append("CI 95% melewati nol — efek tak dapat dibedakan dari "
                       "kebetulan.")
    if not material:
        reasons.append(f"Efek {effect_pct:+.2f}% di bawah ambang material "
                       f"{DECISION['min_effect_pct']:.1f}%.")

    if positive and excludes_zero and material and guard_ok:
        tier, badge = "LAKUKAN", "🟢"
        reasons.append("Efek positif, signifikan, material, penjaga aman.")
    elif positive and (not excludes_zero or not material):
        tier, badge = "UJI ULANG", "🟡"
        reasons.append("Arah positif namun bukti belum cukup kuat — perpanjang "
                       "uji / tambah data sebelum memutuskan.")
    else:
        tier, badge = "HENTIKAN", "🔴"
        if not positive:
            reasons.append("Efek NEGATIF: kebijakan menurunkan metrik utama "
                           "(rugi) — hentikan atau rancang ulang.")

    return {
        "tier": tier, "badge": badge, "method": method,
        "effect_abs": effect_abs, "effect_pct": effect_pct,
        "ci_low": ci_low, "ci_high": ci_high,
        "excludes_zero": excludes_zero, "material": material,
        "guardrail_ok": guard_ok, "reasons": reasons,
    }


def policy_scorecard(did: dict, synth: dict, boot: dict,
                     sensitivity: dict, placebo: dict) -> dict:
    """
    Rapor kebijakan lintas-metode: konsisten atau tidak, dan rekomendasi akhir
    berbasis BUKTI TERKUAT (bukan satu metode yang menguntungkan).
    """
    # efek laba kotor dari metode paling andal (synthetic control bila fit baik)
    synth_fit_ok = synth.get("pre_gap_rmse", 1e9) < abs(synth.get("effect_abs", 1e9))
    primary = "Synthetic Control" if synth_fit_ok else "DiD"
    eff = (synth["effect_abs"] if synth_fit_ok else did["did_abs"])
    eff_pct = (synth["effect_pct"] if synth_fit_ok else did["did_pct_of_control"])
    ci_lo, ci_hi = boot["ci_low"], boot["ci_high"]

    decision = decide(eff, ci_lo, ci_hi, eff_pct, method=primary)

    return {
        "primary_method": primary,
        "did_pct": did["did_pct_of_control"],
        "synth_pct": synth["effect_pct"],
        "synth_fit_ok": synth_fit_ok,
        "bootstrap_ci": [ci_lo, ci_hi],
        "placebo_p": placebo["placebo_p_value"],
        "metrics_agree": sensitivity["same_direction_all_metrics"],
        "decision": decision,
    }
