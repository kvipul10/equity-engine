"""Assemble analysis.json / metrics.csv and the console summary. All text comes from fixed templates."""
from __future__ import annotations

import datetime as _dt
import json
import math
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import __version__
from .registry import PILLAR_NAMES, PILLARS, REGISTRY


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 6)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp, _dt.date)):
        return o.isoformat()
    return o


def fmt(v, unit: str) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    if unit == "pct":
        return f"{v * 100:.1f}%"
    if unit == "pp":
        return f"{v * 100:+.1f}pp"
    if unit == "x":
        return f"{v:.2f}x"
    if unit == "days":
        return f"{v:.0f} days"
    if unit == "inr_cr":
        return f"Rs {v:,.0f} cr"
    if unit == "count":
        return f"{v:.0f}"
    return f"{v:.2f}"


def _band_text(r: Dict, unit: str, direction: str) -> str:
    b = r.get("band") or {}
    if "red" not in b or "green" not in b:
        return ""
    if direction == "higher":
        return f"red <= {fmt(b['red'], unit)}, green >= {fmt(b['green'], unit)}"
    return f"green <= {fmt(b['green'], unit)}, red >= {fmt(b['red'], unit)}"


def metric_text(mid: str, r: Dict, note: Optional[str]) -> str:
    m = REGISTRY[mid]
    parts = [f"{m.name}: {fmt(r.get('value'), m.unit)}"]
    if r.get("rag") and r["rag"] != "n/a":
        lvl = r.get("level") or {}
        ind = " indicative" if (r.get("band") or {}).get("source_type") == "indicative" else ""
        basis = (f"vs {lvl.get('n_peers')} same-archetype peers" if lvl.get("basis") == "percentile"
                 else f"vs{ind} band ({_band_text(r, m.unit, m.direction)})")
        parts.append(f"{r['rag'].upper()} (level {lvl.get('rag')} {basis}")
        t = r.get("trend")
        if t:
            parts[-1] += f"; trend {t['label']} {fmt(t['slope_per_year'], 'pp' if m.unit in ('pct', 'pp') else m.unit)}/yr"
        s = r.get("stability")
        if s:
            parts[-1] += f"; {s['label']} (CV {s['cv']:.2f})"
        parts[-1] += ")"
    elif r.get("reason"):
        parts.append(f"[{r['reason']}]")
    if note:
        parts.append(f"Note: {note}")
    return " ".join(parts)


def _series_dict(s: pd.Series) -> Dict:
    return {k: (None if pd.isna(v) else float(v)) for k, v in s.items()}


def _dupont(metrics: Dict[str, pd.Series], years: List[str], fin: bool) -> Dict:
    out = {"three_step": {}, "five_step": {}}
    keys3 = ["roe", "pat_margin", "asset_turnover", "equity_multiplier"] if not fin else ["roe", "roa", "equity_multiplier"]
    keys5 = ["roe", "attributable_factor", "tax_burden", "interest_burden", "ebit_margin", "asset_turnover", "equity_multiplier"]
    for y in years[-5:]:
        out["three_step"][y] = {k: (float(metrics[k][y]) if k in metrics and not pd.isna(metrics[k][y]) else None) for k in keys3}
        if not fin:
            out["five_step"][y] = {k: (float(metrics[k][y]) if k in metrics and not pd.isna(metrics[k][y]) else None) for k in keys5}
    out["identity"] = ("ROE = ROA x equity multiplier (financials)" if fin else
                       "ROE = net margin x asset turnover x equity multiplier; net margin = attributable factor x tax burden x "
                       "interest burden x EBIT margin")
    return out


def _driver_unit(node: str) -> str:
    if node in REGISTRY:
        u = REGISTRY[node].unit
        if node.endswith("_to_sales") and REGISTRY[node].pillar == "capital_efficiency":
            return "days_of_sales"
        return u
    return "inr_cr" if node in ("revenue",) else "num"


def _fmt_change(node: str, d: float) -> str:
    u = _driver_unit(node)
    if u == "days_of_sales":
        return f"{d * 365:+.0f} days of sales"
    if u in ("pct", "pp"):
        return f"{d * 100:+.1f}pp"
    if u == "x":
        return f"{d:+.2f}x"
    if u == "inr_cr":
        return f"{d:+,.0f} cr"
    return f"{d:+.3f}"


def _driver_texts(drivers: Dict) -> Dict:
    out = {}
    for tid, t in drivers.items():
        root = t["root"]
        ru = REGISTRY[root].unit if root in REGISTRY else "num"
        wins = {}
        for w, r in t["windows"].items():
            if r.get("status") != "ok":
                wins[w] = {"status": "n/a", "reason": r.get("reason")}
                continue
            d = r["root_change"]
            tops = []
            for row in r.get("top_drivers", []):
                share = row["share_of_root"]
                tops.append({
                    "driver": row["driver"], "name": REGISTRY[row["driver"]].name if row["driver"] in REGISTRY else row["driver"],
                    "contribution": row["contribution"], "share_of_root": share, "own_change": row["change"],
                    "own_change_text": _fmt_change(row["driver"], row["change"]), "path": row["path"],
                    "text": f"{REGISTRY[row['driver']].name if row['driver'] in REGISTRY else row['driver']} "
                            f"({_fmt_change(row['driver'], row['change'])}) -> {fmt(row['contribution'], 'pp' if ru in ('pct', 'pp') else ru)}"
                            + (f" ({share * 100:.0f}% of the change)" if share is not None and abs(d) > 1e-9 else ""),
                })
            mids = {n: v for n, v in r["nodes"].items() if n != root and n not in r["leaves"]}
            wins[w] = {
                "status": "ok", "from": r["t0"], "to": r["t1"],
                "root_from": r["nodes"][root]["t0"], "root_to": r["nodes"][root]["t1"], "root_change": d,
                "residual": r["residual"], "inexact_nodes": r["inexact_nodes"],
                "intermediate": {n: {"change": v["change"], "contribution": v["contribution"], "share_of_root": v["share_of_root"],
                                     "method": v["method"]} for n, v in mids.items()},
                "top_drivers": tops,
                "text": (f"{REGISTRY[root].name if root in REGISTRY else root} moved from {fmt(r['nodes'][root]['t0'], ru)} to "
                         f"{fmt(r['nodes'][root]['t1'], ru)} ({r['t0']}->{r['t1']}). Largest drivers: "
                         + "; ".join(x["text"] for x in tops[:3]) + "."),
            }
        out[tid] = {"title": t["title"], "root": root, "windows": wins,
                    **{k: t[k] for k in ("origin", "replaces", "fallback_for", "note") if k in t}}
    return out


def _root(metrics, coc, std, results) -> Dict:
    fin = std.family != "non_financial"
    ep = metrics.get("economic_profit")
    last = std.last_fy
    v = None if ep is None or pd.isna(ep[last]) else float(ep[last])
    if fin:
        ret, hurdle, rname, hname = metrics.get("roe", pd.Series(dtype=float)).get(last), coc.ke.get(last), "ROE", "Ke"
    else:
        ret, hurdle, rname, hname = metrics.get("roic", pd.Series(dtype=float)).get(last), coc.wacc.get(last), "ROIC", "WACC"
    verdict = "n/a" if v is None else ("creates value" if v > 0 else "destroys value")
    ep_s = ep.dropna() if ep is not None else pd.Series(dtype=float)
    pos_years = int((ep_s > 0).sum())
    trend = (results.get("economic_profit") or {}).get("trend")
    ret_txt = fmt(None if ret is None or pd.isna(ret) else float(ret), "pct")
    hur_txt = fmt(None if hurdle is None or pd.isna(hurdle) else float(hurdle), "pct")
    note = ""
    if not fin and (ret is None or pd.isna(ret)):
        ic = std.annual["invested_capital"].get(last)
        if ic is not None and not pd.isna(ic) and ic <= 0:
            note = " ROIC is not meaningful because invested capital is negative (operations are funded by customers/suppliers)."
    text = (f"{verdict.capitalize() if v is not None else 'Cannot judge value creation'}: {rname} {ret_txt} vs {hname} {hur_txt} "
            f"in {last} -> economic profit {fmt(v, 'inr_cr')}. Economic profit was positive in {pos_years} of {len(ep_s)} years"
            + (f"; trend {trend['label']}" if trend else "") + "." + note)
    return {"economic_profit": v, "series": _series_dict(ep) if ep is not None else {}, "return_metric": rname,
            "return": None if ret is None or pd.isna(ret) else float(ret), "hurdle_metric": hname,
            "hurdle": None if hurdle is None or pd.isna(hurdle) else float(hurdle), "verdict": verdict,
            "positive_years": pos_years, "years": int(len(ep_s)), "text": text}


def _pillar_text(p: str, pv: Dict, results: Dict, flags: List[Dict]) -> str:
    items = [(mid, r) for mid, r in results.items() if REGISTRY[mid].pillar == p and r.get("composite") is not None]
    if pv["score"] is None:
        return f"{PILLAR_NAMES[p]}: not scored (no metric with a level for this company)."
    best = sorted(items, key=lambda x: -x[1]["composite"])[:2]
    worst = sorted(items, key=lambda x: x[1]["composite"])[:2]
    fl = [f["id"] for f in flags if f["pillar"] == p and f["status"] == "triggered"]
    return (f"{PILLAR_NAMES[p]}: {pv['rag'].upper()} ({pv['score']:.0f}/100, {pv['n_scored']} scored metrics). "
            f"Strongest: {', '.join(f'{REGISTRY[m].name} {fmt(r['value'], REGISTRY[m].unit)} ({r['rag']})' for m, r in best)}. "
            f"Weakest: {', '.join(f'{REGISTRY[m].name} {fmt(r['value'], REGISTRY[m].unit)} ({r['rag']})' for m, r in worst)}."
            + (f" Flags: {', '.join(fl)}." if fl else ""))


def build_report(comp, results: Dict, pillars: Dict, overall: Dict, flags: List[Dict], drivers: Dict, cfg, names: Dict) -> Dict:
    std, coc, metrics, ctx = comp.std, comp.coc, comp.metrics, comp.ctx
    last = std.last_fy
    fin = std.family != "non_financial"
    mout = {}
    for mid, s in metrics.items():
        m = REGISTRY[mid]
        r = results.get(mid, {})
        mout[mid] = {
            "name": m.name, "pillar": m.pillar, "role": m.role, "unit": m.unit, "direction": m.direction, "kind": m.kind,
            "equation": m.equation, "formula": m.formula or None, "origin": m.origin, "meaning": m.meaning,
            "value": r.get("value"), "value_text": fmt(r.get("value"), m.unit),
            "series": _series_dict(s) if m.kind == "annual" else {}, "level": r.get("level"), "trend": r.get("trend"),
            "stability": r.get("stability"), "composite": r.get("composite"), "rag": r.get("rag"), "band": r.get("band"),
            "reason": r.get("reason"), "note": ctx.info.get(mid), "text": metric_text(mid, r, ctx.info.get(mid)),
        }
    for p in PILLARS:
        pillars[p]["name"] = cfg.sector_of(std.archetype).pillar_names.get(p, PILLAR_NAMES[p])
        pillars[p]["summary"] = _pillar_text(p, pillars[p], results, flags)
        pillars[p]["metrics"] = [mid for mid in metrics if REGISTRY[mid].pillar == p]
        pillars[p]["flags_triggered"] = [f["id"] for f in flags if f["pillar"] == p and f["status"] == "triggered"]
    triggered = [f for f in flags if f["status"] == "triggered"]
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    triggered.sort(key=lambda f: (sev_rank[f["severity"]], f["id"]))
    snap = std.snapshot or {}
    ev_cur = None
    if snap.get("market_cap") is not None and std.family == "non_financial":
        a = std.annual.loc[last]
        ev_cur = snap["market_cap"] + a["borrowings"] - a["cash"] - (a["investments"] if cfg.mv("valuation", "ev_subtract_investments", default=True) else 0)
    info = cfg.archetype_info(std.archetype)
    rep = {
        "engine": {"name": "equity-diagnostic-engine", "version": __version__, "generated_on": _dt.date.today().isoformat(),
                   "note": "Deterministic: no network, no LLM. Diagnoses financials only; strategy and management judgement stay with the analyst."},
        "company": {"ticker": std.ticker, "name": std.company, "archetype": std.archetype, "family": std.family,
                    "damodaran_industries": info.get("damodaran_industries")},
        "asof": {"fy": last, "mode": "as-of (truncated, no look-ahead)" if std.meta.get("asof") else "latest",
                 "period_end": std.annual.loc[last, "period_end"], "data_window": f"{std.export_years[0]}-{last}",
                 "n_years": len(std.export_years),
                 "manual_kpi_window": (f"{std.manual.index[0]}-{std.manual.index[-1]}" if std.manual is not None and not std.manual.empty else None), "latest_quarter_used": (std.quarterly.index[-1] if std.quarterly is not None and not std.quarterly.empty else None),
                 "price_basis": snap.get("basis")},
        "market": {"price": snap.get("price"), "market_cap": snap.get("market_cap"), "shares_cr": snap.get("shares_cr"),
                   "enterprise_value": ev_cur},
        "cost_of_capital": {**{k: v for k, v in coc.current.items()}, "sources": coc.sources, "notes": coc.notes,
                            "series": {"wacc": _series_dict(coc.wacc), "ke": _series_dict(coc.ke), "beta": _series_dict(coc.beta)}},
        "root": _root(metrics, coc, std, results),
        "overall": overall,
        "pillars": pillars,
        "dupont": _dupont(metrics, std.years, fin),
        "drivers": _driver_texts(drivers),
        "flags": {
            "triggered": triggered,
            "clear": [f["id"] for f in flags if f["status"] == "clear"],
            "not_evaluable": [{"id": f["id"], "name": f["name"], "missing": f.get("missing")} for f in flags if f["status"] == "not_evaluable"],
            "counts": {s: sum(1 for f in triggered if f["severity"] == s) for s in ("high", "medium", "low")},
        },
        "metrics": mout,
        "sector_references": (cfg.sector.get("references") or {}).get(std.archetype),
        "sector": _sector_section(cfg, std, ctx, results, flags),
        "manual_kpis": _manual_section(cfg, std),
        "data_notes": std.notes,
    }
    return _clean(rep)


def _sector_section(cfg, std, ctx, results: Dict, flags: List[Dict]) -> Dict:
    sec = cfg.sector_of(std.archetype)
    last = std.last_fy
    man = std.manual if std.manual is not None else pd.DataFrame()
    years5 = [y for y in std.export_years][-5:]
    req = []
    for kid, k in sec.manual_kpis.items():
        have = [y for y in years5 if not man.empty and kid in man.columns and y in man.index and not pd.isna(man.loc[y, kid])]
        req.append({"id": kid, "unit": k.get("unit"), "required": bool(k.get("required")), "description": k.get("description"),
                    "years_present": have, "present_asof": last in have})
    n_req = [r for r in req if r["required"]]
    prov = std.manual_provenance if std.manual_provenance is not None else pd.DataFrame()
    ind = sorted(mid for mid, r in results.items() if (r.get("band") or {}).get("source_type") == "indicative" and r.get("level"))
    sec_flags = [f["id"] for f in flags if f.get("origin", "").startswith("config/sectors/") and f["status"] == "triggered"]
    return {
        "archetype": sec.archetype, "lineage": sec.lineage, "file": sec.file, "family": sec.family,
        "how_to_read": sec.how_to_read,
        "switched_off": [{"id": mid, "name": REGISTRY[mid].name if mid in REGISTRY else mid, "reason": why}
                         for mid, why in sorted(ctx.switched_off.items()) if mid in REGISTRY and REGISTRY[mid].applies_to(ctx.tokens)],
        "switched_off_groups": [{**g, "n_metrics": sum(1 for m in REGISTRY.values() if tuple(m.applies) == (g["applies"],))}
                                for g in getattr(ctx, "switched_off_groups", [])],
        "manual_kpis": req,
        "required_kpis_present_asof": f"{sum(1 for r in n_req if r['present_asof'])}/{len(n_req)}",
        "missing_required_asof": [r["id"] for r in n_req if not r["present_asof"]],
        "kpi_values": int(len(prov)), "kpi_verified_share": (float((prov["verified"] == "Y").mean()) if len(prov) else None),
        "indicative_bands_used": ind,
        "sector_flags_triggered": sec_flags,
        "constants": {k: {kk: v.get(kk) for kk in ("value", "source_url", "as_of", "rationale") if v.get(kk) is not None}
                      for k, v in sec.constants.items()},
    }


def _manual_section(cfg, std) -> Dict:
    prov = std.manual_provenance if std.manual_provenance is not None else pd.DataFrame()
    if prov is None or not len(prov):
        return {}
    sec = cfg.sector_of(std.archetype)
    out: Dict[str, Dict] = {}
    for _, r in prov.iterrows():
        k = r["kpi"]
        d = out.setdefault(k, {"unit": r["unit"], "description": (sec.manual_kpis.get(k) or {}).get("description"), "values": {}})
        d["values"][r["fy"]] = {"value": r["value"], "raw_value": r["raw_value"], "unit": r["unit"], "source_url": r["source_url"],
                                "source_date": r["source_date"], "verified": r["verified"]}
    return out


METRIC_CSV_FIXED = ["metric_id", "name", "pillar", "role", "unit", "direction"]


def metrics_frame(rep: Dict) -> pd.DataFrame:
    years: List[str] = []
    for m in rep["metrics"].values():
        for y in m["series"]:
            if y not in years:
                years.append(y)
    rows = []
    for mid, m in rep["metrics"].items():
        row = {"metric_id": mid, "name": m["name"], "pillar": m["pillar"], "role": m["role"], "unit": m["unit"], "direction": m["direction"],
               "origin": m.get("origin")}
        for y in years:
            row[y] = m["series"].get(y)
        lvl, tr, st, b = m.get("level") or {}, m.get("trend") or {}, m.get("stability") or {}, m.get("band") or {}
        row.update({
            "value": m["value"], "level_score": lvl.get("score"), "level_rag": lvl.get("rag"), "level_basis": lvl.get("basis"),
            "band_red": b.get("red"), "band_green": b.get("green"), "band_origin": b.get("origin"),
            "band_source_type": b.get("source_type"),
            "trend_label": tr.get("label"), "trend_normalised_slope": tr.get("normalised_slope"), "trend_score": tr.get("score"),
            "stability_label": st.get("label"), "stability_cv": st.get("cv"), "stability_score": st.get("score"),
            "composite": m.get("composite"), "rag": m.get("rag"), "note": m.get("note") or m.get("reason"), "equation": m["equation"],
        })
        rows.append(row)
    df = pd.DataFrame(rows)
    order = {p: i for i, p in enumerate(("root",) + PILLARS)}
    df["_o"] = df["pillar"].map(order)
    df = df.sort_values(["_o"], kind="stable").drop(columns="_o")
    return df


def out_dir_for(paths, ticker: str, rep: Dict) -> Path:
    base = paths.reports_dir / ticker
    if rep["asof"]["mode"] != "latest":
        return base / f"asof_{rep['asof']['fy']}"
    return base


def write_outputs(rep: Dict, out_dir: Path) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pj = out_dir / "analysis.json"
    pj.write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=False))
    pc = out_dir / "metrics.csv"
    metrics_frame(rep).to_csv(pc, index=False, float_format="%.6f")
    return {"analysis": pj, "metrics": pc}


def console_summary(rep: Dict) -> str:
    c, o, a = rep["company"], rep["overall"], rep["asof"]
    lines = [f"{c['ticker']} - {c['name']} ({c['archetype']}), as of {a['fy']} [{a['mode']}]",
             f"Overall: {(o['rag'] or 'n/a').upper()} {('%.0f' % o['score']) if o['score'] is not None else 'n/a'}/100 "
             f"(coverage {o['coverage'] * 100:.0f}%, high flags {o['high_flags']})",
             f"Root: {rep['root']['text']}",
             f"Cost of capital: Ke {rep['cost_of_capital']['ke'] * 100:.2f}%, WACC {rep['cost_of_capital']['wacc'] * 100:.2f}% "
             f"(rf {rep['cost_of_capital']['rf'] * 100:.2f}%, beta {rep['cost_of_capital']['beta']:.2f}, ERP {rep['cost_of_capital']['erp'] * 100:.2f}%)",
             "Pillars:"]
    for p in PILLARS:
        pv = rep["pillars"][p]
        sc = f"{pv['score']:.0f}" if pv["score"] is not None else "--"
        lines.append(f"  {pv['name']:<30} {(pv['rag'] or 'n/a').upper():<6} {sc:>3}  "
                     f"g/a/r {pv['rag_counts']['green']}/{pv['rag_counts']['amber']}/{pv['rag_counts']['red']}")
    sec = rep.get("sector") or {}
    if sec:
        vs = sec.get("kpi_verified_share")
        lines.append(f"Sector: {sec['archetype']} ({' > '.join(sec['lineage'])}); required KPIs present {sec['required_kpis_present_asof']}"
                     f"; {len(sec['switched_off'])} metrics switched off; {sec['kpi_values']} manual KPI values"
                     + (f" ({vs * 100:.0f}% verified)" if vs is not None else ""))
    trig = rep["flags"]["triggered"]
    lines.append(f"Flags: {len(trig)} triggered ({rep['flags']['counts']['high']} high), "
                 f"{len(rep['flags']['not_evaluable'])} not evaluable")
    for f in trig[:8]:
        lines.append(f"  [{f['severity'].upper()}] {f['id']} {f['name']}")
    for tid in ("roe_dupont", "fin_roe"):
        t = rep["drivers"].get(tid)
        if t and t["windows"].get("3y", {}).get("status") == "ok":
            lines.append("Drivers (3y): " + t["windows"]["3y"]["text"])
    return "\n".join(lines)
