"""
echarts_charts.py — komponen chart Apache ECharts untuk Streamlit.

KENAPA MODUL INI ADA:
  ECharts unggul pada jenis chart yang Plotly LEMAH atau tidak punya:
  Sankey (alur), graph/network (hubungan), heatmap padat, gauge, radar,
  themeRiver (aliran tema), boxplot (distribusi+outlier), parallel
  (perbandingan multi-dimensi), funnel (tahapan/konversi), pictorialBar
  (komposisi visual), calendar heatmap (pola harian), tree (hierarki),
  dan sunburst.

  Semua fungsi di sini berasal dari galeri resmi ECharts
  (https://echarts.apache.org/examples/en/index.html), diparameterkan agar
  bisa dipakai ulang dan konsisten di seluruh project data analyst.

TEKNIS:
  `streamlit-echarts` TIDAK kompatibel dgn Streamlit 1.64 (error components v2).
  Maka chart dirender via `streamlit.components.v1.html` + ECharts CDN.
  Deterministik & tanpa dependensi Python tambahan.

CATATAN KOMPATIBILITAS:
  Semua chart di sini adalah chart BAWAAN ECharts 5 (tidak butuh
  echarts-gl/echarts-liquidfill), sehingga cukup satu CDN.
"""
from __future__ import annotations

import json

import streamlit.components.v1 as components

ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"

# Palet selaras tema project (hijau tua, biru, kuning, merah, ungu).
PALETTE = ["#1F5C3D", "#2E6F95", "#E4A11B", "#C0392B", "#6A4C93",
           "#2A9D8F", "#E76F51", "#264653"]


def _render(option: dict, height: int = 420, theme: str = "dark") -> None:
    """Render satu opsi ECharts ke Streamlit via HTML/iframe."""
    opt = json.dumps(option, ensure_ascii=False, default=str)
    html = f"""
    <div id="ec" style="width:100%;height:{height}px;"></div>
    <script src="{ECHARTS_CDN}"></script>
    <script>
      (function() {{
        var el = document.getElementById('ec');
        var chart = echarts.init(el, '{theme}', {{renderer: 'canvas'}});
        var option = {opt};
        option.color = option.color || {json.dumps(PALETTE)};
        if (option.textStyle) {{ option.textStyle.color = option.textStyle.color || '#D5DBE1'; }}
        else {{ option.textStyle = {{color: '#D5DBE1'}}; }}
        chart.setOption(option);
        window.addEventListener('resize', function(){{ chart.resize(); }});
      }})();
    </script>
    """
    components.html(html, height=height + 24, scrolling=False)


def _title(text: str) -> dict | None:
    return {"text": text, "textStyle": {"fontSize": 15}} if text else None


# --------------------------------------------------------------- SANKEY -------
def sankey(nodes: list[str], links: list[dict], height: int = 460,
           title: str = "") -> None:
    """Diagram alur (Sankey): nodes + links [{source,target,value}]."""
    _render({
        "title": _title(title),
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "sankey",
            "data": [{"name": n} for n in nodes],
            "links": links,
            "emphasis": {"focus": "adjacency"},
            "lineStyle": {"color": "gradient", "curveness": 0.5},
            "label": {"color": "#D5DBE1", "fontSize": 11},
        }],
    }, height)


# --------------------------------------------------------------- GRAPH --------
def graph(nodes: list[dict], links: list[dict], height: int = 500,
          title: str = "", layout: str = "force") -> None:
    """Jaringan hubungan (nodes: {name,value?,symbolSize?})."""
    _render({
        "title": _title(title),
        "tooltip": {},
        "series": [{
            "type": "graph",
            "layout": layout,
            "roam": True,
            "data": nodes,
            "links": links,
            "label": {"show": True, "color": "#D5DBE1", "fontSize": 10},
            "force": {"repulsion": 120, "edgeLength": 80},
            "lineStyle": {"color": "#8B9AA6", "curveness": 0.15},
        }],
    }, height)


# --------------------------------------------------------------- HEATMAP ------
def heatmap(x: list, y: list, data: list[list], height: int = 480,
            title: str = "", xname: str = "", yname: str = "",
            colors: list[str] | None = None) -> None:
    """Heatmap padat (x, y, value). ECharts jauh lebih mulus dari Plotly."""
    colors = colors or ["#1F5C3D", "#2E6F95", "#E4A11B", "#C0392B"]
    _render({
        "title": _title(title),
        "tooltip": {"position": "top"},
        "grid": {"height": "65%", "bottom": 80, "left": 110},
        "xAxis": {"type": "category", "data": x, "name": xname,
                  "splitArea": {"show": True}},
        "yAxis": {"type": "category", "data": y, "name": yname,
                  "splitArea": {"show": True}},
        "visualMap": {"min": min((d[2] for d in data), default=0),
                      "max": max((d[2] for d in data), default=1),
                      "calculable": True, "orient": "horizontal",
                      "left": "center", "bottom": 10,
                      "inRange": {"color": colors}},
        "series": [{"type": "heatmap", "data": data,
                    "label": {"show": len(data) <= 120},
                    "emphasis": {"itemStyle": {"shadowBlur": 8}}}],
    }, height)


# --------------------------------------------------------------- GAUGE --------
def gauge(value: float, max_value: float = 1.0, title: str = "",
          height: int = 320, unit: str = "") -> None:
    """Gauge satu nilai (indeks/keputusan)."""
    _render({
        "series": [{
            "type": "gauge",
            "min": 0, "max": max_value,
            "progress": {"show": True, "width": 14},
            "axisLine": {"lineStyle": {"width": 14}},
            "axisTick": {"show": False},
            "splitLine": {"length": 12},
            "pointer": {"width": 5},
            "detail": {"valueAnimation": True, "fontSize": 24,
                       "formatter": "{value}" + unit,
                       "color": "#D5DBE1", "offsetCenter": [0, "60%"]},
            "title": {"fontSize": 14, "color": "#8B9AA6"},
            "data": [{"value": round(value, 3), "name": title}],
            "color": PALETTE,
        }],
    }, height)


# --------------------------------------------------------------- RADAR --------
def radar(indicators: list[dict], series: list[dict], maxv: float = 1.0,
          height: int = 420, title: str = "") -> None:
    """Radar multi-dimensi. indicators=[{name,max}], series=[{name,value:[...]}]."""
    _render({
        "title": _title(title),
        "tooltip": {},
        "legend": {"bottom": 0, "textStyle": {"color": "#D5DBE1"}},
        "radar": {"indicator": indicators, "radius": "62%",
                  "axisName": {"color": "#D5DBE1", "fontSize": 11}},
        "series": [{"type": "radar",
                    "data": [{"name": s["name"], "value": s["value"]}
                             for s in series]}],
    }, height)


# --------------------------------------------------------------- TREEMAP ------
def treemap(data: list[dict], height: int = 460, title: str = "") -> None:
    """Treemap hierarki (data=[{name,value,children?}])."""
    _render({
        "title": _title(title),
        "tooltip": {"trigger": "item"},
        "series": [{"type": "treemap", "roam": False, "nodeClick": False,
                    "breadcrumb": {"show": False},
                    "label": {"color": "#fff", "fontSize": 11},
                    "levels": [{"itemStyle": {"borderWidth": 2,
                                              "gapWidth": 2}}],
                    "data": data}],
    }, height)


# ----------------------------------------------------------- CANDLESTICK ------
def candlestick(categories: list, ohlc: list[list], height: int = 460,
                title: str = "") -> None:
    """Candlestick (OHLC). ohlc=[[open,close,low,high], ...]."""
    _render({
        "title": _title(title),
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 70, "right": 30, "top": 50, "bottom": 60},
        "xAxis": {"type": "category", "data": categories},
        "yAxis": {"scale": True, "splitArea": {"show": True}},
        "dataZoom": [{"type": "inside"}, {"type": "slider", "bottom": 10}],
        "series": [{"type": "candlestick", "data": ohlc,
                    "itemStyle": {"color": "#2A9D8F", "color0": "#C0392B",
                                  "borderColor": "#2A9D8F",
                                  "borderColor0": "#C0392B"}}],
    }, height)


# ----------------------------------------------------------- SUNBURST ---------
def sunburst(data: list[dict], height: int = 480, title: str = "") -> None:
    """Sunburst hierarki melingkar."""
    _render({
        "title": _title(title),
        "tooltip": {},
        "series": [{"type": "sunburst", "radius": [0, "90%"], "data": data,
                    "label": {"color": "#fff", "fontSize": 10}}],
    }, height)


# ============================== CHART BARU (v2) ===============================


# ----------------------------------------------------------- THEME RIVER ------
def theme_river(categories: list[str], series: list[dict],
                height: int = 480, title: str = "") -> None:
    """
    ThemeRiver (galeri: 'Theme River') — aliran volume beberapa tema/kategori
    sepanjang waktu. Cocok untuk melihat komposisi topik/sentimen yang
    bergeser dari periode ke periode (mis. topik SDG, tren sentimen).

    categories : daftar titik waktu (string), mis. bulan "2024-01".
    series     : [{"name": tema, "data": [[i, value], ...]}] — i = indeks
                 posisi pada `categories`, nilai = volume tema itu.
    """
    # ECharts themeRiver butuh: singleAxis (kategori) + data [catIdx, val, name],
    # dengan series.coordinateSystem='singleAxis'. Tanpa itu, pita jadi kacau.
    flat = [[int(x), float(v), str(s["name"])]
            for s in series for (x, v) in s["data"]]
    _render({
        "title": _title(title),
        "tooltip": {"trigger": "axis"},
        "legend": {"bottom": 0, "textStyle": {"color": "#D5DBE1"}},
        "color": PALETTE,
        "singleAxis": {
            "type": "category",
            "data": [str(c) for c in categories],
            "top": 60, "bottom": 70, "left": 60, "right": 30,
            "axisTick": {"show": False},
            "axisLine": {"lineStyle": {"color": "#2A3038"}},
            "axisLabel": {"color": "#8B9AA6"},
        },
        "series": [{
            "type": "themeRiver",
            "coordinateSystem": "singleAxis",
            "singleAxisIndex": 0,
            "emphasis": {"itemStyle": {"shadowBlur": 18,
                                       "shadowColor": "rgba(0,0,0,0.7)"}},
            "label": {"show": False},
            "data": flat,
        }],
    }, height)


# --------------------------------------------------------------- BOXPLOT ------
def _quartiles(vals: list[float]) -> list[float]:
    """Hitung [min, Q1, median, Q3, max] ala ECharts (tanpa scipy)."""
    xs = sorted(float(v) for v in vals if v is not None)
    n = len(xs)
    if n == 0:
        return [0, 0, 0, 0, 0]
    if n == 1:
        return [xs[0], xs[0], xs[0], xs[0], xs[0]]

    def q(p: float) -> float:
        # interpolasi linear (metode sama dgn numpy percentile default)
        if n == 1:
            return xs[0]
        idx = p * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return xs[lo] + (xs[hi] - xs[lo]) * frac

    # outlier via 1.5*IQR (whisker), min/max dibatasi ke non-outlier
    q1, med, q3 = q(0.25), q(0.50), q(0.75)
    iqr = q3 - q1
    lo_fence = q1 - 1.5 * iqr
    hi_fence = q3 + 1.5 * iqr
    inner = [v for v in xs if lo_fence <= v <= hi_fence] or xs
    return [min(inner), q1, med, q3, max(inner)]


def boxplot(categories: list, values: list[list], height: int = 480,
            title: str = "", yname: str = "") -> None:
    """
    Boxplot (galeri: 'Boxplot Light Velocity'). Menampilkan median, kuartil,
    dan OUTLIER per grup — lebih informatif dari bar rata-rata, karena
    memperlihatkan sebaran & pencilan (mis. harga per kategori, IV per bucket).

    values : daftar per kategori, tiap elemen = list angka mentah grup itu.
    Statistik [min,Q1,median,Q3,max] dihitung di Python (deterministik,
    tanpa scipy) lalu dikirim ke ECharts; outlier ditandai sebagai scatter.
    """
    boxes, outliers = [], []
    for i, grp in enumerate(values):
        xs = sorted(float(v) for v in grp if v is not None)
        if not xs:
            boxes.append([0, 0, 0, 0, 0])
            continue
        q1 = xs[int(0.25 * (len(xs) - 1))]
        med = xs[int(0.50 * (len(xs) - 1))]
        stats = _quartiles(xs)
        boxes.append(stats)
        lo, hi = stats[0], stats[4]
        for v in xs:
            if v < lo or v > hi:
                outliers.append([i, v])
    _render({
        "title": _title(title),
        "tooltip": {"trigger": "item", "axisPointer": {"type": "shadow"}},
        "grid": {"left": 70, "right": 30, "top": 60, "bottom": 70},
        "xAxis": {"type": "category", "data": list(categories),
                  "boundaryGap": True,
                  "axisLabel": {"color": "#D5DBE1", "rotate": 25},
                  "splitArea": {"show": True}},
        "yAxis": {"type": "value", "name": yname, "splitArea": {"show": True}},
        "dataZoom": [{"type": "inside"}, {"type": "slider", "bottom": 10}],
        "series": [
            {"name": "box", "type": "boxplot", "data": boxes,
             "boxWidth": ["20%", "55%"],
             "itemStyle": {"color": "#2E6F95", "borderColor": "#2A9D8F",
                           "borderWidth": 1.5}},
            {"name": "outlier", "type": "scatter", "data": outliers,
             "symbolSize": 5,
             "itemStyle": {"color": "#E4A11B", "opacity": 0.7}},
        ],
    }, height)


# -------------------------------------------------------------- PARALLEL ------
def parallel(axes: list[dict], rows: list[list], height: int = 480,
             title: str = "", names: list[str] | None = None) -> None:
    """
    Parallel coordinates (galeri: 'Parallel Aqi' / 'Parallel Nutrients') —
    bandingkan BANYAK dimensi sekaligus untuk tiap entitas. Cocok untuk
    memberi profil multi-indikator (mis. 17 indikator ekonomi per negara,
    atau profil value/rating/harga per brand).

    axes : [{"dim": 0, "name": "Harga", "min":..., "max":...}, ...]
    rows : tiap baris = satu entitas, nilai per dimensi (urutan = dim).
    names: nama entitas untuk hover/legenda.
    """
    data = []
    for i, r in enumerate(rows):
        nm = names[i] if names and i < len(names) else f"#{i+1}"
        data.append({"value": r, "name": nm})
    _render({
        "title": _title(title),
        "parallelAxis": axes,
        "parallel": {"left": 60, "right": 60, "top": 60, "bottom": 40,
                     "parallelAxisDefault": {
                         "type": "value",
                         "nameLocation": "start",
                         "nameGap": 20,
                         "nameTextStyle": {"color": "#D5DBE1"}}},
        "series": [{
            "type": "parallel",
            "smooth": True,
            "lineStyle": {"width": 2, "opacity": 0.4},
            "emphasis": {"lineStyle": {"width": 4, "opacity": 1}},
            "data": data,
        }],
    }, height)


# ---------------------------------------------------------------- FUNNEL ------
def funnel(stages: list[dict], height: int = 460, title: str = "",
           sort: str = "descending") -> None:
    """
    Funnel (galeri: 'Funnel Chart') — tahapan bertingkat dengan penyusutan.
    Cocok untuk pipeline data (ingest → valid → bersih → siap analisis) atau
    cakupan (total → terdeteksi → berkualitas).
    stages : [{"name": tahap, "value": n}] dari terbesar ke terkecil.
    """
    _render({
        "title": _title(title),
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b}: {c}"},
        "legend": {"bottom": 0, "textStyle": {"color": "#D5DBE1"}},
        "series": [{
            "type": "funnel",
            "left": "10%", "width": "80%", "sort": sort,
            "gap": 4,
            "label": {"show": True, "position": "inside",
                      "color": "#fff", "fontSize": 12},
            "labelLine": {"length": 10, "lineStyle": {"width": 1,
                                                      "type": "solid"}},
            "itemStyle": {"borderColor": "#0E1117", "borderWidth": 1},
            "emphasis": {"label": {"fontSize": 16}},
            "data": stages,
        }],
    }, height)


# ----------------------------------------------------------- PICTORIAL BAR ----
def pictorial_bar(categories: list, values: list[float], symbol: str = "rect",
                  height: int = 460, title: str = "", yname: str = "",
                  max_value: float | None = None) -> None:
    """
    PictorialBar (galeri: 'PictorialBar Dotted') — bar bertitik/simbol untuk
    membuat komposisi terlihat visual & mudah dibandingkan. Cocok untuk laporan
    ringkas (mis. indikator per negara) agar lebih menarik dari bar polos.

    CATATAN SKALA (penting): pictorialBar menumpuk simbol; untuk nilai besar
    (mis. populasi miliaran) itu menghasilkan ratusan titik dan tampak rusak.
    Di sini nilai **dinormalisasi ke skala 0–100** secara implisit lewat
    symbolBoundingData, dan jumlah simbol dibatasi, sehingga bar selalu rapi
    apa pun magnitudo datanya.

    symbol: 'rect' (blok), 'circle', 'diamond', 'triangle', 'roundRect'.
    """
    vals = [float(v) for v in values]
    vmax = max(vals) if vals else 1.0
    top = max_value if max_value else vmax
    top = top if top > 0 else 1.0
    # batasi jumlah simbol agar tidak "berduri" pada nilai besar
    _n_symbols = 22
    _unit = top / _n_symbols if top else 1.0
    scaled = [round(v / _unit, 3) if _unit else 0 for v in vals]
    _render({
        "title": _title(title),
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"},
                    "formatter": "{b}"},
        "grid": {"left": 70, "right": 30, "top": 60, "bottom": 80},
        "xAxis": {"type": "category", "data": list(categories),
                  "axisLabel": {"color": "#D5DBE1", "rotate": 30}},
        "yAxis": {"max": _n_symbols, "name": yname,
                  "splitLine": {"show": False},
                  "axisLabel": {"show": False}},
        "series": [{
            "type": "pictorialBar",
            "symbol": symbol,
            "symbolRepeat": "fixed",
            "symbolMargin": 2,
            "symbolClip": True,
            "symbolSize": [16, 7],
            "symbolBoundingData": _n_symbols,
            "symbolPosition": "start",
            "data": scaled,
            "z": 10,
            "label": {"show": True, "position": "top", "color": "#D5DBE1",
                      "fontSize": 10},
        }, {
            "type": "pictorialBar",
            "symbol": symbol,
            "symbolRepeat": "fixed",
            "symbolMargin": 2,
            "symbolSize": [16, 7],
            "symbolBoundingData": _n_symbols,
            "symbolPosition": "start",
            "itemStyle": {"color": "#22303C"},
            "data": [_n_symbols] * len(vals),
            "z": 5,
            "silent": True,
        }],
    }, height)


# -------------------------------------------------------- CALENDAR HEATMAP ----
def calendar_heatmap(year: int, data: list[list], height: int = 260,
                     title: str = "", max_value: float | None = None) -> None:
    """
    Calendar heatmap (galeri: 'Calendar Heatmap') — pola harian sepanjang
    tahun (ala GitHub contributions). Cocok untuk melihat musiman/hari aktif
    (mis. volume komentar, hari balapan, frekuensi anomali).

    data : [["2024-01-15", 12], ...]
    """
    mx = max_value or (max((d[1] for d in data), default=1) or 1)
    _render({
        "title": _title(title),
        "tooltip": {"position": "top",
                    "formatter": "{b}: {c}"},
        "visualMap": {"min": 0, "max": mx, "calculable": True,
                      "orient": "horizontal", "left": "center", "bottom": 0,
                      "inRange": {"color": ["#173B2A", "#1F5C3D", "#2A9D8F",
                                            "#E4A11B", "#C0392B"]}},
        "calendar": {
            "top": 60, "left": 40, "right": 20, "cellSize": ["auto", 14],
            "range": str(year),
            "itemStyle": {"borderWidth": 0.5, "borderColor": "#22303C",
                          "color": "transparent"},
            "yearLabel": {"color": "#8B9AA6"},
            "dayLabel": {"color": "#8B9AA6"},
            "monthLabel": {"color": "#8B9AA6"},
            "splitLine": {"lineStyle": {"color": "#2A3038"}},
        },
        "series": [{"type": "heatmap", "coordinateSystem": "calendar",
                    "data": data}],
    }, height)


# ------------------------------------------------------------------ TREE ------
def tree(data: dict, height: int = 520, title: str = "",
         orient: str = "LR") -> None:
    """
    Tree (galeri: 'Tree Basic') — hierarki bercabang, lebih jelas dari treemap
    untuk kedalaman (mis. kategori → sub-kategori → brand; atau tema → subtema).
    data : {"name": root, "children": [ {"name":..., "value":..., "children":[...]} ]}
    """
    _render({
        "title": _title(title),
        "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
        "series": [{
            "type": "tree",
            "data": [data],
            "orient": orient,
            "top": "8%", "left": "8%", "bottom": "8%", "right": "20%",
            "symbolSize": 9,
            "roam": True,
            "expandAndCollapse": True,
            "initialTreeDepth": 2,
            "label": {"backgroundColor": "transparent", "color": "#D5DBE1",
                      "fontSize": 11, "position": "left", "verticalAlign":
                      "middle", "align": "right"},
            "leaves": {"label": {"position": "right", "align": "left"}},
            "lineStyle": {"color": "#8B9AA6", "width": 1.5, "curveness": 0.5},
            "emphasis": {"focus": "descendant"},
        }],
    }, height)


# ------------------------------------------------- WATERFALL (bar bertumpuk) ---
def waterfall(categories: list[str], values: list[float], height: int = 440,
              title: str = "", yname: str = "") -> None:
    """
    Waterfall (galeri: 'Waterfall Chart') — dekomposisi kontribusi naik/turun
    sampai hasil akhir. Cocok untuk jembatan (bridge): kontribusi segmen ke
    perubahan metrik, atau dekomposisi biaya/efek.

    values : perubahan tiap langkah. Bila elemen terakhir = 0, ia dirender
             sebagai BATANG TOTAL (dari 0 ke akumulasi). Bila bukan 0, semua
             elemen diperlakukan sebagai langkah delta.

    Implementasi: satu seri 'base' transparan (nilai awal tiap batang) +
    satu seri 'delta' berwarna (tinggi batang). Keduanya sejajar indeks.
    """
    n = len(values)
    base, delta, colors, labels = [], [], [], []
    running = 0.0
    is_total_last = n > 0 and abs(values[-1]) < 1e-9
    for i, v in enumerate(values):
        if is_total_last and i == n - 1:
            base.append(0.0)
            delta.append(round(running, 4))
            colors.append("#2E6F95")
            labels.append(f"{running:.2f}")
            continue
        if v >= 0:
            base.append(round(running, 4))
            delta.append(round(v, 4))
            colors.append("#1F5C3D")
            labels.append(f"+{v:.2f}")
            running += v
        else:
            running += v
            base.append(round(running, 4))
            delta.append(round(-v, 4))
            colors.append("#C0392B")
            labels.append(f"{v:.2f}")
    _render({
        "title": _title(title),
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": 70, "right": 30, "top": 60, "bottom": 70},
        "xAxis": {"type": "category", "data": list(categories),
                  "axisLabel": {"color": "#D5DBE1", "rotate": 25}},
        "yAxis": {"type": "value", "name": yname},
        "series": [
            {"name": "base", "type": "bar", "stack": "wf", "silent": True,
             "itemStyle": {"color": "transparent"},
             "emphasis": {"itemStyle": {"color": "transparent"}},
             "tooltip": {"show": False},
             "data": base},
            {"name": "delta", "type": "bar", "stack": "wf",
             "label": {"show": True, "position": "top", "color": "#D5DBE1",
                       "fontSize": 10},
             "data": [{"value": d, "itemStyle": {"color": c},
                       "label": {"formatter": lb}}
                      for d, c, lb in zip(delta, colors, labels)]},
        ],
    }, height)


if __name__ == "__main__":
    print("echarts_charts v2: sankey, graph, heatmap, gauge, radar, treemap, "
          "candlestick, sunburst, themeRiver, boxplot, parallel, funnel, "
          "pictorialBar, calendar_heatmap, tree, waterfall")
