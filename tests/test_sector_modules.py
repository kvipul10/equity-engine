"""Session 2: sector modules (config/sectors/*.yaml).

* Hand-computed checks for EVERY sector metric (formulas defined in YAML), on synthetic companies with literal KPIs.
* Bank path: bank DuPont identity and tree (replacing fin_roe), fallback without provisions, switch-offs, sector bands
  and flags, KPI-missing -> not evaluable.
* Real-estate path: cash-flow-led tree, switch-offs, flags.
* Config integrity (inheritance, formulas, tree nodes, sources), templates, manual-KPI v2 loader, data-file rules,
  manual-only years and as-of truncation of KPIs.
"""
from __future__ import annotations

import copy
import json
import math
import random
import statistics as st
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

import test_metric_formulas as T
from synthetic import make_project
from synthetic_sectors import SECTOR_COMPANIES, add_sector_companies, kpi_csv

REPO = Path(__file__).resolve().parent.parent
REL = 1e-9


@pytest.fixture(scope="module")
def sector_root(tmp_path_factory):
    return add_sector_companies(make_project(tmp_path_factory.mktemp("sectors")))


@pytest.fixture(scope="module")
def scfg(sector_root):
    from engine.config import Config
    from engine.paths import Paths

    return Config.load(Paths.default(sector_root))


@pytest.fixture(scope="module")
def comp(scfg):
    from engine.analysis import compute

    return {t: compute(t, scfg) for t in SECTOR_COMPANIES}


@pytest.fixture(scope="module")
def reps(scfg):
    from engine.analysis import analyse

    return {t: analyse(t, scfg) for t in ("SYNTHBK", "SYNTHBKNP", "SYNTHRE", "SYNTHNB")}


K = {t: s["kpis"] for t, s in SECTOR_COMPANIES.items()}


def k(t, kpi, fy="FY26", pct=None):
    v = K[t][kpi][fy]
    return v / 100 if (pct if pct is not None else kpi.endswith("_pct")) else v


# ---------------------------------------------------------------------------------------- hand-computed values
b_nii = [T.b_rev[i] - T.b_int[i] for i in range(6)]
adv, depo, prov = K["SYNTHBK"]["advances_cr"], K["SYNTHBK"]["deposits_cr"], K["SYNTHBK"]["provisions_cr"]
opex_ex_prov = T.b_opex[5] - prov["FY26"] + T.b_dep[5]
gm = T.gm
ept = {fy: T.ebitda[i] * 10 / K["SYNTHMT"]["sales_volume_mt"][fy] for i, fy in enumerate(T.CO_FY if hasattr(T, "CO_FY") else [f"FY{17 + j}" for j in range(10)]) if fy in K["SYNTHMT"]["sales_volume_mt"]}
roce = [None] + [T.ebit[i] / (T.avg(T.eq, i) + T.avg(T.bor, i)) for i in range(1, 10)]
trough = min(range(10), key=lambda i: T.ebm[i])
ci = K["SYNTHFM"]["commodity_index"]
fy_co = [f"FY{17 + j}" for j in range(10)]
cchg = {fy_co[i]: ci[fy_co[i]] / ci[fy_co[i - 1]] - 1 for i in range(1, 10) if fy_co[i] in ci and fy_co[i - 1] in ci}
xs = [cchg[fy_co[i]] for i in range(5, 10)]
ys = [gm[i] - gm[i - 1] for i in range(5, 10)]
gm_beta = sum((a - st.mean(xs)) * (b - st.mean(ys)) for a, b in zip(xs, ys)) / sum((a - st.mean(xs)) ** 2 for a in xs) * 0.10
capex_sales = [T.capex[i] / T.rev[i] for i in range(1, 10)]
units = K["SYNTHAU"]["units_sold"]
roe26 = T.pat_c[9] / T.avg(T.eq, 9)
area = K["SYNTHRT"]["retail_area_msf"]

EXPECTED = {
    # bank (SYNTHBK, FY26)
    "loan_growth": ("SYNTHBK", adv["FY26"] / adv["FY25"] - 1),
    "deposit_growth": ("SYNTHBK", depo["FY26"] / depo["FY25"] - 1),
    "nim_reported": ("SYNTHBK", 0.034), "yield_on_advances": ("SYNTHBK", 0.098), "cost_of_funds_reported": ("SYNTHBK", 0.062),
    "cost_to_income_bank": ("SYNTHBK", opex_ex_prov / (b_nii[5] + T.b_oi[5])),
    "credit_cost": ("SYNTHBK", 85 / ((9600 + 10800) / 2)),
    "gnpa_ratio": ("SYNTHBK", 0.034), "nnpa_ratio": ("SYNTHBK", 0.013), "pcr": ("SYNTHBK", 0.58),
    "provisions_to_ppop": ("SYNTHBK", 85 / (b_nii[5] + T.b_oi[5] - opex_ex_prov)),
    "slippage_ratio": ("SYNTHBK", 0.026), "crar": ("SYNTHBK", 0.126), "cet1": ("SYNTHBK", 0.10), "casa_ratio": ("SYNTHBK", 0.355),
    "cd_ratio": ("SYNTHBK", 10800 / 13600),
    "bank_opex_to_assets": ("SYNTHBK", opex_ex_prov / T.avg(T.b_ta, 5)),
    "provisions_to_assets": ("SYNTHBK", 85 / T.avg(T.b_ta, 5)),
    # nbfc (SYNTHNB)
    "aum_growth": ("SYNTHNB", 14200 / 12500 - 1),
    "aum_vs_equity_growth": ("SYNTHNB", (14200 / 12500 - 1) - (T.b_eq[5] / T.b_eq[4] - 1)),
    "spread": ("SYNTHNB", 0.146 - 0.081), "cost_of_borrowing": ("SYNTHNB", 0.081),
    "credit_cost_aum": ("SYNTHNB", 170 / ((12500 + 14200) / 2)), "stage2_ratio": ("SYNTHNB", 0.028), "alm_gap_1y": ("SYNTHNB", -0.04),
    "bank_borrowing_share": ("SYNTHNB", 0.25), "market_borrowing_share": ("SYNTHNB", 0.50), "cp_share": ("SYNTHNB", 0.12),
    "deposit_share": ("SYNTHNB", 0.20),
    # insurance (SYNTHIN)
    "vnb_margin": ("SYNTHIN", 0.23), "vnb_growth": ("SYNTHIN", 170 / 165 - 1), "ape_growth": ("SYNTHIN", 739 / 688 - 1),
    "ev_growth": ("SYNTHIN", 5800 / 5200 - 1), "operating_roev": ("SYNTHIN", 0.155), "persistency_13m": ("SYNTHIN", 0.835),
    "persistency_61m": ("SYNTHIN", 0.55), "solvency_ratio": ("SYNTHIN", 1.65), "opex_ratio_reported": ("SYNTHIN", 0.108),
    "combined_ratio": ("SYNTHIN", 1.04), "p_ev": ("SYNTHIN", 160 * 5 / 5800),
    # IT services (SYNTHIT, SYNTHCO financials)
    "cc_growth": ("SYNTHIT", 0.02), "book_to_bill": ("SYNTHIT", 6.5 * 1000 / 2700), "deal_tcv_growth": ("SYNTHIT", 6.5 / 7.5 - 1),
    "headcount_growth": ("SYNTHIT", 13000 / 12500 - 1), "utilisation": ("SYNTHIT", 0.78), "attrition": ("SYNTHIT", 0.21),
    "dso_incl_unbilled": ("SYNTHIT", (T.rec[9] + 220) / T.rev[9] * 365),
    "revenue_per_employee": ("SYNTHIT", T.rev[9] * 1e7 / ((12500 + 13000) / 2)),
    # FMCG
    "volume_growth": ("SYNTHFM", -0.02), "price_mix_growth": ("SYNTHFM", (T.rev[9] / T.rev[8] - 1) + 0.02),
    "ad_spend_pct": ("SYNTHFM", 190 / T.rev[9]), "gross_margin_change_1y": ("SYNTHFM", gm[9] - gm[8]),
    "commodity_change_1y": ("SYNTHFM", 101 / 108 - 1), "gm_commodity_pass_through": ("SYNTHFM", gm_beta),
    # cyclical (SYNTHMT)
    "ebitda_margin_10y_avg": ("SYNTHMT", st.mean(T.ebm)),
    "roce_10y_avg": ("SYNTHMT", st.mean(roce[1:])),
    "ebitda_per_tonne": ("SYNTHMT", T.ebitda[9] * 10 / 12),
    "ebitda_per_tonne_vs_avg": ("SYNTHMT", ept["FY26"] / st.mean(ept.values()) - 1),
    "capacity_utilisation": ("SYNTHMT", 12 / ((14 + 15) / 2)),
    "leverage_at_trough": ("SYNTHMT", T.nd[trough] / T.ebitda[trough]),
    # auto
    "volume_growth_units": ("SYNTHAU", 128000 / 130000 - 1), "realisation_per_unit": ("SYNTHAU", T.rev[9] * 1e7 / 128000),
    "realisation_growth": ("SYNTHAU", (T.rev[9] / 128000) / (T.rev[8] / 130000) - 1),
    "auto_capacity_utilisation": ("SYNTHAU", 128000 / 160000),
    "capex_cycle": ("SYNTHAU", (T.capex[9] / T.rev[9]) / st.mean(capex_sales)),
    # pharma
    "rd_pct": ("SYNTHPH", 130 / T.rev[9]), "us_share": ("SYNTHPH", 650 / T.rev[9]), "india_share": ("SYNTHPH", 770 / T.rev[9]),
    "us_growth": ("SYNTHPH", 650 / 680 - 1), "india_growth": ("SYNTHPH", 770 / 690 - 1), "anda_pipeline": ("SYNTHPH", 98),
    # capital goods
    "order_book_to_revenue": ("SYNTHCG", 3900 / T.rev[9]), "book_to_bill_orders": ("SYNTHCG", 2100 / T.rev[9]),
    "order_book_growth": ("SYNTHCG", 3900 / 3800 - 1), "opening_order_book": ("SYNTHCG", 3800),
    "execution_rate": ("SYNTHCG", T.rev[9] / 3800), "advances_to_revenue": ("SYNTHCG", 500 / T.rev[9]),
    # real estate
    "presales_growth": ("SYNTHRE", 2500 / 2600 - 1), "presales_to_revenue": ("SYNTHRE", 2500 / T.rev[9]),
    "collections_to_presales": ("SYNTHRE", 1650 / 2500), "cfo_to_collections": ("SYNTHRE", T.cfo[9] / 1650),
    "cfo_to_presales": ("SYNTHRE", T.cfo[9] / 2500), "inventory_months": ("SYNTHRE", 5600 / (2500 / 12)),
    "net_debt_to_presales": ("SYNTHRE", T.nd[9] / 2500),
    # utilities
    "regulated_roe_gap": ("SYNTHUT", roe26 - 0.155), "regulated_equity_growth": ("SYNTHUT", 870 / 800 - 1),
    "capacity_growth_mw": ("SYNTHUT", 13500 / 12500 - 1), "plf": ("SYNTHUT", 0.66),
    "discom_receivable_days": ("SYNTHUT", 600 / T.rev[9] * 365),
    "de_vs_normative": ("SYNTHUT", (T.bor[9] / T.eq[9]) / 2.333333), "renewable_share": ("SYNTHUT", 3800 / 13500),
    # telecom
    "arpu": ("SYNTHTC", 200), "arpu_growth": ("SYNTHTC", 200 / 205 - 1), "subscriber_growth": ("SYNTHTC", 335 / 330 - 1),
    "capex_intensity_reported": ("SYNTHTC", 360 / T.rev[9]), "lease_share_of_debt": ("SYNTHTC", 160 / T.bor[9]),
    "spectrum_share_of_debt": ("SYNTHTC", 80 / T.bor[9]),
    # retail
    "avg_retail_area": ("SYNTHRT", (13.6 + 15.4) / 2), "revenue_per_sqft": ("SYNTHRT", T.rev[9] * 10 / ((13.6 + 15.4) / 2)),
    "store_additions": ("SYNTHRT", 390 - 340), "store_growth": ("SYNTHRT", 390 / 340 - 1), "sssg": ("SYNTHRT", 0.03),
    "ebitda_margin_pre_ind_as116": ("SYNTHRT", (T.ebitda[9] - 66) / T.rev[9]),
    "lease_adj_net_debt_to_ebitda": ("SYNTHRT", (T.nd[9] - 250) / (T.ebitda[9] - 66)),
    # holdco
    "standalone_pat_share": ("SYNTHHC", 180 / T.pat[9]), "standalone_roe": ("SYNTHHC", 180 / ((1000 + 1100) / 2)),
    "conso_minus_standalone_roe": ("SYNTHHC", roe26 - 180 / ((1000 + 1100) / 2)),
    "standalone_debt_to_equity": ("SYNTHHC", 700 / 1100), "contingent_to_networth": ("SYNTHHC", 600 / 1100),
    "holdco_discount": ("SYNTHHC", 1 - 2200 / 3000), "segment_concentration": ("SYNTHHC", 0.48),
}
SERIES_CHECKED = {"peak_cycle_capex"}


@pytest.mark.parametrize("mid", sorted(EXPECTED))
def test_sector_metric_hand_computed(comp, mid):
    t, exp = EXPECTED[mid]
    got = comp[t].metrics[mid].iloc[-1]
    assert got == pytest.approx(exp, rel=REL, abs=1e-12), f"{mid} ({t}): got {got}, expected {exp}"


@pytest.mark.parametrize("ticker", ["SYNTHMT", "SYNTHMT2"])
def test_peak_cycle_capex_series(comp, ticker):
    """capex/dep in years whose EBITDA margin exceeds the rolling 10y average (>= 5 years), else n/a.
    SYNTHMT2 = SYNTHCO with FY26 raw material 700 instead of 880 (margin spike), so both branches are exercised."""
    s = comp[ticker].metrics["peak_cycle_capex"]
    rm2 = SECTOR_COMPANIES[ticker].get("overrides", {}).get("raw_material", T.rm)
    ebm = [(T.rev[i] - ((rm2[i] - T.ci[i]) + T.emp[i] + T.oopex[i])) / T.rev[i] for i in range(10)]
    for i, fy in enumerate(fy_co):
        window = ebm[max(0, i - 9): i + 1]
        if i == 0 or len(window) < 5:
            assert math.isnan(s[fy]), fy
            continue
        exp = (T.capex[i] / T.dep[i]) if ebm[i] > st.mean(window) else float("nan")
        if math.isnan(exp):
            assert math.isnan(s[fy]), fy
        else:
            assert s[fy] == pytest.approx(exp, rel=REL), fy
    if ticker == "SYNTHMT2":
        assert s.notna().any() and s.isna().any()   # both branches exercised


def test_every_sector_metric_has_a_hand_computed_check(scfg):
    from engine.registry import REGISTRY

    sector_ids = {m for m, d in REGISTRY.items() if d.origin != "engine"}
    missing = sorted(sector_ids - set(EXPECTED) - SERIES_CHECKED)
    assert not missing, f"sector metrics without a hand-computed expectation: {missing}"
    assert len(sector_ids) >= 100


# ---------------------------------------------------------------------------------------- bank path
def test_bank_dupont_identity_exact(comp):
    m = comp["SYNTHBK"].metrics
    for fy in ("FY22", "FY24", "FY26"):
        roa = (m["nii_to_assets"][fy] + m["other_income_to_assets"][fy] - m["bank_opex_to_assets"][fy]
               - m["provisions_to_assets"][fy] - m["tax_to_assets"][fy] + m["minority_to_assets"][fy])
        assert roa == pytest.approx(m["roa"][fy], rel=1e-12, abs=1e-15)
        assert m["roa"][fy] * m["equity_multiplier"][fy] == pytest.approx(m["roe"][fy], rel=1e-12)


def test_bank_dupont_tree_replaces_fin_roe(reps):
    d = reps["SYNTHBK"]["drivers"]
    assert "bank_dupont" in d and "fin_roe" not in d
    w = d["bank_dupont"]["windows"]
    oks = [r for r in w.values() if r["status"] == "ok"]
    assert oks, w
    for r in oks:
        assert not r["inexact_nodes"] and abs(r["residual"]) < 1e-12
        names = {x["driver"] for x in r["top_drivers"]}
        assert names & {"provisions_to_assets", "bank_opex_to_assets", "yield_on_assets", "interest_to_assets"}


def test_bank_dupont_falls_back_without_provisions(reps):
    d = reps["SYNTHBKNP"]["drivers"]
    assert d["fin_roe"]["fallback_for"] == "bank_dupont" and "provisions_cr" in d["fin_roe"]["note"]
    assert all(r["status"] == "n/a" for r in d["bank_dupont"]["windows"].values())


def test_bank_switch_offs_and_sector_section(comp, reps):
    m = comp["SYNTHBK"].metrics
    for off in ("ebitda_margin", "dso", "nwc_days", "credit_deposit_proxy"):
        assert off not in m
    sec = reps["SYNTHBK"]["sector"]
    assert sec["archetype"] == "bank" and sec["lineage"] == ["default", "bank"]
    assert "credit cost" in sec["how_to_read"].lower()
    assert any(x["id"] == "credit_deposit_proxy" for x in sec["switched_off"])
    assert any(g["applies"] == "NF" and g["n_metrics"] > 50 for g in sec["switched_off_groups"])
    assert sec["required_kpis_present_asof"] == "8/8" and sec["kpi_verified_share"] == 1.0
    assert reps["SYNTHBK"]["pillars"]["cash_quality"]["name"].endswith("(asset quality)")
    assert reps["SYNTHBK"]["overall"]["weights_basis"] == "sector:bank"


def test_bank_sector_bands_and_flags(reps):
    r = reps["SYNTHBK"]
    crar = r["metrics"]["crar"]
    assert crar["band"]["origin"] == "config/sectors/bank.yaml" and crar["band"]["red"] == pytest.approx(0.115)
    assert crar["band"]["source_url"].startswith("https://website.rbi.org.in/")
    assert r["metrics"]["casa_ratio"]["band"]["source_type"] == "indicative"
    trig = {f["id"] for f in r["flags"]["triggered"]}
    assert {"BK01", "BK02", "BK03", "BK06"} <= trig
    assert not ({"BK04", "BK05", "BK07"} & trig)
    np_ = {f["id"]: f for f in reps["SYNTHBKNP"]["flags"]["not_evaluable"]}
    assert "BK08" in np_ and "provisions_cr" in np_["BK08"]["missing"]


def test_nbfc_inherits_bank_and_overrides(reps, scfg):
    s = scfg.sector_of("nbfc")
    assert s.lineage == ["default", "bank", "nbfc"]
    assert "casa_pct" not in s.manual_kpis and "aum_cr" in s.manual_kpis
    assert "nii_to_assets" not in s.bands and s.bands["crar"]["red"] == 0.15
    assert s.bands["pcr"]["_origin"] == "config/sectors/bank.yaml"   # inherited band keeps its true origin
    trig = {f["id"] for f in reps["SYNTHNB"]["flags"]["triggered"]}
    assert {"NB02", "NB03", "NB04"} <= trig
    assert "bank_dupont" in reps["SYNTHNB"]["drivers"]


# ---------------------------------------------------------------------------------------- real-estate path
def test_real_estate_switch_offs(comp, reps):
    m = comp["SYNTHRE"].metrics
    for off in ("dio", "dso", "operating_cycle", "asset_turnover", "beneish_m_score", "capex_to_depreciation"):
        assert off not in m, off
    ids = {x["id"] for x in reps["SYNTHRE"]["sector"]["switched_off"]}
    assert {"dio", "asset_turnover", "beneish_m_score"} <= ids


def test_real_estate_cash_tree_exact(reps):
    t = reps["SYNTHRE"]["drivers"]["real_estate_cash"]
    oks = [r for r in t["windows"].values() if r["status"] == "ok"]
    assert len(oks) == 3
    for r in oks:
        assert not r["inexact_nodes"] and abs(r["residual"]) < 1e-9
    r1 = t["windows"]["1y"]
    assert r1["root_from"] == pytest.approx(T.cfo[8]) and r1["root_to"] == pytest.approx(T.cfo[9])
    assert {x["driver"] for x in r1["top_drivers"]} <= {"kpi:presales_cr", "collections_to_presales", "cfo_to_collections"}


def test_real_estate_flags(reps):
    trig = {f["id"] for f in reps["SYNTHRE"]["flags"]["triggered"]}
    assert {"RE01", "RE02", "RE04"} <= trig and "RE03" not in trig
    txt = next(f["text"] for f in reps["SYNTHRE"]["flags"]["triggered"] if f["id"] == "RE01")
    assert "66.0%" in txt


def test_other_sector_flags_trigger(scfg):
    from engine.analysis import analyse

    expect = {"SYNTHIN": {"IN01", "IN05"}, "SYNTHIT": {"IT01", "IT02", "IT03", "IT04", "IT05"}, "SYNTHFM": {"FM01"},
              "SYNTHPH": {"PH01", "PH02"}, "SYNTHCG": {"CG01", "CG02", "CG03"}, "SYNTHUT": {"UT02"}, "SYNTHTC": {"TC01"},
              "SYNTHRT": {"RT01", "RT02"}, "SYNTHHC": {"HC02"}}
    for t, ids in expect.items():
        trig = {f["id"] for f in analyse(t, scfg)["flags"]["triggered"]}
        assert ids <= trig, (t, ids - trig)


def test_sector_trees_exact(scfg):
    from engine.analysis import analyse

    for t, tree in (("SYNTHMT", "cyclical_ebitda"), ("SYNTHAU", "auto_revenue"), ("SYNTHCG", "order_book_revenue"),
                    ("SYNTHRT", "retail_revenue")):
        w = analyse(t, scfg)["drivers"][tree]["windows"]
        oks = [r for r in w.values() if r["status"] == "ok"]
        assert oks, (t, tree, w)
        for r in oks:
            assert not r["inexact_nodes"] and abs(r["residual"]) < 1e-9, (t, tree)


# ---------------------------------------------------------------------------------------- config integrity
ARCHETYPES = {"bank", "nbfc", "insurance", "it_services", "fmcg", "consumer_manufacturing", "metals", "cement", "chemicals", "auto",
              "pharma", "capital_goods_defence", "real_estate", "utilities", "telecom", "retail", "holdco", "default"}


def test_all_archetypes_present_and_resolved(real_cfg):
    assert set(real_cfg.sectors) == ARCHETYPES
    for a, s in real_cfg.sectors.items():
        assert s.lineage[0] == "default" and s.lineage[-1] == a
        assert 3 <= len([l for l in s.how_to_read.splitlines() if l.strip()]) <= 6 or a == "default"
    for a in ("metals", "cement", "chemicals"):
        assert real_cfg.sector_of(a).lineage == ["default", "_cyclical", a]
        assert "leverage_at_trough" in real_cfg.sector_of(a).metrics_add


def test_sector_sources_and_kpis(real_cfg):
    for a, s in real_cfg.sectors.items():
        for mid, b in s.bands.items():
            st_ = b.get("source_type", "external")
            if st_ == "external":
                assert b.get("source_url", "").startswith("http") and b.get("as_of"), (a, mid)
            elif st_ in ("indicative", "rule_of_thumb"):
                assert b.get("rationale") and b.get("as_of"), (a, mid)
        for kid, kd in s.manual_kpis.items():
            assert kd.get("unit") and kd.get("description") and kd.get("where"), (a, kid)


def test_tree_nodes_exist_for_their_archetypes(real_cfg):
    from engine.drivers import Tree, _parse_child, load_trees
    from engine.registry import REGISTRY
    from engine.standardise import BS_COLS, CF_COLS, MARKET_COLS, PNL_COLS, SHARE_COLS

    fields = set(PNL_COLS + BS_COLS + CF_COLS + MARKET_COLS + SHARE_COLS) | {"revenue", "cfo", "ebitda"}
    for a, s in real_cfg.sectors.items():
        toks = real_cfg.tokens(a)
        trees = [t for t in load_trees(real_cfg) + [Tree(x) for x in s.drivers_add] if any(x in toks for x in t.applies)]
        for tree in trees:
            for n in tree.nodes():
                if n.startswith("kpi:"):
                    assert n[4:] in s.manual_kpis, (a, tree.id, n)
                elif n in REGISTRY:
                    assert REGISTRY[n].applies_to(toks), (a, tree.id, n)
                else:
                    assert n in fields, (a, tree.id, n)
        for gen, sid in s.drivers_replace.items():
            assert sid in {t["id"] for t in s.drivers_add}, (a, sid)


def test_rule_ids_unique_and_valid(real_cfg):
    from engine.flags import validate_rules

    rules = real_cfg.all_rules()
    validate_rules(rules)
    assert len(rules) >= 100 and len({r["id"] for r in rules}) == len(rules)


def test_templates_match_configs(real_cfg, tmp_path):
    from engine.templates import COLUMNS, template_rows, year_range

    tdir = REPO / "data" / "manual" / "templates"
    assert {p.stem.replace("_kpis", "") for p in tdir.glob("*_kpis.csv")} == ARCHETYPES
    for a, s in real_cfg.sectors.items():
        df = pd.read_csv(tdir / f"{a}_kpis.csv", dtype=str).fillna("")
        assert list(df.columns) == COLUMNS
        assert df.values.tolist() == [[str(x) for x in r] for r in template_rows(s, year_range("FY22-FY26"))]


# ---------------------------------------------------------------------------------------- manual KPI files
def test_manual_v2_loader(tmp_path):
    from engine.standardise import load_manual_full

    p = tmp_path / "X_kpis.csv"
    p.write_text("metric,fiscal_year,value,unit,source_url,source_date,verified\n"
                 "gnpa_pct,FY25,1.33,%,https://example.org/a,2025-04-19,N\n"
                 "advances_cr,FY25,2600000,Rs cr,https://example.org/b,2025-04-19,Y\n"
                 "crar_pct,FY25,,%,,,\n")
    vals, prov = load_manual_full(p)
    assert vals.loc["FY25", "gnpa_pct"] == pytest.approx(0.0133) and vals.loc["FY25", "advances_cr"] == 2600000
    assert "crar_pct" not in vals.columns                      # blank = not found
    assert set(prov["verified"]) == {"Y", "N"} and prov.loc[prov["kpi"] == "gnpa_pct", "source_url"].iloc[0] == "https://example.org/a"
    vals2, _ = load_manual_full(p, use_unverified=False)
    assert list(vals2.columns) == ["advances_cr"]


def _kpi_files():
    return sorted((REPO / "data" / "manual").glob("*_kpis.csv"))


def test_real_kpi_files_follow_the_rules(real_cfg):
    """Every value collected for a real company carries a source URL and date, a Y/N verification flag, a KPI id the
    company's sector module defines, and a valid fiscal year. Blank values (not found) are allowed; estimates are not."""
    for p in _kpi_files():
        t = p.name.replace("_kpis.csv", "")
        if t.startswith("_"):
            continue
        df = pd.read_csv(p, dtype=str).fillna("")
        assert list(df.columns)[:7] == ["metric", "fiscal_year", "value", "unit", "source_url", "source_date", "verified"], p.name
        known = real_cfg.sector_of(real_cfg.archetype_of(t)).manual_kpis
        for _, r in df.iterrows():
            assert r["metric"] in known, (p.name, r["metric"])
            assert r["fiscal_year"].upper().startswith("FY") and r["fiscal_year"][2:].isdigit(), (p.name, r["fiscal_year"])
            if r["value"].strip():
                float(r["value"].replace(",", ""))
                assert r["source_url"].startswith("http"), (p.name, r["metric"], r["fiscal_year"])
                assert len(r["source_date"]) >= 7 and r["source_date"][:4].isdigit(), (p.name, r["metric"], r["fiscal_year"])
                assert r["verified"] in ("Y", "N"), (p.name, r["metric"], r["fiscal_year"])


# ---------------------------------------------------------------------------------------- manual-only years + as-of
def test_manual_only_years_extend_timeline(tmp_path):
    from engine.analysis import analyse
    from engine.config import Config
    from engine.paths import Paths

    root = add_sector_companies(make_project(tmp_path / "mo"))
    kp = copy.deepcopy(SECTOR_COMPANIES["SYNTHBK"]["kpis"])
    kp["gnpa_pct"].update({"FY19": 3.1, "FY20": 2.8})
    kp["casa_pct"].update({"FY19": 40.0, "FY20": 41.0})
    (root / "data" / "manual" / "SYNTHBK_kpis.csv").write_text(kpi_csv(kp))
    cfg = Config.load(Paths.default(root))
    rep = analyse("SYNTHBK", cfg)
    assert rep["asof"]["data_window"] == "FY21-FY26" and rep["asof"]["manual_kpi_window"] == "FY19-FY26"
    assert rep["metrics"]["gnpa_ratio"]["series"]["FY19"] == pytest.approx(0.031)
    assert rep["metrics"]["roe"]["series"]["FY19"] is None
    rep18 = analyse("SYNTHBK", cfg, asof="FY23")
    assert set(rep18["metrics"]["gnpa_ratio"]["series"]) == {"FY19", "FY20", "FY21", "FY22", "FY23"}


def test_asof_ignores_later_kpis_and_financials(tmp_path):
    from engine.analysis import analyse
    from engine.config import Config
    from engine.paths import Paths

    a = add_sector_companies(make_project(tmp_path / "a"))
    b = add_sector_companies(make_project(tmp_path / "b"))
    rng = random.Random(7)
    kp = copy.deepcopy(SECTOR_COMPANIES["SYNTHBK"]["kpis"])
    for kpi, ser in kp.items():
        for fy in list(ser):
            if fy in ("FY24", "FY25", "FY26"):
                ser[fy] = round(rng.uniform(1, 99), 3)
    (b / "data" / "manual" / "SYNTHBK_kpis.csv").write_text(kpi_csv(kp))
    wb = openpyxl.load_workbook(b / "data" / "raw" / "screener" / "SYNTHBK.xlsx")
    ws = wb["Data Sheet"]
    for r in list(range(17, 32)) + list(range(57, 73)) + list(range(82, 86)) + [90, 93]:
        for c in (5, 6, 7):  # FY24..FY26 columns of the 6-year bank workbook
            ws.cell(r, c, rng.uniform(-5000, 5000))
    ws.cell(8, 2, 1234.5)
    wb.save(b / "data" / "raw" / "screener" / "SYNTHBK.xlsx")
    ra = analyse("SYNTHBK", Config.load(Paths.default(a)), asof="FY23")
    rb = analyse("SYNTHBK", Config.load(Paths.default(b)), asof="FY23")
    for r in (ra, rb):
        r["data_notes"] = [n for n in r["data_notes"] if n["category"] != "source"]
    assert json.dumps(ra, sort_keys=True) == json.dumps(rb, sort_keys=True)
    assert set(ra["manual_kpis"]["gnpa_pct"]["values"]) == {"FY21", "FY22", "FY23"}


# ---------------------------------------------------------------------------------------------- KPI coverage report
def test_kpi_coverage_report_matches_files(real_cfg):
    from engine.templates import _read_kpis, coverage, coverage_markdown, target_years

    rows = coverage(real_cfg)
    assert {r["ticker"] for r in rows} == set(real_cfg.universe)
    yb = [r for r in rows if r["ticker"] == "YESBANK"]
    assert yb and yb[0]["years"][:5] == ["FY14", "FY15", "FY16", "FY17", "FY18"] and yb[0]["years"][-1] == "FY26"
    assert target_years({"role": "test"}) == ["FY22", "FY23", "FY24", "FY25", "FY26"]
    for r in rows:
        have = _read_kpis(real_cfg.paths.manual_file(r["ticker"]))
        assert r["found"] == [y for y in r["years"] if (r["kpi"], y) in have]
    md = coverage_markdown(real_cfg)
    assert md.startswith("# Manual KPI coverage") and "| YESBANK | bank |" in md
    assert (REPO / "data" / "manual" / "COVERAGE.md").read_text() == md, "COVERAGE.md is stale: run python -m engine kpi-coverage"
