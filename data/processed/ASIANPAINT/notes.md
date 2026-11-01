# ASIANPAINT (ASIAN PAINTS LTD): standardisation notes

- Archetype: `consumer_manufacturing` (non-financial); years FY17-FY26 (10); latest quarter 2026-09-30; consolidated (inferred): True
- Source: `ASIANPAINT.xlsx` sha256 `e3cad0e61feab3b8...`, Screener template v2.1, units Rs crore

## source
- Source file ASIANPAINT.xlsx; sha256 e3cad0e61feab3b8...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
- Data Sheet has 2 formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed.

## units
- Units: Rs crore. Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.

## semantics
- Screener puts exceptional items inside Other Income (PBT = Sales - Expenses + Other income - Dep - Interest holds exactly). Other income is split into core and estimated exceptional (see 'exceptional').

## missing
- Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet identities hold on that basis). Blank price or share count = missing.

## reclassification
- **FY17**: Negative cost line(s) other_exp=-2,028: Screener reclassification. Only materials, employee and the sum of all other cost lines (other_opex) are used.

## exceptional
- No exceptional items detected in other income (robust outlier test).

## minority
- Net profit differs from PBT - tax in 10 of 10 years (latest -69.34): minority interest (negative) and share of associates/JVs (positive) sit between PBT and net profit, so the export is consolidated and net profit is the owners' share. Equity excludes minority interest (Screener includes NCI in Other Liabilities); ROIC/ROCE capital therefore omits NCI unless data/manual supplies minority_interest.

## lease
- **FY20**: Ind AS 116 adoption year FY20: no visible step in depreciation/opex/interest ratios.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## market
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-09-30).

## quarterly
- 10 quarters from 2024-06-30 to 2026-09-30 (Q1FY25-Q2FY27). Quarterly profit is as reported (no exceptional-item estimate).

## manual
- Manual KPIs loaded: volume_growth_pct for FY24, FY25.
- 2 manual KPI values: 0 verified against the primary document (Y), 2 from secondary sources (N). Provenance is in analysis.json (manual_kpis).
