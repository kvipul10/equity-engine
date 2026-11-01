"""Build config/sector_benchmarks.yaml from Damodaran's India industry datasets.

Run:  python -m engine build-benchmarks
Input files live in data/external/damodaran/ (download fresh copies each January from
https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html, "India" column).

Output (all values decimals):
  betas:      archetype -> levered / unlevered (cash-corrected) industry beta, D/E, tax rate
  references: archetype -> raw industry values shown as context in reports
  bands:      archetype -> metric -> {red, green, centre, source_url, as_of, derivation}

Band derivation (documented in docs/methodology.md):
  centre c = industry value (simple average when an archetype maps to several industries)
  half-width h = max(relative_half_width * |c|, floor[unit])
  higher-is-better: red = c - h, green = c + h ; lower-is-better: green = c - h, red = c + h
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml

BASE_URL = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/"

# dataset key -> file name
FILES = {
    "margin": "marginIndia.xls",
    "wc": "wcdataIndia.xls",
    "capex": "capexIndia.xls",
    "beta": "betaIndia.xls",
    "eva": "EVAIndia.xls",
    "debt": "dbtfundIndia.xls",
    "pe": "peIndia.xls",
    "pbv": "pbvIndia.xls",
    "vebitda": "vebitdaIndia.xls",
    "div": "divfundIndia.xls",
    "histgr": "histgrIndia.xls",
    "tax": "taxrateIndia.xls",
    "lease": "leaseeffectIndia.xls",
}

# engine metric -> (dataset, column, transform, direction, unit)
# transform: None | "x365" | "x365_per_cogs" (inventory or payables days on a COGS basis)
BAND_SPECS = {
    "gross_margin": ("margin", "Gross Margin", None, "higher", "pct"),
    "ebitda_margin": ("margin", "EBITDA/Sales", None, "higher", "pct"),
    "ebit_margin": ("margin", "Pre-tax Unadjusted Operating Margin", None, "higher", "pct"),
    "pat_margin": ("margin", "Net Margin", None, "higher", "pct"),
    "dso": ("wc", "Acc Rec/ Sales", "x365", "lower", "days"),
    "dio": ("wc", "Inventory/Sales", "x365_per_cogs", "lower", "days"),
    "dpo": ("wc", "Acc Pay/ Sales", "x365_per_cogs", "higher", "days"),
    "nwc_days": ("wc", "Non-cash WC/ Sales", "x365", "lower", "days"),
    "ic_turnover": ("capex", "Sales/ Invested Capital (LTM)", None, "higher", "x"),
}

# Notes on definitional differences vs the engine's Screener-based metric (shown with the band).
BAND_NOTES = {
    "gross_margin": "Damodaran gross margin uses Capital IQ COGS; engine COGS = materials + power & fuel + other manufacturing expenses.",
    "ebit_margin": "Damodaran operating margin excludes other income; engine EBIT margin includes core (non-exceptional) other income, so this band is slightly lenient for treasury-rich companies (other_income_to_pbt is scored separately).",
    "dio": "Industry inventory/sales converted to days of COGS using the industry COGS/sales ratio.",
    "dpo": "Industry payables/sales converted to days of COGS using the industry COGS/sales ratio.",
    "nwc_days": "Damodaran non-cash working capital includes all current items; engine uses Screener other assets - cash - other liabilities (includes some non-current items).",
    "ic_turnover": "Damodaran LTM sales / invested capital (book).",
}

REFERENCE_SPECS = {
    "ebitda_margin": ("margin", "EBITDA/Sales"),
    "gross_margin": ("margin", "Gross Margin"),
    "operating_margin": ("margin", "Pre-tax Unadjusted Operating Margin"),
    "net_margin": ("margin", "Net Margin"),
    "cogs_to_sales": ("margin", "COGS/Sales"),
    "sga_to_sales": ("margin", "SG&A/ Sales"),
    "lease_expense_to_sales": ("margin", "Lease Expense/Sales"),
    "receivables_to_sales": ("wc", "Acc Rec/ Sales"),
    "inventory_to_sales": ("wc", "Inventory/Sales"),
    "payables_to_sales": ("wc", "Acc Pay/ Sales"),
    "noncash_wc_to_sales": ("wc", "Non-cash WC/ Sales"),
    "capex_to_depreciation": ("capex", "Cap Ex/Deprecn"),
    "net_capex_to_sales": ("capex", "Net Cap Ex/Sales"),
    "sales_to_invested_capital": ("capex", "Sales/ Invested Capital (LTM)"),
    "roe": ("eva", "ROE"),
    "roc_after_tax": ("eva", "ROC"),
    "cost_of_equity_usd": ("eva", "Cost of Equity"),
    "cost_of_capital_usd": ("eva", "Cost of Capital"),
    "book_debt_to_capital": ("debt", "Book Debt to Capital"),
    "interest_coverage": ("debt", "Interest Coverage Ratio"),
    "debt_to_ebitda": ("debt", "Debt to EBITDA"),
    "trailing_pe": ("pe", "Trailing PE"),
    "pbv": ("pbv", "PBV"),
    "ev_to_invested_capital": ("pbv", "EV/ Invested Capital"),
    "ev_ebitda": ("vebitda", "EV/EBITDA"),
    "dividend_payout": ("div", "Dividend Payout"),
    "revenue_cagr_5y_hist": ("histgr", "CAGR in Revenues- Last 5 years"),
    "net_income_cagr_5y_hist": ("histgr", "CAGR in Net Income- Last 5 years"),
    "aggregate_tax_rate": ("tax", "Aggregate tax rate"),
}

UNIT_FLOORS = {"pct": 0.02, "days": 10.0, "x": 0.2}
RELATIVE_HALF_WIDTH = 0.20


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("\n", " ")).strip()


def _excel_date(v) -> Optional[str]:
    try:
        d = _dt.date(1899, 12, 30) + _dt.timedelta(days=float(v))
        return d.isoformat()
    except Exception:  # pragma: no cover - defensive
        return None


def read_industry_table(path: Path) -> Dict:
    """Return {"date_updated": iso, "columns": [...], "rows": {industry: {col: value}}}."""
    import xlrd  # optional dependency, only needed here

    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_name("Industry Averages")
    date_updated = None
    for r in range(min(sh.nrows, 6)):
        if _norm(sh.cell_value(r, 0)).lower().startswith("date updated"):
            date_updated = _excel_date(sh.cell_value(r, 1))
    hdr = None
    for r in range(min(sh.nrows, 40)):
        if _norm(sh.cell_value(r, 0)).lower().startswith("industry"):
            hdr = r
            break
    if hdr is None:
        raise ValueError(f"{path.name}: no 'Industry Name' header row found")
    cols: List[str] = []
    for c in range(sh.ncols):
        name = _norm(sh.cell_value(hdr, c))
        if name in cols:  # duplicated header (e.g. vebitda has two blocks)
            name = f"{name} #2"
        cols.append(name)
    rows = {}
    for r in range(hdr + 1, sh.nrows):
        ind = _norm(sh.cell_value(r, 0))
        if not ind:
            continue
        rec = {}
        for c in range(1, sh.ncols):
            v = sh.cell_value(r, c)
            rec[cols[c]] = float(v) if isinstance(v, (int, float)) and v != "" else None
        rows[ind] = rec
    return {"date_updated": date_updated, "columns": cols, "rows": rows}


def _avg(values: List[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _industry_value(tables, dataset, column, industries) -> Optional[float]:
    t = tables[dataset]
    return _avg([t["rows"].get(ind, {}).get(column) for ind in industries])


def derive_band(centre: float, direction: str, unit: str, rel: float = RELATIVE_HALF_WIDTH) -> Dict:
    h = max(rel * abs(centre), UNIT_FLOORS[unit])
    if direction == "higher":
        return {"red": centre - h, "green": centre + h}
    return {"green": centre - h, "red": centre + h}


def build(root: Path) -> Dict:
    ext = root / "data" / "external" / "damodaran"
    sectors = yaml.safe_load((root / "config" / "sectors.yaml").read_text())
    tables = {}
    for key, fname in FILES.items():
        p = ext / fname
        if not p.exists():
            raise FileNotFoundError(f"Missing {p}; download from {BASE_URL}{fname}")
        tables[key] = read_industry_table(p)

    archetypes = dict(sectors["archetypes"])
    archetypes["default"] = sectors["default"]
    out = {
        "generated_by": "python -m engine build-benchmarks",
        "generated_on": _dt.date.today().isoformat(),
        "provider": "Damodaran Online (Aswath Damodaran, NYU Stern), India industry averages",
        "datasets": {
            k: {
                "file": FILES[k],
                "source_url": BASE_URL + FILES[k],
                "local_copy": f"data/external/damodaran/{FILES[k]}",
                "date_updated": tables[k]["date_updated"],
            }
            for k in FILES
        },
        "derivation": {
            "relative_half_width": RELATIVE_HALF_WIDTH,
            "unit_floors": UNIT_FLOORS,
            "rule": "centre = industry value; h = max(rel x |centre|, floor); higher-better: red=c-h, green=c+h; lower-better: green=c-h, red=c+h",
        },
        "betas": {},
        "references": {},
        "bands": {},
    }
    for arch, spec in archetypes.items():
        inds = spec["damodaran_industries"]
        missing = [i for i in inds if i not in tables["margin"]["rows"]]
        if missing:
            raise ValueError(f"{arch}: industries not found in Damodaran India data: {missing}")
        bt = tables["beta"]
        out["betas"][arch] = {
            "industries": inds,
            "n_firms": [int(bt["rows"][i].get("Number of firms") or 0) for i in inds],
            "levered": _industry_value(tables, "beta", "Beta", inds),
            "unlevered_cash_corrected": _industry_value(tables, "beta", "Unlevered beta corrected for cash", inds),
            "unlevered": _industry_value(tables, "beta", "Unlevered beta", inds),
            "de_ratio": _industry_value(tables, "beta", "D/E Ratio", inds),
            "tax_rate": _industry_value(tables, "beta", "Effective Tax rate", inds),
            "source_url": BASE_URL + FILES["beta"],
            "as_of": tables["beta"]["date_updated"],
        }
        refs = {"industries": inds, "as_of": tables["margin"]["date_updated"]}
        for name, (ds, col) in REFERENCE_SPECS.items():
            refs[name] = _industry_value(tables, ds, col, inds)
        out["references"][arch] = refs

        bands = {}
        cogs = _industry_value(tables, "margin", "COGS/Sales", inds)
        for metric, (ds, col, transform, direction, unit) in BAND_SPECS.items():
            v = _industry_value(tables, ds, col, inds)
            if v is None or v == 0:  # Damodaran reports 0 for not-applicable fields (e.g. EBITDA for banks)
                continue
            if transform == "x365":
                v = v * 365.0
            elif transform == "x365_per_cogs":
                if not cogs or cogs < 0.05:
                    continue
                v = v * 365.0 / cogs
            if unit == "pct" and abs(v) > 5:  # guard against bad data
                continue
            b = derive_band(v, direction, unit)
            bands[metric] = {
                "centre": round(v, 6),
                "red": round(b["red"], 6),
                "green": round(b["green"], 6),
                "source_type": "external",
                "source_url": BASE_URL + FILES[ds],
                "as_of": tables[ds]["date_updated"],
                "derivation": f"Damodaran India '{col}' ({', '.join(inds)})"
                + (" x365" if transform == "x365" else "")
                + (" x365 / industry COGS/Sales" if transform == "x365_per_cogs" else "")
                + f"; amber zone = centre +/- max({int(RELATIVE_HALF_WIDTH*100)}%, {UNIT_FLOORS[unit]})",
            }
            if metric in BAND_NOTES:
                bands[metric]["note"] = BAND_NOTES[metric]
        # combined working-capital cycles from the same industry data
        if "dso" in bands:
            dso_c = bands["dso"]["centre"]
            dio_c = bands["dio"]["centre"] if "dio" in bands else 0.0
            combos = {"operating_cycle": dso_c + dio_c}
            if "dpo" in bands:
                combos["cash_conversion_cycle"] = dso_c + dio_c - bands["dpo"]["centre"]
            for metric, cval in combos.items():
                b = derive_band(cval, "lower", "days")
                bands[metric] = {
                    "centre": round(cval, 6), "red": round(b["red"], 6), "green": round(b["green"], 6),
                    "source_type": "external", "source_url": BASE_URL + FILES["wc"], "as_of": tables["wc"]["date_updated"],
                    "derivation": f"Industry receivable days + inventory days" + (" - payable days" if metric == "cash_conversion_cycle" else "")
                                  + f" ({', '.join(inds)}); amber zone = centre +/- max({int(RELATIVE_HALF_WIDTH*100)}%, 10 days)",
                }
        out["bands"][arch] = bands
    return out


def write(root: Path) -> Path:
    data = build(root)
    path = root / "config" / "sector_benchmarks.yaml"
    header = (
        "# GENERATED by `python -m engine build-benchmarks` from data/external/damodaran/*.xls.\n"
        "# Do not edit by hand: change config/sectors.yaml (industry mapping) or engine/benchmarks.py, then rebuild.\n"
    )
    path.write_text(header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=140))
    return path
