# ADANIENT (ADANI ENTERPRISES LTD): standardisation notes

- Archetype: `holdco` (non-financial); years FY17-FY26 (10); latest quarter 2026-09-30; consolidated (inferred): True
- Source: `ADANIENT.xlsx` sha256 `d1fc932a1718da61...`, Screener template v2.1, units Rs crore

## source
- Source file ADANIENT.xlsx; sha256 d1fc932a1718da61...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
- Data Sheet has 2 formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed.

## units
- Units: Rs crore. Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.

## semantics
- Screener puts exceptional items inside Other Income (PBT = Sales - Expenses + Other income - Dep - Interest holds exactly). Other income is split into core and estimated exceptional (see 'exceptional').

## missing
- Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet identities hold on that basis). Blank price or share count = missing.

## exceptional
- **FY25**: Estimated exceptional item 5,179 (pre-tax, gain): other income 6.5% of sales vs normal 1.3% (median of other years). Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).
- **FY26**: Estimated exceptional item 10,432 (pre-tax, gain): other income 11.6% of sales vs normal 1.3% (median of other years). Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).

## minority
- Net profit differs from PBT - tax in 10 of 10 years (latest -354): minority interest (negative) and share of associates/JVs (positive) sit between PBT and net profit, so the export is consolidated and net profit is the owners' share. Equity excludes minority interest (Screener includes NCI in Other Liabilities); ROIC/ROCE capital therefore omits NCI unless data/manual supplies minority_interest.

## lease
- **FY20**: Ind AS 116 adoption year FY20: no visible step in depreciation/opex/interest ratios.

## merger
- **FY22**: Balance-sheet step change: total assets +97% in one year (acquisition, consolidation change or large capital raise). Growth across FY21->FY22 may not be organic.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## shares
- Per-share history is split/bonus/rights-adjusted by Screener (adjusted shares / reported shares: FY17 x1.12, FY18 x1.12, FY19 x1.12, FY20 x1.12, FY21 x1.12, FY22 x1.12, FY23 x1.12, FY24 x1.12, FY25 x1.12). EPS, BVPS, DPS and FY-end prices all use the adjusted basis, so ratios are unaffected; per-share levels are in today's share units (a unit look-ahead, not an information look-ahead).

## market
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-09-30).

## quarterly
- 10 quarters from 2024-06-30 to 2026-09-30 (Q1FY25-Q2FY27). Quarterly profit is as reported (no exceptional-item estimate).

## manual
- Manual KPIs loaded: standalone_pat_cr for FY25, FY26.
- 2 manual KPI values: 0 verified against the primary document (Y), 2 from secondary sources (N). Provenance is in analysis.json (manual_kpis).
