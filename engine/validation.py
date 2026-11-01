"""Validation against pre-registered analyst/press expectations (validation/expected.yaml).

expected.yaml is written and committed before the engine is compared (see validation/expected.md). Each expected
item names its engine signals in advance:
  strength  -> matched when any signal metric is GREEN at the as-of year
  weakness  -> matched when any signal metric is RED, or AMBER with a deteriorating trend, or any signal flag fired
A stricter "headline" match also requires the signal to appear in the report's top lists (strengths for a strength;
weaknesses or watch for a weakness) or in its bull/bear evidence.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

from .registry import REGISTRY

TAG_NOTE = {"financial": "visible in the Screener financials", "kpi": "needs a manual KPI",
            "qualitative": "not a number in the data"}


def load_expected(path: Path) -> Dict:
    return yaml.safe_load(Path(path).read_text())


def check_expected(cfg, exp: Dict) -> List[str]:
    """Signals must exist, apply to the company's archetype and not be switched off by its sector module."""
    problems = []
    for t, c in exp["companies"].items():
        arch = c["archetype"]
        tokens, off = cfg.tokens(arch), set(cfg.sectors[arch].metrics_off)
        rules = {r["id"]: r for r in cfg.rules_for(arch)}
        seen = set()
        for kind in ("strengths", "weaknesses"):
            for it in c.get(kind) or []:
                if it["id"] in seen:
                    problems.append(f"{it['id']}: duplicate id")
                seen.add(it["id"])
                if it.get("tag") not in TAG_NOTE:
                    problems.append(f"{it['id']}: tag {it.get('tag')!r}")
                if not it.get("sources") or not all(str(s.get("url", "")).startswith("http") and s.get("date") for s in it["sources"]):
                    problems.append(f"{it['id']}: every item needs sources with url and date")
                for m in it["signals"].get("metrics", []):
                    if m not in REGISTRY:
                        problems.append(f"{it['id']}: unknown metric {m}")
                    elif not REGISTRY[m].applies_to(tokens) or m in off:
                        problems.append(f"{it['id']}: metric {m} not applicable to {arch}")
                for f in it["signals"].get("flags", []):
                    r = rules.get(f)
                    if r is None or not (set(r.get("applies", ["ALL"])) & tokens):
                        problems.append(f"{it['id']}: flag {f} not applicable to {arch}")
                if it.get("tag") != "qualitative" and not (it["signals"].get("metrics") or it["signals"].get("flags")):
                    problems.append(f"{it['id']}: a non-qualitative item needs at least one signal")
    return problems


def expected_markdown(exp: Dict) -> str:
    """Human-readable twin of expected.yaml (same content, generated so the two never drift)."""
    lines = ["# Expected strengths and weaknesses (pre-registered)", "",
             "Written from published analyst and press commentary found by web search in Session 4, **before** the",
             "engine was run or compared. The commit that adds this file precedes every comparison (see `git log`).",
             "`validation/expected.yaml` is the machine-readable twin; this file is generated from it.", "",
             "- **Scope:** the 16 `test` companies as of FY26; the 4 `peer` companies (ICICI Bank, Infosys, Nestle,",
             "  HAL) as a holdout scored only before and after fixing; Yes Bank as of FY18 (warning signs before the collapse).",
             "- **Signals** are engine metric ids and flag ids chosen in advance from `docs/metrics.md` and `docs/flags.md`",
             "  by meaning. A strength counts as found if a signal metric is GREEN; a weakness if a signal metric is RED,",
             "  or AMBER and deteriorating, or a signal flag fires.",
             "- **Tags:** `financial` (visible in the Screener financials), `kpi` (needs a manual KPI), `qualitative`",
             "  (not a number in the data; reported separately).",
             "- **Disclosure:** earlier sessions produced reports, and parts of the TCS, HDFC Bank, DLF, Tata Steel and",
             "  Yes Bank outputs were seen then. Every item below rests on the cited sources.",
             "- **Sources** are mostly results coverage and brokerage notes as reported by media; figures in them vary",
             "  slightly between outlets. They were taken from search extracts, not from the primary documents.", ""]
    for t, c in exp["companies"].items():
        role = c.get("role")
        head = f"## {t} ({c['archetype']}, as of {c['asof']})"
        if c.get("holdout"):
            head += " — holdout"
        if role == "blowup":
            head += " — blow-up"
        lines += [head, ""]
        if c.get("note"):
            lines += [c["note"], ""]
        for kind, title in (("strengths", "Strengths"), ("weaknesses", "Warning signs" if role == "blowup" else "Weaknesses")):
            items = c.get(kind) or []
            if not items:
                continue
            lines += [f"**{title}**", ""]
            for it in items:
                sig = ", ".join([f"`{m}`" for m in it["signals"].get("metrics", [])] +
                                [f"flag `{f}`" for f in it["signals"].get("flags", [])]) or "none (qualitative)"
                src = "; ".join(f"[{s.get('what') or s['url']}]({s['url']}) ({s['date']})" for s in it["sources"])
                lines.append(f"{it['id'].split('-')[-1]}. {it['claim']} — *{it['tag']}*. Signals: {sig}. Sources: {src}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
