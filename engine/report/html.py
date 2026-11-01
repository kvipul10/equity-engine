"""report.html and compare.html: a view model built from analysis.json, rendered with Jinja2 (autoescape on).

Self-contained output: CSS, JS and SVG charts are inlined. The only external request is KaTeX (pinned) for
equations; offline, every equation still shows as plain text and nothing else changes.
"""
from __future__ import annotations

import statistics as st
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from ..registry import PILLAR_NAMES, PILLARS
from . import charts
from . import formats as fmt
from .findings import level_context, mid_sentence, report_cfg, say, trend_text
from .latex import to_latex

TEMPLATES = Path(__file__).resolve().parent / "templates"
KATEX_VERSION = "0.16.11"
KATEX_CSS = f"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.css"
KATEX_JS = f"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.js"
GROUPS = [("Operations", ["growth", "margins", "capital_efficiency"]), ("Value and quality", ["returns", "cash_quality"]),
          ("Financing", ["balance_sheet", "capital_allocation"]), ("Market", ["valuation"])]
VAL_MULTIPLES = [("pe", "pe_percentile_10y", "trailing_pe"), ("pb", "pb_percentile_10y", "pbv"),
                 ("ev_ebitda", "ev_ebitda_percentile_10y", "ev_ebitda"), ("ev_sales", "ev_sales_percentile_10y", None)]
ROE_TREES = ["bank_dupont", "fin_roe", "roe_dupont"]


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html", "j2"]),
                      undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    env.filters["rag"] = lambda r: r if r in ("green", "amber", "red") else "na"
    return env


def _svg(s: str) -> Markup:
    return Markup(s)  # produced by charts.py, which escapes every text node


def _years(rep: Dict) -> List[str]:
    for m in rep["metrics"].values():
        if m.get("series"):
            return list(m["series"].keys())
    return []


# ---------------------------------------------------------------------------------------------- metric rows
def _peer_text(rep: Dict, mid: str, unit: str) -> str:
    vals = ((rep.get("peers") or {}).get("values") or {}).get(mid) or {}
    return ", ".join(f"{t} {fmt.value(v, unit)}" for t, v in sorted(vals.items()))


def metric_row(rep: Dict, mid: str, years: Sequence[str]) -> Dict:
    m = rep["metrics"][mid]
    series = [m["series"].get(y) for y in years] if m.get("series") else []
    b = m.get("band") or {}
    lv = m.get("level") or {}
    strip = ""
    if lv.get("basis") == "band" and m.get("value") is not None and "red" in b and "green" in b:
        strip = charts.band_strip(m["value"], b["red"], b["green"], m.get("direction", "higher"))
    stab = m.get("stability") or {}
    return {
        "id": mid, "name": m["name"], "role": m.get("role"), "rag": m.get("rag"), "unit": m["unit"],
        "value": fmt.value(m.get("value"), m["unit"]),
        "spark": _svg(charts.sparkline(series, list(years))) if series else "",
        "level": level_context(m) if m.get("rag") in ("green", "amber", "red") else (m.get("reason") or "not scored"),
        "band_strip": _svg(strip) if strip else "",
        "band_source": (f"{b.get('source_type') or ''}: {b.get('origin') or ''}".strip(": ") if b else ""),
        "band_url": b.get("source_url") if b else None,
        "peers": _peer_text(rep, mid, m["unit"]),
        "trend": trend_text(m),
        "stability": stab.get("label") or "",
        "equation": m.get("equation") or "", "latex": to_latex(m.get("equation") or "") or "",
        "meaning": m.get("meaning") or "", "origin": m.get("origin") or "engine", "note": m.get("note") or "",
    }


def pillar_views(rep: Dict, years: Sequence[str]) -> List[Dict]:
    out = []
    for p in PILLARS:
        pv = rep["pillars"][p]
        rows = [metric_row(rep, mid, years) for mid in pv.get("metrics", [])]
        rows.sort(key=lambda r: ({"scored": 0, "root": 0, "component": 1}.get(r["role"], 2), r["rag"] is None, r["name"]))
        out.append({"id": p, "name": pv["name"], "score": "n/a" if pv.get("score") is None else f"{pv['score']:.0f}",
                    "rag": pv.get("rag"), "weight": pv.get("weight"), "n_scored": pv.get("n_scored", 0),
                    "n_metrics": pv.get("n_metrics", len(rows)), "summary": pv.get("summary", ""),
                    "flags": pv.get("flags_triggered", []), "rows": rows})
    return out


# ---------------------------------------------------------------------------------------------- drivers
def _tree_view(rep: Dict, tid: str) -> Dict:
    t = rep["drivers"][tid]
    root = t["root"]
    ru = rep["metrics"][root]["unit"] if root in rep["metrics"] else "num"
    rname = rep["metrics"][root]["name"] if root in rep["metrics"] else root
    wins = []
    for w, win in t["windows"].items():
        if win.get("status") != "ok":
            wins.append({"key": w, "ok": False, "reason": say("empty.drivers", reason=win.get("reason") or "n/a")})
            continue
        nodes = win.get("nodes") or {}
        first = [(n, v) for n, v in nodes.items() if v["path"].count(" > ") == 1]
        first.sort(key=lambda x: -abs(x[1]["contribution"] or 0))
        steps = [(v["name"], v["contribution"] or 0.0, fmt.delta(v["contribution"], ru)) for _, v in first]
        if abs(win.get("residual") or 0) > 1e-9:
            steps.append(("Residual", win["residual"], fmt.delta(win["residual"], ru)))
        svg = charts.waterfall(f"{rname} {win['from']}", win["root_from"], steps, f"{rname} {win['to']}",
                               lambda v: fmt.value(v, ru), None)
        tops = [{"name": d["name"], "own": fmt.signed(d["own_change_text"]), "contribution": fmt.delta(d["contribution"], ru),
                 "share": fmt.pct(d["share_of_root"]) if d.get("share_of_root") is not None else "n/a", "path": d["path"]}
                for d in win.get("top_drivers", [])]
        wins.append({"key": w, "ok": True, "from": win["from"], "to": win["to"],
                     "change": f"{fmt.value(win['root_from'], ru)} → {fmt.value(win['root_to'], ru)} ({fmt.delta(win['root_change'], ru)})",
                     "svg": _svg(svg), "tops": tops, "inexact": win.get("inexact_nodes") or []})
    ok = [w["key"] for w in wins if w["ok"]]
    default = "3y" if "3y" in ok else (ok[0] if ok else (wins[0]["key"] if wins else ""))
    return {"id": tid, "title": t["title"], "root_name": rname, "windows": wins, "default": default, "origin": t.get("origin", ""),
            "note": t.get("note") or "", "replaces": t.get("replaces") or "", "fallback_for": t.get("fallback_for") or ""}


def driver_views(rep: Dict) -> Dict:
    drivers = rep.get("drivers") or {}
    roe = next((t for t in ROE_TREES if t in drivers and any(w.get("status") == "ok" for w in drivers[t]["windows"].values())),
               next((t for t in ROE_TREES if t in drivers), None))
    roic = "roic_tree" if "roic_tree" in drivers else None
    others = [t for t in drivers if t not in (roe, roic) and t not in ROE_TREES]
    fam = rep["company"]["family"]
    return {"roe": _tree_view(rep, roe) if roe else None, "roic": _tree_view(rep, roic) if roic else None,
            "roic_na": say("empty.roic_bank", family=fam.replace("_", "-")) if not roic and fam != "non_financial" else "",
            "others": [_tree_view(rep, t) for t in others]}


# ---------------------------------------------------------------------------------------------- valuation
def valuation_view(rep: Dict, years: Sequence[str]) -> Dict:
    ms = rep["metrics"]
    refs = rep.get("sector_references") or {}
    rows = []
    for mid, pct_id, ind in VAL_MULTIPLES:
        m = ms.get(mid)
        if not m:
            continue
        hist = [v for v in (m.get("series") or {}).values() if v is not None]
        series = [m["series"].get(y) for y in years] if m.get("series") else []
        rows.append({"id": mid, "name": m["name"], "value": fmt.value(m.get("value"), m["unit"]), "rag": m.get("rag"),
                     "min": fmt.value(min(hist), m["unit"]) if hist else "n/a",
                     "median": fmt.value(st.median(hist), m["unit"]) if hist else "n/a",
                     "max": fmt.value(max(hist), m["unit"]) if hist else "n/a",
                     "percentile": fmt.ordinal((ms.get(pct_id) or {}).get("value")),
                     "spark": _svg(charts.sparkline(series, list(years))) if series else "",
                     "peers": _peer_text(rep, mid, m["unit"]) or "none",
                     "industry": fmt.value(refs.get(ind), "x") if ind and refs.get(ind) is not None else "n/a"})
    fin = rep["company"]["family"] != "non_financial"
    imp_id, gap_id = ("implied_growth_pb", "implied_pb_growth_minus_delivered") if fin else ("implied_growth_reverse_dcf", "implied_minus_delivered_growth")
    imp, gap = (ms.get(imp_id) or {}).get("value"), (ms.get(gap_id) or {}).get("value")
    items = []
    if imp is not None:
        items.append((("Implied by P/B (sustainable growth)" if fin else "Implied by price (reverse DCF, 10y FCF)"), imp, fmt.value(imp, "pct"), "impl"))
        if gap is not None:
            items.append(("Delivered (as used in the gap)", imp - gap, fmt.value(imp - gap, "pct"), "deliv"))
    for gid in ("revenue_cagr_3y", "revenue_cagr_5y", "revenue_cagr_10y", "pat_cagr_5y", "eps_cagr_5y", "nii_cagr_3y"):
        g = ms.get(gid)
        if g and g.get("value") is not None:
            items.append((g["name"], g["value"], fmt.value(g["value"], "pct"), "hist"))
    checks = [{"name": ms[c]["name"], "value": ms[c]["value_text"], "rag": ms[c].get("rag"), "equation": ms[c].get("equation", "")}
              for c in ("justified_pb", "pb_to_justified_pb", "ev_ic", "ev_ic_to_roic_wacc", "holdco_discount", "p_ev", gap_id)
              if c in ms and ms[c].get("value") is not None]
    return {"rows": rows, "growth_svg": _svg(charts.bars(items)) if items else "", "checks": checks,
            "industries": ", ".join(refs.get("industries") or []), "ref_asof": refs.get("as_of") or "",
            "ev_note": "EV-based multiples are not used for banks, NBFCs and insurers (debt is raw material, not financing)." if fin else "",
            "peers": ", ".join((rep.get("peers") or {}).get("tickers") or []) or say("empty.peers", fy=rep["asof"]["fy"])}


# ---------------------------------------------------------------------------------------------- flags
def _evidence(values: Dict) -> str:
    out = []
    for k, v in (values or {}).items():
        if isinstance(v, (int, float)):
            out.append(f"{k} = {v:,.4g}")
        elif v is not None:
            out.append(f"{k} = {v}")
    return "; ".join(out)


def flag_views(rep: Dict) -> Dict:
    fl = rep.get("flags") or {}
    names = {p: rep["pillars"][p]["name"] for p in rep["pillars"]}
    trig = [{"id": f["id"], "name": f["name"], "pillar": names.get(f["pillar"], f["pillar"]), "severity": f["severity"],
             "condition": f.get("condition") or "", "origin": f.get("origin") or "", "evidence": _evidence(f.get("values")),
             "text": f.get("text") or ""} for f in fl.get("triggered", [])]
    return {"triggered": trig, "not_evaluable": fl.get("not_evaluable", []), "n_clear": len(fl.get("clear", [])),
            "counts": fl.get("counts", {})}


# ---------------------------------------------------------------------------------------------- page
def _assets() -> Dict[str, Markup]:
    return {"css": Markup((TEMPLATES / "style.css").read_text()), "js": Markup((TEMPLATES / "app.js").read_text())}


def _sources(src: Dict) -> List[Dict]:
    out = []
    for k, v in sorted(src.items()):
        if isinstance(v, dict):
            text = "; ".join(f"{kk} {vv}" for kk, vv in v.items() if kk not in ("source_url", "as_of") and isinstance(vv, (str, int, float)))
            out.append({"key": k, "text": text, "url": v.get("source_url"), "as_of": v.get("as_of")})
        else:
            out.append({"key": k, "text": str(v), "url": None, "as_of": None})
    return out


def report_context(rep: Dict, cfg=None) -> Dict:
    years = _years(rep)
    f = rep.get("findings") or {}
    pills = pillar_views(rep, years)
    by_id = {p["id"]: p for p in pills}
    groups = [{"name": g, "pillars": [by_id[p] for p in ps]} for g, ps in GROUPS]
    root = rep.get("root") or {}
    coc = rep.get("cost_of_capital") or {}
    sec = rep.get("sector") or {}
    return {
        **_assets(), "katex_css": KATEX_CSS, "katex_js": KATEX_JS, "text": {k: say(f"section_intro.{k}") for k in
            ("findings", "tree", "flags", "drivers", "valuation", "missing", "bullbear")},
        "empty": {k: say(f"empty.{k}") for k in ("strengths", "weaknesses", "watch", "flags", "bull", "bear")},
        "company": rep["company"], "asof": rep["asof"], "engine": rep["engine"], "overall": rep["overall"],
        "overall_score": "n/a" if rep["overall"].get("score") is None else f"{rep['overall']['score']:.0f}",
        "verdict": f.get("verdict", ""), "lineage": " → ".join(sec.get("lineage") or []),
        "how_to_read": sec.get("how_to_read") or "", "market": {
            "price": fmt.value((rep.get("market") or {}).get("price"), "inr"),
            "mcap": fmt.value((rep.get("market") or {}).get("market_cap"), "inr_cr")},
        "coc": {"wacc": fmt.value(coc.get("wacc"), "pct"), "ke": fmt.value(coc.get("ke"), "pct"),
                "beta": f"{coc['beta']:.2f}" if coc.get("beta") is not None else "n/a", "rf": fmt.value(coc.get("rf"), "pct"),
                "erp": fmt.value(coc.get("erp"), "pct"), "rating": coc.get("rating") or "n/a"},
        "root": {"text": root.get("text", ""), "ep": fmt.crore(root.get("economic_profit")),
                 "verdict": root.get("verdict", ""), "positive": root.get("verdict", "").startswith("creates"),
                 "spark": _svg(charts.sparkline([(root.get("series") or {}).get(y) for y in years], years, w=160, h=30))},
        "lists": [("Strengths", "strengths", f.get("strengths", [])), ("Weaknesses", "weaknesses", f.get("weaknesses", [])),
                  ("Watch", "watch", f.get("watch", []))],
        "groups": groups, "pillars": pills, "switched_off": sec.get("switched_off") or [],
        "flags": flag_views(rep), "drivers": driver_views(rep), "valuation": valuation_view(rep, years),
        "missing": f.get("missing_data") or {}, "bull": f.get("bull", []), "bear": f.get("bear", []),
        "notes": rep.get("data_notes", []), "sources": _sources(coc.get("sources") or {}), "years": years,
        "pillar_name": {p["id"]: p["name"] for p in pills},
    }


def render_report(rep: Dict, cfg=None) -> str:
    return _env().get_template("report.html.j2").render(**report_context(rep, cfg))


def write_report_html(rep: Dict, out_dir: Path, cfg=None) -> Path:
    p = Path(out_dir) / "report.html"
    p.write_text(render_report(rep, cfg), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------------------------- compare
def compare_context(reps: List[Dict]) -> Dict:
    pillar_names = [PILLAR_NAMES[p] for p in PILLARS]  # the fixed tree's names (sector renames shown per cell)
    cols = []
    for r in reps:
        best = {}
        for p in PILLARS:
            mids = [m for m in r["pillars"][p].get("metrics", []) if r["metrics"][m].get("composite") is not None
                    and r["metrics"][m].get("role") in ("scored", "root")]
            if mids:
                hi = max(mids, key=lambda m: (r["metrics"][m]["composite"], m))
                lo = min(mids, key=lambda m: (r["metrics"][m]["composite"], m))
                best[p] = {"best": f"{r['metrics'][hi]['name']} {fmt.value(r['metrics'][hi]['value'], r['metrics'][hi]['unit'])}",
                           "worst": "" if hi == lo else f"{r['metrics'][lo]['name']} {fmt.value(r['metrics'][lo]['value'], r['metrics'][lo]['unit'])}"}
        cols.append({"ticker": r["company"]["ticker"], "name": r["company"]["name"], "archetype": r["company"]["archetype"],
                     "fy": r["asof"]["fy"], "overall": "n/a" if r["overall"].get("score") is None else f"{r['overall']['score']:.0f}",
                     "overall_rag": r["overall"].get("rag"), "verdict": (r.get("findings") or {}).get("verdict", ""),
                     "ep": fmt.crore((r.get("root") or {}).get("economic_profit")),
                     "pillars": [{"score": "n/a" if r["pillars"][p].get("score") is None else f"{r['pillars'][p]['score']:.0f}",
                                  "alias": r["pillars"][p]["name"] if r["pillars"][p]["name"] != PILLAR_NAMES[p] else "",
                                  "rag": r["pillars"][p].get("rag"), "weight": r["pillars"][p].get("weight"), **best.get(p, {"best": "", "worst": ""})}
                                 for p in PILLARS],
                     "flags": (r.get("flags") or {}).get("counts", {})})
    series = [(c["ticker"], [r["pillars"][p].get("score") for p in PILLARS]) for c, r in zip(cols, reps)]
    archetypes = sorted({c["archetype"] for c in cols})
    return {**_assets(), "cols": cols, "pillar_names": pillar_names, "svg": _svg(charts.grouped_bars(pillar_names, series)),
            "mixed": len(archetypes) > 1, "archetypes": ", ".join(archetypes),
            "engine": reps[0]["engine"], "fys": ", ".join(sorted({c["fy"] for c in cols}))}


def render_compare(reps: List[Dict]) -> str:
    return _env().get_template("compare.html.j2").render(**compare_context(reps))
