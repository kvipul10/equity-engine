"""Metric formulas, one module per pillar. Importing engine.registry.load_all() registers them."""
from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from .context import Ctx, MetricError


def compute_all(std, cfg, coc) -> Tuple[Dict[str, pd.Series], Ctx]:
    from ..registry import load_all

    reg = load_all()
    ctx = Ctx(std, cfg, coc)
    out: Dict[str, pd.Series] = {}
    for mid, m in reg.items():
        if not m.applies_to(ctx.tokens):
            continue
        try:
            out[mid] = ctx.m(mid)
        except MetricError as e:
            out[mid] = ctx.empty()
            ctx.info[mid] = f"not computed: {e}"
    return out, ctx
