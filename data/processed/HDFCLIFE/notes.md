# HDFCLIFE (HDFC LIFE INSURANCE COMPANY LTD): standardisation notes

- Archetype: `insurance` (insurance); years FY17-FY26 (10); latest quarter 2026-09-30; consolidated (inferred): False
- Source: `HDFCLIFE.xlsx` sha256 `37cf4508798ac857...`, Screener template v2.1, units Rs crore

## source
- Source file HDFCLIFE.xlsx; sha256 37cf4508798ac857...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
- Data Sheet has 2 formula cell(s) without cached values (e.g. 'Number of shares'); recomputed where needed.

## units
- Units: Rs crore. Share counts in crore (Screener 'Adjusted Equity Shares in Cr'); prices in Rs.

## semantics
- Insurance mapping: Sales = premium + investment income; Other Mfr. Exp = benefits paid + change in valuation of policy liabilities; Other Liabilities = policyholders' funds; Investments include policyholders' investments.

## missing
- Blank line items are treated as zero (Screener leaves zero items blank; the P&L and balance-sheet identities hold on that basis). Blank price or share count = missing.

## exceptional
- Financial company: other income is core (fees, treasury), so no exceptional-item estimate is made.

## minority
- No material minority/associate residual: export is standalone or has no minorities.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## market
- **FY17**: No FY-end price (e.g. not yet listed): market multiples for this year are missing.
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-09-30).

## quarterly
- 10 quarters from 2024-06-30 to 2026-09-30 (Q1FY25-Q2FY27). Quarterly profit is as reported (no exceptional-item estimate).
