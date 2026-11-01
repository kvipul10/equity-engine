"""Pillar 7: Capital allocation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..registry import metric
from .context import Ctx
from .returns import nopat

CAP = 99.0


@metric(id="reinvestment_rate", name="Reinvestment rate", pillar="capital_allocation", unit="ratio", direction="neutral", applies="NF",
        meaning="Share of after-tax operating profit ploughed back into fixed assets and working capital. Good only if incremental "
                "ROIC exceeds WACC.",
        equation="(Capex proxy - Depreciation + change in NWC) / NOPAT (NOPAT > 0); NWC = other assets - cash - other liabilities")
def reinvestment_rate(c: Ctx):
    dnwc = c.f("nwc") - c.opening("nwc")
    return c.div(c.f("capex_proxy") - c.f("depreciation") + dnwc, nopat(c), positive=True)


@metric(id="payout_ratio", name="Dividend payout", pillar="capital_allocation", unit="ratio", direction="neutral", applies="ALL",
        meaning="Share of core profit paid as dividends (Screener 'Dividend Amount', declared for the year).",
        equation="Dividend / core PAT (PAT > 0)")
def payout_ratio(c: Ctx):
    return c.div(c.f("dividend"), c.f("pat_core"), positive=True)


@metric(id="share_count_change", name="Share count change", pillar="capital_allocation", unit="pct", direction="lower", applies="ALL",
        meaning="Net issuance (dilution, +) or buyback (-) of shares, adjusted for splits and bonuses.",
        equation="Adjusted shares_t / Adjusted shares_t-1 - 1")
def share_count_change(c: Ctx):
    return c.growth(c.f("adjusted_shares_cr"), 1)


@metric(id="buyback_estimate", name="Buyback (estimate)", pillar="capital_allocation", unit="inr_cr", direction="neutral", applies="ALL",
        stability=False, meaning="Estimated rupees spent on buybacks: shares retired x average of the two year-end prices.",
        equation="max(0, -(Adj shares_t - Adj shares_t-1)) x (Price_t + Price_t-1)/2")
def buyback_estimate(c: Ctx):
    sh = c.f("adjusted_shares_cr")
    retired = (c.lag(sh, 1) - sh).clip(lower=0)
    px = (c.f("price") + c.lag(c.f("price"), 1)) / 2
    return retired * px


@metric(id="shareholder_yield", name="Shareholder yield", pillar="capital_allocation", unit="pct", direction="neutral", applies="ALL",
        meaning="Cash returned to shareholders (dividends + estimated buybacks) as a share of year-end market value.",
        equation="(Dividend + buyback estimate) / Market cap (FY-end)")
def shareholder_yield(c: Ctx):
    return c.div(c.f("dividend") + c.m("buyback_estimate").fillna(0.0), c.f("market_cap"), positive=True)


@metric(id="dividend_to_fcf", name="Dividends / FCF", pillar="capital_allocation", unit="ratio", direction="lower", applies="NF",
        trend=False, stability=False,
        meaning="Dividends relative to free cash flow: above 1 = payouts funded from the balance sheet (99 = dividend paid with FCF <= 0).",
        equation="Dividend / (CFO - capex proxy); 99 if FCF <= 0 and dividend > 0; 0 if no dividend")
def dividend_to_fcf(c: Ctx):
    d, fcf = c.f("dividend"), c.f("fcf")
    out = d / fcf.where(fcf > 0)
    out = out.where(fcf > 0, np.where(d > 0, CAP, 0.0))
    return out.where(d.notna() & fcf.notna())


@metric(id="non_capex_investing_3y", name="Non-capex investing (3y, % of IC)", pillar="capital_allocation", unit="pct",
        direction="neutral", applies="NF", stability=False,
        meaning="Investing outflows beyond capex over 3 years (acquisitions, stakes, treasury investments) relative to opening invested capital.",
        equation="sum3(-CFI - capex proxy) / IC_t-3 (IC_t-3 > 0)")
def non_capex_investing_3y(c: Ctx):
    return c.div(c.rolling_sum(c.f("non_capex_investing"), 3), c.lag(c.f("invested_capital"), 3), positive=True)


@metric(id="acquisition_spend_3y", name="Acquisition-like spend (3y, % of IC)", pillar="capital_allocation", unit="pct",
        direction="neutral", applies="NF", stability=False,
        meaning="Investing outflows beyond capex that did not end up as cash or investments on the balance sheet (stakes and "
                "businesses bought), over 3 years, relative to opening invested capital. Treasury moves are netted out.",
        equation="sum3(max(0, -CFI - capex proxy - (change in cash + investments - net cash flow))) / IC_t-3")
def acquisition_spend_3y(c: Ctx):
    return c.div(c.rolling_sum(c.f("acquisition_spend"), 3), c.lag(c.f("invested_capital"), 3), positive=True)


@metric(id="acquisition_roic_delta_3y", name="ROIC change after acquisition spend", pillar="capital_allocation", unit="pp",
        direction="higher", applies="NF",
        meaning="When a company spent materially on acquisitions (> 10% of IC over 3 years, treasury moves excluded), did ROIC "
                "subsequently rise or fall?",
        equation="ROIC_t - ROIC_t-3 if acquisition_spend_3y > 10%, else n/a")
def acquisition_roic_delta_3y(c: Ctx):
    r = c.m("roic")
    return (r - c.lag(r, 3)).where(c.m("acquisition_spend_3y") > 0.10)


@metric(id="promoter_holding", name="Promoter holding", pillar="capital_allocation", unit="pct", direction="neutral", applies="ALL",
        meaning="Promoter (controlling shareholder) stake. Not in the Screener export: supply promoter_holding_pct in data/manual.",
        equation="manual promoter_holding_pct (FY-end)")
def promoter_holding(c: Ctx):
    return c.manual_series("promoter_holding_pct")


@metric(id="promoter_holding_change_3y", name="Promoter holding change 3y", pillar="capital_allocation", unit="pp",
        direction="higher", applies="ALL", stability=False,
        meaning="Change in promoter stake over 3 years (selling down = negative).", equation="Promoter holding_t - Promoter holding_t-3")
def promoter_holding_change_3y(c: Ctx):
    p = c.m("promoter_holding")
    return p - c.lag(p, 3)


@metric(id="promoter_pledge", name="Promoter pledge", pillar="capital_allocation", unit="pct", direction="lower", applies="ALL",
        meaning="Share of promoter holding pledged to lenders (forced-selling risk). Manual data only.",
        equation="manual promoter_pledge_pct (pledged shares / promoter shares)")
def promoter_pledge(c: Ctx):
    return c.manual_series("promoter_pledge_pct")


@metric(id="internal_capital_generation", name="Internal capital generation", pillar="capital_allocation", unit="pct",
        direction="neutral", applies="FIN",
        meaning="Growth in equity a lender can fund from retained profit alone.", equation="ROE x (1 - payout)")
def internal_capital_generation(c: Ctx):
    po = c.m("payout_ratio")
    po = po.where(po.notna(), np.where(c.f("dividend") == 0, 0.0, np.nan))
    return c.m("roe") * (1 - po.clip(0, 1))


@metric(id="growth_minus_icg", name="Asset growth - internal capital generation", pillar="capital_allocation", unit="pp",
        direction="lower", applies="BL",
        meaning="Balance-sheet growth beyond what retained earnings can support: must be funded by new equity or by higher leverage.",
        equation="(Total assets_t / Total assets_t-1 - 1) - ROE x (1 - payout)")
def growth_minus_icg(c: Ctx):
    return c.growth(c.f("total_assets"), 1) - c.m("internal_capital_generation")
