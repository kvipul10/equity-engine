# Equity Diagnostic Engine

Takes a **Screener.in Excel export** of an Indian listed company and works out, quantitatively, what the company is doing right and wrong financially, and why. The analysis is MECE: one root question split into eight pillars.

```
Root: does the company create value?   economic profit = (ROIC - WACC) x invested capital
├─ Operations          1 Growth · 2 Margins · 3 Capital efficiency
├─ Value and quality   4 Returns (DuPont, ROIC) · 5 Cash and earnings quality
├─ Financing           6 Balance sheet · 7 Capital allocation
└─ Market              8 Valuation
```

- **Offline and deterministic.** It runs offline on a Mac with Python 3 and makes no paid API or LLM calls. All text comes from fixed templates.
- **Financials only.** It diagnoses the numbers; strategy and management judgement stay with you.
- **What you get per company:**
  - every metric with a green/amber/red verdict (level vs peers or sourced bands, trend, stability)
  - pillar and overall scores
  - DuPont and ROIC driver trees that decompose 1/3/5-year changes down to individual cost lines and working-capital days
  - 54 red-flag rules
  - a no-look-ahead **as-of** mode for blow-up back-tests

## Setup (Mac)

```bash
cd ~/path/to/equity-engine
```

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

After setup, everything runs offline. The requirements are pandas, numpy, openpyxl, pyyaml and jinja2; pytest is for the tests, and xlrd is used only to rebuild sector benchmarks.

## Usage

Analyse one company. This writes `reports/<TICKER>/report.html`, `analysis.xlsx`, `analysis.json` and `metrics.csv`:

```bash
python -m engine analyse TCS
```

As-of analysis uses only data up to that fiscal year. Output goes to `reports/<TICKER>/asof_FY18/`:

```bash
python -m engine analyse YESBANK --asof FY18
```

Analyse the whole universe in `data/universe.csv`, each company at its own `asof`. This also writes `reports/universe_summary.csv`:

```bash
python -m engine analyse-all
```

Parse and standardise only, into `data/processed/<TICKER>/` (CSVs + `notes.md`):

```bash
python -m engine ingest --all
```

Compare 2-5 companies side by side. This writes `reports/compare.html`. Each company is taken at its universe as-of year; `--asof FY24` sets a common year:

```bash
python -m engine compare TCS INFY HDFCBANK
```

List the metric registry (`--markdown` writes `docs/metrics.md`) and the red-flag rules (`--markdown` writes `docs/flags.md`):

```bash
python -m engine metrics
```

```bash
python -m engine rules
```

Write the blank manual-KPI template for every archetype (`data/manual/templates/<archetype>_kpis.csv`), and the coverage report of the filled KPI files (`data/manual/COVERAGE.md`):

```bash
python -m engine kpi-templates --years FY22-FY26
```

```bash
python -m engine kpi-coverage
```

Run the tests:

```bash
python -m pytest -q
```

Options for `analyse`:
- `--asof FY18 | latest`: the default is the `asof` column in `data/universe.csv`. An as-of equal to the newest year in the file runs as "latest" (current price, all quarters).
- `--beta 0.9`: overrides the levered beta.
- `--archetype fmcg`: overrides the archetype from the universe file.
- `--quiet`: suppresses the console summary.

## Inputs

| Path | What |
|---|---|
| `data/raw/screener/<TICKER>.xlsx` | Screener export (only the `Data Sheet` is read; see `docs/screener_format.md`) |
| `data/universe.csv` | `ticker,archetype,role,asof`. Each archetype is a sector module in `config/sectors/<archetype>.yaml` |
| `data/manual/<TICKER>_kpis.csv` | Sector KPIs (asset quality, order book, volumes, ARPU...) and extra data such as payables or promoter pledge. Every value carries a source URL, date and verified flag (see `data/manual/README.md`; coverage in `data/manual/COVERAGE.md`) |
| `data/raw/screener/vintages/<TICKER>/*.xlsx` | Optional older exports; restated years are logged in `notes.md` |

To add a company:
1. Download its Excel export from Screener into `data/raw/screener/`.
2. Add a row to `data/universe.csv`.
3. Run `analyse`.

## Outputs

- **`data/processed/<TICKER>/`** contains:
  - `pnl.csv`, `balance_sheet.csv`, `cash_flow.csv`, `quarterly.csv`, `market.csv`, `shares.csv`, `raw_datasheet.csv`
  - `notes.md`: every assumption the standardiser made, for example exceptional items found in other income, the Nestlé 15-month period, Ind AS 116 breaks, minority interest and mergers
- **`reports/<TICKER>/analysis.json`** contains:
  - company and as-of window
  - cost of capital, with sources
  - the root verdict (economic profit)
  - overall and pillar scores with summaries
  - every metric with its series, level/trend/stability, RAG, band source and a text line
  - DuPont 3- and 5-step
  - driver decompositions (1y/3y/5y)
  - red flags with explanations
  - all data notes
  - peers (same archetype, same as-of year), the full driver nodes, and `findings` (strengths, weaknesses, watch, bull and bear evidence, missing data)
- **`reports/<TICKER>/metrics.csv`**: one row per metric, with FY columns and scores, ready for Excel.
- **`reports/<TICKER>/report.html`**: the readable report, one self-contained file. Open it in a browser; print to PDF from the browser (A4 print styles open every panel). Sections:
  1. header and one-line verdict
  2. strengths, weaknesses and watch, each line with the number, trend and driver chain, ranked by severity × confidence
  3. the interactive MECE tree: click a pillar for its metrics (10-year sparkline, level vs band or peers, trend, equation, meaning)
  4. red flags with the rule and evidence
  5. ROE and ROIC driver waterfalls (1y/3y/5y)
  6. valuation vs history, peers and industry, and reverse-DCF implied vs delivered growth
  7. missing data and what it blocks
  8. the bull and bear case starter (financial evidence only)

  Equations render with KaTeX from a CDN when online. Offline, they show as plain text and everything else works.
- **`reports/<TICKER>/analysis.xlsx`**: a Summary sheet, one sheet per pillar (all metrics × years as numbers), Flags and Drivers.
- **`reports/compare.html`**: from `python -m engine compare A B C` (2-5 tickers): pillar scores side by side, with the strongest and weakest metric per pillar.

## Configuration (every external benchmark carries a source URL and an as-of date)

| File | Content |
|---|---|
| `config/market.yaml` | Risk-free rate (India 10y G-sec), ERP (Damodaran, India), tax rate, macro anchors, synthetic-rating table, beta method/overrides |
| `config/sectors/<archetype>.yaml` | One sector module per archetype (18, plus the shared `_cyclical` base): family, Damodaran industries, how to read the sector, metrics switched off, sector metrics with formulas, required manual KPIs, sourced or `indicative` bands, sector red flags, driver trees and pillar weights. Modules inherit from `default` (or `extends:`); see `docs/methodology.md` section 10 |
| `config/sector_benchmarks.yaml` | **Generated** by `python -m engine build-benchmarks` from `data/external/damodaran/*.xls`: industry betas, sector bands, references |
| `config/bands.yaml` | Generic, family and archetype bands (macro, cost of capital, rating-agency, academic), each with its source |
| `config/scoring.yaml` | Level/trend/stability rules, RAG cut-offs, pillar and metric weights |
| `config/flags.yaml` | 54 generic red-flag rules (id, pillar, severity, applies, condition, explanation template); sector rules live in the sector modules |
| `config/drivers.yaml` | Driver trees as data |

**Refresh before a pitch:**
- Update `risk_free` in `market.yaml`.
- Each January (and July for the ERP), download Damodaran's India datasets from https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html into `data/external/damodaran/`.
- Then rebuild the sector benchmarks:

```bash
python -m engine build-benchmarks
```

## Documentation

- `docs/screener_format.md`: the actual export layout and its quirks.
- `docs/methodology.md`: canonical schema, assumptions, cost of capital, scoring rules, driver mathematics, Altman/Beneish variants, as-of design, limitations.
- `docs/metrics.md`: the metric registry, generated from code.
- `docs/flags.md`: the red-flag rules, generated from config.
