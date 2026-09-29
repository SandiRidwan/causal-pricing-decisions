"""
test_decision_spec.py — audit SPEC & decision engine.

Memastikan ambang keputusan berperilaku sesuai spec (tidak ada overclaim):
efek merugi → HENTIKAN, CI lewat nol → bukan LAKUKAN, dst.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from decide import annualized_value, decide  # noqa: E402


def test_efek_negatif_signifikan_dihentikan():
    d = decide(effect_abs=-10, ci_low=-15, ci_high=-5, effect_pct=-20)
    assert d["tier"] == "HENTIKAN"


def test_efek_positif_signifikan_material_dilakukan():
    d = decide(effect_abs=10, ci_low=5, ci_high=15, effect_pct=8)
    assert d["tier"] == "LAKUKAN"


def test_ci_lewati_nol_bukan_lakukan():
    d = decide(effect_abs=10, ci_low=-2, ci_high=15, effect_pct=8)
    assert d["tier"] != "LAKUKAN", "CI lewat nol tak boleh LAKUKAN"


def test_efek_tidak_material_bukan_lakukan():
    d = decide(effect_abs=10, ci_low=5, ci_high=15, effect_pct=0.5)
    assert d["tier"] != "LAKUKAN", "efek < ambang tak boleh LAKUKAN"


def test_guardrail_margin_dilanggar():
    d = decide(effect_abs=10, ci_low=5, ci_high=15, effect_pct=8,
               margin_after=0.10)  # < 0.20
    assert d["tier"] != "LAKUKAN"
    assert not d["guardrail_ok"]


def test_annualized_value_rentang_konsisten():
    v = annualized_value(effect_abs=-10, ci_low=-15, ci_high=-5,
                         weeks_observed=20, n_units=100)
    assert v["annual_effect_low"] <= v["annual_effect_point"] <= \
        v["annual_effect_high"]
    assert v["scale_factor"] > 0


def test_justifikasi_selalu_ada():
    for eff in (-10, 10), (10, 0.3):
        d = decide(effect_abs=eff[0], ci_low=eff[1], ci_high=eff[0],
                   effect_pct=eff[1] * 10)
        assert d["reasons"], "keputusan tanpa justifikasi"
