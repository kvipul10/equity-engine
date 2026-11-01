"""The metric registry: every metric is defined exactly once, here, via the @metric decorator.

Each entry carries: id, name, pillar, formula (the decorated function), direction, applicable archetypes
(tokens), unit, plain-English meaning and its equation. docs/metrics.md is generated from this registry
(`python -m engine metrics --markdown`).

Archetype tokens: ALL, NF (non-financial), FIN (bank-like + insurance), BL (bank + NBFC), BANK, NBFC, INS,
or an explicit archetype name from config/sectors.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Tuple

PILLARS = (
    "growth",
    "margins",
    "capital_efficiency",
    "returns",
    "cash_quality",
    "balance_sheet",
    "capital_allocation",
    "valuation",
)
PILLAR_NAMES = {
    "root": "Root: value creation",
    "growth": "1 Growth",
    "margins": "2 Margins",
    "capital_efficiency": "3 Capital efficiency",
    "returns": "4 Returns",
    "cash_quality": "5 Cash and earnings quality",
    "balance_sheet": "6 Balance sheet",
    "capital_allocation": "7 Capital allocation",
    "valuation": "8 Valuation",
}
DIRECTIONS = ("higher", "lower", "target", "neutral")
UNITS = ("pct", "pp", "x", "days", "ratio", "inr_cr", "inr", "num", "count", "score")
ROLES = ("scored", "component", "root")
TOKENS = {"ALL", "NF", "FIN", "BL", "BANK", "NBFC", "INS"}


@dataclass(frozen=True)
class Metric:
    id: str
    name: str
    pillar: str
    unit: str
    direction: str
    applies: Tuple[str, ...]
    meaning: str
    equation: str
    func: Callable
    role: str = "scored"
    trend: bool = True
    stability: bool = True
    kind: str = "annual"  # annual: value per FY; point: only at the as-of FY
    origin: str = "engine"  # 'engine' (Python, engine/metrics/) or the sector file that defines it
    formula: str = ""  # sector metrics: the formula in the safe expression language

    def applies_to(self, tokens: Iterable[str]) -> bool:
        toks = set(tokens)
        return any(a in toks for a in self.applies)


REGISTRY: Dict[str, Metric] = {}


def validate_fields(id: str, pillar: str, direction: str, unit: str, role: str, kind: str) -> None:
    if pillar not in PILLARS and pillar != "root":
        raise ValueError(f"{id}: unknown pillar {pillar}")
    if direction not in DIRECTIONS:
        raise ValueError(f"{id}: unknown direction {direction}")
    if unit not in UNITS:
        raise ValueError(f"{id}: unknown unit {unit}")
    if role not in ROLES:
        raise ValueError(f"{id}: unknown role {role}")
    if kind not in ("annual", "point"):
        raise ValueError(f"{id}: unknown kind {kind}")


def metric(id: str, name: str, pillar: str, unit: str, direction: str, applies, meaning: str, equation: str,
           role: str = "scored", trend: bool = True, stability: bool = True, kind: str = "annual"):
    if isinstance(applies, str):
        applies = (applies,)
    validate_fields(id, pillar, direction, unit, role, kind)
    if not meaning or not equation:
        raise ValueError(f"{id}: meaning and equation are required")

    def deco(fn):
        if id in REGISTRY:
            raise ValueError(f"metric '{id}' defined twice")
        REGISTRY[id] = Metric(id=id, name=name, pillar=pillar, unit=unit, direction=direction, applies=tuple(applies),
                              meaning=meaning, equation=equation, func=fn, role=role, trend=trend and kind == "annual",
                              stability=stability and kind == "annual", kind=kind)
        return fn

    return deco


def load_all() -> Dict[str, Metric]:
    """Import the metric modules (registration happens at import)."""
    from .metrics import (  # noqa: F401
        allocation,
        balance_sheet,
        cash_quality,
        efficiency,
        growth,
        margins,
        returns,
        root,
        valuation,
    )

    return REGISTRY


def to_markdown() -> str:
    reg = load_all()
    try:  # include sector metrics defined in config/sectors/*.yaml
        from .config import Config
        from .paths import Paths

        Config.load(Paths.default())
        reg = REGISTRY
    except Exception:  # pragma: no cover - docs still render engine metrics
        pass
    lines = ["# Metric registry", "",
             "Generated from `engine/registry.py` by `python -m engine metrics --markdown`. Do not edit by hand.", "",
             "Units: pct = fraction shown as %, pp = difference of fractions shown as percentage points, x = multiple. "
             "Applies: ALL, NF = non-financial, FIN = financials, BL = bank + NBFC, BANK, NBFC, INS = insurance. "
             "Role: scored (gets level/trend/stability and a RAG), component (shown, used by driver trees, not scored), "
             "root (the value-creation verdict). Origin: `engine` = Python (engine/metrics/), otherwise the sector file "
             "that defines the metric (formula in the safe expression language).", ""]
    for p in ("root",) + PILLARS:
        ms = [m for m in reg.values() if m.pillar == p]
        if not ms:
            continue
        lines += [f"## {PILLAR_NAMES[p]}", "", "| id | name | unit | direction | applies | role | origin | equation | meaning |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for m in ms:
            eq = m.equation.replace("|", "\\|")
            if m.formula:
                eq += f"<br>`{m.formula.replace('|', '/')}`"
            lines.append(f"| `{m.id}` | {m.name} | {m.unit} | {m.direction} | {', '.join(m.applies)} | {m.role}"
                         f"{' (point)' if m.kind == 'point' else ''} | {m.origin} | {eq} | {m.meaning} |")
        lines.append("")
    return "\n".join(lines)
