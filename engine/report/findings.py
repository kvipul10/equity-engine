"""Strengths / Weaknesses / Watch, driver chains, bull/bear starter and the missing-data map.

Everything here is computed from the report dict (analysis.json) plus the configs, so it is deterministic and
testable without HTML. Ranking = severity x confidence (config/scoring.yaml: report):

  metric severity  = |composite - 50| / 50 x pillar weight factor x role factor
                     (watch list: the larger of the composite and trend-score distances from 50)
  flag severity    = high 1.0 / medium 0.6 / low 0.3
  confidence       = data coverage (years with data / 5, capped at 1) x level source (external band or peer
                     percentile 1.0, derived 0.9, indicative 0.6, no band 0.5) x 0.8 if an unverified manual KPI
                     feeds the metric
"""
from __future__ import annotations

import copy
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import yaml
from jinja2 import Environment, StrictUndefined

from ..registry import PILLARS, REGISTRY
from . import formats as fmt

TEMPLATES = Path(__file__).resolve().parent / "templates"
RAGS = ("green", "amber", "red")

DEFAULTS = {
    "severity": {"flag": {"high": 1.0, "medium": 0.6, "low": 0.3},
                 "role": {"scored": 1.0, "root": 1.0, "component": 0.67},
                 "pillar_weight_floor": 0.25},
    "confidence": {"years_full": 5, "point_metric_coverage": 0.6, "unverified_kpi": 0.8,
                   "source": {"percentile": 1.0, "external": 1.0, "derived": 0.9, "indicative": 0.6,
                              "rule_of_thumb": 0.6, "none": 0.5}},
    "lists": {"max_items": 6, "max_per_pillar": 2, "watch_fast_trend_score": 25},
    "bullbear": {"max_items": 8, "from_lists": 4, "cheap_percentile": 0.3, "rich_percentile": 0.7,
                 "relative_gap": 0.2},
    "driver_window_order": ["3y", "5y", "1y"],
    "driver_tree_order": ["bank_dupont", "fin_roe", "roe_dupont", "roic_tree", "eps_tree"],
    "estimate_note_categories": ["exceptional", "capex", "lease", "minority", "stale", "reclassification"],
}

MULTIPLES = [("pe", "pe_percentile_10y", "trailing_pe"), ("pb", "pb_percentile_10y", "pbv"),
             ("ev_ebitda", "ev_ebitda_percentile_10y", "ev_ebitda")]
HURDLE_NAMES = {"wacc": "WACC", "ke": "cost of equity"}


# ---------------------------------------------------------------------------------------------- config + text
def report_cfg(cfg) -> Dict:
    out = copy.deepcopy(DEFAULTS)
    user = (getattr(cfg, "scoring", None) or {}).get("report") or {}

    def merge(a, b):
        for k, v in b.items():
            if isinstance(v, dict) and isinstance(a.get(k), dict):
                merge(a[k], v)
            else:
                a[k] = v
    merge(out, user)
    return out


@lru_cache(maxsize=1)
def text_templates() -> Dict:
    return yaml.safe_load((TEMPLATES / "text.yaml").read_text())


_ENV = Environment(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=False)


@lru_cache(maxsize=None)
def _compiled(src: str):
    return _ENV.from_string(src)


def say(path: str, **kw) -> str:
    """Render the text template at a dotted path of templates/text.yaml."""
    node = text_templates()
    for part in path.split("."):
        node = node[part]
    return " ".join(_compiled(node).render(**kw).split())


def rag_word(r) -> str:
    return say(f"rag_word.{r if r in RAGS else 'none'}")


def mid_sentence(name: str) -> str:
    """'Asset turnover' -> 'asset turnover'; acronyms ('EBIT margin', 'DSO', 'P/E') stay as they are."""
    if len(name) > 1 and (name[1].isupper() or not name[1].isalpha()):
        return name
    return name[:1].lower() + name[1:]


# ---------------------------------------------------------------------------------------------- KPI dependency map
_CALL = re.compile(r"(\w+)\(\s*'([\w:]+)'")
_QUOTED = re.compile(r"'([\w:]+)'")


def _refs(expr: str, metric_ids: Set[str], kpi_ids: Set[str]) -> Tuple[Set[str], Set[str]]:
    """(metric ids, kpi ids) referenced by a sector formula or a flag condition."""
    expr = expr or ""
    funcs = {}
    for fn, arg in _CALL.findall(expr):
        funcs.setdefault(arg, fn)
    ms, ks = set(), set()
    for q in _QUOTED.findall(expr):
        fn = funcs.get(q)
        if q.startswith("kpi:"):
            ks.add(q[4:])
        elif fn == "kpi":
            ks.add(q)
        elif fn == "f":
            continue
        elif q in metric_ids:
            ms.add(q)
        elif q in kpi_ids:
            ks.add(q)
    return ms, ks


def kpi_dependencies(cfg, archetype: str) -> Dict[str, Dict[str, List[str]]]:
    """For every manual KPI of the archetype: the metrics (transitively), flags and driver trees that use it.
    Built statically from the sector formulas, flag conditions and tree nodes, so it does not depend on data."""
    from ..drivers import Tree

    sec = cfg.sector_of(archetype)
    kpi_ids = set(sec.manual_kpis)
    metric_ids = set(REGISTRY)
    direct: Dict[str, Tuple[Set[str], Set[str]]] = {}
    for mid, spec in sec.metrics_add.items():
        direct[mid] = _refs(spec.get("formula", ""), metric_ids, kpi_ids)

    memo: Dict[str, Set[str]] = {}

    def kpis_of(mid: str, seen=()) -> Set[str]:
        if mid in memo:
            return memo[mid]
        if mid not in direct or mid in seen:
            return set()
        ms, ks = direct[mid]
        out = set(ks)
        for m in ms:
            out |= kpis_of(m, seen + (mid,))
        memo[mid] = out
        return out

    deps = {k: {"metrics": set(), "flags": set(), "trees": set()} for k in kpi_ids}
    metric_kpis: Dict[str, Set[str]] = {}
    for mid in direct:
        ks = kpis_of(mid)
        metric_kpis[mid] = ks
        for k in ks:
            deps.setdefault(k, {"metrics": set(), "flags": set(), "trees": set()})["metrics"].add(mid)
    for r in cfg.rules_for(archetype):
        ms, ks = _refs(r.get("condition", ""), metric_ids, kpi_ids)
        for m in ms:
            ks |= metric_kpis.get(m, set())
        for k in ks:
            deps.setdefault(k, {"metrics": set(), "flags": set(), "trees": set()})["flags"].add(r["id"])
    specs = list((cfg.drivers or {}).get("trees") or []) + list(sec.drivers_add)
    for spec in specs:
        t = Tree(spec)
        for n in t.nodes():
            ks = {n[4:]} if n.startswith("kpi:") else metric_kpis.get(n, set())
            for k in ks:
                deps.setdefault(k, {"metrics": set(), "flags": set(), "trees": set()})["trees"].add(t.id)
    return {k: {kk: sorted(vv) for kk, vv in v.items()} for k, v in sorted(deps.items())}


def metric_kpi_map(deps: Dict) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for k, d in deps.items():
        for m in d["metrics"]:
            out.setdefault(m, set()).add(k)
    return out


# ---------------------------------------------------------------------------------------------- scoring of candidates
def pillar_factor(rep: Dict, pillar: str, rc: Dict) -> float:
    ws = [float(p.get("weight") or 0) for p in rep["pillars"].values()]
    mx = max(ws) if ws else 0
    w = float(rep["pillars"].get(pillar, {}).get("weight") or 0)
    if mx <= 0:
        return 1.0
    return max(w / mx, float(rc["severity"]["pillar_weight_floor"]))


def coverage_factor(m: Dict, rc: Dict) -> float:
    s = m.get("series") or {}
    if not s:
        return float(rc["confidence"]["point_metric_coverage"])
    n = sum(1 for v in s.values() if v is not None)
    return min(1.0, n / float(rc["confidence"]["years_full"]))


def source_factor(m: Dict, rc: Dict) -> float:
    src = rc["confidence"]["source"]
    lv = m.get("level") or {}
    if lv.get("basis") == "percentile":
        return float(src["percentile"])
    if lv.get("basis") == "band":
        st = (m.get("band") or {}).get("source_type") or "none"
        return float(src.get(st, src["none"]))
    return float(src["none"])


def family_key(mid: str) -> str:
    """Variants of one concept share a key, so a list shows the concept once (revenue_cagr_3y ~ revenue_cagr_5y)."""
    k = mid
    for pat in (r"_percentile_10y$", r"_(3y|5y|10y|1y)$", r"_(ttm|yoy|qoq)$"):
        k = re.sub(pat, "", k)
    return k


def level_context(m: Dict) -> str:
    rag = rag_word(m.get("rag"))
    lv = m.get("level") or {}
    b = m.get("band") or {}
    if lv.get("basis") == "band" and "red" in b and "green" in b:
        hi = m.get("direction") == "higher"
        return say("level_context.band", rag=rag, red_op="≤" if hi else "≥", green_op="≥" if hi else "≤",
                   red=fmt.value(b["red"], m["unit"]), green=fmt.value(b["green"], m["unit"]),
                   indicative=b.get("source_type") in ("indicative", "rule_of_thumb"))
    if lv.get("basis") == "percentile":
        return say("level_context.percentile", rag=rag, pct=fmt.ordinal((lv.get("score") or 0) / 100.0),
                   n=lv.get("n_peers", 0))
    return say("level_context.none", rag=rag)


def trend_text(m: Dict) -> str:
    t = m.get("trend") or {}
    if not t.get("label") or t.get("slope_per_year") is None:
        return ""
    return say("trend", label=t["label"], slope=fmt.slope(t["slope_per_year"], m["unit"]), window=t.get("window", ""))


# ---------------------------------------------------------------------------------------------- driver chains
def _children(nodes: Dict, path: str) -> List[str]:
    return [n for n, v in nodes.items() if v["path"].rsplit(" > ", 1)[0] == path and v["path"] != path]


def _move(d: float) -> str:
    if d is None or abs(d) < 1e-12:
        return say("move.flat")
    return say("move.up" if d > 0 else "move.down")


def _best(nodes: Dict, ids: Iterable[str], sign: float) -> Optional[str]:
    best, val = None, 0.0
    for n in sorted(ids):
        c = nodes[n].get("contribution")
        if c is None:
            continue
        if c * sign > val + 1e-15:
            best, val = n, c * sign
    return best


def chain_for_node(mid: str, win: Dict, window: str, root_name: str) -> Optional[str]:
    """Chain text for a node of one computed decomposition window (see module docstring for the shape)."""
    nodes = win.get("nodes") or {}
    nd = nodes.get(mid)
    if not nd:
        return None
    c = nd.get("contribution")
    if c is None or abs(c) < 1e-12:
        return None
    sign = 1.0 if c > 0 else -1.0
    if nd["leaf"]:
        share = nd.get("share_of_root")
        if share is None:
            return None
        root = next(v for v in nodes.values() if " > " not in v["path"])
        return say("chain.as_leaf", share=fmt.pct(share), root=root_name, window=window,
                   root_delta=fmt.delta(root["change"], root["unit"]))
    parts = [say("chain.head", name=nd["name"], delta=fmt.delta(nd["change"], nd["unit"]), window=window)]
    child = _best(nodes, _children(nodes, nd["path"]), sign)
    if child is None:
        return parts[0]
    ch = nodes[child]
    share = ch["contribution"] / c
    parts.append(say("chain.share_offset" if share > 1.0 else "chain.share", share=fmt.pct(share), child=mid_sentence(ch["name"])))
    if ch["leaf"]:
        parts.append(say("chain.leaf_only", child=mid_sentence(ch["name"]), child_move=_move(ch["change"]),
                         a=fmt.value(ch["t0"], ch["unit"]), b=fmt.value(ch["t1"], ch["unit"])))
    else:
        leaves = [n for n, v in nodes.items() if v["leaf"] and v["path"].startswith(ch["path"] + " > ")]
        leaf = _best(nodes, leaves, 1.0 if ch["contribution"] > 0 else -1.0)
        if leaf is not None:
            lf = nodes[leaf]
            parts.append(say("chain.because", child=mid_sentence(ch["name"]), child_move=_move(ch["change"]),
                             leaf=mid_sentence(lf["name"]), leaf_move=_move(lf["change"]),
                             a=fmt.value(lf["t0"], lf["unit"]), b=fmt.value(lf["t1"], lf["unit"])))
    return "; ".join(parts)


def tree_order(rep: Dict, rc: Dict) -> List[str]:
    pref = [t for t in rc["driver_tree_order"] if t in rep.get("drivers", {})]
    return pref + sorted(t for t in rep.get("drivers", {}) if t not in pref)


def driver_chain(mid: str, rep: Dict, rc: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    """Prefer a tree where the metric is the root or an inner node (so the chain can say *why*); else a leaf."""
    for want_leaf in (False, True):
        for tid in tree_order(rep, rc):
            t = rep["drivers"][tid]
            for w in rc["driver_window_order"]:
                win = (t.get("windows") or {}).get(w) or {}
                if win.get("status") != "ok":
                    continue
                nd = (win.get("nodes") or {}).get(mid)
                if not nd or bool(nd["leaf"]) != want_leaf:
                    continue
                root_name = REGISTRY[t["root"]].name if t["root"] in REGISTRY else t["root"]
                txt = chain_for_node(mid, win, w, mid_sentence(root_name))
                if txt:
                    return txt, {"tree": tid, "window": w}
    return None, None


# ---------------------------------------------------------------------------------------------- lists
def _metric_item(mid: str, m: Dict, rep: Dict, rc: Dict, unverified: Set[str], mk: Dict[str, Set[str]],
                 watch: bool = False) -> Dict:
    comp = float(m["composite"])
    dist = abs(comp - 50.0) / 50.0
    if watch and (m.get("trend") or {}).get("score") is not None:
        dist = max(dist, abs(float(m["trend"]["score"]) - 50.0) / 50.0)
    sev = dist * pillar_factor(rep, m["pillar"], rc) * float(rc["severity"]["role"].get(m["role"], 1.0))
    q = float(rc["confidence"]["unverified_kpi"]) if (mk.get(mid, set()) & unverified) else 1.0
    conf = coverage_factor(m, rc) * source_factor(m, rc) * q
    chain, chain_src = driver_chain(mid, rep, rc)
    value, context, trend = fmt.value(m.get("value"), m["unit"]), level_context(m), trend_text(m)
    return {"kind": "metric", "id": mid, "pillar": m["pillar"], "rag": m.get("rag"), "severity": round(sev, 6),
            "confidence": round(conf, 6), "score": round(sev * conf, 6), "name": m["name"], "number": value,
            "context": context, "trend": trend, "chain": chain, "chain_source": chain_src,
            "text": say("finding.metric", name=m["name"], value=value, context=context, trend=trend, chain=chain)}


def _flag_item(f: Dict, rep: Dict, rc: Dict, unverified: Set[str], mk: Dict[str, Set[str]], kpi_ids: Set[str]) -> Dict:
    ms, ks = _refs(f.get("condition") or "", set(REGISTRY), kpi_ids)
    used = set(ks)
    for m in ms:
        used |= mk.get(m, set())
    sev = float(rc["severity"]["flag"][f["severity"]])
    conf = float(rc["confidence"]["unverified_kpi"]) if used & unverified else 1.0
    return {"kind": "flag", "id": f["id"], "pillar": f["pillar"], "severity_label": f["severity"],
            "severity": round(sev, 6), "confidence": round(conf, 6), "score": round(sev * conf, 6), "name": f["name"],
            "covers": sorted(ms), "text": say("finding.flag", id=f["id"], name=f["name"], text=f.get("text", ""))}


def select(cands: List[Dict], rc: Dict) -> List[Dict]:
    """Top items by score (ties by id), at most max_per_pillar per pillar, one per concept, and no metric that a
    flag in the same list already covers."""
    covered = set()
    for c in cands:
        if c["kind"] == "flag":
            covered |= set(c.get("covers", []))
    out, per_pillar, fams = [], {}, set()
    for c in sorted(cands, key=lambda c: (-c["score"], c["kind"] != "flag", c["id"])):
        if len(out) >= int(rc["lists"]["max_items"]):
            break
        if per_pillar.get(c["pillar"], 0) >= int(rc["lists"]["max_per_pillar"]):
            continue
        if c["kind"] == "metric":
            if c["id"] in covered or family_key(c["id"]) in fams:
                continue
            fams.add(family_key(c["id"]))
        if c["score"] <= 0:
            continue
        per_pillar[c["pillar"]] = per_pillar.get(c["pillar"], 0) + 1
        out.append(c)
    return out


def unverified_kpis(rep: Dict) -> Set[str]:
    fy = rep["asof"]["fy"]
    out = set()
    for k, d in (rep.get("manual_kpis") or {}).items():
        v = (d.get("values") or {}).get(fy)
        if v and str(v.get("verified", "N")).upper() != "Y":
            out.add(k)
    return out


def classify(m: Dict, rc: Dict) -> Optional[str]:
    """strengths / weaknesses / watch for one metric (a partition: a metric appears in one list at most)."""
    rag, t = m.get("rag"), m.get("trend") or {}
    if rag not in RAGS or m.get("composite") is None:
        return None
    label, tscore = t.get("label"), t.get("score")
    if rag == "green":
        if tscore is not None and tscore <= float(rc["lists"]["watch_fast_trend_score"]):
            return "watch"
        return "strengths"
    if rag == "red":
        return "watch" if label == "improving" else "weaknesses"
    return "watch" if label == "deteriorating" else None


# ---------------------------------------------------------------------------------------------- verdict, bull/bear
def verdict(rep: Dict) -> str:
    root, ov = rep.get("root") or {}, rep.get("overall") or {}
    v = str(root.get("verdict") or "")
    key = "creates" if v.startswith("creates") else "destroys" if v.startswith("destroys") else "unknown"
    scored = [(p, d) for p, d in rep["pillars"].items() if d.get("score") is not None and (d.get("weight") or 0) > 0]
    best = max(scored, key=lambda x: (x[1]["score"], x[0]))[1]["name"] if scored else ""
    worst = min(scored, key=lambda x: (x[1]["score"], x[0]))[1]["name"] if scored else ""
    rm = root.get("return_metric")
    ret_name = rep["metrics"][rm]["name"] if rm in rep["metrics"] else str(rm or "return").upper()
    hm = root.get("hurdle_metric")
    return say("verdict", company=rep["company"]["name"],
               ep_verdict=say(f"ep_verdict.{key}"), ret_name=ret_name, ret=fmt.value(root.get("return"), "pct"),
               hurdle_name=HURDLE_NAMES.get(hm, str(hm or "hurdle")), hurdle=fmt.value(root.get("hurdle"), "pct"),
               fy=rep["asof"]["fy"], rag=rag_word(ov.get("rag")),
               score=f"{ov['score']:.0f}" if ov.get("score") is not None else "n/a", best=best, worst=worst,
               high=int((rep.get("flags") or {}).get("counts", {}).get("high", 0)))


def _median(xs: List[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _top_leaf(rep: Dict, rc: Dict, sign: float) -> Optional[Dict]:
    """Largest leaf of the first computable window of the first tree in tree order (the ROE tree when it exists)."""
    for tid in tree_order(rep, rc):
        t = rep["drivers"][tid]
        for w in rc["driver_window_order"]:
            win = (t.get("windows") or {}).get(w) or {}
            if win.get("status") != "ok":
                continue
            tops = [x for x in win.get("top_drivers", []) if (x.get("contribution") or 0) * sign > 0]
            if not tops:
                return None
            root_name = REGISTRY[t["root"]].name if t["root"] in REGISTRY else t["root"]
            return {"tree": tid, "window": w, "root": mid_sentence(root_name), "text": tops[0]["text"]}
    return None


def bull_bear(rep: Dict, lists: Dict, rc: Dict, missing: Dict) -> Tuple[List[Dict], List[Dict]]:
    bb = rc["bullbear"]
    ms = rep["metrics"]
    root = rep.get("root") or {}
    bull = [{"ref": c["id"], "text": say("bull.strength", text=c["text"], id=c["id"])} for c in lists["strengths"][:bb["from_lists"]]]
    bear = [{"ref": c["id"], "text": say("bear.weakness", text=c["text"], id=c["id"])} for c in lists["weaknesses"][:bb["from_lists"]]]
    v = str(root.get("verdict") or "")
    if root.get("economic_profit") is not None and (v.startswith("creates") or v.startswith("destroys")):
        rm, hm = root.get("return_metric"), root.get("hurdle_metric")
        kw = dict(ret_name=ms[rm]["name"] if rm in ms else str(rm).upper(), ret=fmt.value(root.get("return"), "pct"),
                  hurdle_name=HURDLE_NAMES.get(hm, str(hm)), hurdle=fmt.value(root.get("hurdle"), "pct"),
                  ep=fmt.crore(root["economic_profit"]), fy=rep["asof"]["fy"], pos=root.get("positive_years", 0),
                  n=root.get("years", 0))
        (bull if v.startswith("creates") else bear).append({"ref": "economic_profit", "text": say("bull.ep" if v.startswith("creates") else "bear.ep", **kw)})
    refs = rep.get("sector_references") or {}
    peers = (rep.get("peers") or {}).get("values") or {}
    for mid, pct_id, ind_key in MULTIPLES:
        m = ms.get(mid)
        if not m or m.get("value") is None or m["value"] <= 0:
            continue
        name, val = m["name"], fmt.value(m["value"], m["unit"])
        p = (ms.get(pct_id) or {}).get("value")
        if p is not None:
            if p <= bb["cheap_percentile"]:
                bull.append({"ref": pct_id, "text": say("bull.cheap_history", name=name, value=val, pct=fmt.ordinal(p), id=pct_id)})
            elif p >= bb["rich_percentile"]:
                bear.append({"ref": pct_id, "text": say("bear.rich_history", name=name, value=val, pct=fmt.ordinal(p), id=pct_id)})
        pv = [x for x in (peers.get(mid) or {}).values() if x is not None and x > 0]
        if pv:
            med = _median(pv)
            ptxt = ", ".join(f"{t} {fmt.value(x, m['unit'])}" for t, x in sorted((peers.get(mid) or {}).items()) if x is not None)
            if m["value"] <= med * (1 - bb["relative_gap"]):
                bull.append({"ref": mid, "text": say("bull.cheap_peers", name=name, value=val, peers=ptxt, id=mid)})
            elif m["value"] >= med * (1 + bb["relative_gap"]):
                bear.append({"ref": mid, "text": say("bear.rich_peers", name=name, value=val, peers=ptxt, id=mid)})
        iv = refs.get(ind_key)
        if iv is not None and iv > 0:
            kw = dict(name=name, value=val, industry=fmt.value(iv, "x"), industries=", ".join(refs.get("industries") or []), id=mid)
            if m["value"] <= iv * (1 - bb["relative_gap"]):
                bull.append({"ref": mid, "text": say("bull.cheap_industry", **kw)})
            elif m["value"] >= iv * (1 + bb["relative_gap"]):
                bear.append({"ref": mid, "text": say("bear.rich_industry", **kw)})
    gap = (ms.get("implied_minus_delivered_growth") or {}).get("value")
    imp = (ms.get("implied_growth_reverse_dcf") or {}).get("value")
    if gap is not None and imp is not None:
        kw = dict(implied=fmt.value(imp, "pct"), delivered=fmt.value(imp - gap, "pct"), gap=fmt.delta(gap, "pct"))
        (bull if gap < 0 else bear).append({"ref": "implied_minus_delivered_growth", "text": say("bull.growth_gap" if gap < 0 else "bear.growth_gap", **kw)})
    pos, neg = _top_leaf(rep, rc, 1.0), _top_leaf(rep, rc, -1.0)
    if pos:
        bull.append({"ref": pos["tree"], "text": say("bull.driver", **pos)})
    if neg:
        bear.append({"ref": neg["tree"], "text": say("bear.driver", **neg)})
    req = [k for k in missing.get("kpis", []) if k["required"]]
    if req:
        hit = {REGISTRY[m].pillar for k in req for m in k["metrics"] if m in REGISTRY}
        pillars = [p for p in PILLARS if p in hit]
        names = [rep["pillars"][p]["name"] for p in pillars if p in rep["pillars"]]
        bear.append({"ref": "missing data", "text": say("bear.missing", n=len(req), fy=rep["asof"]["fy"],
                                                     kpis=", ".join(k["kpi"] for k in req),
                                                     pillars=", ".join(names) or "the sector KPIs")})
    return bull[:bb["max_items"]], bear[:bb["max_items"]]


# ---------------------------------------------------------------------------------------------- missing data
def missing_data(rep: Dict, cfg, deps: Dict, rc: Dict) -> Dict:
    fy = rep["asof"]["fy"]
    ms = rep["metrics"]
    sec = rep.get("sector") or {}
    ne = {f["id"]: f for f in (rep.get("flags") or {}).get("not_evaluable", [])}
    drivers = rep.get("drivers") or {}
    replaced = {t.get("fallback_for"): tid for tid, t in drivers.items() if t.get("fallback_for")}
    kpis = []
    for k in sec.get("manual_kpis", []):
        if k.get("present_asof"):
            continue
        d = deps.get(k["id"], {"metrics": [], "flags": [], "trees": []})
        mets = [m for m in d["metrics"] if m in ms and ms[m].get("value") is None]
        mets += sorted(m for m, v in ms.items() if m not in mets and k["id"] in str(v.get("note") or ""))
        flags = [f for f in d["flags"] if f in ne]
        trees = []
        for t in d["trees"]:
            if t in replaced:
                trees.append({"id": t, "text": drivers[replaced[t]].get("note") or ""})
            elif t in drivers and not any(w.get("status") == "ok" for w in drivers[t]["windows"].values()):
                trees.append({"id": t, "text": next((w.get("reason") for w in drivers[t]["windows"].values() if w.get("reason")), "")})
        if not k.get("required") and not (mets or flags or trees):
            continue
        lines = [say("missing.kpi", kpi=k["id"], description=k.get("description", ""), fy=fy,
                     years=", ".join(k.get("years_present") or []))]
        if mets:
            lines.append(say("missing.metrics", n=len(mets), names=", ".join(ms[m]["name"] for m in mets)))
        if flags:
            lines.append(say("missing.flags", ids=", ".join(flags)))
        if trees:
            lines.append(say("missing.trees", trees="; ".join(f"{t['id']} ({t['text']})" if t["text"] else t["id"] for t in trees)))
        if not (mets or flags or trees):
            lines.append(say("missing.none"))
        kpis.append({"kpi": k["id"], "required": bool(k.get("required")), "description": k.get("description", ""),
                     "years_present": k.get("years_present") or [], "metrics": mets, "flags": flags,
                     "trees": [t["id"] for t in trees], "lines": lines})
    kpis.sort(key=lambda x: (not x["required"], x["kpi"]))
    total = sum(len(d.get("values") or {}) for d in (rep.get("manual_kpis") or {}).values())
    unver = sum(1 for d in (rep.get("manual_kpis") or {}).values() for v in (d.get("values") or {}).values()
                if str(v.get("verified", "N")).upper() != "Y")
    reasons: Dict[str, int] = {}
    for m in ms.values():
        if m.get("role") == "scored" and m.get("rag") is None and m.get("value") is not None and m.get("reason"):
            reasons[m["reason"]] = reasons.get(m["reason"], 0) + 1
    not_scored = [say("missing.not_scored", n=n, reason=r) for r, n in sorted(reasons.items(), key=lambda x: (-x[1], x[0]))]
    cats = set(rc["estimate_note_categories"])
    return {
        "kpis": kpis,
        "all_required_present": not any(k["required"] for k in kpis),
        "all_present_text": say("missing.all_present", fy=fy),
        "not_evaluable": [{"id": f["id"], "name": f["name"], "missing": f.get("missing")} for f in ne.values()],
        "unverified": {"n": unver, "total": total,
                       "text": say("missing.unverified", n=unver, total=total, share=fmt.pct(unver / total)) if total else None},
        "not_scored": not_scored,
        "estimates": [n["text"] for n in rep.get("data_notes", []) if n.get("category") in cats],
        "driver_notes": [t["note"] for t in drivers.values() if t.get("note")],
    }


# ---------------------------------------------------------------------------------------------- entry point
def build_findings(rep: Dict, cfg) -> Dict:
    rc = report_cfg(cfg)
    arch = rep["company"]["archetype"]
    deps = kpi_dependencies(cfg, arch)
    mk = metric_kpi_map(deps)
    unver = unverified_kpis(rep)
    kpi_ids = set(cfg.sector_of(arch).manual_kpis)
    cands = {"strengths": [], "weaknesses": [], "watch": []}
    for mid, m in rep["metrics"].items():
        lst = classify(m, rc)
        if lst:
            cands[lst].append(_metric_item(mid, m, rep, rc, unver, mk, watch=(lst == "watch")))
    for f in (rep.get("flags") or {}).get("triggered", []):
        lst = "watch" if f["severity"] == "low" else "weaknesses"
        cands[lst].append(_flag_item(f, rep, rc, unver, mk, kpi_ids))
    lists = {k: select(v, rc) for k, v in cands.items()}
    miss = missing_data(rep, cfg, deps, rc)
    bull, bear = bull_bear(rep, lists, rc, miss)
    return {"verdict": verdict(rep), **lists, "bull": bull, "bear": bear, "missing_data": miss,
            "method": "severity x confidence; see config/scoring.yaml: report and engine/report/findings.py"}
