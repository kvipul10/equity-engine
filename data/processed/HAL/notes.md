# HAL (HINDUSTAN AERONAUTICS LTD): standardisation notes

- Archetype: `capital_goods_defence` (non-financial); years FY17-FY26 (10); latest quarter 2026-06-30; consolidated (inferred): False
- Source: `HAL.xlsx` sha256 `8636ec14fb8dcf61...`, Screener template v2.1, units Rs crore

## source
- Source file HAL.xlsx; sha256 8636ec14fb8dcf61...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
- Data Sheet has 2 formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed.

## units
- Units: Rs crore. Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.

## semantics
- Screener puts exceptional items inside Other Income (PBT = Sales - Expenses + Other income - Dep - Interest holds exactly). Other income is split into core and estimated exceptional (see 'exceptional').

## missing
- Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet identities hold on that basis). Blank price or share count = missing.

## exceptional
- No exceptional items detected in other income (robust outlier test).

## minority
- No material minority/associate residual: export is standalone or has no minorities.

## lease
- **FY20**: Ind AS 116 adoption year FY20: no visible step in depreciation/opex/interest ratios.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## shares
- Per-share history is split/bonus/rights-adjusted by Screener (adjusted shares / reported shares: FY17 x2.00, FY18 x2.00, FY19 x2.00, FY20 x2.00, FY21 x2.00, FY22 x2.00, FY23 x2.00). EPS, BVPS, DPS and FY-end prices all use the adjusted basis, so ratios are unaffected; per-share levels are in today's share units (a unit look-ahead, not an information look-ahead).

## market
- **FY17**: No FY-end price (e.g. not yet listed): market multiples for this year are missing.
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-06-30).

## quarterly
- 10 quarters from 2024-03-31 to 2026-06-30 (Q4FY24-Q1FY27). Quarterly profit is as reported (no exceptional-item estimate).
