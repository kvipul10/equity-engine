"""Load and validate YAML configuration.

Rule enforced here (CLAUDE.md): every external benchmark carries a source_url and an as_of date.
Engine parameters that are judgement calls are allowed, but must say so (source_type: rule_of_thumb)
and give a rationale.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from .paths import Paths


class ConfigError(ValueError):
    pass


SOURCE_TYPES = {"external", "rule_of_thumb", "derived"}


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise ConfigError(f"Missing config file: {path}")
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def _check_benchmark(where: str, entry: Dict) -> None:
    st = entry.get("source_type", "external")
    if st not in SOURCE_TYPES:
        raise ConfigError(f"{where}: unknown source_type '{st}'")
    if st == "external":
        for k in ("source_url", "as_of"):
            if not entry.get(k):
                raise ConfigError(f"{where}: external benchmark needs '{k}'")
    elif st == "rule_of_thumb":
        for k in ("rationale", "as_of"):
            if not entry.get(k):
                raise ConfigError(f"{where}: rule_of_thumb needs '{k}'")
    elif st == "derived":
        if not entry.get("rationale"):
            raise ConfigError(f"{where}: derived band needs 'rationale'")


def _check_market(market: Dict) -> None:
    def walk(node, path):
        if isinstance(node, dict):
            if "value" in node and not isinstance(node.get("value"), (dict, list)):
                _check_benchmark(path, node)
            for k, v in node.items():
                walk(v, f"{path}.{k}")

    walk(market, "market.yaml")
    st = market.get("synthetic_rating", {})
    for k in ("source_url", "as_of", "table"):
        if not st.get(k):
            raise ConfigError(f"market.yaml.synthetic_rating needs '{k}'")


def _check_bands(name: str, bands: Dict) -> None:
    for section in ("generic", "family", "archetype"):
        for key, val in (bands.get(section) or {}).items():
            if section == "generic":
                _check_benchmark(f"{name}.generic.{key}", val)
            else:
                for metric, entry in (val or {}).items():
                    _check_benchmark(f"{name}.{section}.{key}.{metric}", entry)


@dataclass
class Config:
    market: Dict
    scoring: Dict
    bands: Dict
    sector: Dict
    sectors: Dict
    flags: List[Dict]
    drivers: Dict
    paths: Optional[Paths] = None
    universe: Dict[str, Dict] = field(default_factory=dict)

    @classmethod
    def load(cls, paths: Paths) -> "Config":
        cd = paths.config_dir
        market = _load_yaml(cd / "market.yaml")
        _check_market(market)
        bands = _load_yaml(cd / "bands.yaml")
        _check_bands("bands.yaml", bands)
        sector = _load_yaml(cd / "sector_benchmarks.yaml")
        for arch, mets in (sector.get("bands") or {}).items():
            for metric, entry in mets.items():
                _check_benchmark(f"sector_benchmarks.yaml.bands.{arch}.{metric}", entry)
        for arch, b in (sector.get("betas") or {}).items():
            _check_benchmark(f"sector_benchmarks.yaml.betas.{arch}", b)
        flags = _load_yaml(cd / "flags.yaml").get("rules", [])
        cfg = cls(
            market=market,
            scoring=_load_yaml(cd / "scoring.yaml"),
            bands=bands,
            sector=sector,
            sectors=_load_yaml(cd / "sectors.yaml"),
            flags=flags,
            drivers=_load_yaml(cd / "drivers.yaml"),
            paths=paths,
        )
        cfg.universe = load_universe(paths)
        return cfg

    # ---- archetypes -------------------------------------------------------------------------
    def archetype_info(self, archetype: str) -> Dict:
        arch = self.sectors.get("archetypes", {}).get(archetype)
        if arch is None:
            arch = dict(self.sectors.get("default", {"family": "non_financial"}))
        return arch

    def family(self, archetype: str) -> str:
        return self.archetype_info(archetype).get("family", "non_financial")

    def tokens(self, archetype: str) -> Set[str]:
        info = self.archetype_info(archetype)
        fam = info.get("family", "non_financial")
        toks = {"ALL", archetype}
        if fam == "non_financial":
            toks.add("NF")
        elif fam == "bank_like":
            toks |= {"FIN", "BL"}
            sub = info.get("subtype")
            if sub == "bank":
                toks.add("BANK")
            elif sub == "nbfc":
                toks.add("NBFC")
        elif fam == "insurance":
            toks |= {"FIN", "INS"}
        return toks

    def archetype_of(self, ticker: str) -> str:
        row = self.universe.get(ticker)
        if row:
            return row["archetype"]
        return self.sectors.get("default_archetype", "default")

    def universe_asof(self, ticker: str) -> Optional[str]:
        row = self.universe.get(ticker)
        return row.get("asof") if row else None

    # ---- market helpers ----------------------------------------------------------------------
    def mv(self, *keys: str, default=None):
        node: Any = self.market
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        if isinstance(node, dict) and "value" in node:
            return node["value"]
        return node

    def sv(self, *keys: str, default=None):
        node: Any = self.scoring
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node


def load_universe(paths: Paths) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    p = paths.universe_csv
    if not p.exists():
        return out
    with p.open(newline="") as fh:
        for row in csv.DictReader(fh):
            t = (row.get("ticker") or "").strip()
            if not t:
                continue
            out[t] = {k: (v or "").strip() for k, v in row.items()}
    return out
