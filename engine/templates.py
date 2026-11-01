"""Manual-KPI templates generated from the sector modules (so templates never drift from configs).

data/manual/templates/<archetype>_kpis.csv: one row per manual KPI (inherited ones included) x fiscal year,
columns metric,fiscal_year,value,unit,source_url,source_date,verified with value/source/date/verified blank.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from .standardise import fy_year, year_label

COLUMNS = ["metric", "fiscal_year", "value", "unit", "source_url", "source_date", "verified"]


def year_range(spec: str) -> List[str]:
    a, b = [x.strip().upper() for x in spec.split("-")]
    return [year_label(y) for y in range(fy_year(a), fy_year(b) + 1)]


def template_rows(sector, years: List[str]) -> List[List[str]]:
    rows = []
    kpis = sorted(sector.manual_kpis.values(), key=lambda k: (not k.get("required"), k["id"]))
    for k in kpis:
        for y in years:
            rows.append([k["id"], y, "", k["unit"], "", "", ""])
    return rows


def write_templates(cfg, years_spec: str = "FY22-FY26") -> List[Path]:
    years = year_range(years_spec)
    out_dir = cfg.paths.manual_dir / "templates"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for arch, sec in sorted(cfg.sectors.items()):
        p = out_dir / f"{arch}_kpis.csv"
        with p.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(COLUMNS)
            w.writerows(template_rows(sec, years))
        paths.append(p)
    return paths
