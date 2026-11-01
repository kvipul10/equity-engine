# INFY (INFOSYS LTD): standardisation notes

- Archetype: `it_services` (non-financial); years FY17-FY26 (10); latest quarter 2026-09-30; consolidated (inferred): True
- Source: `INFY.xlsx` sha256 `a3510de175415f26...`, Screener template v2.1, units Rs crore

## source
- Source file INFY.xlsx; sha256 a3510de175415f26...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
- Data Sheet has 2 formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed.

## units
- Units: Rs crore. Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.

## semantics
- Screener puts exceptional items inside Other Income (PBT = Sales - Expenses + Other income - Dep - Interest holds exactly). Other income is split into core and estimated exceptional (see 'exceptional').

## missing
- Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet identities hold on that basis). Blank price or share count = missing.

## exceptional
- **FY18**: Estimated exceptional item 1,753 (pre-tax, gain): other income 4.7% of sales vs normal 2.2% (median of other years). Core profit excludes it (tax effect at statutory rate). Override via data/manual (exceptional_items).

## minority
- Net profit differs from PBT - tax in 8 of 10 years (latest -34.00): minority interest (negative) and share of associates/JVs (positive) sit between PBT and net profit, so the export is consolidated and net profit is the owners' share. Equity excludes minority interest (Screener includes NCI in Other Liabilities); ROIC/ROCE capital therefore omits NCI unless data/manual supplies minority_interest.

## lease
- **FY20**: Ind AS 116 (leases) visible in FY20, the first period starting on/after 1-Apr-2019: depreciation/sales +0.8%, other opex/sales -1.4%, interest/sales +0.2% vs FY19. Lease rentals moved out of operating costs into depreciation and interest, so EBITDA margins before and after FY20 are not comparable; lease liabilities sit inside Borrowings.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## shares
- Per-share history is split/bonus/rights-adjusted by Screener (adjusted shares / reported shares: FY17 x2.01, FY18 x2.01, FY19 x1.01). EPS, BVPS, DPS and FY-end prices all use the adjusted basis, so ratios are unaffected; per-share levels are in today's share units (a unit look-ahead, not an information look-ahead).

## market
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-09-30).

## quarterly
- 10 quarters from 2024-06-30 to 2026-09-30 (Q1FY25-Q2FY27). Quarterly profit is as reported (no exceptional-item estimate).

## manual
- Manual KPIs loaded: attrition_ltm_pct, cc_revenue_growth_pct, deal_tcv_usd_bn, headcount, revenue_usd_mn, utilisation_pct for FY22, FY23, FY24, FY25, FY26.
- 23 manual KPI values: 0 verified against the primary document (Y), 23 from secondary sources (N). Provenance is in analysis.json (manual_kpis).
