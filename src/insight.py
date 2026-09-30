"""
insight.py — kotak 'Insight & Rekomendasi' untuk bawah setiap chart.

Pola wajib portofolio:
  · KESIMPULAN   — "dari chart ini kita bisa simpulkan ..."
  · REKOMENDASI  — tindakan konkret seolah kita PEMILIK data (agar hasil ideal)
  · RISIKO       — apa yang terjadi bila diabaikan / salah tafsir

DUA FORMAT REKOMENDASI (backward-compatible):
  1. Ringkas (lama):  rekomendasi=["aksi 1", "aksi 2"]
  2. Kaya (v2):       rekomendasi=[
                          {"aksi": "...",
                           "langkah": ["langkah 1", "langkah 2"],
                           "metrik": "cara mengukur keberhasilan",
                           "pemilik": "siapa yang mengeksekusi"},
                      ]
     Format kaya direkomendasikan: setiap rekomendasi dapat dieksekusi,
     punya langkah detail, metrik sukses terukur, dan penanggung jawab jelas.
"""

from __future__ import annotations

from typing import Any

INSIGHTS: dict[str, dict] = {}


def register(key: str, kesimpulan: str,
             rekomendasi: list[Any],
             risiko: str, tingkat: str = "sedang") -> None:
    """
    Daftarkan insight untuk sebuah key chart.

    `rekomendasi` menerima DUA bentuk (boleh campur):
      · str            → bullet ringkas (lama)
      · dict           → {aksi, langkah:[...], metrik, pemilik} (kaya)

    `langkah` boleh berupa list[str] (bullet) atau list[dict]
    {langkah, metrik} untuk detail per-langkah.
    """
    INSIGHTS[key] = {
        "kesimpulan": kesimpulan,
        "rekomendasi": rekomendasi,
        "risiko": risiko,
        "tingkat": tingkat,
    }


_TONE = {
    "kritis": ("#7f1d1d", "#fca5a5", "🔴 KRITIS"),
    "tinggi": ("#78350f", "#fcd34d", "🟠 PERHATIAN"),
    "sedang": ("#1e3a5f", "#93c5fd", "🔵 INSIGHT"),
    "rendah": ("#14532d", "#86efac", "🟢 SEHAT"),
}


def _fmt_rec(r: Any) -> str:
    """Render satu rekomendasi (str ringkas ATAU dict kaya) ke HTML."""
    if isinstance(r, str):
        return f"<li>{r}</li>"

    aksi = r.get("aksi", "")
    langkah = r.get("langkah", []) or []
    metrik = r.get("metrik", "")
    pemilik = r.get("pemilik", "")

    steps_html = ""
    if langkah:
        items = []
        for s in langkah:
            if isinstance(s, dict):
                txt = s.get("langkah", "")
                mt = s.get("metrik", "")
                extra = (f' <span style="color:#93c5fd;">[{mt}]</span>'
                         if mt else "")
                items.append(f"<li>{txt}{extra}</li>")
            else:
                items.append(f"<li>{s}</li>")
        steps_html = (
            '<ol style="margin:4px 0 6px 18px;color:#D7DEE6;font-size:.85rem;'
            'line-height:1.5;">' + "".join(items) + "</ol>")

    meta = []
    if metrik:
        meta.append(f'<span style="color:#86efac;">📊 Metrik: {metrik}</span>')
    if pemilik:
        meta.append(f'<span style="color:#fcd34d;">👤 Pemilik: {pemilik}</span>')
    meta_html = ("<div style=\"margin-top:4px;font-size:.8rem;\">"
                 + " &nbsp;·&nbsp; ".join(meta) + "</div>") if meta else ""

    return (f'<li style="margin-bottom:8px;"><b>{aksi}</b>'
            f"{steps_html}{meta_html}</li>")


def box(key: str, st=None) -> None:
    """Render kotak 'Insight & Rekomendasi' di Streamlit."""
    if st is None:
        import streamlit as st  # noqa
    ins = INSIGHTS.get(key)
    if not ins:
        return
    bg, fg, badge = _TONE.get(ins.get("tingkat", "sedang"), _TONE["sedang"])
    recs = "".join(_fmt_rec(r) for r in ins["rekomendasi"])
    st.markdown(
        f"""
        <div style="background:{bg};border-left:5px solid {fg};
        padding:16px 20px;border-radius:10px;margin:6px 0 18px 0;">
          <div style="color:{fg};font-weight:800;font-size:.82rem;
          letter-spacing:.08em;margin-bottom:8px;">{badge} · INSIGHT &amp;
          REKOMENDASI</div>
          <div style="color:#E8EEF4;font-size:.92rem;margin-bottom:10px;">
          <b>Kesimpulan.</b> {ins['kesimpulan']}</div>
          <div style="color:#CBD5E1;font-size:.88rem;">
          <b>Rekomendasi tindakan:</b>
          <ul style="margin:6px 0 10px 18px;">{recs}</ul></div>
          <div style="color:#f0b8b8;font-size:.84rem;border-top:1px solid
          rgba(255,255,255,.12);padding-top:8px;">
          <b>⚠️ Risiko bila diabaikan.</b> {ins['risiko']}</div>
        </div>""", unsafe_allow_html=True)


def text(key: str) -> str:
    """Render sebagai markdown untuk README."""
    ins = INSIGHTS.get(key)
    if not ins:
        return ""
    lines = []
    for r in ins["rekomendasi"]:
        if isinstance(r, str):
            lines.append(f"  - {r}")
        else:
            lines.append(f"  - **{r.get('aksi','')}**")
            for s in (r.get("langkah") or []):
                txt = s.get("langkah", s) if isinstance(s, dict) else s
                lines.append(f"      1. {txt}")
            if r.get("metrik"):
                lines.append(f"      · Metrik sukses: {r['metrik']}")
            if r.get("pemilik"):
                lines.append(f"      · Pemilik: {r['pemilik']}")
    recs = "\n".join(lines)
    return (f"**Kesimpulan.** {ins['kesimpulan']}\n\n"
            f"**Rekomendasi tindakan:**\n{recs}\n\n"
            f"**⚠️ Risiko bila diabaikan.** {ins['risiko']}")


def audit(required_keys: list[str] | None = None, verbose: bool = True) -> bool:
    """Pastikan setiap insight lengkap (kesimpulan, >=1 rekomendasi, risiko)."""
    ok = True
    for k, v in INSIGHTS.items():
        miss = []
        if not v.get("kesimpulan"):
            miss.append("kesimpulan")
        if not v.get("rekomendasi"):
            miss.append("rekomendasi")
        if not v.get("risiko"):
            miss.append("risiko")
        if miss:
            ok = False
            if verbose:
                print(f"  MISSING {k}: {miss}")
    if required_keys:
        for k in required_keys:
            if k not in INSIGHTS:
                ok = False
                if verbose:
                    print(f"  MISSING key: {k}")
    return ok
