"""Pillar 8: Valuation.

'Current' = export-date price (latest run) or the as-of year-end price (as-of run). History = FY-end values.
Own-history percentiles compare the current multiple with the FY-end multiples of earlier years (>= 5 needed).
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from ..registry import metric
from .context import Ctx
from .growth import bvps
from .returns import avg_ic, nopat


def _mode(c: Ctx) -> str:
    return "latest" if (c.snapshot or {}).get("basis") == "export" else "asof"


def _current_mcap(c: Ctx) -> Optional[float]:
    v = (c.snapshot or {}).get("market_cap")
    if v is None or (isinstance(v, float) and math.isnan(v)):
        v = c.f("market_cap").iloc[-1]
    return None if pd.isna(v) else float(v)


def _current_ev(c: Ctx) -> Optional[float]:
    mc = _current_mcap(c)
    if mc is None:
        return None
    last = c.asof
    inv = c.f("investments")[last] if c.cfg.mv("valuation", "ev_subtract_investments", default=True) else 0.0
    ev = mc + c.f("borrowings")[last] - c.f("cash")[last] - inv
    return None if pd.isna(ev) else float(ev)


def _latest_flow(c: Ctx, field_annual: str, field_q: str, mid: str, core_ok: bool = True) -> Tuple[Optional[float], str]:
    """TTM from quarters in a latest run (if quarters run past the last FY end), else the last FY value."""
    last = c.asof
    annual = c.f(field_annual)[last]
    if _mode(c) == "latest":
        exc_last = c.f("exceptional_est")[last]
        t = c.ttm(field_q)
        if t is not None and (core_ok or not exc_last):
            return t, "TTM from last 4 quarters"
    return (None if pd.isna(annual) else float(annual)), f"{last} annual"


def _with_current(c: Ctx, hist: pd.Series, current: Optional[float]) -> pd.Series:
    s = hist.copy()
    if _mode(c) == "latest" and current is not None:
        s.iloc[-1] = current
    return s


def _pe_hist(c: Ctx) -> pd.Series:
    return c.div(c.f("market_cap"), c.f("pat_core"), positive=True)


def _pb_hist(c: Ctx) -> pd.Series:
    return c.div(c.f("market_cap"), c.f("equity"), positive=True)


def _evebitda_hist(c: Ctx) -> pd.Series:
    return c.div(c.f("ev"), c.f("ebitda"), positive=True)


def _evsales_hist(c: Ctx) -> pd.Series:
    return c.div(c.f("ev"), c.f("revenue"), positive=True)


def _pe_current(c: Ctx) -> Optional[float]:
    mc = _current_mcap(c)
    pat, basis = _latest_flow(c, "pat_core", "pat", "pe", core_ok=False)
    c.info["pe"] = f"current = market cap / {basis} PAT" + (" (reported quarterly PAT)" if basis.startswith("TTM") else " (core)")
    return mc / pat if (mc and pat and pat > 0) else None


def _pb_current(c: Ctx) -> Optional[float]:
    mc, eq = _current_mcap(c), c.f("equity")[c.asof]
    return mc / eq if (mc and not pd.isna(eq) and eq > 0) else None


def _evebitda_current(c: Ctx) -> Optional[float]:
    ev = _current_ev(c)
    e, basis = _latest_flow(c, "ebitda", "ebitda", "ev_ebitda")
    c.info["ev_ebitda"] = f"current = EV (export price, {c.asof} debt/cash/investments) / {basis} EBITDA"
    return ev / e if (ev is not None and e and e > 0) else None


def _evsales_current(c: Ctx) -> Optional[float]:
    ev = _current_ev(c)
    r, basis = _latest_flow(c, "revenue", "revenue", "ev_sales")
    c.info["ev_sales"] = f"current = EV / {basis} revenue"
    return ev / r if (ev is not None and r and r > 0) else None


MULTIPLES = {
    "pe": ("P/E", "ALL", _pe_hist, _pe_current, "Market cap / core PAT (current: TTM PAT when available)"),
    "pb": ("P/B", "ALL", _pb_hist, _pb_current, "Market cap / book equity"),
    "ev_ebitda": ("EV/EBITDA", "NF", _evebitda_hist, _evebitda_current,
                  "EV / EBITDA, EV = market cap + borrowings - cash - investments"),
    "ev_sales": ("EV/Sales", "NF", _evsales_hist, _evsales_current, "EV / Revenue"),
}


def own_percentile(c: Ctx, hist: pd.Series, current: Optional[float]) -> float:
    if current is None or pd.isna(current):
        return np.nan
    h = hist.dropna()
    if _mode(c) == "asof":
        h = h.drop(c.asof, errors="ignore")
    min_n = int(c.cfg.mv("valuation", "min_history_points", default=5))
    if len(h) < min_n:
        return np.nan
    below = float((h < current).sum())
    equal = float((h == current).sum())
    return (below + 0.5 * equal) / len(h)


def _make_multiple(key: str):
    nm, applies, hist_f, cur_f, eq = MULTIPLES[key]

    @metric(id=key, name=nm, pillar="valuation", unit="x", direction="neutral", applies=applies, trend=False, stability=False,
            meaning=f"{nm} multiple. Series = FY-end values; the last value is the current multiple (export price) in a latest run.",
            equation=eq)
    def _m(c: Ctx, hist_f=hist_f, cur_f=cur_f):
        return _with_current(c, hist_f(c), cur_f(c))

    @metric(id=f"{key}_percentile_10y", name=f"{nm} percentile vs own history", pillar="valuation", unit="pct", direction="lower",
            applies=applies, kind="point",
            meaning=f"Where today's {nm} sits within the company's own FY-end history (0% = cheapest ever, 100% = richest). Needs >= 5 years.",
            equation=f"(# historical FY-end {nm} below current + 0.5 x # equal) / # historical values")
    def _p(c: Ctx, hist_f=hist_f, cur_f=cur_f):
        return c.point(own_percentile(c, hist_f(c), cur_f(c)))


for _k in MULTIPLES:
    _make_multiple(_k)


# ---- reverse DCF ----------------------------------------------------------------------------------------
# Market-implied free-cash-flow growth. Base cash flow is the steady-state FCF the business throws off when it
# reinvests only what terminal growth needs: F0 = NOPAT0 x (1 - gT / RONIC) (value-driver identity, RONIC = 3y avg
# ROIC). F0 then grows at g for N years, followed by a Gordon terminal value at gT. PV is monotonic in g, so the
# solution is unique (a value-driver model with growth-linked reinvestment was tried first but cannot reach the EV
# of high-multiple stocks within 10 years, so it returns no answer exactly where the question matters most).
def dcf_value(f0: float, g: float, wacc: float, g_term: float, years: int) -> float:
    pv, f = 0.0, f0
    for t in range(1, years + 1):
        f *= 1 + g
        pv += f / (1 + wacc) ** t
    tv = f * (1 + g_term) / (wacc - g_term)
    return pv + tv / (1 + wacc) ** years


def solve_implied_growth(ev: float, f0: float, wacc: float, g_term: float, years: int) -> Tuple[float, str]:
    if ev is None or f0 is None or not (f0 > 0) or not (wacc > g_term + 0.005) or pd.isna(ev):
        return np.nan, "inputs not usable (base FCF <= 0 or WACC too close to terminal growth)"
    fn = lambda g: dcf_value(f0, g, wacc, g_term, years) - ev
    lo, hi = -0.50, 1.50
    if fn(lo) > 0:
        return np.nan, "EV below the value of a 50%-a-year decline"
    if fn(hi) < 0:
        return np.nan, "EV implies FCF growth above 150% a year"
    for _ in range(200):
        mid = (lo + hi) / 2
        if fn(mid) >= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2, "solved"


def _ronic(c: Ctx) -> Optional[float]:
    w = c.window(c.m("roic"), 3)
    if not len(w):
        return None
    r = float(w.mean())
    return min(r, float(c.cfg.mv("valuation", "ronic_cap", default=1.0))) if r > 0 else None


@metric(id="implied_growth_reverse_dcf", name="Reverse-DCF implied FCF growth (10y)", pillar="valuation", unit="pct",
        direction="neutral", applies="NF", kind="point",
        meaning="Annual free-cash-flow growth for the next 10 years that today's enterprise value implies, starting from the "
                "steady-state FCF the business generates at its 3-year average ROIC, then growing at the terminal rate.",
        equation="solve g: EV = sum_{t=1..10} F0(1+g)^t/(1+WACC)^t + F10(1+gT)/((WACC-gT)(1+WACC)^10), "
                 "F0 = NOPAT0 x (1 - gT/RONIC), RONIC = 3y avg ROIC (capped at 100%)")
def implied_growth_reverse_dcf(c: Ctx):
    ev = _current_ev(c)
    n0 = nopat(c)[c.asof]
    wacc = float(c.coc.current["wacc"])
    ronic = _ronic(c)
    gT = float(c.cfg.mv("valuation", "terminal_growth"))
    yrs = int(c.cfg.mv("valuation", "reverse_dcf_years", default=10))
    if ronic is None or pd.isna(n0) or n0 <= 0:
        c.info["implied_growth_reverse_dcf"] = "n/m: NOPAT or ROIC not positive"
        return c.point(np.nan)
    if ronic <= gT:
        c.info["implied_growth_reverse_dcf"] = f"n/m: ROIC {ronic:.1%} <= terminal growth {gT:.1%} (growth would destroy cash)"
        return c.point(np.nan)
    f0 = float(n0) * (1 - gT / ronic)
    g, msg = solve_implied_growth(ev, f0, wacc, gT, yrs)
    c.info["implied_growth_reverse_dcf"] = (f"{msg}; EV {ev:,.0f} cr, NOPAT {n0:,.0f} cr, base FCF {f0:,.0f} cr, WACC {wacc:.2%}, "
                                            f"RONIC {ronic:.1%}, terminal g {gT:.1%}, {yrs}y") if ev is not None else msg
    return c.point(g)


@metric(id="implied_minus_delivered_growth", name="Implied - delivered growth", pillar="valuation", unit="pp", direction="lower",
        applies="NF", kind="point",
        meaning="How much faster the market expects NOPAT to grow than it did over the last 5 years (positive = priced for acceleration).",
        equation="implied_growth_reverse_dcf - 5y NOPAT CAGR (revenue CAGR 5y if NOPAT CAGR is n/m)")
def implied_minus_delivered_growth(c: Ctx):
    g = c.m("implied_growth_reverse_dcf").iloc[-1]
    d = c.cagr(nopat(c), 5).iloc[-1]
    if pd.isna(d):
        d = c.m("revenue_cagr_5y").iloc[-1]
    return c.point(g - d)


@metric(id="implied_growth_pb", name="P/B-implied growth", pillar="valuation", unit="pct", direction="neutral", applies="FIN",
        kind="point",
        meaning="Perpetual growth implied by today's P/B for a lender/insurer (justified P/B solved for g) at its 3-year average ROE.",
        equation="g = (Ke x P/B - ROE) / (P/B - 1); n/m if |P/B - 1| < 0.05")
def implied_growth_pb(c: Ctx):
    pb = c.m("pb").iloc[-1]
    w = c.window(c.m("roe"), 3)
    ke = c.coc.current["ke"]
    if pd.isna(pb) or not len(w) or abs(pb - 1) < 0.05:
        return c.point(np.nan)
    return c.point((ke * pb - float(w.mean())) / (pb - 1))


@metric(id="implied_pb_growth_minus_delivered", name="P/B-implied - delivered growth", pillar="valuation", unit="pp",
        direction="lower", applies="FIN", kind="point",
        meaning="Growth the market prices in versus the book-value compounding actually delivered over 5 years.",
        equation="implied_growth_pb - BVPS CAGR 5y (PAT CAGR 5y if n/m)")
def implied_pb_growth_minus_delivered(c: Ctx):
    g = c.m("implied_growth_pb").iloc[-1]
    d = c.m("bvps_cagr_5y").iloc[-1]
    if pd.isna(d):
        d = c.m("pat_cagr_5y").iloc[-1]
    return c.point(g - d)


def _justified_pb(c: Ctx) -> Tuple[float, Dict]:
    w = c.window(c.m("roe"), 3)
    po = c.window(c.m("payout_ratio"), 3)
    ke = c.coc.current["ke"]
    gT = float(c.cfg.mv("valuation", "terminal_growth"))
    if not len(w):
        return np.nan, {}
    roe = float(w.mean())
    payout = float(po.clip(0, 1).mean()) if len(po) else 0.0
    g = min(roe * (1 - payout), gT)
    if ke - g <= 0.005:
        return np.nan, {}
    return (roe - g) / (ke - g), {"roe": roe, "payout": payout, "g": g, "ke": ke}


@metric(id="justified_pb", name="Justified P/B", pillar="valuation", unit="x", direction="neutral", applies="ALL", kind="point",
        meaning="P/B a single-stage residual-income model supports: (ROE - g) / (Ke - g) with sustainable ROE and growth.",
        equation="(ROE - g) / (Ke - g); ROE = 3y avg, g = min(ROE x (1 - 3y avg payout), terminal g)")
def justified_pb(c: Ctx):
    v, d = _justified_pb(c)
    if d:
        c.info["justified_pb"] = f"ROE {d['roe']:.1%}, g {d['g']:.1%}, Ke {d['ke']:.2%}"
    return c.point(v)


@metric(id="pb_to_justified_pb", name="P/B / justified P/B", pillar="valuation", unit="x", direction="lower", applies="ALL", kind="point",
        meaning="Market P/B relative to what returns justify: above 1 = paying for more than current ROE supports.",
        equation="current P/B / justified P/B (justified > 0)")
def pb_to_justified_pb(c: Ctx):
    pb, j = c.m("pb").iloc[-1], c.m("justified_pb").iloc[-1]
    return c.point(pb / j if (not pd.isna(pb) and not pd.isna(j) and j > 0) else np.nan)


@metric(id="ev_ic", name="EV / invested capital", pillar="valuation", unit="x", direction="neutral", applies="NF", kind="point",
        meaning="Market value of operations per rupee of capital invested in them.", equation="current EV / IC (latest FY, IC > 0)")
def ev_ic(c: Ctx):
    ev, ic = _current_ev(c), c.f("invested_capital")[c.asof]
    return c.point(ev / ic if (ev is not None and not pd.isna(ic) and ic > 0) else np.nan)


@metric(id="ev_ic_to_roic_wacc", name="(EV/IC) / (ROIC/WACC)", pillar="valuation", unit="x", direction="lower", applies="NF",
        kind="point",
        meaning="In a no-growth steady state EV/IC = ROIC/WACC. Above 1 = the market pays for growth or improvement beyond today's "
                "returns; below 1 = priced for decline.",
        equation="(EV / IC) / (ROIC / WACC), ROIC = latest, WACC = current")
def ev_ic_to_roic_wacc(c: Ctx):
    evic = c.m("ev_ic").iloc[-1]
    r = c.m("roic").iloc[-1]
    w = c.coc.current["wacc"]
    if pd.isna(evic) or pd.isna(r) or r <= 0 or not w:
        return c.point(np.nan)
    return c.point(evic / (r / w))
