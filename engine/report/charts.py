"""Inline SVG charts for the HTML report (pure Python, deterministic, no JavaScript chart library).

Colours come from CSS classes defined in templates/style.css, so print and screen stay consistent. Every chart
has a *_geometry function that returns the numbers it draws; tests check those numbers by hand.
"""
from __future__ import annotations

import math
from html import escape
from typing import Dict, List, Optional, Sequence, Tuple


def _r(x: float) -> str:
    """Coordinates rounded to 0.01 px; '-0' normalised so output is byte-stable."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _ok(v) -> bool:
    return v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))


# ---------------------------------------------------------------------------------------------- sparkline
def sparkline_geometry(values: Sequence[Optional[float]], w: float = 120, h: float = 28, pad: float = 3
                       ) -> List[Optional[Tuple[float, float]]]:
    """x evenly spaced over [pad, w - pad]; y maps [min, max] to [h - pad, pad] (a flat series sits mid-height)."""
    n = len(values)
    vals = [float(v) for v in values if _ok(v)]
    if n == 0 or not vals:
        return []
    lo, hi = min(vals), max(vals)
    pts: List[Optional[Tuple[float, float]]] = []
    for i, v in enumerate(values):
        if not _ok(v):
            pts.append(None)
            continue
        x = pad + (i * (w - 2 * pad) / (n - 1) if n > 1 else (w - 2 * pad) / 2)
        y = h / 2 if hi == lo else pad + (hi - float(v)) / (hi - lo) * (h - 2 * pad)
        pts.append((x, y))
    return pts


def sparkline(values: Sequence[Optional[float]], labels: Sequence[str] = (), w: float = 120, h: float = 28,
              cls: str = "") -> str:
    pts = sparkline_geometry(values, w, h)
    if not pts:
        return f'<svg class="spark empty" width="{_r(w)}" height="{_r(h)}" viewBox="0 0 {_r(w)} {_r(h)}" role="img" aria-label="no data"></svg>'
    runs, cur = [], []
    for p in pts:
        if p is None:
            if cur:
                runs.append(cur)
            cur = []
        else:
            cur.append(p)
    if cur:
        runs.append(cur)
    lines = "".join(f'<polyline points="{" ".join(f"{_r(x)},{_r(y)}" for x, y in run)}"/>' for run in runs if len(run) > 1)
    dots = "".join(f'<circle cx="{_r(x)}" cy="{_r(y)}" r="1.6"/>' for run in runs for x, y in run if len(run) == 1)
    last_i = max(i for i, p in enumerate(pts) if p is not None)
    lx, ly = pts[last_i]
    title = ""
    if labels:
        span = [labels[i] for i, p in enumerate(pts) if p is not None]
        title = f"<title>{escape(span[0])}-{escape(span[-1])}</title>" if span else ""
    return (f'<svg class="spark {cls}" width="{_r(w)}" height="{_r(h)}" viewBox="0 0 {_r(w)} {_r(h)}" role="img">'
            f'{title}<g class="line">{lines}{dots}</g><circle class="last" cx="{_r(lx)}" cy="{_r(ly)}" r="2.2"/></svg>')


# ---------------------------------------------------------------------------------------------- band strip
def band_geometry(value: float, red: float, green: float, w: float = 140) -> Dict[str, float]:
    """Domain = [min, max] of (value, red, green) widened by 15% of the span (or 1 when all equal)."""
    lo, hi = min(value, red, green), max(value, red, green)
    span = hi - lo if hi > lo else 1.0
    lo, hi = lo - 0.15 * span, hi + 0.15 * span

    def x(v):
        return (v - lo) / (hi - lo) * w
    return {"lo": lo, "hi": hi, "x_red": x(red), "x_green": x(green), "x_value": x(value)}


def band_strip(value, red, green, direction: str, w: float = 140, h: float = 12) -> str:
    """Red / amber / green zones with a marker at the value (higher-is-better: red on the left)."""
    if not all(_ok(v) for v in (value, red, green)):
        return ""
    g = band_geometry(float(value), float(red), float(green), w)
    xr, xg, xv = g["x_red"], g["x_green"], g["x_value"]
    a, b = min(xr, xg), max(xr, xg)
    left, right = ("red", "green") if xr <= xg else ("green", "red")
    return (f'<svg class="band" width="{_r(w)}" height="{_r(h + 6)}" viewBox="0 0 {_r(w)} {_r(h + 6)}" role="img">'
            f'<rect class="z-{left}" x="0" y="3" width="{_r(a)}" height="{_r(h)}"/>'
            f'<rect class="z-amber" x="{_r(a)}" y="3" width="{_r(b - a)}" height="{_r(h)}"/>'
            f'<rect class="z-{right}" x="{_r(b)}" y="3" width="{_r(w - b)}" height="{_r(h)}"/>'
            f'<rect class="marker" x="{_r(xv - 1.5)}" y="0" width="3" height="{_r(h + 6)}"/></svg>')


# ---------------------------------------------------------------------------------------------- waterfall (horizontal)
def waterfall_geometry(start: float, steps: Sequence[Tuple[str, float]], w: float = 360) -> Dict:
    """Rows: start bar (0 -> start), one floating bar per step (cum -> cum + delta), end bar (0 -> end).
    The x scale spans [min(0, all running totals), max(0, all running totals)]."""
    cums = [start]
    for _, d in steps:
        cums.append(cums[-1] + d)
    lo, hi = min(0.0, *cums), max(0.0, *cums)
    if hi == lo:
        hi = lo + 1.0

    def x(v):
        return (v - lo) / (hi - lo) * w
    rows = [{"kind": "start", "x0": x(min(0.0, start)), "x1": x(max(0.0, start)), "value": start}]
    for i, (lab, d) in enumerate(steps):
        a, b = cums[i], cums[i + 1]
        rows.append({"kind": "pos" if d >= 0 else "neg", "label": lab, "x0": x(min(a, b)), "x1": x(max(a, b)), "value": d})
    end = cums[-1]
    rows.append({"kind": "end", "x0": x(min(0.0, end)), "x1": x(max(0.0, end)), "value": end})
    return {"lo": lo, "hi": hi, "x_zero": x(0.0), "rows": rows, "end": end}


def waterfall(start_label: str, start: float, steps: Sequence[Tuple[str, float, str]], end_label: str,
              fmt_level, fmt_step, w: float = 360, label_w: float = 210, row_h: float = 20) -> str:
    """steps: (label, delta, delta_text). fmt_level formats start/end values; delta_text is shown as given."""
    geo = waterfall_geometry(start, [(lab, d) for lab, d, _ in steps], w)
    n = len(geo["rows"])
    total_w = label_w + w + 90
    total_h = n * row_h + 8
    out = [f'<svg class="waterfall" width="{_r(total_w)}" height="{_r(total_h)}" viewBox="0 0 {_r(total_w)} {_r(total_h)}" role="img">',
           f'<line class="axis" x1="{_r(label_w + geo["x_zero"])}" y1="0" x2="{_r(label_w + geo["x_zero"])}" y2="{_r(total_h)}"/>']
    texts = [start_label] + [s[0] for s in steps] + [end_label]
    vals = [fmt_level(start)] + [s[2] for s in steps] + [fmt_level(geo["end"])]
    for i, (row, lab, val) in enumerate(zip(geo["rows"], texts, vals)):
        y = 4 + i * row_h
        bw = max(row["x1"] - row["x0"], 1.0)
        out.append(f'<text class="lab" x="{_r(label_w - 6)}" y="{_r(y + row_h * 0.62)}" text-anchor="end">{escape(lab)}</text>')
        out.append(f'<rect class="wf-{row["kind"]}" x="{_r(label_w + row["x0"])}" y="{_r(y + 3)}" width="{_r(bw)}" height="{_r(row_h - 6)}"/>')
        out.append(f'<text class="val" x="{_r(label_w + max(row["x1"], row["x0"] + bw) + 4)}" y="{_r(y + row_h * 0.62)}">{escape(val)}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------------------------- bars
def bars_geometry(values: Sequence[float], w: float = 300) -> Dict:
    """Horizontal bars from zero; scale spans [min(0, values), max(0, values)]."""
    vals = [float(v) for v in values]
    lo, hi = min(0.0, *vals) if vals else 0.0, max(0.0, *vals) if vals else 1.0
    if hi == lo:
        hi = lo + 1.0

    def x(v):
        return (v - lo) / (hi - lo) * w
    return {"lo": lo, "hi": hi, "x_zero": x(0.0), "bars": [(x(min(0.0, v)), x(max(0.0, v))) for v in vals]}


def bars(items: Sequence[Tuple[str, float, str, str]], w: float = 300, label_w: float = 220, row_h: float = 20) -> str:
    """items: (label, value, value_text, css class)."""
    items = [it for it in items if _ok(it[1])]
    if not items:
        return ""
    geo = bars_geometry([it[1] for it in items], w)
    total_w, total_h = label_w + w + 80, len(items) * row_h + 8
    out = [f'<svg class="bars" width="{_r(total_w)}" height="{_r(total_h)}" viewBox="0 0 {_r(total_w)} {_r(total_h)}" role="img">',
           f'<line class="axis" x1="{_r(label_w + geo["x_zero"])}" y1="0" x2="{_r(label_w + geo["x_zero"])}" y2="{_r(total_h)}"/>']
    for i, ((lab, _, txt, cls), (x0, x1)) in enumerate(zip(items, geo["bars"])):
        y = 4 + i * row_h
        out.append(f'<text class="lab" x="{_r(label_w - 6)}" y="{_r(y + row_h * 0.62)}" text-anchor="end">{escape(lab)}</text>')
        out.append(f'<rect class="{cls}" x="{_r(label_w + x0)}" y="{_r(y + 3)}" width="{_r(max(x1 - x0, 1.0))}" height="{_r(row_h - 6)}"/>')
        out.append(f'<text class="val" x="{_r(label_w + max(x1, x0 + 1.0) + 4)}" y="{_r(y + row_h * 0.62)}">{escape(txt)}</text>')
    out.append("</svg>")
    return "".join(out)


def grouped_bars(categories: Sequence[str], series: Sequence[Tuple[str, Sequence[Optional[float]]]], w: float = 320,
                 label_w: float = 200, bar_h: float = 9, gap: float = 8) -> str:
    """Pillar scores (0-100) side by side: one group per category, one bar per series (css class s0..s4)."""
    k = len(series)
    group_h = k * bar_h + gap
    total_w, total_h = label_w + w + 40, len(categories) * group_h + 24
    out = [f'<svg class="grouped" width="{_r(total_w)}" height="{_r(total_h)}" viewBox="0 0 {_r(total_w)} {_r(total_h)}" role="img">']
    for t in (0, 50, 100):
        x = label_w + t / 100 * w
        out.append(f'<line class="grid" x1="{_r(x)}" y1="0" x2="{_r(x)}" y2="{_r(total_h - 16)}"/>'
                   f'<text class="tick" x="{_r(x)}" y="{_r(total_h - 4)}" text-anchor="middle">{t}</text>')
    for gi, cat in enumerate(categories):
        y0 = gi * group_h + 2
        out.append(f'<text class="lab" x="{_r(label_w - 6)}" y="{_r(y0 + k * bar_h / 2 + 4)}" text-anchor="end">{escape(cat)}</text>')
        for si, (name, vals) in enumerate(series):
            v = vals[gi] if gi < len(vals) else None
            if not _ok(v):
                continue
            out.append(f'<rect class="s{si}" x="{_r(label_w)}" y="{_r(y0 + si * bar_h)}" width="{_r(max(0.0, min(100.0, v)) / 100 * w)}" '
                       f'height="{_r(bar_h - 1)}"><title>{escape(name)}: {v:.0f}</title></rect>')
    out.append("</svg>")
    return "".join(out)
