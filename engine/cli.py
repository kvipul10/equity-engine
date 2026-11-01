"""Command line interface.

  python -m engine ingest [TICKER ...] [--all]
  python -m engine analyse TICKER [--asof FY18|latest] [--beta 1.1] [--archetype fmcg] [--quiet]
  python -m engine analyse-all [--asof FYxx]
  python -m engine metrics [--markdown]
  python -m engine rules [--markdown]
  python -m engine kpi-templates [--years FY22-FY26]
  python -m engine build-benchmarks
Global option: --root PATH (project root; default = repository root or $EQUITY_ENGINE_ROOT).
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path
from typing import List, Optional

import pandas as pd

from .config import Config, ConfigError
from .paths import Paths


def _cfg(args) -> Config:
    return Config.load(Paths.default(args.root))


def cmd_ingest(args) -> int:
    from .standardise import load_standardised, write_processed

    cfg = _cfg(args)
    tickers = args.tickers or []
    if args.all or not tickers:
        tickers = sorted(p.stem for p in cfg.paths.raw_dir.glob("*.xlsx") if not p.name.startswith("~$"))
    for t in tickers:
        std = load_standardised(t, cfg)
        out = cfg.paths.processed_dir / t
        write_processed(std, out)
        print(f"{t}: {std.meta['first_fy']}-{std.meta['last_fy']} ({std.meta['n_years']}y), {len(std.notes)} notes -> {out}")
    return 0


def _analyse_one(cfg: Config, ticker: str, asof: Optional[str], beta: Optional[float], archetype: Optional[str], peers=None,
                 quiet: bool = False, fy_end: bool = False):
    from .analysis import analyse
    from .report import console_summary, out_dir_for, write_outputs
    from .standardise import load_standardised, write_processed

    std = load_standardised(ticker, cfg, archetype=archetype)
    write_processed(std, cfg.paths.processed_dir / ticker)
    rep = analyse(ticker, cfg, asof=asof, beta=beta, archetype=archetype, peers=peers, fy_end=fy_end)
    out = out_dir_for(cfg.paths, ticker, rep)
    files = write_outputs(rep, out, cfg)
    if not quiet:
        print(console_summary(rep))
        print("Wrote " + ", ".join(str(files[k]) for k in ("analysis", "metrics", "html", "xlsx") if k in files))
    return rep, files


def cmd_analyse(args) -> int:
    cfg = _cfg(args)
    asof = args.asof if args.asof is not None else cfg.universe_asof(args.ticker)
    _analyse_one(cfg, args.ticker, asof, args.beta, args.archetype, quiet=args.quiet, fy_end=args.fy_end)
    return 0


def cmd_analyse_all(args) -> int:
    from .analysis import PeerSet

    cfg = _cfg(args)
    if not cfg.universe:
        print("data/universe.csv is empty or missing", file=sys.stderr)
        return 1
    peers = PeerSet(cfg, fy_end=args.fy_end)
    rows = []
    for t, row in cfg.universe.items():
        asof = args.asof if args.asof is not None else row.get("asof")
        try:
            rep, files = _analyse_one(cfg, t, asof, None, None, peers=peers, quiet=True, fy_end=args.fy_end)
        except Exception as e:  # keep going; report the failure
            print(f"{t}: FAILED - {type(e).__name__}: {e}", file=sys.stderr)
            rows.append({"ticker": t, "archetype": row.get("archetype"), "status": f"failed: {e}"})
            continue
        o = rep["overall"]
        r = {"ticker": t, "archetype": row.get("archetype"), "role": row.get("role"), "asof": rep["asof"]["fy"],
             "mode": rep["asof"]["mode"], "overall_score": o["score"], "overall_rag": o["rag"], "coverage": o["coverage"],
             "root_verdict": rep["root"]["verdict"], "economic_profit_cr": rep["root"]["economic_profit"],
             "flags_high": rep["flags"]["counts"]["high"], "flags_medium": rep["flags"]["counts"]["medium"],
             "flags_low": rep["flags"]["counts"]["low"], "status": "ok"}
        for p, pv in rep["pillars"].items():
            r[f"{p}_score"] = pv["score"]
            r[f"{p}_rag"] = pv["rag"]
        rows.append(r)
        sc = f"{o['score']:.0f}" if o["score"] is not None else "--"
        print(f"{t:<12} {rep['asof']['fy']:<5} {(o['rag'] or 'n/a').upper():<6} {sc:>3}  {rep['root']['verdict']:<15} "
              f"flags H/M/L {rep['flags']['counts']['high']}/{rep['flags']['counts']['medium']}/{rep['flags']['counts']['low']}  -> {files['analysis'].parent}")
    out = cfg.paths.reports_dir / ("universe_summary_fy_end.csv" if args.fy_end else "universe_summary.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False, float_format="%.4f")
    print(f"Wrote {out}")
    return 0 if all(r.get("status") == "ok" for r in rows) else 2


def cmd_compare(args) -> int:
    from .analysis import PeerSet, analyse
    from .report.html import render_compare

    tickers = [t.upper() for t in args.tickers]
    if not 2 <= len(tickers) <= 5 or len(set(tickers)) != len(tickers):
        print("compare takes 2 to 5 distinct tickers", file=sys.stderr)
        return 1
    cfg = _cfg(args)
    peers = PeerSet(cfg, fy_end=args.fy_end)
    reps = []
    for t in tickers:
        asof = args.asof if args.asof is not None else cfg.universe_asof(t)
        try:
            reps.append(analyse(t, cfg, asof=asof, peers=peers, fy_end=args.fy_end))
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            return 1
    out = Path(args.out) if args.out else cfg.paths.reports_dir / "compare.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_compare(reps), encoding="utf-8")
    for r in reps:
        sc = f"{r['overall']['score']:.0f}" if r["overall"]["score"] is not None else "--"
        print(f"{r['company']['ticker']:<12} {r['asof']['fy']:<5} overall {sc:>3}  " +
              " ".join(f"P{i + 1} {('%.0f' % v['score']) if v['score'] is not None else '--'}" for i, v in enumerate(r["pillars"].values())))
    print(f"Wrote {out}")
    return 0


def cmd_validate(args) -> int:
    import json

    import yaml

    from .validation import check_expected, evaluate, load_expected, results_markdown

    cfg = _cfg(args)
    vdir = cfg.paths.root / "validation"
    exp = load_expected(vdir / "expected.yaml")
    problems = check_expected(cfg, exp)
    if problems:
        print("expected.yaml problems:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    adj_path = vdir / "adjudication.yaml"
    adj = (yaml.safe_load(adj_path.read_text()) or {}) if adj_path.exists() else {}
    sets = ("test", "blowup", "holdout") if args.include_holdout else ("test", "blowup")
    res = evaluate(exp, cfg.paths.reports_dir, adj, sets=sets)
    show = ("test", "blowup", "holdout") if args.holdout_details else ("test", "blowup")
    (vdir / "results.md").write_text(results_markdown(res, show_details_for=show))
    (vdir / "results.json").write_text(json.dumps({k: v for k, v in res.items() if k != "companies"} |
                                                  {"companies": {t: c for t, c in res["companies"].items()
                                                                 if c.get("role") in show or "error" in c}},
                                                  indent=1, default=str))
    for s, v in res["by_set"].items():
        a, h = v["all"], v["headline"]
        print(f"{s:<8} hit rate {a['n']}/{a['d']} = {(a['rate'] or 0):.0%}  "
              f"excl. qualitative {(v['excl_qualitative']['rate'] or 0):.0%}  "
              f"excl. qual+missing {(v['excl_qualitative_and_missing_data']['rate'] or 0):.0%}  headline {(h['rate'] or 0):.0%}")
    fa = res["false_alarms"]
    print(f"false alarms {fa['n']} (headline items {fa['headline_items']}, reviewed {fa['reviewed']})")
    print(f"Wrote {vdir / 'results.md'}")
    return 0


def cmd_metrics(args) -> int:
    from .registry import REGISTRY, load_all, to_markdown

    load_all()
    _cfg(args)  # registers sector metrics from config/sectors/*.yaml
    reg = REGISTRY
    if args.markdown:
        cfg_paths = Paths.default(args.root)
        out = cfg_paths.root / "docs" / "metrics.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(to_markdown())
        print(f"Wrote {out} ({len(reg)} metrics)")
        return 0
    for m in reg.values():
        print(f"{m.id:<34} {m.pillar:<20} {m.unit:<7} {m.direction:<8} {','.join(m.applies)[:24]:<24} {m.role:<9} {m.equation[:70]}")
    print(f"{len(reg)} metrics")
    return 0


def cmd_rules(args) -> int:
    from .flags import validate_rules

    cfg = _cfg(args)
    rules = cfg.all_rules()
    validate_rules(rules)
    if args.markdown:
        lines = ["# Red-flag rules", "", "Generated from `config/flags.yaml` (generic) and `config/sectors/*.yaml` (sector rules) by "
                 "`python -m engine rules --markdown`.", "",
                 "| id | pillar | severity | applies | origin | name | condition |", "|---|---|---|---|---|---|---|"]
        for r in rules:
            cond = r["condition"].replace("|", "\\|")
            lines.append(f"| {r['id']} | {r['pillar']} | {r['severity']} | {', '.join(r['applies'])} | "
                         f"{r.get('_origin', 'config/flags.yaml')} | {r['name']} | `{cond}` |")
        out = cfg.paths.root / "docs" / "flags.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n")
        print(f"Wrote {out} ({len(rules)} rules)")
        return 0
    for r in rules:
        print(f"{r['id']:<5} {r['pillar']:<20} {r['severity']:<7} {','.join(r['applies'])[:22]:<22} {r['name']}")
    print(f"{len(rules)} rules ({len(cfg.flags)} generic, {len(rules) - len(cfg.flags)} sector)")
    return 0


def cmd_kpi_templates(args) -> int:
    from .kpi_templates import write_templates

    cfg = _cfg(args)
    paths = write_templates(cfg, args.years)
    print(f"Wrote {len(paths)} templates to {paths[0].parent if paths else '-'}")
    return 0


def cmd_kpi_coverage(args) -> int:
    from .kpi_templates import write_coverage

    p = write_coverage(_cfg(args))
    print(f"Wrote {p}")
    return 0


def cmd_build_benchmarks(args) -> int:
    from .benchmarks import write

    p = write(Paths.default(args.root).root)
    print(f"Wrote {p}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m engine", description="Equity diagnostic engine (Screener.in exports, offline).")
    ap.add_argument("--root", help="project root (default: repository root or $EQUITY_ENGINE_ROOT)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest", help="parse + standardise raw exports into data/processed/<TICKER>/")
    p.add_argument("tickers", nargs="*")
    p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("analyse", help="analyse one company -> reports/<TICKER>/analysis.json + metrics.csv")
    p.add_argument("ticker")
    p.add_argument("--asof", help="fiscal year, e.g. FY18 (default: universe.csv asof; 'latest' = newest data)")
    p.add_argument("--beta", type=float, help="override the levered beta")
    p.add_argument("--archetype", help="override the archetype from universe.csv")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--fy-end", action="store_true", help="truncate at the as-of fiscal year-end even when it is the newest year (drop later quarters, FY-end price)")
    p.set_defaults(fn=cmd_analyse)
    p = sub.add_parser("analyse-all", help="analyse every company in data/universe.csv")
    p.add_argument("--asof", help="override every row's asof")
    p.add_argument("--fy-end", action="store_true", help="truncate at the as-of fiscal year-end even when it is the newest year (drop later quarters, FY-end price)")
    p.set_defaults(fn=cmd_analyse_all)
    p = sub.add_parser("compare", help="reports/compare.html: side-by-side pillar scores for 2-5 tickers")
    p.add_argument("tickers", nargs="+")
    p.add_argument("--asof", help="common fiscal year for all tickers (default: each ticker's universe as-of)")
    p.add_argument("--out", help="output path (default reports/compare.html)")
    p.add_argument("--fy-end", action="store_true", help="truncate at the as-of fiscal year-end even when it is the newest year (drop later quarters, FY-end price)")
    p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("validate", help="compare reports with validation/expected.yaml -> validation/results.md")
    p.add_argument("--include-holdout", action="store_true", help="also score the holdout peers (aggregates only)")
    p.add_argument("--holdout-details", action="store_true", help="show per-item holdout results (final scoring only)")
    p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("metrics", help="list the metric registry")
    p.add_argument("--markdown", action="store_true", help="write docs/metrics.md")
    p.set_defaults(fn=cmd_metrics)
    p = sub.add_parser("rules", help="list / validate red-flag rules")
    p.add_argument("--markdown", action="store_true", help="write docs/flags.md")
    p.set_defaults(fn=cmd_rules)
    p = sub.add_parser("kpi-templates", help="write data/manual/templates/<archetype>_kpis.csv from config/sectors/*.yaml")
    p.add_argument("--years", default="FY22-FY26", help="fiscal-year range, e.g. FY22-FY26")
    p.set_defaults(fn=cmd_kpi_templates)
    p = sub.add_parser("kpi-coverage", help="write data/manual/COVERAGE.md (found / blank per company x KPI x year)")
    p.set_defaults(fn=cmd_kpi_coverage)
    p = sub.add_parser("build-benchmarks", help="rebuild config/sector_benchmarks.yaml from data/external/damodaran/*.xls")
    p.set_defaults(fn=cmd_build_benchmarks)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    args = build_parser().parse_args(argv)
    try:
        return int(args.fn(args) or 0)
    except (ConfigError, FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
