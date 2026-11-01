"""Red-flag rules engine (rules in config/flags.yaml).

Each rule: id, name, pillar, severity (high|medium|low), applies (archetype tokens), condition (safe expression),
values (named expressions for the explanation), explanation (Jinja2 template with fixed number formats).
Optional: not_for (tokens the rule is switched off for) + not_for_reason; suppresses (metric ids that cannot be listed as
strengths while the rule stands, because the rule puts their inputs or meaning in doubt).
Outcome per rule: triggered | clear | not_evaluable (data missing, with the missing input named).

Functions available in conditions (ids may be metric ids or standardised field names):
  m(id, lag=0)            value at the as-of year (or lag years earlier)
  chg(id, years)          m(id) - m(id, lag=years)
  pchg(id, years)         m(id) / m(id, lag=years) - 1 (base > 0)
  rising(id, years)       increased in each of the last `years` year-on-year steps
  falling(id, years)      decreased in each of the last `years` steps
  all_last(id, n, op, x)  condition true in each of the last n years (op: '>', '>=', '<', '<=')
  count_last(id, n, op, x) number of the last n years where the condition holds
  sum_last(id, n)         sum over the last n years
  avail(id)               True if a value exists at the as-of year (never 'missing')
  first_of(a, b, ...)     the first argument that is available (lazy fallback; a constant ends the chain)
  abs, min, max
Names: wacc, ke, rf, tax_rate, inflation_target, nominal_gdp_growth, terminal_growth.
"""
from __future__ import annotations

import math
from typing import Dict, List

import jinja2
import pandas as pd

from .expr import OPS_BY_STR, ExprError, Missing, compile_expr, evaluate
from .standardise import fy_year

FUNCS = {"m", "chg", "pchg", "rising", "falling", "all_last", "count_last", "sum_last", "avail", "abs", "min", "max", "first_of"}
SEVERITIES = ("high", "medium", "low")


def _isnan(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def fmt_pct(v, d=1):
    return "n/a" if _isnan(v) or isinstance(v, str) else f"{v * 100:.{d}f}%"


def fmt_pp(v, d=1):
    return "n/a" if _isnan(v) or isinstance(v, str) else f"{v * 100:+.{d}f}pp"


def fmt_x(v, d=1):
    return "n/a" if _isnan(v) or isinstance(v, str) else f"{v:.{d}f}x"


def fmt_days(v):
    return "n/a" if _isnan(v) or isinstance(v, str) else f"{v:.0f} days"


def fmt_cr(v):
    return "n/a" if _isnan(v) or isinstance(v, str) else f"Rs {v:,.0f} cr"


def fmt_num(v, d=2):
    return "n/a" if _isnan(v) or isinstance(v, str) else f"{v:,.{d}f}"


def jinja_env() -> jinja2.Environment:
    env = jinja2.Environment(undefined=jinja2.StrictUndefined, autoescape=False, keep_trailing_newline=False)
    env.filters.update({"pct": fmt_pct, "pp": fmt_pp, "x": fmt_x, "days": fmt_days, "cr": fmt_cr, "num": fmt_num})
    return env


class SeriesBook:
    """Resolves ids to series: metric results first, then standardised fields."""

    def __init__(self, metrics: Dict[str, pd.Series], annual: pd.DataFrame, manual: pd.DataFrame = None, info: Dict = None):
        self.info = info or {}
        self.metrics = metrics
        self.annual = annual
        self.manual = manual if manual is not None else pd.DataFrame()
        self.idx = list(annual.index)
        self.asof = self.idx[-1]
        self.y1 = fy_year(self.asof)
        self.label_of = {fy_year(l): l for l in self.idx}

    def series(self, ident: str) -> pd.Series:
        if ident.startswith("kpi:"):
            k = ident[4:]
            if not self.manual.empty and k in self.manual.columns:
                return pd.to_numeric(self.manual[k], errors="coerce").reindex(self.idx)
            raise Missing(f"{k} (manual KPI)")
        if ident in self.metrics:
            return self.metrics[ident]
        if ident in self.annual.columns:
            return pd.to_numeric(self.annual[ident], errors="coerce")
        if not self.manual.empty and ident in self.manual.columns:
            return pd.to_numeric(self.manual[ident], errors="coerce").reindex(self.idx)
        raise Missing(f"{ident} (not available for this company)")

    def at(self, ident: str, lag: int = 0) -> float:
        lab = self.label_of.get(self.y1 - int(lag))
        if lab is None:
            raise Missing(f"{ident} at t-{lag} (year not in data)")
        v = self.series(ident).get(lab)
        if _isnan(v):
            why = " (manual KPI)" if ident.startswith("kpi:") else ""
            note = self.info.get(ident) if lab == self.asof else None
            raise Missing(f"{ident.replace('kpi:', '')} {lab}{why}" + (f" [{note}]" if note else ""))
        return float(v)

    def last_n(self, ident: str, n: int) -> List[float]:
        return [self.at(ident, k) for k in range(int(n) - 1, -1, -1)]


def make_funcs(book: SeriesBook) -> Dict:
    def m(ident, lag=0):
        return book.at(ident, lag)

    def chg(ident, years):
        return book.at(ident) - book.at(ident, years)

    def pchg(ident, years):
        base = book.at(ident, years)
        if base <= 0:
            raise Missing(f"{ident}: base <= 0")
        return book.at(ident) / base - 1

    def rising(ident, years):
        v = book.last_n(ident, int(years) + 1)
        return all(b > a for a, b in zip(v, v[1:]))

    def falling(ident, years):
        v = book.last_n(ident, int(years) + 1)
        return all(b < a for a, b in zip(v, v[1:]))

    def all_last(ident, n, op, x):
        return all(OPS_BY_STR[op](v, x) for v in book.last_n(ident, n))

    def count_last(ident, n, op, x):
        return sum(1 for v in book.last_n(ident, n) if OPS_BY_STR[op](v, x))

    def sum_last(ident, n):
        return sum(book.last_n(ident, n))

    def avail(ident):
        try:
            book.at(ident)
            return True
        except Missing:
            return False

    return {"m": m, "chg": chg, "pchg": pchg, "rising": rising, "falling": falling, "all_last": all_last,
            "count_last": count_last, "sum_last": sum_last, "avail": avail, "abs": abs, "min": min, "max": max,
            "first_of": lambda *a: next((x for x in a if not _isnan(x)), float("nan"))}  # lazy in expr.evaluate


def validate_rules(rules: List[Dict]) -> None:
    seen = set()
    from .registry import PILLARS

    for r in rules:
        for k in ("id", "name", "pillar", "severity", "applies", "condition", "explanation"):
            if k not in r:
                raise ExprError(f"flag rule {r.get('id', '?')} lacks '{k}'")
        if r["id"] in seen:
            raise ExprError(f"duplicate flag id {r['id']}")
        seen.add(r["id"])
        if r["pillar"] not in PILLARS:
            raise ExprError(f"flag {r['id']}: unknown pillar {r['pillar']}")
        if r.get("not_for") and not r.get("not_for_reason"):
            raise ExprError(f"flag {r['id']}: not_for needs not_for_reason")
        if not isinstance(r.get("suppresses", []), list):
            raise ExprError(f"flag {r['id']}: suppresses must be a list of metric ids")
        if r["severity"] not in SEVERITIES:
            raise ExprError(f"flag {r['id']}: unknown severity {r['severity']}")
        compile_expr(r["condition"], FUNCS)
        for v in (r.get("values") or {}).values():
            compile_expr(v, FUNCS)
        jinja_env().from_string(r["explanation"])


def evaluate_rules(rules: List[Dict], metrics: Dict[str, pd.Series], annual: pd.DataFrame, tokens, names: Dict[str, float],
                   manual: pd.DataFrame = None, info: Dict = None) -> List[Dict]:
    book = SeriesBook(metrics, annual, manual, info)
    funcs = make_funcs(book)
    env = jinja_env()
    out = []
    for r in rules:
        applies = r["applies"] if isinstance(r["applies"], list) else [r["applies"]]
        base = {"id": r["id"], "name": r["name"], "pillar": r["pillar"], "severity": r["severity"],
                "origin": r.get("_origin", "config/flags.yaml")}
        if not any(a in tokens for a in applies) or any(a in tokens for a in (r.get("not_for") or [])):
            continue
        try:
            hit = bool(evaluate(compile_expr(r["condition"], FUNCS), names, funcs))
        except Missing as e:
            out.append({**base, "status": "not_evaluable", "missing": e.what})
            continue
        if not hit:
            out.append({**base, "status": "clear"})
            continue
        vals = {}
        for k, src in (r.get("values") or {}).items():
            try:
                vals[k] = evaluate(compile_expr(src, FUNCS), names, funcs)
            except Missing:
                vals[k] = float("nan")
        try:
            text = env.from_string(r["explanation"]).render(**vals, **names)
        except Exception as e:  # pragma: no cover - template authoring error
            text = f"{r['name']} (explanation template error: {e})"
        if r.get("suppresses"):
            base["suppresses"] = list(r["suppresses"])
        out.append({**base, "status": "triggered", "values": {k: (None if _isnan(v) else v) for k, v in vals.items()},
                    "text": " ".join(text.split())})
    return out
