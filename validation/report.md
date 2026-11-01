# Validation report (Session 4)

The engine's diagnosis was compared with what published analyst and press commentary says, for 17 companies (16 test
companies as of FY26 and Yes Bank as of FY18, before its collapse). Four holdout companies were scored only before and
after the fixes. Expectations were written from sources and committed before any engine output was compared.

## 1. Results

| Set | Items | Hit rate | Excl. qualitative | Excl. qualitative and missing data | Headline hit rate |
|---|---|---|---|---|---|
| Test (16 companies, FY26) | 96 | **75/96 (78%)** | **75/85 (88%)** | 75/85 (88%) | 46/96 (48%) |
| Blow-up (Yes Bank, FY18) | 5 | 3/5 (60%) | 3/4 (75%) | 3/4 (75%) | 2/5 (40%) |
| Holdout (4 companies, FY26) | 24 | 15/24 (62%) | 15/20 (75%) | 15/20 (75%) | 9/24 (38%) |

Test strengths are matched at 41/48 (85%) and test weaknesses at 34/48 (71%).

**False alarms.** 15 of 209 headline items for the test and blow-up companies, a rate of
7.2%. That is 14 reviewed items in `validation/adjudication.yaml` plus 1 automatic contradiction
(NTPC-S2). The holdout adds 1 automatic contradiction (Infosys book-to-bill). Holdout headline items were not
adjudicated.

**How to read the rates:**
- A hit means the engine flags the expected item anywhere in the report. For a strength, a signal metric is GREEN. For a
  weakness, a signal metric is RED, or AMBER and deteriorating, or a signal rule fired.
- A headline hit also requires the signal to appear in the report's top lists: top-6 strengths, weaknesses or watch, or
  the bull/bear case.
- Qualitative items (FDA compliance, competition, Europe risks and similar) are kept and reported. The engine diagnoses
  financials only, so these items are not expected to match.

## 2. Method

**Pre-registration.** `validation/expected.yaml` and `validation/expected.md` were committed in `d11d405`
(2026-11-01 14:44 UTC), before analyse-all was run for this session or any output was compared.
- They hold 125 items: 60 strengths and 65 weaknesses. Of these, 76 are financial, 33 KPI and 16 qualitative.
- Each item cites one or two analyst or press sources with dates.
- Each item names its signals in advance: metric ids and rule ids chosen by meaning from `docs/metrics.md` and
  `docs/flags.md`.
- Before the commit, signals were checked only against the registry, never against outputs. Four signal entries
  named a metric or rule that is switched off for that archetype, and were removed or replaced.

**Disclosure.** Earlier sessions produced reports, and parts of five had been seen (TCS, HDFC Bank, DLF, Tata Steel,
Yes Bank). Every expected item still comes from a source found in this session.

**As-of alignment.** Validation runs use `--fy-end`: data stop at 31 March 2026 (FY18 for Yes Bank) and the FY-end price
is used. This matches the results that the commentary discussed.

**False alarms** come in two kinds:
- *Automatic*: the engine says the opposite of an expected item. A signal for an expected strength is RED, or a signal
  for an expected weakness is GREEN and listed as a strength.
- *Reviewed*: every headline item was checked against the sources and the reported numbers. Headline items are the
  top-6 strengths and weaknesses and the high/medium rules. The verdict, cause and reason for each of the
  209 items are in `validation/adjudication.yaml`. Items that are signals of a matched pre-registered item
  are ok by construction.

**Fix discipline:**
- Every fix is general: a parsing rule, metric definition, threshold, sector logic or data. Each comes with a
  hand-computed test (`tests/test_session4_fixes.py` and the formula tests).
- Changed thresholds keep a source or are marked `indicative`.
- The holdout was not opened until the fixes were final.

**Commands:**
```
python -m engine analyse-all --fy-end
python -m engine validate                                   # writes validation/results.md and results.json
python -m engine validate --include-holdout --holdout-details
```

## 3. Per company (test and blow-up)

Columns:
- **Matched** and **Excl. qual.**: hits out of all items, and out of items excluding qualitative ones.
- **Headline**: headline hits out of all items.
- **Non-qualitative misses**: item ids; `*` means the item is also contradicted.
- **Qual.**: qualitative items.
- **False alarms / headline items**: false alarms out of the company's headline items.

| Company | Archetype | Matched | Excl. qual. | Headline | Non-qualitative misses | Qual. | False alarms / headline items |
|---|---|---|---|---|---|---|---|
| TCS | it_services | 5/6 | 5/5 | 3/6 | - | 1 | 0 / 11 |
| HDFCBANK | bank | 5/6 | 5/6 | 4/6 | W1 | 0 | 3 / 12 |
| BAJFINANCE | nbfc | 5/6 | 5/6 | 5/6 | W2 | 0 | 0 / 10 |
| HDFCLIFE | insurance | 5/6 | 5/5 | 4/6 | - | 1 | 0 / 12 |
| HINDUNILVR | fmcg | 4/6 | 4/6 | 3/6 | S1, W2 | 0 | 1 / 12 |
| ASIANPAINT | consumer_manufacturing | 5/6 | 5/5 | 4/6 | - | 1 | 0 / 12 |
| TATASTEEL | metals | 3/6 | 3/3 | 2/6 | - | 3 | 1 / 12 |
| ULTRACEMCO | cement | 4/6 | 4/5 | 2/6 | S2 | 1 | 0 / 12 |
| SUNPHARMA | pharma | 4/6 | 4/4 | 1/6 | - | 2 | 1 / 12 |
| MARUTI | auto | 3/6 | 3/4 | 2/6 | W3 | 2 | 2 / 12 |
| BEL | capital_goods_defence | 6/6 | 6/6 | 3/6 | - | 0 | 1 / 14 |
| DLF | real_estate | 6/6 | 6/6 | 4/6 | - | 0 | 0 / 12 |
| NTPC | utilities | 5/6 | 5/6 | 2/6 | S2* | 0 | 5 / 13 |
| DMART | retail | 4/6 | 4/6 | 2/6 | W2, W3 | 0 | 0 / 12 |
| ADANIENT | holdco | 6/6 | 6/6 | 4/6 | - | 0 | 1 / 21 |
| BHARTIARTL | telecom | 5/6 | 5/6 | 1/6 | W3 | 0 | 0 / 12 |
| YESBANK | bank | 3/5 | 3/4 | 2/5 | W3 | 1 | 0 / 8 |

## 4. Per archetype

There is one test company per archetype and 6 items each, so one item moves a rate by 17 points. Read these as
indications, not estimates.

| Test archetype | Hit rate | Excl. qualitative | Headline |
|---|---|---|---|
| auto | 3/6 (50%) | 3/4 (75%) | 2/6 (33%) |
| bank | 5/6 (83%) | 5/6 (83%) | 4/6 (67%) |
| capital_goods_defence | 6/6 (100%) | 6/6 (100%) | 3/6 (50%) |
| cement | 4/6 (67%) | 4/5 (80%) | 2/6 (33%) |
| consumer_manufacturing | 5/6 (83%) | 5/5 (100%) | 4/6 (67%) |
| fmcg | 4/6 (67%) | 4/6 (67%) | 3/6 (50%) |
| holdco | 6/6 (100%) | 6/6 (100%) | 4/6 (67%) |
| insurance | 5/6 (83%) | 5/5 (100%) | 4/6 (67%) |
| it_services | 5/6 (83%) | 5/5 (100%) | 3/6 (50%) |
| metals | 3/6 (50%) | 3/3 (100%) | 2/6 (33%) |
| nbfc | 5/6 (83%) | 5/6 (83%) | 5/6 (83%) |
| pharma | 4/6 (67%) | 4/4 (100%) | 1/6 (17%) |
| real_estate | 6/6 (100%) | 6/6 (100%) | 4/6 (67%) |
| retail | 4/6 (67%) | 4/6 (67%) | 2/6 (33%) |
| telecom | 5/6 (83%) | 5/6 (83%) | 1/6 (17%) |
| utilities | 5/6 (83%) | 5/6 (83%) | 2/6 (33%) |

| Holdout archetype | Hit rate | Excl. qualitative | Headline |
|---|---|---|---|
| bank | 4/6 (67%) | 4/6 (67%) | 3/6 (50%) |
| capital_goods_defence | 3/6 (50%) | 3/4 (75%) | 1/6 (17%) |
| fmcg | 5/6 (83%) | 5/6 (83%) | 4/6 (67%) |
| it_services | 3/6 (50%) | 3/4 (75%) | 1/6 (17%) |

## 5. Iteration log (test set, 96 items; blow-up 5 items)

| # | Change (all general, each with a test) | Hit rate | Excl. qual. | Excl. qual. + missing | Headline | Blow-up | Automatic contradictions | Headline items |
|---|---|---|---|---|---|---|---|---|
| 0 | Baseline engine (latest data, export-date price) | 61 (64%) | 72% | 74% | 40% | 2/5 | 6 | 255 |
| 1 | `--fy-end` as-of alignment | 63 (66%) | 74% | 77% | 42% | 2/5 | 5 | - |
| 2 | Rule recalibration (IT01, IN01, IN03, TC03); bands (telecom ARPU, utilities RoE and capacity, order book); pharma US growth in USD (lazy `first_of`); merger-window CAGRs unscored; sourced KPI fills | 74 (77%) | 87% | 87% | 47% | 2/5 | 2 | - |
| 3 | One-off tax normalisation; retail store-growth band; bank NPA-divergence rule BK09 | 75 (78%) | 88% | 88% | 46% | 2/5 | 2 | 219 |
| 4 | False-alarm fixes: debt materiality gate (B01 and debt growth), liquidity incl. investments, growth-aware V03/V04, reverse DCF n/m when ROIC <= WACC, EV/IC value-driver steady state, sector switch-offs (R02 insurers, B05 telecom, V03/EV-IC/justified P/B developers), suppression of doubted strengths, merger-window growth flags, NBFC coverage band, acquisition spend net of treasury, RE01 on 3-year pre-sales, insurer revenue/margin metrics off | 75 (78%) | 88% | 88% | 48% | 2/5 | 1 | 209 |
| 5 | Sourced KPI fills: Yes Bank FY18 deposits, HDFC Bank NIM, UltraTech FY24 volume | **75 (78%)** | **88%** | **88%** | **48%** | **3/5** | **1** | **209** |

Stopping rule: the test hit rate was flat for iterations 3 to 5. Every remaining miss is qualitative, missing data, or a
definition or threshold difference that would need a new metric or a company-specific change (section 6).

False alarms over the iterations:
- Iteration 3, reviewed against the sources: about 33 wrong headline claims out of 219 (review notes). The committed
  adjudication covers the final run.
- Iteration 4 fixed these with general causes:
  - Immaterial debt (TCS, Asian Paints).
  - Treasury held in investments (Maruti, UltraTech, Airtel).
  - Growth-blind valuation tests (TCS, Maruti V03, NTPC V01, DLF V01).
  - Book-based valuation for developers (DLF).
  - Collections lag in a launch-heavy year (DLF RE01).
  - Insurer revenue, leverage, margin and solvency readings (HDFC Life, 5 items).
  - Doubted strengths for Yes Bank: loan growth, credit cost, CRAR, ROA and PAT growth, and the GNPA contradiction.
  - HDFC Bank's merger-inflated G02.
  - The bank coverage band applied to an NBFC (Bajaj Finance).
  - Treasury deposits read as acquisitions (BEL A05).
  - Altman Z'' for a telecom (Airtel).
- After the fixes: 14 reviewed plus 1 automatic, out of 209 (7.2%).

## 6. Remaining misses (test set, non-qualitative) and their causes

| Item | Expected | What the engine sees | Cause |
|---|---|---|---|
| HDFCBANK-W1 | NIM compression, weak NII growth | Reported NIM 3.46% to 3.38% (mid-band; red at 2.8%); NII/assets stable at 3.5%; the 3-year NII CAGR is unscored (merger window) | threshold: no 1-year NII growth metric for banks, and an 8 bp fall is inside the band |
| BAJFINANCE-W2 | Rising borrowing cost, deposits -4% | Computed cost of funds 7.3% and deteriorating, but it has no band; deposit share is a neutral metric | missing data (cost of borrowing KPI not found) |
| HINDUNILVR-S1 | Volume recovery, Q4 +6% | FY26 volume growth 4% (AMBER) | missing data: no quarterly volume KPI (annual vs quarter) |
| HINDUNILVR-W2 | Input-cost margin pressure | FY26 gross margin -0.5pp, Q4 EBITDA margin -0.4pp, both inside bands | threshold, and partly forward-looking |
| ULTRACEMCO-S2 | EBITDA/t +11% in Q4 | Rs 1,102/t in FY26 (+19% on FY25) is mid-band; the vs-cycle-average metric is context for cyclicals | metric definition: no scored per-tonne growth |
| MARUTI-W3 | Rising costs, heavy capex | Annual gross margin stable at 25.9%; capex 1.5x depreciation and falling | threshold and timing (a quarterly, forward-looking concern) |
| NTPC-S2 (contradicted) | Steady regulated core RoE 16-17% | Consolidated core ROE 9.3% (RED) | metric definition: consolidated book ROE (CWIP, JVs; FY26 tax write-back removed without the regulatory income offset Screener does not separate) vs standalone regulated RoE |
| DMART-W2 | Gross margin squeeze | Gross margin 11.4% and EBITDA margin 7.5%, both stable | the data contradict the claim; sources conflict |
| DMART-W3 | Rising debt, inventory, slower turnover | Inventory days 35 (stable), net debt/equity 0.09x, asset turnover improving; revenue per sq ft missing | the data contradict the claim; store-area KPI missing |
| BHARTIARTL-W3 | Leverage incl. leases and spectrum dues | Net debt/EBITDA 1.4x (GREEN, improving); lease and spectrum KPIs missing | missing data |

There are 11 qualitative misses: TCS-W2, HDFCLIFE-S3, ASIANPAINT-W2, TATASTEEL-S3/W1/W2, ULTRACEMCO-W3, SUNPHARMA-S1/W2
and MARUTI-S2/W2. These are segment, regulatory and competitive items that a financial diagnosis does not see.

## 7. Remaining false alarms and their causes

| Company | Headline item | Cause | Why it is wrong |
|---|---|---|---|
| HDFC Bank | R05 ROE below Ke; `roe` RED; V03 P/B vs justified | metric definition (Ke) | Ke = 7.41% G-sec + beta x 6.92% ERP is about 15.8%, above analysts' 12-13%. P/B 1.9x is near the bottom of its own history |
| Maruti | `ev_ic_to_roic_wacc`, `pb_to_justified_pb` RED | metric definition | Single-stage tests at a 13.6% WACC; equity includes Rs 77,000 cr of treasury. The growth-aware test does not flag it |
| NTPC | R01, `regulated_roe_gap`, A07, V03 (+ automatic S2) | missing sector logic | Consolidated returns include CWIP that earns only after commissioning; regulated RoE is not modelled |
| Hindustan Unilever | `q_pat_yoy` +21% as a strength | missing data | Q4 PAT includes the Nutritionalab stake-sale gain; quarterly exceptional items are not separable |
| Tata Steel | B04 liquidity squeeze | metric definition | No debt-maturity split, so all borrowings count as short-term |
| Sun Pharma | `fcf_to_pat` 0.25 | metric definition | Capex proxy (change in net block + CWIP + depreciation) counts acquired intangibles (Checkpoint, in-licensing) and the currency translation of overseas assets |
| BEL | Q06 Beneish "manipulator zone" | metric definition | Driven by government-customer receivables, already flagged as working capital; no manipulation concern |
| Adani Enterprises | `share_count_change` -0.1% as a strength | parsing | Screener's adjusted shares absorb the FY26 rights issue; reported shares rose 12% |
| Infosys (holdout) | INFY-S2 contradicted: book-to-bill 0.74x RED | threshold | Infosys discloses large-deal TCV only, so TCV/revenue below 1 is normal for it. Found after holdout scoring, not fixed |

**Cost-of-equity sensitivity.** The Session 1 spec sets rf = the G-sec yield. `rf_net_of_default_spread: true` in
`config/market.yaml` gives a Damodaran-consistent Ke, 1.75pp lower. Re-running everything with it:
- The test hit rate is 74/96 (77%), one lower: Bajaj Finance's "valuation rich" (W3) flips to contradicted once its
  P/B falls below the justified P/B.
- HDFC Bank's R05 clears, but its ROE of 13.7% still sits below a 14.0% Ke, so `roe` and V03 remain.

So Ke is not the main cause of the valuation false alarms, and the spec default is kept.

## 8. Holdout (ICICI Bank, Infosys, Nestle India, HAL)

| | Hit rate | Excl. qualitative | Headline |
|---|---|---|---|
| Before fixes (baseline engine, iteration 0) | 13/24 (54%) | - | - |
| After fixes (final engine, `--fy-end`) | 15/24 (62%) | 15/20 (75%) | 9/24 (38%) |

The holdout improved by about as much as the test set did over the same changes (54% to 62%, against 64% to 78%). That
suggests the fixes generalise rather than fit the 16 test companies.

Holdout misses after the fixes:
- ICICIBANK-W1: NIM compression, but the NIM KPI is missing.
- ICICIBANK-W2: opex growth, but cost-to-income has no band.
- NESTLEIND-W3: capex rising, but the capex ratios are context only.
- HAL-W3: lumpy execution, but the data show low revenue volatility.
- INFY-S2: contradicted (book-to-bill, section 7).
- 4 qualitative items.

## 9. Blow-up test: Yes Bank as of FY18

3/5 (60%) of the warning signs are flagged, all from data published by May 2018:
- **W1, hyper growth beyond capital.** Matched: advances +54%; A06 assets +45% against 15% internal capital generation;
  B06 and B07 also fire.
- **W2, thin core capital.** Matched: CET1 9.7% (AMBER) and B06. CRAR 18.4% is no longer listed as a strength while B06
  stands.
- **W4, credit-deposit ratio above 100%.** Matched once FY18 deposits (Rs 2,00,738 cr) were sourced: CD ratio 101% and
  BK07 fires.
- **W3, reported asset quality unreliable.** Still a miss. Reported GNPA of 1.3% looks clean. The new rule BK09 (RBI
  divergence of Rs 6,355 cr against reported GNPA, 244%) fires and keeps GNPA, credit cost, ROA and PAT growth off the
  strengths list. BK09 was not a pre-registered signal, so W3 is not counted; with it the blow-up score would be 4/5.
- **W5, borrower concentration.** Qualitative.

## 10. Reliability by archetype

From most to least reliable, judged on non-qualitative hit rate, false alarms and headline rate. Every tier rests on one
or two companies.

1. **Most reliable: real estate, capital goods and defence, holdco, IT services, insurance, consumer manufacturing.**
   - All non-qualitative items match, and there are 0-1 false alarms.
   - Sector modules carry the right KPIs: pre-sales and collections, order book, TCV and attrition, VNB and solvency.
   - The holdout agrees for capital goods (HAL 3/4) and IT (Infosys 3/4).
2. **Reliable: NBFC, telecom, pharma, metals, cement, retail, FMCG.**
   - One or two misses, or one false alarm, each.
   - Telecom and pharma have weak headline rates: the right signal is computed but not ranked into the top lists.
   - Retail's misses are cases where the data contradict the commentary.
   - FMCG misses quarter-level volume and one-off gains.
3. **Least reliable: banks, auto, utilities.**
   - Banks: ROE and valuation tests hinge on a Ke above market practice (HDFC Bank, 3 false alarms). The NIM signal
     needs the NIM KPI and a growth metric (ICICI holdout 4/6).
   - Auto: cash-rich balance sheets break the single-stage valuation tests (2 false alarms), and cost concerns are
     quarterly.
   - Utilities: regulated returns are not modelled. Consolidated ROE and ROIC read as value destruction for a regulated
     compounder (4 false alarms and 1 contradiction).

## 11. Limitations

- **Small samples.** Each archetype has one test company and six items, so archetype rates are indicative. Signals were
  chosen by meaning, but a different but equally valid signal choice would move single items.
- **Unverified KPIs.** Manual KPIs come from web search and nearly all are `verified = N`. They are cited but not checked
  against the primary document.
- **Qualitative items** (16 of 125) are outside a financial diagnosis by design.
- **Quarter vs year.** Much commentary is about the latest quarter. The engine reads quarters for revenue, PAT and
  margin, but KPIs and most rules are annual.
- **Valuation.** Single-stage justified P/B and EV/IC are growth-blind. The G-sec-based Ke runs above market practice
  for banks (section 7).
- **Regulated utilities.** Returns are measured on consolidated book capital, not regulated equity. The FY19 and FY26
  tax write-backs are normalised, but the matching regulatory income reversal cannot be separated.
- **Export limits:**
  - no debt-maturity split, so B04 treats all debt as short-term
  - no separate capex or acquisitions line, so acquired intangibles count as capex
  - Screener's adjusted share basis can absorb rights issues
  - quarterly exceptional items are not separable
- **Rules added after pre-registration** (BK09, the not_for switches, suppression) are not counted toward matches they
  would earn. They are judged only through false alarms.
- **One adjudicator.** The adjudication is a single reviewer's reading of the cited sources. Every verdict and reason is in
  `validation/adjudication.yaml` for anyone to dispute.
