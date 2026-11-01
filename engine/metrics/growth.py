"""Pillar 1: Growth."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..registry import metric
from .context import Ctx, ols_slope


def eps(c: Ctx) -> pd.Series:
    return c.div(c.f("pat_core"), c.f("adjusted_shares_cr"), positive=True)


def bvps(c: Ctx) -> pd.Series:
    return c.div(c.f("equity"), c.f("adjusted_shares_cr"), positive=True)


_SERIES = {
    "revenue": (lambda c: c.f("revenue"), "Revenue", "ALL", "revenue (Screener 'Sales'; banks: interest earned; insurers: premium + investment income)"),
    "ebitda": (lambda c: c.f("ebitda"), "EBITDA", "NF", "EBITDA (operating profit before other income)"),
    "pat": (lambda c: c.f("pat_core"), "PAT", "ALL", "core PAT (owners' net profit excluding estimated exceptional items)"),
    "eps": (eps, "EPS", "ALL", "EPS = core PAT / split-adjusted shares"),
}


def _make_cagr(key: str, n: int):
    getter, nm, applies, what = _SERIES[key]
    if n == 10:
        @metric(id=f"{key}_cagr_10y", name=f"{nm} CAGR (full span, up to 10y)", pillar="growth", unit="pct", direction="higher",
                applies=applies, kind="point",
                meaning=f"Compound annual growth of {what} over the longest available history (max 10 years; 9 with a 10-column export).",
                equation=f"({nm}_t / {nm}_t-n)^(1/n) - 1, n = full available span <= 10; n/m if either value <= 0")
        def _f(c: Ctx, getter=getter, key=key):
            return c.full_span_cagr(getter(c), f"{key}_cagr_10y")
    else:
        @metric(id=f"{key}_cagr_{n}y", name=f"{nm} CAGR {n}y", pillar="growth", unit="pct", direction="higher", applies=applies,
                stability=False,
                meaning=f"Compound annual growth of {what} over {n} years.",
                equation=f"({nm}_t / {nm}_t-{n})^(1/{n}) - 1; n/m if either value <= 0")
        def _f(c: Ctx, getter=getter, n=n):
            return c.cagr(getter(c), n)
    return _f


for _k in _SERIES:
    for _n in (3, 5, 10):
        _make_cagr(_k, _n)


@metric(id="bvps_cagr_5y", name="Book value per share CAGR 5y", pillar="growth", unit="pct", direction="higher", applies="FIN",
        stability=False, meaning="Compounding of book value per share, the core growth measure for lenders and insurers.",
        equation="(BVPS_t / BVPS_t-5)^(1/5) - 1, BVPS = equity / adjusted shares")
def bvps_cagr_5y(c: Ctx):
    return c.cagr(bvps(c), 5)


@metric(id="assets_cagr_3y", name="Total assets CAGR 3y", pillar="growth", unit="pct", direction="higher", applies="FIN",
        stability=False, meaning="Balance-sheet growth (loan book + investments) for financials.",
        equation="(Total assets_t / Total assets_t-3)^(1/3) - 1")
def assets_cagr_3y(c: Ctx):
    return c.cagr(c.f("total_assets"), 3)


@metric(id="nii_cagr_3y", name="Net interest income CAGR 3y", pillar="growth", unit="pct", direction="higher", applies="BL",
        stability=False, meaning="Growth of the spread business (interest earned - interest expended).",
        equation="(NII_t / NII_t-3)^(1/3) - 1, NII = interest earned - interest expended")
def nii_cagr_3y(c: Ctx):
    return c.cagr(c.f("nii"), 3)


def _growth_vol(c: Ctx, s: pd.Series) -> float:
    g = c.growth(s, 1)
    w = c.window(g, 10)
    if len(w) < 4:
        return np.nan
    mu = w.mean()
    if abs(mu) < 0.01:
        return np.nan
    return float(w.std(ddof=1) / abs(mu))


@metric(id="revenue_growth_volatility", name="Revenue growth volatility", pillar="growth", unit="ratio", direction="lower",
        applies="ALL", kind="point",
        meaning="How erratic annual revenue growth is: standard deviation of yearly growth divided by its mean (lower = steadier).",
        equation="sd(g_t) / |mean(g_t)| over the last 10 annual growth rates (>= 4 needed); n/m if |mean| < 1%")
def revenue_growth_volatility(c: Ctx):
    return c.point(_growth_vol(c, c.f("revenue")))


@metric(id="pat_growth_volatility", name="PAT growth volatility", pillar="growth", unit="ratio", direction="lower", applies="ALL",
        kind="point", meaning="How erratic annual core-profit growth is (sd / mean of yearly growth).",
        equation="sd(g_t) / |mean(g_t)| of core PAT growth over the last 10 years (base year PAT > 0); n/m if |mean| < 1%")
def pat_growth_volatility(c: Ctx):
    return c.point(_growth_vol(c, c.f("pat_core")))


@metric(id="organic_capital_share_3y", name="Organic share of capital deployed 3y", pillar="growth", unit="ratio",
        direction="higher", applies="NF", stability=False,
        meaning="Of the money put into long-term assets over 3 years, the share spent on own capex rather than on additions to "
                "investments (acquisitions, stakes in associates, treasury). Proxy for organic vs bought growth: the export has no goodwill line.",
        equation="sum3(capex) / (sum3(capex) + sum3(max(delta Investments, 0)))")
def organic_capital_share_3y(c: Ctx):
    capex = c.f("capex_proxy")
    dinv = (c.f("investments") - c.opening("investments")).clip(lower=0)
    sc, si = c.rolling_sum(capex, 3), c.rolling_sum(dinv, 3)
    den = sc + si
    return c.div(sc.clip(lower=0), den, positive=True)


@metric(id="q_revenue_yoy", name="Latest quarter revenue YoY", pillar="growth", unit="pct", direction="higher", applies="ALL",
        kind="point", meaning="Revenue growth in the latest reported quarter versus the same quarter a year earlier.",
        equation="Revenue_q / Revenue_q-4 - 1")
def q_revenue_yoy(c: Ctx):
    y = c.q_yoy("revenue")
    return c.point(y.iloc[-1] if len(y) else np.nan)


@metric(id="q_pat_yoy", name="Latest quarter PAT YoY", pillar="growth", unit="pct", direction="higher", applies="ALL", kind="point",
        meaning="Reported net profit growth in the latest quarter versus a year earlier (n/m if the year-ago quarter was a loss).",
        equation="PAT_q / PAT_q-4 - 1 (PAT_q-4 > 0)")
def q_pat_yoy(c: Ctx):
    y = c.q_yoy("pat")
    return c.point(y.iloc[-1] if len(y) else np.nan)


@metric(id="q_revenue_yoy_trend", name="Quarterly YoY growth trend", pillar="growth", unit="pp", direction="higher", applies="ALL",
        kind="point", meaning="Is quarterly growth accelerating or decelerating? Slope of the last 4 quarterly YoY revenue growth prints.",
        equation="OLS slope of the last 4 values of (Revenue_q / Revenue_q-4 - 1), per quarter")
def q_revenue_yoy_trend(c: Ctx):
    y = c.q_yoy("revenue")
    if len(y) < 4:
        return c.point(np.nan)
    return c.point(ols_slope(y.iloc[-4:]))
