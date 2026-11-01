"""Report building blocks with hand-computed expected values: number formats, SVG geometry, LaTeX conversion,
severity x confidence ranking, driver chains and the KPI dependency map."""
from __future__ import annotations

import pytest

from engine.report import charts
from engine.report import formats as F
from engine.report.findings import (_flag_item, _metric_item, chain_for_node, classify, family_key, kpi_dependencies,
                                    report_cfg, select)
from engine.report.latex import to_latex


# ---------------------------------------------------------------------------------------------- formats
def test_formats():
    assert F.delta(-0.041, "pct") == "−4.1 pts"
    assert F.delta(0.041, "pct") == "+4.1 pts"
    assert F.delta(-0.00004, "pct") == "0.0 pts"            # rounds to zero: no sign
    assert F.delta(25 / 365, "days_of_sales") == "+25 days"
    assert F.value(60 / 365, "days_of_sales") == "60 days"
    assert F.value(0.529612, "pct") == "53.0%"
    assert F.value(-1.5, "x") == "−1.50x"
    assert F.ordinal(0.1) == "10th" and F.ordinal(0.22) == "22nd" and F.ordinal(0.11) == "11th" and F.ordinal(0.03) == "3rd"
    assert F.pct(0.7) == "70%" and F.pct(None) == "n/a"


# ---------------------------------------------------------------------------------------------- SVG geometry
def test_sparkline_geometry():
    # n = 4, x = i * 100 / 3; lo = 1, hi = 3, y = (3 - v) / 2 * 20
    pts = charts.sparkline_geometry([1, 3, None, 2], w=100, h=20, pad=0)
    assert pts[0] == pytest.approx((0, 20)) and pts[1] == pytest.approx((100 / 3, 0))
    assert pts[2] is None and pts[3] == pytest.approx((100, 10))
    flat = charts.sparkline_geometry([5, 5], w=100, h=20, pad=0)
    assert flat == [pytest.approx((0, 10)), pytest.approx((100, 10))]
    svg = charts.sparkline([1, 3, None, 2], ["FY23", "FY24", "FY25", "FY26"])
    assert svg.startswith("<svg") and svg.count("<polyline") == 1 and "<title>FY23-FY26</title>" in svg


def test_band_geometry():
    # values 0.10..0.20, widened by 15% of 0.10 -> [0.085, 0.215]
    g = charts.band_geometry(0.15, 0.10, 0.20, w=100)
    assert g["lo"] == pytest.approx(0.085) and g["hi"] == pytest.approx(0.215)
    assert g["x_red"] == pytest.approx(0.015 / 0.13 * 100) and g["x_green"] == pytest.approx(0.115 / 0.13 * 100)
    assert g["x_value"] == pytest.approx(50.0)


def test_waterfall_geometry():
    # running totals 0.20 -> 0.25 -> 0.15; scale [0, 0.25] -> [0, 100]
    g = charts.waterfall_geometry(0.20, [("a", 0.05), ("b", -0.10)], w=100)
    rows = [(r["kind"], round(r["x0"], 6), round(r["x1"], 6)) for r in g["rows"]]
    assert rows == [("start", 0, 80), ("pos", 80, 100), ("neg", 60, 100), ("end", 0, 60)]
    assert g["end"] == pytest.approx(0.15) and g["x_zero"] == 0


def test_bars_geometry():
    # scale [-0.02, 0.06] -> [0, 80]: zero at 20
    g = charts.bars_geometry([-0.02, 0.06], w=80)
    assert g["x_zero"] == pytest.approx(20)
    assert g["bars"][0] == pytest.approx((0, 20)) and g["bars"][1] == pytest.approx((20, 80))


# ---------------------------------------------------------------------------------------------- LaTeX
@pytest.mark.parametrize("eq, tex", [
    ("core PAT / average equity", r"\dfrac{\text{core PAT}}{\text{average equity}}"),
    ("(Revenue_t / Revenue_t-3)^(1/3) - 1; n/m if either value <= 0",
     r"{\left(\dfrac{\text{Revenue}_{t}}{\text{Revenue}_{t-3}}\right)}^{\tfrac{1}{3}} - 1"),
    ("ROE - Ke, Ke = rf + beta x ERP", r"\text{ROE} - \text{Ke},\quad \text{Ke} = \text{rf} + \text{beta} \times \text{ERP}"),
    ("Inventory / COGS x 365", r"\dfrac{\text{Inventory}}{\text{COGS}} \times 365"),
    ("sum5(|estimated exceptional|) / sum5(|reported PBT|)",
     r"\dfrac{\Sigma_{5}\left(\left\lvert \text{estimated exceptional}\right\rvert\right)}{\Sigma_{5}\left(\left\lvert \text{reported PBT}\right\rvert\right)}"),
    ("Market cap / core PAT (current: TTM PAT when available)",
     r"\dfrac{\text{Market cap}}{\text{core PAT}}\,\;\text{(current: TTM PAT when available)}"),
])
def test_latex_examples(eq, tex):
    assert to_latex(eq) == tex


def test_latex_falls_back_and_covers_registry(real_cfg):
    from engine.registry import REGISTRY

    assert to_latex("solve g: EV = sum_{t=1..10} F0(1+g)^t") is None
    eqs = {m.equation for m in REGISTRY.values()}
    out = {e: to_latex(e) for e in eqs}
    for e, t in out.items():
        if t is not None:
            assert t.count("{") - t.count(r"\{") == t.count("}") - t.count(r"\}"), e
    assert sum(t is not None for t in out.values()) >= 0.95 * len(eqs)


# ---------------------------------------------------------------------------------------------- ranking
def _m(pillar, rag, composite, n_years, basis="band", source="external", role="scored", trend=None, value=0.1, unit="pct"):
    series = {f"FY{20 + i}": 0.1 for i in range(n_years)}
    return {"name": pillar + " metric", "pillar": pillar, "role": role, "unit": unit, "direction": "higher", "rag": rag,
            "composite": composite, "series": series, "value": value,
            "level": {"basis": basis} if basis else None, "band": {"red": 0.05, "green": 0.15, "source_type": source},
            "trend": trend or {"label": "stable", "score": 50, "slope_per_year": 0.0, "window": "FY22-FY26"}}


@pytest.fixture()
def toy():
    rep = {"pillars": {"growth": {"weight": 10}, "returns": {"weight": 20}}, "drivers": {}, "metrics": {
        "roe": _m("returns", "green", 90, 5),                                   # sev 0.8 x 1 x 1; conf 1 x 1 -> 0.8
        "revenue_cagr_3y": _m("growth", "green", 80, 3, source="indicative"),   # sev 0.6 x 0.5; conf 0.6 x 0.6 -> 0.108
        "roa": _m("returns", "red", 20, 10, source="derived", role="component"),  # sev 0.6 x 1 x 0.67; conf 0.9 -> 0.3618
        "roce": _m("returns", "red", 10, 5, trend={"label": "improving", "score": 70, "slope_per_year": 0.01, "window": "FY22-FY26"}),
    }}
    return rep, report_cfg(None)


def test_severity_confidence_hand_computed(toy):
    rep, rc = toy
    it = {mid: _metric_item(mid, m, rep, rc, set(), {}, watch=classify(m, rc) == "watch") for mid, m in rep["metrics"].items()}
    assert (it["roe"]["severity"], it["roe"]["confidence"], it["roe"]["score"]) == pytest.approx((0.8, 1.0, 0.8))
    assert (it["revenue_cagr_3y"]["severity"], it["revenue_cagr_3y"]["confidence"]) == pytest.approx((0.3, 0.36))
    assert it["revenue_cagr_3y"]["score"] == pytest.approx(0.108)
    assert (it["roa"]["severity"], it["roa"]["confidence"]) == pytest.approx((0.402, 0.9))
    # watch severity uses the larger of |composite - 50| = 40 and |trend - 50| = 20 -> 0.8
    assert it["roce"]["severity"] == pytest.approx(0.8)
    assert [classify(m, rc) for m in rep["metrics"].values()] == ["strengths", "strengths", "weaknesses", "watch"]
    # an unverified manual KPI feeding the metric multiplies confidence by 0.8
    q = _metric_item("roe", rep["metrics"]["roe"], rep, rc, {"k1"}, {"roe": {"k1"}})
    assert q["confidence"] == pytest.approx(0.8)


def test_select_caps_and_flag_cover(toy):
    rep, rc = toy
    flag = {"id": "R99", "name": "toy", "pillar": "returns", "severity": "high", "text": "t", "condition": "m('roa') < 0.01"}
    f = _flag_item(flag, rep, rc, set(), {}, set())
    assert f["score"] == pytest.approx(1.0) and f["covers"] == ["roa"]
    roa = _metric_item("roa", rep["metrics"]["roa"], rep, rc, set(), {})
    assert [c["id"] for c in select([roa, f], rc)] == ["R99"]          # roa is covered by the flag
    many = [_metric_item(mid, _m("returns", "green", c, 5), rep, rc, set(), {})
            for mid, c in (("roe", 95), ("roce", 90), ("roic", 85), ("roa", 80))]
    assert [c["id"] for c in select(many, rc)] == ["roe", "roce"]       # max 2 per pillar
    assert family_key("revenue_cagr_3y") == family_key("revenue_cagr_5y") == "revenue_cagr"
    assert family_key("pe_percentile_10y") == "pe"


# ---------------------------------------------------------------------------------------------- driver chain
def _node(name, path, t0, t1, contribution, unit, leaf):
    return {"name": name, "path": path, "t0": t0, "t1": t1, "change": t1 - t0, "contribution": contribution,
            "share_of_root": contribution / -0.041, "unit": unit, "leaf": leaf}


def test_driver_chain_hand_built():
    win = {"status": "ok", "nodes": {
        "roe": _node("Return on equity", "roe", 0.200, 0.159, -0.041, "pct", False),
        "pat_margin": _node("PAT margin", "roe > pat_margin", 0.10, 0.094, -0.0123, "pct", True),
        "asset_turnover": _node("Asset turnover", "roe > asset_turnover", 1.2, 1.0, -0.0287, "x", False),
        "receivables_to_sales": _node("Receivables / sales", "roe > asset_turnover > receivables_to_sales", 60 / 365, 85 / 365, -0.025, "days_of_sales", True),
        "inventory_to_sales": _node("Inventory / sales", "roe > asset_turnover > inventory_to_sales", 30 / 365, 31 / 365, -0.0037, "days_of_sales", True),
    }}
    # 0.0287 / 0.041 = 70%; the largest same-sign leaf under asset turnover is receivables / sales
    assert chain_for_node("roe", win, "3y", "return on equity") == (
        "−4.1 pts over 3y; 70% from asset turnover; asset turnover fell because receivables / sales rose 60 days → 85 days")
    # a leaf: 0.025 / 0.041 = 61% of the root change
    assert chain_for_node("receivables_to_sales", win, "3y", "return on equity") == (
        "drove 61% of the return on equity change over 3y (−4.1 pts)")


# ---------------------------------------------------------------------------------------------- KPI dependency map
def test_kpi_dependencies_bank(real_cfg):
    d = kpi_dependencies(real_cfg, "bank")
    assert {"credit_cost", "provisions_to_assets", "provisions_to_ppop", "cost_to_income_bank"} <= set(d["provisions_cr"]["metrics"])
    assert "BK08" in d["provisions_cr"]["flags"]
    assert "bank_dupont" in d["provisions_cr"]["trees"]
    assert "loan_growth" in d["advances_cr"]["metrics"]
