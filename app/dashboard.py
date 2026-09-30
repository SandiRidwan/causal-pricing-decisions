"""
dashboard.py — Streamlit: Causal Pricing Decisions.

Menyajikan analisis kausal kebijakan harga:
KPI & keputusan · tren treated vs kontrol · event study (uji asumsi) ·
synthetic control · uji ketahanan · metodologi.

Data dibaca dari laporan JSON + marts (hasil pipeline). Setiap elemen
disertai narasi Kenapa-Tujuan-Dampak & kotak Insight+rekomendasi.
Jalankan: streamlit run app/dashboard.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import COLORS as C, DB_FILE, MARTS, POLICY, REPORTS  # noqa: E402
import explanations as X  # noqa: E402
import insights_content  # noqa: E402,F401
import insight as INS  # noqa: E402
import echarts_charts as EC  # noqa: E402

st.set_page_config(page_title="Causal Pricing Decisions", page_icon="🧪",
                   layout="wide")


def _src() -> str:
    if (REPORTS / "policy_report.json").exists():
        return "report"
    return "none"


def _need_data() -> bool:
    """Butuh bootstrap bila laporan ATAU panel (untuk chart) belum ada."""
    report_ok = (REPORTS / "policy_report.json").exists()
    panel_ok = (MARTS / "price_panel.parquet").exists() or DB_FILE.exists()
    return not (report_ok and panel_ok)


def _bootstrap_if_needed() -> None:
    """
    Self-bootstrap untuk deploy Cloud: bila laporan/panel belum ada
    (mis. data/ tidak ter-commit), jalankan pipeline SEKALI di sini.
    Di Cloud, katalog Morrisons mungkin tak tersedia → ingest otomatis
    memakai katalog sintetis cadangan (berlabel), sehingga app tetap jalan.
    """
    if not _need_data():
        return
    import subprocess
    with st.spinner("Menyiapkan data (menjalankan pipeline sekali, ~30–60 dtk)..."):
        r = subprocess.run([sys.executable, str(ROOT / "src" / "run_pipeline.py")],
                           cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0 and _src() == "none":
        st.error("Bootstrap pipeline gagal.")
        st.code((r.stderr or r.stdout)[-1500:], language="text")
        st.stop()


_bootstrap_if_needed()
_S = _src()
if _S == "none":
    st.error("Laporan belum ada. Jalankan: `python src/run_pipeline.py`")
    st.stop()


@st.cache_data(show_spinner="Membaca hasil analisis kausal...")
def load_report() -> dict:
    return json.loads((REPORTS / "policy_report.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner="Membaca panel...")
def load_mart(name: str) -> pd.DataFrame:
    if DB_FILE.exists():
        try:
            con = duckdb.connect(str(DB_FILE), read_only=True)
            df = con.execute(f"SELECT * FROM mart_{name}").df()
            con.close()
            return df
        except Exception:  # noqa: BLE001
            pass
    p = MARTS / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def style(fig, h=420):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=54, b=10),
                      paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#D5DBE1"),
                      title=dict(font=dict(size=16, color="#fff")),
                      legend=dict(bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(gridcolor="#2A3038", zeroline=False)
    fig.update_yaxes(gridcolor="#2A3038", zeroline=False)
    return fig


def kpi(col, label, value, sub, color):
    col.markdown(
        f"""<div style="background:#1A1F2B;border-left:4px solid {color};
        padding:14px 16px;border-radius:10px;height:124px;">
        <div style="color:#9AA7B4;font-size:.76rem;text-transform:uppercase;
        letter-spacing:.06em;">{label}</div>
        <div style="color:{color};font-size:1.55rem;font-weight:700;
        margin-top:6px;">{value}</div>
        <div style="color:#6B7885;font-size:.75rem;">{sub}</div></div>""",
        unsafe_allow_html=True)


rep = load_report()
did = rep["did"]
synth = rep["synthetic_control"]
boot = rep["bootstrap"]
placebo = rep["placebo"]
sens = rep["sensitivity"]
pt = rep["parallel_trends"]
cuped = rep["cuped"]
dec = rep["decision"]
truth = rep["ground_truth"]
val = rep["annualized_value"]

st.markdown(
    f"""<div style="background:linear-gradient(100deg,{C['primary']},{C['red']});
    padding:22px 26px;border-radius:14px;margin-bottom:18px;">
    <div style="font-size:1.7rem;font-weight:800;color:white;">
    🧪 Causal Pricing Decisions</div>
    <div style="color:#F3D9D4;font-size:.9rem;margin-top:4px;">
    Kebijakan harga/promo mana yang BENAR-BENAR menaikkan laba? · inferensi
    kausal (DiD · Synthetic Control · CUPED) + nilai uang · by
    <b>Sandi Ridwan</b></div></div>""",
    unsafe_allow_html=True)

# ---- KPI -----------------------------------------------------------------
X.render("kpi", st=st)
k1, k2, k3, k4 = st.columns(4)
tier = dec["decision"]["tier"]
tone = {"LAKUKAN": C["primary"], "UJI ULANG": C["accent"],
        "HENTIKAN": C["red"]}.get(tier, C["grey"])
kpi(k1, "Keputusan", f"{dec['decision']['badge']} {tier}",
    f"metode utama: {dec['primary_method']}", tone)
kpi(k2, "Efek laba kotor (synth)", f"{synth['effect_pct']:+.1f}%",
    f"ground-truth {truth['effect_on_gross_profit_pct_true']:+.1f}%", C["red"])
kpi(k3, "CI 95% (bootstrap)",
    f"[{boot['ci_low']:,.3f}, {boot['ci_high']:,.3f}]",
    "tak lewat 0 = nyata" if boot["excludes_zero"] else "melewati 0 = ragu",
    C["blue"])
kpi(k4, "Parallel trends", "OK" if pt["ok"] else "TIDAK",
    f"slope={pt['slope']:.3f} p={pt['p_value']:.2f}",
    C["primary"] if pt["ok"] else C["red"])
INS.box("kpi", st=st)
st.write("")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 DiD & Tren", "📉 Event Study", "🧬 Synthetic Control",
     "🛡️ Ketahanan & Keputusan", "🔬 Metodologi"])

# ============================================================ TAB 1 =========
with tab1:
    X.render("did", st=st)
    st.markdown("#### Laporan Difference-in-Differences")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("DiD (absolut, laba kotor)", f"{did['did_abs']:,.1f}")
        st.metric("DiD (% dari kontrol)", f"{did['did_pct_of_control']:+.2f}%")
    with c2:
        st.metric("Treated: pre → post",
                  f"{did['treated_pre']:,.0f} → {did['treated_post']:,.0f}")
        st.metric("Control: pre → post",
                  f"{did['control_pre']:,.0f} → {did['control_post']:,.0f}")

    # Sumber tren: utamakan event_study (kecil, ter-commit) agar chart selalu
    # muncul bahkan saat panel besar belum dibangun. Fallback ke panel.
    es_trend = load_mart("event_study")
    panel = load_mart("price_panel")
    ws = None
    if len(es_trend) and {"week", "treated", "control"} <= set(es_trend.columns):
        ws = es_trend[["week", "treated", "control"]].rename(
            columns={"treated": "Treated", "control": "Control"}).copy()
        _post = float(es_trend.loc[es_trend["is_post"], "week"].min())
    elif len(panel):
        ws = (panel.groupby(["week", "is_treated"])["gross_profit"].mean()
              .unstack().rename(columns={True: "Treated", False: "Control"})
              .reset_index())
        _post = float(panel.loc[panel["is_post"], "week"].min())
    if ws is not None and len(ws):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ws["week"], y=ws["Treated"], name="Treated",
                                 mode="lines+markers",
                                 line=dict(color=C["red"], width=2.6)))
        fig.add_trace(go.Scatter(x=ws["week"], y=ws["Control"], name="Control",
                                 mode="lines+markers",
                                 line=dict(color=C["blue"], width=2.6)))
        fig.add_vline(x=_post - 0.5, line_dash="dash",
                      line_color="#8B9AA6",
                      annotation_text="intervensi", annotation_font_size=10)
        style(fig, 440).update_layout(
            title="Laba kotor mingguan: Treated vs Control",
            xaxis_title="Minggu", yaxis_title="Laba kotor (agregat)")
        st.plotly_chart(fig, use_container_width=True)
    INS.box("did", st=st)

# ============================================================ TAB 2 =========
with tab2:
    X.render("event_study", st=st)
    es = load_mart("event_study")
    if len(es):
        fig = go.Figure()
        fig.add_hline(y=0, line_dash="dash", line_color="#8B9AA6")
        fig.add_vline(x=0, line_dash="dot", line_color="#E4A11B")
        fig.add_trace(go.Scatter(
            x=es["rel_week"], y=es["rel_effect"], mode="lines+markers",
            line=dict(color=C["purple"], width=2.6), name="efek relatif"))
        fig.add_trace(go.Bar(
            x=es["rel_week"], y=es["rel_effect"],
            marker_color=[C["grey"] if not p else C["red"] for p in es["is_post"]],
            opacity=0.35, name="pra / pasca"))
        style(fig, 440).update_layout(
            title="Event study — efek relatif per minggu (pra-intervensi harus ≈0)",
            xaxis_title="Minggu relatif terhadap intervensi",
            yaxis_title="Efek relatif (%)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Uji parallel trends: slope={pt['slope']:.3f}, "
                   f"p={pt['p_value']:.3f} → "
                   f"{'OK (tren paralel)' if pt['ok'] else 'PERINGATAN'}")
    INS.box("event_study", st=st)

# ============================================================ TAB 3 =========
with tab3:
    X.render("synthetic", st=st)
    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.metric("Efek synthetic control (% laba kotor)",
                  f"{synth['effect_pct']:+.2f}%")
        st.metric("Pre-gap RMSE (kualitas fit)",
                  f"{synth['pre_gap_rmse']:,.1f}",
                  help="Kecil = counterfactual cocok di pra-periode")
    with c2:
        st.metric("Jumlah donor", f"{synth['n_donors']}")
        st.metric("Kategori perlakuan", ", ".join(synth["treated_categories"]))
    st.markdown("**Bobot donor teratas (penyusun counterfactual):**")
    st.dataframe(pd.DataFrame(synth["weights_top"],
                              columns=["donor", "bobot"]),
                 use_container_width=True, hide_index=True)

    summary = load_mart("policy_summary")
    if len(summary):
        EC.pictorial_bar(
            categories=list(summary["method"]),
            values=[abs(float(v)) for v in summary["effect_pct"]],
            symbol="rect", title="Besar efek per metode (% laba kotor)",
            yname="|efek| (%)", height=340)
    INS.box("synthetic", st=st)

# ============================================================ TAB 4 =========
with tab4:
    X.render("robustness", st=st)
    st.markdown("#### Matriks ketahanan lintas metrik")
    sm = sens["by_metric"]
    dfm = pd.DataFrame([
        {"metrik": k, "DiD absolut": round(v["did_abs"], 2),
         "DiD %": round(v["did_pct"], 3)} for k, v in sm.items()])
    st.dataframe(dfm, use_container_width=True, hide_index=True)
    st.caption(
        f"Arah {'SAMA' if sens['same_direction_all_metrics'] else 'BERBEDA'} "
        f"di semua metrik · placebo p-value = {placebo['placebo_p_value']:.3f} "
        f"({'signifikan' if placebo['significant_at_05'] else 'TIDAK signifikan'})")

    X.render("decision", st=st)
    d = dec["decision"]
    st.markdown(
        f"""<div style="background:{'#14532d' if d['tier']=='LAKUKAN' else
        ('#78350f' if d['tier']=='UJI ULANG' else '#7f1d1d')};
        border-radius:12px;padding:18px 22px;">
        <div style="color:#fff;font-size:1.4rem;font-weight:800;">
        {d['badge']} KEPUTUSAN: {d['tier']}</div>
        <ul style="color:#E8EEF4;margin-top:10px;">
        {''.join(f'<li>{r}</li>' for r in d['reasons'])}</ul></div>""",
        unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    kpi(c1, "Efek material?", "Ya" if d["material"] else "Tidak",
        f"ambang {2.0:.0f}%", C["primary"] if d["material"] else C["grey"])
    kpi(c2, "CI lewat nol?", "Tidak" if d["excludes_zero"] else "Ya",
        "bukti kuat?" , C["primary"] if d["excludes_zero"] else C["red"])
    kpi(c3, "Guardrail margin", "Aman" if d["guardrail_ok"] else "Dilanggar",
        "ambang 20%", C["primary"] if d["guardrail_ok"] else C["red"])

    st.markdown("#### Nilai finansial tahunan (rentang, bukan titik)")
    st.write(
        f"Efek tahunan laba kotor: **{val['annual_effect_point']:,.0f}** "
        f"[{val['annual_effect_low']:,.0f}, {val['annual_effect_high']:,.0f}] "
        f"(satuan agregat). {val['note']}")
    INS.box("decision", st=st)
    INS.box("robustness", st=st)

# ============================================================ TAB 5 =========
with tab5:
    st.markdown("#### Alur pipeline")
    st.code("""
 Morrisons (katalog NYATA) ─┐
                            ├─► ingest.py ─► panel harian/mingguan (controlled)
 DGP terdokumentasi ────────┘        │
                                     ▼
        causal.py (DiD · Event study · Synthetic Control · CUPED ·
                   Bootstrap CI · Placebo · Sensitivity)
                                     │
                       decide.py ─► tier aksi + nilai uang
                                     │
              run_pipeline.py ─► DuckDB marts + policy_report.json
                                     │
                       dashboard.py · tests/
    """, language="text")
    st.markdown(
        "#### Metode & mengapa\n"
        "- **Difference-in-Differences** — estimasi efek dari data observasi; "
        "valid bila tren pra-periode paralel (diuji).\n"
        "- **Event study** — menguji asumsi parallel trends + dinamika efek.\n"
        "- **Synthetic Control** — counterfactual berbobot saat arm tak "
        "seimbang; metode utama di sini.\n"
        "- **CUPED** — kurangi varians dengan kovariat pra-periode.\n"
        "- **Bootstrap (block) CI** — interval yang menghormati korelasi unit.\n"
        "- **Placebo/permutation** — uji apakah efek bisa muncul dari kebetulan.\n"
        "- **Sensitivity lintas metrik** — memastikan kesimpulan tak rapuh.\n\n"
        f"CUPED: varians turun **{cuped['var_reduction_pct']:.1f}%** "
        f"(θ={cuped['theta']:.2f}).")
    st.markdown(
        "#### Batas jujur (lihat docs/LIMITATIONS.md)\n"
        "- Panel harga-waktu adalah **simulasi terkontrol** dengan ground-truth "
        "diketahui (untuk memvalidasi estimator), bukan data pasar nyata.\n"
        "- Katalog sumber NYATA (Morrisons, 11.208 produk) untuk struktur harga.\n"
        "- COGS tidak tersedia → margin kotor diasumsikan 30% (eksplisit).\n"
        "- Pasar nyata punya confounding tak teramati yang tidak dimodelkan.")

st.markdown(
    f"""<hr style="border-color:#2A3038;">
    <div style="color:#8B9AA6;font-size:.8rem;text-align:center;">
    🧪 Causal Pricing Decisions · katalog Morrisons (nyata) + panel terkontrol ·
    DiD · Synthetic Control · CUPED · oleh <b>Sandi Ridwan</b><br>
    Analisis edukasional. Keputusan harga nyata butuh konteks bisnis & data COGS asli.</div>""",
    unsafe_allow_html=True)
