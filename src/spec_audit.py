"""spec_audit.py — audit kepatuhan terhadap SPEC (dijalankan di CI).

Memeriksa bahwa output pipeline memenuhi kontrak: kolom lengkap, metrik
terdefinisi, keputusan punya justifikasi, dan angka dalam rentang wajar.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import DECISION, METRICS, OUTPUT_FIELDS, REPORTS  # noqa: E402


def audit() -> tuple[bool, list[str]]:
    issues: list[str] = []
    rep_path = REPORTS / "policy_report.json"
    if not rep_path.exists():
        return False, ["policy_report.json tidak ada — jalankan run_pipeline"]

    rep = json.loads(rep_path.read_text(encoding="utf-8"))

    # 1. kunci wajib
    for key in ["did", "synthetic_control", "bootstrap", "placebo",
                "sensitivity", "decision", "ground_truth"]:
        if key not in rep:
            issues.append(f"bagian '{key}' hilang dari laporan")

    # 2. keputusan punya justifikasi & tier valid
    dec = rep.get("decision", {}).get("decision", {})
    if dec.get("tier") not in {"LAKUKAN", "UJI ULANG", "HENTIKAN"}:
        issues.append(f"tier tak valid: {dec.get('tier')}")
    if not dec.get("reasons"):
        issues.append("keputusan tanpa justifikasi")

    # 3. metrik keputusan terdefinisi
    if "gross_profit" not in METRICS:
        issues.append("metrik keputusan gross_profit tak terdefinisi")

    # 4. angka dalam rentang wajar
    ci = rep.get("bootstrap", {})
    if ci and ci.get("ci_low") is not None and ci.get("ci_high") is not None:
        if ci["ci_low"] > ci["ci_high"]:
            issues.append("CI terbalik (low > high)")

    # 5. ground truth dilaporkan (transparansi)
    if "effect_on_gross_profit_pct_true" not in rep.get("ground_truth", {}):
        issues.append("ground-truth tidak dilaporkan")

    # 6. ambang keputusan terdefinisi
    for k in ["min_effect_pct", "guardrail_margin_floor",
              "ci_must_exclude_zero"]:
        if k not in DECISION:
            issues.append(f"ambang keputusan '{k}' tak terdefinisi")

    return (len(issues) == 0), issues


if __name__ == "__main__":
    ok, problems = audit()
    if ok:
        print("SPEC AUDIT: LULUS (semua kontrak terpenuhi)")
    else:
        print("SPEC AUDIT: GAGAL")
        for p in problems:
            print("  -", p)
    sys.exit(0 if ok else 1)
