# PLAN: Session 2, sector modules

**Status:** waiting for your OK. Session 1 is merged (`main` @ 539f279). Its plan is archived in `docs/plans/session1_plan.md`.

---

## 0. Starting point (what Session 2 changes in Session 1)

| Session 1 piece | Today | Session 2 change |
|---|---|---|
| `config/sectors.yaml` | archetype → family + Damodaran industries | **Replaced** by `config/sectors/<archetype>.yaml` (one file per archetype, with inheritance) |
| `engine/registry.py` | 146 Python-defined metrics, family tokens | Also registers **sector metrics defined in YAML** (formula + equation + meaning). Still defined once; `docs/metrics.md` lists both kinds |
| `engine/scoring.py` `find_band` | archetype bands > Damodaran > family > generic | **Sector file bands first**, then Damodaran, then generic. Pillar weights can be set per archetype |
| `config/flags.yaml` | 54 generic rules | Plus **sector rules** in each sector file (same schema, ids prefixed by sector) |
| `config/drivers.yaml` | ROE/ROIC/EPS/financial trees | Plus **sector trees**, e.g. bank DuPont with provisions split out, which **replaces** `fin_roe` for lenders |
| `data/manual/<T>_kpis.csv` | `period,kpi,value,unit,source` | **v2 format** `metric,fiscal_year,value,unit,source_url,source_date,verified` (v1 still read). Provenance flows into the report |
| `engine/benchmarks.py` | reads `sectors.yaml` | Reads `config/sectors/*.yaml`. New `chemicals` archetype |

## 1. Sector config architecture

```
config/sectors/
  default.yaml                  base for every archetype: universal KPIs (promoter holding/pledge), no switch-offs
  _cyclical.yaml                shared base (not an archetype): through-cycle metrics for metals/cement/chemicals
  bank.yaml   nbfc.yaml (extends bank)   insurance.yaml
  it_services.yaml  fmcg.yaml  consumer_manufacturing.yaml (extends fmcg)
  metals.yaml  cement.yaml  chemicals.yaml  (all extend _cyclical)
  auto.yaml  pharma.yaml  capital_goods_defence.yaml  real_estate.yaml
  utilities.yaml  telecom.yaml  retail.yaml  holdco.yaml
```

Each file has the same sections. Inheritance is single (`extends:`): lists merge by `id`, dicts merge by key, and the child wins.

```yaml
archetype: bank
extends: default
family: bank_like            # non_financial | bank_like | insurance (drives the Session-1 metric families)
subtype: bank
damodaran_industries: ["Bank (Money Center)"]
how_to_read: |               # 3-5 lines, printed in the report
metrics_off:                 # registry metrics invalid for the sector: not computed, not scored, listed with reason
  - {id: ebitda_margin, reason: "Banks have no EBITDA; spread income is the operating line"}
metrics_add:                 # sector metrics, defined once (formula in the safe expression language)
  - id: credit_cost
    name: Credit cost
    pillar: cash_quality     # one of the 8 pillars; asset quality = earnings quality for lenders
    unit: pct
    direction: lower
    formula: "kpi('provisions_cr') / avg_kpi('advances_cr')"
    equation: "Provisions & contingencies / average advances"
    meaning: "..."
manual_kpis:                 # fields this sector needs from annual reports / investor presentations
  - {id: provisions_cr, unit: "Rs cr", required: true, description: "...", where: "P&L, provisions and contingencies"}
bands:                       # sourced + dated, or flagged 'indicative'
  crar: {red: 0.115, green: 0.15, source_type: external, source_url: "<RBI>", as_of: "..."}
  credit_cost: {green: 0.008, red: 0.02, source_type: indicative, rationale: "...", as_of: "2026-11-01"}
flags: [...]                 # sector red flags, same schema as config/flags.yaml
drivers: {add: [...], replace: {fin_roe: bank_dupont}}
pillar_weights: {...}        # optional override of config/scoring.yaml
```

**Sector-metric formula language.** This extends the Session 1 safe evaluator, which still never calls `eval`.
- **Evaluation:** formulas are evaluated **for each fiscal year t**, so trend and stability scoring work unchanged.
- **Functions:** `f(field, lag)`, `kpi(name, lag)`, `m(metric, lag)`, `avg_f/avg_kpi` (opening/closing average), `growth(x, years)`, `cagr(x, n)`, `mean_last(x, n)`, `min_last/max_last`, `at_min(x, y, n)` ("y in the year x was lowest", e.g. leverage at trough).
- **Missing input:** gives NaN for that year, and the metric reports which KPI is missing.

## 2. Sector content (minimum set from the brief, plus a few needed for consistency)

KPI = required manual field. Bands use these markers: **E** = external (published, URL + date); **I** = indicative.

| Archetype | Switched off (invalid) | Sector metrics added | Required KPIs | Sector flags (examples) | Bands | Driver tree |
|---|---|---|---|---|---|---|
| **bank** | All EBITDA/working-capital/capex metrics (listed explicitly); `credit_deposit_proxy` (replaced) | NIM (reported), yield on advances, cost of funds (reported), cost-to-income **ex-provisions**, credit cost, GNPA, NNPA, PCR, CRAR, CET1, CASA, loan growth, deposit growth, CD ratio, provisions/PPOP. **Bank DuPont:** RoA = NII/A + Fees/A − Opex/A − Provisions/A − Tax/A (+ minority/associates/A); RoE = RoA × A/E | advances, deposits, CASA %, GNPA %, NNPA %, PCR %, CRAR %, provisions | GNPA up 2y and > 3%; PCR < 60% or falling; CRAR < 13%; credit cost > 2%; loans +25% while CRAR falls; CASA −3pp in 2y; CD > 90%; provisions > 50% of PPOP | CRAR (E: RBI Basel III minimum 11.5% incl. CCB); PCR (E: RBI 70% benchmark); GNPA/NNPA/CASA/cost-to-income (E: RBI FSR system levels); credit cost (I) | `bank_dupont` replaces `fin_roe` when provisions are supplied (else falls back, with a note) |
| **nbfc** (extends bank) | CASA, deposit metrics optional | + spread (yield on AUM − cost of borrowing), ALM gap (≤1y cumulative mismatch), borrowing mix (bank / market NCD+CP / deposits / other), AUM growth − equity growth, stage-2 %, stage-3 %, stage-3 coverage | AUM, stage-2 %, stage-3 %, NS3 %, CRAR %, borrowing mix, ALM gap, provisions | AUM outgrows equity +15pp for 2y; stage 2 rising; CP > 10% of borrowings; negative ALM gap; GS3 up | CRAR 15% (E: RBI SBR); NNPA 6% (E: RBI PCA for NBFCs); ALM bucket caps (E: RBI liquidity framework 2019); rest I | `bank_dupont` (provisions = impairment) |
| **insurance** | yield/opex/liquidity on assets, equity/assets, justified P/B, P/B-implied g (insurers are valued on EV) | VNB margin, VNB growth, EV growth, operating RoEV, persistency 13m/61m, solvency ratio, opex ratio, combined ratio (GI), APE growth, **P/EV** | VNB, VNB margin %, EV, solvency %, persistency 13m/61m %, APE | Solvency < 170%; 13m persistency −3pp; VNB margin −3pp; P/EV rich vs RoEV | Solvency 150% (E: IRDAI control level); combined ratio 100% (E: definition); rest I | none (insufficient identity) |
| **it_services** | gross margin, materials %, DIO, operating cycle | CC growth, utilisation, attrition, deal TCV + book-to-bill, DSO **incl. unbilled**, revenue per employee | CC growth %, utilisation %, attrition %, TCV, unbilled revenue, headcount | Attrition > 20%; utilisation < 80%; CC growth < 3%; DSO+unbilled up 2y; TCV down | I (NASSCOM-style norms where a source exists) | – |
| **fmcg** | – | Volume growth, price/mix growth (revenue − volume), A&P %, gross-margin vs commodity (5y pass-through beta), negative-WC check (NWC days band ≤ 0) | volume growth %, A&P spend, commodity index (analyst-chosen, documented) | Price-led growth with negative volume; A&P cut while gross margin rises; NWC turns positive | I | – |
| **consumer_manufacturing** (extends fmcg) | – | as fmcg | as fmcg | as fmcg | I | – |
| **metals / cement / chemicals** (extend _cyclical) | revenue-growth volatility (cyclical noise; through-cycle metrics replace it) | 10y-average EBITDA margin and ROCE, EBITDA per tonne, capacity utilisation, **leverage at trough year**, capex at peak (capex/dep when margin > 10y avg) | sales volume (t), production, capacity | Leverage at trough > 4x; expanding at cycle peak; utilisation < 70%; EBITDA/t 30% below 10y avg | Leverage 4x (E: S&P); utilisation, EBITDA/t (I) | EBITDA = volume × EBITDA/t |
| **auto** | – | Volume growth, realisation per unit, realisation growth, capex cycle (capex/sales vs 10y avg) | units sold | Volumes falling while capex above cycle average; realisation falling | I | Revenue = units × realisation |
| **pharma** | – | R&D %, US share, India share, ANDA pipeline (pending), specialty share | R&D spend, US revenue, India revenue, ANDAs pending | R&D cut > 1pp; US share falling with pipeline shrinking; FDA actions (optional KPI) | I | – |
| **capital_goods_defence** | – | Order book / revenue, book-to-bill, execution rate, customer advances / revenue | order book, order inflow, customer advances | Book-to-bill < 1 for 2y; order book < 2x revenue; advances falling | I | Revenue = opening order book × execution rate |
| **real_estate** | DIO, DSO, operating cycle, CCC, NWC days, asset/fixed/IC turnover, DOL, capex/sales, capex/dep, receivables-vs-revenue (P&L lags; land is inventory) | Pre-sales growth, collections / pre-sales, **inventory months**, CFO / collections, CFO / pre-sales, net debt / pre-sales | pre-sales, collections, unsold inventory value (area optional) | Collections < 70% of pre-sales; inventory months > 24 and rising; CFO < 0 while pre-sales grow; net debt up while pre-sales fall | I (published inventory-overhang norms where found) | **CFO = pre-sales × collections/pre-sales × CFO/collections** |
| **utilities** | – | ROE − allowed ROE (regulated-return framing), discom receivable days, D/E vs normative 70:30, PLF, capacity growth | installed capacity, generation, PLF, discom receivables (or days), regulated equity | ROE > 3pp below allowed; receivables > 90 days; D/E above normative | Allowed ROE 15.5% and 70:30 (E: CERC Tariff Regulations 2024-29); 45-day payment (E: MoP LPS Rules 2022) | – |
| **telecom** | gross margin, materials %, DIO, operating cycle | ARPU growth, subscriber growth, capex/sales (sector band), lease + spectrum share of debt, EBITDA after leases | ARPU, subscribers, capex, lease liabilities, spectrum liabilities | ARPU falling; net debt incl. spectrum/EBITDA > 3.5x; capex/sales > 35% | Leverage (E: S&P); rest I | – |
| **retail** | – | Revenue per sq ft, same-store growth, store additions, **lease-adjusted (pre-Ind AS 116) EBITDA margin**, lease-adjusted net debt / EBITDA | store count, retail area, LFL growth, lease payments | SSSG below inflation 2y; revenue/sq ft falling while store additions accelerate; lease-adjusted margin down 2y | I | Revenue = avg area × revenue/sq ft |
| **holdco** | – | Segment concentration, standalone share of PAT, standalone net debt/equity, consolidated − standalone ROE, **holding-company discount** = 1 − mcap ÷ (listed stakes + standalone net cash) | segment revenue/EBITDA, standalone PAT, standalone net worth/debt, value of listed stakes | Standalone leverage rising; guarantees/contingent liabilities > 50% of net worth; discount/premium vs history | I | – |
| **default** | – | – | promoter holding %, pledge % | – | – | – |

**`how_to_read`.** Each file carries 3–5 lines on how to read the sector, for example: "Banks: judge earnings after credit costs, not before. NIM × leverage drives RoE, and asset quality and capital decide whether it lasts. Read GNPA, PCR and CRAR before profit growth."

**Pillar weights.** Lenders get pillar 5 relabelled *cash and earnings quality (asset quality)* with weight 15 (it was 0 in Session 1). Real estate shifts weight from margins to cash quality.

## 3. Bands policy

- **Lookup order:**
  1. sector file (including inherited)
  2. `sector_benchmarks.yaml` (Damodaran)
  3. `bands.yaml` generic
- **`source_type`:**
  - `external`: needs `source_url` + `as_of`.
  - `indicative`: needs `rationale` + `as_of`, and is shown as **indicative** in every report.
  - `derived`: computed from market inputs.
  - Session 1's `rule_of_thumb` is renamed `indicative`; the old name is still accepted.
- **External sources to pin during the build, via web search with URL + date:**
  - RBI: Basel III CRAR/CCB, PCR benchmark, FSR/Trend & Progress system GNPA/NNPA/CASA/cost-to-income/credit-deposit ratio
  - RBI NBFC: SBR CRAR, PCA thresholds, liquidity-risk framework
  - IRDAI solvency control level
  - CERC Tariff Regulations 2024-29 (ROE, D/E)
  - MoP Late Payment Surcharge Rules 2022

  If a published figure can't be pinned, the band ships as `indicative`, never with an invented source.

## 4. Manual KPIs (tasks 2 and 3)

- **Format v2** (exactly as requested): `metric,fiscal_year,value,unit,source_url,source_date,verified`.
  - `unit` = `%` means a percent number (1.33 = 1.33%).
  - A blank `value` means "not found", which is allowed.
  - `verified` = **Y** only if I opened the cited primary document (annual report / investor presentation / exchange filing) and saw the number; **N** = taken from a secondary source or a search summary.
- **Templates:** `python -m engine kpi-templates` writes `data/manual/templates/<archetype>_kpis.csv` from the sector configs: every manual KPI (inherited ones included) × FY22–FY26, with blank values. It is deterministic, so templates never drift from configs (a test checks this).
- **Loader:** reads v1 and v2. Each value carries its provenance into `analysis.json` (`manual_kpis` section: value, unit, source_url, source_date, verified). Manual-only years before the export's first year (YESBANK FY14–FY16) extend the timeline with export fields left as NaN, so KPI trends work as of FY18. As-of truncation still applies.
- **Filling (task 3):** 21 companies × FY22–FY26, plus YESBANK FY14–FY18, by web search of annual reports, investor presentations and results coverage.
  - **Rules:**
    - Only values explicitly stated in a source, with that source's URL and date.
    - Year-end stock or ratio values are taken as at 31 March; annual flows are taken for the full year, never one quarter.
    - Nothing is derived or estimated; blanks are allowed.
  - **Expected volume:** about 1,000 values, done company by company and committed after each one.
  - **Calibration (one test search, HDFC Bank FY25):** it returned GNPA 1.33%, NNPA 0.43%, CASA 34.8% and CRAR 19.6% from Business Standard and aggregators. It showed a quarter-vs-year trap (the provisions figure was Q4-only) and no PCR. Expect high coverage for banks, the insurer and IT, and patchier coverage elsewhere.
  - **Coverage report:** `data/manual/COVERAGE.md`, found/blank per company × KPI.
  - **Priority:** first the KPIs that drive sector metrics, bands, flags and trees (the "required" ones above); then optional ones if time allows.

## 5. Wiring

- **Registry/metrics:**
  - Sector metrics register at load with `applies = [archetypes using them]`.
  - `metrics_off` removes metrics for that archetype from computation, scoring and pillars; the report lists them with the reason.
- **Scoring:** the new band lookup order, per-archetype pillar weights, and an "indicative" marker on the level basis.
- **Flags:** generic rules plus sector rules, with ids like `BK01`, `NB01`, `IN01`, `IT01`, `FM01`, `CY01`, `AU01`, `PH01`, `CG01`, `RE01`, `UT01`, `TC01`, `RT01`, `HC01`. Rules whose KPIs are missing report "not evaluable: provisions_cr (manual KPI)".
- **Drivers:** sector files `add` trees or `replace` generic ones, with an automatic fallback when the required KPIs are missing (logged).
- **Report:** a new `sector` section containing:
  - `how_to_read`
  - switched-off metrics
  - required KPIs that are missing
  - KPI provenance and verification share
  - which bands are indicative

  The console summary gains one sector line.

## 6. Tests (all existing tests keep passing)

- **Bank path:** a synthetic bank with a full KPI file.
  - Every bank metric is checked by hand.
  - **Bank DuPont identity:** RoA = NII/A + Fees/A − Opex/A − Prov/A − Tax/A + MI/A, exact to 1e-12. The `bank_dupont` tree replaces `fin_roe` and is exact, and it falls back to `fin_roe` when provisions are removed.
  - EBITDA/WC metrics are off; sector bands win over generic ones; sector flags trigger (CRAR, GNPA, PCR); missing KPIs make them not evaluable.
- **Real-estate path:** a synthetic developer with pre-sales/collections/inventory KPIs.
  - Metrics are checked by hand.
  - The switch-offs are applied.
  - The CFO tree is exact.
  - Flags trigger (collections < 70%, inventory months rising).
- **Config integrity:**
  - All 18 archetype files load and `extends` resolves.
  - Every sector metric formula compiles, and every metric/tree node referenced exists for that archetype.
  - External bands have URL + date; indicative bands have a rationale.
  - Templates match the configs.
- **Data files:**
  - Every non-blank KPI value has `source_url` + `source_date` and `verified` ∈ {Y, N}.
  - Metric ids exist in the sector config.
  - Fiscal years are valid.
- **As-of:** the no-look-ahead proof is extended to sector metrics, KPIs and manual-only years.

## 7. Order of work

1. Engine + configs + templates + tests, then commit and push.
2. Band sourcing, committed.
3. KPI collection, one commit per company.
4. `analyse-all`, regenerate docs, run tests.
5. PR **"Session 2: Sector modules"**.

## 8. Decisions (defaults in bold; say "OK" to accept all)

1. **Primary-source access for task 3.** Only search works today. Without primary access, every value will be `verified = N`, sourced from news/aggregator pages that cite the companies' results.
   - **Default: I proceed with search only.**
   - Optional: to let me open annual reports/presentations and mark values `Y`, add these under Network access → Allowed domains:
     - Exchanges: `bseindia.com`, `nseindia.com`
     - Company IR sites: `hdfcbank.com`, `icicibank.com`, `bajajfinserv.in`, `hdfclife.com`, `tcs.com`, `infosys.com`, `hul.co.in`, `nestle.in`, `asianpaints.com`, `tatasteel.com`, `ultratechcement.com`, `marutisuzuki.com`, `sunpharma.com`, `bel-india.in`, `hal-india.co.in`, `dlf.in`, `ntpc.co.in`, `airtel.in`, `dmartindia.com`, `adanienterprises.com`, `yesbank.in`
2. **Unverified (N) values are used in scoring.** The report shows the verification share. Alternative: score only Y values.
3. **No parallel research agents.** I collect the data inline, one company at a time, which is slower. Say so if you want agents for speed.
4. **`config/sectors.yaml` is removed; its content moves into `config/sectors/*.yaml`.**
5. **`rule_of_thumb` is renamed `indicative` everywhere.** The old name keeps working.

## 9. Known gaps after Session 2

- Values sourced only from search are unverified until checked against primary documents.
- Optional KPIs will be sparse.
- `chemicals` has no company in the universe, so its config is tested only synthetically.
- Segment-level SOTP for the holdco needs listed-stake values, which may be incomplete.
- "Commodity index" for FMCG is analyst-chosen per company and will often be blank.
