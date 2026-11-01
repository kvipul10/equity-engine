"""As-of analysis without look-ahead.

The raw export is truncated BEFORE standardisation: annual columns after the as-of fiscal year, quarters
ending after that year-end, and the export-date price/market cap are dropped. Standardisation, metrics,
scoring, drivers and flags then run unchanged, so no later data can leak in by construction
(tests/test_asof.py proves it by scrambling all later data and comparing outputs).

as-of == the latest fiscal year in the file is treated as the normal ('latest') run: current price and all
quarters are kept.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .ingest import RawExport
from .standardise import fy_label, fy_year


def normalise_asof(asof: Optional[str]) -> Optional[str]:
    if asof is None:
        return None
    a = str(asof).strip().upper()
    if a in ("", "LATEST", "NONE"):
        return None
    if a.isdigit():  # 2018 -> FY18
        a = f"FY{int(a) % 100:02d}"
    if not a.startswith("FY"):
        raise ValueError(f"as-of must look like FY18 (got {asof})")
    return f"FY{int(a[2:]):02d}"


def available_fys(raw: RawExport):
    return [fy_label(d) for d in raw.annual.columns]


def is_latest(raw: RawExport, asof: Optional[str]) -> bool:
    a = normalise_asof(asof)
    return a is None or a == available_fys(raw)[-1]


def truncate_raw(raw: RawExport, asof: str) -> RawExport:
    a = normalise_asof(asof)
    labels = {fy_label(d): d for d in raw.annual.columns}
    if a is None or a == list(labels)[-1]:
        return raw
    if a not in labels:
        raise ValueError(f"{raw.ticker}: as-of {a} not in export (available: {', '.join(labels)})")
    cutoff = labels[a]
    r = raw.copy()
    r.annual = r.annual.loc[:, [c for c in r.annual.columns if c <= cutoff]]
    if r.quarterly is not None and not r.quarterly.empty:
        r.quarterly = r.quarterly.loc[:, [c for c in r.quarterly.columns if c <= cutoff]]
        if r.quarterly.shape[1] == 0:
            r.quarterly = pd.DataFrame()
    r.meta = dict(r.meta)
    r.meta["current_price"] = None
    r.meta["market_cap"] = None
    r.meta["number_of_shares"] = None
    r.section_dates = {k: [d for d in v if d <= cutoff] for k, v in r.section_dates.items()}
    r.asof_label = a
    return r


def truncate_manual(manual: pd.DataFrame, asof_label: Optional[str]) -> pd.DataFrame:
    if manual is None or manual.empty or not asof_label:
        return manual
    keep = [i for i in manual.index if fy_year(i) <= fy_year(asof_label)]
    return manual.loc[keep]
