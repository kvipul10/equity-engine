# PLAN: Session 1, core engine

**Status:** approved 2026-11-01 (option 1a: Damodaran hosts allowed) and built in this session. Build notes are in section 12.

---

## 0. What the exports contain (from inspecting all 21 files)

| Finding | Evidence | Consequence for the engine |
|---|---|---|
| All 21 files are Screener **Data Sheet v2.1**, and the row labels are identical for banks, the NBFC, the insurer and non-financials | label diff across files is empty | One parser. It finds sections and rows **by label**, not fixed row numbers, so a layout change gets logged instead of misread |
| The 4 display sheets (P&L, Quarters, BS, CF) are formulas with **no cached values** | 208/112/181/52 formulas, 0 cached | Only `Data Sheet` is read. Screener's own formulas (OPM, ROCE, Debtor days) are documented and reproduced |
| Same labels mean **different things for financials** | HDFCBANK: Sales 3.49 lakh cr = interest earned, Interest = interest expended, Borrowings 36.9 lakh cr = deposits + borrowings; HDFCLIFE: "Other Mfr. Exp" 89,774 = benefits + reserve changes | Archetype-group semantics: `bank`/`nbfc` = bank-like, `insurance`, everything else non-financial. Bank provisions sit inside Other Expenses and cannot be split out |
| **Exceptional items are inside Other Income**: PBT = Sales − Expenses + OI − Dep − Interest holds exactly in every file | DLF FY18 OI = 145% of sales; Bharti FY20 OI = −43% of sales (AGR); Sun FY21–22 negative OI | Estimate exceptional items as OI outliers (median/MAD of OI/sales, causal), log each one, allow manual override. Skipped for financials, where OI is core fee income |
| **Net profit ≠ PBT − Tax** for groups | Bharti FY26 −7,128 (minority); DLF FY26 +1,793 (DCCDL associate) | Net profit = owners' share. The residual is stored as `minority_and_associates`. Equity excludes NCI (Screener puts NCI in Other Liabilities), so ROIC is overstated for big-minority groups. Logged; manual override available |
| **Irregular / stale periods** | Nestlé: Dec year-ends to Dec-23, then Mar-24 (15-month transition, sales 24,394 ≈ CY23 19,126 + Q1), Mar-25, Mar-26. The Dec-23 balance sheet is an exact copy of Dec-22 | Detect stale columns (balance sheet identical to the prior one) and set them to NaN. Period length comes from the chain of real balance-sheet dates (Mar-24 = 15 months), and flows are annualised ×12/months. All of it is logged |
| **Negative cost lines** from reclassification | Asian Paints FY17 Other Exp −2,028 (S&A 4,364); NTPC most years; Nestlé | Only three cost buckets are trusted: materials (RM − ΔInventory), employee, and "other opex" (power + other mfr + S&A + other) |
| **Ind AS 116** is visible in FY20 | Bharti dep/sales 26%→32%; DMart S&A 136→66 while dep jumps | Detected and logged as a comparability break for EBITDA margin. Lease liabilities sit inside Borrowings (Screener) |
| **Merger step-change** | HDFC Bank FY24: assets +59%, adjusted shares +36% | Logged as a likely share-swap merger. Growth across it is marked inorganic |
| Per-share data | Row 93 "Adjusted Equity Shares in Cr" and the FY-end price row are split/bonus/rights-adjusted consistently (HDFC Bank 1:1 bonus 2025, Bajaj 4:1 + split). Current "Number of shares" is a formula with no value | EPS/BVPS use row 93. Current shares = market cap / price |
| Missing data | HAL & HDFC Life FY17 price blank (pre-listing); blank P&L/BS cells = zero (identities confirm it) | Blank line item = 0, blank price/shares = missing |
| **Not in the export** | trade payables, current/non-current split, capex, goodwill, short-term debt, promoter holding/pledge, export date | Proxies are labelled as proxies (§3), and true values can come from `data/manual/<TICKER>_kpis.csv` |
| History depth | 10 annual points (FY17–FY26 = 9-year span); quarters only Jun-24→Sep-26 | "10y" CAGR = full available span (9y here), with the span recorded. **YESBANK as-of FY18 has only FY17–FY18 and no quarters**, so flags designed to work on a 1-year change matter for that test |

Units: ₹ crore (the parser checks for million/lakh labels and checks market cap ÷ price against the adjusted share count). The export is consolidated (inferred from minority/associate residuals). The file does not state this.

---

## 1. Package layout

```
engine/
  __main__.py, cli.py         CLI (argparse)
  paths.py, config.py         project paths, YAML loading + validation (benchmarks must carry source_url + as_of)
  ingest.py                   Data Sheet -> raw tables (label-based), units/version checks, optional vintages
  standardise.py              canonical schema, archetype semantics, periods, exceptional/minority/lease/merger handling, notes.md
  asof.py                     truncates RAW data to an as-of FY before standardising (no look-ahead by construction)
  registry.py                 @metric decorator: id, pillar, formula (the function), direction, archetypes, unit, meaning, equation
  metrics/                    context.py (helpers: avg, lag-by-FY-label, cagr, ttm) + one module per pillar + root.py
  capital_cost.py             Ke, Kd, WACC from config/market.yaml
  sectors.py                  archetype groups, peer sets, band lookup
  scoring.py                  level / trend / stability -> composite -> RAG; pillar + overall roll-up
  drivers.py                  driver-tree engine (log, shift-share, Shapley fallback)
  expr.py, flags.py           safe expression evaluator (ast whitelist, no eval) + rule engine
  report.py, templates/       analysis.json, metrics.csv, console summary; Jinja2 text templates (deterministic)
config/  market.yaml  scoring.yaml  bands.yaml  sectors.yaml  flags.yaml  drivers.yaml
data/processed/<TICKER>/  pnl.csv balance_sheet.csv cash_flow.csv quarterly.csv market.csv shares.csv raw_datasheet.csv notes.md
data/manual/README.md + _TEMPLATE_kpis.csv      (format only, no invented data)
reports/<TICKER>/analysis.json, metrics.csv     reports/universe_summary.csv
docs/screener_format.md  docs/methodology.md  docs/metrics.md (generated from the registry)  docs/flags.md (generated)
tests/                         synthetic Screener workbook builder + test modules
README.md (Mac setup/usage), requirements.txt, .gitignore
```
Runtime deps: pandas, numpy, openpyxl, pyyaml, jinja2. No scipy, no network, no LLM at runtime. The code supports Python ≥ 3.9 and pandas 2.x/3.x.

---

## 2. Ingest and standardise

**Canonical annual schema** (one row per FY, the same superset of columns for every archetype; columns that don't apply are NaN):
- *P&L:* revenue, raw_material, change_in_inventory, materials_cost (= RM − ΔInv), power_fuel, other_mfr, employee_cost, selling_admin, other_exp, other_opex (sum of the four), total_opex, ebitda, other_income, exceptional_est, other_income_core, depreciation, interest, pbt, pbt_core, tax, tax_core, pat, pat_core, minority_and_associates, ebit_core (= pbt_core + interest), operating_ebit (= ebitda − dep), dividend.
  Bank-like extras: nii, net_total_income, opex_incl_provisions. Insurance extras: benefits, opex.
- *Balance sheet:* share_capital, reserves, equity, borrowings, other_liabilities, total_liabilities, net_block, cwip, investments, other_assets, receivables, inventory, cash, other_assets_rest, total_assets, invested_capital (= equity + borrowings − cash − investments), net_debt.
- *Cash flow:* cfo, cfi, cff, net_cash_flow, capex_proxy (= ΔNB + ΔCWIP + Dep), fcf (= CFO − capex_proxy), non_capex_investing (= −CFI − capex_proxy).
- *Per-period:* period_end, period_months, annualised flag, stale_bs flag, comparability_break, notes keys.
- *Quarterly:* quarter_end, revenue, expenses, ebitda, other_income, depreciation, interest, pbt, tax, pat, minority_and_associates.
- *Market:* FY-end adjusted price, adjusted shares (cr), market cap, EV (= mcap + borrowings − cash − investments, so it matches EBITDA/IC, which exclude other income and investments), plus the export-snapshot row (current price, market cap, shares).
- *Shares:* raw count, face value, bonus shares, adjusted count, implied adjustment factor.

**Rules (each one writes a line to notes.md when it fires):** blank line item = 0, blank price/shares = missing; stale BS → NaN; irregular period → annualise flows (opening balance = last real BS); exceptional estimate = OI − median(OI/sales)·sales when |deviation| > 3·MAD and > 5% of PBT, or OI < 0 (median taken only over years ≤ the year being cleaned, never later ones); tax effect at the statutory rate; reclassification (negative lines) logged; Ind AS 116 first year (first period starting ≥ 1-Apr-2019) checked for a visible dep/opex shift; merger heuristic (assets +40% & shares +10%); identity checks (P&L, BS totals, CF) logged; units/version check.
**Restatements:** a single export can't reveal them. Stale and overlap detection covers the visible cases. If you drop older exports in `data/raw/screener/vintages/<TICKER>/`, overlapping years are compared and differences above 0.5% are logged as restatements. Point-in-time use of vintages is out of scope (§11).
**Profit basis:** growth, margins, returns and conversion use *core* profit (reported minus estimated exceptional items, which is identical in most years). The exceptional metrics and the Beneish total accruals measure (TATA) use reported profit. Both versions are kept in the CSVs.

---

## 3. Metric registry and pillars

Each metric is a decorated function with `id, pillar, direction (higher|lower|target|neutral), archetypes, unit, meaning, equation, trend?, stability?, role (scored|component)`. Every metric belongs to exactly one pillar. Components (DuPont factors, capital-intensity terms, Beneish indices) are registered too but not scored. `docs/metrics.md` is generated from the registry. Archetype groups: NF = non-financial, BL = bank + nbfc, INS = insurance, ALL. Averages use (opening + closing)/2; working-capital days use year-end balances, as Screener does.

**Root (the question):** `economic_profit` = (ROIC − WACC) × avg IC [NF]; (ROE − Ke) × avg equity [BL, INS].

1. **Growth:** revenue / EBITDA[NF] / PAT / EPS CAGR 3y, 5y, 10y (= full span); `revenue_growth_volatility`, `pat_growth_volatility` (σ/mean of annual growth); `organic_capital_share_3y` = Σcapex ÷ (Σcapex + ΣΔinvestments⁺) [NF] (the export has no goodwill line, so Δinvestments stands in); `q_revenue_yoy`, `q_pat_yoy` (latest quarter), `q_revenue_yoy_trend` (slope of the last 4 YoY prints); BL/INS extras `bvps_cagr_5y`, `assets_cagr_3y`, `nii_cagr_3y`.
2. **Margins:** gross (1 − materials/sales, n/m if materials < 2% of sales), EBITDA, EBIT (core), PAT margin; materials %, employee %, other-opex % of sales; `dol` = %ΔEBIT/%ΔSales (neutral, n/m if |%ΔSales| < 2%); `ebitda_margin_sd_10y`; `other_income_to_pbt`; `q_ebitda_margin_yoy_change`. BL: `nii_to_assets` (NIM proxy), `yield_on_assets`, `cost_of_funds`, `cost_to_income` (provisions included, labelled as such), `other_income_share`. INS: `benefits_ratio`, `expense_ratio`.
3. **Capital efficiency:** asset turnover, fixed-asset turnover, DSO, DIO (on COGS = materials + power + other mfr), DPO and CCC (**only when payables come from the manual CSV**, since the export has none), `operating_cycle` (DSO + DIO), `nwc_days` (payables-inclusive proxy: (other assets − cash − other liabilities)/sales), capex/sales, capex/depreciation (neutral), CWIP/net block. Components: each asset class ÷ sales (feeds the turnover driver tree). BL: `opex_to_assets`.
4. **Returns:** ROE, ROA, ROCE (Screener definition: EBIT / avg(equity + borrowings)), ROIC = NOPAT / avg IC (NOPAT = operating EBIT × (1 − ETR), ETR clipped to 0–40%, statutory rate if PBT ≤ 0; n/m if IC ≤ 0), `roic_wacc_spread`, `incremental_roic_3y` = ΔNOPAT/ΔIC, BL/INS `roe_ke_spread`. DuPont components: attributable factor (PAT/(PBT − Tax)), tax burden, interest burden, EBIT margin, asset turnover, equity multiplier. **3-step:** ROE = NPM × AT × EM. **5-step:** NPM = attributable × tax burden × interest burden × EBIT margin. Both multiply out exactly. BL: ROE = ROA × EM with additive ROA components.
5. **Cash and earnings quality [NF]:** CFO/EBITDA, FCF/PAT (annual and 5y cumulative), CFO/PAT 5y cumulative, accruals = (PAT − CFO)/avg assets, receivables growth − revenue growth, exceptional frequency (years in the last 5 with |exc| > 5% of PBT) and size (Σ|exc| / Σ|PBT|). **Beneish-style M-score** (8-variable coefficients) built from Screener proxies: current assets ≈ receivables + inventory + cash, SGA ≈ S&A + other exp, dep rate = dep/(dep + NB). Each index is reported, and the variant is documented.
6. **Balance sheet:** net debt/EBITDA, net debt/equity, interest cover (EBIT/interest, capped at 99×), current ratio **proxy** (other assets / other liabilities, Screener's own working-capital split), cash/short-term borrowings (manual ST debt if supplied, otherwise cash / total borrowings, labelled conservative), debt growth − EBITDA growth, **India-adapted Altman Z''-EM** = 3.25 + 6.56·(WC/TA) + 3.26·(Reserves/TA) + 6.72·(EBIT/TA) + 1.05·(Equity/Liabilities), with WC = other assets − other liabilities and reserves standing in for retained earnings. Zones are safe > 5.85 and distress < 4.35. BL/INS: `equity_to_assets`, `funding_vs_equity_growth`, NBFC `borrowings_to_equity`.
7. **Capital allocation:** reinvestment rate = (capex − dep + ΔNWC)/NOPAT (neutral), payout, `share_count_change` (adjusted shares), `buyback_estimate` (shares retired × average FY-end price), shareholder yield, `dividend_to_fcf`, `non_capex_investing_3y` (% of IC), `acquisition_roic_delta_3y` (ROIC change after material non-capex investing, more than 10% of IC), promoter holding / change / pledge (**manual CSV only**; shown as "not in export" otherwise), BL `internal_capital_generation` = ROE × retention and `growth_minus_icg`.
8. **Valuation:** P/E, P/B (ALL), EV/EBITDA, EV/Sales (NF). Each has a **percentile vs its own FY-end history**, which is what gets scored (needs ≥ 5 points). The current point uses the export price and TTM earnings from quarters; an as-of run uses the FY-end price and annual figures. Further metrics: **reverse DCF** `implied_growth_reverse_dcf` (solve g so that EV = PV of NOPAT·(1 − g/ROIC) over 10 years plus a value-driver terminal value at WACC, by bisection) and `implied_minus_delivered_growth`; BL/INS implied g from P/B; **justified P/B** = (ROE − g)/(Ke − g) with ROE = 3y average and g = min(ROE × retention, terminal g), plus `pb_to_justified_pb`; EV/IC and `ev_ic_to_roic_wacc` = (EV/IC)/(ROIC/WACC).
   **WACC:** Ke = rf + β·ERP; Kd = rf + spread (from interest cover via a synthetic-rating table); market-value weights; statutory tax rate 25.17% (s.115BAA). rf = current India 10y G-sec (≈7.37% on 12-Oct-2026; I'll pin the latest close with source and date). β comes from the archetype default, overridable in config, the manual CSV or `--beta`.

That makes about 85 scored metrics and about 40 components. Tests cover every one of them.

---

## 4. Scoring (rules live in config/scoring.yaml and are written up in docs/methodology.md)

- **Level, 0–100.** If the archetype has 4+ companies with a value (as-of consistent), the score is the direction-adjusted percentile rank. Otherwise it comes from config bands: score = 33.3 at the red threshold and 66.7 at the green threshold, linear between them, clipped to 0–100. Target metrics peak inside their green range. Valuation multiples use their own-history percentile. Level RAG cut-offs are ≥ 66.7 green and ≤ 33.3 red.
  - Today **no archetype has 4+ companies** (banks have 3), so every level comes from bands.
- **Trend.** OLS slope over the last 5 annual values (needs ≥ 3), normalised as slope ÷ max(|window mean|, unit floor). Score = 50 + 50·tanh(direction × normalised slope / 0.10). Improving means ≥ +3%/yr, deteriorating means ≤ −3%/yr.
- **Stability.** CV = sd ÷ max(|mean|, unit floor) over up to 10 years (needs ≥ 4). Score = 100·exp(−CV/0.35). Stable means CV ≤ 0.15, volatile means CV ≥ 0.40.
- **Composite.** 0.60·level + 0.25·trend + 0.15·stability, renormalised over the components available. With no level there is no RAG.
- **Metric RAG.** Green if composite ≥ 60, red if < 40, otherwise amber. Overrides: a red level can never be green; a red level with a deteriorating trend is red.
- **Pillar score.** Weighted mean of the metric composites (metric weights in scoring.yaml). A triggered high-severity flag in the pillar caps it at amber.
- **Overall score.** Weighted mean of the pillar scores, with coverage reported. Two or more high-severity flags cap it at amber. Economic profit is reported separately as the root verdict.
- **Proposed pillar weights:**

  | Pillar | NF | BL/INS |
  |---|---|---|
  | Growth | 15 | 15 |
  | Margins | 15 | 15 |
  | Capital efficiency | 10 | 5 |
  | Returns | 20 | 25 |
  | Cash & quality | 15 | n/a |
  | Balance sheet | 10 | 20 |
  | Capital allocation | 5 | 10 |
  | Valuation | 10 | 10 |

---

## 5. Driver trees (config/drivers.yaml, with data separate from code)

- **Link types.**
  - `product`: log decomposition, Δln parent = Σ p·Δln child. If any value is ≤ 0 it falls back to an exact Shapley split.
  - `sum` (shift-share): Δparent = Σ sign·Δchild.
  - `inverse_sum`: turnover = 1 / Σ(capital components ÷ sales). The log change is spread over the components by their share of the intensity change.
  - `weighted_sum`: mix and rate effects, using midpoint weights.
- **Trees.**
  - **ROE (NF):** NPM × AT × EM. NPM splits into attributable × tax burden × interest burden × EBIT margin. EBIT margin = EBITDA margin − dep/sales + core OI/sales. EBITDA margin = 1 − materials% − employee% − other-opex%. AT splits into NB, CWIP, investments, receivable, inventory, cash and other-asset intensity. EM = 1 + D/E + OL/E.
  - **ROIC:** NOPAT margin × IC turnover, then down to the cost lines and to the components of IC/sales.
  - **EPS:** sales × NPM × shares⁻¹.
  - **Market cap:** PAT × P/E (rating change vs earnings growth).
  - **Bank ROE:** ROA × EM. ROA = yield − interest/assets + OI/assets − opex/assets − dep/assets − tax/assets + minority/assets.
- **Windows.** 1y, 3y and 5y changes ending at the as-of year.
- **Output.** Each node's contribution as a % of the parent change, chained down to the deepest leaves. The report shows the top 5 leaves by % of the root change and their own move (e.g. "inventory/sales +18 days → −1.9pp of a −3.5pp ROE fall, 54%"). If the parent change is close to zero, absolute contributions are shown instead of percentages.

---

## 6. Red-flag rules (config/flags.yaml, 40 rules; ≥ 25 required)

Each rule has `id, pillar, severity, applies_to, condition, values, explanation template`. Conditions use a small safe expression language: `m()`, `f()`, `lag`, `chg`, `rising`, `falling`, `streak`, `count_last`, `sum_last`, `growth`, `avail`. A rule that is missing data is reported as **not evaluable**, which is different from not triggered.

- **Growth:** PAT CAGR ≫ revenue CAGR; EPS CAGR < PAT CAGR (dilution); low organic share while growing fast; volatile growth; quarterly revenue decelerating 3 quarters.
- **Margins:** EBITDA margin down 3 years running; **other income > 25% of PBT**; materials %, employee % or other-opex % up > 3pp over 3y; high DOL with falling sales; margin σ > 5pp.
- **Capital efficiency:** **DSO up 3 years running**; DIO up 3 years running; **CWIP/net block > 30% for 2+ years**; asset turnover down > 20% over 3y; capex/dep < 0.8 for 3 years; heavy capex with falling fixed-asset turnover.
- **Returns:** ROIC < WACC for 3 years; **ROE up through leverage while margins fall**; incremental ROIC < WACC while IC grows; ROE down 3 years running.
- **Quality:** **cumulative 5y CFO < 60% of PAT**; FCF negative 3 years with PAT > 0; accruals > 10% of assets; receivables outgrowing revenue 2 years; exceptional items in 3 of the last 5 years; M-score > −1.78; CFO/EBITDA < 50% for 2 years.
- **Balance sheet:** **debt growth > EBITDA growth for 3 years**; net debt/EBITDA > 4×; interest cover < 2×; liquidity squeeze; Altman Z'' distress; BL equity/assets down > 1pp with assets +25%; funding outgrowing equity.
- **Capital allocation:** **dilution while ROE falls**; **rising pledge** (manual data); promoter selling (manual data); dividends > FCF while net debt rises; acquisition spend followed by falling ROIC; BL asset growth > internal capital generation + 15pp.
- **Valuation:** implied growth > delivered + 5pp; above the 90th percentile of own history on both P/E and EV/EBITDA; P/B > 1.5× justified; EV/IC > 1.5× ROIC/WACC.

Explanations are Jinja2 templates with fixed number formats. They are deterministic and make no LLM calls.

---

## 7. CLI and outputs

```
python -m engine ingest [TICKER ...|--all]       # raw -> data/processed/<TICKER>/
python -m engine analyse <TICKER> [--asof FY18|latest] [--beta 1.1]
python -m engine analyse-all [--asof FYxx]       # whole universe (each row's asof) + reports/universe_summary.csv
python -m engine metrics [--markdown]            # registry listing / docs/metrics.md
python -m engine rules                           # flag rules listing / docs/flags.md
```
- `analyse` always re-standardises from raw (it takes milliseconds). `--asof` defaults to the universe.csv value.
- `analysis.json` contains: meta and data window, cost of capital with sources, the root verdict, overall and pillar scores, each metric (series, level, trend, stability, RAG, text), DuPont, drivers (1y/3y/5y), flags (triggered and not evaluable) and data notes.
- `metrics.csv` has one row per metric: pillar, unit, direction, the FY columns, the scores and the RAG.
- Proposal: as-of runs before the latest year write to `reports/<TICKER>/asof_FY18/` so they don't overwrite the current analysis.

---

## 8. Tests (pytest)

- **Synthetic company.** A builder writes a genuine Screener-format `.xlsx` (same Data Sheet layout) for a 10-year non-financial company and a 6-year bank. That way ingest → standardise → metrics is tested end to end.
- **Every registered metric** has an expected value written as arithmetic on the fixture's literal numbers, independent of the engine. A meta-test fails if any metric lacks one. The reverse DCF is checked on a closed-form case and by plugging the solved g back in.
- **No look-ahead.** Run as-of FY(t) on the original data and on a copy where every later year, every later quarter and the current price are replaced with random numbers. The JSON outputs must be byte-identical, and no FY after t may appear anywhere. YESBANK as-of FY18 is also run as a real-data smoke test.
- **Other tests.** Ingest on all 21 real files (identities, Nestlé periods, bank mapping, blanks); hand-computed scoring examples; driver decompositions summing exactly (including the Shapley fallback); expression-evaluator safety (rejects attribute access and imports); every rule parses; key rules triggered on purpose; CLI via subprocess against a temporary project root.

---

## 9. Config and external benchmarks

- **config/market.yaml:** rf (value, source_url, as_of), ERP (India total = mature + CRP), terminal g (6% = RBI 4% CPI target + 2% real; rationale given), statutory tax, synthetic-rating spread table, betas by archetype, overrides.
- **config/bands.yaml:** the entry for each metric is either generic or archetype-specific, with `source_type: external | rule_of_thumb`. External entries require `source_url` and `as_of`, and the config loader rejects them otherwise. Bands may reference market inputs, e.g. ROIC red ≤ `wacc`, green ≥ `wacc + 0.05`.
- **Anchors that need no sector data:**
  - Growth: red at the RBI 4% inflation target, green at nominal GDP growth.
  - Returns: anchored to Ke and WACC.
  - Leverage and coverage: rating-agency criteria and the synthetic-rating table.
  - Altman, Beneish and accruals: thresholds from the original papers.
- **Needs sector data:** margins, turnover, working-capital days, capex intensity and betas are sector-specific. The natural source is Damodaran's **India** industry datasets (January 2026). Those would be mapped archetype → industry in sectors.yaml, with amber = industry value ± 20% (relative, documented).

---

## 10. Decisions (defaults in bold; say "OK" to accept all)

1. **Sector benchmarks.** This session's network blocks `pages.stern.nyu.edu` (Damodaran). Only web search works.
   - (a) **You allow `pages.stern.nyu.edu` and `www.stern.nyu.edu`. I fetch the India datasets and build bands, betas and ERP with URLs and dates.**
   - (b) You put the `.xls` files in `data/external/damodaran/`, and I add `python -m engine build-bands` to parse them. That also works offline on your Mac each January.
   - (c) Generic sourced bands only. Sector-specific band entries ship as `TODO` and those metrics show "no sourced band" instead of an invented threshold.
2. **As-of outputs go to `reports/<TICKER>/asof_<FY>/`.**
3. **Core profit, excluding estimated exceptional items, for growth, returns and margins.** Reported profit is kept alongside.
4. **"10y" CAGR = full available span (9y with these exports).**
5. **EV subtracts investments (book value)** so it is consistent with EBITDA and IC. Screener's EV doesn't.
6. Pillar weights as in §4.
7. **Generated outputs (`data/processed`, `reports`) are committed** so you can browse them in the PR.

## 11. Known gaps after Session 1

- Proxies stand in for payables, the current-assets split, capex, goodwill and minority capital until manual KPIs are supplied.
- Bank provisions and asset quality (GNPA, CASA, capital adequacy) need the manual CSV.
- The as-of tests are limited by the 10-year export window: YESBANK FY18 has 2 years.
- The benchmarks are a 2026 snapshot, so they are look-ahead for old as-of runs. The rf history is optional.
- No point-in-time vintages.
- No HTML report or charts (a later session).

---

## 12. Build notes (changes from this plan)

1. **Reverse DCF method.** The value-driver form planned in section 3 (growth-linked reinvestment over 10 years) cannot reach the EV of high-multiple stocks: Asian Paints at about 50x NOPAT has no solution. It was replaced by market-implied **FCF growth**: base FCF = NOPAT x (1 - gT/ROIC), grown at g for 10 years, then a Gordon terminal value. This is monotonic, so the solution is unique. See docs/methodology.md section 3.
2. **Industry mapping** follows Damodaran's own classification of the universe companies (indname.xls, Jan 2026). Cement maps to *Construction Supplies*, real estate (DLF) to *Real Estate (General/Diversified)* and telecom (Bharti) to *Telecom (Wireless)*. *holdco* maps to *Diversified* because Damodaran puts ADANIENT in Retail (Distributors). Edit config/sectors.yaml to change any of these.
3. **Bank ROA/NIM bands** use RBI's June-2025 FSR (SCB ROA 1.4%, NIM 3.5%). The June-2026 figures could not be retrieved; other bank bands are documented rules of thumb.
4. **rf_history** is empty because historical FY-end G-sec yields were not retrievable. As-of runs use today's rf, and the report says so.
5. **Extra driver tree:** EPS = revenue per share x net margin.
6. **Scale:** 146 registered metrics (about 85 scored, the rest components or informational), 54 red-flag rules and 251 tests.
