"""Pillar 2: Margins."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..registry import metric
from .context import Ctx


def _rev(c: Ctx) -> pd.Series:
    return c.f("revenue")


@metric(id="gross_margin", name="Gross margin", pillar="margins", unit="pct", direction="higher", applies="NF",
        meaning="Share of revenue left after the direct cost of making the product (materials, power & fuel, other manufacturing). "
                "n/m when such costs are under 2% of revenue (services).",
        equation="1 - COGS / Revenue, COGS = (raw material - change in inventory) + power & fuel + other mfr. exp")
def gross_margin(c: Ctx):
    cogs, rev = c.f("cogs"), _rev(c)
    share = c.div(cogs, rev, positive=True)
    return (1 - share).where(share >= 0.02)


@metric(id="ebitda_margin", name="EBITDA margin", pillar="margins", unit="pct", direction="higher", applies="NF",
        meaning="Operating profit before depreciation, interest and other income, per rupee of revenue (Screener OPM).",
        equation="EBITDA / Revenue, EBITDA = Revenue - (materials + employee + other opex)")
def ebitda_margin(c: Ctx):
    return c.div(c.f("ebitda"), _rev(c), positive=True)


@metric(id="ebit_margin", name="EBIT margin", pillar="margins", unit="pct", direction="higher", applies="NF",
        meaning="Profit before interest and tax (including core other income, excluding exceptional items) per rupee of revenue.",
        equation="EBIT / Revenue, EBIT = core PBT + interest = EBITDA - depreciation + core other income")
def ebit_margin(c: Ctx):
    return c.div(c.f("ebit_core"), _rev(c), positive=True)


@metric(id="pat_margin", name="PAT margin", pillar="margins", unit="pct", direction="higher", applies="ALL",
        meaning="Owners' core net profit per rupee of revenue (net profit margin, NPM).",
        equation="core PAT / Revenue")
def pat_margin(c: Ctx):
    return c.div(c.f("pat_core"), _rev(c), positive=True)


@metric(id="materials_pct", name="Materials % of sales", pillar="margins", unit="pct", direction="lower", applies="NF",
        meaning="Raw materials consumed (net of inventory change) as a share of revenue.",
        equation="(Raw material - Change in inventory) / Revenue")
def materials_pct(c: Ctx):
    return c.div(c.f("materials_cost"), _rev(c), positive=True)


@metric(id="employee_pct", name="Employee cost % of sales", pillar="margins", unit="pct", direction="lower", applies="NF",
        meaning="Staff costs as a share of revenue.", equation="Employee cost / Revenue")
def employee_pct(c: Ctx):
    return c.div(c.f("employee_cost"), _rev(c), positive=True)


@metric(id="other_expenses_pct", name="Other expenses % of sales", pillar="margins", unit="pct", direction="lower", applies="NF",
        meaning="All other operating costs (power & fuel, other manufacturing, selling & admin, other) as a share of revenue. "
                "Summed because Screener reclassifies between these lines.",
        equation="(Power & fuel + Other mfr. + Selling & admin + Other expenses) / Revenue")
def other_expenses_pct(c: Ctx):
    return c.div(c.f("other_opex"), _rev(c), positive=True)


@metric(id="dol", name="Degree of operating leverage", pillar="margins", unit="x", direction="neutral", applies="NF",
        meaning="How much EBIT moves for a 1% move in sales: high DOL magnifies both upturns and downturns.",
        equation="%change EBIT / %change Revenue (n/m if |%change revenue| < 2% or prior EBIT <= 0)")
def dol(c: Ctx):
    ge = c.growth(c.f("ebit_core"), 1)
    gr = c.growth(_rev(c), 1)
    return (ge / gr.where(gr.abs() >= 0.02)).astype(float)


@metric(id="ebitda_margin_sd_10y", name="EBITDA margin volatility (sd)", pillar="margins", unit="pp", direction="lower", applies="NF",
        kind="point", meaning="Standard deviation of the EBITDA margin over up to 10 years: pricing power and cost pass-through.",
        equation="sd(EBITDA margin_t) over the last 10 years (>= 4 needed, sample sd)")
def ebitda_margin_sd_10y(c: Ctx):
    w = c.window(c.m("ebitda_margin"), 10)
    return c.point(float(w.std(ddof=1)) if len(w) >= 4 else np.nan)


@metric(id="other_income_to_pbt", name="Other income / PBT", pillar="margins", unit="pct", direction="lower", applies="NF",
        meaning="How much of pre-tax profit comes from other income (treasury, one-offs) rather than operations (reported basis).",
        equation="Other income (reported, incl. exceptional) / PBT (reported); n/m if PBT <= 0")
def other_income_to_pbt(c: Ctx):
    return c.div(c.f("other_income"), c.f("pbt"), positive=True)


@metric(id="q_ebitda_margin_yoy_change", name="Latest quarter EBITDA margin change YoY", pillar="margins", unit="pp",
        direction="higher", applies="NF", kind="point",
        meaning="Latest quarter's operating margin versus the same quarter a year earlier.",
        equation="OPM_q - OPM_q-4, OPM = operating profit / revenue")
def q_ebitda_margin_yoy_change(c: Ctx):
    s = c.qf("ebitda_margin")
    if s.empty:
        return c.point(np.nan)
    idx = pd.to_datetime(s.index)
    d = idx[-1]
    prev = (d - pd.DateOffset(years=1)) + pd.offsets.MonthEnd(0)
    m = dict(zip(idx, s.values))
    if prev not in m or pd.isna(m[prev]) or pd.isna(m[d]):
        return c.point(np.nan)
    return c.point(m[d] - m[prev])


# ---- components used by driver trees -------------------------------------------------------------------
@metric(id="dep_to_sales", name="Depreciation / sales", pillar="margins", unit="pct", direction="lower", applies="NF", role="component",
        meaning="Depreciation per rupee of revenue (bridge from EBITDA to EBIT margin).", equation="Depreciation / Revenue")
def dep_to_sales(c: Ctx):
    return c.div(c.f("depreciation"), _rev(c), positive=True)


@metric(id="oi_core_to_sales", name="Core other income / sales", pillar="margins", unit="pct", direction="neutral", applies="NF",
        role="component", meaning="Recurring other income per rupee of revenue (bridge from EBITDA to EBIT margin).",
        equation="(Other income - estimated exceptional items) / Revenue")
def oi_core_to_sales(c: Ctx):
    return c.div(c.f("other_income_core"), _rev(c), positive=True)


@metric(id="operating_margin", name="Operating (EBIT excl. other income) margin", pillar="margins", unit="pct", direction="higher",
        applies="NF", role="component", meaning="Operating EBIT per rupee of revenue, excluding other income (used for NOPAT/ROIC).",
        equation="(EBITDA - Depreciation) / Revenue")
def operating_margin(c: Ctx):
    return c.div(c.f("operating_ebit"), _rev(c), positive=True)


# ---- financials -----------------------------------------------------------------------------------------
@metric(id="nii_to_assets", name="NII / average assets (NIM proxy)", pillar="margins", unit="pct", direction="higher", applies="BL",
        meaning="Net interest margin on the whole balance sheet (RBI defines NIM as NII / average total assets).",
        equation="(Interest earned - Interest expended) / average total assets")
def nii_to_assets(c: Ctx):
    return c.div(c.f("nii"), c.avg("total_assets"), positive=True)


@metric(id="yield_on_assets", name="Revenue / average assets", pillar="margins", unit="pct", direction="neutral", applies="FIN",
        meaning="Gross yield of the balance sheet (banks: interest earned / assets; insurers: revenue / assets).",
        equation="Revenue / average total assets")
def yield_on_assets(c: Ctx):
    return c.div(_rev(c), c.avg("total_assets"), positive=True)


@metric(id="cost_of_funds", name="Cost of funds", pillar="margins", unit="pct", direction="lower", applies="BL",
        meaning="Interest paid per rupee of deposits + borrowings.",
        equation="Interest expended / average (deposits + borrowings)")
def cost_of_funds(c: Ctx):
    return c.div(c.f("interest"), c.avg("borrowings"), positive=True)


@metric(id="cost_to_income", name="Cost (incl. provisions) / income", pillar="margins", unit="pct", direction="lower", applies="BL",
        meaning="Operating costs including provisions per rupee of net income (Screener does not separate provisions, so this is "
                "higher than the reported cost-to-income ratio).",
        equation="(Total opex incl. provisions + depreciation) / (NII + other income)")
def cost_to_income(c: Ctx):
    return c.div(c.f("total_opex") + c.f("depreciation"), c.f("net_total_income"), positive=True)


@metric(id="other_income_share", name="Fee & other income share", pillar="margins", unit="pct", direction="neutral", applies="BL",
        meaning="Share of net income from fees and other non-interest sources.", equation="Other income / (NII + other income)")
def other_income_share(c: Ctx):
    return c.div(c.f("other_income"), c.f("net_total_income"), positive=True)


@metric(id="benefits_ratio", name="Benefits ratio", pillar="margins", unit="pct", direction="neutral", applies="INS",
        meaning="Benefits paid plus change in policy reserves per rupee of revenue (Screener 'Other Mfr. Exp' for insurers).",
        equation="Benefits / Revenue")
def benefits_ratio(c: Ctx):
    return c.div(c.f("benefits"), _rev(c), positive=True)


@metric(id="expense_ratio", name="Expense ratio", pillar="margins", unit="pct", direction="lower", applies="INS",
        meaning="Operating expenses other than benefits per rupee of revenue.", equation="(Total opex - Benefits) / Revenue")
def expense_ratio(c: Ctx):
    return c.div(c.f("opex_ex_benefits"), _rev(c), positive=True)
