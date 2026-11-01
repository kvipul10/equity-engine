# TATASTEEL (TATA STEEL LTD): standardisation notes

- Archetype: `metals` (non-financial); years FY17-FY26 (10); latest quarter 2026-06-30; consolidated (inferred): True
- Source: `TATASTEEL.xlsx` sha256 `390ac484f2ef9a17...`, Screener template v2.1, units Rs crore

## source
- Source file TATASTEEL.xlsx; sha256 390ac484f2ef9a17...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
- Data Sheet has 2 formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed.

## units
- Units: Rs crore. Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.

## semantics
- Screener puts exceptional items inside Other Income (PBT = Sales - Expenses + Other income - Dep - Interest holds exactly). Other income is split into core and estimated exceptional (see 'exceptional').

## missing
- Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet identities hold on that basis). Blank price or share count = missing.

## exceptional
- **FY17**: Estimated exceptional item -4,240 (pre-tax, loss): other income -3.4% of sales vs normal 0.4% (median of other years). Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).
- **FY18**: Estimated exceptional item 10,507 (pre-tax, gain): other income 8.8% of sales vs normal 0.3% (median of other years). Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).
- **FY20**: Estimated exceptional item -3,445 (pre-tax, loss): other income -2.1% of sales vs normal 0.4% (median of other years). Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).
- **FY24**: Estimated exceptional item -6,925 (pre-tax, loss): other income -2.6% of sales vs normal 0.4% (median of other years). Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).

## minority
- Net profit differs from PBT - tax in 10 of 10 years (latest -91.95): minority interest (negative) and share of associates/JVs (positive) sit between PBT and net profit, so the export is consolidated and net profit is the owners' share. Equity excludes minority interest (Screener includes NCI in Other Liabilities); ROIC/ROCE capital therefore omits NCI unless data/manual supplies minority_interest.

## lease
- **FY20**: Ind AS 116 (leases) visible in FY20, the first period starting on/after 1-Apr-2019: depreciation/sales +1.4%, other opex/sales +2.2%, interest/sales +0.5% vs FY19. Lease rentals moved out of operating costs into depreciation and interest, so EBITDA margins before and after FY20 are not comparable; lease liabilities sit inside Borrowings.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## shares
- Per-share history is split/bonus/rights-adjusted by Screener (adjusted shares / reported shares: FY17 x11.61, FY18 x9.36, FY19 x9.36, FY20 x9.36, FY21 x9.94, FY22 x10.00). EPS, BVPS, DPS and FY-end prices all use the adjusted basis, so ratios are unaffected; per-share levels are in today's share units (a unit look-ahead, not an information look-ahead).

## market
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-06-30).

## quarterly
- 10 quarters from 2024-03-31 to 2026-06-30 (Q4FY24-Q1FY27). Quarterly profit is as reported (no exceptional-item estimate).

## manual
- Manual KPIs loaded: capacity_mtpa, production_mt, sales_volume_mt for FY22, FY23, FY24, FY25, FY26.
- 13 manual KPI values: 0 verified against the primary document (Y), 13 from secondary sources (N). Provenance is in analysis.json (manual_kpis).
