"""Session 4 (validation) general fixes: rule switches per archetype (not_for), flags that keep a metric off the strengths
list (suppresses), the materiality gate, the growth-aware V03/V04, the B01 debt gate and the reverse-DCF guard."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from engine.flags import evaluate_rules

REPO = Path(__file__).resolve().parent.parent
NAMES = {"wacc": 0.12, "ke": 0.13, "rf": 0.07, "tax_rate": 0.25, "inflation_target": 0.04, "nominal_gdp_growth": 0.089,
         "terminal_growth": 0.06}
IDX = [f"FY{y}" for y in range(20, 27)]


@pytest.fixture(scope="module")
def cfg():
    from engine.config import Config
    from engine.paths import Paths

    return Config.load(Paths.default(REPO))


def _run(cfg, ids, series, tokens, rules=None):
    rules = rules if rules is not None else [r for r in cfg.all_rules() if r["id"] in ids]
    metrics = {k: pd.Series(v if isinstance(v, list) else [v] * len(IDX), index=IDX, dtype=float) for k, v in series.items()}
    annual = pd.DataFrame(index=IDX)
    return {f["id"]: f for f in evaluate_rules(rules, metrics, annual, set(tokens), NAMES)}


def test_not_for_switches_rules_off_by_archetype(cfg):
    s = {"roe": [0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16], "equity_multiplier": [10, 11, 12, 13, 14, 15, 16],
         "pat_margin": [0.10, 0.10, 0.10, 0.10, 0.09, 0.08, 0.07], "altman_z_india": 3.0, "pb_to_justified_pb": 2.0}
    ins = _run(cfg, {"R02"}, s, cfg.tokens("insurance"))
    assert "R02" not in ins                                     # insurer's equity multiplier is policyholder funds
    assert _run(cfg, {"R02"}, s, cfg.tokens("bank"))["R02"]["status"] == "triggered"
    assert "B05" not in _run(cfg, {"B05"}, s, cfg.tokens("telecom"))
    assert _run(cfg, {"B05"}, s, cfg.tokens("fmcg"))["B05"]["status"] == "triggered"
    assert "V03" not in _run(cfg, {"V03"}, s, cfg.tokens("real_estate"))
    for r in cfg.all_rules():                                  # every switch carries a reason and names real tokens
        if r.get("not_for"):
            assert r.get("not_for_reason")
            known = {"ALL", "NF", "FIN", "BL", "BANK", "NBFC", "INS"} | set(cfg.sectors)
            assert set(r["not_for"]) <= known, r["id"]


def test_v03_and_v04_need_the_growth_aware_test_to_agree(cfg):
    base = {"pb_to_justified_pb": 2.0, "ev_ic_to_roic_wacc": 2.0}
    nf = cfg.tokens("fmcg")
    # the price implies less growth than delivered (gap -2pp): P/B above the single-stage value is explained by growth
    out = _run(cfg, {"V03", "V04"}, {**base, "implied_minus_delivered_growth": -0.02}, nf)
    assert out["V03"]["status"] == "clear" and out["V04"]["status"] == "clear"
    out = _run(cfg, {"V03", "V04"}, {**base, "implied_minus_delivered_growth": 0.03}, nf)
    assert out["V03"]["status"] == "triggered" and out["V04"]["status"] == "triggered"
    # no growth-aware test available (e.g. ROIC <= WACC): the steady-state test stands alone (first_of falls back to 1.0)
    out = _run(cfg, {"V03", "V04"}, base, nf)
    assert out["V03"]["status"] == "triggered" and out["V04"]["status"] == "triggered"
    # financials keep the plain test (P/B-implied growth is perpetual; delivered book growth includes equity raises)
    fin = _run(cfg, {"V03"}, {"pb_to_justified_pb": 2.0, "implied_pb_growth_minus_delivered": -0.15}, cfg.tokens("nbfc"))
    assert fin["V03"]["status"] == "triggered"


def test_b01_needs_material_debt(cfg):
    up = [0, 0, 0, -0.1, 0.05, 0.10, 0.20]
    nf = cfg.tokens("fmcg")
    assert _run(cfg, {"B01"}, {"debt_vs_ebitda_growth": up, "net_debt_to_ebitda": 0.3}, nf)["B01"]["status"] == "clear"
    assert _run(cfg, {"B01"}, {"debt_vs_ebitda_growth": up, "net_debt_to_ebitda": 0.5}, nf)["B01"]["status"] == "triggered"


def test_materiality_gate_unscores_hand_computed():
    from engine.scoring import materiality_exclusions

    rules = [{"metric": "debt_vs_ebitda_growth", "gate": "net_debt_to_ebitda", "min": 0.5, "reason": "debt is immaterial"}]
    res = {"debt_vs_ebitda_growth": {"value": 0.2, "rag": "red", "level": 10.0, "composite": 20.0},
           "net_debt_to_ebitda": {"value": 0.3, "rag": "green"}}
    assert materiality_exclusions(res, rules) == ["debt_vs_ebitda_growth"]
    r = res["debt_vs_ebitda_growth"]
    assert r["rag"] is None and r["composite"] is None and r["value"] == 0.2   # value kept, no RAG
    assert "net_debt_to_ebitda 0.30 < 0.5" in r["reason"]
    res2 = {"debt_vs_ebitda_growth": {"value": 0.2, "rag": "red", "level": 10.0, "composite": 20.0},
            "net_debt_to_ebitda": {"value": 0.5, "rag": "amber"}}
    assert materiality_exclusions(res2, rules) == [] and res2["debt_vs_ebitda_growth"]["rag"] == "red"


def test_config_suppresses_and_materiality_name_real_metrics(cfg):
    from engine.registry import REGISTRY

    known = set(REGISTRY) | {m for s in cfg.sectors.values() for m in s.metrics_add}
    for r in cfg.all_rules():
        assert set(r.get("suppresses") or []) <= known, r["id"]
    for g in cfg.sv("materiality", default=[]):
        assert {g["metric"], g["gate"]} <= known and g["reason"]


def test_reverse_dcf_not_meaningful_when_returns_below_wacc(cfg, monkeypatch):
    from engine.metrics import valuation as V

    monkeypatch.setattr(V, "_current_ev", lambda c: 1000.0)
    monkeypatch.setattr(V, "nopat", lambda c: pd.Series({"FY26": 50.0}))
    c = SimpleNamespace(asof="FY26", info={}, cfg=cfg, coc=SimpleNamespace(current={"wacc": 0.12}), point=lambda v: v)
    monkeypatch.setattr(V, "_ronic", lambda c: 0.09)           # 9% <= 12% WACC: growth adds no value
    assert np.isnan(V.implied_growth_reverse_dcf(c)) and "<= WACC" in c.info["implied_growth_reverse_dcf"]
    monkeypatch.setattr(V, "_ronic", lambda c: 0.20)
    g = V.implied_growth_reverse_dcf(c)
    # re-price: F0 = 50 x (1 - 0.06/0.20) = 35 grown at g for 10 years then Gordon at 6% equals the EV of 1000
    assert V.dcf_value(35.0, g, 0.12, 0.06, 10) == pytest.approx(1000.0, rel=1e-6)


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    from synthetic import make_project

    from engine.analysis import PeerSet, analyse
    from engine.config import Config
    from engine.paths import Paths

    root = make_project(tmp_path_factory.mktemp("s4"))
    scfg = Config.load(Paths.default(root))
    return analyse("SYNTHCO", scfg, peers=PeerSet(scfg)), scfg


def test_suppressing_flag_keeps_metric_off_strengths(synth):
    import copy

    from engine.report.findings import build_findings

    rep, scfg = synth
    strengths = rep["findings"]["strengths"]
    target = next(c["id"] for c in strengths if c["kind"] == "metric")
    r2 = copy.deepcopy(rep)
    r2["flags"]["triggered"].append({"id": "ZZ1", "name": "Test doubt", "pillar": "balance_sheet", "severity": "high",
                                     "status": "triggered", "text": "test", "suppresses": [target], "condition": "1 > 0"})
    f2 = build_findings(r2, scfg)
    assert target not in {c["id"] for c in f2["strengths"]}
    held = next(c for c in f2["watch"] if c["id"] == target)
    assert held["suppressed_by"] == "ZZ1" and "not counted as a strength while ZZ1 (Test doubt) stands" in held["text"]
    # a low-severity flag does not suppress
    r3 = copy.deepcopy(rep)
    r3["flags"]["triggered"].append({**r2["flags"]["triggered"][-1], "severity": "low"})
    assert target in {c["id"] for c in build_findings(r3, scfg)["strengths"]}


def test_growth_flag_over_a_merger_window_is_not_evaluable():
    from engine.scoring import merger_window_flags

    rules = [{"id": "G02", "condition": "m('pat_cagr_5y') - m('eps_cagr_5y') > 0.03"},
             {"id": "B02", "condition": "m('net_debt_to_ebitda') > 4"}]
    flags = [{"id": "G02", "status": "triggered", "severity": "medium", "text": "x", "values": {}},
             {"id": "B02", "status": "triggered", "severity": "medium", "text": "y", "values": {}}]
    out = {f["id"]: f for f in merger_window_flags(flags, rules, ["pat_cagr_5y", "eps_cagr_5y"])}
    assert out["G02"]["status"] == "not_evaluable" and "merger" in out["G02"]["missing"] and "text" not in out["G02"]
    assert out["B02"]["status"] == "triggered"
