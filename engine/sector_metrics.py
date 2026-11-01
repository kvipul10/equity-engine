"""Sector metrics defined in config/sectors/*.yaml (formula + equation + meaning), registered into the metric registry.

A formula is evaluated once per fiscal year t with functions anchored at t (safe expression language, no eval):
  f(field, lag=0)        standardised field (data/processed/<T>/*.csv)
  kpi(name, lag=0)       manual KPI (data/manual/<T>_kpis.csv; % values already divided by 100)
  m(metric, lag=0)       another registered metric
  avg(ident)             opening/closing average (fields use the period's real opening balance; KPIs/metrics t-1)
  growth(ident, years=1) x_t / x_t-years - 1 (base > 0)
  cagr(ident, n)         (x_t / x_t-n)^(1/n) - 1 (both > 0)
  mean_last(ident, n, min_n=n) / min_last / max_last / sum_last(ident, n)
  at_min(x, y, n)        y in the year (within the last n) where x was lowest (e.g. leverage at the cycle trough)
  slope_last(y, x, n, min_n=4)  OLS slope of y on x over the last n years
  mcap_now()             market cap: export-date value in the as-of year of a latest run, else FY-end
  nan()                  not-a-number (for 'x if cond else nan()')
  abs, min, max
Identifiers passed as strings may carry a namespace prefix: 'f:revenue', 'kpi:advances_cr', 'm:roe'. Unprefixed
names resolve as metric, then field, then KPI. Constants declared in the sector file are available as names.
A missing input makes that year NaN; the missing input is reported in the metric note.
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
import pandas as pd

from .expr import Missing, compile_expr, evaluate
from .standardise import fy_year

FORMULA_FUNCS = {"f", "kpi", "m", "avg", "growth", "cagr", "mean_last", "min_last", "max_last", "sum_last", "at_min",
                 "slope_last", "mcap_now", "nan", "abs", "min", "max", "first_of"}
NAN = float("nan")


def _isnan(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


class YearFuncs:
    def __init__(self, c, lab: str):
        self.c = c
        self.lab = lab
        self.y = fy_year(lab)

    def series(self, ident: str) -> pd.Series:
        from .registry import REGISTRY

        c = self.c
        if ident.startswith("kpi:"):
            return c.manual_series(ident[4:])
        if ident.startswith("f:"):
            return c.f(ident[2:])
        if ident.startswith("m:"):
            return c.m(ident[2:])
        if ident in REGISTRY and REGISTRY[ident].applies_to(c.tokens):
            return c.m(ident)
        if ident in c.a.columns:
            return c.f(ident)
        if c.manual is not None and not c.manual.empty and ident in c.manual.columns:
            return c.manual_series(ident)
        raise Missing(f"{ident} (unknown or not applicable)")

    def val(self, ident: str, lag: int = 0) -> float:
        lab = self.c.label_of.get(self.y - int(lag))
        if lab is None:
            raise Missing(f"{ident} at t-{int(lag)}")
        v = self.series(ident).get(lab, NAN)
        if _isnan(v):
            kind = "manual KPI" if ident.startswith("kpi:") else "value"
            raise Missing(f"{ident.replace('kpi:', '')} {lab} ({kind})")
        return float(v)

    def window(self, ident: str, n: int) -> List[float]:
        out = []
        for k in range(int(n)):
            try:
                out.append(self.val(ident, k))
            except Missing:
                pass
        return out

    def funcs(self) -> Dict:
        c = self.c

        def f(field, lag=0):
            return self.val(f"f:{field}", lag)

        def kpi(name, lag=0):
            return self.val(f"kpi:{name}", lag)

        def m(mid, lag=0):
            return self.val(f"m:{mid}", lag)

        def avg(ident):
            if ident.startswith("f:") or (ident in c.a.columns and ":" not in ident):
                fld = ident[2:] if ident.startswith("f:") else ident
                v = c.avg(fld).get(self.lab, NAN)
                if _isnan(v):
                    raise Missing(f"{fld} opening/closing {self.lab}")
                return float(v)
            return (self.val(ident) + self.val(ident, 1)) / 2.0

        def growth(ident, years=1):
            base = self.val(ident, years)
            if base <= 0:
                raise Missing(f"{ident}: base <= 0")
            return self.val(ident) / base - 1.0

        def cagr(ident, n):
            a, b = self.val(ident), self.val(ident, n)
            if a <= 0 or b <= 0:
                raise Missing(f"{ident}: non-positive value for CAGR")
            return (a / b) ** (1.0 / n) - 1.0

        def _need(vals, n, min_n, ident):
            need = int(min_n) if min_n is not None else int(n)
            if len(vals) < need:
                raise Missing(f"{ident}: {len(vals)} of {need} years available")
            return vals

        def mean_last(ident, n, min_n=None):
            v = _need(self.window(ident, n), n, min_n, ident)
            return float(sum(v) / len(v))

        def min_last(ident, n, min_n=None):
            return float(min(_need(self.window(ident, n), n, min_n, ident)))

        def max_last(ident, n, min_n=None):
            return float(max(_need(self.window(ident, n), n, min_n, ident)))

        def sum_last(ident, n):
            return float(sum(self.val(ident, k) for k in range(int(n))))

        def at_min(x, yid, n):
            best = None
            for k in range(int(n)):
                try:
                    xv = self.val(x, k)
                except Missing:
                    continue
                if best is None or xv < best[0]:
                    best = (xv, k)
            if best is None:
                raise Missing(f"{x}: no values in window")
            return self.val(yid, best[1])

        def slope_last(yid, x, n, min_n=4):
            pts = []
            for k in range(int(n)):
                try:
                    pts.append((self.val(x, k), self.val(yid, k)))
                except Missing:
                    continue
            if len(pts) < int(min_n):
                raise Missing(f"{yid} vs {x}: {len(pts)} points (< {int(min_n)})")
            xs = np.array([p[0] for p in pts])
            ys = np.array([p[1] for p in pts])
            den = ((xs - xs.mean()) ** 2).sum()
            if den == 0:
                raise Missing(f"{x}: no variation")
            return float(((xs - xs.mean()) * (ys - ys.mean())).sum() / den)

        def mcap_now():
            if self.lab == c.asof and (c.snapshot or {}).get("market_cap"):
                return float(c.snapshot["market_cap"])
            return self.val("f:market_cap")

        return {"f": f, "kpi": kpi, "m": m, "avg": avg, "growth": growth, "cagr": cagr, "mean_last": mean_last,
                "min_last": min_last, "max_last": max_last, "sum_last": sum_last, "at_min": at_min,
                "slope_last": slope_last, "mcap_now": mcap_now, "nan": lambda: NAN, "abs": abs, "min": min, "max": max,
                "first_of": lambda *a: next((x for x in a if not (isinstance(x, float) and x != x)), NAN)}  # lazy in expr.evaluate


def make_func(mid: str, formula: str, kind: str, constants_by_archetype: Dict[str, Dict[str, float]]):
    tree = compile_expr(formula, FORMULA_FUNCS)

    def func(c):
        names = dict(constants_by_archetype.get(c.std.archetype, {}))
        out, last_missing = [], None
        for lab in c.idx:
            if kind == "point" and lab != c.asof:
                out.append(NAN)
                continue
            try:
                v = evaluate(tree, names, YearFuncs(c, lab).funcs())
                v = NAN if v is None else float(v)
            except Missing as e:
                v = NAN
                if lab == c.asof:
                    last_missing = e.what
            out.append(v)
        if last_missing:
            c.info[mid] = f"n/a in {c.asof}: missing {last_missing}"
        return pd.Series(out, index=c.idx, dtype=float)

    return func


REQUIRED_KEYS = ("id", "name", "pillar", "unit", "direction", "formula", "equation", "meaning")


def register(sectors) -> List[str]:
    """Register every sector metric (idempotent; a changed definition replaces the old one)."""
    from .registry import REGISTRY, Metric, validate_fields

    defs: Dict[str, Dict] = {}
    applies: Dict[str, List[str]] = {}
    origin: Dict[str, str] = {}
    for arch, s in sectors.items():
        for mid, d in s.metrics_add.items():
            for k in REQUIRED_KEYS:
                if k not in d:
                    raise ValueError(f"{s.file}: sector metric '{mid}' lacks '{k}'")
            key = {k: d.get(k) for k in REQUIRED_KEYS + ("role", "kind", "trend", "stability")}
            if mid in defs and defs[mid] != key:
                raise ValueError(f"sector metric '{mid}' is defined differently in two sector files ({origin[mid]} and {s.file}); "
                                 f"define it once in a shared base and inherit it")
            defs[mid] = key
            applies.setdefault(mid, []).append(arch)
            origin.setdefault(mid, (sectors[arch].file if not d.get("_origin") else d["_origin"]))
    consts = {a: s.constant_values() for a, s in sectors.items()}
    registered = []
    for mid, d in defs.items():
        if mid in REGISTRY and getattr(REGISTRY[mid], "origin", "engine") == "engine":
            raise ValueError(f"sector metric '{mid}' clashes with an engine metric of the same id")
        kind = d.get("kind") or "annual"
        validate_fields(mid, d["pillar"], d["direction"], d["unit"], d.get("role") or "scored", kind)
        compile_expr(d["formula"], FORMULA_FUNCS)
        REGISTRY[mid] = Metric(
            id=mid, name=d["name"], pillar=d["pillar"], unit=d["unit"], direction=d["direction"],
            applies=tuple(sorted(applies[mid])), meaning=d["meaning"], equation=d["equation"],
            func=make_func(mid, d["formula"], kind, consts), role=d.get("role") or "scored",
            trend=bool(d.get("trend", True)) and kind == "annual", stability=bool(d.get("stability", True)) and kind == "annual",
            kind=kind, origin=origin[mid], formula=d["formula"])
        registered.append(mid)
    return registered
