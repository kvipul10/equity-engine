"""Load and validate YAML configuration.

Rule enforced here (CLAUDE.md): every external benchmark carries a source_url and an as_of date. Values that are
judgement calls are allowed but must say so (source_type: indicative, with a rationale and date) and are shown as
'indicative' in every report. ('rule_of_thumb', the Session-1 name, is accepted as an alias.)
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from .paths import Paths
from .sectors import Sector, load_sectors


class ConfigError(ValueError):
    pass


SOURCE_TYPES = {"external", "indicative", "rule_of_thumb", "derived"}


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise ConfigError(f"Missing config file: {path}")
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def normalise_source_type(st: Optional[str]) -> str:
    st = st or "external"
    return "indicative" if st == "rule_of_thumb" else st


def _check_benchmark(where: str, entry: Dict) -> None:
    if not isinstance(entry, dict):
        raise ConfigError(f"{where}: benchmark must be a mapping")
    st = entry.get("source_type", "external")
    if st not in SOURCE_TYPES:
        raise ConfigError(f"{where}: unknown source_type '{st}'")
    st = normalise_source_type(st)
    if st == "external":
        for k in ("source_url", "as_of"):
            if not entry.get(k):
                raise ConfigError(f"{where}: external benchmark needs '{k}'")
    elif st == "indicative":
        for k in ("rationale", "as_of"):
            if not entry.get(k):
                raise ConfigError(f"{where}: indicative benchmark needs '{k}'")
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


def _check_sectors(sectors: Dict[str, Sector]) -> None:
    for a, s in sectors.items():
        for mid, b in s.bands.items():
            _check_benchmark(f"{s.file} bands.{mid}", b)
        for k, c in s.constants.items():
            if "value" not in c:
                raise ConfigError(f"{s.file} constants.{k}: needs 'value'")
            _check_benchmark(f"{s.file} constants.{k}", c)
        for kid, k in s.manual_kpis.items():
            for f in ("unit", "description"):
                if not k.get(f):
                    raise ConfigError(f"{s.file} manual_kpis.{kid}: needs '{f}'")


@dataclass
class Config:
    market: Dict
    scoring: Dict
    bands: Dict
    sector: Dict                     # generated Damodaran benchmarks (config/sector_benchmarks.yaml)
    sectors: Dict[str, Sector]       # sector modules (config/sectors/*.yaml), resolved
    flags: List[Dict]                # generic rules (config/flags.yaml)
    drivers: Dict
    paths: Optional[Paths] = None
    universe: Dict[str, Dict] = field(default_factory=dict)

    @classmethod
    def load(cls, paths: Paths) -> "Config":
        from .registry import load_all
        from .sector_metrics import register

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
        sectors = load_sectors(cd)
        _check_sectors(sectors)
        flags = _load_yaml(cd / "flags.yaml").get("rules", [])
        cfg = cls(market=market, scoring=_load_yaml(cd / "scoring.yaml"), bands=bands, sector=sector, sectors=sectors,
                  flags=flags, drivers=_load_yaml(cd / "drivers.yaml"), paths=paths)
        cfg.universe = load_universe(paths)
        load_all()
        register(sectors)
        return cfg

    # ---- archetypes -------------------------------------------------------------------------
    def sector_of(self, archetype: str) -> Sector:
        return self.sectors.get(archetype) or self.sectors["default"]

    def archetype_info(self, archetype: str) -> Dict:
        return self.sector_of(archetype).info()

    def family(self, archetype: str) -> str:
        return self.sector_of(archetype).family

    def tokens(self, archetype: str) -> Set[str]:
        s = self.sector_of(archetype)
        toks = {"ALL", archetype}
        if s.family == "non_financial":
            toks.add("NF")
        elif s.family == "bank_like":
            toks |= {"FIN", "BL"}
            if s.subtype == "bank":
                toks.add("BANK")
            elif s.subtype == "nbfc":
                toks.add("NBFC")
        elif s.family == "insurance":
            toks |= {"FIN", "INS"}
        return toks

    def archetype_of(self, ticker: str) -> str:
        row = self.universe.get(ticker)
        return row["archetype"] if row else "default"

    def universe_asof(self, ticker: str) -> Optional[str]:
        row = self.universe.get(ticker)
        return row.get("asof") if row else None

    def rules_for(self, archetype: str) -> List[Dict]:
        """Generic red-flag rules plus the sector's own rules."""
        return list(self.flags) + list(self.sector_of(archetype).flags)

    def all_rules(self) -> List[Dict]:
        seen, out = set(), []
        for r in list(self.flags) + [r for s in self.sectors.values() for r in s.flags]:
            key = (r["id"], r.get("_origin", "config/flags.yaml"))
            if key not in seen:
                seen.add(key)
                out.append(r)
        return out

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
