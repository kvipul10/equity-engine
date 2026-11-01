"""Parse a Screener.in Excel export into raw tables.

Only the 'Data Sheet' is read: the other sheets (Profit & Loss, Quarters, Balance Sheet, Cash Flow) are
formulas that reference it and carry no cached values. Rows are located by LABEL inside each section
(PROFIT & LOSS, Quarters, BALANCE SHEET, CASH FLOW:, PRICE:, DERIVED:), never by fixed row numbers, and the
number of year columns is read from each section's 'Report Date' row. See docs/screener_format.md.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

SECTION_PATTERNS = [
    ("meta", re.compile(r"^meta$")),
    ("pnl", re.compile(r"^profit\s*(&|and)\s*loss$")),
    ("quarters", re.compile(r"^quarter(s|ly results)?$")),
    ("bs", re.compile(r"^balance\s*sheet$")),
    ("cf", re.compile(r"^cash\s*flow$")),
    ("price", re.compile(r"^price$")),
    ("derived", re.compile(r"^derived$")),
]

# (section, regex on normalised label, canonical key)
ROW_PATTERNS: Dict[str, List[Tuple[re.Pattern, str]]] = {
    "pnl": [
        (re.compile(r"^report date$"), "_date"),
        (re.compile(r"^(sales|revenue)$"), "sales"),
        (re.compile(r"^raw material"), "raw_material"),
        (re.compile(r"^change in inventor"), "change_in_inventory"),
        (re.compile(r"^power (and|&) fuel"), "power_fuel"),
        (re.compile(r"^other mfr"), "other_mfr"),
        (re.compile(r"^employee"), "employee_cost"),
        (re.compile(r"^selling (and|&) admin"), "selling_admin"),
        (re.compile(r"^other expenses?$"), "other_exp"),
        (re.compile(r"^other income$"), "other_income"),
        (re.compile(r"^depreciation"), "depreciation"),
        (re.compile(r"^interest$"), "interest"),
        (re.compile(r"^profit before tax$"), "pbt"),
        (re.compile(r"^tax$"), "tax"),
        (re.compile(r"^net profit$"), "net_profit"),
        (re.compile(r"^dividend amount$"), "dividend"),
    ],
    "quarters": [
        (re.compile(r"^report date$"), "_date"),
        (re.compile(r"^(sales|revenue)$"), "sales"),
        (re.compile(r"^expenses$"), "expenses"),
        (re.compile(r"^other income$"), "other_income"),
        (re.compile(r"^depreciation"), "depreciation"),
        (re.compile(r"^interest$"), "interest"),
        (re.compile(r"^profit before tax$"), "pbt"),
        (re.compile(r"^tax$"), "tax"),
        (re.compile(r"^net profit$"), "net_profit"),
        (re.compile(r"^operating profit$"), "operating_profit"),
    ],
    "bs": [
        (re.compile(r"^report date$"), "_date"),
        (re.compile(r"^equity share capital$"), "share_capital"),
        (re.compile(r"^reserves"), "reserves"),
        (re.compile(r"^borrowings$"), "borrowings"),
        (re.compile(r"^other liabilities$"), "other_liabilities"),
        (re.compile(r"^total$"), "_total"),
        (re.compile(r"^net block$"), "net_block"),
        (re.compile(r"^capital work in progress$"), "cwip"),
        (re.compile(r"^investments$"), "investments"),
        (re.compile(r"^other assets$"), "other_assets"),
        (re.compile(r"^receivables$"), "receivables"),
        (re.compile(r"^inventor(y|ies)$"), "inventory"),
        (re.compile(r"^cash (&|and) bank$"), "cash"),
        (re.compile(r"^no\.? of equity shares$"), "shares_raw"),
        (re.compile(r"^new bonus shares$"), "bonus_shares"),
        (re.compile(r"^face value$"), "face_value"),
    ],
    "cf": [
        (re.compile(r"^report date$"), "_date"),
        (re.compile(r"^cash from operating"), "cfo"),
        (re.compile(r"^cash from investing"), "cfi"),
        (re.compile(r"^cash from financing"), "cff"),
        (re.compile(r"^net cash flow$"), "net_cash_flow"),
    ],
    "derived": [
        (re.compile(r"^adjusted equity shares in (cr|crores?)$"), "adjusted_shares_cr"),
    ],
}

META_PATTERNS = [
    (re.compile(r"^company name$"), "company_name"),
    (re.compile(r"^latest version$"), "latest_version"),
    (re.compile(r"^current version$"), "current_version"),
    (re.compile(r"^number of shares$"), "number_of_shares"),
    (re.compile(r"^face value$"), "face_value"),
    (re.compile(r"^current price$"), "current_price"),
    (re.compile(r"^market capitali[sz]ation$"), "market_cap"),
]

UNIT_PATTERNS = [
    (re.compile(r"\b(rs\.?|inr|₹)?\s*(in\s+)?millions?\b", re.I), "million", 0.1),
    (re.compile(r"\b(rs\.?|inr|₹)?\s*(in\s+)?lakhs?\b|\blacs\b", re.I), "lakh", 0.01),
    (re.compile(r"\b(rs\.?|inr|₹)?\s*(in\s+)?billions?\b", re.I), "billion", 100.0),
]


def norm_label(v) -> str:
    s = str(v).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(":").rstrip(".").strip()
    return s


def _to_float(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float, np.integer, np.floating)):
        f = float(v)
        return None if np.isnan(f) else f
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if not s or s.startswith("="):
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _to_date(v) -> Optional[pd.Timestamp]:
    if isinstance(v, (_dt.datetime, _dt.date)):
        return pd.Timestamp(v).normalize()
    if isinstance(v, str):
        try:
            return pd.Timestamp(v).normalize()
        except Exception:
            return None
    return None


@dataclass
class RawExport:
    ticker: str
    path: Optional[Path]
    sha256: str
    company: str
    version: Dict[str, Optional[str]]
    meta: Dict[str, Optional[float]]
    annual: pd.DataFrame  # index = canonical keys, columns = period-end Timestamps (ascending)
    quarterly: pd.DataFrame  # index = canonical keys, columns = quarter-end Timestamps (ascending)
    label_map: Dict[str, str] = field(default_factory=dict)
    unmapped: List[Tuple[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    units: str = "crore"
    unit_scale: float = 1.0
    section_dates: Dict[str, List[pd.Timestamp]] = field(default_factory=dict)
    asof_label: Optional[str] = None  # set by asof.truncate_raw

    def copy(self) -> "RawExport":
        import copy as _copy

        return _copy.deepcopy(self)


def _find_sheet(wb, name: str):
    for ws in wb.worksheets:
        if ws.title.strip().lower() == name.lower():
            return ws
    raise ValueError(f"No '{name}' sheet found (sheets: {[w.title for w in wb.worksheets]})")


def parse_workbook(path: Path, ticker: Optional[str] = None) -> RawExport:
    import openpyxl

    path = Path(path)
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    wb = openpyxl.load_workbook(path, data_only=True, read_only=False)
    ws = _find_sheet(wb, "Data Sheet")
    grid = [[c for c in row] for row in ws.iter_rows(values_only=True)]
    raw = parse_grid(grid, ticker or path.stem, path=path, sha256=sha)
    # formula cells without cached values (e.g. 'Number of shares' = B9/B8) come through as None.
    wbf = openpyxl.load_workbook(path, data_only=False, read_only=False)
    wsf = _find_sheet(wbf, "Data Sheet")
    n_formula = sum(
        1 for row in wsf.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")
    )
    if n_formula:
        raw.warnings.append(
            f"Data Sheet has {n_formula} formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed."
        )
    return raw


def parse_grid(grid: List[List], ticker: str, path: Optional[Path] = None, sha256: str = "") -> RawExport:
    meta: Dict[str, Optional[float]] = {}
    company = ""
    version: Dict[str, Optional[str]] = {"latest": None, "current": None}
    section: Optional[str] = None
    dates: Dict[str, List[Tuple[int, pd.Timestamp]]] = {}
    values: Dict[str, Dict[str, Dict[int, Optional[float]]]] = {}
    label_map: Dict[str, str] = {}
    unmapped: List[Tuple[str, str]] = []
    warnings: List[str] = []
    bs_total_seen = 0
    unit_hits = []

    for row in grid:
        if not row:
            continue
        a = row[0]
        rest = list(row[1:])
        for cell in row:
            if isinstance(cell, str):
                for pat, unit, scale in UNIT_PATTERNS:
                    if pat.search(cell):
                        unit_hits.append((unit, scale, cell))
        if a is None or (isinstance(a, str) and not a.strip()):
            continue
        lab = norm_label(a)
        # section header?
        sec_hit = None
        for name, pat in SECTION_PATTERNS:
            if pat.match(lab):
                sec_hit = name
                break
        if sec_hit:
            section = sec_hit
            if sec_hit == "bs":
                bs_total_seen = 0
            if sec_hit == "price":
                values.setdefault("price", {})["price"] = {
                    i: _to_float(v) for i, v in enumerate(rest, start=1) if v is not None
                }
                label_map["price"] = str(a).strip()
            continue
        if section in (None, "meta"):
            for pat, key in META_PATTERNS:
                if pat.match(lab):
                    if key == "company_name":
                        company = str(rest[0]).strip() if rest and rest[0] is not None else ""
                    elif key in ("latest_version", "current_version"):
                        version[key.split("_")[0]] = None if not rest or rest[0] is None else str(rest[0])
                    else:
                        meta[key] = _to_float(rest[0]) if rest else None
                    break
            continue
        patterns = ROW_PATTERNS.get(section, [])
        key = None
        for pat, k in patterns:
            if pat.match(lab):
                key = k
                break
        if key is None:
            if any(v is not None for v in rest):
                unmapped.append((section, str(a).strip()))
            continue
        if key == "_date":
            ds = [(i, _to_date(v)) for i, v in enumerate(rest, start=1)]
            dates[section] = [(i, d) for i, d in ds if d is not None]
            continue
        if key == "_total":
            bs_total_seen += 1
            key = "total_liabilities" if bs_total_seen == 1 else "total_assets"
        vals = {i: _to_float(v) for i, v in enumerate(rest, start=1)}
        values.setdefault(section, {})[key] = vals
        label_map.setdefault(key, str(a).strip())

    # ---- assemble annual table ----------------------------------------------------------
    if "pnl" not in dates:
        raise ValueError(f"{ticker}: no 'Report Date' row found in PROFIT & LOSS section")
    col_dates: Dict[pd.Timestamp, Dict[str, Optional[float]]] = {}
    section_dates: Dict[str, List[pd.Timestamp]] = {}
    for sec in ("pnl", "bs", "cf"):
        if sec not in dates:
            warnings.append(f"Section '{sec}' has no Report Date row; its values are ignored.")
            continue
        section_dates[sec] = [d for _, d in dates[sec]]
        for key, vals in values.get(sec, {}).items():
            for i, d in dates[sec]:
                col_dates.setdefault(d, {})[key] = vals.get(i)
    # PRICE and DERIVED rows carry no dates: they share the P&L column positions.
    for sec, keys in (("price", ["price"]), ("derived", ["adjusted_shares_cr"])):
        for key in keys:
            vals = values.get(sec, {}).get(key)
            if vals is None:
                warnings.append(f"Row '{key}' not found in export.")
                continue
            for i, d in dates["pnl"]:
                col_dates.setdefault(d, {})[key] = vals.get(i)
    if section_dates.get("bs") and section_dates.get("pnl") and section_dates["bs"] != section_dates["pnl"]:
        warnings.append("Balance-sheet dates differ from P&L dates; aligned by date.")
    if section_dates.get("cf") and section_dates.get("pnl") and section_dates["cf"] != section_dates["pnl"]:
        warnings.append("Cash-flow dates differ from P&L dates; aligned by date.")
    annual = pd.DataFrame(col_dates).sort_index(axis=1).astype(float)

    qcols: Dict[pd.Timestamp, Dict[str, Optional[float]]] = {}
    if "quarters" in dates:
        section_dates["quarters"] = [d for _, d in dates["quarters"]]
        for key, vals in values.get("quarters", {}).items():
            for i, d in dates["quarters"]:
                qcols.setdefault(d, {})[key] = vals.get(i)
    quarterly = pd.DataFrame(qcols).sort_index(axis=1).astype(float) if qcols else pd.DataFrame()

    units, scale = "crore", 1.0
    if unit_hits:
        units, scale = unit_hits[0][0], unit_hits[0][1]
        warnings.append(f"Unit label found: '{unit_hits[0][2]}' -> values scaled to Rs crore (x{scale}).")
        num_keys = [k for k in annual.index if k not in ("shares_raw", "bonus_shares", "face_value", "price", "adjusted_shares_cr")]
        annual.loc[num_keys] = annual.loc[num_keys] * scale
        if not quarterly.empty:
            quarterly = quarterly * scale
        if meta.get("market_cap") is not None:
            meta["market_cap"] = meta["market_cap"] * scale

    if version.get("latest") and version.get("current") and version["latest"] != version["current"]:
        warnings.append(f"Screener template version {version['current']} differs from latest {version['latest']}.")
    return RawExport(
        ticker=ticker,
        path=path,
        sha256=sha256,
        company=company,
        version=version,
        meta=meta,
        annual=annual,
        quarterly=quarterly,
        label_map=label_map,
        unmapped=unmapped,
        warnings=warnings,
        units=units,
        unit_scale=scale,
        section_dates=section_dates,
    )


def find_vintages(vintages_dir: Path, ticker: str) -> List[Path]:
    d = vintages_dir / ticker
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.xlsx") if not p.name.startswith("~$"))
