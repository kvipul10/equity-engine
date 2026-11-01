"""analysis.xlsx: Summary, one sheet per pillar (all metrics x years as numbers), Flags, Drivers (openpyxl)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..registry import PILLAR_NAMES, PILLARS

NUMBER_FORMATS = {"pct": "0.0%", "pp": '+0.0"pp";-0.0"pp";0.0"pp"', "x": '0.00"x"', "days": "0", "inr_cr": "#,##0",
                  "inr": "#,##0", "count": "#,##0", "ratio": "0.00", "num": "0.00", "score": "0.00",
                  "days_of_sales": "0.000"}
FILLS = {"green": PatternFill("solid", fgColor="E3F4EA"), "amber": PatternFill("solid", fgColor="FDF1DC"),
         "red": PatternFill("solid", fgColor="FDE7E4")}
BOLD = Font(bold=True)
HEAD_FILL = PatternFill("solid", fgColor="EEF0F3")


def sheet_name(p: str) -> str:
    """'1 Growth' ... '8 Valuation' (the registry's names, so sheet names are stable across sectors; max 31 chars)."""
    return PILLAR_NAMES[p][:31]


def _header(ws, cols: List[str]) -> None:
    ws.append(cols)
    for c in ws[1]:
        c.font = BOLD
        c.fill = HEAD_FILL
        c.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "B2"


def _widths(ws, widths: Dict[int, float]) -> None:
    for i, w in widths.items():
        ws.column_dimensions[get_column_letter(i)].width = w


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _summary(wb: Workbook, rep: Dict) -> None:
    ws = wb.active
    ws.title = "Summary"
    c, a, ov, root, coc = rep["company"], rep["asof"], rep["overall"], rep.get("root") or {}, rep.get("cost_of_capital") or {}
    rows = [("Company", c["name"]), ("Ticker", c["ticker"]), ("Archetype", c["archetype"]), ("Family", c["family"]),
            ("As of", a["fy"]), ("Mode", a["mode"]), ("Data window", a["data_window"]),
            ("Overall score", _num(ov.get("score"))), ("Overall RAG", ov.get("rag")),
            ("Verdict", (rep.get("findings") or {}).get("verdict", "")), ("Economic profit (Rs cr)", _num(root.get("economic_profit"))),
            ("Return metric", root.get("return_metric")), ("Return", _num(root.get("return"))),
            ("Hurdle", root.get("hurdle_metric")), ("Hurdle rate", _num(root.get("hurdle"))),
            ("WACC", _num(coc.get("wacc"))), ("Cost of equity", _num(coc.get("ke"))), ("Beta", _num(coc.get("beta"))),
            ("Risk-free rate", _num(coc.get("rf"))), ("Equity risk premium", _num(coc.get("erp")))]
    for k, v in rows:
        ws.append([k, v])
        ws.cell(ws.max_row, 1).font = BOLD
    for r in range(1, ws.max_row + 1):
        if ws.cell(r, 1).value in ("Return", "Hurdle rate", "WACC", "Cost of equity", "Risk-free rate", "Equity risk premium"):
            ws.cell(r, 2).number_format = "0.0%"
        if ws.cell(r, 1).value == "Economic profit (Rs cr)":
            ws.cell(r, 2).number_format = "#,##0"
    ws.append([])
    ws.append(["Pillar", "Score", "RAG", "Weight", "Scored metrics", "Metrics", "Flags", "Summary"])
    for cell in ws[ws.max_row]:
        cell.font = BOLD
        cell.fill = HEAD_FILL
    for p in PILLARS:
        pv = rep["pillars"][p]
        ws.append([pv["name"], _num(pv.get("score")), pv.get("rag"), _num(pv.get("weight")), pv.get("n_scored"),
                   pv.get("n_metrics"), ", ".join(pv.get("flags_triggered", [])), pv.get("summary", "")])
        if pv.get("rag") in FILLS:
            ws.cell(ws.max_row, 3).fill = FILLS[pv["rag"]]
        ws.cell(ws.max_row, 2).number_format = "0"
    f = rep.get("findings") or {}
    for title, key in (("Strengths", "strengths"), ("Weaknesses", "weaknesses"), ("Watch", "watch"),
                       ("Bull case evidence", "bull"), ("Bear case evidence", "bear")):
        ws.append([])
        ws.append([title])
        ws.cell(ws.max_row, 1).font = BOLD
        for it in f.get(key, []):
            ws.append(["", it["text"]])
    _widths(ws, {1: 34, 2: 60, 3: 10, 4: 8, 5: 9, 6: 9, 7: 14, 8: 90})


def _pillar_sheet(wb: Workbook, rep: Dict, p: str, years: List[str]) -> None:
    ws = wb.create_sheet(sheet_name(p))
    cols = (["Metric id", "Name", "Role", "Unit", "Direction"] + years +
            ["Latest", "RAG", "Composite", "Level basis", "Band red", "Band green", "Band source type", "Band origin",
             "Band source URL", "Trend", "Trend slope / yr", "Trend window", "Stability", "Equation", "Meaning", "Note"])
    _header(ws, cols)
    ny = len(years)
    for mid in rep["pillars"][p].get("metrics", []):
        m = rep["metrics"][mid]
        b, t, stb = m.get("band") or {}, m.get("trend") or {}, m.get("stability") or {}
        row = ([mid, m["name"], m.get("role"), m["unit"], m.get("direction")] +
               [_num((m.get("series") or {}).get(y)) for y in years] +
               [_num(m.get("value")), m.get("rag"), _num(m.get("composite")), (m.get("level") or {}).get("basis"),
                _num(b.get("red")), _num(b.get("green")), b.get("source_type"), b.get("origin"), b.get("source_url"),
                t.get("label"), _num(t.get("slope_per_year")), t.get("window"), stb.get("label"),
                m.get("equation"), m.get("meaning"), m.get("note") or m.get("reason")])
        ws.append(row)
        r = ws.max_row
        nf = NUMBER_FORMATS.get(m["unit"], "0.00")
        for ci in list(range(6, 6 + ny)) + [6 + ny, 6 + ny + 4, 6 + ny + 5, 6 + ny + 10]:
            ws.cell(r, ci).number_format = nf
        ws.cell(r, 6 + ny + 2).number_format = "0"
        if m.get("rag") in FILLS:
            ws.cell(r, 6 + ny + 1).fill = FILLS[m["rag"]]
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(ws.max_row, 1)}"
    ws.freeze_panes = "C2"
    _widths(ws, {1: 26, 2: 34, 3: 10, 4: 7, 5: 9, **{6 + i: 10 for i in range(ny + 1)},
                 6 + ny + 1: 8, 6 + ny + 6: 12, 6 + ny + 7: 26, 6 + ny + 13: 60, 6 + ny + 14: 60})


def _flags(wb: Workbook, rep: Dict, cfg=None) -> None:
    ws = wb.create_sheet("Flags")
    _header(ws, ["Rule", "Name", "Status", "Severity", "Pillar", "Origin", "Condition", "Evidence", "Explanation / missing input"])
    rules = {r["id"]: r for r in (cfg.rules_for(rep["company"]["archetype"]) if cfg is not None else [])}
    fl = rep.get("flags") or {}
    for f in fl.get("triggered", []):
        ev = "; ".join(f"{k} = {v:.6g}" if isinstance(v, (int, float)) else f"{k} = {v}" for k, v in (f.get("values") or {}).items())
        ws.append([f["id"], f["name"], "triggered", f["severity"], f["pillar"], f.get("origin"), f.get("condition"), ev, f.get("text")])
        ws.cell(ws.max_row, 3).fill = FILLS["red" if f["severity"] == "high" else "amber"]
    for f in fl.get("not_evaluable", []):
        r = rules.get(f["id"], {})
        ws.append([f["id"], f["name"], "not evaluable", r.get("severity"), r.get("pillar"), r.get("_origin"), r.get("condition"), "", f.get("missing")])
    for fid in fl.get("clear", []):
        r = rules.get(fid, {})
        ws.append([fid, r.get("name"), "clear", r.get("severity"), r.get("pillar"), r.get("_origin"), r.get("condition"), "", ""])
    ws.auto_filter.ref = f"A1:I{max(ws.max_row, 1)}"
    _widths(ws, {1: 8, 2: 40, 3: 13, 4: 9, 5: 18, 6: 28, 7: 60, 8: 40, 9: 90})


def _drivers(wb: Workbook, rep: Dict) -> None:
    ws = wb.create_sheet("Drivers")
    _header(ws, ["Tree", "Window", "From", "To", "Status / note", "Node", "Name", "Leaf", "Path", "Unit", "Value from",
                 "Value to", "Change", "Contribution to root", "Share of root change"])
    for tid, t in (rep.get("drivers") or {}).items():
        for w, win in t["windows"].items():
            if win.get("status") != "ok":
                ws.append([tid, w, None, None, f"n/a: {win.get('reason')}"])
                continue
            note = "ok" + (f"; residual {win.get('residual'):.3g}" if abs(win.get("residual") or 0) > 1e-12 else "")
            nodes = win.get("nodes") or {}
            for n, v in sorted(nodes.items(), key=lambda x: (x[1]["path"].count(" > "), x[1]["path"])):
                ws.append([tid, w, win["from"], win["to"], note, n, v["name"], "leaf" if v["leaf"] else "node", v["path"], v["unit"],
                           _num(v["t0"]), _num(v["t1"]), _num(v["change"]), _num(v["contribution"]), _num(v["share_of_root"])])
                ws.cell(ws.max_row, 15).number_format = "0%"
    ws.auto_filter.ref = f"A1:O{max(ws.max_row, 1)}"
    _widths(ws, {1: 14, 2: 7, 3: 7, 4: 7, 5: 18, 6: 24, 7: 30, 8: 6, 9: 60, 10: 12})


def write_xlsx(rep: Dict, out_dir: Path, cfg=None) -> Path:
    years: List[str] = []
    for m in rep["metrics"].values():
        if m.get("series"):
            years = list(m["series"].keys())
            break
    wb = Workbook()
    _summary(wb, rep)
    for p in PILLARS:
        _pillar_sheet(wb, rep, p, years)
    _flags(wb, rep, cfg)
    _drivers(wb, rep)
    p = Path(out_dir) / "analysis.xlsx"
    wb.save(p)
    return p
