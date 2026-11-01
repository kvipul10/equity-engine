# NESTLEIND (NESTLE INDIA LTD): standardisation notes

- Archetype: `fmcg` (non-financial); years FY17-FY26 (10); latest quarter 2026-09-30; consolidated (inferred): False
- Source: `NESTLEIND.xlsx` sha256 `620af3ceb80d6eff...`, Screener template v2.1, units Rs crore

## source
- Source file NESTLEIND.xlsx; sha256 620af3ceb80d6eff...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
- Data Sheet has 2 formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed.

## units
- Units: Rs crore. Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.

## semantics
- Screener puts exceptional items inside Other Income (PBT = Sales - Expenses + Other income - Dep - Interest holds exactly). Other income is split into core and estimated exceptional (see 'exceptional').

## period
- Some year-ends are not March: FY label = calendar year of the period end (e.g. Dec-2019 -> FY19). Peer comparisons across different year-ends are approximate.
- **FY24**: Period ending 2024-03-31 inferred as 15 months (previous real balance sheet FY22); sales 24,394 vs 19,126 in the preceding column (ratio 1.28, vs 15/12 = 1.25). Flows annualised x12/15.
- **FY24**: FY24 overlaps FY23 (whose balance sheet is stale): year-on-year growth into FY24 compares an annualised 15-month rate with a 12-month period and is understated/approximate.

## stale
- **FY23**: Balance sheet dated 2023-12-31 is an exact copy of the previous column (no real balance sheet at this date); set to missing. The next period's opening balance is taken from the previous real balance sheet.

## missing
- Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet identities hold on that basis). Blank price or share count = missing.

## reclassification
- **FY21**: Negative cost line(s) other_exp=-245: Screener reclassification. Only materials, employee and the sum of all other cost lines (other_opex) are used.
- **FY22**: Negative cost line(s) other_exp=-223: Screener reclassification. Only materials, employee and the sum of all other cost lines (other_opex) are used.
- **FY24**: Negative cost line(s) other_exp=-311: Screener reclassification. Only materials, employee and the sum of all other cost lines (other_opex) are used.
- **FY25**: Negative cost line(s) other_exp=-389: Screener reclassification. Only materials, employee and the sum of all other cost lines (other_opex) are used.
- **FY26**: Negative cost line(s) other_exp=-561: Screener reclassification. Only materials, employee and the sum of all other cost lines (other_opex) are used.

## exceptional
- **FY21**: Estimated exceptional item -273 (pre-tax, loss): other income -0.8% of sales vs normal 1.1% (median of other years). Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).

## minority
- No material minority/associate residual: export is standalone or has no minorities.

## lease
- **FY20**: Ind AS 116 adoption year FY20: no visible step in depreciation/opex/interest ratios.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## shares
- Per-share history is split/bonus/rights-adjusted by Screener (adjusted shares / reported shares: FY17 x20.00, FY18 x20.00, FY19 x20.00, FY20 x20.00, FY21 x20.00, FY22 x20.00, FY24 x2.00, FY25 x2.00). EPS, BVPS, DPS and FY-end prices all use the adjusted basis, so ratios are unaffected; per-share levels are in today's share units (a unit look-ahead, not an information look-ahead).

## market
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-09-30).

## quarterly
- 10 quarters from 2024-06-30 to 2026-09-30 (Q1FY25-Q2FY27). Quarterly profit is as reported (no exceptional-item estimate).

## manual
- Manual KPIs loaded: ad_promo_cr for FY25.
- 1 manual KPI values: 0 verified against the primary document (Y), 1 from secondary sources (N). Provenance is in analysis.json (manual_kpis).
