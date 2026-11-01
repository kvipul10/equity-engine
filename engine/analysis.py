"""One-company pipeline: standardise -> cost of capital -> metrics -> flags -> scoring -> drivers -> report dict."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import capital_cost
from .asof import normalise_asof
from .config import Config
from .drivers import run_trees
from .flags import evaluate_rules
from .metrics import compute_all
from .registry import REGISTRY, load_all
from .scoring import band_vars, roll_up, score_metric
from .standardise import Standardised, load_standardised


@dataclass
class Computed:
    std: Standardised
    coc: object
    metrics: Dict[str, pd.Series]
    ctx: object


def compute(ticker: str, cfg: Config, asof: Optional[str] = None, beta: Optional[float] = None,
            archetype: Optional[str] = None) -> Computed:
    load_all()
    std = load_standardised(ticker, cfg, archetype=archetype, asof=normalise_asof(asof))
    coc = capital_cost.compute(std, cfg, beta_override=beta)
    metrics, ctx = compute_all(std, cfg, coc)
    return Computed(std=std, coc=coc, metrics=metrics, ctx=ctx)


class PeerSet:
    """Latest metric values of same-archetype companies, computed as of the same fiscal year (no look-ahead)."""

    def __init__(self, cfg: Config, cache: Optional[Dict] = None):
        self.cfg = cfg
        self.cache = cache if cache is not None else {}

    def members(self, archetype: str) -> List[str]:
        return [t for t, r in self.cfg.universe.items() if r.get("archetype") == archetype]

    def _latest(self, ticker: str, asof_label: str) -> Optional[Dict[str, float]]:
        key = (ticker, asof_label)
        if key in self.cache:
            return self.cache[key]
        try:
            c = compute(ticker, self.cfg, asof=asof_label)
        except (ValueError, FileNotFoundError):
            self.cache[key] = None
            return None
        if c.std.last_fy != asof_label:
            self.cache[key] = None
            return None
        vals = {mid: (float(s.iloc[-1]) if len(s) and not pd.isna(s.iloc[-1]) else None) for mid, s in c.metrics.items()}
        self.cache[key] = vals
        return vals

    def values(self, archetype: str, asof_label: str, ticker: str, own: Dict[str, pd.Series]) -> Dict[str, List[float]]:
        members = self.members(archetype)
        need = int(self.cfg.scoring["level"]["min_peers_for_percentile"])
        if ticker in members:
            others = [t for t in members if t != ticker]
        else:
            others = members
        if len(others) + 1 < need:
            return {}
        rows = [r for r in (self._latest(t, asof_label) for t in others) if r]
        out: Dict[str, List[float]] = {}
        for mid, s in own.items():
            v = s.iloc[-1] if len(s) else np.nan
            vals = [r.get(mid) for r in rows if r.get(mid) is not None]
            if not pd.isna(v):
                vals.append(float(v))
            out[mid] = vals
        return out


def analyse(ticker: str, cfg: Config, asof: Optional[str] = None, beta: Optional[float] = None,
            archetype: Optional[str] = None, peers: Optional[PeerSet] = None) -> Dict:
    comp = compute(ticker, cfg, asof=asof, beta=beta, archetype=archetype)
    std, coc, metrics, ctx = comp.std, comp.coc, comp.metrics, comp.ctx
    names = band_vars(cfg, coc)
    sector = cfg.sector_of(std.archetype)
    names.update(sector.constant_values())
    manual = std.manual.reindex(std.annual.index) if std.manual is not None and not std.manual.empty else None
    flags = evaluate_rules(cfg.rules_for(std.archetype), metrics, std.annual, ctx.tokens, names, manual=manual, info=ctx.info)
    triggered = [f for f in flags if f["status"] == "triggered"]
    peer_vals = (peers or PeerSet(cfg)).values(std.archetype, std.last_fy, ticker, metrics)
    results = {}
    for mid, s in metrics.items():
        results[mid] = score_metric(mid, s, std.last_fy, cfg, std.archetype, std.family, names, peer_vals.get(mid) if peer_vals else None)
    pillars, overall = roll_up(results, std.family, cfg, triggered, archetype=std.archetype)

    def get(node):
        if node.startswith("kpi:"):
            return ctx.manual_series(node[4:])
        if node in metrics:
            return metrics[node]
        if node in std.annual.columns:
            return pd.to_numeric(std.annual[node], errors="coerce")
        if node in REGISTRY and REGISTRY[node].applies_to(ctx.tokens):  # switched-off metric still usable as a node
            return ctx.m(node)
        if manual is not None and node in manual.columns:
            return ctx.manual_series(node)
        return None

    drivers = run_trees(cfg, ctx.tokens, get, std.last_fy, set(std.years), sector=sector, explain=lambda n: ctx.info.get(n))
    from .report import build_report

    return build_report(comp, results, pillars, overall, flags, drivers, cfg, names)
