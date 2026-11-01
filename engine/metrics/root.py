"""Root of the MECE tree: does the company create value?"""
from __future__ import annotations

from ..registry import metric
from .context import Ctx
from .returns import avg_ic, nopat


@metric(id="economic_profit", name="Economic profit", pillar="root", unit="inr_cr", direction="higher", applies="ALL", role="root",
        stability=False,
        meaning="Rupees of value created (or destroyed) in the year after charging for all capital at its required return.",
        equation="Non-financials: (ROIC - WACC) x average IC = NOPAT - WACC x average IC (defined even when IC <= 0); "
                 "financials: (ROE - Ke) x average equity")
def economic_profit(c: Ctx):
    if "NF" in c.tokens:
        return nopat(c) - c.coc.wacc.reindex(c.idx) * avg_ic(c)
    return (c.m("roe") - c.coc.ke.reindex(c.idx)) * c.avg("equity")
