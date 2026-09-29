"""
run_pipeline.py — orkestrasi end-to-end (satu perintah, hasil lengkap).

  ingest ──► kausal (DiD/Synth/CUPED/placebo) ──► decisions ($ + tier)
        ──► DuckDB (marts) ──► reports (JSON) ──► [dashboard membaca ini]

Jalankan:  python src/run_pipeline.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from causal import (cuped_adjust, did_bootstrap_ci, did_estimate, event_study,
                    parallel_trends_test, placebo_test, sensitivity,
                    synthetic_control, weekly_series)
from config import DB_FILE, MARTS, POLICY, REPORTS, SEED
from decide import annualized_value, policy_scorecard
from ingest import build_panel, load_catalog, save_raw

try:
    import duckdb
    _HAS_DUCKDB = True
except Exception:  # noqa: BLE001
    _HAS_DUCKDB = False


def _log(msg: str) -> None:
    print(f"[pipeline] {msg}")


def load_marts() -> None:
    """Tulis marts ke DuckDB (dipakai dashboard). Parquet sebagai fallback."""
    if not _HAS_DUCKDB:
        _log("duckdb tidak tersedia — marts hanya Parquet")
        return
    con = duckdb.connect(str(DB_FILE))
    for mart in ["price_panel", "event_study", "policy_summary"]:
        p = MARTS / f"{mart}.parquet"
        if p.exists():
            con.execute(f"CREATE OR REPLACE TABLE mart_{mart} AS "
                        f"SELECT * FROM read_parquet('{p.as_posix()}')")
    con.close()
    _log("marts dimuat ke DuckDB")


def run() -> dict:
    _log("1/6 ingest (katalog nyata + panel terkontrol)")
    catalog = load_catalog()
    panel, truth = build_panel()
    save_raw(panel, catalog)

    _log("2/6 agregasi & Difference-in-Differences")
    ws = weekly_series(panel, "gross_profit")
    did = did_estimate(ws)
    es = event_study(ws)
    pt = parallel_trends_test(es)

    _log("3/6 Synthetic Control")
    synth = synthetic_control(panel, "gross_profit")

    _log("4/6 inferensi: bootstrap CI, placebo, sensitivitas, CUPED")
    boot = did_bootstrap_ci(panel, "gross_profit", n_boot=1500)
    placebo = placebo_test(panel, "gross_profit", n_perm=800)
    sens = sensitivity(panel)
    cuped = cuped_adjust(panel, "gross_profit")

    _log("5/6 decision engine (nilai uang + tier)")
    scorecard = policy_scorecard(did, synth, boot, sens, placebo)
    val = annualized_value(synth["effect_abs"], boot["ci_low"], boot["ci_high"],
                           weeks_observed=int((~ws["is_post"]).sum() +
                                              ws["is_post"].sum()),
                           n_units=truth["n_units"])

    # ---- tulis marts ----
    es.to_parquet(MARTS / "event_study.parquet", index=False)
    pd.DataFrame([
        {"method": "DiD", "effect_pct": did["did_pct_of_control"],
         "effect_abs": did["did_abs"]},
        {"method": "Synthetic Control", "effect_pct": synth["effect_pct"],
         "effect_abs": synth["effect_abs"]},
    ]).to_parquet(MARTS / "policy_summary.parquet", index=False)
    panel.to_parquet(MARTS / "price_panel.parquet", index=False)

    # ---- laporan JSON (audit + dashboard) ----
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "policy": POLICY,
        "ground_truth": truth,
        "did": did,
        "parallel_trends": pt,
        "synthetic_control": synth,
        "bootstrap": boot,
        "placebo": placebo,
        "sensitivity": sens,
        "cuped": cuped,
        "decision": scorecard,
        "annualized_value": val,
    }
    (REPORTS / "policy_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")

    load_marts()

    _log("6/6 selesai")
    _log(f"  keputusan: {scorecard['decision']['tier']} "
         f"(metode utama: {scorecard['primary_method']})")
    _log(f"  efek laba kotor: DiD {did['did_pct_of_control']:+.2f}% | "
         f"Synth {synth['effect_pct']:+.2f}% | ground-truth "
         f"{truth['effect_on_gross_profit_pct_true']:+.2f}%")
    return report


if __name__ == "__main__":
    run()
