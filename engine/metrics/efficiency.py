"""Pillar 3: Capital efficiency."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..registry import metric
from .context import Ctx

DAYS = 365.0


def _rev(c):
    return c.f("revenue")


def _inventory_material(c: Ctx) -> pd.Series:
    return c.div(c.f("inventory"), _rev(c), positive=True) >= 0.005


@metric(id="asset_turnover", name="Asset turnover", pillar="capital_efficiency", unit="x", direction="higher", applies="NF",
        meaning="Revenue generated per rupee of total assets (the AT in DuPont).", equation="Revenue / average total assets")
def asset_turnover(c: Ctx):
    return c.div(_rev(c), c.avg("total_assets"), positive=True)


@metric(id="fixed_asset_turnover", name="Fixed-asset turnover", pillar="capital_efficiency", unit="x", direction="higher", applies="NF",
        meaning="Revenue per rupee of net fixed assets (plant, property, equipment, intangibles).",
        equation="Revenue / average net block")
def fixed_asset_turnover(c: Ctx):
    return c.div(_rev(c), c.avg("net_block"), positive=True)


@metric(id="ic_turnover", name="Invested-capital turnover", pillar="capital_efficiency", unit="x", direction="higher", applies="NF",
        meaning="Revenue per rupee of operating invested capital (the turnover half of ROIC).",
        equation="Revenue / average invested capital, IC = equity + borrowings - cash - investments (n/m if IC <= 0)")
def ic_turnover(c: Ctx):
    return c.div(_rev(c), c.avg("invested_capital"), positive=True)


@metric(id="dso", name="Receivable days (DSO)", pillar="capital_efficiency", unit="days", direction="lower", applies="NF",
        meaning="Days of sales tied up in customer receivables (year-end, as Screener's debtor days).",
        equation="Receivables / Revenue x 365")
def dso(c: Ctx):
    return c.div(c.f("receivables"), _rev(c), positive=True) * DAYS


@metric(id="dio", name="Inventory days (DIO)", pillar="capital_efficiency", unit="days", direction="lower", applies="NF",
        meaning="Days of production cost held as inventory (n/m when inventory < 0.5% of revenue or COGS < 2% of revenue).",
        equation="Inventory / COGS x 365, COGS = materials + power & fuel + other mfr.")
def dio(c: Ctx):
    cogs = c.f("cogs")
    ok = _inventory_material(c) & (c.div(cogs, _rev(c), positive=True) >= 0.02)
    return (c.div(c.f("inventory"), cogs, positive=True) * DAYS).where(ok)


def _dio0(c: Ctx) -> pd.Series:
    """DIO with immaterial inventory treated as 0 days (services)."""
    d = c.m("dio")
    return d.where(d.notna(), np.where(~_inventory_material(c) & _rev(c).gt(0), 0.0, np.nan))


@metric(id="dpo", name="Payable days (DPO)", pillar="capital_efficiency", unit="days", direction="higher", applies="NF",
        meaning="Days of production cost financed by suppliers. Needs trade_payables in data/manual (not in the Screener export).",
        equation="Trade payables (manual) / COGS x 365")
def dpo(c: Ctx):
    return c.div(c.manual_series("trade_payables"), c.f("cogs"), positive=True) * DAYS


@metric(id="cash_conversion_cycle", name="Cash conversion cycle", pillar="capital_efficiency", unit="days", direction="lower",
        applies="NF", meaning="Days between paying suppliers and collecting from customers. Needs manual trade payables.",
        equation="DSO + DIO - DPO (DIO = 0 when inventory is immaterial)")
def cash_conversion_cycle(c: Ctx):
    return c.m("dso") + _dio0(c) - c.m("dpo")


@metric(id="operating_cycle", name="Operating cycle", pillar="capital_efficiency", unit="days", direction="lower", applies="NF",
        meaning="Days from buying inventory to collecting cash (before supplier credit): always computable from the export.",
        equation="DSO + DIO (DIO = 0 when inventory is immaterial)")
def operating_cycle(c: Ctx):
    return c.m("dso") + _dio0(c)


@metric(id="nwc_days", name="Net working capital days", pillar="capital_efficiency", unit="days", direction="lower", applies="NF",
        meaning="Non-cash working capital in days of sales; includes payables and provisions implicitly (proxy for CCC). "
                "Negative = suppliers/customers fund the business.",
        equation="(Other assets - cash - other liabilities) / Revenue x 365")
def nwc_days(c: Ctx):
    return c.div(c.f("nwc"), _rev(c), positive=True) * DAYS


@metric(id="capex_to_sales", name="Capex / sales", pillar="capital_efficiency", unit="pct", direction="neutral", applies="NF",
        meaning="Capital spending intensity (capex proxy from the balance sheet).", equation="Capex proxy / Revenue")
def capex_to_sales(c: Ctx):
    return c.div(c.f("capex_proxy"), _rev(c), positive=True)


@metric(id="capex_to_depreciation", name="Capex / depreciation", pillar="capital_efficiency", unit="x", direction="neutral",
        applies="NF", meaning="Above 1 = growing the asset base; persistently below 1 = under-investing (or asset-light).",
        equation="Capex proxy / Depreciation")
def capex_to_depreciation(c: Ctx):
    return c.div(c.f("capex_proxy"), c.f("depreciation"), positive=True)


@metric(id="cwip_to_net_block", name="CWIP / net block", pillar="capital_efficiency", unit="pct", direction="lower", applies="NF",
        meaning="Capital work in progress relative to productive assets: high and persistent = capital locked in projects not yet earning.",
        equation="CWIP / Net block")
def cwip_to_net_block(c: Ctx):
    return c.div(c.f("cwip"), c.f("net_block"), positive=True)


def _intensity(field):
    def f(c: Ctx):
        return c.div(c.avg(field), _rev(c), positive=True)
    return f


for _fid, _field, _nm in [
    ("nb_to_sales", "net_block", "Net block"),
    ("cwip_to_sales", "cwip", "CWIP"),
    ("investments_to_sales", "investments", "Investments"),
    ("receivables_to_sales", "receivables", "Receivables"),
    ("inventory_to_sales", "inventory", "Inventory"),
    ("cash_to_sales", "cash", "Cash & bank"),
    ("other_assets_rest_to_sales", "other_assets_rest", "Other assets (loans, advances, other)"),
    ("other_liabilities_to_sales", "other_liabilities", "Other liabilities"),
]:
    metric(id=_fid, name=f"{_nm} / sales", pillar="capital_efficiency", unit="ratio", direction="lower" if _fid != "other_liabilities_to_sales" else "neutral",
           applies="NF", role="component",
           meaning=f"Average {_nm.lower()} per rupee of revenue: a capital-intensity term in the asset-turnover / IC-turnover driver trees "
                   f"(x365 = days of sales).",
           equation=f"average {_nm} / Revenue")(_intensity(_field))


@metric(id="opex_to_assets", name="Operating cost / average assets", pillar="capital_efficiency", unit="pct", direction="lower",
        applies="FIN", meaning="Operating costs (incl. provisions; insurers: incl. benefits) per rupee of balance sheet.",
        equation="Total opex / average total assets")
def opex_to_assets(c: Ctx):
    return c.div(c.f("total_opex"), c.avg("total_assets"), positive=True)


@metric(id="credit_deposit_proxy", name="Other assets / (deposits + borrowings)", pillar="capital_efficiency", unit="ratio",
        direction="neutral", applies="BL",
        meaning="Proxy for the credit-deposit ratio: advances and other assets per rupee of deposits + borrowings.",
        equation="Other assets / Borrowings (Screener: deposits + borrowings)")
def credit_deposit_proxy(c: Ctx):
    return c.div(c.f("other_assets"), c.f("borrowings"), positive=True)


@metric(id="liquid_assets_ratio", name="Cash + investments / assets", pillar="capital_efficiency", unit="pct", direction="neutral",
        applies="FIN", meaning="Share of the balance sheet in cash and investments (liquidity buffer vs yield).",
        equation="(Cash & bank + Investments) / Total assets")
def liquid_assets_ratio(c: Ctx):
    return c.div(c.f("cash") + c.f("investments"), c.f("total_assets"), positive=True)
