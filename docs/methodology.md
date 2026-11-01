# Methodology

## 1. Pipeline

```
data/raw/screener/<T>.xlsx ──ingest──> raw tables (label-based) ──[as-of truncation]──> standardise ──> canonical CSVs + notes.md
      │                                                                                     │
config/market.yaml + sector_benchmarks.yaml ──> cost of capital (Ke, Kd, WACC) ─────────────┤
                                                                                            v
                         metric registry (146 metrics, 8 pillars + root) ──> red-flag rules (54)
                                                                                            │
                         scoring (level, trend, stability -> RAG -> pillars -> overall) <───┤
                         driver trees (exact 1y/3y/5y decompositions) <─────────────────────┘
                                                                                            v
                                                       reports/<T>/analysis.json + metrics.csv
```

Every step is deterministic. Every number in a report can be traced through `metrics.csv` (each metric with its equation), `data/processed/<T>/*.csv` (the standardised lines) and `notes.md` (every assumption that fired).

## 2. Standardisation rules (logged per company in `notes.md`)

| Rule | Detail |
|---|---|
| Only `Data Sheet` | The display sheets are formulas without cached values |
| Label-based parsing | Sections and rows are found by label and the year columns by the `Report Date` row. Unknown labels are logged, missing labels become NaN |
| Units | Rs crore unless a units label (million/lakh/billion) is found, in which case values are scaled. Share counts are in crore |
| Blanks | A blank line item = 0, because Screener leaves zero items blank and the identities hold on that basis. A blank price or share count = missing |
| Fiscal-year labels | `FY` + two-digit year of the period end. A Dec year-end is labelled by its calendar year |
| Stale columns | A balance sheet or P&L identical to the previous column is set to missing. Example: Nestlé Dec-23, whose balance sheet copies Dec-22 |
| Period length | Months since the previous real balance sheet (stale columns are skipped). Flows are annualised ×12/months, and averages use that real opening balance. Example: Nestlé FY24 = 15 months from Dec-22 |
| Cost lines | Materials = raw material − change in inventory. COGS = materials + power & fuel + other mfr. Other opex = power & fuel + other mfr + S&A + other expenses, summed because Screener reclassifies between these lines (negative lines are logged) |
| Exceptional items | Screener puts them inside other income. A year is flagged when its other-income/sales ratio is a robust outlier versus the other years (leave-one-out median, σ = 1.4826×MAD floored at 0.25% of sales, \|deviation\| > 3σ and > 5% of PBT), and any negative other income is flagged too. Amount = (ratio − median) × sales. Tax effect at the statutory rate. Core PBT/PAT exclude it. Override via the manual KPI file. Not applied to financials, whose other income is core |
| Minority / associates | `pat − (pbt − tax)` = associates' share minus minority interest. Net profit is the owners' share. Equity excludes NCI (Screener has NCI inside other liabilities) |
| Capex | Proxy = ΔNet block + ΔCWIP + depreciation. FCF = CFO − capex. Non-capex investing = −CFI − capex |
| Invested capital | IC = equity + borrowings − cash − investments. This equals net block + CWIP + receivables + inventory + other assets − other liabilities |
| EV | Market cap + borrowings − cash − investments (consistent with EBITDA and IC, which exclude other income and investments). Screener's EV does not subtract investments |
| Ind AS 116 | In the first period starting on or after 1 Apr 2019, a jump in dep/sales together with a fall in opex/sales or a rise in interest/sales is logged as an EBITDA comparability break |
| Mergers | Total assets +40% with adjusted shares +10% (or assets +60%) is logged as an inorganic step |
| Identities | P&L, balance-sheet totals and the cash-flow sum are checked. Residuals are logged |
| Financials | Bank-like semantics: Sales = interest earned; Interest = interest expended; Borrowings = deposits + borrowings; other expenses include provisions. Insurance semantics: Other Mfr = benefits + reserve changes |
| Restatements | Optional older exports in `data/raw/screener/vintages/<T>/` are compared with the current file; differences above 0.5% are logged |

## 3. Metric conventions

- **Averages:** return and turnover ratios use the average of opening and closing balances. Working-capital days use year-end balances, matching Screener's debtor days.
- **Profit basis:** growth, margins, returns and cash conversion use **core** profit (reported minus estimated exceptional items). The accruals ratio, Beneish TATA and other-income/PBT use **reported** profit.
- **EBIT** = core PBT + interest, i.e. it includes core other income. This is the textbook DuPont EBIT and Screener's ROCE numerator.
- **NOPAT** = (EBITDA − depreciation) × (1 − ETR), with ETR = core tax ÷ core PBT clipped to 0–40%, or the statutory 25.168% if PBT ≤ 0. NOPAT excludes other income because IC excludes the cash and investments that earn it.
- **"10y" CAGR** = the full available span, capped at 10 years. A 10-column export gives 9 years, and the actual span is recorded in the metric note.
- **n/m rules** (not meaningful): CAGR with a non-positive end point; IC ≤ 0, which makes ROIC n/m (economic profit stays defined as NOPAT − WACC × IC); immaterial inventory, which makes DIO n/m.
- **Proxies:**
  - current ratio = other assets ÷ other liabilities
  - cash ÷ short-term borrowings uses total borrowings unless manual data is supplied
  - `nwc_days` includes payables implicitly
  - DPO and CCC need manual trade payables
- **Beneish-style M-score:** the 8-variable model (Beneish 1999), with current assets ≈ receivables + inventory + cash, SGA ≈ S&A + other expenses (other opex if that is ≤ 0), and depreciation rate = dep ÷ (dep + net block).
- **India-adapted Altman Z''-EM** = 3.25 + 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4 (Altman 2005, emerging-market score). The inputs are:
  - X1 = (other assets − other liabilities) ÷ TA
  - X2 = reserves ÷ TA (a proxy for retained earnings that includes securities premium)
  - X3 = EBIT ÷ TA
  - X4 = book equity ÷ total liabilities

  Zones: safe > 5.85, distress < 4.35. Z'' omits the sales/assets term, which makes it suitable for service-heavy Indian companies; book equity replaces market value.
- **Reverse DCF:** market-implied 10-year free-cash-flow growth. The equation:

  ```
  EV = Σ F0(1+g)^t / (1+WACC)^t + F10(1+gT) / ((WACC − gT)(1+WACC)^10)
  ```

  Base FCF is F0 = NOPAT0 × (1 − gT/RONIC), where RONIC is the 3-year average ROIC, capped at 100%. That base is the steady-state cash flow after the reinvestment terminal growth requires. The solution is unique because PV rises monotonically in g.

  *This is a change from PLAN.md.* The planned value-driver form (growth-linked reinvestment in the explicit period) cannot reach the EV of high-multiple stocks within 10 years. It returned no answer for, for example, Asian Paints, which is exactly where the question matters.
- **Justified P/B** = (ROE − g)/(Ke − g), where ROE = 3-year average and g = min(ROE × (1 − 3-year average payout), terminal g). P/B-implied growth for financials: g = (Ke·P/B − ROE)/(P/B − 1).
- **Valuation "current":**
  - Latest run: the export-date price, with TTM PAT/EBITDA/revenue from the last 4 quarters (if they run past the last FY end). Core annual PAT is used instead when the last FY had an exceptional item.
  - As-of run: the as-of year-end price and annual figures.
  - Own-history percentiles compare the current multiple with FY-end multiples and need at least 5 points.

## 4. Cost of capital

- **Ke** = rf + β·ERP.
  - rf = India 10-year G-sec (7.41%, 30 Oct 2026).
  - ERP = India total ERP (6.92% = mature 4.20% + country risk premium 2.72%; Damodaran, July 2026).
  - rf already embeds India's sovereign default spread (1.75%). Set `rf_net_of_default_spread: true` for a Damodaran-consistent Ke.
- **β:**
  - Non-financials: bottom-up, i.e. the industry unlevered (cash-corrected) beta from Damodaran India (Jan 2026), re-levered at the company's market D/E with β_L = β_U(1 + (1 − t)D/E).
  - Financials: the industry levered beta.
  - Overrides, in priority order: `--beta`, then the manual KPI, then `config/market.yaml`.
- **Kd** = rf + default spread for the synthetic rating implied by interest cover (Damodaran large-firm table, Jan 2026), × (1 − 25.168%).
- **WACC** uses market-value weights (market cap, book borrowings). For financials, WACC = Ke.
- **Historical years** use `rf_history` if supplied, otherwise today's rf. The report states which, because this is the only place a later-dated input can reach an as-of run.

## 5. Scoring (config/scoring.yaml)

**Level (0–100).**
- **Peer mode:** if the archetype has ≥ 4 companies with a value, all computed at the same as-of year, the level is the direction-adjusted percentile rank: (#below + 0.5·#ties) ÷ (n − 1).
- **Band mode** otherwise: score = 33.3 + 33.3 × (v − red)/(green − red), clipped to 0–100 and mirrored for lower-is-better. So the red threshold scores 33.3 and the green threshold 66.7.
  - Target metrics score 75 inside the green range.
  - Level RAG: green ≥ 66.7, red ≤ 33.3.

**Trend.**
1. OLS slope of the last 5 annual values (≥ 3 needed), using fiscal years as x.
2. Normalised slope = slope ÷ max(|window mean|, unit floor).
3. Score = 50 + 50·tanh(direction × normalised slope ÷ 0.10).
4. Label: improving if ≥ +3%/yr, deteriorating if ≤ −3%/yr.

**Stability.**
1. CV = sd ÷ max(|mean|, unit floor) over up to 10 years (≥ 4 needed).
2. Score = 100·exp(−CV/0.35).
3. Label: stable if CV ≤ 0.15, volatile if CV ≥ 0.40.

**Composite** = (0.60·level + 0.25·trend + 0.15·stability), renormalised over the components available. With no level there is no RAG.

**Metric RAG.** Green if the composite is ≥ 60, red if < 40, amber otherwise. Two overrides:
1. A red level can never be green.
2. A red level with a deteriorating trend is red.

Neutral-direction metrics (payout, capex/depreciation, raw multiples …) are informational: their trend and stability are shown but they get no RAG.

**Pillar** = weighted mean of the metric composites (`metric_weights`, default 1). A triggered high-severity flag in the pillar caps it at amber.

**Overall** = weighted mean of the pillar scores (`pillar_weights`, by family). Coverage = the weight of the pillars that could be scored. Two or more high-severity flags cap the overall score at amber.

**Root (economic profit)** is reported separately as the verdict. The pillars explain it rather than being averaged with it.

Worked example (tests/test_scoring_drivers.py): ROIC 12% with WACC 12% is exactly at the red threshold, so level = 33.3 (red). A 5-year slope of −2pp/yr on a mean of 16% gives a normalised slope of −0.125, i.e. deteriorating. The metric is therefore RED (override 2), whatever the composite.

## 6. Bands and benchmarks

Lookup order for a company's metric:
1. `bands.yaml` archetype entries
2. `sector_benchmarks.yaml` (Damodaran India, by archetype)
3. `bands.yaml` family entries
4. `bands.yaml` generic entries

Each band is one of three types:
- `external`: carries `source_url` and `as_of`, enforced at load time.
- `rule_of_thumb`: carries a `rationale` and `as_of`.
- `derived`: expressed in market inputs, e.g. ROIC red ≤ `wacc`, green ≥ `wacc + 0.05`; growth red ≤ inflation target, green ≥ nominal GDP growth.

**Sector bands** (margins, DSO/DIO/DPO, NWC days, operating cycle/CCC, IC turnover) come from Damodaran's January 2026 India datasets. Each archetype is mapped to industries by Damodaran's own classification of the universe companies (`config/sectors.yaml`):
- centre = industry value
- half-width = max(20% × |centre|, unit floor: 2pp, 10 days, 0.2x)
- higher-is-better: red = centre − h, green = centre + h (mirrored for lower-is-better)

Damodaran's figures are aggregates, so a dominant company influences its own benchmark (Bharti in Telecom (Wireless), NTPC in Power). Rebuild with `python -m engine build-benchmarks`.

## 7. Driver trees (config/drivers.yaml)

| Link | Identity | Decomposition |
|---|---|---|
| `product` | P = Π cᵢ^pᵢ | Δln P = Σ pᵢ Δln cᵢ, converted to level units with the logarithmic mean L(P₁,P₀) = (P₁ − P₀)/(ln P₁ − ln P₀). Exact (Sato–Vartia). If any value ≤ 0, an exact Shapley split is used instead |
| `sum` (shift-share) | P = k + Σ sᵢ cᵢ | contribution = sᵢ Δcᵢ |
| `inverse_sum` | P = 1/Σ sᵢ cᵢ (turnover = 1/capital intensity) | contribution = −sᵢ Δcᵢ · L(P)/L(CI) |
| `weighted_sum` | P = Σ wᵢ rᵢ | mix Δwᵢ·r̄ᵢ + rate w̄ᵢ·Δrᵢ |

- **Chaining:** each child gets a factor (parent units per unit of child change). A leaf's contribution to the root is the product of the factors along its path times the leaf's own change. Because no step divides by a small change, offsetting moves are handled cleanly, and leaf contributions sum exactly to the root change. The engine reports the residual and checks every link identity (`inexact_nodes`).
- **Trees:**
  - **ROE (non-financial):** 3-step × 5-step, down to the materials/employee/other-opex shares of sales, depreciation, core other income, and capital intensity (days of sales of net block, CWIP, investments, receivables, inventory, cash, other assets).
  - **ROIC:** NOPAT margin × IC turnover.
  - **EPS:** revenue per share × net margin.
  - **Financials:** ROE = ROA × EM, with additive ROA components.
- **Windows:** 1y, 3y, 5y. The report shows the top 5 leaves.

## 8. Red flags (config/flags.yaml)

- **Conditions:** safe expressions (Python `ast` with a whitelist of nodes and functions; no `eval`), over metric ids and standardised fields: `m`, `chg`, `pchg`, `rising`, `falling`, `all_last`, `count_last`, `sum_last`, `avail`.
- **Outcomes:** each rule is *triggered*, *clear* or *not evaluable*. "Not evaluable" names the missing input, for example promoter pledge when no manual data exists.
- **Explanations:** Jinja2 templates with fixed number formats.
- **Coverage:** 54 rules across the 8 pillars, including every example in the brief:
  - cumulative CFO < 60% of PAT over 5 years
  - DSO up 3 years running
  - debt growth > EBITDA growth for 3 years
  - ROE rising on leverage while margins fall
  - CWIP/net block > 30% for 2+ years
  - other income > 25% of PBT
  - dilution while ROE falls
  - rising pledge

## 9. As-of design (no look-ahead)

`--asof FYxx` truncates the **raw** export before standardisation. It drops:
- later annual columns
- quarters ending after the as-of year-end
- the export-date price, replaced by the as-of year-end price
- later manual KPIs

Same-archetype peers used for percentiles are truncated to the same year. Exceptional-item estimates, bands and scores therefore see only data up to that year by construction.

`tests/test_asof.py` proves it:
1. Every value after FY21 is scrambled, for the company and three peers, including all quarters, the current price and the manual KPIs.
2. The FY21 report must be identical to the unscrambled one.
3. No later year may appear in its data.

Remaining non-data look-ahead:
- split/bonus adjustment factors, which are in today's share units (ratios are unaffected)
- the 2026 benchmark vintage (bands, betas, ERP)
- the rf, unless `rf_history` is supplied

## 10. Known limitations

- Ten annual points and ten quarters per export. YESBANK as of FY18 has two years and no quarters, so trend and stability are not computable there and level-only flags carry the analysis (A06 and B06 still fire).
- No payables, current/non-current split, capex, goodwill or shareholding in the export. These are proxies until `data/manual` is filled.
- Bank provisions and asset quality are not separable, so cost-to-income includes provisions. Insurer metrics are Screener approximations; embedded value and VNB need manual data.
- Exceptional items are estimates. Their tax effect assumes the statutory rate (capital gains may be taxed differently).
- ROIC/ROCE omit balance-sheet minority interest unless supplied, so ROIC is overstated for groups with large minorities (e.g. Bharti).
- Consolidated vs standalone is inferred, not stated in the file.
