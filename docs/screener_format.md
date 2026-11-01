# Screener.in Excel export: actual layout

Inspected on 2026-11-01. All 21 files in `data/raw/screener/` were checked, with three read in detail:
- **ASIANPAINT** (non-financial)
- **HDFCBANK** (bank)
- **HDFCLIFE** (insurer)

BAJFINANCE (NBFC) and NESTLEIND (irregular fiscal calendar) were also examined because they have quirks of their own. All files use Screener template **v2.1**.

## Workbook

| Sheet | Size | Content |
|---|---|---|
| `Profit & Loss` | 25×14 | Display only: formulas referencing `Data Sheet` (e.g. `='Data Sheet'!K17`), **no cached values** |
| `Quarters` | 14×11 | Display only, formulas, no cached values |
| `Balance Sheet` | 24×11 | Display only, formulas, no cached values |
| `Cash Flow` | 8×11 | Display only, formulas, no cached values |
| `Customization` | 16×7 | Instructions for customising the export |
| `Data Sheet` | 93×11 | **The only sheet with numbers.** Column A = labels, columns B..K = 10 periods (oldest → newest) |

Because the display sheets carry no cached values, the engine reads only `Data Sheet`. Openpyxl returns `None` for those formula cells, and so would any parser that doesn't recalculate.

## Data Sheet sections (rows as found; the parser finds them by label, not by row number)

| Rows | Section header (col A) | Content |
|---|---|---|
| 1–3 | `COMPANY NAME`, `LATEST VERSION`, `CURRENT VERSION` | Name, template version (2.1/2.1) |
| 5–9 | `META` | `Number of shares` (**formula** `=IF(B9>0,B9/B8,0)`, no cached value → recomputed as market cap ÷ price), `Face Value`, `Current Price` (₹, export date), `Market Capitalization` (₹ cr) |
| 15–31 | `PROFIT & LOSS` | `Report Date` row, then Sales, Raw Material Cost, Change in Inventory, Power and Fuel, Other Mfr. Exp, Employee Cost, Selling and admin, Other Expenses, Other Income, Depreciation, Interest, Profit before tax, Tax, Net profit, Dividend Amount |
| 40–50 | `Quarters` | `Report Date`, Sales, Expenses, Other Income, Depreciation, Interest, Profit before tax, Tax, Net profit, Operating Profit (10 quarters) |
| 55–72 | `BALANCE SHEET` | `Report Date`, Equity Share Capital, Reserves, Borrowings, Other Liabilities, **Total**, Net Block, Capital Work in Progress, Investments, Other Assets, **Total**, Receivables, Inventory, Cash & Bank, No. of Equity Shares, New Bonus Shares, Face value |
| 80–85 | `CASH FLOW:` | `Report Date`, Cash from Operating/Investing/Financing Activity, Net Cash Flow |
| 90 | `PRICE:` | FY-end share price for each annual column (same columns as the P&L; no own date row) |
| 92–93 | `DERIVED:` | `Adjusted Equity Shares in Cr`: split/bonus/rights-adjusted share count per annual column |

Notes on the layout:
- **Two rows are labelled `Total`.** The first is total liabilities and the second is total assets; the parser tells them apart by order.
- **Receivables, Inventory and Cash & Bank are sub-items of Other Assets.** For example, Asian Paints FY26 has Other Assets 15,968, made up of receivables 4,462 + inventory 5,744 + cash 1,074 + the rest.
- **Screener's display formulas,** which the engine reproduces:
  - Expenses = RM + P&F + Other Mfr + Employee + S&A + Other − Change in Inventory
  - OPM = Operating profit ÷ Sales
  - Debtor days = Receivables ÷ (Sales/365)
  - ROE = Net profit ÷ (Share capital + Reserves), year-end
  - ROCE = (PBT + Interest) ÷ average(Equity + Reserves + Borrowings)
  - Working capital = Other Assets − Other Liabilities
  - EPS = Net profit ÷ Adjusted shares

## Same labels, different meaning by type of company

The Data Sheet labels are **identical in every file**, including banks, NBFCs and insurers. What differs is what the numbers mean:

| Label | Non-financial (ASIANPAINT) | Bank (HDFCBANK) | Insurer (HDFCLIFE) | NBFC (BAJFINANCE) |
|---|---|---|---|---|
| Sales | Revenue from operations | **Interest earned** (FY26 3,48,615) | **Premium + investment income** (99,432) | Revenue from operations (interest + fees) |
| Raw Material, Change in Inv., Power & Fuel | Populated | Blank | Blank | Blank |
| Other Mfr. Exp | Manufacturing overheads | Small opex line | **Benefits paid + change in policy liabilities** (89,774) | Small |
| Other Expenses | Other opex | Opex **incl. provisions & contingencies** (not separable) | Other opex | Opex incl. impairment on financial instruments |
| Other Income | Treasury, other income **and exceptional items** | **Fee and other income (core)** | Small | Small, can be negative |
| Interest | Finance cost | **Interest expended** (1,85,491) | Blank after FY19 | Finance cost |
| Borrowings | Debt incl. lease liabilities | **Deposits + borrowings** (36.9 lakh cr) | Subordinated debt | Borrowings |
| Other Liabilities | Payables, provisions, **minority interest**, other | Other liabilities + provisions | **Policyholders' funds** | Other |
| Investments | Investments incl. associates/JVs | Investment book | Policyholders' + shareholders' investments | Investments |
| Other Assets | Receivables, inventory, cash, loans & advances, other | **Advances** + other assets | Other | **Loans** + other |
| Receivables / Inventory | Trade receivables / inventory | Blank | Mostly blank | Trade receivables (small) |
| CFO | Operating cash flow | Driven by deposit/loan flows | Premium-driven | **Negative by construction** (loan growth) |

In the bank, insurer and NBFC exports, 4 to 7 rows are blank in every year (e.g. raw materials). The engine maps the semantics by archetype family (see `config/sectors.yaml` and `engine/standardise.py`).

## Identities verified on all 21 files

- **P&L:** Sales − Expenses + Other Income − Depreciation − Interest = PBT holds to the rupee in every year, with no separate exceptional line. It follows that **exceptional items are inside Other Income** (sometimes in Other Expenses). Examples:
  - DLF FY18: other income = 145% of sales (DCCDL transaction gain)
  - Bharti FY20: other income = −43% of sales (AGR charge)
  - Sun Pharma FY21–22: negative
  - TCS FY26: −₹124 cr
- **Net profit ≠ PBT − Tax** for groups. The residual is minority interest (negative) plus the share of associates/JVs (positive), so net profit is the **owners' share** and the export is consolidated:
  - Bharti FY26: −7,128
  - HDFC Bank FY26: −3,193
  - DLF FY26: +1,793
- **Balance sheet:** totals add up and liabilities = assets in every file.
- **Quarters:** Operating Profit = Sales − Expenses, and PBT = OP + OI − Dep − Interest. The same minority/associate residual appears below PBT.

## Quirks found

| Quirk | Where | Handling |
|---|---|---|
| Dec year-ends, then a **15-month transition** period | NESTLEIND: 2017-12 … 2023-12, then 2024-03 (Jan-23 → Mar-24, sales 24,394 ≈ CY23 19,126 + Q1), 2025-03, 2026-03 | Period length is taken from the previous real balance-sheet date (15 months). Flows are annualised ×12/15. The YoY comparison into FY24 is flagged as approximate. FY label = calendar year of the period end |
| **Stale column** | NESTLEIND 2023-12: balance sheet identical to 2022-12; P&L lines lumped into Other Expenses (P&F, other mfr, S&A blank) | Balance sheet set to missing. The next period's opening balance comes from 2022-12 |
| Negative cost lines (reclassification) | ASIANPAINT FY17 Other Expenses −2,028 (S&A 4,364); NTPC most years; NESTLEIND FY21–26 | Only three cost buckets are used: materials, employees and "other opex" (the sum of the remaining lines) |
| Blank = zero | P&L/BS blanks (e.g. HDFCLIFE Borrowings FY17–20, Interest FY20+; bank Depreciation in quarters) | Blank line item = 0 (the identities confirm it). Blank price or share count = missing |
| Missing FY-end price | HAL, HDFCLIFE FY17 (not yet listed) | Multiples for that year are missing |
| Corporate actions | Row 93 / row 70 ratio: HDFCBANK ×4→×2→×1 (split + 2025 1:1 bonus), BAJFINANCE ×10, NESTLEIND ×20, TATASTEEL ~×10 (split + rights) | EPS, BVPS, DPS and prices use the adjusted basis, so ratios are unaffected |
| Ind AS 116 (leases) | Bharti FY20 dep/sales 26%→32%; DMart S&A 136→66 while depreciation jumps | Logged as an EBITDA comparability break. Lease liabilities are inside Borrowings |
| Merger step change | HDFCBANK FY24: total assets +59%, adjusted shares +36% (HDFC Ltd merger) | Logged as inorganic |
| Quarter coverage | 10 quarters, Jun-24→Sep-26 (Bharti, HAL, Tata Steel: Mar-24→Jun-26) | Used for TTM and YoY quarterly metrics |
| Export date | Not recorded anywhere in the file | Logged. The current price is "as of export" |

## Not in the export (the engine uses proxies or `data/manual/<TICKER>_kpis.csv`)

| Missing item | Proxy or source used |
|---|---|
| Trade payables | DPO and CCC need the manual file. The `nwc_days` proxy includes payables implicitly |
| Current vs non-current split | Current-ratio proxy = other assets ÷ other liabilities |
| Capex | ΔNet block + ΔCWIP + depreciation |
| Goodwill | Organic proxy uses Δinvestments |
| Short-term borrowings | Cash ÷ total borrowings (conservative) unless supplied |
| Minority interest on the balance sheet | Inside other liabilities |
| Promoter holding / pledge | Manual file only |
| Bank items: provisions, GNPA, CASA, CRAR | Manual file only |

## History depth

The export holds 10 annual columns (9-year span) and 10 quarters. "10y" metrics therefore use the full available span (9 years here), and an as-of FY18 run sees only FY17–FY18 and no quarters.
