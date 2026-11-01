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
  - 54 generic red-flag rules plus 57 sector rules
  - a no-look-ahead **as-of** mode for blow-up back-tests
- **Validated.** In Session 4 the engine was compared with published analyst and press commentary for 21 companies (`validation/report.md`):
  - 78% of the expected strengths and weaknesses are flagged; 88% excluding qualitative items such as competition or FDA issues.
  - 3 of 5 pre-collapse warning signs are flagged for Yes Bank as of FY18.
  - 7% of headline claims are false alarms.
  - The holdout companies improved from 54% to 62%.

## Setup (Mac)

You need Python 3.9 or newer. Check with `python3 --version`. If it is missing, install it from python.org or with `brew install python`.

Download or clone the repository, then open Terminal in its folder:

```bash
cd ~/path/to/equity-engine
```

Create a virtual environment (once), activate it (in every new Terminal window) and install the packages:

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

Check the install (about a minute; every test should pass):

```bash
python -m pytest -q
```

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

Strict fiscal-year-end mode drops quarters after 31 March and uses the FY-end price. Use it to see exactly what was published for the year. Output goes to `reports/<TICKER>/asof_FY26/` (and `reports/universe_summary_fy_end.csv`):

```bash
python -m engine analyse-all --fy-end
```

Score the reports against the pre-registered expectations in `validation/expected.yaml`. This writes `validation/results.md` and `results.json`. Add `--include-holdout` to score the four holdout companies too:

```bash
python -m engine validate
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
- `--asof FY18 | latest`: the default is the `asof` column in `data/universe.csv`. An as-of equal to the newest year in the file runs as "latest" (current price, all quarters) unless `--fy-end` is given.
- `--fy-end`: strict fiscal-year-end cut, also for the newest year (no later quarters, FY-end price).
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

## Add a new company

1. **Download the export.** On screener.in, open the company page and log in. Click **Export to Excel** (choose Consolidated if the group reports consolidated figures).
2. **Rename and place it.** Rename the file to `<TICKER>.xlsx`, using the NSE symbol in capitals (e.g. `PIDILITIND.xlsx`), and put it in `data/raw/screener/`.
   - The engine reads the `Data Sheet` tab and never assumes its layout (`docs/screener_format.md`).
   - Units are Rs crore.
3. **Add a row to `data/universe.csv`**: `ticker,archetype,role,asof`, for example `PIDILITIND,consumer_manufacturing,test,FY26`.
   - The archetype picks the sector module. It must be one of: auto, bank, capital_goods_defence, cement, chemicals, consumer_manufacturing, fmcg, holdco, insurance, it_services, metals, nbfc, pharma, real_estate, retail, telecom, utilities, or default for anything else.
   - `asof` is the fiscal year to analyse (`FY26`, or an earlier year for a back-test).
4. **Optional: fill the sector KPIs.** These are asset quality, order book, volumes, ARPU and similar figures that the export lacks.
   - Copy the blank template from `data/manual/templates/<archetype>_kpis.csv` to `data/manual/<TICKER>_kpis.csv`.
   - Fill one row per KPI and year: `value`, `unit`, `source_url`, `source_date` and `verified`. `verified` is `Y` only if you checked the primary document.
   - Leave unknown values blank. The report then lists them as missing data and says what they block.
   - Regenerate the templates with `python -m engine kpi-templates --years FY22-FY26` if you need other years.
5. **Run it** and open `reports/<TICKER>/report.html`:

```bash
python -m engine analyse PIDILITIND
```

6. **Read `data/processed/<TICKER>/notes.md`.** It lists every assumption the standardiser made: exceptional items, one-off tax, mergers, Ind AS 116 and period lengths. Check that nothing surprising happened.

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

## How to read the report

- **Verdict line (header).** Does the company create value? This compares ROIC with WACC (ROE with Ke for banks and
  insurers) for the as-of year. It also gives the overall score (0-100, RAG) and the strongest and weakest pillar.
- **RAG per metric.** Each metric's colour combines three things (weights in `config/scoring.yaml`):
  - **level**: against a sourced or `indicative` band, otherwise the percentile among same-archetype peers
  - **trend**: the slope over the last 5 years
  - **stability**
  - The line says which comparison was used. `indicative` bands are judgement, not a published standard.
  - `n/a` or `UNSCORED` means the metric could not be judged, and the reason is shown. Examples: missing KPI, merger
    window, immaterial debt.
- **Strengths, weaknesses, watch.** Each list is the top 6, ranked by severity x confidence, with at most 2 per pillar.
  Each line gives the number, its trend and, where a driver tree exists, the chain behind it, e.g. "ROE +6pts over 3y,
  57% from PAT margin, because other expenses fell...".
  - Confidence is lower when the input is an unverified manual KPI.
  - A metric doubted by a fired rule is moved to watch with a note, e.g. solvency while IN01 stands.
- **MECE tree.** Click a pillar to open its metrics: sparkline, level vs band or peers, equation and meaning.
- **Red flags.** Each fired rule shows its condition, the evidence and what it means. Not-evaluable rules name the
  missing input.
- **Drivers.** These are exact decompositions of the change in ROE and ROIC over 1, 3 and 5 years. Contributions sum
  to the change, and any residual is shown.
- **Valuation.** Multiples are shown against three references:
  - the company's own 10-year history
  - same-archetype peers at the same year
  - Damodaran's India industry aggregate
  - The reverse DCF shows the growth the price implies against the growth delivered. Single-stage tests such as P/B vs
    justified P/B are growth-blind, so read them with the reverse DCF.
- **Missing data.** This section lists the KPIs that the sector module needs but cannot find, and what they block.
- **Bull and bear case starter.** Financial evidence only, each bullet citing the metric or rule behind it. Strategy and
  management judgement are yours to add.
- **How far to trust it** (from `validation/report.md`):
  - Most reliable for real estate, capital goods and defence, holdcos, IT services, insurers and consumer manufacturing.
  - Least reliable for:
    - regulated utilities (consolidated returns, not regulated equity)
    - banks (Ke above market practice; NIM needs the KPI)
    - auto (cash-rich valuation)
  - Quarterly one-offs and qualitative issues (competition, regulation) are outside what it can see.

## Configuration (every external benchmark carries a source URL and an as-of date)

| File | Content |
|---|---|
| `config/market.yaml` | Risk-free rate (India 10y G-sec), ERP (Damodaran, India), tax rate, macro anchors, synthetic-rating table, beta method/overrides |
| `config/sectors/<archetype>.yaml` | One sector module per archetype (18, plus the shared `_cyclical` base): family, Damodaran industries, how to read the sector, metrics switched off, sector metrics with formulas, required manual KPIs, sourced or `indicative` bands, sector red flags, driver trees and pillar weights. Modules inherit from `default` (or `extends:`); see `docs/methodology.md` section 10 |
| `config/sector_benchmarks.yaml` | **Generated** by `python -m engine build-benchmarks` from `data/external/damodaran/*.xls`: industry betas, sector bands, references |
| `config/bands.yaml` | Generic, family and archetype bands (macro, cost of capital, rating-agency, academic), each with its source |
| `config/scoring.yaml` | Level/trend/stability rules, RAG cut-offs, pillar and metric weights |
| `config/flags.yaml` | 54 generic red-flag rules (id, pillar, severity, applies, optional `not_for` and `suppresses`, condition, explanation template); sector rules live in the sector modules |
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
- `validation/report.md`: Session 4 validation against analyst and press commentary. It covers hit rates, false alarms,
  the iteration log, the holdout and blow-up results, reliability by archetype and limitations. `validation/expected.md`
  holds the pre-registered expectations and `validation/adjudication.yaml` the review of every headline claim.
