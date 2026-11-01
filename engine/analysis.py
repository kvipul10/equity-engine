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
from .scoring import band_vars, merger_exclusions, roll_up, score_metric
from .standardise import Standardised, load_standardised


@dataclass
class Computed:
    std: Standardised
    coc: object
    metrics: Dict[str, pd.Series]
    ctx: object


def compute(ticker: str, cfg: Config, asof: Optional[str] = None, beta: Optional[float] = None,
            archetype: Optional[str] = None, fy_end: bool = False) -> Computed:
    load_all()
    std = load_standardised(ticker, cfg, archetype=archetype, asof=normalise_asof(asof), fy_end=fy_end)
    coc = capital_cost.compute(std, cfg, beta_override=beta)
    metrics, ctx = compute_all(std, cfg, coc)
    return Computed(std=std, coc=coc, metrics=metrics, ctx=ctx)


class PeerSet:
    """Latest metric values of same-archetype companies, computed as of the same fiscal year (no look-ahead)."""

    def __init__(self, cfg: Config, cache: Optional[Dict] = None, fy_end: bool = False):
        self.cfg = cfg
        self.cache = cache if cache is not None else {}
        self.fy_end = fy_end

    def members(self, archetype: str) -> List[str]:
        return [t for t, r in self.cfg.universe.items() if r.get("archetype") == archetype]

    def _latest(self, ticker: str, asof_label: str) -> Optional[Dict[str, float]]:
        key = (ticker, asof_label)
        if key in self.cache:
            return self.cache[key]
        try:
            c = compute(ticker, self.cfg, asof=asof_label, fy_end=self.fy_end)
        except (ValueError, FileNotFoundError):
            self.cache[key] = None
            return None
        if c.std.last_fy != asof_label:
            self.cache[key] = None
            return None
        vals = {mid: (float(s.iloc[-1]) if len(s) and not pd.isna(s.iloc[-1]) else None) for mid, s in c.metrics.items()}
        self.cache[key] = vals
        return vals

    def table(self, archetype: str, asof_label: str, ticker: str) -> Dict[str, Dict[str, float]]:
        """{peer ticker: {metric: latest value}} for same-archetype companies with data at the same as-of year
        (any number of peers; used by the report, not by scoring)."""
        out = {}
        for t in self.members(archetype):
            if t == ticker:
                continue
            r = self._latest(t, asof_label)
            if r:
                out[t] = {k: v for k, v in r.items() if v is not None}
        return out

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
            archetype: Optional[str] = None, peers: Optional[PeerSet] = None, fy_end: bool = False) -> Dict:
    comp = compute(ticker, cfg, asof=asof, beta=beta, archetype=archetype, fy_end=fy_end)
    std, coc, metrics, ctx = comp.std, comp.coc, comp.metrics, comp.ctx
    names = band_vars(cfg, coc)
    sector = cfg.sector_of(std.archetype)
    names.update(sector.constant_values())
    manual = std.manual.reindex(std.annual.index) if std.manual is not None and not std.manual.empty else None
    flags = evaluate_rules(cfg.rules_for(std.archetype), metrics, std.annual, ctx.tokens, names, manual=manual, info=ctx.info)
    triggered = [f for f in flags if f["status"] == "triggered"]
    peers = peers or PeerSet(cfg, fy_end=fy_end)
    peer_vals = peers.values(std.archetype, std.last_fy, ticker, metrics)
    results = {}
    for mid, s in metrics.items():
        results[mid] = score_metric(mid, s, std.last_fy, cfg, std.archetype, std.family, names, peer_vals.get(mid) if peer_vals else None)
    merger_exclusions(results, std.notes, std.last_fy)
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
    from .report.findings import build_findings

    rep = build_report(comp, results, pillars, overall, flags, drivers, cfg, names,
                       peer_table=peers.table(std.archetype, std.last_fy, ticker))
    rep["findings"] = build_findings(rep, cfg)
    return rep
