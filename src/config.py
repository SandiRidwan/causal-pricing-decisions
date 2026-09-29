"""
config.py — SATU SUMBER KEBENARAN (path, spec, konstanta, parameter statistik).

Project : Causal Pricing Decisions
Peran   : menjawab "kebijakan harga/promo mana yang BENAR-BENAR menaikkan
          profit?" dengan inferensi KAUSAL (bukan korelasi) + nilai uang.

DATA (kejujuran dulu — baca ini):
  · `retail_catalog`  = data NYATA Morrisons (11.208 produk, harga, promo,
    rating) — dipakai untuk analisis cross-sectional & estimasi elastisitas.
  · `price_panel`     = panel harga-waktu mingguan yang DIBANGUN dari katalog
    nyata dengan mekanisme promo yang EKSPLISIT dan diketahui. Panel ini
    dipakai untuk menguji estimator kausal (DiD/Synthetic Control) terhadap
    efek yang BENAR-BENAR ADA (ground truth diketahui). Ini adalah
    SIMULASI TERKONTROL, bukan data observasi pasar — dan itu disengaja:
    tanpa ground truth, kita tidak bisa membuktikan estimator-nya benar.

Spec metrik & ambang keputusan didefinisikan di sini agar dapat diaudit
(lihat docs/SPEC.md dan src/spec_audit.py).
"""

from __future__ import annotations

from pathlib import Path

# ---- Path -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
STAGING = DATA / "staging"
MARTS = DATA / "marts"
DB = ROOT / "db"
SQL = ROOT / "sql"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
DOCS = ROOT / "docs"

for _p in (RAW, STAGING, MARTS, DB, SQL, REPORTS, FIGURES, DOCS):
    _p.mkdir(parents=True, exist_ok=True)

DB_FILE = DB / "causal_pricing.duckdb"

# ---- Sumber NYATA ----------------------------------------------------------
# Katalog ritel Morrisons (dipakai ulang dari project morrisons-market-
# intelligence agar tidak scraping ulang; berasal dari groceries.morrisons.com).
MORRISONS_CSV = (ROOT.parent / "morrisons-market-intelligence" / "data" /
                 "processed" / "morrisons_clean.csv")

# ---- Palet warna (konsisten dengan portofolio lain) ------------------------
COLORS = {
    "primary": "#1F5C3D", "accent": "#E4A11B", "blue": "#2E6F95",
    "red": "#C0392B", "purple": "#6A4C93", "teal": "#2A9D8F",
    "grey": "#8B9AA6", "control": "#2E6F95", "treatment": "#C0392B",
    "treated": "#C0392B", "synthetic": "#2E6F95",
}

# ---- Parameter statistik ---------------------------------------------------
ALPHA = 0.05                 # tingkat signifikansi
POWER = 0.80                 # target power
N_BOOTSTRAP = 2000           # iterasi bootstrap
N_PERMUTATION = 2000         # iterasi placebo/permutation test
SEED = 42

# ---- Definisi intervensi (spec kebijakan harga) ----------------------------
# Kebijakan yang diuji: "Diskon X% untuk kategori P selama T minggu".
POLICY = {
    "name": "Diskon Terarah Kategori (Targeted Category Discount)",
    "treated_category_hint": ["Bakery & Cakes", "Drinks",
                              "Beers, Wines & Spirits"],
    "discount_pct": 15.0,          # kedalaman diskon yang diuji
    "duration_weeks": 8,           # lama intervensi
    "pre_weeks": 12,               # periode pra-intervensi (baseline)
    "post_weeks": 12,              # periode pasca-intervensi (efek jangka pj)
}

# ---- Metrik keputusan (spec) -----------------------------------------------
# Setiap metrik punya: tipe, arah, dan PERAN dalam keputusan (utama/penjaga).
METRICS = {
    "units_sold":   {"tipe": "hitung",  "peran": "utama",
                     "label": "Unit terjual",
                     "arah": "lebih tinggi lebih baik"},
    "revenue":      {"tipe": "uang",    "peran": "sekunder",
                     "label": "Pendapatan (revenue)"},
    "gross_profit": {"tipe": "uang",    "peran": "UTAMA (keputusan)",
                     "label": "Laba kotor (gross profit)",
                     "arah": "lebih tinggi lebih baik"},
    "margin_pct":   {"tipe": "rasio",   "peran": "penjaga (guardrail)",
                     "label": "Margin (%)",
                     "arah": "jangan turun di bawah ambang"},
}

# ---- Ambang keputusan (spec) -----------------------------------------------
# Dipakai decision engine untuk memetakan estimasi + CI ke TIER AKSI.
DECISION = {
    "min_periods_pre": 8,        # minimal titik pra-intervensi (paralel trend)
    "min_periods_post": 6,       # minimal titik pasca
    "min_donor_units": 3,        # minimal unit donor untuk synthetic control
    "guardrail_margin_floor": 0.20,   # margin tidak boleh < 20% (relatif ke base)
    "payback_weeks_max": 12,     # investasi diskon harus balik <= 12 minggu
    "ci_must_exclude_zero": True,     # klaim "berhasil" wajib CI tak lewati 0
    "min_effect_pct": 2.0,       # efek minimal dianggap MATERIAL (% laba kotor)
}

# ---- Biaya unit (untuk gross profit) ---------------------------------------
# Margin kotor per unit: kita tidak punya COGS asli, jadi pakai ASUMSI EKSPLISIT
# (diakui sebagai batas di docs/LIMITATIONS.md). Default 30% margin.
ASSUMED_GROSS_MARGIN = 0.30

# ---- Skema output (kontrak kolom, untuk validasi & audit) -------------------
OUTPUT_FIELDS = [
    "policy", "unit_id", "category", "period", "week",
    "is_treated", "is_post", "price", "units_sold", "revenue",
    "gross_profit", "discount_pct",
]
