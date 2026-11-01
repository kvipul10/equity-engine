"""Sector modules: config/sectors/<archetype>.yaml with single inheritance.

Files whose name starts with '_' are shared bases (not archetypes). Every archetype implicitly extends 'default'.
Merge rules (child over parent):
  scalars (family, subtype, damodaran_industries, evidence, how_to_read): child replaces parent
  metrics_off / metrics_add / manual_kpis / flags: merged by 'id'; an entry {id: x, remove: true} deletes x
  bands / constants: merged by key; a null value deletes the inherited key
  drivers: {add: [...]} merged by tree id, {replace: {generic_tree: sector_tree}} merged by key
  pillar_weights: child replaces parent
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

SCALARS = ("family", "subtype", "damodaran_industries", "evidence", "how_to_read", "pillar_names")
LISTS_BY_ID = ("metrics_off", "metrics_add", "manual_kpis", "flags")
DICTS = ("bands", "constants")
FAMILIES = ("non_financial", "bank_like", "insurance")


class SectorError(ValueError):
    pass


@dataclass
class Sector:
    archetype: str
    family: str
    subtype: Optional[str]
    damodaran_industries: List[str]
    evidence: str
    how_to_read: str
    metrics_off: Dict[str, Dict] = field(default_factory=dict)      # id -> {reason, applies?}
    metrics_add: Dict[str, Dict] = field(default_factory=dict)      # id -> definition
    manual_kpis: Dict[str, Dict] = field(default_factory=dict)      # id -> {unit, required, description, where}
    bands: Dict[str, Dict] = field(default_factory=dict)
    constants: Dict[str, Dict] = field(default_factory=dict)
    flags: List[Dict] = field(default_factory=list)
    drivers_add: List[Dict] = field(default_factory=list)
    drivers_replace: Dict[str, str] = field(default_factory=dict)
    pillar_weights: Optional[Dict[str, float]] = None
    pillar_names: Dict[str, str] = field(default_factory=dict)
    lineage: List[str] = field(default_factory=list)
    file: str = ""

    def info(self) -> Dict:
        """Session-1 compatible dict (family, subtype, industries)."""
        return {"family": self.family, "subtype": self.subtype, "damodaran_industries": self.damodaran_industries,
                "evidence": self.evidence}

    def constant_values(self) -> Dict[str, float]:
        return {k: float(v["value"]) for k, v in self.constants.items()}


def _merge_by_id(parent: List[Dict], child: List[Dict], where: str) -> List[Dict]:
    out: Dict[str, Dict] = {}
    for e in parent or []:
        out[e["id"]] = e
    for e in child or []:
        if "id" not in e:
            raise SectorError(f"{where}: entry without 'id': {e}")
        if e.get("remove"):
            out.pop(e["id"], None)
        else:
            out[e["id"]] = e
    return list(out.values())


def _merge(parent: Dict, child: Dict, where: str) -> Dict:
    m = dict(parent)
    for k in SCALARS:
        if k in child:
            m[k] = child[k]
    for k in LISTS_BY_ID:
        m[k] = _merge_by_id(parent.get(k, []), child.get(k, []), f"{where}.{k}")
    for k in DICTS:
        d = dict(parent.get(k) or {})
        for kk, vv in (child.get(k) or {}).items():
            if vv is None:
                d.pop(kk, None)
            else:
                d[kk] = vv
        m[k] = d
    pd_ = parent.get("drivers") or {}
    cd_ = child.get("drivers") or {}
    m["drivers"] = {"add": _merge_by_id(pd_.get("add", []), cd_.get("add", []), f"{where}.drivers.add"),
                    "replace": {**(pd_.get("replace") or {}), **(cd_.get("replace") or {})}}
    if "pillar_weights" in child:
        m["pillar_weights"] = child["pillar_weights"]
    m["lineage"] = list(parent.get("lineage", [])) + [child.get("archetype") or child.get("_name")]
    return m


def load_raw(sectors_dir: Path) -> Dict[str, Dict]:
    if not sectors_dir.is_dir():
        raise SectorError(f"Missing sector config directory {sectors_dir}")
    raw = {}
    for p in sorted(sectors_dir.glob("*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        d["_name"] = p.stem
        d["_file"] = f"config/sectors/{p.name}"
        for k in LISTS_BY_ID:
            for e in d.get(k) or []:
                if isinstance(e, dict):
                    e.setdefault("_origin", d["_file"])
        for t in (d.get("drivers") or {}).get("add", []) or []:
            t.setdefault("_origin", d["_file"])
        for k in DICTS:
            for v in (d.get(k) or {}).values():
                if isinstance(v, dict):
                    v.setdefault("_origin", d["_file"])
        raw[p.stem] = d
    if "default" not in raw:
        raise SectorError("config/sectors/default.yaml is required")
    return raw


def resolve_all(raw: Dict[str, Dict]) -> Dict[str, Sector]:
    cache: Dict[str, Dict] = {}

    def resolve(name: str, stack=()) -> Dict:
        if name in cache:
            return cache[name]
        if name in stack:
            raise SectorError(f"circular 'extends': {' -> '.join(stack + (name,))}")
        if name not in raw:
            raise SectorError(f"unknown sector '{name}' (extends in {stack[-1] if stack else '?'})")
        d = raw[name]
        parent_name = d.get("extends")
        if parent_name is None and name != "default":
            parent_name = "default"
        base = resolve(parent_name, stack + (name,)) if parent_name else {"lineage": []}
        merged = _merge(base, d, name)
        merged["_file"] = d["_file"]
        cache[name] = merged
        return merged

    out: Dict[str, Sector] = {}
    for name in raw:
        r = resolve(name)
        if name.startswith("_"):
            continue
        fam = r.get("family")
        if fam not in FAMILIES:
            raise SectorError(f"{name}: family must be one of {FAMILIES} (got {fam})")
        if not r.get("damodaran_industries"):
            raise SectorError(f"{name}: damodaran_industries is required")
        how = (r.get("how_to_read") or "").strip()
        if not how:
            raise SectorError(f"{name}: how_to_read is required")
        out[name] = Sector(
            archetype=name, family=fam, subtype=r.get("subtype"), damodaran_industries=list(r["damodaran_industries"]),
            evidence=r.get("evidence", ""), how_to_read=how,
            metrics_off={e["id"]: e for e in r.get("metrics_off", [])},
            metrics_add={e["id"]: e for e in r.get("metrics_add", [])},
            manual_kpis={e["id"]: e for e in r.get("manual_kpis", [])},
            bands=r.get("bands") or {}, constants=r.get("constants") or {}, flags=r.get("flags", []),
            drivers_add=(r.get("drivers") or {}).get("add", []), drivers_replace=(r.get("drivers") or {}).get("replace", {}),
            pillar_weights=r.get("pillar_weights"), pillar_names=r.get("pillar_names") or {},
            lineage=[x for x in r.get("lineage", []) if x], file=r.get("_file", ""),
        )
    return out


def load_sectors(config_dir: Path) -> Dict[str, Sector]:
    return resolve_all(load_raw(config_dir / "sectors"))
