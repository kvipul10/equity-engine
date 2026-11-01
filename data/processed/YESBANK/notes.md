# YESBANK (YES BANK LTD): standardisation notes

- Archetype: `bank` (bank-like); years FY17-FY26 (10); latest quarter 2026-09-30; consolidated (inferred): False
- Source: `YESBANK.xlsx` sha256 `a97a2aeb512bb819...`, Screener template v2.1, units Rs crore

## source
- Source file YESBANK.xlsx; sha256 a97a2aeb512bb819...; Screener template version 2.1. Only the 'Data Sheet' is read (display sheets are formulas without cached values).
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
- No material minority/associate residual: export is standalone or has no minorities.

## capex
- Capex is not in the export. Proxy = change in net block + change in CWIP + depreciation (includes acquired fixed assets and Ind AS 116 right-of-use additions; impairments and disposals understate it). FCF = CFO - capex proxy.

## shares
- Per-share history is split/bonus/rights-adjusted by Screener (adjusted shares / reported shares: FY17 x5.00). EPS, BVPS, DPS and FY-end prices all use the adjusted basis, so ratios are unaffected; per-share levels are in today's share units (a unit look-ahead, not an information look-ahead).

## market
- Current price and market cap are as of the export date, which the file does not record (latest quarter in file: 2026-09-30).

## quarterly
- 10 quarters from 2024-06-30 to 2026-09-30 (Q1FY25-Q2FY27). Quarterly profit is as reported (no exceptional-item estimate).

## manual
- Manual KPIs loaded: advances_cr, casa_pct, cet1_pct, crar_pct, deposits_cr, gnpa_pct, nnpa_pct, npa_divergence_cr, pcr_pct, provisions_cr for FY14, FY15, FY16, FY17, FY18, FY22, FY23, FY24, FY25, FY26.
- 63 manual KPI values: 0 verified against the primary document (Y), 63 from secondary sources (N). Provenance is in analysis.json (manual_kpis).
- Manual KPI years FY14, FY15, FY16 precede the export (FY17): added as KPI-only rows (all export fields blank) so KPI trends cover them.
