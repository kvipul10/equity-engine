# Session 3 plan: Report

Sessions 1-2 are merged (`main` @ 01c2674). This session adds human-readable outputs on top of the existing
`analysis.json`: `report.html` and `analysis.xlsx` per company, plus `compare.html`. **No new metrics, scores or
thresholds**: the report presents what the engine already computes. The small additions to `analysis.json`
(peers, full driver leaves, findings) are listed in section 2. All text comes from deterministic templates
in `engine/report/templates/`.

## 1. Package layout

| Path | What |
|---|---|
| `engine/report/__init__.py` | Re-exports the current API (`build_report`, `write_outputs`, `console_summary`, `metrics_frame`, `out_dir_for`), so `engine.analysis` and `engine.cli` keep working |
| `engine/report/core.py` | Today's `engine/report.py` (JSON/CSV assembly), moved unchanged except the additions in section 2 |
| `engine/report/findings.py` | Strengths / Weaknesses / Watch ranking, driver chains, bull/bear starter, missing-data impact map |
| `engine/report/latex.py` | Deterministic converter from the registry's plain-text equations to LaTeX for KaTeX. Falls back to the plain text when it cannot parse one |
| `engine/report/charts.py` | Inline SVG (sparkline, band strip, waterfall, grouped bars). Pure Python, no JS chart library |
| `engine/report/html.py` | Renders `report.html` and `compare.html` with Jinja2 (autoescape on) |
| `engine/report/xlsx.py` | Writes `analysis.xlsx` with openpyxl |
| `engine/report/templates/` | `report.html.j2`, `compare.html.j2`, `_macros.j2`, `style.css`, `app.js` (inlined at render time), and `text.yaml` (every sentence template: verdict, findings, chains, missing-data lines, bull/bear bullets, empty-state messages) |

Also: rename `engine/templates.py` (the KPI-template writer) to `engine/kpi_templates.py`, and remove the empty
`engine/templates/` folder, so "templates" means one thing only.

## 2. Additions to analysis.json (computed in Python, so the HTML only renders)

- **`peers`**: same-archetype universe companies truncated to the same as-of year (the existing peer logic, so no
  look-ahead), with their latest values for every scored metric and for the valuation multiples. Each company
  also gets Damodaran India industry multiples (trailing P/E, P/BV, EV/EBITDA) from `sector_references`.
- **`drivers.*.windows.*.leaves`**: every leaf, not only the top 5, with its from/to values. This is needed for
  driver chains such as "DSO rose 60 → 85 days".
- **`flags.triggered[*].condition`**: the rule expression, and `applies`.
- **`findings`**: `strengths`, `weaknesses` and `watch` (6 each at most), `bull`, `bear`, and `missing_data`.
  Storing them in the JSON means tests can check them without parsing HTML.

## 3. report.html: sections

The file is self-contained: CSS, JS and SVG are all inline, with no external requests except KaTeX
(`cdn.jsdelivr.net/npm/katex@0.16.11`, pinned version). Offline, every equation still shows as plain text and
nothing else changes. The layout targets about 1100px on a laptop. Print CSS (A4) opens every collapsible
panel and driver window, hides the controls and avoids page breaks inside cards. RAG status is shown by colour
plus a text label, never by colour alone.

1. **Header**: company, ticker, archetype (and lineage), as-of year with the data window, overall score and RAG, and a one-line verdict. The verdict template is built from the root economic-profit result, the overall RAG, the strongest and weakest pillar, and the high-flag count.
2. **Strengths / Weaknesses / Watch**: at most 6 each, ranked by severity × confidence (definitions below). Each line gives the finding, the number, the trend and the driver chain, for example: "ROE −4.1 pts over 3y; 70% from asset turnover; asset turnover fell because DSO rose 60 → 85 days". Chains come from the driver decomposition: root change, then the largest contributing intermediate node and its share, then the largest leaf under it with its from/to values. The 3y window is used, falling back to 5y and then 1y. A metric with no tree node shows its own trend only.
3. **Interactive MECE tree**: root (economic profit = (ROIC − WACC) × IC), then Operations / Value and quality / Financing / Market, then the 8 pillars, coloured by RAG with their scores. Clicking a pillar opens its metrics. Each metric row shows:
   - a 10-year sparkline
   - its level vs band (red/green thresholds, band source and type, with indicative bands flagged) or vs peers (percentile and the peer values)
   - the trend label and slope
   - the equation (KaTeX) and the plain-English meaning
   Switched-off sector metrics are listed separately, with the reason each was switched off.
4. **Red flags fired**: id, name, pillar and severity, the rule (condition expression and origin file), the evidence numbers (the rule's `values`, formatted) and the explanation. Not-evaluable rules are in a collapsed list naming the missing input.
5. **Driver decomposition**: waterfall charts for ROE and ROIC over 1y, 3y and 5y, with tabs on screen and all three in print. Bars run start value, then contributions by the tree's first-level nodes, then end value, followed by the top-5 leaves table.
   - Banks: the ROE chart uses `bank_dupont`, or `fin_roe` when it falls back, and says so. The ROIC chart reads "not applicable for banks" (ROIC is switched off).
   - Any sector tree (e.g. real-estate CFO, order book) appears as an extra chart.
6. **Valuation box**:
   - P/E, P/B, EV/EBITDA and EV/Sales: current value vs own 10-year history (min, median, max, percentile, sparkline), vs peers, and vs the Damodaran industry multiple.
   - Reverse-DCF implied growth vs delivered growth: revenue CAGR 3/5/10y, NOPAT CAGR 5y and EPS CAGR, as a bar chart.
   - Justified P/B and (EV/IC)/(ROIC/WACC).
   - EV-based multiples are hidden for banks, and the box says why.
7. **Missing-data panel**: required KPIs absent at the as-of year, and how each limits the diagnosis. The limits come from a static dependency map built from the configs: sector-metric formulas (`kpi('x')`, `m('y')`, followed transitively), flag conditions (`kpi:x`, metric ids) and driver-tree nodes. Example: "provisions_cr missing → bank DuPont falls back to ROA = ROE/EM; credit cost and provisions/assets n/a; BK08 not evaluable". The panel also lists the share of unverified KPIs, estimated inputs taken from the data notes (e.g. the exceptional-item estimate), and metrics that are not scored.
8. **Bull and bear case starter**: financial evidence only, in bullets (6-8 each at most).
   - Bull: top strengths, positive driver contributions, value creation, a cheap multiple vs history or peers, implied growth below delivered growth.
   - Bear: weaknesses, fired flags, a rich multiple, implied growth above delivered growth, missing-data caveats.
   - Every bullet cites its metric or flag id. No strategy or management statements.

### Severity × confidence (proposed defaults; set in `config/scoring.yaml: report`)

- **Severity**
  - Metric: |composite − 50| / 50, times its pillar weight share (0-1), times 1.5 for role `scored` vs `info`.
  - Fired flag: high 1.0, medium 0.6, low 0.3.
- **Confidence** = data_coverage × source × input_quality.
  - data_coverage = min(1, years with data / 5).
  - source: external band 1.0, peer percentile 1.0, derived 0.9, indicative band 0.6.
  - input_quality: 0.8 if the metric uses an unverified manual KPI or an estimated input, else 1.0.
- **Lists**
  - Strengths: green metrics.
  - Weaknesses: red metrics and medium/high flags.
  - Watch: amber metrics with a deteriorating trend, green metrics deteriorating fast, red metrics improving, and low flags.
- **De-duplication**: at most 2 items per pillar per list. A metric already covered by a flag in the same list is dropped.

## 4. analysis.xlsx

- **Sheets**: `Summary` (overall, pillars, root, cost of capital), one sheet per pillar (`1 Growth` ... `8 Valuation`), `Flags` and `Drivers`.
- **Pillar sheets**: all metrics × years as real numbers with number formats (%, x, days, Rs cr), then latest value, RAG (cell fill and text), level basis, band red/green and its source, trend, stability, equation and meaning. Panes are frozen and the sheets filterable.
- **Flags**: every rule with its status, severity, pillar, condition, evidence values and text.
- **Drivers**: tree × window × node and leaf, with from/to values, contribution and share of the root.

## 5. compare.html

`python -m engine compare A B C [--asof FY26]` takes 2-5 tickers. Fewer or more is an error.

- Each ticker is analysed at its universe as-of year, unless `--asof` is given.
- The page shows a side-by-side table of the overall score and the 8 pillar scores and RAG, the root verdict and economic profit, a grouped-bar SVG of pillar scores, and the strongest and weakest metric per pillar per company.
- When archetypes differ, a note says that pillar weights and bands differ.
- Output goes to `reports/compare.html` and is overwritten on each run. The page is self-contained in the same way as report.html.

## 6. CLI

- `analyse` and `analyse-all` also write `report.html` and `analysis.xlsx` next to `analysis.json`. As-of runs go to the `asof_FYxx/` folder as today.
- New: `compare`. Existing commands are unchanged.

## 7. Tests (hand-computed expected values)

- **Ranking:** severity, confidence and their product for 4 synthetic metric/flag records, with the expected order and the per-pillar cap.
- **Driver chain:** text and shares for a hand-built window (e.g. ROE −4.1 pts, 70% asset turnover, DSO 60 → 85).
- **SVG geometry:** sparkline point coordinates for a known series, and waterfall bar positions and heights.
- **LaTeX converter:** exact output for sample equations. Every registry equation converts or falls back without error.
- **Missing-data map:** for the synthetic bank without `provisions_cr`, the expected set of affected metrics, flags and trees.
- **report.html for synthetic companies (non-financial, bank, real estate):**
  - all 8 section anchors present, and the 8 pillar nodes carry the RAG from the JSON
  - HTML parses with balanced tags
  - no external URL except the pinned KaTeX CDN
  - rendering twice gives byte-identical output
- **As-of:** the FY21 report for SYNTHCO contains no later year anywhere in the HTML or the xlsx.
- **analysis.xlsx:** sheet names, and cell values equal the JSON series.
- **compare:** the CLI accepts 2-5 tickers and rejects others, and the page shows each ticker's pillar scores.
- **Universe run:** all 21 companies write report.html and analysis.xlsx.

## 8. Order of work

1. Move to the `engine/report/` package (no behaviour change; the existing tests stay green).
2. JSON additions.
3. findings.py, latex.py, charts.py, with their tests.
4. Templates and html.py.
5. xlsx.py.
6. compare.
7. Docs: README usage, and a methodology section on the report.
8. Run the universe, run the tests, commit, push, open a PR titled "Session 3: Report", summarise.

## Decisions needed (defaults in bold)

1. Ranking definition: **as in section 3** (weights in config, easy to tune later).
2. Equations: **auto-convert the existing plain-text equations to LaTeX, with plain-text fallback**. The alternative is hand-written LaTeX for the 258 metrics.
3. Valuation peers: **same-archetype universe companies plus Damodaran India industry multiples**. Most archetypes have 0-2 universe peers.
4. compare as-of: **each ticker's universe as-of**, with an optional `--asof`.
5. Rename `engine/templates.py` → `engine/kpi_templates.py`: **yes**.
6. Add a `Summary` sheet to analysis.xlsx beyond the requested pillar, Flags and Drivers sheets: **yes**.
