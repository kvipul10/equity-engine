# BAJFINANCE (BAJAJ FINANCE LTD): standardisation notes

- Archetype: `nbfc` (bank-like); years FY17-FY26 (10); latest quarter 2026-09-30; consolidated (inferred): True
- Source: `BAJFINANCE.xlsx` sha256 `2b5a22a1198b0859...`, Screener template v2.1, units Rs crore

## source
- Source file BAJFINANCE.xlsx; sha256 2b5a22a1198b0859...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
- Data Sheet has 2 formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed.

## units
- Units: Rs crore. Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.

## semantics
- Bank-like mapping: Sales = interest earned (NBFC: revenue from operations); Interest = interest expended; Borrowings = deposits + borrowings (NBFC: borrowings); Other Assets include advances/loans; Other Expenses include provisions & contingencies (credit costs are not separable in the export); CFO is driven by loan/deposit flows and is not an earnings-quality signal.

## missing
- Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet identities hold on that basis). Blank price or share count = missing.

## exceptional
- Financial company: other income is core (fees, treasury), so no exceptional-item estimate is made.

## minority
- Net profit differs from PBT - tax in 2 of 10 years (latest -315): minority interest (negative) and share of associates/JVs (positive) sit between PBT and net profit, so the export is consolidated and net profit is the owners' share. Equity excludes minority interest (Screener includes NCI in Other Liabilities); ROIC/ROCE capital therefore omits NCI unless data/manual supplies minority_interest.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## shares
- Per-share history is split/bonus/rights-adjusted by Screener (adjusted shares / reported shares: FY17 x10.06, FY18 x10.05, FY19 x10.02, FY20 x10.03, FY21 x10.02, FY22 x10.04, FY23 x10.02, FY24 x10.02, FY25 x10.00). EPS, BVPS, DPS and FY-end prices all use the adjusted basis, so ratios are unaffected; per-share levels are in today's share units (a unit look-ahead, not an information look-ahead).

## market
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-09-30).

## quarterly
- 10 quarters from 2024-06-30 to 2026-09-30 (Q1FY25-Q2FY27). Quarterly profit is as reported (no exceptional-item estimate).
