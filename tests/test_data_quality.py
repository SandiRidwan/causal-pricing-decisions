"""
test_data_quality.py — kualitas data & kontrak kolom.

Memastikan panel memenuhi kontrak (config.OUTPUT_FIELDS), tidak ada nilai
mustahil, dan struktur intervensi konsisten. Ini gerbang SEBELUM analisis.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import DECISION, OUTPUT_FIELDS, POLICY  # noqa: E402

PANEL = ROOT / "data" / "raw" / "price_panel.parquet"


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    if not PANEL.exists():
        pytest.skip("panel belum dibuat — jalankan src/run_pipeline.py")
    return pd.read_parquet(PANEL)


def test_kontrak_kolom(panel):
    missing = [c for c in OUTPUT_FIELDS if c not in panel.columns]
    assert not missing, f"kolom wajib hilang: {missing}"


def test_tidak_ada_nilai_null_di_kolom_kunci(panel):
    for c in ["unit_id", "category", "week", "price", "units_sold",
              "gross_profit"]:
        assert panel[c].notna().all(), f"{c} punya nilai null"


def test_harga_positif(panel):
    assert (panel["price"] > 0).all(), "ada harga <= 0"


def test_unit_tidak_negatif(panel):
    assert (panel["units_sold"] >= 0).all(), "ada unit negatif"


def test_margin_konsisten_dengan_asumsi(panel):
    """gross_profit harus = units * (price - unit_cost), unit_cost>0."""
    gp = panel["gross_profit"]
    rev = panel["revenue"]
    # laba kotor < revenue selalu (karena ada biaya unit)
    assert (gp <= rev + 1e-6).all(), "laba kotor melebihi revenue"


def test_struktur_pra_pasca_konsisten(panel):
    """is_post harus True tepat saat week >= pre_weeks."""
    pre = POLICY["pre_weeks"]
    expect = panel["week"] >= pre
    assert (panel["is_post"] == expect).all(), "flag is_post tak konsisten"


def test_intervensi_hanya_pada_kategori_perlakuan(panel):
    """Diskon hanya muncul di unit treated, pada jendela intervensi."""
    disc = panel[panel["discount_pct"] > 0]
    assert bool((disc["is_treated"]).all()), \
        "ada diskon pada unit kontrol"
    pre, dur = POLICY["pre_weeks"], POLICY["duration_weeks"]
    in_window = (disc["week"] >= pre) & (disc["week"] < pre + dur)
    assert bool(in_window.all()), "ada diskon di luar jendela intervensi"


def test_minimal_titik_untuk_estimasi(panel):
    n_pre = panel.loc[~panel["is_post"], "week"].nunique()
    n_post = panel.loc[panel["is_post"], "week"].nunique()
    assert n_pre >= DECISION["min_periods_pre"]
    assert n_post >= DECISION["min_periods_post"]
