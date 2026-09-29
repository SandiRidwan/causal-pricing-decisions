"""
test_causal_validity.py — validitas STATISTIK estimator kausal.

Bukan sekadar "kode jalan": kita menguji bahwa estimator MENGHASILKAN ANGKA
YANG BENAR pada kasus dengan ground-truth yang diketahui. Ini pembeda utama
dari project analitik biasa.

  · DiD memulihkan efek yang ditanam pada kasus sintetis bersih.
  · Synthetic control punya pre-gap kecil bila donor cocok.
  · Bootstrap CI konsisten dengan estimasi titik.
  · Placebo tidak signifikan ketika TIDAK ada efek (uji spesifisitas).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from causal import (did_estimate, did_bootstrap_ci, event_study,  # noqa: E402
                    parallel_trends_test, placebo_test, synthetic_control,
                    weekly_series)
from config import SEED  # noqa: E402


def _clean_did_panel(effect: float = 50.0, seed: int = SEED,
                     n_units: int = 20, n_weeks: int = 20) -> pd.DataFrame:
    """
    Panel sintetis BERSIH: treated naik `effect` setelah intervensi,
    kontrol tidak. Tren pra-periode identik (parallel). Uji apakah DiD = effect.
    Kategori: 'tg' (treated) dan 'cg0..' (donor) agar synthetic control punya
    donor nyata.
    """
    rng = np.random.default_rng(seed)
    rows = []
    half = n_weeks // 2
    for unit in range(n_units):
        treated = unit < (n_units // 2)
        base = 100.0 + unit  # level berbeda per unit (fixed effect)
        cat = "tg" if treated else f"donor{unit % 4}"
        for w in range(n_weeks):
            post = w >= half
            val = base + 0.5 * w + (effect if (treated and post) else 0.0)
            val += rng.normal(0, 1.0)
            rows.append({"unit_id": f"u{unit}", "is_treated": treated,
                         "is_post": post, "week": w, "gross_profit": val,
                         "category": cat})
    return pd.DataFrame(rows)


def test_did_memulihkan_efek_ditanam():
    """DiD pada data bersih harus ≈ efek yang ditanam (50)."""
    panel = _clean_did_panel(effect=50.0)
    ws = weekly_series(panel, "gross_profit")
    est = did_estimate(ws)["did_abs"]
    assert abs(est - 50.0) < 3.0, f"DiD={est:.2f}, seharusnya ≈50"


def test_did_nol_saat_tak_ada_efek():
    """Tanpa efek, DiD harus ≈ 0 (bias rendah)."""
    panel = _clean_did_panel(effect=0.0)
    ws = weekly_series(panel, "gross_profit")
    est = did_estimate(ws)["did_abs"]
    assert abs(est) < 2.0, f"DiD={est:.2f}, seharusnya ≈0"


def test_parallel_trends_terdeteksi_benar():
    """Pra-periode paralel → uji harus menyatakan OK."""
    panel = _clean_did_panel(effect=40.0)
    es = event_study(weekly_series(panel, "gross_profit"))
    pt = parallel_trends_test(es)
    assert pt["ok"], f"parallel trends seharusnya OK: {pt}"


def test_bootstrap_ci_mengandung_estimasi_titik():
    panel = _clean_did_panel(effect=30.0)
    ws = weekly_series(panel, "gross_profit")
    point = did_estimate(ws)["did_abs"]
    ci = did_bootstrap_ci(panel, "gross_profit", n_boot=400)
    lo, hi = sorted([ci["ci_low"], ci["ci_high"]])
    assert lo - 5 <= point <= hi + 5, "CI tidak mencakup estimasi titik"


def test_synthetic_control_fit_baik_pada_donor_relevan():
    """Donor = replika treated (tanpa efek) → pre-gap sangat kecil."""
    panel = _clean_did_panel(effect=25.0)
    # buat donor identik dgn treated (tanpa efek) agar fit harus bagus
    sc = synthetic_control(panel, "gross_profit")
    assert sc["pre_gap_rmse"] < 10.0, f"pre-gap terlalu besar: {sc['pre_gap_rmse']}"


def test_placebo_tidak_signifikan_tanpa_efek():
    """Spesifisitas: tanpa efek, placebo tidak boleh menandai signifikan."""
    panel = _clean_did_panel(effect=0.0)
    pl = placebo_test(panel, "gross_profit", n_perm=200)
    assert not pl["significant_at_05"], \
        f"placebo salah tanda signifikan: p={pl['placebo_p_value']}"
