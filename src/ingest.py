"""
ingest.py — pengambilan & pembentukan data.

DUA SUMBER, DUA PERAN (jelas & jujur):
  1. `load_catalog()` → katalog ritel NYATA (Morrisons, 11.208 produk).
     Dipakai untuk analisis cross-sectional (elastisitas harga, struktur promo).
  2. `build_panel()` → panel harga-waktu mingguan dengan intervensi yang
     DIKETAHUI. Dibangun dari katalog nyata + mekanisme promo eksplisit.

MENGAPA PANEL DISIMULASIKAN (bukan diambil dari pasar)?
  Untuk MEMBUKTIKAN estimator kausal benar, kita butuh data yang efek
  sebenarnya (ground truth) DIKETAHUI. Data pasar nyata tidak memberi itu.
  Maka: kita tulis proses pembangkit data (DGP) yang transparan, lalu uji
  apakah DiD / Synthetic Control / CUPED memulihkan efek yang kita tanam.
  Ini praktik standar dalam ekonometrika (Monte Carlo study). Panel diberi
  label "controlled" agar tidak pernah disalahartikan sebagai pasar nyata.

DGP (proses pembangkit data) — eksplisit:
  · Baseline permintaan per unit = fungsi dari katalog nyata (harga, rating,
    kategori) → realistis, bukan angka acak.
  · Permintaan mengikuti elastisitas harga β (ditanam, mis. -1.4).
  · Intervensi: kategori terpilih dapat diskon `discount_pct` pada minggu
    `pre_weeks`..`pre_weeks+duration_weeks`.
  · Efek sebenarnya = kenaikan unit karena elastisitas × penurunan harga,
    DINETRALKAN oleh biaya diskon → efek BERSIH pada laba kotor diketahui.
  · Noise: musiman mingguan + noise unit (agar realistis & outlier muncul).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import (ASSUMED_GROSS_MARGIN, CATALOG_CSV, CATALOG_PARQUET,  # noqa
                    POLICY, RAW, SEED)

RNG = np.random.default_rng(SEED)


# ---------------------------------------------------------------- KATALOG ---
def _synthetic_catalog(n: int = 600) -> pd.DataFrame:
    """
    Katalog cadangan BILA katalog Morrisons tak tersedia (mis. di CI/cloud).
    JELAS berlabel sintetis — bukan data nyata. Dipakai hanya agar pipeline
    tetap reproducible di lingkungan tanpa akses ke repo katalog.
    """
    cats = ["Bakery & Cakes", "Drinks", "Beers, Wines & Spirits",
            "Fresh Foods", "Treats & Snacks", "Food Cupboard"]
    rng = np.random.default_rng(SEED)
    rows = []
    for i in range(n):
        cat = cats[i % len(cats)]
        price = round(float(np.clip(rng.lognormal(0.5, 0.6), 0.4, 14.0)), 2)
        rows.append({
            "product_id": f"SYN-{i:05d}", "name": f"Item {i}", "brand": "SYN",
            "category": cat, "price": price, "list_price": price,
            "discount_pct": 0.0, "is_promo": False,
            "rating": float(np.clip(rng.normal(4.0, 0.5), 1, 5)),
            "reviews": int(rng.integers(0, 120)),
        })
    return pd.DataFrame(rows)


def load_catalog() -> pd.DataFrame:
    """
    Muat katalog ritel nyata (Morrisons). Prioritas sumber:
      1) parquet ringkas yang di-bundle (Cloud-friendly)  → data/raw
      2) CSV penuh lokal (project morrisons-market-intelligence)
      3) katalog sintetis cadangan (BERLABEL) bila tak ada
    Kolom distandarkan: product_id, category, price, rating, reviews.
    """
    if CATALOG_PARQUET.exists():
        df = pd.read_parquet(CATALOG_PARQUET)
        df["category"] = df["category"].astype(str).str.strip()
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df["reviews"] = pd.to_numeric(df["reviews"], errors="coerce")
        return df.dropna(subset=["price"]).query("price > 0").reset_index(
            drop=True)

    if not CATALOG_CSV.exists():
        # fallback yang JUJUR: katalog sintetis berlabel, agar reproducible
        cat = _synthetic_catalog()
        cat["_synthetic"] = True
        return cat
    df = pd.read_csv(CATALOG_CSV, low_memory=False)
    # standarkan kolom yang dipakai
    keep = ["product_id", "name", "brand", "cat1", "effective_price",
            "list_price", "discount_pct", "is_promo", "rating", "reviews"]
    df = df[[c for c in keep if c in df.columns]].copy()
    df = df.rename(columns={"cat1": "category", "effective_price": "price"})
    df["category"] = df["category"].astype(str).str.strip()
    df["brand"] = df["brand"].astype(str).str.strip()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["reviews"] = pd.to_numeric(df["reviews"], errors="coerce")
    df = df.dropna(subset=["price"])
    df = df[df["price"] > 0]
    df = df[~df["category"].isin(["nan", ""])]
    return df.reset_index(drop=True)


# ------------------------------------------------------------------ PANEL ---
def _baseline_demand(cat: pd.DataFrame, elasticity: float) -> np.ndarray:
    """
    Permintaan mingguan dasar per SKU: turunkan dari harga & rating NYATA.
    Skala: unit dasar ~ 8..120 per minggu, dipengaruhi rating & popularitas.
    """
    base = 40.0 * np.exp(-elasticity * np.log1p(cat["price"].to_numpy()) / 4.0)
    pop = np.clip(np.nan_to_num(cat["reviews"].to_numpy()) / 50.0, 0.2, 3.0)
    rate = np.nan_to_num(cat["rating"].to_numpy(), nan=3.5) / 3.5
    demand = base * pop * rate
    return np.clip(demand, 4.0, 400.0)


def build_panel(n_treated_categories: int = 2) -> tuple[pd.DataFrame, dict]:
    """
    Bangun panel harga-waktu mingguan (controlled experiment).

    Returns
    -------
    panel : DataFrame kolom per config.OUTPUT_FIELDS
    truth : dict ground-truth (efek yang DITANAM) untuk verifikasi estimator.
    """
    cat = load_catalog()

    # pilih kategori perlakuan DIKETAHUI (deterministik) dari spec, fallback
    # ke kategori terbesar bila tak ada.
    hints = set(POLICY["treated_category_hint"])
    present = [c for c in cat["category"].unique() if c in hints]
    if len(present) < n_treated_categories:
        top = (cat["category"].value_counts().head(6).index.tolist())
        present = list(dict.fromkeys(present + top))[:n_treated_categories]
    treated = present[:n_treated_categories]

    # elastisitas NYATA yang ditanam (inilah "efek sebenarnya")
    elasticity = -1.40

    cat = cat.copy()
    cat["base_demand"] = _baseline_demand(cat, elasticity)
    cat["unit_cost"] = cat["price"] * (1.0 - ASSUMED_GROSS_MARGIN)

    pre = POLICY["pre_weeks"]
    dur = POLICY["duration_weeks"]
    post = POLICY["post_weeks"]
    total_weeks = pre + dur + post
    weeks = list(range(total_weeks))

    # musiman mingguan (pola halus, sama untuk semua unit → netral utk DiD)
    seasonal = 1.0 + 0.06 * np.sin(np.array(weeks) * 2 * np.pi / 13.0)

    rows = []
    for r in cat.itertuples():
        is_treated = r.category in treated
        for w in weeks:
            is_post = w >= pre
            is_active = pre <= w < pre + dur      # promo sedang berjalan
            # harga dasar; promo menurunkan harga pada unit terpilih
            price = r.price
            disc = 0.0
            if is_treated and is_active:
                disc = POLICY["discount_pct"]
                price = r.price * (1 - disc / 100.0)
            # permintaan: elastisitas harga + musiman + noise unit
            ratio = price / r.price
            demand = r.base_demand * (ratio ** elasticity) * seasonal[w]
            noise = RNG.normal(1.0, 0.10)
            units = max(0.0, demand * noise)
            revenue = units * price
            gp = units * (price - r.unit_cost)
            rows.append((POLICY["name"], r.product_id, r.category, w, w,
                         is_treated, is_post, round(price, 4),
                         round(units, 3), round(revenue, 4),
                         round(gp, 4), disc))

    panel = pd.DataFrame(rows, columns=[
        "policy", "unit_id", "category", "period", "week",
        "is_treated", "is_post", "price", "units_sold", "revenue",
        "gross_profit", "discount_pct"])

    # ---- ground truth: efek yang BENAR-BENAR ada (di data, bukan estimasi) --
    tw = panel[(panel.is_treated) & (panel.is_post)]
    cw = panel[(~panel.is_treated) & (panel.is_post)]
    truth = {
        "elasticity_true": elasticity,
        "treated_categories": treated,
        "discount_pct": POLICY["discount_pct"],
        "effect_on_units_pct_true": float(
            ((POLICY["discount_pct"] / 100.0) * -elasticity) * 100.0),
        "treated_gp_post_mean": float(tw["gross_profit"].mean()),
        "control_gp_post_mean": float(cw["gross_profit"].mean()),
        "effect_on_gross_profit_pct_true": float(
            (tw["gross_profit"].mean() - cw["gross_profit"].mean())
            / cw["gross_profit"].mean() * 100.0),
        "n_units": int(panel["unit_id"].nunique()),
        "n_weeks": int(total_weeks),
    }
    return panel, truth


def save_raw(panel: pd.DataFrame, catalog: pd.DataFrame) -> None:
    panel.to_parquet(RAW / "price_panel.parquet", index=False)
    catalog.to_parquet(RAW / "retail_catalog.parquet", index=False)


if __name__ == "__main__":
    _cat = load_catalog()
    _panel, _truth = build_panel()
    save_raw(_panel, _cat)
    print(f"catalog: {_cat.shape} | panel: {_panel.shape}")
    print("ground truth:", {k: round(v, 3) if isinstance(v, float) else v
                            for k, v in _truth.items()})
