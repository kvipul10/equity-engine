"""Red-flag rules + safe expression language, configuration integrity, and the CLI end to end."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from engine.expr import ExprError, Missing, compile_expr, eval_number, evaluate
from engine.flags import FUNCS, evaluate_rules, validate_rules

REPO = Path(__file__).resolve().parent.parent
NAMES = {"wacc": 0.12, "ke": 0.13, "rf": 0.07, "tax_rate": 0.25, "inflation_target": 0.04, "nominal_gdp_growth": 0.089,
         "terminal_growth": 0.06}


# ---------------------------------------------------------------------------------------------- expressions
@pytest.mark.parametrize("bad", ["__import__('os')", "a.b", "x[0]", "lambda: 1", "[i for i in x]", "().__class__",
                                 "open('f')", "m('roe').real", "_secret + 1"])
def test_expression_language_rejects_unsafe_code(bad):
    with pytest.raises(ExprError):
        compile_expr(bad, FUNCS)


def test_expression_language_evaluates():
    t = compile_expr("max(a, 2) * 3 > 5 and not b", None)
    assert evaluate(t, {"a": 1, "b": False}, {"max": max}) is True
    assert eval_number("wacc + 0.05", NAMES) == pytest.approx(0.17)
    assert eval_number("wacc / (1 - tax_rate)", NAMES) == pytest.approx(0.16)
    with pytest.raises(Missing):
        evaluate(compile_expr("a > 1", None), {"a": float("nan")}, {})


# ---------------------------------------------------------------------------------------------- rules
def test_at_least_25_rules_all_valid(real_cfg):
    rules = real_cfg.flags
    assert len(rules) >= 25
    validate_rules(rules)
    pillars = {r["pillar"] for r in rules}
    assert pillars == {"growth", "margins", "capital_efficiency", "returns", "cash_quality", "balance_sheet",
                       "capital_allocation", "valuation"}


def _book(series: dict, fields: dict):
    idx = [f"FY{y}" for y in range(20, 27)]
    metrics = {k: pd.Series(v, index=idx, dtype=float) for k, v in series.items()}
    annual = pd.DataFrame({k: v for k, v in fields.items()}, index=idx)
    return metrics, annual


def _run(real_cfg, ids, metrics, annual, tokens=("ALL", "NF")):
    rules = [r for r in real_cfg.flags if r["id"] in ids]
    return {f["id"]: f for f in evaluate_rules(rules, metrics, annual, set(tokens), NAMES)}


def test_rules_from_the_brief_trigger(real_cfg):
    n = 7
    metrics, annual = _book(
        {"dso": [40, 41, 42, 44, 50, 58, 66],                       # up 3 years running
         "cwip_to_net_block": [0.1, 0.1, 0.1, 0.2, 0.25, 0.35, 0.40],  # > 30% for 2 years
         "other_income_to_pbt": [0.1] * 6 + [0.30],                 # > 25% of PBT
         "debt_vs_ebitda_growth": [0, 0, 0, -0.1, 0.05, 0.10, 0.20],   # debt outgrew EBITDA 3 years
         "net_debt_to_ebitda": [1.0] * 7,                           # material debt (B01 gate >= 0.5x)
         "roe": [0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.14],
         "equity_multiplier": [2.0, 2.0, 2.0, 2.0, 2.4, 2.8, 3.2],
         "pat_margin": [0.10, 0.10, 0.10, 0.10, 0.09, 0.085, 0.08],
         "share_count_change": [0.0] * 6 + [0.05],
         "promoter_pledge": [0.0, 0.0, 0.0, 0.0, 0.05, 0.10, 0.20]},
        {"cfo": [50] * n, "pat_core": [100] * n, "other_income": [30] * n, "exceptional_est": [0] * n})
    out = _run(real_cfg, {"Q01", "C01", "C03", "M02", "B01", "R02", "A01", "A02"}, metrics, annual)
    for rid in ("Q01", "C01", "C03", "M02", "B01", "R02", "A01", "A02"):
        assert out[rid]["status"] == "triggered", (rid, out[rid])
    assert "50.0%" in out["Q01"]["text"] and "60%" in out["Q01"]["text"]


def test_rules_clear_and_not_evaluable(real_cfg):
    metrics, annual = _book({"dso": [60, 55, 50, 45, 40, 35, 30]}, {"cfo": [100] * 7, "pat_core": [100] * 7})
    out = _run(real_cfg, {"C01", "Q01", "A02"}, metrics, annual)
    assert out["C01"]["status"] == "clear" and out["Q01"]["status"] == "clear"
    assert out["A02"]["status"] == "not_evaluable" and "promoter_pledge" in out["A02"]["missing"]


def test_rule_applicability(real_cfg):
    metrics, annual = _book({"growth_minus_icg": [0.3] * 7}, {"total_assets": [1, 2, 3, 4, 5, 6, 7]})
    assert "A06" not in _run(real_cfg, {"A06"}, metrics, annual, tokens=("ALL", "NF"))
    assert _run(real_cfg, {"A06"}, metrics, annual, tokens=("ALL", "FIN", "BL", "BANK"))["A06"]["status"] == "triggered"


# ---------------------------------------------------------------------------------------------- config integrity
def test_external_benchmarks_need_source(tmp_path):
    import shutil

    from engine.config import Config, ConfigError
    from engine.paths import Paths

    shutil.copytree(REPO / "config", tmp_path / "config")
    b = yaml.safe_load((tmp_path / "config" / "bands.yaml").read_text())
    b["generic"]["interest_cover"].pop("source_url")
    (tmp_path / "config" / "bands.yaml").write_text(yaml.safe_dump(b))
    with pytest.raises(ConfigError, match="source_url"):
        Config.load(Paths.default(tmp_path))


def test_market_inputs_sourced_and_consistent_with_damodaran(real_cfg):
    import openpyxl

    for k in ("risk_free", "equity_risk_premium"):
        assert real_cfg.market[k]["source_url"].startswith("http") and real_cfg.market[k]["as_of"]
    wb = openpyxl.load_workbook(REPO / "data" / "external" / "damodaran" / "ctrypremJuly26.xlsx", read_only=True, data_only=True)
    for row in wb["ERPs by country"].iter_rows(values_only=True):
        if row and row[0] == "India":
            assert real_cfg.mv("equity_risk_premium") == pytest.approx(row[4], abs=1e-4)
            break
    else:
        pytest.fail("India not found in Damodaran ERP file")


def test_every_universe_archetype_is_mapped(real_cfg):
    for t, row in real_cfg.universe.items():
        a = row["archetype"]
        assert a in real_cfg.sectors, a
        assert a in real_cfg.sector["betas"] and real_cfg.sector["betas"][a]["levered"], a
        for m, band in real_cfg.sector["bands"].get(a, {}).items():
            assert band["source_url"].startswith("https://pages.stern.nyu.edu/") and band["as_of"]


def test_sector_benchmarks_rebuild_reproducibly(real_cfg):
    from engine.benchmarks import build

    fresh = build(REPO)
    assert fresh["bands"] == real_cfg.sector["bands"]
    assert fresh["betas"] == real_cfg.sector["betas"]


def test_registry_shape():
    from engine.registry import PILLARS, load_all

    reg = load_all()
    assert len(PILLARS) == 8
    for m in reg.values():
        assert m.pillar in PILLARS or (m.pillar == "root" and m.role == "root")
        assert m.equation and m.meaning and m.unit and m.direction


# ---------------------------------------------------------------------------------------------- CLI
def _cli(root, *args):
    return subprocess.run([sys.executable, "-m", "engine", "--root", str(root), *args], cwd=REPO, capture_output=True, text=True)


def test_cli_analyse_writes_reports(project_root):
    p = _cli(project_root, "analyse", "SYNTHCO")
    assert p.returncode == 0, p.stderr
    out = project_root / "reports" / "SYNTHCO"
    rep = json.loads((out / "analysis.json").read_text())
    for k in ("company", "asof", "cost_of_capital", "root", "overall", "pillars", "dupont", "drivers", "flags", "metrics", "data_notes"):
        assert k in rep
    assert len(rep["pillars"]) == 8
    df = pd.read_csv(out / "metrics.csv")
    assert len(df) >= 100 and {"metric_id", "pillar", "FY26", "value", "rag"} <= set(df.columns)
    assert (project_root / "data" / "processed" / "SYNTHCO" / "notes.md").exists()
    assert "Overall:" in p.stdout


def test_cli_asof_goes_to_subfolder(project_root):
    p = _cli(project_root, "analyse", "SYNTHCO", "--asof", "FY21", "--quiet")
    assert p.returncode == 0, p.stderr
    rep = json.loads((project_root / "reports" / "SYNTHCO" / "asof_FY21" / "analysis.json").read_text())
    assert rep["asof"]["fy"] == "FY21"


def test_cli_analyse_all_and_listings(project_root):
    p = _cli(project_root, "analyse-all")
    assert p.returncode == 0, p.stderr + p.stdout
    summ = pd.read_csv(project_root / "reports" / "universe_summary.csv")
    assert set(summ["ticker"]) == {"SYNTHCO", "SYNTHBANK", "SYNTHNBFC", "SYNTHINS"} and (summ["status"] == "ok").all()
    assert _cli(project_root, "metrics").returncode == 0
    assert _cli(project_root, "rules").returncode == 0
    bad = _cli(project_root, "analyse", "NOPE")
    assert bad.returncode == 1 and "No Screener export" in bad.stderr
