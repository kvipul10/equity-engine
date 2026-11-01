"""Validation matching rules (hand-built reports) and the integrity of the pre-registered expectations."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.validation import assess_item, check_expected, evaluate, expected_markdown, load_expected

REPO = Path(__file__).resolve().parent.parent


def _rep(metrics, fired=(), not_eval=(), strengths=(), weaknesses=(), asof="FY26"):
    return {"asof": {"fy": asof},
            "metrics": {k: {"value": v[0], "value_text": str(v[0]), "rag": v[1], "trend": {"label": v[2]} if len(v) > 2 else {}}
                        for k, v in metrics.items()},
            "flags": {"triggered": [{"id": f, "severity": "medium", "name": f} for f in fired],
                      "not_evaluable": [{"id": f, "name": f} for f in not_eval]},
            "findings": {"strengths": [{"id": i, "text": i} for i in strengths],
                         "weaknesses": [{"id": i, "text": i} for i in weaknesses], "watch": [], "bull": [], "bear": []}}


def _item(metrics=(), flags=(), tag="financial"):
    return {"id": "X-1", "claim": "c", "tag": tag, "signals": {"metrics": list(metrics), "flags": list(flags)}}


def test_strength_rules():
    rep = _rep({"a": (1, "green"), "b": (1, "red"), "c": (None, None)}, strengths=["a"])
    r = assess_item(_item(["a", "b"]), "strengths", rep)
    assert r["matched"] and r["headline"] and r["hits"] == ["a"] and not r["contradicted"] and r["status"] == "match"
    r = assess_item(_item(["b"]), "strengths", rep)
    assert not r["matched"] and r["contradicted"] and r["status"] == "contradicted"
    r = assess_item(_item(["c"]), "strengths", rep)
    assert r["blocked"] and r["status"] == "miss (missing data)"


def test_weakness_rules():
    rep = _rep({"x": (1, "amber", "deteriorating"), "y": (1, "amber", "stable"), "g": (1, "green"), "n": (None, None)},
               fired=["F1"], not_eval=["F2"], strengths=["g"], weaknesses=["F1"])
    assert assess_item(_item(["x"]), "weaknesses", rep)["matched"]             # amber and deteriorating
    r = assess_item(_item(["y"]), "weaknesses", rep)
    assert not r["matched"] and r["status"] == "miss"                          # amber but stable
    r = assess_item(_item(flags=["F1"]), "weaknesses", rep)
    assert r["matched"] and r["headline"]                                      # flag fired and in the weaknesses list
    r = assess_item(_item(["n"], ["F2"]), "weaknesses", rep)
    assert r["blocked"] and r["status"] == "miss (missing data)"               # nothing computable
    r = assess_item(_item(["g"]), "weaknesses", rep)
    assert r["contradicted"] and r["status"] == "contradicted"                 # headlined as a strength
    r = assess_item(_item([], [], tag="qualitative"), "weaknesses", rep)
    assert r["status"] == "miss (qualitative)" and not r["blocked"]


def test_evaluate_rates_hand_computed(tmp_path):
    exp = {"companies": {
        "AAA": {"archetype": "fmcg", "role": "test", "asof": "FY26",
                "strengths": [{**_item(["a"]), "id": "AAA-S1"}, {**_item(["b"]), "id": "AAA-S2"}],
                "weaknesses": [{**_item(flags=["F1"]), "id": "AAA-W1"}, {**_item([], [], "qualitative"), "id": "AAA-W2"}]}}}
    d = tmp_path / "AAA"
    d.mkdir()
    (d / "analysis.json").write_text(json.dumps(_rep({"a": (1, "green"), "b": (1, "red")}, fired=["F1"], weaknesses=["F1"])))
    res = evaluate(exp, tmp_path, {"AAA": {"weaknesses:F1": {"verdict": "ok"}}})
    s = res["by_set"]["test"]
    # matched: S1 (green), W1 (flag); S2 is contradicted (red); W2 qualitative
    assert (s["all"]["n"], s["all"]["d"]) == (2, 4)
    assert (s["excl_qualitative"]["n"], s["excl_qualitative"]["d"]) == (2, 3)
    assert (s["headline"]["n"], s["headline"]["d"]) == (1, 4)                  # only W1 is in a top list
    assert res["false_alarms"]["n"] == 1 and res["false_alarms"]["reviewed"] == 1


def test_expected_file_is_valid_and_markdown_in_sync(real_cfg):
    exp = load_expected(REPO / "validation" / "expected.yaml")
    assert check_expected(real_cfg, exp) == []
    assert (REPO / "validation" / "expected.md").read_text() == expected_markdown(exp)
    roles = [c.get("role") for c in exp["companies"].values()]
    assert roles.count("test") == 16 and roles.count("blowup") == 1 and sum(bool(c.get("holdout")) for c in exp["companies"].values()) == 4
    for t, c in exp["companies"].items():
        if c.get("role") == "test":
            assert len(c["strengths"]) == 3 and len(c["weaknesses"]) == 3, t
