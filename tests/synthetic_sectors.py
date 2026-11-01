"""Synthetic sector companies: the SYNTHCO / SYNTHBANK workbooks re-used under every archetype, each with a literal
v2 manual-KPI file. KPI values are chosen so that specific sector flags trigger (documented next to each series).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from synthetic import BK, BK_YEARS, CO, CO_YEARS, write_workbook

CO_FY = [f"FY{17 + i}" for i in range(10)]   # FY17..FY26
BK_FY = [f"FY{21 + i}" for i in range(6)]    # FY21..FY26


def _series(fys, vals):
    return dict(zip(fys, vals))


def last(n, vals):
    """Map the last len(vals) fiscal years ending FY26 to vals."""
    fys = [f"FY{26 - len(vals) + 1 + i}" for i in range(len(vals))]
    return dict(zip(fys, vals))


# ticker -> (archetype, base workbook, {kpi: {FY: value}}) ; '%' units are written for *_pct KPIs
SECTOR_COMPANIES: Dict[str, Dict] = {
    "SYNTHBK": {"archetype": "bank", "base": "bank", "kpis": {
        "advances_cr": last(6, [6000, 6800, 7700, 8600, 9600, 10800]),
        "deposits_cr": last(6, [8000, 8900, 9900, 11000, 12300, 13600]),
        "casa_pct": last(6, [42, 43, 41, 39, 37, 35.5]),           # -3.5pp in 2y -> BK06
        "gnpa_pct": last(6, [2.5, 2.2, 2.0, 2.4, 2.9, 3.4]),       # rising 2y and > 3% -> BK01
        "nnpa_pct": last(6, [0.8, 0.7, 0.6, 0.8, 1.0, 1.3]),
        "pcr_pct": last(6, [68, 70, 72, 66, 62, 58]),               # < 60% -> BK02
        "crar_pct": last(6, [16.5, 16.0, 15.2, 14.1, 13.4, 12.6]), # < 13% -> BK03
        "provisions_cr": last(6, [40, 45, 50, 60, 70, 85]),
        "cet1_pct": last(6, [13.0, 12.6, 12.0, 11.2, 10.6, 10.0]),
        "nim_pct": last(6, [3.9, 3.8, 3.7, 3.6, 3.5, 3.4]),
        "yield_on_advances_pct": last(6, [9.5, 9.3, 9.4, 9.6, 9.7, 9.8]),
        "cost_of_funds_pct": last(6, [5.6, 5.4, 5.6, 5.9, 6.1, 6.2]),
        "cost_to_income_pct": last(6, [48, 47, 46, 46, 45, 45]),
        "slippage_ratio_pct": last(6, [1.6, 1.5, 1.4, 1.9, 2.2, 2.6]),
        "promoter_holding_pct": last(3, [26.0, 25.5, 25.0]),
    }},
    "SYNTHBKNP": {"archetype": "bank", "base": "bank", "kpis": {   # no provisions -> bank_dupont falls back to fin_roe
        "advances_cr": last(2, [9600, 10800]), "deposits_cr": last(2, [12300, 13600]), "gnpa_pct": last(2, [2.9, 3.4]),
    }},
    "SYNTHNB": {"archetype": "nbfc", "base": "bank", "kpis": {
        "advances_cr": last(6, [7000, 7900, 8900, 10000, 11200, 12500]),
        "aum_cr": last(6, [7500, 8500, 9700, 11000, 12500, 14200]),
        "gnpa_pct": last(6, [1.8, 1.7, 1.6, 1.5, 1.6, 1.9]),
        "nnpa_pct": last(6, [0.7, 0.6, 0.6, 0.6, 0.7, 0.9]),
        "pcr_pct": last(6, [60, 62, 63, 62, 60, 55]),
        "crar_pct": last(6, [22, 21, 20, 19.5, 19, 18.5]),
        "provisions_cr": last(6, [90, 100, 110, 125, 140, 170]),
        "stage2_pct": last(6, [2.0, 1.8, 1.7, 1.9, 2.3, 2.8]),     # rising 2y -> NB02
        "yield_on_aum_pct": last(6, [15.0, 15.2, 15.1, 15.0, 14.8, 14.6]),
        "cost_of_borrowing_pct": last(6, [7.5, 7.3, 7.6, 7.9, 8.0, 8.1]),
        "alm_gap_1y_pct": last(6, [5, 4, 3, 1, -2, -4]),           # negative -> NB04
        "borrowing_bank_pct": last(6, [30, 29, 28, 27, 26, 25]),
        "borrowing_market_pct": last(6, [45, 46, 47, 48, 49, 50]),
        "borrowing_cp_pct": last(6, [8, 9, 10, 11, 12, 12]),       # > 10% -> NB03
        "borrowing_deposits_pct": last(6, [20, 20, 20, 20, 20, 20]),
    }},
    "SYNTHIN": {"archetype": "insurance", "base": "bank", "kpis": {
        "vnb_cr": last(6, [100, 120, 135, 150, 165, 170]),
        "vnb_margin_pct": last(6, [26, 27, 27.5, 26, 24, 23]),
        "embedded_value_cr": last(6, [3000, 3500, 4000, 4600, 5200, 5800]),
        "operating_roev_pct": last(6, [17, 17.5, 16.8, 16.2, 16.0, 15.5]),
        "ape_cr": last(6, [385, 445, 490, 577, 688, 739]),
        "persistency_13m_pct": last(6, [86, 87, 87.5, 86, 85, 83.5]),
        "persistency_61m_pct": last(6, [50, 52, 53, 54, 54, 55]),
        "solvency_ratio_pct": last(6, [200, 195, 190, 180, 172, 165]),  # < 170% -> IN01
        "opex_ratio_pct": last(6, [12, 11.8, 11.5, 11.2, 11, 10.8]),
        "combined_ratio_pct": last(6, [102, 101, 99, 98, 103, 104]),   # > 100% -> IN05
    }},
    "SYNTHIT": {"archetype": "it_services", "base": "co", "kpis": {
        "cc_revenue_growth_pct": last(5, [10, 9, 8, 7, 2]),         # < 3% -> IT03
        "utilisation_pct": last(5, [86, 85, 84, 82, 78]),           # < 80% -> IT02
        "attrition_ltm_pct": last(5, [15, 22, 18, 14, 21]),         # > 20% -> IT01
        "deal_tcv_usd_bn": last(5, [5.0, 6.0, 7.0, 7.5, 6.5]),      # -13% -> IT05
        "revenue_usd_mn": last(5, [2100, 2300, 2450, 2550, 2700]),
        "unbilled_revenue_cr": last(5, [100, 120, 150, 180, 220]),  # DSO+unbilled rising 2y -> IT04
        "headcount": last(5, [10000, 11000, 11800, 12500, 13000]),
    }},
    "SYNTHFM": {"archetype": "fmcg", "base": "co", "kpis": {
        "volume_growth_pct": last(5, [5, 4, 3, 1, -2]),            # negative with price/mix > 8% -> FM01
        "ad_promo_cr": last(5, [160, 175, 185, 200, 190]),
        "commodity_index": last(7, [100, 104, 115, 121, 112, 108, 101]),
    }},
    "SYNTHMT": {"archetype": "metals", "base": "co", "kpis": {
        "sales_volume_mt": last(5, [10, 10.5, 11, 11.5, 12]),
        "capacity_mtpa": last(6, [12, 12, 13, 13, 14, 15]),
    }},
    "SYNTHMT2": {"archetype": "metals", "base": "co",   # FY26 margin spike (raw material 700) -> capex at the cycle peak
                 "overrides": {"raw_material": [400, 440, 480, 520, 580, 640, 700, 760, 820, 700]},
                 "kpis": {"sales_volume_mt": last(5, [10, 10.5, 11, 11.5, 12]), "capacity_mtpa": last(6, [12, 12, 13, 13, 14, 15])}},
    "SYNTHAU": {"archetype": "auto", "base": "co", "kpis": {
        "units_sold": last(6, [100000, 110000, 120000, 125000, 130000, 128000]),
        "capacity_units": last(6, [140000, 140000, 150000, 150000, 150000, 160000]),
    }},
    "SYNTHPH": {"archetype": "pharma", "base": "co", "kpis": {
        "rd_expense_cr": last(5, [110, 120, 130, 145, 130]),       # -1.2pp of sales -> PH01
        "us_revenue_cr": last(5, [700, 720, 700, 680, 650]),       # falling 2y ...
        "india_revenue_cr": last(5, [500, 560, 620, 690, 770]),
        "anda_pending_count": last(5, [100, 105, 110, 104, 98]),   # ... with pipeline shrinking -> PH02
        "fda_oai_count": last(5, [0, 0, 1, 1, 0]),
    }},
    "SYNTHCG": {"archetype": "capital_goods_defence", "base": "co", "kpis": {
        "order_book_cr": last(6, [3000, 3300, 3600, 3700, 3800, 3900]),     # < 2x revenue -> CG02
        "order_inflow_cr": last(6, [1500, 1800, 1900, 1800, 1950, 2100]),  # book-to-bill < 1 for 2y -> CG01
        "customer_advances_cr": last(6, [500, 520, 560, 600, 650, 500]),   # -23% -> CG03
    }},
    "SYNTHRE": {"archetype": "real_estate", "base": "co", "kpis": {
        "presales_cr": last(6, [1500, 1800, 2100, 2400, 2600, 2500]),      # falling while net debt rises -> RE04
        "collections_cr": last(6, [1300, 1500, 1700, 1900, 2000, 1650]),   # 66% of pre-sales -> RE01
        "unsold_inventory_cr": last(6, [3000, 3300, 3600, 4000, 4800, 5600]),  # 27 months and rising -> RE02
    }},
    "SYNTHUT": {"archetype": "utilities", "base": "co", "kpis": {
        "installed_capacity_mw": last(6, [10000, 10500, 11000, 11800, 12500, 13500]),
        "plf_pct": last(6, [70, 72, 71, 69, 68, 66]),
        "regulated_equity_cr": last(6, [600, 640, 690, 740, 800, 870]),
        "discom_receivables_cr": last(6, [300, 320, 350, 420, 500, 600]),  # ~100 days -> UT02
        "renewable_capacity_mw": last(6, [500, 900, 1400, 2000, 2800, 3800]),
    }},
    "SYNTHTC": {"archetype": "telecom", "base": "co", "kpis": {
        "arpu_inr": last(5, [150, 170, 190, 205, 200]),            # falling -> TC01
        "subscribers_mn": last(5, [300, 310, 320, 330, 335]),
        "lease_liabilities_cr": last(5, [120, 130, 140, 150, 160]),
        "spectrum_liabilities_cr": last(5, [50, 50, 60, 70, 80]),
        "capex_cr": last(5, [300, 320, 330, 350, 360]),
    }},
    "SYNTHRT": {"archetype": "retail", "base": "co", "kpis": {
        "store_count": last(6, [200, 230, 265, 300, 340, 390]),    # store growth accelerating ...
        "retail_area_msf": last(6, [8.0, 9.2, 10.6, 12.0, 13.6, 15.4]),  # ... while revenue/sq ft falls -> RT02
        "lfl_growth_pct": last(6, [5, 9, 7, 4, 3.5, 3]),           # < 4% for 2y -> RT01
        "lease_payments_cr": last(6, [40, 45, 50, 55, 60, 66]),
        "lease_liabilities_cr": last(6, [150, 170, 190, 210, 230, 250]),
    }},
    "SYNTHHC": {"archetype": "holdco", "base": "co", "kpis": {
        "standalone_pat_cr": last(4, [150, 170, 160, 180]),
        "standalone_networth_cr": last(4, [800, 900, 1000, 1100]),
        "standalone_borrowings_cr": last(4, [300, 350, 600, 700]),
        "listed_holdings_value_cr": last(1, [3000]),
        "contingent_liabilities_cr": last(4, [300, 400, 500, 600]),  # 55% of net worth -> HC02
        "largest_segment_ebitda_share_pct": last(4, [55, 52, 50, 48]),
    }},
}


def kpi_csv(kpis: Dict[str, Dict[str, float]]) -> str:
    lines = ["metric,fiscal_year,value,unit,source_url,source_date,verified"]
    for k, series in kpis.items():
        unit = "%" if k.endswith("_pct") else "unit"
        for fy, v in series.items():
            lines.append(f"{k},{fy},{v},{unit},synthetic://tests,2026-11-01,Y")
    return "\n".join(lines) + "\n"


def add_sector_companies(root: Path) -> Path:
    raw = root / "data" / "raw" / "screener"
    rows = []
    for t, spec in SECTOR_COMPANIES.items():
        if spec["base"] == "bank":
            write_workbook(raw / f"{t}.xlsx", BK, BK_YEARS, f"{t} LTD")
        else:
            spec_ = dict(CO)
            spec_.update(spec.get("overrides", {}))
            write_workbook(raw / f"{t}.xlsx", spec_, CO_YEARS, f"{t} LTD")
        (root / "data" / "manual" / f"{t}_kpis.csv").write_text(kpi_csv(spec["kpis"]))
        rows.append(f"{t},{spec['archetype']},test,FY26")
    uni = root / "data" / "universe.csv"
    uni.write_text(uni.read_text() + "\n".join(rows) + "\n")
    return root
