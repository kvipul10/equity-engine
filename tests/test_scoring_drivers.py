"""Scoring rules (hand-computed) and driver-tree decompositions (exactness, fallbacks, real data)."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from engine.drivers import Tree, decompose, logmean, shapley_product
from engine.registry import REGISTRY, load_all
from engine.scoring import band_score, percentile_score, rag_from, roll_up, score_metric, stability_stats, trend_stats

load_all()
THIRD = 100 / 3


# ---------------------------------------------------------------------------------------------- scoring
def test_band_score_hand_computed():
    hb = {"red": 0.10, "green": 0.20}
    assert band_score(0.10, hb, "higher") == pytest.approx(THIRD)
    assert band_score(0.20, hb, "higher") == pytest.approx(2 * THIRD)
    assert band_score(0.15, hb, "higher") == pytest.approx(50.0)
    assert band_score(0.40, hb, "higher") == 100.0 and band_score(-0.5, hb, "higher") == 0.0
    lb = {"green": 2.0, "red": 4.0}
    assert band_score(4.0, lb, "lower") == pytest.approx(THIRD)
    assert band_score(3.0, lb, "lower") == pytest.approx(50.0)
    tb = {"green_low": 1.0, "green_high": 2.0, "red_low": 0.5, "red_high": 3.0}
    assert band_score(1.5, tb, "target") == 75.0
    assert band_score(0.5, tb, "target") == pytest.approx(THIRD)
    assert band_score(0.75, tb, "target") == pytest.approx(THIRD + (75 - THIRD) * 0.5)


def test_percentile_score_hand_computed():
    peers = [0.10, 0.20, 0.30, 0.40]
    assert percentile_score(0.40, peers, "higher") == pytest.approx(100.0)
    assert percentile_score(0.20, peers, "higher") == pytest.approx(100 / 3)
    assert percentile_score(0.20, peers, "lower") == pytest.approx(200 / 3)


def test_trend_and_stability_hand_computed(project_cfg):
    m = REGISTRY["ebitda_margin"]  # pct, higher is better
    s = pd.Series({"FY22": 0.10, "FY23": 0.11, "FY24": 0.12, "FY25": 0.13, "FY26": 0.14})
    t = trend_stats(s, m, "FY26", project_cfg)
    assert t["slope_per_year"] == pytest.approx(0.01)
    norm = 0.01 / max(0.12, 0.05)
    assert t["normalised_slope"] == pytest.approx(norm)
    assert t["score"] == pytest.approx(50 + 50 * math.tanh(norm / 0.10))
    assert t["label"] == "improving"
    st = stability_stats(s, m, "FY26", project_cfg)
    sd = pd.Series([0.10, 0.11, 0.12, 0.13, 0.14]).std(ddof=1)
    assert st["cv"] == pytest.approx(sd / 0.12)
    assert st["score"] == pytest.approx(100 * math.exp(-(sd / 0.12) / 0.35))
    assert st["label"] == "stable"


def test_composite_and_rag_overrides(project_cfg):
    vars_ = {"wacc": 0.12, "ke": 0.13, "rf": 0.07, "tax_rate": 0.25168, "inflation_target": 0.04, "nominal_gdp_growth": 0.089,
             "terminal_growth": 0.06}
    # level at the red threshold of roic (= wacc) with a falling trend -> red
    falling = pd.Series({"FY22": 0.20, "FY23": 0.18, "FY24": 0.16, "FY25": 0.14, "FY26": 0.12})
    r = score_metric("roic", falling, "FY26", project_cfg, "consumer_manufacturing", "non_financial", vars_)
    assert r["level"]["score"] == pytest.approx(THIRD) and r["level"]["rag"] == "red"
    assert r["trend"]["label"] == "deteriorating" and r["rag"] == "red"
    w = project_cfg.scoring["composite"]["weights"]
    exp = (w["level"] * r["level"]["score"] + w["trend"] * r["trend"]["score"] + w["stability"] * r["stability"]["score"]) / sum(w.values())
    assert r["composite"] == pytest.approx(exp)
    # red level can never be green, even with a strong improving trend and perfect stability
    rising = pd.Series({"FY22": 0.02, "FY23": 0.05, "FY24": 0.08, "FY25": 0.10, "FY26": 0.115})
    r2 = score_metric("roic", rising, "FY26", project_cfg, "consumer_manufacturing", "non_financial", vars_)
    assert r2["level"]["rag"] == "red" and r2["rag"] != "green"
    # neutral metrics are informational
    r3 = score_metric("payout_ratio", rising, "FY26", project_cfg, "consumer_manufacturing", "non_financial", vars_)
    assert r3["rag"] == "n/a" and "neutral" in r3["reason"]


def test_roll_up_weights_and_flag_caps(project_cfg):
    res = {"roic": {"composite": 80.0, "rag": "green"}, "roe": {"composite": 50.0, "rag": "amber"},
           "ebitda_margin": {"composite": 70.0, "rag": "green"}}
    pillars, overall = roll_up(res, "non_financial", project_cfg, [])
    assert pillars["returns"]["score"] == pytest.approx((80 * 3 + 50 * 2) / 5)
    assert pillars["margins"]["score"] == pytest.approx(70.0)
    pw = project_cfg.scoring["pillar_weights"]["non_financial"]
    exp = (pillars["returns"]["score"] * pw["returns"] + 70 * pw["margins"]) / (pw["returns"] + pw["margins"])
    assert overall["score"] == pytest.approx(exp)
    assert overall["coverage"] == pytest.approx((pw["returns"] + pw["margins"]) / sum(pw.values()))
    flags = [{"id": "R01", "pillar": "returns", "severity": "high"}, {"id": "B02", "pillar": "balance_sheet", "severity": "high"}]
    pillars2, overall2 = roll_up(res, "non_financial", project_cfg, flags)
    assert pillars2["returns"]["rag"] == "amber" and pillars2["returns"]["capped_by_flags"] == ["R01"]
    assert overall2["rag"] in ("amber", "red") and overall2["high_flags"] == 2


def test_rag_from():
    assert rag_from(66.7, 66.666, 33.334) == "green"
    assert rag_from(33.3334, 66.666, 33.334) == "red"
    assert rag_from(None, 60, 40) == "n/a"


# ---------------------------------------------------------------------------------------------- drivers
def _tree(links, root="p"):
    return Tree({"id": "t", "root": root, "applies": ["ALL"], "links": links})


def _getter(d):
    return lambda n: pd.Series(d[n]) if n in d else None


def test_product_log_decomposition_is_exact():
    d = {"p": {"A": 6.0, "B": 13.5}, "a": {"A": 2.0, "B": 3.0}, "b": {"A": 3.0, "B": 4.5}}
    r = decompose(_tree({"p": {"type": "product", "children": ["a", "b"]}}), _getter(d), "A", "B")
    c = r["nodes"]
    assert r["root_change"] == pytest.approx(7.5)
    L = logmean(13.5, 6.0)
    assert c["a"]["contribution"] == pytest.approx(L * math.log(1.5))
    assert c["b"]["contribution"] == pytest.approx(L * math.log(1.5))
    assert c["a"]["contribution"] + c["b"]["contribution"] == pytest.approx(7.5)


def test_shapley_fallback_with_negative_values():
    d = {"p": {"A": -2.0, "B": 3.0}, "a": {"A": -1.0, "B": 1.0}, "b": {"A": 2.0, "B": 3.0}}
    r = decompose(_tree({"p": {"type": "product", "children": ["a", "b"]}}), _getter(d), "A", "B")
    assert r["nodes"]["p"]["method"] == "shapley"
    # two-factor Shapley by hand: phi_a = da x (b0+b1)/2 = 2 x 2.5 = 5; phi_b = db x (a0+a1)/2 = 1 x 0 = 0
    assert r["nodes"]["a"]["contribution"] == pytest.approx(5.0)
    assert r["nodes"]["b"]["contribution"] == pytest.approx(0.0)
    assert r["residual"] == pytest.approx(0.0, abs=1e-12)
    assert sum(shapley_product([-1, 2], [1, 3], [1, 1])) == pytest.approx(5.0)


def test_sum_inverse_sum_and_chaining_exact():
    # p = a x t ; t = 1 / (x + y) ; a = 1 - c
    d = {"p": {"A": 0.8 / 2.0, "B": 0.7 / 2.5}, "a": {"A": 0.8, "B": 0.7}, "c": {"A": 0.2, "B": 0.3},
         "t": {"A": 0.5, "B": 0.4}, "x": {"A": 1.5, "B": 1.5}, "y": {"A": 0.5, "B": 1.0}}
    links = {"p": {"type": "product", "children": ["a", "t"]}, "a": {"type": "sum", "const": 1.0, "children": ["-c"]},
             "t": {"type": "inverse_sum", "children": ["x", "y"]}}
    r = decompose(_tree(links), _getter(d), "A", "B")
    assert not r["inexact_nodes"]
    assert r["residual"] == pytest.approx(0.0, abs=1e-12)
    assert r["nodes"]["x"]["contribution"] == pytest.approx(0.0)   # x did not move
    assert r["nodes"]["c"]["contribution"] + r["nodes"]["y"]["contribution"] == pytest.approx(0.7 / 2.5 - 0.4)


def test_weighted_sum_mix_and_rate():
    d = {"p": {"A": 0.5 * 0.1 + 0.5 * 0.2, "B": 0.4 * 0.12 + 0.6 * 0.2}, "w1": {"A": 0.5, "B": 0.4}, "r1": {"A": 0.1, "B": 0.12},
         "w2": {"A": 0.5, "B": 0.6}, "r2": {"A": 0.2, "B": 0.2}}
    r = decompose(_tree({"p": {"type": "weighted_sum", "pairs": [["w1", "r1"], ["w2", "r2"]]}}), _getter(d), "A", "B")
    assert r["residual"] == pytest.approx(0.0, abs=1e-12)
    assert r["nodes"]["r1"]["contribution"] == pytest.approx(0.45 * 0.02)  # mean weight x rate change
    assert r["nodes"]["w1"]["contribution"] == pytest.approx(-0.1 * 0.11)  # weight change x mean rate


@pytest.mark.parametrize("ticker,tree", [("ASIANPAINT", "roe_dupont"), ("TCS", "roic_tree"), ("HDFCBANK", "fin_roe"),
                                         ("MARUTI", "eps_tree")])
def test_real_trees_are_exact(real_cfg, ticker, tree):
    from engine.analysis import analyse

    rep = analyse(ticker, real_cfg)
    for w, res in rep["drivers"][tree]["windows"].items():
        if res["status"] != "ok":
            continue
        assert not res["inexact_nodes"], f"{ticker} {tree} {w}: {res['inexact_nodes']}"
        assert abs(res["residual"]) < 1e-9 * max(1.0, abs(res["root_change"])) + 1e-12
        assert res["top_drivers"]
