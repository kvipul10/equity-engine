"""Synthetic companies written as genuine Screener-format workbooks (same 'Data Sheet' layout as the real export).

All inputs are literal round numbers so every metric can be checked by hand (tests/test_metric_formulas.py).
Derived rows (PBT, net profit, totals) are computed here so the accounting identities hold exactly.
"""
from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path
from typing import Dict, List

import yaml

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------------------------------------
# SYNTHCO: non-financial, 10 years FY17..FY26 (index 0..9), March year-end.
CO_YEARS = [dt.datetime(2017 + i, 3, 31) for i in range(10)]
CO = {
    "sales":        [1000, 1100, 1200, 1300, 1450, 1600, 1750, 1900, 2050, 2200],
    "raw_material": [400, 440, 480, 520, 580, 640, 700, 760, 820, 880],
    "change_in_inventory": [10] * 10,
    "power_fuel":   [50, 55, 60, 65, 70, 80, 85, 95, 100, 110],
    "other_mfr":    [30, 33, 36, 39, 45, 48, 52, 57, 60, 66],
    "employee":     [100, 110, 120, 130, 145, 160, 180, 200, 220, 240],
    "selling_admin": [80, 88, 96, 104, 116, 128, 140, 152, 164, 176],
    "other_exp":    [40, 44, 48, 52, 58, 64, 70, 76, 82, 88],
    # 2% of sales every year, plus a Rs 100 cr exceptional gain inside FY22 other income
    "other_income": [20, 22, 24, 26, 29, 132, 35, 38, 41, 44],
    "depreciation": [50, 55, 60, 70, 75, 80, 85, 90, 95, 100],
    "interest":     [20, 20, 22, 24, 25, 25, 26, 28, 30, 30],
    "tax_rate": 0.25,          # tax = 25% of PBT
    "minority": -10,           # net profit = PBT - tax - 10 (minority interest)
    "dividend":     [30, 32, 35, 38, 40, 60, 50, 55, 60, 66],
    "shares_cr":    [10, 10, 10, 10, 10, 10, 10, 10.2, 10.2, 10.0],
    "face_value": 10,
    "reserves":     [400, 460, 530, 600, 680, 770, 860, 960, 1060, 1170],
    "borrowings":   [200, 220, 240, 250, 300, 320, 330, 350, 380, 400],
    "other_liabilities": [300, 320, 340, 370, 400, 430, 460, 500, 540, 580],
    "net_block":    [500, 540, 580, 620, 700, 760, 800, 850, 900, 950],
    "cwip":         [50, 60, 70, 80, 90, 100, 110, 120, 130, 140],
    "investments":  [100, 110, 120, 130, 140, 150, 160, 170, 180, 190],
    "receivables":  [150, 170, 190, 210, 240, 270, 300, 330, 360, 400],
    "inventory":    [120, 130, 140, 150, 165, 180, 195, 210, 225, 240],
    "cash":         [60, 65, 70, 75, 80, 85, 90, 95, 100, 105],
    "cfo":          [150, 160, 170, 180, 190, 200, 210, 230, 250, 270],
    "cfi":          [-120, -130, -140, -150, -180, -160, -150, -200, -220, -240],
    "cff":          [-20, -25, -25, -25, -5, -35, -55, -25, -25, -25],
    "price":        [100, 110, 120, 90, 150, 160, 170, 180, 200, 210],
    "current_price": 220,
    "q_dates": [dt.datetime(2024, 6, 30), dt.datetime(2024, 9, 30), dt.datetime(2024, 12, 31), dt.datetime(2025, 3, 31),
                dt.datetime(2025, 6, 30), dt.datetime(2025, 9, 30), dt.datetime(2025, 12, 31), dt.datetime(2026, 3, 31),
                dt.datetime(2026, 6, 30), dt.datetime(2026, 9, 30)],
    "q_sales":    [450, 470, 480, 500, 490, 520, 540, 560, 550, 580],
    "q_expenses": [315, 329, 336, 350, 343, 364, 378, 392, 385, 406],
    "q_other_income": [9, 9, 10, 10, 10, 11, 11, 11, 11, 12],
    "q_depreciation": [22, 23, 23, 24, 24, 25, 25, 26, 26, 27],
    "q_interest": [7] * 10,
    "q_minority": -2,
}
CO_MANUAL = """period,kpi,value,unit,source
FY24,trade_payables,180,Rs cr,synthetic
FY25,trade_payables,190,Rs cr,synthetic
FY26,trade_payables,200,Rs cr,synthetic
FY23,promoter_holding_pct,60,%,synthetic
FY24,promoter_holding_pct,59,%,synthetic
FY25,promoter_holding_pct,58,%,synthetic
FY26,promoter_holding_pct,55,%,synthetic
FY24,promoter_pledge_pct,5,%,synthetic
FY25,promoter_pledge_pct,8,%,synthetic
FY26,promoter_pledge_pct,12,%,synthetic
"""

# ---------------------------------------------------------------------------------------------------------
# SYNTHBANK: bank, 6 years FY21..FY26 (index 0..5). Sales = interest earned, Interest = interest expended,
# Borrowings = deposits + borrowings, Other expenses include provisions.
BK_YEARS = [dt.datetime(2021 + i, 3, 31) for i in range(6)]
BK = {
    "sales":        [1000, 1100, 1250, 1400, 1550, 1700],
    "raw_material": [0] * 6, "change_in_inventory": [0] * 6, "power_fuel": [0] * 6, "other_mfr": [0] * 6,
    "employee":     [100, 110, 120, 130, 140, 150],
    "selling_admin": [50, 55, 60, 65, 70, 75],
    "other_exp":    [80, 90, 100, 110, 120, 130],
    "other_income": [150, 165, 180, 200, 220, 240],
    "depreciation": [10, 11, 12, 13, 14, 15],
    "interest":     [600, 650, 740, 830, 920, 1000],
    "tax_rate": 0.25,
    "minority": -5,
    "dividend":     [20, 22, 25, 28, 30, 33],
    "shares_cr":    [5, 5, 5, 5, 5, 5],
    "face_value": 10,
    "reserves":     [450, 520, 600, 690, 790, 900],
    "borrowings":   [9000, 10000, 11200, 12500, 14000, 15500],
    "other_liabilities": [400, 450, 500, 560, 620, 690],
    "net_block":    [100, 110, 120, 130, 140, 150],
    "cwip":         [0] * 6,
    "investments":  [2500, 2800, 3100, 3500, 3900, 4300],
    "receivables":  [0] * 6,
    "inventory":    [0] * 6,
    "cash":         [600, 650, 700, 750, 800, 850],
    "cfo":          [100, -50, 200, 150, 120, 300],
    "cfi":          [-20, -25, -30, -30, -35, -40],
    "cff":          [-30, 100, -120, -80, -50, -200],
    "price":        [100, 120, 130, 125, 140, 150],
    "current_price": 160,
    "q_dates": [],
}


def derive(spec: Dict) -> Dict[str, List[float]]:
    """Rows that Screener computes: PBT, tax, net profit, totals, other assets (so identities hold)."""
    n = len(spec["sales"])
    d = {}
    exp = [spec["raw_material"][i] - spec["change_in_inventory"][i] + spec["power_fuel"][i] + spec["other_mfr"][i]
           + spec["employee"][i] + spec["selling_admin"][i] + spec["other_exp"][i] for i in range(n)]
    pbt = [spec["sales"][i] - exp[i] + spec["other_income"][i] - spec["depreciation"][i] - spec["interest"][i] for i in range(n)]
    tax = [spec["tax_rate"] * p for p in pbt]
    np_ = [pbt[i] - tax[i] + spec["minority"] for i in range(n)]
    sc = [s * spec["face_value"] for s in spec["shares_cr"]]
    tl = [sc[i] + spec["reserves"][i] + spec["borrowings"][i] + spec["other_liabilities"][i] for i in range(n)]
    oa = [tl[i] - spec["net_block"][i] - spec["cwip"][i] - spec["investments"][i] for i in range(n)]
    ncf = [spec["cfo"][i] + spec["cfi"][i] + spec["cff"][i] for i in range(n)]
    d.update(expenses=exp, pbt=pbt, tax=tax, net_profit=np_, share_capital=sc, total=tl, other_assets=oa, ncf=ncf)
    if spec.get("q_dates"):
        qn = len(spec["q_sales"])
        op = [spec["q_sales"][i] - spec["q_expenses"][i] for i in range(qn)]
        qpbt = [op[i] + spec["q_other_income"][i] - spec["q_depreciation"][i] - spec["q_interest"][i] for i in range(qn)]
        qtax = [spec["tax_rate"] * p for p in qpbt]
        qnp = [qpbt[i] - qtax[i] + spec["q_minority"] for i in range(qn)]
        d.update(q_op=op, q_pbt=qpbt, q_tax=qtax, q_np=qnp)
    return d


def write_workbook(path: Path, spec: Dict, years: List[dt.datetime], company: str) -> Path:
    import openpyxl

    d = derive(spec)
    wb = openpyxl.Workbook()
    pl = wb.active
    pl.title = "Profit & Loss"
    pl["A1"] = "='Data Sheet'!B1"
    pl["B4"] = "='Data Sheet'!B17"
    for name in ("Quarters", "Balance Sheet", "Cash Flow", "Customization"):
        wb.create_sheet(name)
    ws = wb.create_sheet("Data Sheet")
    n = len(years)

    def row(r, label, vals=None):
        ws.cell(r, 1, label)
        if vals is not None:
            for i, v in enumerate(vals):
                ws.cell(r, 2 + i, v)

    row(1, "COMPANY NAME", [company])
    row(2, "LATEST VERSION", [2.1])
    row(3, "CURRENT VERSION", [2.1])
    row(5, "META")
    ws.cell(6, 1, "Number of shares")
    ws.cell(6, 2, "=IF(B9>0, B9/B8, 0)")
    row(7, "Face Value", [spec["face_value"]])
    row(8, "Current Price", [spec["current_price"]])
    row(9, "Market Capitalization", [spec["current_price"] * spec["shares_cr"][-1]])
    row(15, "PROFIT & LOSS")
    row(16, "Report Date", years)
    for r, lab, key in [(17, "Sales", "sales"), (18, "Raw Material Cost", "raw_material"), (19, "Change in Inventory", "change_in_inventory"),
                        (20, "Power and Fuel", "power_fuel"), (21, "Other Mfr. Exp", "other_mfr"), (22, "Employee Cost", "employee"),
                        (23, "Selling and admin", "selling_admin"), (24, "Other Expenses", "other_exp"), (25, "Other Income", "other_income"),
                        (26, "Depreciation", "depreciation"), (27, "Interest", "interest")]:
        row(r, lab, [None if v == 0 else v for v in spec[key]])
    row(28, "Profit before tax", d["pbt"])
    row(29, "Tax", d["tax"])
    row(30, "Net profit", d["net_profit"])
    row(31, "Dividend Amount", spec["dividend"])
    row(40, "Quarters")
    if spec.get("q_dates"):
        row(41, "Report Date", spec["q_dates"])
        row(42, "Sales", spec["q_sales"])
        row(43, "Expenses", spec["q_expenses"])
        row(44, "Other Income", spec["q_other_income"])
        row(45, "Depreciation", spec["q_depreciation"])
        row(46, "Interest", spec["q_interest"])
        row(47, "Profit before tax", d["q_pbt"])
        row(48, "Tax", d["q_tax"])
        row(49, "Net profit", d["q_np"])
        row(50, "Operating Profit", d["q_op"])
    row(55, "BALANCE SHEET")
    row(56, "Report Date", years)
    row(57, "Equity Share Capital", d["share_capital"])
    row(58, "Reserves", spec["reserves"])
    row(59, "Borrowings", spec["borrowings"])
    row(60, "Other Liabilities", spec["other_liabilities"])
    row(61, "Total", d["total"])
    row(62, "Net Block", spec["net_block"])
    row(63, "Capital Work in Progress", [None if v == 0 else v for v in spec["cwip"]])
    row(64, "Investments", spec["investments"])
    row(65, "Other Assets", d["other_assets"])
    row(66, "Total", d["total"])
    row(67, "Receivables", [None if v == 0 else v for v in spec["receivables"]])
    row(68, "Inventory", [None if v == 0 else v for v in spec["inventory"]])
    row(69, "Cash & Bank", spec["cash"])
    row(70, "No. of Equity Shares", [s * 1e7 for s in spec["shares_cr"]])
    row(71, "New Bonus Shares")
    row(72, "Face value", [spec["face_value"]] * n)
    row(80, "CASH FLOW:")
    row(81, "Report Date", years)
    row(82, "Cash from Operating Activity", spec["cfo"])
    row(83, "Cash from Investing Activity", spec["cfi"])
    row(84, "Cash from Financing Activity", spec["cff"])
    row(85, "Net Cash Flow", d["ncf"])
    row(90, "PRICE:", spec["price"])
    row(92, "DERIVED:")
    row(93, "Adjusted Equity Shares in Cr", spec["shares_cr"])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


# Test market inputs: round numbers so the cost of capital is easy to compute by hand.
TEST_RF = 0.07
TEST_ERP = 0.06
TEST_BETA = 1.0  # override for both synthetic companies -> Ke = 0.07 + 1.0 x 0.06 = 0.13


def make_project(root: Path, extra_universe: str = "") -> Path:
    """A self-contained project root: copied config (with round market inputs), synthetic raw files, universe, manual KPIs."""
    shutil.copytree(REPO / "config", root / "config")
    m = yaml.safe_load((root / "config" / "market.yaml").read_text())
    m["risk_free"].update(value=TEST_RF, as_of="2026-10-30")
    m["equity_risk_premium"].update(value=TEST_ERP)
    m["beta"]["overrides"] = {"SYNTHCO": TEST_BETA, "SYNTHBANK": TEST_BETA, "SYNTHNBFC": TEST_BETA, "SYNTHINS": TEST_BETA}
    (root / "config" / "market.yaml").write_text(yaml.safe_dump(m, sort_keys=False))
    raw = root / "data" / "raw" / "screener"
    write_workbook(raw / "SYNTHCO.xlsx", CO, CO_YEARS, "SYNTHETIC CO LTD")
    write_workbook(raw / "SYNTHBANK.xlsx", BK, BK_YEARS, "SYNTHETIC BANK LTD")
    write_workbook(raw / "SYNTHNBFC.xlsx", BK, BK_YEARS, "SYNTHETIC NBFC LTD")
    write_workbook(raw / "SYNTHINS.xlsx", BK, BK_YEARS, "SYNTHETIC INSURER LTD")
    (root / "data" / "manual").mkdir(parents=True, exist_ok=True)
    (root / "data" / "manual" / "SYNTHCO_kpis.csv").write_text(CO_MANUAL)
    (root / "data" / "universe.csv").write_text(
        "ticker,archetype,role,asof\nSYNTHCO,consumer_manufacturing,test,FY26\nSYNTHBANK,bank,test,FY26\n"
        "SYNTHNBFC,nbfc,test,FY26\nSYNTHINS,insurance,test,FY26\n" + extra_universe)
    return root
