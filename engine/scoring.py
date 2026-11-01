"""Scoring: level, trend, stability -> composite -> green/amber/red; pillar and overall roll-ups.
Rules and parameters live in config/scoring.yaml; docs/methodology.md explains them with worked examples.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import Config, ConfigError
from .expr import Missing, eval_number
from .registry import PILLARS, REGISTRY, Metric
from .standardise import fy_year

THIRD = 100.0 / 3.0


def band_vars(cfg: Config, coc) -> Dict[str, float]:
    cur = coc.current
    return {
        "wacc": float(cur["wacc"]), "ke": float(cur["ke"]), "rf": float(cur["rf"]), "tax_rate": float(cfg.mv("tax", "statutory_rate")),
        "inflation_target": float(cfg.mv("macro", "inflation_target")),
        "nominal_gdp_growth": float(cfg.mv("macro", "nominal_gdp_growth")),
        "terminal_growth": float(cfg.mv("valuation", "terminal_growth")),
    }


def find_band(mid: str, archetype: str, family: str, cfg: Config) -> Tuple[Optional[Dict], Optional[str]]:
    b = ((cfg.bands.get("archetype") or {}).get(archetype) or {}).get(mid)
    if b:
        return b, f"config/bands.yaml (archetype: {archetype})"
    b = ((cfg.sector.get("bands") or {}).get(archetype) or {}).get(mid)
    if b:
        return b, f"config/sector_benchmarks.yaml ({archetype})"
    b = ((cfg.bands.get("family") or {}).get(family) or {}).get(mid)
    if b:
        return b, f"config/bands.yaml (family: {family})"
    b = (cfg.bands.get("generic") or {}).get(mid)
    if b:
        return b, "config/bands.yaml (generic)"
    return None, None


def resolve_band(band: Dict, direction: str, vars_: Dict[str, float], mid: str) -> Dict[str, float]:
    keys = ("green_low", "green_high", "red_low", "red_high") if direction == "target" else ("red", "green")
    out = {}
    for k in keys:
        if k not in band:
            raise ConfigError(f"band for {mid} lacks '{k}'")
        out[k] = eval_number(band[k], vars_)
    if direction == "higher" and not out["green"] > out["red"]:
        raise ConfigError(f"band for {mid}: higher-is-better needs green > red ({out})")
    if direction == "lower" and not out["green"] < out["red"]:
        raise ConfigError(f"band for {mid}: lower-is-better needs green < red ({out})")
    return out


def band_score(v: float, b: Dict[str, float], direction: str) -> float:
    if direction == "higher":
        x = (v - b["red"]) / (b["green"] - b["red"])
    elif direction == "lower":
        x = (b["red"] - v) / (b["red"] - b["green"])
    else:  # target
        gl, gh, rl, rh = b["green_low"], b["green_high"], b["red_low"], b["red_high"]
        if gl <= v <= gh:
            return 75.0
        if v < gl:
            w = gl - rl
            return float(np.clip(THIRD + (75 - THIRD) * (v - rl) / w if v >= rl else THIRD - THIRD * (rl - v) / w, 0, 100))
        w = rh - gh
        return float(np.clip(THIRD + (75 - THIRD) * (rh - v) / w if v <= rh else THIRD - THIRD * (v - rh) / w, 0, 100))
    return float(np.clip(THIRD + THIRD * x, 0.0, 100.0))


def percentile_score(v: float, peers: List[float], direction: str) -> float:
    n = len(peers)
    below = sum(1 for p in peers if p < v)
    equal = sum(1 for p in peers if p == v) - 1  # exclude self
    pct = (below + 0.5 * max(equal, 0)) / (n - 1)
    return 100.0 * (pct if direction == "higher" else 1 - pct)


def rag_from(score: Optional[float], green_min: float, red_max: float, strict_red: bool = False) -> str:
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return "n/a"
    if score >= green_min:
        return "green"
    if (score < red_max) if strict_red else (score <= red_max):
        return "red"
    return "amber"


def _window(series: pd.Series, asof: str, n: int) -> pd.Series:
    y1 = fy_year(asof)
    s = series.dropna()
    keep = {lab: v for lab, v in s.items() if y1 - n < fy_year(lab) <= y1}
    return pd.Series(keep, dtype=float)


def trend_stats(series: pd.Series, m: Metric, asof: str, cfg: Config) -> Optional[Dict]:
    tc = cfg.scoring["trend"]
    w = _window(series, asof, int(tc["window_years"]))
    if len(w) < int(tc["min_points"]):
        return None
    x = np.array([fy_year(l) for l in w.index], dtype=float)
    y = w.values.astype(float)
    xm = x.mean()
    den = ((x - xm) ** 2).sum()
    slope = float(((x - xm) * (y - y.mean())).sum() / den) if den else 0.0
    floor = float(cfg.scoring["unit_floors"].get(m.unit, 1.0))
    scale = max(abs(float(y.mean())), floor)
    norm = slope / scale
    out = {"slope_per_year": slope, "normalised_slope": norm, "n": int(len(w)), "window": f"{w.index[0]}-{w.index[-1]}"}
    if m.direction in ("higher", "lower"):
        d = 1.0 if m.direction == "higher" else -1.0
        out["score"] = 50.0 + 50.0 * math.tanh(d * norm / float(tc["scale_k"]))
        dn = d * norm
        out["label"] = "improving" if dn >= tc["improving_min"] else ("deteriorating" if dn <= tc["deteriorating_max"] else "stable")
    else:
        out["score"] = None
        out["label"] = "rising" if norm >= tc["improving_min"] else ("falling" if norm <= tc["deteriorating_max"] else "flat")
    return out


def stability_stats(series: pd.Series, m: Metric, asof: str, cfg: Config) -> Optional[Dict]:
    sc = cfg.scoring["stability"]
    w = _window(series, asof, int(sc["window_years"]))
    if len(w) < int(sc["min_points"]):
        return None
    floor = float(cfg.scoring["unit_floors"].get(m.unit, 1.0))
    sd = float(w.std(ddof=1))
    cv = sd / max(abs(float(w.mean())), floor)
    score = 100.0 * math.exp(-cv / float(sc["cv_scale"]))
    label = "stable" if cv <= sc["stable_max"] else ("volatile" if cv >= sc["volatile_min"] else "moderate")
    return {"cv": cv, "sd": sd, "n": int(len(w)), "score": score if m.direction != "neutral" else None, "label": label,
            "window": f"{w.index[0]}-{w.index[-1]}"}


def score_metric(mid: str, series: pd.Series, asof: str, cfg: Config, archetype: str, family: str, vars_: Dict[str, float],
                 peers: Optional[List[float]] = None) -> Dict:
    m = REGISTRY[mid]
    value = series.iloc[-1] if len(series) else np.nan
    res: Dict = {"value": None if pd.isna(value) else float(value), "level": None, "trend": None, "stability": None,
                 "composite": None, "rag": "n/a"}
    scorable = m.role == "scored" and m.direction != "neutral"
    if m.trend:
        res["trend"] = trend_stats(series, m, asof, cfg)
    if m.stability:
        res["stability"] = stability_stats(series, m, asof, cfg)
    band, origin = find_band(mid, archetype, family, cfg)
    if band is not None:
        try:
            rb = resolve_band(band, m.direction if m.direction != "neutral" else "higher", vars_, mid)
        except (ConfigError, Missing):
            rb = None
        res["band"] = {**(rb or {}), "origin": origin, "source_type": band.get("source_type", "external"),
                       "source_url": band.get("source_url"), "as_of": band.get("as_of"),
                       "rationale": band.get("rationale") or band.get("derivation"), "centre": band.get("centre")}
    if not scorable:
        res["reason"] = "informational (neutral direction)" if m.direction == "neutral" else f"{m.role} metric (not scored)"
        return res
    lc = cfg.scoring["level"]
    if res["value"] is None:
        res["reason"] = "no value for the as-of year"
    else:
        v = res["value"]
        need = ("green_low", "green_high", "red_low", "red_high") if m.direction == "target" else ("red", "green")
        band_ok = bool(res.get("band")) and all(k in res["band"] for k in need)
        if peers is not None and len(peers) >= int(lc["min_peers_for_percentile"]):
            s = percentile_score(v, peers, m.direction)
            res["level"] = {"score": s, "basis": "percentile", "n_peers": len(peers)}
        elif band_ok:
            s = band_score(v, {k: res["band"][k] for k in need}, m.direction)
            res["level"] = {"score": s, "basis": "band"}
        else:
            res["reason"] = "no sourced band and fewer than 4 same-archetype peers: level not scored"
        if res["level"]:
            res["level"]["rag"] = rag_from(res["level"]["score"], lc["rag_green_min"], lc["rag_red_max"])
    comp = cfg.scoring["composite"]
    if res["level"]:
        parts = {"level": res["level"]["score"]}
        if res["trend"] and res["trend"].get("score") is not None:
            parts["trend"] = res["trend"]["score"]
        if res["stability"] and res["stability"].get("score") is not None:
            parts["stability"] = res["stability"]["score"]
        w = comp["weights"]
        tot = sum(w[k] for k in parts)
        score = sum(w[k] * parts[k] for k in parts) / tot
        res["composite"] = score
        rag = rag_from(score, comp["rag_green_min"], comp["rag_red_max"], strict_red=True)
        lrag = res["level"]["rag"]
        tlab = (res["trend"] or {}).get("label")
        if lrag == "red" and rag == "green":
            rag = "amber"
        if lrag == "red" and tlab == "deteriorating":
            rag = "red"
        res["rag"] = rag
        res["components_used"] = sorted(parts)
    return res


def weighted(scores: List[Tuple[float, float]]) -> Optional[float]:
    tot = sum(w for _, w in scores)
    return sum(s * w for s, w in scores) / tot if tot > 0 else None


def roll_up(metric_results: Dict[str, Dict], family: str, cfg: Config, triggered_flags: List[Dict]) -> Tuple[Dict, Dict]:
    pc = cfg.scoring["pillar"]
    mw = cfg.scoring.get("metric_weights", {}) or {}
    fam_key = family if family in cfg.scoring["pillar_weights"] else "non_financial"
    pw = cfg.scoring["pillar_weights"][fam_key]
    high_by_pillar: Dict[str, List[str]] = {}
    for f in triggered_flags:
        if f.get("severity") == "high":
            high_by_pillar.setdefault(f["pillar"], []).append(f["id"])
    pillars = {}
    for p in PILLARS:
        items = [(mid, r) for mid, r in metric_results.items() if REGISTRY[mid].pillar == p and REGISTRY[mid].role == "scored"
                 and REGISTRY[mid].direction != "neutral"]
        scored = [(r["composite"], float(mw.get(mid, pc["default_metric_weight"]))) for mid, r in items if r.get("composite") is not None]
        score = weighted(scored)
        rag = rag_from(score, pc["rag_green_min"], pc["rag_red_max"], strict_red=True)
        capped = False
        if pc.get("high_flag_caps_at_amber") and high_by_pillar.get(p) and rag == "green":
            rag, capped = "amber", True
        counts = {k: sum(1 for _, r in items if r.get("rag") == k) for k in ("green", "amber", "red", "n/a")}
        pillars[p] = {"score": score, "rag": rag, "weight": float(pw.get(p, 0)), "n_scored": len(scored), "n_metrics": len(items),
                      "rag_counts": counts, "capped_by_flags": high_by_pillar.get(p, []) if capped else []}
    oc = cfg.scoring["overall"]
    avail = [(v["score"], v["weight"]) for v in pillars.values() if v["score"] is not None and v["weight"] > 0]
    total_w = sum(v["weight"] for v in pillars.values() if v["weight"] > 0)
    score = weighted(avail)
    rag = rag_from(score, oc["rag_green_min"], oc["rag_red_max"], strict_red=True)
    n_high = sum(1 for f in triggered_flags if f.get("severity") == "high")
    capped = False
    if n_high >= int(oc["high_flags_cap_at_amber"]) and rag == "green":
        rag, capped = "amber", True
    overall = {"score": score, "rag": rag, "coverage": (sum(w for _, w in avail) / total_w) if total_w else 0.0,
               "high_flags": n_high, "capped_by_flags": capped, "weights_basis": fam_key}
    return pillars, overall
