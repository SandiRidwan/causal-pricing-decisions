"""
explanations.py — narasi Kenapa · Tujuan · Dampak untuk tiap elemen dashboard.
Menjaga agar SETIAP chart punya alasan bisnis, bukan sekadar angka.
"""

from __future__ import annotations

EXPLAIN: dict[str, dict] = {
    "kpi": {
        "judul": "Ringkasan Kebijakan",
        "kenapa": "Butuh gambaran cepat: apa kebijakannya, apa efeknya, apa "
                  "keputusannya.",
        "tujuan": "Menjawab: apakah kebijakan harga ini layak dilanjutkan?",
        "dampak": "Menentukan langkah berikutnya (lanjut / uji ulang / stop).",
        "baca": "Tier keputusan + efek laba kotor vs ground-truth.",
    },
    "did": {
        "judul": "Difference-in-Differences",
        "kenapa": "Metode standar industri untuk mengukur efek kebijakan dari "
                  "data observasi (bukan eksperimen acak).",
        "tujuan": "Menjawab: apa efek kebijakan di atas tren yang sudah ada?",
        "dampak": "Estimasi kausal pertama; dasar keputusan bila asumsi terpenuhi.",
        "baca": "DiD = (treated post−pre) − (control post−pre).",
    },
    "event_study": {
        "judul": "Event Study (uji asumsi)",
        "kenapa": "DiD hanya valid jika tren pra-periode PARALEL. Ini mengujinya.",
        "tujuan": "Menjawab: apakah treated & control bergerak serupa sebelum "
                  "intervensi?",
        "dampak": "Bila pra-periode menyimpang, DiD tidak boleh dipercaya.",
        "baca": "Efek relatif per minggu; pra-periode harus ≈ 0.",
    },
    "synthetic": {
        "judul": "Synthetic Control",
        "kenapa": "Saat arm tak seimbang, DiD 2-grup rapuh. Synthetic control "
                  "membangun counterfactual berbobot dari donor.",
        "tujuan": "Menjawab: apa yang akan terjadi TANPA kebijakan?",
        "dampak": "Estimasi lebih andal; dipakai sebagai metode utama.",
        "baca": "Selisih treated vs synthetic pasca-intervensi.",
    },
    "decision": {
        "judul": "Decision Engine",
        "kenapa": "Analisis menjadi bernilai hanya bila berujung keputusan.",
        "tujuan": "Menerjemahkan estimasi + CI → tier aksi + nilai uang.",
        "dampak": "Rekomendasi eksplisit, dapat diaudit.",
        "baca": "Tier LAKUKAN/UJI ULANG/HENTIKAN + justifikasi.",
    },
    "robustness": {
        "judul": "Uji Ketahanan",
        "kenapa": "Kesimpulan yang bergantung pada satu metode/asumsi itu rapuh.",
        "tujuan": "Menjawab: apakah hasil konsisten lintas metode & metrik?",
        "dampak": "Menentukan seberapa yakin kita boleh.",
        "baca": "Efek per metode & per metrik; placebo p-value.",
    },
}


def render(key: str, st=None) -> None:
    if st is None:
        import streamlit as st  # noqa
    e = EXPLAIN.get(key)
    if not e:
        return
    st.markdown(
        f"""
        <div style="background:#141b24;border:1px solid #2A3038;
        border-radius:10px;padding:12px 16px;margin:4px 0 14px 0;">
          <div style="color:#E4A11B;font-weight:700;font-size:.85rem;">
          📌 {e['judul']} — Kenapa · Tujuan · Dampak</div>
          <div style="color:#9AA7B4;font-size:.82rem;margin-top:6px;">
          <b>Kenapa:</b> {e['kenapa']}<br/>
          <b>Tujuan:</b> {e['tujuan']}<br/>
          <b>Dampak:</b> {e['dampak']}<br/>
          <b>Cara baca:</b> {e['baca']}</div>
        </div>""", unsafe_allow_html=True)
