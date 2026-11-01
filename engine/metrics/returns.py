"""Pillar 4: Returns (DuPont, ROIC)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..registry import metric
from .context import Ctx


def nopat_tax_rate(c: Ctx) -> pd.Series:
    pbt, tax = c.f("pbt_core"), c.f("tax_core")
    etr = (tax / pbt.where(pbt > 0)).clip(0.0, 0.40)
    return etr.where(pbt > 0, c.stat_tax)


def nopat(c: Ctx) -> pd.Series:
    return c.f("operating_ebit") * (1 - nopat_tax_rate(c))


def avg_ic(c: Ctx) -> pd.Series:
    ic = c.avg("invested_capital")
    mi = c.manual_series("minority_interest")
    if mi.notna().any():
        mi_avg = (mi + c.lag(mi, 1)) / 2
        ic = ic + mi_avg.fillna(mi).fillna(0.0)  # add-back only in years where it is supplied
    return ic


@metric(id="roe", name="Return on equity", pillar="returns", unit="pct", direction="higher", applies="ALL",
        meaning="Owners' core profit per rupee of shareholders' equity.", equation="core PAT / average equity (share capital + reserves)")
def roe(c: Ctx):
    return c.div(c.f("pat_core"), c.avg("equity"), positive=True)


@metric(id="roa", name="Return on assets", pillar="returns", unit="pct", direction="higher", applies="ALL",
        meaning="Owners' core profit per rupee of total assets.", equation="core PAT / average total assets")
def roa(c: Ctx):
    return c.div(c.f("pat_core"), c.avg("total_assets"), positive=True)


@metric(id="roce", name="Return on capital employed", pillar="returns", unit="pct", direction="higher", applies="NF",
        meaning="Pre-tax operating return on all funding (Screener's definition).",
        equation="EBIT / average (equity + borrowings), EBIT = core PBT + interest")
def roce(c: Ctx):
    return c.div(c.f("ebit_core"), c.avg("equity") + c.avg("borrowings"), positive=True)


@metric(id="roic", name="Return on invested capital", pillar="returns", unit="pct", direction="higher", applies="NF",
        meaning="After-tax operating return on the capital actually tied up in operations (excludes cash, investments and the "
                "income they earn).",
        equation="NOPAT / average IC; NOPAT = (EBITDA - Dep) x (1 - ETR), ETR = core tax / core PBT clipped 0-40% (statutory if PBT <= 0); "
                 "IC = equity + borrowings - cash - investments (+ manual minority interest); n/m if IC <= 0")
def roic(c: Ctx):
    ic = avg_ic(c)
    if not pd.isna(ic.iloc[-1]) and ic.iloc[-1] <= 0:
        c.info["roic"] = (f"n/m in {c.asof}: average invested capital is negative ({ic.iloc[-1]:,.0f} cr): customer advances/payables "
                          "exceed operating assets, so returns on capital are unbounded; economic profit remains defined.")
    return c.div(nopat(c), ic, positive=True)


@metric(id="roic_wacc_spread", name="ROIC - WACC", pillar="returns", unit="pp", direction="higher", applies="NF",
        meaning="Value created per rupee of invested capital: positive = earns more than investors require.",
        equation="ROIC - WACC (WACC from config/market.yaml, see capital_cost.py)")
def roic_wacc_spread(c: Ctx):
    return c.m("roic") - c.coc.wacc.reindex(c.idx)


@metric(id="incremental_roic_3y", name="Incremental ROIC 3y", pillar="returns", unit="pct", direction="higher", applies="NF",
        meaning="Return on the capital added over the last 3 years: is new money earning as much as the old?",
        equation="(NOPAT_t - NOPAT_t-3) / (avg IC_t - avg IC_t-3); n/m if capital grew < 5%")
def incremental_roic_3y(c: Ctx):
    n, ic = nopat(c), avg_ic(c)
    dn, dic = n - c.lag(n, 3), ic - c.lag(ic, 3)
    ok = dic > 0.05 * c.lag(ic, 3).abs()
    return (dn / dic).where(ok)


@metric(id="roe_ke_spread", name="ROE - cost of equity", pillar="returns", unit="pp", direction="higher", applies="FIN",
        meaning="Value created per rupee of equity for a lender/insurer.", equation="ROE - Ke, Ke = rf + beta x ERP")
def roe_ke_spread(c: Ctx):
    return c.m("roe") - c.coc.ke.reindex(c.idx)


# ---- DuPont components ---------------------------------------------------------------------------------
@metric(id="attributable_factor", name="Attributable-profit factor", pillar="returns", unit="ratio", direction="neutral",
        applies="ALL", role="component",
        meaning="Owners' share of after-tax profit: below 1 = minorities take a slice; above 1 = associate/JV income adds to it.",
        equation="core PAT / (core PBT - core tax)")
def attributable_factor(c: Ctx):
    return c.div(c.f("pat_core"), c.f("pbt_core") - c.f("tax_core"), positive=True)


@metric(id="tax_burden", name="Tax burden", pillar="returns", unit="ratio", direction="higher", applies="ALL", role="component",
        meaning="Share of pre-tax profit kept after tax (1 - effective tax rate).", equation="(core PBT - core tax) / core PBT")
def tax_burden(c: Ctx):
    pbt = c.f("pbt_core")
    return c.div(pbt - c.f("tax_core"), pbt, positive=True)


@metric(id="interest_burden", name="Interest burden", pillar="returns", unit="ratio", direction="higher", applies="NF",
        role="component", meaning="Share of EBIT left after interest.", equation="core PBT / EBIT")
def interest_burden(c: Ctx):
    return c.div(c.f("pbt_core"), c.f("ebit_core"), positive=True)


@metric(id="equity_multiplier", name="Equity multiplier", pillar="returns", unit="x", direction="neutral", applies="ALL",
        role="component", meaning="Assets per rupee of equity: the leverage term in DuPont.", equation="average total assets / average equity")
def equity_multiplier(c: Ctx):
    return c.div(c.avg("total_assets"), c.avg("equity"), positive=True)


@metric(id="debt_to_equity_avg", name="Borrowings / equity (average)", pillar="returns", unit="x", direction="neutral", applies="ALL",
        role="component", meaning="Debt part of the equity multiplier.", equation="average borrowings / average equity")
def debt_to_equity_avg(c: Ctx):
    return c.div(c.avg("borrowings"), c.avg("equity"), positive=True)


@metric(id="other_liab_to_equity_avg", name="Other liabilities / equity (average)", pillar="returns", unit="x", direction="neutral",
        applies="ALL", role="component", meaning="Non-debt liabilities part of the equity multiplier.",
        equation="average other liabilities / average equity")
def other_liab_to_equity_avg(c: Ctx):
    return c.div(c.avg("other_liabilities"), c.avg("equity"), positive=True)


@metric(id="nopat_tax_factor", name="NOPAT tax factor", pillar="returns", unit="ratio", direction="higher", applies="NF",
        role="component", meaning="Operating profit kept after tax.", equation="1 - ETR (as in ROIC)")
def nopat_tax_factor(c: Ctx):
    return 1 - nopat_tax_rate(c)


@metric(id="nopat_margin", name="NOPAT margin", pillar="returns", unit="pct", direction="higher", applies="NF", role="component",
        meaning="After-tax operating profit per rupee of revenue (the margin half of ROIC).", equation="NOPAT / Revenue")
def nopat_margin(c: Ctx):
    return c.div(nopat(c), c.f("revenue"), positive=True)


# ---- financials: ROA components (all per rupee of average assets) --------------------------------------
def _per_assets(field, sign=1.0):
    def f(c: Ctx):
        return c.div(sign * c.f(field), c.avg("total_assets"), positive=True)
    return f


for _fid, _field, _nm, _mean in [
    ("interest_to_assets", "interest", "Interest expended / assets", "Interest paid per rupee of average assets."),
    ("other_income_to_assets", "other_income", "Other income / assets", "Fee and other income per rupee of average assets."),
    ("dep_to_assets", "depreciation", "Depreciation / assets", "Depreciation per rupee of average assets."),
    ("tax_to_assets", "tax_core", "Tax / assets", "Tax per rupee of average assets."),
    ("minority_to_assets", "minority_and_associates", "Minority & associates / assets",
     "Associate income less minority share per rupee of average assets."),
]:
    metric(id=_fid, name=_nm, pillar="returns", unit="pct", direction="neutral", applies="FIN", role="component",
           meaning=_mean + " ROA = yield - interest + other income - opex - depreciation - tax + minority/associates.",
           equation=f"{_field} / average total assets")(_per_assets(_field))
