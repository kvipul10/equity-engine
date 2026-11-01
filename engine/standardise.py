"""Turn a RawExport into the canonical schema, logging every assumption.

Canonical annual table: one row per fiscal year (index 'FY17'...), same superset of columns for every
archetype (non-applicable columns are NaN). Flow items are annualised when a period is not 12 months.
Every rule that fires appends a note (category, fy, text) that is written to data/processed/<T>/notes.md.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .config import Config
from .ingest import RawExport, find_vintages, parse_workbook

FLOW_PNL = [
    "sales", "raw_material", "change_in_inventory", "power_fuel", "other_mfr", "employee_cost",
    "selling_admin", "other_exp", "other_income", "depreciation", "interest", "pbt", "tax", "net_profit", "dividend",
]
FLOW_CF = ["cfo", "cfi", "cff", "net_cash_flow"]
STOCK_BS = [
    "share_capital", "reserves", "borrowings", "other_liabilities", "total_liabilities", "net_block", "cwip",
    "investments", "other_assets", "total_assets", "receivables", "inventory", "cash",
]
BS_CORE = ["share_capital", "reserves", "borrowings", "other_liabilities", "net_block", "cwip", "investments", "other_assets"]
Q_FLOWS = ["sales", "expenses", "other_income", "depreciation", "interest", "pbt", "tax", "net_profit", "operating_profit"]

PNL_COLS = [
    "period_end", "period_months", "annualised", "revenue", "raw_material", "change_in_inventory", "materials_cost",
    "power_fuel", "other_mfr", "cogs", "employee_cost", "selling_admin", "other_exp", "other_opex", "total_opex",
    "ebitda", "other_income", "exceptional_est", "exceptional_tax", "other_income_core", "depreciation",
    "operating_ebit", "interest", "pbt", "pbt_core", "tax", "tax_core", "minority_and_associates", "pat",
    "pat_core", "ebit_core", "dividend", "nii", "net_total_income", "benefits", "opex_ex_benefits",
]
BS_COLS = [
    "period_end", "opening_fy", "stale_bs", "share_capital", "reserves", "equity", "borrowings", "other_liabilities",
    "total_liabilities", "net_block", "cwip", "investments", "other_assets", "receivables", "inventory", "cash",
    "other_assets_rest", "total_assets", "invested_capital", "net_debt", "nwc",
]
CF_COLS = ["period_end", "cfo", "cfi", "cff", "net_cash_flow", "capex_proxy", "capex_basis", "fcf", "non_capex_investing"]
MARKET_COLS = ["period_end", "price", "adjusted_shares_cr", "market_cap", "ev"]
SHARE_COLS = ["period_end", "shares_raw_cr", "face_value", "bonus_shares_cr", "adjusted_shares_cr", "adjustment_factor",
              "eps_core", "bvps", "revenue_per_share"]


def fy_label(ts: pd.Timestamp) -> str:
    return f"FY{ts.year % 100:02d}"


def fy_year(label: str) -> int:
    yy = int(str(label).upper().replace("FY", ""))
    return 1900 + yy if yy >= 70 else 2000 + yy


def year_label(year: int) -> str:
    return f"FY{year % 100:02d}"


def quarter_label(ts: pd.Timestamp) -> str:
    """Indian (April-March) fiscal quarter label, e.g. 2026-09-30 -> Q2FY27."""
    m, y = ts.month, ts.year
    q = {6: 1, 9: 2, 12: 3, 3: 4}.get(m)
    if q is None:  # non-standard quarter end
        q = (m - 4) // 3 % 4 + 1
    fy = y + 1 if m >= 4 else y
    return f"Q{q}FY{fy % 100:02d}"


def _months_between(a: pd.Timestamp, b: pd.Timestamp) -> int:
    return int(round((b - a).days / 30.4375))


def _fmt(x: float) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:,.0f}" if abs(x) >= 100 else f"{x:,.2f}"


@dataclass
class Standardised:
    ticker: str
    company: str
    archetype: str
    family: str
    annual: pd.DataFrame
    quarterly: pd.DataFrame
    snapshot: Dict
    manual: pd.DataFrame
    notes: List[Dict] = field(default_factory=list)
    meta: Dict = field(default_factory=dict)
    raw: Optional[RawExport] = None

    @property
    def years(self) -> List[str]:
        return list(self.annual.index)

    @property
    def last_fy(self) -> str:
        return self.annual.index[-1]


class _Notes(list):
    def add(self, category: str, text: str, fy: Optional[str] = None):
        self.append({"category": category, "fy": fy, "text": text})


# ---------------------------------------------------------------------------------------------------------
def load_manual(path: Path) -> pd.DataFrame:
    """data/manual/<TICKER>_kpis.csv (long format): period,kpi,value[,unit,source,note]."""
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, comment="#", dtype=str).fillna("")
    if df.empty:
        return pd.DataFrame()
    recs = []
    for _, r in df.iterrows():
        period = str(r.get("period", "")).strip()
        kpi = str(r.get("kpi", "")).strip()
        if not period or not kpi:
            continue
        try:
            val = float(str(r.get("value", "")).replace(",", ""))
        except ValueError:
            continue
        unit = str(r.get("unit", "")).strip()
        if unit == "%" or kpi.endswith("_pct"):
            val = val / 100.0
        p = period.upper()
        if p.startswith("FY"):
            fy, order = p, pd.Timestamp(fy_year(p), 3, 31)
        elif p.startswith("Q") and "FY" in p:
            fy = "FY" + p.split("FY")[1]
            q = int(p[1])
            order = pd.Timestamp(fy_year(fy) - 1, 3, 31) + pd.DateOffset(months=3 * q)
        else:
            ts = pd.Timestamp(period)
            fy = year_label(ts.year if ts.month <= 3 else ts.year + 1)
            order = ts
        recs.append({"fy": fy, "kpi": kpi, "value": val, "order": order, "source": r.get("source", "")})
    if not recs:
        return pd.DataFrame()
    m = pd.DataFrame(recs).sort_values("order")
    wide = m.groupby(["fy", "kpi"])["value"].last().unstack("kpi")
    wide = wide.loc[sorted(wide.index, key=fy_year)]
    return wide


# ---------------------------------------------------------------------------------------------------------
def standardise(raw: RawExport, archetype: str, cfg: Config, manual: Optional[pd.DataFrame] = None,
                vintages: Optional[List[RawExport]] = None) -> Standardised:
    notes = _Notes()
    family = cfg.family(archetype)
    stat_tax = float(cfg.mv("tax", "statutory_rate"))
    fin = family != "non_financial"

    notes.add("source", f"Source file {raw.path.name if raw.path else '(in-memory)'}; sha256 {raw.sha256[:16]}...; "
                        f"Screener template version {raw.version.get('current')}. Only the 'Data Sheet' is read "
                        f"(display sheets are formulas without cached values).")
    notes.add("units", f"Units: Rs {raw.units}" + ("" if raw.unit_scale == 1 else f" (scaled x{raw.unit_scale} to Rs crore)")
              + ". Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.")
    for w in raw.warnings:
        notes.add("source", w)
    for sec, lab in raw.unmapped:
        notes.add("source", f"Unmapped row '{lab}' in section {sec} (kept in raw_datasheet.csv only).")

    A = raw.annual.T.copy()  # index = period_end
    A = A.reindex(columns=sorted(set(A.columns) | set(FLOW_PNL + FLOW_CF + STOCK_BS + ["price", "adjusted_shares_cr", "shares_raw", "bonus_shares", "face_value"])))
    A = A.sort_index()

    # ---- activity masks & blanks ---------------------------------------------------------
    pnl_active = A[FLOW_PNL].notna().any(axis=1)
    bs_active = A[STOCK_BS].notna().any(axis=1)
    cf_active = A[FLOW_CF].notna().any(axis=1)
    keep = pnl_active | bs_active | cf_active
    for d in A.index[~keep]:
        notes.add("missing", f"Column dated {d.date()} has no data and is ignored.")
    A = A[keep]
    pnl_active, bs_active, cf_active = pnl_active[keep], bs_active[keep], cf_active[keep]
    for d in A.index:
        lab = fy_label(d)
        if pnl_active[d]:
            A.loc[d, FLOW_PNL] = A.loc[d, FLOW_PNL].fillna(0.0)
        else:
            notes.add("missing", "No P&L data for this year.", lab)
        if bs_active[d]:
            A.loc[d, STOCK_BS] = A.loc[d, STOCK_BS].fillna(0.0)
        else:
            notes.add("missing", "No balance-sheet data for this year.", lab)
        if cf_active[d]:
            A.loc[d, FLOW_CF] = A.loc[d, FLOW_CF].fillna(0.0)
        else:
            notes.add("missing", "No cash-flow data for this year.", lab)
    A["bonus_shares"] = A["bonus_shares"].fillna(0.0)
    notes.add("missing", "Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet "
                         "identities hold on that basis). Blank price or share count = missing.")

    # ---- stale / duplicated columns --------------------------------------------------------
    dates = list(A.index)
    stale_bs = pd.Series(False, index=A.index)
    stale_pnl = pd.Series(False, index=A.index)
    for i in range(1, len(dates)):
        d, p = dates[i], dates[i - 1]
        if bs_active[d] and bs_active[p]:
            cur, prev = A.loc[d, BS_CORE].astype(float), A.loc[p, BS_CORE].astype(float)
            if (cur != 0).sum() >= 3 and np.allclose(cur.values, prev.values, rtol=0, atol=1e-9):
                stale_bs[d] = True
        if pnl_active[d] and pnl_active[p]:
            cur, prev = A.loc[d, FLOW_PNL].astype(float), A.loc[p, FLOW_PNL].astype(float)
            if (cur != 0).sum() >= 3 and np.allclose(cur.values, prev.values, rtol=0, atol=1e-9):
                stale_pnl[d] = True
    for d in A.index[stale_bs]:
        notes.add("stale", f"Balance sheet dated {d.date()} is an exact copy of the previous column (no real balance sheet at this date); "
                           f"set to missing. The next period's opening balance is taken from the previous real balance sheet.", fy_label(d))
        A.loc[d, STOCK_BS] = np.nan
    for d in A.index[stale_pnl]:
        notes.add("stale", f"P&L dated {d.date()} is an exact copy of the previous column; set to missing.", fy_label(d))
        A.loc[d, FLOW_PNL] = np.nan

    # ---- FY labels ------------------------------------------------------------------------
    labels = [fy_label(d) for d in A.index]
    if len(set(labels)) != len(labels):
        seen = {}
        for d, lab in zip(A.index, labels):
            if lab in seen:
                notes.add("period", f"Two columns map to {lab} ({seen[lab].date()} and {d.date()}); keeping the later one.", lab)
            seen[lab] = d
        keep_dates = sorted(seen.values())
        A = A.loc[keep_dates]
        stale_bs, stale_pnl = stale_bs.loc[keep_dates], stale_pnl.loc[keep_dates]
        bs_active, pnl_active, cf_active = bs_active.loc[keep_dates], pnl_active.loc[keep_dates], cf_active.loc[keep_dates]
        labels = [fy_label(d) for d in A.index]
    if any(d.month != 3 for d in A.index):
        notes.add("period", "Some year-ends are not March: FY label = calendar year of the period end (e.g. Dec-2019 -> FY19). "
                            "Peer comparisons across different year-ends are approximate.")

    # ---- period length & opening balance pointer ------------------------------------------
    dates = list(A.index)
    months, opening = [], []
    for i, d in enumerate(dates):
        prev_ok = [x for x in dates[:i] if not stale_bs[x]]
        if i == 0:
            months.append(12)
            opening.append(None)
            continue
        if stale_bs[d]:
            mth = _months_between(dates[i - 1], d)
            op = fy_label(prev_ok[-1]) if prev_ok else None
        else:
            ref = prev_ok[-1] if prev_ok else dates[i - 1]
            mth = _months_between(ref, d)
            op = fy_label(ref) if bs_active.get(ref, False) and not stale_bs[ref] else None
        months.append(mth)
        opening.append(op)
    A["period_months"] = months
    A["opening_fy"] = opening
    for i, d in enumerate(dates):
        mth = months[i]
        if mth != 12:
            lab = labels[i]
            prev = dates[i - 1]
            ratio = (A.loc[d, "sales"] / A.loc[prev, "sales"]) if A.loc[prev, "sales"] else float("nan")
            notes.add("period", f"Period ending {d.date()} inferred as {mth} months (previous real balance sheet {A.loc[d, 'opening_fy'] or 'n/a'}); "
                                f"sales {_fmt(A.loc[d, 'sales'])} vs {_fmt(A.loc[prev, 'sales'])} in the preceding column "
                                f"(ratio {ratio:.2f}, vs {mth}/12 = {mth/12:.2f}). Flows annualised x12/{mth}.", lab)
            if stale_bs[prev]:
                notes.add("period", f"{lab} overlaps {labels[i-1]} (whose balance sheet is stale): year-on-year growth into {lab} "
                                    f"compares an annualised {mth}-month rate with a 12-month period and is understated/approximate.", lab)

    # ---- capex proxy on raw (unannualised) values ----------------------------------------
    capex = pd.Series(np.nan, index=A.index)
    basis = pd.Series("", index=A.index, dtype=object)
    by_label = dict(zip(labels, A.index))
    for d, lab in zip(A.index, labels):
        op = A.loc[d, "opening_fy"]
        if op and op in by_label and not pd.isna(A.loc[d, "net_block"]):
            o = by_label[op]
            capex[d] = (A.loc[d, "net_block"] - A.loc[o, "net_block"]) + (A.loc[d, "cwip"] - A.loc[o, "cwip"]) + A.loc[d, "depreciation"]
            basis[d] = "proxy"
    # ---- annualise flows ------------------------------------------------------------------
    raw_values = A.copy()
    factor = 12.0 / A["period_months"].astype(float)
    flows = FLOW_PNL + FLOW_CF
    A[flows] = A[flows].mul(factor, axis=0)
    capex = capex * factor
    A["annualised"] = A["period_months"] != 12

    # ---- build canonical annual frame ------------------------------------------------------
    S = pd.DataFrame(index=labels)
    S.index.name = "fy"
    g = lambda k: pd.Series(A[k].values, index=labels, dtype=float)
    S["period_end"] = [d.date().isoformat() for d in A.index]
    S["period_months"] = A["period_months"].values
    S["annualised"] = A["annualised"].values
    S["opening_fy"] = A["opening_fy"].values
    S["stale_bs"] = stale_bs.values
    S["revenue"] = g("sales")
    for k in ["raw_material", "change_in_inventory", "power_fuel", "other_mfr", "employee_cost", "selling_admin",
              "other_exp", "other_income", "depreciation", "interest", "pbt", "tax", "dividend"]:
        S[k] = g(k)
    S["materials_cost"] = S["raw_material"] - S["change_in_inventory"]
    S["cogs"] = S["materials_cost"] + S["power_fuel"] + S["other_mfr"]
    S["other_opex"] = S["power_fuel"] + S["other_mfr"] + S["selling_admin"] + S["other_exp"]
    S["total_opex"] = S["materials_cost"] + S["employee_cost"] + S["other_opex"]
    S["ebitda"] = S["revenue"] - S["total_opex"]
    S["operating_ebit"] = S["ebitda"] - S["depreciation"]
    S["pat"] = g("net_profit")
    S["minority_and_associates"] = S["pat"] - (S["pbt"] - S["tax"])

    # identity checks
    resid = S["ebitda"] + S["other_income"] - S["depreciation"] - S["interest"] - S["pbt"]
    for lab, r in resid.items():
        if not pd.isna(r) and abs(r) > max(0.5, 1e-3 * abs(S.loc[lab, "revenue"] or 0)):
            notes.add("identity", f"P&L identity residual {_fmt(r)}: Sales - Expenses + Other income - Depreciation - Interest != PBT.", lab)

    # negative cost lines (reclassification)
    for lab in labels:
        negs = [k for k in ["raw_material", "power_fuel", "other_mfr", "employee_cost", "selling_admin", "other_exp"]
                if not pd.isna(S.loc[lab, k]) and S.loc[lab, k] < 0]
        if negs:
            notes.add("reclassification", f"Negative cost line(s) {', '.join(f'{k}={_fmt(S.loc[lab, k])}' for k in negs)}: Screener "
                                          f"reclassification. Only materials, employee and the sum of all other cost lines (other_opex) are used.", lab)

    # ---- exceptional items (non-financials only) -----------------------------------------
    S["exceptional_est"] = 0.0
    if not fin:
        _estimate_exceptionals(S, notes)
    else:
        notes.add("exceptional", "Financial company: other income is core (fees, treasury), so no exceptional-item estimate is made.")
    if manual is not None and not manual.empty and "exceptional_items" in manual.columns:
        for lab, v in manual["exceptional_items"].dropna().items():
            if lab in S.index:
                S.loc[lab, "exceptional_est"] = v
                notes.add("manual", f"Exceptional items taken from manual KPI file: {_fmt(v)} (pre-tax).", lab)
    S["exceptional_tax"] = S["exceptional_est"] * stat_tax
    S["other_income_core"] = S["other_income"] - S["exceptional_est"]
    S["pbt_core"] = S["pbt"] - S["exceptional_est"]
    S["tax_core"] = S["tax"] - S["exceptional_tax"]
    S["pat_core"] = S["pat"] - S["exceptional_est"] + S["exceptional_tax"]
    S["ebit_core"] = S["pbt_core"] + S["interest"]

    # minority / associates
    mi = S["minority_and_associates"]
    nz = mi[(mi.abs() > 0.5)]
    if len(nz) >= 2:
        notes.add("minority", f"Net profit differs from PBT - tax in {len(nz)} of {len(mi.dropna())} years (latest {_fmt(mi.iloc[-1])}): "
                              "minority interest (negative) and share of associates/JVs (positive) sit between PBT and net profit, so the "
                              "export is consolidated and net profit is the owners' share. Equity excludes minority interest (Screener "
                              "includes NCI in Other Liabilities); ROIC/ROCE capital therefore omits NCI unless data/manual supplies "
                              "minority_interest.")
    else:
        notes.add("minority", "No material minority/associate residual: export is standalone or has no minorities.")

    # bank-like / insurance semantics
    if family == "bank_like":
        S["nii"] = S["revenue"] - S["interest"]
        S["net_total_income"] = S["nii"] + S["other_income"]
        notes.add("semantics", "Bank-like mapping: Sales = interest earned (NBFC: revenue from operations); Interest = interest expended; "
                               "Borrowings = deposits + borrowings (NBFC: borrowings); Other Assets include advances/loans; Other Expenses "
                               "include provisions & contingencies (credit costs are not separable in the export); CFO is driven by "
                               "loan/deposit flows and is not an earnings-quality signal.")
    else:
        S["nii"] = np.nan
        S["net_total_income"] = np.nan
    if family == "insurance":
        S["benefits"] = S["other_mfr"]
        S["opex_ex_benefits"] = S["total_opex"] - S["benefits"]
        notes.add("semantics", "Insurance mapping: Sales = premium + investment income; Other Mfr. Exp = benefits paid + change in "
                               "valuation of policy liabilities; Other Liabilities = policyholders' funds; Investments include "
                               "policyholders' investments.")
    else:
        S["benefits"] = np.nan
        S["opex_ex_benefits"] = np.nan
    if family == "non_financial":
        notes.add("semantics", "Screener puts exceptional items inside Other Income (PBT = Sales - Expenses + Other income - Dep - Interest "
                               "holds exactly). Other income is split into core and estimated exceptional (see 'exceptional').")

    # ---- balance sheet ---------------------------------------------------------------------
    for k in ["share_capital", "reserves", "borrowings", "other_liabilities", "total_liabilities", "net_block", "cwip",
              "investments", "other_assets", "receivables", "inventory", "cash", "total_assets"]:
        S[k] = g(k)
    S["equity"] = S["share_capital"] + S["reserves"]
    S["other_assets_rest"] = S["other_assets"] - S["receivables"] - S["inventory"] - S["cash"]
    S["invested_capital"] = S["equity"] + S["borrowings"] - S["cash"] - S["investments"]
    S["net_debt"] = S["borrowings"] - S["cash"]
    S["nwc"] = S["other_assets"] - S["cash"] - S["other_liabilities"]
    for lab in labels:
        if pd.isna(S.loc[lab, "total_assets"]):
            continue
        rl = S.loc[lab, ["share_capital", "reserves", "borrowings", "other_liabilities"]].sum() - S.loc[lab, "total_liabilities"]
        ra = S.loc[lab, ["net_block", "cwip", "investments", "other_assets"]].sum() - S.loc[lab, "total_assets"]
        rt = S.loc[lab, "total_liabilities"] - S.loc[lab, "total_assets"]
        tol = max(0.5, 1e-4 * abs(S.loc[lab, "total_assets"]))
        if abs(rl) > tol or abs(ra) > tol or abs(rt) > tol:
            notes.add("identity", f"Balance-sheet totals do not add up (liabilities {_fmt(rl)}, assets {_fmt(ra)}, L-A {_fmt(rt)}).", lab)
        if S.loc[lab, "other_assets_rest"] < -tol:
            notes.add("identity", f"Receivables + inventory + cash exceed Other Assets by {_fmt(-S.loc[lab, 'other_assets_rest'])}.", lab)

    # ---- cash flow -------------------------------------------------------------------------
    for k in FLOW_CF:
        S[k] = g(k)
    S["capex_proxy"] = capex.values
    S["capex_basis"] = basis.values
    if manual is not None and not manual.empty and "capex" in manual.columns:
        for lab, v in manual["capex"].dropna().items():
            if lab in S.index:
                S.loc[lab, "capex_proxy"] = v
                S.loc[lab, "capex_basis"] = "manual"
        notes.add("manual", "Capex taken from manual KPI file where provided.")
    notes.add("capex", "Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes "
                       "acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). "
                       "FCF = CFO - capex proxy.")
    S["fcf"] = S["cfo"] - S["capex_proxy"]
    S["non_capex_investing"] = -S["cfi"] - S["capex_proxy"]
    for lab in labels:
        r = S.loc[lab, ["cfo", "cfi", "cff"]].sum() - S.loc[lab, "net_cash_flow"]
        if not pd.isna(r) and abs(r) > 1.0:
            notes.add("identity", f"CFO + CFI + CFF differs from net cash flow by {_fmt(r)}.", lab)

    # ---- shares & market -------------------------------------------------------------------
    S["shares_raw_cr"] = g("shares_raw") / 1e7
    S["face_value"] = g("face_value")
    S["bonus_shares_cr"] = g("bonus_shares") / 1e7
    S["adjusted_shares_cr"] = g("adjusted_shares_cr")
    S["adjustment_factor"] = S["adjusted_shares_cr"] / S["shares_raw_cr"]
    sh = S["adjusted_shares_cr"].where(S["adjusted_shares_cr"] > 0)
    S["eps_core"] = S["pat_core"] / sh
    S["bvps"] = S["equity"] / sh
    S["revenue_per_share"] = S["revenue"] / sh
    S["price"] = g("price")
    S["market_cap"] = S["price"] * S["adjusted_shares_cr"]
    ev_inv = bool(cfg.mv("valuation", "ev_subtract_investments", default=True))
    S["ev"] = S["market_cap"] + S["borrowings"] - S["cash"] - (S["investments"] if ev_inv else 0.0)
    af = S["adjustment_factor"].dropna()
    if len(af) and (af.round(2) != 1.0).any():
        changes = [f"{lab} x{v:.2f}" for lab, v in af.items() if round(v, 2) != 1.0]
        notes.add("shares", "Per-share history is split/bonus/rights-adjusted by Screener (adjusted shares / reported shares: "
                            + ", ".join(changes) + "). EPS, BVPS, DPS and FY-end prices all use the adjusted basis, so ratios "
                            "are unaffected; per-share levels are in today's share units (a unit look-ahead, not an information look-ahead).")
    for lab in labels:
        if pd.isna(S.loc[lab, "price"]):
            notes.add("market", "No FY-end price (e.g. not yet listed): market multiples for this year are missing.", lab)

    # snapshot
    snap = {}
    if raw.asof_label:
        lab = raw.asof_label
        snap = {"basis": "fy_end_asof", "date": S.loc[lab, "period_end"], "price": float(S.loc[lab, "price"]),
                "shares_cr": float(S.loc[lab, "adjusted_shares_cr"]),
                "market_cap": float(S.loc[lab, "market_cap"])}
        notes.add("asof", f"As-of {lab}: annual data after {lab}, all later quarters and the export-date price are removed before "
                          f"standardisation; valuation uses the {lab} year-end price.")
    else:
        price, mcap = raw.meta.get("current_price"), raw.meta.get("market_cap")
        shares = (mcap / price) if (price and mcap) else None
        snap = {"basis": "export", "date": None, "price": price, "market_cap": mcap, "shares_cr": shares}
        last = labels[-1]
        if shares and not pd.isna(S.loc[last, "adjusted_shares_cr"]):
            diff = shares / S.loc[last, "adjusted_shares_cr"] - 1
            if abs(diff) > 0.10:
                notes.add("market", f"Current share count (market cap / price = {shares:,.2f} cr) differs from {last} adjusted shares "
                                    f"({S.loc[last, 'adjusted_shares_cr']:,.2f} cr) by {diff:+.0%}: corporate action after year-end or a unit issue.")
        notes.add("market", "Current price and market cap are as of the export date, which the file does not record "
                            "(latest quarter in file: " + (str(raw.quarterly.columns[-1].date()) if not raw.quarterly.empty else "n/a") + ").")

    # ---- Ind AS 116 and step changes (non-financials) ----------------------------------
    S["comparability_break"] = ""
    for i, (d, lab) in enumerate(zip(A.index, labels)):
        if i > 0 and stale_bs.iloc[i - 1] and S.loc[lab, "period_months"] != 12:
            S.loc[lab, "comparability_break"] = "period_change"
    if not fin:
        _detect_ind_as_116(S, A, labels, notes)
    _detect_step_changes(S, labels, notes)

    # ---- quarterly -------------------------------------------------------------------------
    Q = _standardise_quarters(raw, notes)

    # ---- manual KPIs -----------------------------------------------------------------------
    man = manual if manual is not None else pd.DataFrame()
    if not man.empty:
        notes.add("manual", f"Manual KPIs loaded: {', '.join(man.columns)} for {', '.join(man.index)}.")

    # ---- restatements (older exports in data/raw/screener/vintages/<TICKER>/) -------------
    if vintages:
        _compare_vintages(raw, vintages, notes)

    family_txt = {"non_financial": "non-financial", "bank_like": "bank-like", "insurance": "insurance"}[family]
    meta = {
        "ticker": raw.ticker, "company": raw.company, "archetype": archetype, "family": family_txt,
        "source_file": str(raw.path.name) if raw.path else None, "sha256": raw.sha256,
        "screener_version": raw.version.get("current"), "units": "Rs crore",
        "first_fy": labels[0], "last_fy": labels[-1], "n_years": len(labels),
        "latest_quarter": str(raw.quarterly.columns[-1].date()) if not raw.quarterly.empty else None,
        "consolidated_inferred": bool(len(nz) >= 2),
        "asof": raw.asof_label,
    }
    return Standardised(ticker=raw.ticker, company=raw.company, archetype=archetype, family=family, annual=S,
                        quarterly=Q, snapshot=snap, manual=man, notes=list(notes), meta=meta, raw=raw)


def _estimate_exceptionals(S: pd.DataFrame, notes: _Notes) -> None:
    """Exceptional items are inside Screener's Other Income. Flag a year when its other-income/sales ratio is a
    robust outlier versus the OTHER years available (leave-one-out median, sigma = 1.4826 x MAD, floored at 0.25%
    of sales) and the abnormal amount exceeds 5% of PBT; any negative other income is treated as exceptional."""
    rev, oi, pbt = S["revenue"], S["other_income"], S["pbt"]
    ratio = (oi / rev).where(rev > 0)
    found = []
    for lab in S.index:
        r = ratio.get(lab)
        if pd.isna(r):
            continue
        others = ratio.drop(lab).dropna()
        base = None
        if len(others) >= 3:
            base = float(others.median())
            sigma = max(1.4826 * float((others - base).abs().median()), 0.0025)
            dev = r - base
            amount = dev * rev[lab]
            if abs(dev) > 3 * sigma and abs(amount) > 0.05 * abs(pbt[lab] if pbt[lab] else 1.0):
                S.loc[lab, "exceptional_est"] = amount
                found.append((lab, amount, r, base))
                continue
        if oi[lab] < 0:
            amount = oi[lab] - (base * rev[lab] if base is not None else 0.0)
            S.loc[lab, "exceptional_est"] = amount
            found.append((lab, amount, r, base))
    for lab, amount, r, base in found:
        notes.add("exceptional", f"Estimated exceptional item {_fmt(amount)} (pre-tax, {'gain' if amount > 0 else 'loss'}): other income "
                                 f"{r:.1%} of sales vs normal {('n/a' if base is None else f'{base:.1%}')} (median of other years). "
                                 f"Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).", lab)
    if not found:
        notes.add("exceptional", "No exceptional items detected in other income (robust outlier test).")


def _detect_ind_as_116(S: pd.DataFrame, A: pd.DataFrame, labels: List[str], notes: _Notes) -> None:
    for i, (d, lab) in enumerate(zip(A.index, labels)):
        start = d - pd.DateOffset(months=int(S.loc[lab, "period_months"]))
        if start + pd.Timedelta(days=1) >= pd.Timestamp("2019-04-01"):
            if i == 0:
                return
            p = labels[i - 1]
            if pd.isna(S.loc[lab, "revenue"]) or pd.isna(S.loc[p, "revenue"]) or not S.loc[p, "revenue"]:
                return
            d_dep = S.loc[lab, "depreciation"] / S.loc[lab, "revenue"] - S.loc[p, "depreciation"] / S.loc[p, "revenue"]
            d_opex = S.loc[lab, "other_opex"] / S.loc[lab, "revenue"] - S.loc[p, "other_opex"] / S.loc[p, "revenue"]
            d_int = S.loc[lab, "interest"] / S.loc[lab, "revenue"] - S.loc[p, "interest"] / S.loc[p, "revenue"]
            if d_dep >= 0.003 and (d_opex <= -0.003 or d_int >= 0.001):
                S.loc[lab, "comparability_break"] = (S.loc[lab, "comparability_break"] + ";ind_as_116").strip(";")
                notes.add("lease", f"Ind AS 116 (leases) visible in {lab}, the first period starting on/after 1-Apr-2019: depreciation/sales "
                                   f"{d_dep:+.1%}, other opex/sales {d_opex:+.1%}, interest/sales {d_int:+.1%} vs {p}. Lease rentals moved "
                                   f"out of operating costs into depreciation and interest, so EBITDA margins before and after {lab} are "
                                   f"not comparable; lease liabilities sit inside Borrowings.", lab)
            else:
                notes.add("lease", f"Ind AS 116 adoption year {lab}: no visible step in depreciation/opex/interest ratios.", lab)
            return


def _detect_step_changes(S: pd.DataFrame, labels: List[str], notes: _Notes) -> None:
    S["inorganic_step"] = False
    for i in range(1, len(labels)):
        lab, p = labels[i], labels[i - 1]
        ta0, ta1 = S.loc[p, "total_assets"], S.loc[lab, "total_assets"]
        sh0, sh1 = S.loc[p, "adjusted_shares_cr"], S.loc[lab, "adjusted_shares_cr"]
        if any(pd.isna(x) for x in (ta0, ta1)) or not ta0:
            continue
        g_ta = ta1 / ta0 - 1
        g_sh = (sh1 / sh0 - 1) if (not pd.isna(sh0) and not pd.isna(sh1) and sh0) else float("nan")
        if g_ta >= 0.40 and not pd.isna(g_sh) and g_sh >= 0.10:
            S.loc[lab, "inorganic_step"] = True
            notes.add("merger", f"Balance-sheet step change: total assets {g_ta:+.0%} with adjusted share count {g_sh:+.0%} - likely a "
                                f"merger/acquisition paid in shares. Growth across {p}->{lab} is largely inorganic.", lab)
        elif g_ta >= 0.60:
            S.loc[lab, "inorganic_step"] = True
            notes.add("merger", f"Balance-sheet step change: total assets {g_ta:+.0%} in one year (acquisition, consolidation change or "
                                f"large capital raise). Growth across {p}->{lab} may not be organic.", lab)


def _standardise_quarters(raw: RawExport, notes: _Notes) -> pd.DataFrame:
    if raw.quarterly is None or raw.quarterly.empty:
        notes.add("quarterly", "No quarterly data in export (or none on/before the as-of date).")
        return pd.DataFrame()
    Q = raw.quarterly.T.copy().sort_index()
    Q = Q.reindex(columns=sorted(set(Q.columns) | set(Q_FLOWS)))
    active = Q[["sales", "net_profit"]].notna().any(axis=1)
    Q = Q[active]
    Q[Q_FLOWS] = Q[Q_FLOWS].fillna(0.0)
    out = pd.DataFrame(index=[d.date().isoformat() for d in Q.index])
    out.index.name = "quarter_end"
    out["fiscal_quarter"] = [quarter_label(d) for d in Q.index]
    out["revenue"] = Q["sales"].values
    out["expenses"] = Q["expenses"].values
    out["ebitda"] = Q["operating_profit"].values
    out["other_income"] = Q["other_income"].values
    out["depreciation"] = Q["depreciation"].values
    out["interest"] = Q["interest"].values
    out["pbt"] = Q["pbt"].values
    out["tax"] = Q["tax"].values
    out["pat"] = Q["net_profit"].values
    out["minority_and_associates"] = out["pat"] - (out["pbt"] - out["tax"])
    out["ebitda_margin"] = (out["ebitda"] / out["revenue"]).where(out["revenue"] > 0)
    resid = out["revenue"] - out["expenses"] - out["ebitda"]
    if (resid.abs() > 0.5).any():
        notes.add("quarterly", "Quarterly operating profit != sales - expenses in some quarters: " +
                  ", ".join(f"{q} {r:+.1f}" for q, r in resid[resid.abs() > 0.5].items()))
    gaps = []
    ds = list(Q.index)
    for a, b in zip(ds, ds[1:]):
        if _months_between(a, b) != 3:
            gaps.append(f"{a.date()}->{b.date()}")
    if gaps:
        notes.add("quarterly", "Non-consecutive quarters: " + ", ".join(gaps))
    notes.add("quarterly", f"{len(out)} quarters from {out.index[0]} to {out.index[-1]} ({out['fiscal_quarter'].iloc[0]}-"
                           f"{out['fiscal_quarter'].iloc[-1]}). Quarterly profit is as reported (no exceptional-item estimate).")
    return out


def _compare_vintages(raw: RawExport, vintages: List[RawExport], notes: _Notes) -> None:
    cur = raw.annual
    for v in vintages:
        common = [c for c in v.annual.columns if c in cur.columns]
        diffs = []
        for c in common:
            for k in ["sales", "pbt", "net_profit", "reserves", "borrowings", "total_assets", "cfo"]:
                a, b = cur.at[k, c] if k in cur.index else np.nan, v.annual.at[k, c] if k in v.annual.index else np.nan
                if pd.isna(a) or pd.isna(b) or b == 0:
                    continue
                if abs(a / b - 1) > 0.005:
                    diffs.append(f"{fy_label(c)} {k} {_fmt(b)} -> {_fmt(a)}")
        src = v.path.name if v.path else "vintage"
        if diffs:
            notes.add("restatement", f"Restated vs older export {src}: " + "; ".join(diffs[:20]) + (" ..." if len(diffs) > 20 else ""))
        else:
            notes.add("restatement", f"No restatements (>0.5%) vs older export {src} for overlapping years.")


# ---------------------------------------------------------------------------------------------------------
def load_standardised(ticker: str, cfg: Config, archetype: Optional[str] = None, asof: Optional[str] = None) -> Standardised:
    """Parse + (optionally truncate to as-of) + standardise. Always works from the raw file."""
    from .asof import truncate_manual, truncate_raw

    paths = cfg.paths
    path = paths.raw_file(ticker)
    if not path.exists():
        raise FileNotFoundError(f"No Screener export for {ticker} at {path}")
    raw = parse_workbook(path, ticker)
    arch = archetype or cfg.archetype_of(ticker)
    manual = load_manual(paths.manual_file(ticker))
    vint = [parse_workbook(p, ticker) for p in find_vintages(paths.vintages_dir, ticker)]
    if asof:
        raw = truncate_raw(raw, asof)
        manual = truncate_manual(manual, raw.asof_label)
        vint = []  # restatement comparison is a latest-data feature
    return standardise(raw, arch, cfg, manual=manual, vintages=vint)


def write_processed(std: Standardised, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    S = std.annual
    S.reindex(columns=PNL_COLS).to_csv(out_dir / "pnl.csv", float_format="%.4f")
    S.reindex(columns=BS_COLS).to_csv(out_dir / "balance_sheet.csv", float_format="%.4f")
    S.reindex(columns=CF_COLS).to_csv(out_dir / "cash_flow.csv", float_format="%.4f")
    mk = S.reindex(columns=MARKET_COLS).copy()
    snap = std.snapshot
    mk.loc["current"] = [snap.get("date") or "export date", snap.get("price"), snap.get("shares_cr"), snap.get("market_cap"), np.nan]
    mk.to_csv(out_dir / "market.csv", float_format="%.4f")
    S.reindex(columns=SHARE_COLS).to_csv(out_dir / "shares.csv", float_format="%.6f")
    if std.quarterly is not None and not std.quarterly.empty:
        std.quarterly.to_csv(out_dir / "quarterly.csv", float_format="%.4f")
    if std.raw is not None:
        rawdf = std.raw.annual.copy()
        rawdf.columns = [c.date().isoformat() for c in rawdf.columns]
        rawdf.to_csv(out_dir / "raw_datasheet.csv", float_format="%.4f")
    (out_dir / "meta.json").write_text(json.dumps(std.meta, indent=2, default=str))
    (out_dir / "notes.md").write_text(render_notes(std))


def render_notes(std: Standardised) -> str:
    m = std.meta
    lines = [f"# {m['ticker']} ({m['company']}): standardisation notes", "",
             f"- Archetype: `{m['archetype']}` ({m['family']}); years {m['first_fy']}-{m['last_fy']} ({m['n_years']}); "
             f"latest quarter {m['latest_quarter']}; consolidated (inferred): {m['consolidated_inferred']}",
             f"- Source: `{m['source_file']}` sha256 `{m['sha256'][:16]}...`, Screener template v{m['screener_version']}, units {m['units']}",
             ""]
    order = ["source", "units", "asof", "semantics", "period", "stale", "missing", "identity", "reclassification", "exceptional",
             "minority", "lease", "merger", "capex", "shares", "market", "quarterly", "manual", "restatement"]
    cats = {}
    for n in std.notes:
        cats.setdefault(n["category"], []).append(n)
    for c in order + sorted(set(cats) - set(order)):
        if c not in cats:
            continue
        lines.append(f"## {c}")
        for n in cats[c]:
            lines.append(f"- {'**' + n['fy'] + '**: ' if n['fy'] else ''}{n['text']}")
        lines.append("")
    return "\n".join(lines)
