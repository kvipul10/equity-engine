"""Pillar 5: Cash and earnings quality (non-financials; CFO of lenders/insurers is not an earnings-quality signal)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..registry import metric
from .context import Ctx


@metric(id="cfo_to_ebitda", name="CFO / EBITDA", pillar="cash_quality", unit="ratio", direction="higher", applies="NF",
        meaning="How much of operating profit arrives as operating cash (after working capital and tax).",
        equation="CFO / EBITDA (EBITDA > 0)")
def cfo_to_ebitda(c: Ctx):
    return c.div(c.f("cfo"), c.f("ebitda"), positive=True)


@metric(id="fcf_to_pat", name="FCF / PAT", pillar="cash_quality", unit="ratio", direction="higher", applies="NF",
        meaning="Free cash flow per rupee of core profit in the year.", equation="(CFO - capex proxy) / core PAT (PAT > 0)")
def fcf_to_pat(c: Ctx):
    return c.div(c.f("fcf"), c.f("pat_core"), positive=True)


@metric(id="fcf_to_pat_5y", name="FCF / PAT (5y cumulative)", pillar="cash_quality", unit="ratio", direction="higher", applies="NF",
        meaning="Free cash flow conversion over a full cycle (5 years), smoothing lumpy capex.",
        equation="sum5(CFO - capex proxy) / sum5(core PAT)")
def fcf_to_pat_5y(c: Ctx):
    return c.div(c.rolling_sum(c.f("fcf"), 5), c.rolling_sum(c.f("pat_core"), 5), positive=True)


@metric(id="cfo_to_pat_5y", name="CFO / PAT (5y cumulative)", pillar="cash_quality", unit="ratio", direction="higher", applies="NF",
        meaning="Operating cash flow conversion of profits over 5 years: below 60% means profits are not turning into cash.",
        equation="sum5(CFO) / sum5(core PAT)")
def cfo_to_pat_5y(c: Ctx):
    return c.div(c.rolling_sum(c.f("cfo"), 5), c.rolling_sum(c.f("pat_core"), 5), positive=True)


@metric(id="accruals_ratio", name="Accruals ratio", pillar="cash_quality", unit="pct", direction="lower", applies="NF",
        meaning="Profit not backed by operating cash, scaled by assets (Sloan-style total accruals): high = lower-quality earnings.",
        equation="(reported PAT - CFO) / average total assets")
def accruals_ratio(c: Ctx):
    return c.div(c.f("pat") - c.f("cfo"), c.avg("total_assets"), positive=True)


@metric(id="receivables_vs_revenue_growth", name="Receivables growth - revenue growth", pillar="cash_quality", unit="pp",
        direction="lower", applies="NF",
        meaning="Receivables growing faster than sales can signal channel stuffing, looser credit or collection problems.",
        equation="(Rec_t / Rec_t-1 - 1) - (Rev_t / Rev_t-1 - 1); n/m if prior receivables < 0.5% of revenue")
def receivables_vs_revenue_growth(c: Ctx):
    rec, rev = c.f("receivables"), c.f("revenue")
    ok = c.div(c.lag(rec, 1), c.lag(rev, 1), positive=True) >= 0.005
    return (c.growth(rec, 1) - c.growth(rev, 1)).where(ok)


def _exc_flag(c: Ctx) -> pd.Series:
    exc, pbt = c.f("exceptional_est"), c.f("pbt")
    return ((exc.abs() > 0.05 * pbt.abs()) & (exc != 0)).astype(float).where(exc.notna())


@metric(id="exceptional_frequency_5y", name="Exceptional items frequency (5y)", pillar="cash_quality", unit="count",
        direction="lower", applies="NF", stability=False,
        meaning="In how many of the last 5 years profit contained a material exceptional item (|item| > 5% of PBT).",
        equation="count over last 5 years of [|estimated exceptional| > 5% x |PBT|]")
def exceptional_frequency_5y(c: Ctx):
    return c.rolling_sum(_exc_flag(c), 5)


@metric(id="exceptional_size_5y", name="Exceptional items size (5y)", pillar="cash_quality", unit="pct", direction="lower",
        applies="NF", stability=False,
        meaning="How big exceptional items were relative to profit over 5 years.",
        equation="sum5(|estimated exceptional|) / sum5(|reported PBT|)")
def exceptional_size_5y(c: Ctx):
    return c.div(c.rolling_sum(c.f("exceptional_est").abs(), 5), c.rolling_sum(c.f("pbt").abs(), 5), positive=True)


# ---- Beneish-style M-score from Screener proxies --------------------------------------------------------
def _ca(c: Ctx) -> pd.Series:
    return c.f("receivables") + c.f("inventory") + c.f("cash")


def _sga(c: Ctx) -> pd.Series:
    s = c.f("selling_admin") + c.f("other_exp")
    alt = c.f("other_opex")
    ok = (s > 0) & (c.lag(s, 1) > 0)
    return s.where(ok, alt)


def _idx(c: Ctx, s: pd.Series, inverse: bool = False) -> pd.Series:
    prev = c.lag(s, 1)
    if inverse:
        return (prev / s.where(s > 0)).where(prev > 0)
    return (s / prev.where(prev > 0)).where(s > 0)


BENEISH = {"dsri": 0.920, "gmi": 0.528, "aqi": 0.404, "sgi": 0.892, "depi": 0.115, "sgai": -0.172, "tata": 4.679, "lvgi": -0.327}
BENEISH_CONST = -4.84


@metric(id="beneish_dsri", name="Beneish DSRI", pillar="cash_quality", unit="ratio", direction="lower", applies="NF", role="component",
        meaning="Days-sales-in-receivables index: receivables/sales this year vs last.", equation="(Rec_t/Sales_t) / (Rec_t-1/Sales_t-1)")
def beneish_dsri(c: Ctx):
    return _idx(c, c.div(c.f("receivables"), c.f("revenue"), positive=True))


@metric(id="beneish_gmi", name="Beneish GMI", pillar="cash_quality", unit="ratio", direction="lower", applies="NF", role="component",
        meaning="Gross-margin index: last year's gross margin / this year's (>1 = deteriorating margins).",
        equation="GM_t-1 / GM_t, GM = 1 - COGS/Sales")
def beneish_gmi(c: Ctx):
    gm = 1 - c.div(c.f("cogs"), c.f("revenue"), positive=True)
    return _idx(c, gm, inverse=True)


@metric(id="beneish_aqi", name="Beneish AQI", pillar="cash_quality", unit="ratio", direction="lower", applies="NF", role="component",
        meaning="Asset-quality index: share of 'soft' assets (not current assets or net block) this year vs last.",
        equation="[1 - (CA_t + NB_t)/TA_t] / [1 - (CA_t-1 + NB_t-1)/TA_t-1], CA proxy = receivables + inventory + cash")
def beneish_aqi(c: Ctx):
    soft = 1 - c.div(_ca(c) + c.f("net_block"), c.f("total_assets"), positive=True)
    return _idx(c, soft)


@metric(id="beneish_sgi", name="Beneish SGI", pillar="cash_quality", unit="ratio", direction="lower", applies="NF", role="component",
        meaning="Sales-growth index.", equation="Sales_t / Sales_t-1")
def beneish_sgi(c: Ctx):
    return _idx(c, c.f("revenue"))


@metric(id="beneish_depi", name="Beneish DEPI", pillar="cash_quality", unit="ratio", direction="lower", applies="NF", role="component",
        meaning="Depreciation index: last year's depreciation rate / this year's (>1 = slower depreciation).",
        equation="DepRate_t-1 / DepRate_t, DepRate = Dep / (Dep + Net block)")
def beneish_depi(c: Ctx):
    rate = c.div(c.f("depreciation"), c.f("depreciation") + c.f("net_block"), positive=True)
    return _idx(c, rate, inverse=True)


@metric(id="beneish_sgai", name="Beneish SGAI", pillar="cash_quality", unit="ratio", direction="neutral", applies="NF", role="component",
        meaning="SG&A index: SG&A/sales this year vs last.",
        equation="(SGA_t/Sales_t) / (SGA_t-1/Sales_t-1), SGA proxy = selling & admin + other expenses (other opex if that is <= 0)")
def beneish_sgai(c: Ctx):
    return _idx(c, c.div(_sga(c), c.f("revenue"), positive=True))


@metric(id="beneish_lvgi", name="Beneish LVGI", pillar="cash_quality", unit="ratio", direction="lower", applies="NF", role="component",
        meaning="Leverage index: (debt + other liabilities)/assets this year vs last.",
        equation="[(Borrowings_t + OL_t)/TA_t] / [(Borrowings_t-1 + OL_t-1)/TA_t-1]")
def beneish_lvgi(c: Ctx):
    return _idx(c, c.div(c.f("borrowings") + c.f("other_liabilities"), c.f("total_assets"), positive=True))


@metric(id="beneish_tata", name="Beneish TATA", pillar="cash_quality", unit="ratio", direction="lower", applies="NF", role="component",
        meaning="Total accruals to total assets (year-end).", equation="(reported PAT - CFO) / Total assets_t")
def beneish_tata(c: Ctx):
    return c.div(c.f("pat") - c.f("cfo"), c.f("total_assets"), positive=True)


@metric(id="beneish_m_score", name="Beneish M-score (Screener proxies)", pillar="cash_quality", unit="score", direction="lower",
        applies="NF",
        meaning="Probability-style earnings-manipulation screen (Beneish 1999, 8 variables) built from Screener line items. Above -1.78 "
                "= profile resembles known manipulators; a screen, not proof.",
        equation="-4.84 + 0.920 DSRI + 0.528 GMI + 0.404 AQI + 0.892 SGI + 0.115 DEPI - 0.172 SGAI + 4.679 TATA - 0.327 LVGI")
def beneish_m_score(c: Ctx):
    tot = pd.Series(BENEISH_CONST, index=c.idx, dtype=float)
    for k, w in BENEISH.items():
        tot = tot + w * c.m(f"beneish_{k}")
    return tot
