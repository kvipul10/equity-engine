"""Metric formulas, one module per pillar. Importing engine.registry.load_all() registers them; sector metrics are
registered from config/sectors/*.yaml when the Config is loaded."""
from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from .context import Ctx, MetricError


def switched_off(sector, reg) -> Dict[str, str]:
    """Expand a sector's metrics_off into {metric id: reason}. Entries: {id, reason} or a group {id, applies: TOKEN, reason}
    that switches off every metric whose applicability is exactly that token (e.g. all non-financial-only metrics)."""
    out: Dict[str, str] = {}
    for key, e in (sector.metrics_off or {}).items():
        reason = e.get("reason", "switched off for this sector")
        grp = e.get("applies")
        if grp:
            for mid, m in reg.items():
                if tuple(m.applies) == (grp,):
                    out.setdefault(mid, reason)
        else:
            out[key] = reason
    return out


def compute_all(std, cfg, coc) -> Tuple[Dict[str, pd.Series], Ctx]:
    from ..registry import load_all

    reg = load_all()
    ctx = Ctx(std, cfg, coc)
    ctx.switched_off = switched_off(ctx.sector, reg)
    ctx.switched_off_groups = [{"id": k, "applies": e["applies"], "reason": e.get("reason", "")}
                               for k, e in (ctx.sector.metrics_off or {}).items() if e.get("applies")]
    out: Dict[str, pd.Series] = {}
    for mid, m in reg.items():
        if not m.applies_to(ctx.tokens) or mid in ctx.switched_off:
            continue
        try:
            out[mid] = ctx.m(mid)
        except MetricError as e:
            out[mid] = ctx.empty()
            ctx.info[mid] = f"not computed: {e}"
    return out, ctx
