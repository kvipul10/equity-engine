"""Cost of capital from config/market.yaml (+ generated industry betas).

Ke  = rf + beta x ERP
Kd  = rf + default spread for the synthetic rating implied by interest cover (Damodaran table), after tax at the
      statutory rate
WACC = E/(D+E) x Ke + D/(D+E) x Kd x (1 - t), with E = market cap, D = borrowings (book, incl. leases)
beta: override > manual KPI 'beta' > bottom-up (industry unlevered, cash-corrected beta re-levered at the
      company's market D/E) for non-financials; industry levered beta for financials.
Historical years use rf_history[FY] when supplied, otherwise today's rf (reported in the output).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .standardise import Standardised


@dataclass
class CostOfCapital:
    rf: pd.Series
    erp: float
    tax: float
    beta: pd.Series
    ke: pd.Series
    kd_pre: pd.Series
    kd_post: pd.Series
    rating: pd.Series
    wd: pd.Series
    wacc: pd.Series
    current: Dict
    sources: Dict
    notes: List[str] = field(default_factory=list)


def rating_for(cover: float, table) -> (str, float):
    rating, spread = table[0][1], table[0][2]
    for lo, r, s in table:
        if cover >= lo:
            rating, spread = r, s
    return rating, float(spread)


def compute(std: Standardised, cfg, beta_override: Optional[float] = None) -> CostOfCapital:
    a = std.annual
    idx = list(a.index)
    notes: List[str] = []
    mk = cfg.market
    rf_now = float(cfg.mv("risk_free"))
    erp = float(cfg.mv("equity_risk_premium"))
    tax = float(cfg.mv("tax", "statutory_rate"))
    net_spread = bool(mk.get("rf_net_of_default_spread", False))
    sov = float(mk["equity_risk_premium"].get("components", {}).get("sovereign_default_spread", 0.0)) if net_spread else 0.0
    hist = mk.get("rf_history") or {}
    rf_vals = []
    used_hist = False
    for lab in idx:
        h = hist.get(lab)
        if isinstance(h, dict) and h.get("value") is not None:
            rf_vals.append(float(h["value"]) - sov)
            used_hist = True
        else:
            rf_vals.append(rf_now - sov)
    rf = pd.Series(rf_vals, index=idx, dtype=float)
    asof = std.meta.get("asof")
    if asof and not (isinstance(hist.get(asof), dict)):
        notes.append(f"As-of {asof}: no rf_history entry, so today's risk-free rate ({rf_now:.2%}, {mk['risk_free']['as_of']}) is used "
                     "- a look-ahead in the discount rate only (add rf_history in config/market.yaml to remove it).")
    elif not used_hist:
        notes.append(f"Historical years use today's risk-free rate ({rf_now:.2%}); add rf_history for year-specific rates.")
    if net_spread:
        notes.append(f"rf is net of India's sovereign default spread ({sov:.2%}).")

    fam = std.family
    betas = (cfg.sector.get("betas") or {})
    bi = betas.get(std.archetype) or betas.get("default") or {}
    override = beta_override
    src = "cli"
    if override is None:
        ov = (mk.get("beta") or {}).get("overrides") or {}
        if std.ticker in ov:
            override, src = float(ov[std.ticker]), "config override"
    if override is None and std.manual is not None and not std.manual.empty and "beta" in std.manual.columns:
        b = std.manual["beta"].dropna()
        if len(b):
            override, src = float(b.iloc[-1]), "manual KPI"

    mcap = pd.to_numeric(a["market_cap"], errors="coerce")
    debt = pd.to_numeric(a["borrowings"], errors="coerce")
    equity_book = pd.to_numeric(a["equity"], errors="coerce")
    cur_mcap = std.snapshot.get("market_cap") if std.snapshot else None
    if override is not None:
        beta = pd.Series(override, index=idx, dtype=float)
        beta_cur = float(override)
        beta_method = f"override ({src})"
    elif fam == "non_financial" and bi.get("unlevered_cash_corrected"):
        bu = float(bi["unlevered_cash_corrected"])
        e_w = mcap.where(mcap > 0, equity_book)
        de = (debt / e_w).clip(lower=0)
        beta = bu * (1 + (1 - tax) * de)
        de_cur = (debt.iloc[-1] / cur_mcap) if cur_mcap else de.iloc[-1]
        beta_cur = bu * (1 + (1 - tax) * max(de_cur, 0.0)) if not pd.isna(de_cur) else float(bi.get("levered", 1.0))
        beta_method = (f"bottom-up: unlevered {bu:.2f} ({', '.join(bi.get('industries', []))}) re-levered at market D/E")
    else:
        lev = float(bi.get("levered") or 1.0)
        beta = pd.Series(lev, index=idx, dtype=float)
        beta_cur = lev
        beta_method = f"industry levered beta {lev:.2f} ({', '.join(bi.get('industries', []))})"
    beta = beta.fillna(float(bi.get("levered") or 1.0))

    ke = rf + beta * erp
    ebit = pd.to_numeric(a["ebit_core"], errors="coerce")
    intr = pd.to_numeric(a["interest"], errors="coerce")
    table = mk["synthetic_rating"]["table"]
    ratings, spreads = [], []
    for e, i in zip(ebit, intr):
        if pd.isna(e) or pd.isna(i):
            ratings.append(None)
            spreads.append(np.nan)
            continue
        cover = 99.0 if i <= 1e-9 else e / i
        r, s = rating_for(cover, table)
        ratings.append(r)
        spreads.append(s)
    spread = pd.Series(spreads, index=idx, dtype=float)
    kd_pre = rf + spread
    kd_post = kd_pre * (1 - tax)
    e_w = mcap.where(mcap > 0, equity_book)
    wd = (debt / (debt + e_w)).where((debt + e_w) > 0)
    if fam == "non_financial":
        wacc = (1 - wd) * ke + wd * kd_post
    else:
        wacc = ke.copy()
        notes.append("Financial company: WACC not meaningful (deposits/borrowings are raw material); Ke is the hurdle rate.")
    # current (snapshot) values
    last = idx[-1]
    w_e = cur_mcap if cur_mcap else e_w.iloc[-1]
    d_last = debt.iloc[-1]
    wd_cur = d_last / (d_last + w_e) if (w_e and not pd.isna(d_last) and (d_last + w_e) > 0) else wd.iloc[-1]
    rf_cur = rf.iloc[-1]
    ke_cur = rf_cur + beta_cur * erp
    wacc_cur = (1 - wd_cur) * ke_cur + wd_cur * kd_post.iloc[-1] if fam == "non_financial" else ke_cur
    if fam == "non_financial" and pd.isna(wacc_cur):
        wacc_cur = ke_cur
    current = {
        "rf": rf_cur, "erp": erp, "beta": beta_cur, "beta_method": beta_method, "ke": ke_cur,
        "rating": ratings[-1], "kd_pre": kd_pre.iloc[-1], "kd_post": kd_post.iloc[-1], "wd": wd_cur, "wacc": wacc_cur,
        "tax": tax, "asof": last,
    }
    sources = {
        "risk_free": {k: mk["risk_free"].get(k) for k in ("value", "as_of", "source_url")},
        "equity_risk_premium": {k: mk["equity_risk_premium"].get(k) for k in ("value", "as_of", "source_url")},
        "tax": {k: mk["tax"]["statutory_rate"].get(k) for k in ("value", "as_of", "source_url")},
        "beta": {"method": beta_method, "source_url": bi.get("source_url"), "as_of": bi.get("as_of")},
        "synthetic_rating": {k: mk["synthetic_rating"].get(k) for k in ("as_of", "source_url")},
    }
    return CostOfCapital(rf=rf, erp=erp, tax=tax, beta=beta, ke=ke, kd_pre=kd_pre, kd_post=kd_post,
                         rating=pd.Series(ratings, index=idx, dtype=object), wd=wd, wacc=wacc, current=current,
                         sources=sources, notes=notes)
