"""Helpers shared by metric formulas. All series are indexed by FY label ('FY17'..) in ascending order.

Lags are taken by fiscal-year LABEL (FY24 - 1 = FY23), never by position, so a missing year yields NaN
instead of silently comparing the wrong years. Averages use the period's opening balance (the previous real
balance sheet; for Nestle's 15-month FY24 that is FY22) and closing balance.
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np
import pandas as pd

from ..standardise import Standardised, fy_year, year_label


class MetricError(Exception):
    pass


class Ctx:
    def __init__(self, std: Standardised, cfg, coc):
        self.std = std
        self.cfg = cfg
        self.coc = coc
        self.a = std.annual
        self.q = std.quarterly if std.quarterly is not None else pd.DataFrame()
        self.idx = list(self.a.index)
        self.year_of = {lab: fy_year(lab) for lab in self.idx}
        self.label_of = {y: lab for lab, y in self.year_of.items()}
        self.tokens = cfg.tokens(std.archetype)
        self.family = std.family
        self.asof = self.idx[-1]
        self.snapshot = std.snapshot or {}
        self.manual = std.manual if std.manual is not None else pd.DataFrame()
        self.stat_tax = float(cfg.mv("tax", "statutory_rate"))
        self.info: Dict[str, str] = {}  # metric id -> extra note (e.g. actual CAGR span)
        self._cache: Dict[str, pd.Series] = {}
        self._computing = set()

    # ---- series access ----------------------------------------------------------------------
    def empty(self) -> pd.Series:
        return pd.Series(np.nan, index=self.idx, dtype=float)

    def f(self, field: str) -> pd.Series:
        if field not in self.a.columns:
            return self.empty()
        return pd.to_numeric(self.a[field], errors="coerce").astype(float)

    def manual_series(self, kpi: str) -> pd.Series:
        if self.manual is None or self.manual.empty or kpi not in self.manual.columns:
            return self.empty()
        s = self.manual[kpi].reindex(self.idx)
        return pd.to_numeric(s, errors="coerce").astype(float)

    def has_manual(self, kpi: str) -> bool:
        return self.manual_series(kpi).notna().any()

    def point(self, value) -> pd.Series:
        s = self.empty()
        if value is not None and not (isinstance(value, float) and math.isnan(value)):
            s.iloc[-1] = float(value)
        return s

    def m(self, mid: str) -> pd.Series:
        """Value series of another metric (memoised)."""
        if mid in self._cache:
            return self._cache[mid]
        from ..registry import REGISTRY

        if mid not in REGISTRY:
            raise MetricError(f"unknown metric {mid}")
        if mid in self._computing:
            raise MetricError(f"circular metric dependency at {mid}")
        self._computing.add(mid)
        try:
            out = REGISTRY[mid].func(self)
            if not isinstance(out, pd.Series):
                out = self.point(out)
            out = out.reindex(self.idx).astype(float)
            out = out.replace([np.inf, -np.inf], np.nan)
        finally:
            self._computing.discard(mid)
        self._cache[mid] = out
        return out

    # ---- time helpers -------------------------------------------------------------------------
    def lag(self, s: pd.Series, k: int = 1) -> pd.Series:
        vals = s.to_dict()
        out = []
        for lab in self.idx:
            prev = self.label_of.get(self.year_of[lab] - k)
            out.append(vals.get(prev, np.nan) if prev is not None else np.nan)
        return pd.Series(out, index=self.idx, dtype=float)

    def opening(self, field: str) -> pd.Series:
        s = self.f(field)
        vals = s.to_dict()
        ops = self.a["opening_fy"] if "opening_fy" in self.a.columns else pd.Series([None] * len(self.idx), index=self.idx)
        out = []
        for lab in self.idx:
            op = ops.get(lab)
            out.append(vals.get(op, np.nan) if isinstance(op, str) and op else np.nan)
        return pd.Series(out, index=self.idx, dtype=float)

    def avg(self, field: str) -> pd.Series:
        return (self.f(field) + self.opening(field)) / 2.0

    @staticmethod
    def div(a: pd.Series, b, positive: bool = False) -> pd.Series:
        if not isinstance(b, pd.Series):
            b = pd.Series(b, index=a.index, dtype=float)
        bb = b.where(b > 0) if positive else b.where(b != 0)
        return (a / bb).astype(float)

    def growth(self, s: pd.Series, k: int = 1) -> pd.Series:
        base = self.lag(s, k)
        return (s / base.where(base > 0) - 1.0).astype(float)

    def cagr(self, s: pd.Series, n: int) -> pd.Series:
        base = self.lag(s, n)
        ok = (base > 0) & (s > 0)
        r = (s / base).where(ok)
        return (r ** (1.0 / n) - 1.0).astype(float)

    def full_span_cagr(self, s: pd.Series, mid: str, max_years: int = 10) -> pd.Series:
        last = self.asof
        y1 = self.year_of[last]
        v1 = s.get(last, np.nan)
        start = None
        for k in range(max_years, 0, -1):
            lab = self.label_of.get(y1 - k)
            if lab is not None and not pd.isna(s.get(lab, np.nan)):
                start = (lab, k)
                break
        if start is None or pd.isna(v1):
            return self.empty()
        lab0, n = start
        v0 = s[lab0]
        if v0 <= 0 or v1 <= 0:
            self.info[mid] = f"n/m: non-positive value at {lab0} or {last}"
            return self.empty()
        self.info[mid] = f"CAGR over {n} years ({lab0}-{last}); export holds {len(self.idx)} annual points"
        return self.point((v1 / v0) ** (1.0 / n) - 1.0)

    def rolling_sum(self, s: pd.Series, n: int) -> pd.Series:
        out = []
        for lab in self.idx:
            y = self.year_of[lab]
            labs = [self.label_of.get(y - k) for k in range(n)]
            if any(x is None for x in labs):
                out.append(np.nan)
                continue
            vals = [s.get(x, np.nan) for x in labs]
            out.append(np.nan if any(pd.isna(v) for v in vals) else float(sum(vals)))
        return pd.Series(out, index=self.idx, dtype=float)

    def window(self, s: pd.Series, n: int) -> pd.Series:
        """Last n annual values ending at the as-of year (by label), NaNs dropped."""
        y = self.year_of[self.asof]
        labs = [self.label_of.get(y - k) for k in range(n - 1, -1, -1)]
        vals = [(lab, s.get(lab, np.nan)) for lab in labs if lab is not None]
        return pd.Series({lab: v for lab, v in vals}, dtype=float).dropna()

    # ---- quarterly ---------------------------------------------------------------------------
    def qf(self, field: str) -> pd.Series:
        if self.q.empty or field not in self.q.columns:
            return pd.Series(dtype=float)
        return pd.to_numeric(self.q[field], errors="coerce").astype(float)

    def q_yoy(self, field: str) -> pd.Series:
        """YoY growth for each quarter whose same quarter a year earlier exists."""
        s = self.qf(field)
        if s.empty:
            return s
        idx = pd.to_datetime(s.index)
        by_date = dict(zip(idx, s.values))
        out = {}
        for d, v in zip(idx, s.values):
            prev = (d - pd.DateOffset(years=1)) + pd.offsets.MonthEnd(0)
            pv = by_date.get(prev)
            if pv is not None and pv > 0:
                out[d.date().isoformat()] = v / pv - 1.0
        return pd.Series(out, dtype=float)

    def ttm(self, field: str) -> Optional[float]:
        """Sum of the last 4 consecutive quarters, only if the latest quarter ends after the last FY end
        (otherwise the annual figure is the better 'latest'). Never used in as-of runs (quarters are truncated)."""
        s = self.qf(field)
        if len(s) < 4:
            return None
        idx = pd.to_datetime(s.index)
        last4 = idx[-4:]
        months = [(b.year - a.year) * 12 + b.month - a.month for a, b in zip(last4[:-1], last4[1:])]
        if any(m != 3 for m in months):
            return None
        fy_end = pd.Timestamp(self.a.loc[self.asof, "period_end"])
        if idx[-1] <= fy_end:
            return None
        return float(s.iloc[-4:].sum())


def ols_slope(y: pd.Series) -> float:
    y = y.dropna()
    n = len(y)
    if n < 2:
        return float("nan")
    x = np.arange(n, dtype=float)
    xm, ym = x.mean(), y.values.mean()
    den = ((x - xm) ** 2).sum()
    return float(((x - xm) * (y.values - ym)).sum() / den) if den else float("nan")
