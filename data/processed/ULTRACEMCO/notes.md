# ULTRACEMCO (ULTRATECH CEMENT LTD): standardisation notes

- Archetype: `cement` (non-financial); years FY17-FY26 (10); latest quarter 2026-09-30; consolidated (inferred): True
- Source: `ULTRACEMCO.xlsx` sha256 `5e758f9b1e002f7b...`, Screener template v2.1, units Rs crore

## source
- Source file ULTRACEMCO.xlsx; sha256 5e758f9b1e002f7b...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
- Data Sheet has 2 formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed.

## units
- Units: Rs crore. Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.

## semantics
- Screener puts exceptional items inside Other Income (PBT = Sales - Expenses + Other income - Dep - Interest holds exactly). Other income is split into core and estimated exceptional (see 'exceptional').

## missing
- Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet identities hold on that basis). Blank price or share count = missing.

## exceptional
- **FY17**: Estimated exceptional item 434 (pre-tax, gain): other income 2.6% of sales vs normal 0.8% (median of other years). Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).

## minority
- Net profit differs from PBT - tax in 10 of 10 years (latest -22.71): minority interest (negative) and share of associates/JVs (positive) sit between PBT and net profit, so the export is consolidated and net profit is the owners' share. Equity excludes minority interest (Screener includes NCI in Other Liabilities); ROIC/ROCE capital therefore omits NCI unless data/manual supplies minority_interest.

## lease
- **FY20**: Ind AS 116 (leases) visible in FY20, the first period starting on/after 1-Apr-2019: depreciation/sales +0.5%, other opex/sales -3.0%, interest/sales +0.4% vs FY19. Lease rentals moved out of operating costs into depreciation and interest, so EBITDA margins before and after FY20 are not comparable; lease liabilities sit inside Borrowings.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## market
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-09-30).

## quarterly
- 10 quarters from 2024-06-30 to 2026-09-30 (Q1FY25-Q2FY27). Quarterly profit is as reported (no exceptional-item estimate).
