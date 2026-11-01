"""Pillar 6: Balance sheet."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..registry import metric
from .context import Ctx

CAP = 99.0


@metric(id="net_debt_to_ebitda", name="Net debt / EBITDA", pillar="balance_sheet", unit="x", direction="lower", applies="NF",
        meaning="Years of operating profit needed to repay net debt (negative = net cash). Borrowings include lease liabilities.",
        equation="(Borrowings - Cash & bank) / EBITDA (EBITDA > 0)")
def net_debt_to_ebitda(c: Ctx):
    return c.div(c.f("net_debt"), c.f("ebitda"), positive=True)


@metric(id="net_debt_to_equity", name="Net debt / equity", pillar="balance_sheet", unit="x", direction="lower", applies="NF",
        meaning="Net financial leverage on book equity.", equation="(Borrowings - Cash & bank) / Equity")
def net_debt_to_equity(c: Ctx):
    return c.div(c.f("net_debt"), c.f("equity"), positive=True)


@metric(id="interest_cover", name="Interest cover", pillar="balance_sheet", unit="x", direction="higher", applies="NF",
        meaning="How many times EBIT covers interest (capped at 99x when interest is negligible).",
        equation="EBIT / Interest, EBIT = core PBT + interest; = 99 if interest ~ 0; clipped to [-99, 99]")
def interest_cover(c: Ctx):
    ebit, i = c.f("ebit_core"), c.f("interest")
    raw = ebit / i.where(i > 1e-9)
    tiny = (i <= 1e-9) | (i <= 0.001 * ebit.abs())
    out = raw.where(~tiny, np.where(ebit >= 0, CAP, -CAP))
    return out.clip(-CAP, CAP).where(ebit.notna() & i.notna())


@metric(id="current_ratio_proxy", name="Current ratio (Screener proxy)", pillar="balance_sheet", unit="x", direction="higher",
        applies="NF",
        meaning="Short-term liquidity proxy: the export has no current/non-current split, so other assets / other liabilities is used "
                "(Screener's own working-capital split). Excludes short-term debt (inside Borrowings).",
        equation="Other assets / Other liabilities")
def current_ratio_proxy(c: Ctx):
    return c.div(c.f("other_assets"), c.f("other_liabilities"), positive=True)


@metric(id="cash_to_st_borrowings", name="Cash / short-term borrowings", pillar="balance_sheet", unit="x", direction="higher",
        applies="NF",
        meaning="Cash cover for debt falling due soon. Uses manual short_term_borrowings when supplied, otherwise total borrowings "
                "(conservative: treats all debt as short-term).",
        equation="Cash & bank / short-term borrowings (manual) or / Borrowings; = 99 when there is no debt")
def cash_to_st_borrowings(c: Ctx):
    st = c.manual_series("short_term_borrowings")
    den = st.where(st.notna(), c.f("borrowings"))
    cash = c.f("cash")
    out = (cash / den.where(den > 0)).clip(upper=CAP)
    return out.where(den > 0, np.where(cash.notna() & den.notna(), CAP, np.nan))


@metric(id="debt_vs_ebitda_growth", name="Debt growth - EBITDA growth", pillar="balance_sheet", unit="pp", direction="lower",
        applies="NF", meaning="Debt growing faster than the profit that services it (n/m when debt was negligible).",
        equation="(Borrowings_t/Borrowings_t-1 - 1) - (EBITDA_t/EBITDA_t-1 - 1); n/m if prior debt < 1% of assets or prior EBITDA <= 0")
def debt_vs_ebitda_growth(c: Ctx):
    b, e = c.f("borrowings"), c.f("ebitda")
    ok = c.div(c.lag(b, 1), c.lag(c.f("total_assets"), 1), positive=True) >= 0.01
    return (c.growth(b, 1) - c.growth(e, 1)).where(ok)


def _x(c: Ctx, i: int) -> pd.Series:
    ta = c.f("total_assets")
    if i == 1:
        return c.div(c.f("other_assets") - c.f("other_liabilities"), ta, positive=True)
    if i == 2:
        return c.div(c.f("reserves"), ta, positive=True)
    if i == 3:
        return c.div(c.f("ebit_core"), ta, positive=True)
    return c.div(c.f("equity"), c.f("borrowings") + c.f("other_liabilities"), positive=True)


for _i, _mean, _eq in [
    (1, "Working capital (Screener split) / total assets", "(Other assets - Other liabilities) / Total assets"),
    (2, "Reserves (proxy for retained earnings; includes securities premium) / total assets", "Reserves / Total assets"),
    (3, "Operating return on assets", "EBIT / Total assets"),
    (4, "Book equity / total liabilities (book value replaces market value in Z'')", "Equity / (Borrowings + Other liabilities)"),
]:
    metric(id=f"altman_x{_i}", name=f"Altman Z'' X{_i}", pillar="balance_sheet", unit="ratio", direction="higher", applies="NF",
           role="component", meaning=_mean, equation=_eq)((lambda i: (lambda c: _x(c, i)))(_i))


@metric(id="altman_z_india", name="Altman Z''-EM (India-adapted)", pillar="balance_sheet", unit="score", direction="higher",
        applies="NF",
        meaning="Distress score for emerging-market non-financials (Altman 2005 EM score: Z'' + 3.25) using Screener proxies. "
                "Above 5.85 safe, below 4.35 distress zone.",
        equation="3.25 + 6.56 X1 + 3.26 X2 + 6.72 X3 + 1.05 X4 (X1..X4 as defined in altman_x1..x4)")
def altman_z_india(c: Ctx):
    return 3.25 + 6.56 * c.m("altman_x1") + 3.26 * c.m("altman_x2") + 6.72 * c.m("altman_x3") + 1.05 * c.m("altman_x4")


@metric(id="equity_to_assets", name="Equity / assets", pillar="balance_sheet", unit="pct", direction="higher", applies="FIN",
        meaning="Book capital cushion per rupee of assets (unweighted leverage; regulatory CRAR needs risk weights not in the export).",
        equation="Equity / Total assets")
def equity_to_assets(c: Ctx):
    return c.div(c.f("equity"), c.f("total_assets"), positive=True)


@metric(id="funding_vs_equity_growth", name="Funding growth - equity growth", pillar="balance_sheet", unit="pp", direction="lower",
        applies="BL", meaning="Deposits + borrowings growing faster than capital = rising leverage.",
        equation="(Borrowings_t/Borrowings_t-1 - 1) - (Equity_t/Equity_t-1 - 1)")
def funding_vs_equity_growth(c: Ctx):
    return c.growth(c.f("borrowings"), 1) - c.growth(c.f("equity"), 1)


@metric(id="borrowings_to_equity", name="Borrowings / equity", pillar="balance_sheet", unit="x", direction="lower", applies="NBFC",
        meaning="NBFC leverage (RBI caps base-layer NBFCs at 7x outside liabilities / owned funds).", equation="Borrowings / Equity")
def borrowings_to_equity(c: Ctx):
    return c.div(c.f("borrowings"), c.f("equity"), positive=True)
