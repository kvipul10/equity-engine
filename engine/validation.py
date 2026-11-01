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


# ---------------------------------------------------------------------------------------------- comparison
RAGS = ("green", "amber", "red")


def report_path(reports_dir: Path, ticker: str, asof: str) -> Path:
    """reports/<T>/asof_<FY>/analysis.json for as-of runs, else reports/<T>/analysis.json."""
    p = Path(reports_dir) / ticker / f"asof_{asof}" / "analysis.json"
    return p if p.exists() else Path(reports_dir) / ticker / "analysis.json"


def _headline_ids(rep: Dict, kind: str) -> set:
    f = rep.get("findings") or {}
    if kind == "strengths":
        return {c["id"] for c in f.get("strengths", [])} | {b.get("ref") for b in f.get("bull", [])}
    return ({c["id"] for c in f.get("weaknesses", [])} | {c["id"] for c in f.get("watch", [])}
            | {b.get("ref") for b in f.get("bear", [])})


def assess_item(item: Dict, kind: str, rep: Dict) -> Dict:
    """Match one expected item against one analysis.json (see the module docstring for the rules)."""
    ms = rep["metrics"]
    fired = {f["id"] for f in (rep.get("flags") or {}).get("triggered", [])}
    not_eval = {f["id"] for f in (rep.get("flags") or {}).get("not_evaluable", [])}
    sig_m, sig_f = item["signals"].get("metrics", []), item["signals"].get("flags", [])
    evidence, computed, hits, opposite = [], 0, [], []
    for m in sig_m:
        r = ms.get(m)
        if r is None or r.get("value") is None:
            evidence.append(f"{m} n/a" + (f" ({r.get('note') or r.get('reason')})" if r and (r.get("note") or r.get("reason")) else ""))
            continue
        computed += 1
        rag, label = r.get("rag"), (r.get("trend") or {}).get("label")
        evidence.append(f"{m} {(rag or 'unscored').upper()} {r.get('value_text')}" + (f" ({label})" if label else ""))
        if kind == "strengths":
            if rag == "green":
                hits.append(m)
            elif rag == "red":
                opposite.append(m)
        else:
            if rag == "red" or (rag == "amber" and label == "deteriorating"):
                hits.append(m)
            elif rag == "green":
                opposite.append(m)
    for f in sig_f:
        if f in fired:
            hits.append(f)
            evidence.append(f"flag {f} fired")
            computed += 1
        elif f in not_eval:
            evidence.append(f"flag {f} not evaluable")
        else:
            evidence.append(f"flag {f} clear")
            computed += 1
    head = _headline_ids(rep, kind)
    strengths_head = _headline_ids(rep, "strengths")
    matched = bool(hits)
    blocked = not matched and computed == 0 and item.get("tag") != "qualitative"
    if kind == "strengths":
        contradicted = not matched and bool(opposite)
    else:  # the engine headlines as a strength what analysts call a weakness
        contradicted = not matched and bool(set(opposite) & strengths_head)
    if matched:
        status = "match"
    elif item.get("tag") == "qualitative":
        status = "miss (qualitative)"
    elif blocked:
        status = "miss (missing data)"
    elif contradicted:
        status = "contradicted"
    else:
        status = "miss"
    return {"id": item["id"], "kind": kind, "tag": item.get("tag"), "claim": item["claim"], "status": status,
            "matched": matched, "headline": matched and bool(set(hits) & head), "contradicted": contradicted,
            "blocked": blocked, "hits": hits, "evidence": evidence}


def headline_items(rep: Dict) -> List[Dict]:
    """The engine's headline claims that adjudication reviews: top strengths, top weaknesses, high/medium flags."""
    f = rep.get("findings") or {}
    out = [{"list": "strengths", "id": c["id"], "text": c["text"]} for c in f.get("strengths", [])]
    out += [{"list": "weaknesses", "id": c["id"], "text": c["text"]} for c in f.get("weaknesses", [])]
    seen = {(o["list"], o["id"]) for o in out}
    for fl in (rep.get("flags") or {}).get("triggered", []):
        if fl["severity"] in ("high", "medium") and ("weaknesses", fl["id"]) not in seen:
            out.append({"list": "flags", "id": fl["id"], "text": f"{fl['id']} {fl['name']}: {fl.get('text', '')}"})
    return out


def _rate(n: int, d: int) -> Dict:
    return {"n": n, "d": d, "rate": (n / d) if d else None}


def evaluate(exp: Dict, reports_dir: Path, adjudication: Dict = None, sets=("test", "blowup")) -> Dict:
    adjudication = adjudication or {}
    companies, rows = {}, []
    for t, c in exp["companies"].items():
        role = "holdout" if c.get("holdout") else c.get("role", "test")
        if role not in sets:
            continue
        path = report_path(reports_dir, t, c["asof"])
        if not path.exists():
            companies[t] = {"error": f"no report at {path}"}
            continue
        import json

        rep = json.loads(path.read_text())
        if rep["asof"]["fy"] != c["asof"]:
            companies[t] = {"error": f"report is as of {rep['asof']['fy']}, expected {c['asof']}"}
            continue
        items = [assess_item(it, k, rep) for k in ("strengths", "weaknesses") for it in (c.get(k) or [])]
        heads = headline_items(rep)
        adj = adjudication.get(t, {}) or {}
        false_alarms = [{"source": "contradiction", "id": i["id"], "text": i["claim"], "evidence": i["evidence"]}
                        for i in items if i["contradicted"]]
        for h in heads:
            a = adj.get(f"{h['list']}:{h['id']}")
            if a and a.get("verdict") == "false_alarm":
                false_alarms.append({"source": "review", "id": h["id"], "list": h["list"], "text": h["text"],
                                     "reason": a.get("reason"), "cause": a.get("cause")})
        companies[t] = {"archetype": c["archetype"], "role": role, "asof": c["asof"], "items": items,
                        "headline_items": heads, "false_alarms": false_alarms,
                        "reviewed": sum(1 for h in heads if f"{h['list']}:{h['id']}" in adj)}
        for i in items:
            rows.append({**i, "ticker": t, "archetype": c["archetype"], "role": role})

    def summary(sel: List[Dict]) -> Dict:
        nq = [r for r in sel if r["tag"] != "qualitative"]
        nd = [r for r in nq if not r["blocked"]]
        return {"all": _rate(sum(r["matched"] for r in sel), len(sel)),
                "excl_qualitative": _rate(sum(r["matched"] for r in nq), len(nq)),
                "excl_qualitative_and_missing_data": _rate(sum(r["matched"] for r in nd), len(nd)),
                "headline": _rate(sum(r["headline"] for r in sel), len(sel)),
                "strengths": _rate(sum(r["matched"] for r in sel if r["kind"] == "strengths"), sum(1 for r in sel if r["kind"] == "strengths")),
                "weaknesses": _rate(sum(r["matched"] for r in sel if r["kind"] == "weaknesses"), sum(1 for r in sel if r["kind"] == "weaknesses"))}

    by_set = {s: summary([r for r in rows if r["role"] == s]) for s in sets}
    by_arch = {}
    for r in rows:
        by_arch.setdefault((r["role"], r["archetype"]), []).append(r)
    fa = {t: len(v.get("false_alarms", [])) for t, v in companies.items() if "items" in v}
    heads_n = {t: len(v.get("headline_items", [])) for t, v in companies.items() if "items" in v}
    return {"sets": list(sets), "by_set": by_set,
            "by_archetype": {f"{k[0]}:{k[1]}": summary(v) for k, v in sorted(by_arch.items())},
            "by_tag": {tag: summary([r for r in rows if r["tag"] == tag and r["role"] != "holdout"])
                       for tag in ("financial", "kpi", "qualitative")},
            "false_alarms": {"n": sum(fa.values()), "headline_items": sum(heads_n.values()),
                             "reviewed": sum(v.get("reviewed", 0) for v in companies.values() if "items" in v),
                             "by_company": fa},
            "companies": companies}


def _pct(r: Dict) -> str:
    return "n/a" if r["rate"] is None else f"{r['rate']:.0%} ({r['n']}/{r['d']})"


def results_markdown(res: Dict, show_details_for=("test", "blowup")) -> str:
    lines = ["# Validation results", "",
             "Generated by `python -m engine validate` from `validation/expected.yaml`, `validation/adjudication.yaml` and",
             "`reports/*/analysis.json`. Matching rules: see `validation/expected.md`.", "", "## Hit rates", "",
             "| Set | All items | Excl. qualitative | Excl. qualitative and missing data | Headline (top lists) | Strengths | Weaknesses |",
             "|---|---|---|---|---|---|---|"]
    for s, v in res["by_set"].items():
        lines.append(f"| {s} | {_pct(v['all'])} | {_pct(v['excl_qualitative'])} | {_pct(v['excl_qualitative_and_missing_data'])} | "
                     f"{_pct(v['headline'])} | {_pct(v['strengths'])} | {_pct(v['weaknesses'])} |")
    lines += ["", "## By archetype", "", "| Set:archetype | All items | Excl. qualitative | Excl. qual. and missing data | Headline |", "|---|---|---|---|---|"]
    for k, v in res["by_archetype"].items():
        if k.split(":")[0] not in show_details_for:
            continue
        lines.append(f"| {k} | {_pct(v['all'])} | {_pct(v['excl_qualitative'])} | {_pct(v['excl_qualitative_and_missing_data'])} | {_pct(v['headline'])} |")
    lines += ["", "## By tag (test and blow-up)", "", "| Tag | Hit rate |", "|---|---|"]
    for tag, v in res["by_tag"].items():
        lines.append(f"| {tag} | {_pct(v['all'])} |")
    fa = res["false_alarms"]
    lines += ["", "## False alarms", "",
              f"{fa['n']} false alarms; {fa['headline_items']} engine headline items, {fa['reviewed']} reviewed in `validation/adjudication.yaml`.", ""]
    lines += ["## Per company", ""]
    for t, c in res["companies"].items():
        if "error" in c:
            lines += [f"### {t}", "", f"Error: {c['error']}", ""]
            continue
        if c["role"] not in show_details_for:
            continue
        m = sum(i["matched"] for i in c["items"])
        lines += [f"### {t} ({c['archetype']}, {c['asof']}): {m}/{len(c['items'])} matched", "",
                  "| Item | Tag | Status | Claim | Engine evidence |", "|---|---|---|---|---|"]
        for i in c["items"]:
            lines.append(f"| {i['id']} | {i['tag']} | {i['status']}{' (headline)' if i['headline'] else ''} | {i['claim']} | {'; '.join(i['evidence'])} |")
        if c["false_alarms"]:
            lines += ["", "False alarms:", ""]
            for f in c["false_alarms"]:
                why = f.get("reason") or "engine scores the opposite of the expected item"
                lines.append(f"- {f['id']} ({f['source']}{', ' + f['cause'] if f.get('cause') else ''}): {why}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
