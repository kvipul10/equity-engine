"""Ingest (label-based Data Sheet parser) and standardisation rules, on real exports and synthetic grids."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from engine.ingest import parse_grid, parse_workbook
from engine.standardise import load_manual, quarter_label

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw" / "screener"
REAL = sorted(p.stem for p in RAW.glob("*.xlsx"))
KEYS = {"sales", "raw_material", "change_in_inventory", "power_fuel", "other_mfr", "employee_cost", "selling_admin", "other_exp",
        "other_income", "depreciation", "interest", "pbt", "tax", "net_profit", "dividend", "share_capital", "reserves", "borrowings",
        "other_liabilities", "total_liabilities", "net_block", "cwip", "investments", "other_assets", "total_assets", "receivables",
        "inventory", "cash", "shares_raw", "bonus_shares", "face_value", "cfo", "cfi", "cff", "net_cash_flow", "price",
        "adjusted_shares_cr"}


@pytest.mark.parametrize("ticker", REAL)
def test_every_real_export_parses(ticker):
    r = parse_workbook(RAW / f"{ticker}.xlsx")
    assert set(r.annual.index) == KEYS
    assert r.unmapped == []
    assert r.annual.shape[1] == 10 and list(r.annual.columns) == sorted(r.annual.columns)
    assert r.quarterly.shape == (9, 10)
    assert r.meta["current_price"] > 0 and r.meta["market_cap"] > 0
    assert r.meta.get("number_of_shares") is None  # formula without cached value
    assert any("formula" in w for w in r.warnings)
    # the two 'Total' rows are liabilities and assets, which must agree
    assert (r.annual.loc["total_liabilities"] - r.annual.loc["total_assets"]).abs().max() < 1.0


def test_parser_is_label_based_not_row_based():
    d1, d2 = dt.datetime(2025, 3, 31), dt.datetime(2026, 3, 31)
    grid = [
        ["COMPANY NAME", "X LTD"], [None], ["Current Price", 10.0], ["Market Capitalization", 100.0], [None], [None],
        ["PROFIT & LOSS"], [None], ["Report Date", d1, d2], ["Net profit", 5.0, 6.0], ["Sales", 100.0, 120.0], ["Tax", 1, 2],
        ["Profit before tax", 6, 8], [None], ["BALANCE SHEET"], ["Report Date", d1, d2], ["Reserves", 50, 55],
        ["Equity Share Capital", 10, 10], ["Total", 60, 65], ["Net Block", 30, 30], ["Total", 60, 65], ["CASH FLOW:"],
        ["Report Date", d1, d2], ["Cash from Operating Activity", 4, 5], ["PRICE:", 9, 10], ["DERIVED:"],
        ["Adjusted Equity Shares in Cr", 10, 10], ["Mystery Row", 1, 2],
    ]
    r = parse_grid(grid, "X")
    assert r.annual.loc["sales"].tolist() == [100.0, 120.0]
    assert r.annual.loc["net_profit"].tolist() == [5.0, 6.0]
    assert r.annual.loc["total_liabilities"].tolist() == [60.0, 65.0]
    assert r.annual.loc["total_assets"].tolist() == [60.0, 65.0]
    assert r.annual.loc["price"].tolist() == [9.0, 10.0]
    assert ("derived", "Mystery Row") in r.unmapped


def test_unit_label_detected_and_scaled():
    d = dt.datetime(2026, 3, 31)
    grid = [["COMPANY NAME", "Y"], ["Note", "Figures in Rs. Million"], ["PROFIT & LOSS"], ["Report Date", d], ["Sales", 1000.0],
            ["PRICE:", 5.0], ["DERIVED:"], ["Adjusted Equity Shares in Cr", 2.0]]
    r = parse_grid(grid, "Y")
    assert r.units == "million" and r.annual.loc["sales"].iloc[0] == pytest.approx(100.0)
    assert r.annual.loc["price"].iloc[0] == 5.0  # prices and share counts are not scaled


def test_synthetic_roundtrip(project_root):
    from synthetic import CO

    r = parse_workbook(project_root / "data" / "raw" / "screener" / "SYNTHCO.xlsx")
    assert r.annual.loc["sales"].tolist() == CO["sales"]
    assert r.annual.loc["adjusted_shares_cr"].tolist() == CO["shares_cr"]
    assert r.company == "SYNTHETIC CO LTD"


def test_nestle_fifteen_month_period_and_stale_column(real_cfg):
    from engine.standardise import load_standardised

    s = load_standardised("NESTLEIND", real_cfg)
    a = s.annual
    assert a.loc["FY24", "period_months"] == 15 and bool(a.loc["FY24", "annualised"])
    assert a.loc["FY24", "revenue"] == pytest.approx(24393.89 * 12 / 15, rel=1e-6)
    assert bool(a.loc["FY23", "stale_bs"]) and pd.isna(a.loc["FY23", "equity"])
    assert a.loc["FY24", "opening_fy"] == "FY22"
    assert a.loc["FY23", "period_months"] == 12 and not pd.isna(a.loc["FY23", "revenue"])
    assert "period_change" in a.loc["FY24", "comparability_break"]
    texts = " ".join(n["text"] for n in s.notes)
    assert "15 months" in texts and "exact copy" in texts


def test_exceptional_minority_and_core_profit(project_cfg):
    from engine.standardise import load_standardised

    s = load_standardised("SYNTHCO", project_cfg)
    a = s.annual
    assert a["exceptional_est"].tolist() == [0, 0, 0, 0, 0, 100, 0, 0, 0, 0]
    assert a.loc["FY22", "pat_core"] == pytest.approx(a.loc["FY22", "pat"] - 100 + 100 * 0.25168)
    assert (a["minority_and_associates"] - (-10)).abs().max() < 1e-9
    assert not [n for n in s.notes if n["category"] == "identity"]


def test_real_exceptionals_detected(real_cfg):
    from engine.standardise import load_standardised

    dlf = load_standardised("DLF", real_cfg).annual
    assert dlf.loc["FY18", "exceptional_est"] > 5000          # DCCDL transaction gain inside other income
    bharti = load_standardised("BHARTIARTL", real_cfg).annual
    assert bharti.loc["FY20", "exceptional_est"] < -20000      # AGR charge


def test_bank_semantics_and_blanks(real_cfg):
    from engine.standardise import load_standardised

    b = load_standardised("HDFCBANK", real_cfg)
    assert b.family == "bank_like"
    assert b.annual.loc["FY26", "nii"] == pytest.approx(348614.62 - 185490.58, rel=1e-6)
    assert (b.annual["exceptional_est"] == 0).all()
    assert b.annual.loc["FY24", "inorganic_step"]               # HDFC Ltd merger
    life = load_standardised("HDFCLIFE", real_cfg)
    assert life.annual.loc["FY17", "borrowings"] == 0.0          # blank = zero
    assert pd.isna(life.annual.loc["FY17", "price"])             # blank price = missing


def test_ind_as_116_detected(real_cfg):
    from engine.standardise import load_standardised

    for t in ("DMART", "BHARTIARTL"):
        assert "ind_as_116" in load_standardised(t, real_cfg).annual.loc["FY20", "comparability_break"]


def test_manual_kpis(tmp_path):
    p = tmp_path / "X_kpis.csv"
    p.write_text("period,kpi,value,unit,source\nFY24,promoter_holding_pct,51.5,%,AR\nQ2FY25,promoter_holding_pct,50,%,BSE\n"
                 "2025-03-31,promoter_holding_pct,49,%,BSE\nFY25,trade_payables,1200,Rs cr,AR\n")
    m = load_manual(p)
    assert m.loc["FY24", "promoter_holding_pct"] == pytest.approx(0.515)
    assert m.loc["FY25", "promoter_holding_pct"] == pytest.approx(0.49)     # last observation in the FY wins
    assert m.loc["FY25", "trade_payables"] == 1200


def test_quarter_labels():
    assert quarter_label(pd.Timestamp("2026-09-30")) == "Q2FY27"
    assert quarter_label(pd.Timestamp("2026-03-31")) == "Q4FY26"
    assert quarter_label(pd.Timestamp("2025-12-31")) == "Q3FY26"
