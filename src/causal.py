"""
causal.py — ESTIMATOR KAUSAL yang benar & dapat diaudit (inti project).

Menyediakan:
  · Difference-in-Differences (DiD) klasik (2×2) + regresi interaksi
  · Event study (efek per minggu, uji parallel-trends pra-periode)
  · Synthetic Control (bobot donor optimal → counterfactual)
  · CUPED (variance reduction dengan kovariat pra-periode)
  · Bootstrap CI & placebo/permutation test (inferensi yang jujur)
  · Analisis sensitivitas (seberapa kuat asumsi bisa dilanggar)

PRINSIP (sama seperti portofolio lain — kejujuran dulu):
  · Setiap estimasi disertai interval kepercayaan; efek kecil tidak
    disebut "berhasil" hanya karena p<0.05.
  · Asumsi diuji, bukan diandaikan: parallel-trends pada pra-periode,
    placebo test pada unit kontrol, robustness lintas spesifikasi.
  · Bila estimasi ≠ ground truth, katakan — jangan dipoles.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

from config import ALPHA, DECISION, N_BOOTSTRAP, N_PERMUTATION, POWER, SEED

RNG = np.random.default_rng(SEED)


# ============================================================ AGGREGASI ======
def weekly_series(panel: pd.DataFrame, metric: str = "gross_profit",
                  group: str = "arm") -> pd.DataFrame:
    """
    Agregasi mingguan per grup (arm = treated/control).
    Memakai MEAN (bukan sum) agar DiD mengukur efek per-unit yang sebenarnya —
    sum akan mendilusi efek oleh jumlah unit per arm yang tak seimbang.
    Mengembalikan kolom: week, is_post, treated, control.
    """
    g = (panel.groupby(["week", "is_treated"])[metric].mean().unstack())
    g = g.rename(columns={True: "treated", False: "control"})
    g = g.reset_index().sort_values("week")
    g["is_post"] = g["week"] >= _pre_weeks(panel)
    return g


def _pre_weeks(panel: pd.DataFrame) -> int:
    """Jumlah minggu pra-intervensi (dari data: minggu pertama is_post)."""
    post_weeks = panel.loc[panel["is_post"], "week"]
    return int(post_weeks.min()) if len(post_weeks) else 0


# ================================================================ DID =======
def did_estimate(series: pd.DataFrame) -> dict:
    """
    Difference-in-Differences 2×2 pada seri agregat mingguan.

        DiD = (Ȳ_treated,post − Ȳ_treated,pre) − (Ȳ_control,post − Ȳ_control,pre)

    Parallel trends diuji terpisah via `event_study`.
    """
    pre = series[~series["is_post"]]
    post = series[series["is_post"]]

    def mean(df, col):
        return float(df[col].mean()) if len(df) else float("nan")

    t_pre, t_post = mean(pre, "treated"), mean(post, "treated")
    c_pre, c_post = mean(pre, "control"), mean(post, "control")
    did = (t_post - t_pre) - (c_post - c_pre)
    base = c_post if c_post else float("nan")
    return {
        "did_abs": did,
        "did_pct_of_control": (did / base * 100.0) if base else float("nan"),
        "treated_pre": t_pre, "treated_post": t_post,
        "control_pre": c_pre, "control_post": c_post,
        "n_pre": int(len(pre)), "n_post": int(len(post)),
    }


def did_bootstrap_ci(panel: pd.DataFrame, metric: str = "gross_profit",
                     n_boot: int = N_BOOTSTRAP, alpha: float = ALPHA) -> dict:
    """
    CI untuk DiD via bootstrap pada UNIT (block bootstrap) — menghormati
    korelasi dalam unit, bukan pada baris. Ini standar yang benar.
    Dioptimalkan: agregasi per (unit, arm, post) sekali, lalu resample vektor.
    """
    # ringkas: satu baris per (unit_id, is_treated, is_post) → mean metrik
    agg = (panel.groupby(["unit_id", "is_treated", "is_post"])[metric]
           .mean().reset_index())
    codes = agg["unit_id"].astype("category").cat.codes.to_numpy()
    n_units = codes.max() + 1
    val = agg[metric].to_numpy(dtype=float)
    trt = agg["is_treated"].to_numpy()
    post = agg["is_post"].to_numpy()

    est = np.empty(n_boot)
    for b in range(n_boot):
        pick = RNG.integers(0, n_units, size=n_units)
        mask = np.isin(codes, pick)
        v, t, p = val[mask], trt[mask], post[mask]
        # perubahan per arm (mean pre → post) ditimbang bootstrap
        try:
            td = v[(t) & (p)].mean() - v[(t) & (~p)].mean()
            cd = v[(~t) & (p)].mean() - v[(~t) & (~p)].mean()
        except (IndexError, RuntimeWarning):
            continue
        est[b] = td - cd
    est = est[np.isfinite(est)]
    lo, hi = np.percentile(est, [alpha / 2 * 100, (1 - alpha / 2) * 100])
    return {"boot_mean": float(est.mean()), "ci_low": float(lo),
            "ci_high": float(hi), "n_boot": int(len(est)),
            "excludes_zero": bool(lo > 0 or hi < 0)}


# ========================================================= EVENT STUDY ======
def event_study(series: pd.DataFrame) -> pd.DataFrame:
    """
    Efek relatif per minggu (treated − control, dinormalisasi ke minggu 0
    pra-periode). Pra-periode ≈ 0 → parallel trends wajar.
    """
    df = series.copy()
    base_week = int(df[~df["is_post"]]["week"].max()) if (~df["is_post"]).any() \
        else int(df["week"].min())
    ref = df[df["week"] == base_week]
    t0 = float(ref["treated"].iloc[0]) if len(ref) else 0.0
    c0 = float(ref["control"].iloc[0]) if len(ref) else 1.0
    df["treated_idx"] = df["treated"] / t0 if t0 else 1.0
    df["control_idx"] = df["control"] / c0 if c0 else 1.0
    df["rel_effect"] = (df["treated_idx"] - df["control_idx"]) * 100.0
    df["rel_week"] = df["week"] - base_week
    return df[["week", "rel_week", "is_post", "treated", "control",
               "treated_idx", "control_idx", "rel_effect"]]


def parallel_trends_test(es: pd.DataFrame) -> dict:
    """
    Uji tren pra-periode: kemiringan efek relatif pra-intervensi.
    |slope| kecil & p besar → parallel trends masuk akal.
    """
    pre = es[~es["is_post"]]
    if len(pre) < 3:
        return {"slope": float("nan"), "p_value": float("nan"),
                "ok": False, "note": "titik pra-periode kurang"}
    lr = sps.linregress(pre["rel_week"], pre["rel_effect"])
    return {"slope": float(lr.slope), "p_value": float(lr.pvalue),
            "ok": bool(abs(lr.slope) < 1.0 and lr.pvalue > 0.05),
            "note": "slope kecil & tak signifikan = tren paralel"}


# ===================================================== SYNTHETIC CONTROL ====
def synthetic_control(panel: pd.DataFrame, metric: str = "gross_profit",
                      max_donors: int = 60) -> dict:
    """
    Synthetic Control: bangun counterfactual unit perlakuan dari kombinasi
    berbobot unit donor (belum-terpapar), bobot dioptimalkan pada pra-periode.
    Dipakai untuk menaksir efek ketika DiD 2-grup kurang meyakinkan.

    Di sini: agregat per kategori. Kategori perlakuan disintesis dari
    kategori donor terpilih; bobot = non-negatif, jumlah 1 (grid + proyeksi).
    """
    cat_week = (panel.groupby(["category", "week", "is_treated"])[metric]
                .mean().reset_index())
    treated_cats = sorted(panel.loc[panel.is_treated, "category"].unique())
    donor_cats = sorted(panel.loc[~panel.is_treated, "category"].unique())[:max_donors]
    pre_weeks = _pre_weeks(panel)

    piv = cat_week.pivot_table(index="week", columns="category",
                               values=metric, aggfunc="mean").sort_index()
    pre_idx = [w for w in piv.index if w < pre_weeks]

    # target = rata-rata kategori perlakuan (gabung)
    target = piv[treated_cats].mean(axis=1)
    donors = piv[donor_cats]
    X_pre = donors.loc[pre_idx].to_numpy()
    y_pre = target.loc[pre_idx].to_numpy()

    # bobot non-negatif via least squares + clip (pendekatan sederhana & stabil)
    w, *_ = np.linalg.lstsq(X_pre, y_pre, rcond=None)
    w = np.clip(w, 0, None)
    w = w / w.sum() if w.sum() > 0 else np.ones_like(w) / len(w)
    synth = donors.to_numpy() @ w

    # efek pasca = target − synthetic
    post_idx = [w_ for w_ in piv.index if w_ >= pre_weeks]
    eff_post = (target.loc[post_idx] - pd.Series(synth, index=piv.index)
                .loc[post_idx])
    pre_gap = (target.loc[pre_idx] - pd.Series(synth, index=piv.index)
               .loc[pre_idx])
    base = float(pd.Series(synth, index=piv.index).loc[post_idx].mean())
    return {
        "effect_abs": float(eff_post.mean()),
        "effect_pct": float(eff_post.mean() / base * 100.0) if base else float("nan"),
        "pre_gap_rmse": float(np.sqrt((pre_gap ** 2).mean())),
        "pre_gap_mean": float(pre_gap.mean()),
        "n_donors": int(len(donor_cats)),
        "weights_top": sorted(
            [(donor_cats[i], round(float(w[i]), 3)) for i in np.argsort(w)[::-1][:5]],
            key=lambda x: -x[1]),
        "treated_categories": treated_cats,
    }


# ================================================================ CUPED =====
def cuped_adjust(panel: pd.DataFrame, metric: str = "gross_profit",
                 covariate: str = "units_sold") -> dict:
    """
    CUPED: kurangi varians memakai kovariat PRA-periode (units pra-intervensi).
    Y_adj = Y − θ·(X − X̄), θ = Cov(Y,X)/Var(X).
    Di sini X = rata-rata metrik pra-periode per unit.
    """
    pre = (panel[~panel.is_post].groupby("unit_id")[covariate].mean()
           .rename("x_pre"))
    post = (panel[panel.is_post].groupby(["unit_id", "is_treated"])[metric]
            .mean().reset_index().merge(pre, on="unit_id", how="inner"))
    if len(post) < 10:
        return {"ok": False, "note": "data pra/periode kurang"}
    x, y = post["x_pre"].to_numpy(), post[metric].to_numpy()
    theta = float(np.cov(y, x)[0, 1] / np.var(x)) if np.var(x) > 0 else 0.0
    post["y_adj"] = y - theta * (x - x.mean())

    def diff(col):
        t = post.loc[post.is_treated, col]
        c = post.loc[~post.is_treated, col]
        return float(t.mean() - c.mean())

    raw = diff(metric)
    adj = diff("y_adj")
    var_raw = float(post[metric].var())
    var_adj = float(post["y_adj"].var())
    return {
        "ok": True, "theta": theta,
        "effect_raw": raw, "effect_cuped": adj,
        "var_reduction_pct": (1 - var_adj / var_raw) * 100.0 if var_raw else 0.0,
    }


# ========================================================= PLACEBO / PERM ===
def placebo_test(panel: pd.DataFrame, metric: str = "gross_profit",
                 n_perm: int = N_PERMUTATION) -> dict:
    """
    Placebo/permutation: acak label perlakuan antar-KATEGORI, ulang DiD.
    p-value = proporsi placebo ≥ efek nyata (dua sisi). Uji apakah efek
    bisa muncul dari kebetulan struktur kategori.
    """
    cats = panel["category"].unique()
    real_treated = set(panel.loc[panel.is_treated, "category"].unique())
    real = abs(did_estimate(weekly_series(panel, metric)).get("did_abs", np.nan))

    # pra-hitung metrik per kategori×post untuk kecepatan
    agg = (panel.groupby(["category", "is_post"])[metric].sum().unstack())
    drew = []
    for _ in range(min(n_perm, 500)):
        perm = RNG.choice(cats, size=len(real_treated), replace=False)
        t_post = agg.loc[agg.index.isin(perm), True].sum()
        t_pre = agg.loc[agg.index.isin(perm), False].sum()
        c_post = agg.loc[~agg.index.isin(perm), True].sum()
        c_pre = agg.loc[~agg.index.isin(perm), False].sum()
        did = (t_post - t_pre) - (c_post - c_pre)
        drew.append(abs(did))
    drew = np.array(drew)
    p = float((drew >= real).mean()) if len(drew) else float("nan")
    return {"real_abs_did": float(real), "placebo_p_value": p,
            "n_perm": int(len(drew)), "significant_at_05": bool(p < ALPHA)}


# ======================================================= SENSITIVITY ========
def sensitivity(panel: pd.DataFrame, metric: str = "gross_profit") -> dict:
    """
    Seberapa sensitif kesimpulan terhadap pilihan metrik & asumsi?
    Hitung DiD pada 3 metrik; bila arah/kesimpulan berubah → rapuh.
    """
    out = {}
    for m in ["units_sold", "revenue", "gross_profit"]:
        d = did_estimate(weekly_series(panel, m))
        out[m] = {"did_abs": d["did_abs"], "did_pct": d["did_pct_of_control"]}
    signs = [np.sign(v["did_abs"]) for v in out.values()]
    robust = len(set(signs)) == 1
    return {"by_metric": out, "same_direction_all_metrics": bool(robust)}
