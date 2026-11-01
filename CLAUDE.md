# Equity Diagnostic Engine

## Purpose
A tool that takes a Screener.in Excel export of an Indian listed company and tells me, quantitatively and MECE, what the company is doing right and wrong financially, and why. Used for stock pitches, equity research competitions, credit case comps, interview prep and my own investing. It diagnoses financials only; strategy and management judgement stay with me.

## Hard requirements
- Runs offline on my Mac after download: Python 3, no paid APIs, no LLM calls at runtime. Output text comes from deterministic templates.
- Input: data/raw/screener/<TICKER>.xlsx (Screener export) + optional data/manual/<TICKER>_kpis.csv. Universe and archetypes come from data/universe.csv.
- Never assume the Screener layout: inspect the actual files and handle differences (e.g. banks have different line items). Units are ₹ crore unless the file says otherwise.
- "As-of" analysis must use only data up to that fiscal year (no look-ahead), for blow-up tests.
- Every metric is defined once in a registry: id, pillar, formula, direction (higher-is-better or not), applicable archetypes, unit, plain-English meaning, and its equation.
- Every external benchmark (sector bands, risk-free rate, ERP) is stored in config with source URL and as-of date.

## The MECE diagnostic tree (fixed)
Root: does the company create value? Economic profit = (ROIC − WACC) × Invested capital.
Operations: 1 Growth, 2 Margins, 3 Capital efficiency.
Value and quality: 4 Returns (DuPont, ROIC), 5 Cash and earnings quality.
Financing: 6 Balance sheet, 7 Capital allocation.
Market: 8 Valuation.
Each metric belongs to exactly one pillar.

## Code standards
- Package layout: engine/ (ingest, standardise, metrics, scoring, drivers, flags, sectors, report), config/, data/, reports/, tests/.
- pytest tests with hand-computed expected values for every formula, on a synthetic company.
- Clear CLI. README with setup and usage for a Mac.

## Cloud session workflow
- Install packages you need at the start (pandas, openpyxl, pyyaml, jinja2, pytest, numpy).
- Write the plan to PLAN.md, show it to me and wait for my OK before building.
- Don't print large file contents into chat. Keep context lean.
- When done: run tests, commit, push, open a PR into main titled with the session name, and summarise in 10 lines or fewer: what was built, test status, open gaps.
