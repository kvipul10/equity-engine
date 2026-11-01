# Metric registry

Generated from `engine/registry.py` by `python -m engine metrics --markdown`. Do not edit by hand.

Units: pct = fraction shown as %, pp = difference of fractions shown as percentage points, x = multiple. Applies: ALL, NF = non-financial, FIN = financials, BL = bank + NBFC, BANK, NBFC, INS = insurance. Role: scored (gets level/trend/stability and a RAG), component (shown, used by driver trees, not scored), root (the value-creation verdict).

## Root: value creation

| id | name | unit | direction | applies | role | equation | meaning |
|---|---|---|---|---|---|---|---|
| `economic_profit` | Economic profit | inr_cr | higher | ALL | root | Non-financials: (ROIC - WACC) x average IC = NOPAT - WACC x average IC (defined even when IC <= 0); financials: (ROE - Ke) x average equity | Rupees of value created (or destroyed) in the year after charging for all capital at its required return. |

## 1 Growth

| id | name | unit | direction | applies | role | equation | meaning |
|---|---|---|---|---|---|---|---|
| `revenue_cagr_3y` | Revenue CAGR 3y | pct | higher | ALL | scored | (Revenue_t / Revenue_t-3)^(1/3) - 1; n/m if either value <= 0 | Compound annual growth of revenue (Screener 'Sales'; banks: interest earned; insurers: premium + investment income) over 3 years. |
| `revenue_cagr_5y` | Revenue CAGR 5y | pct | higher | ALL | scored | (Revenue_t / Revenue_t-5)^(1/5) - 1; n/m if either value <= 0 | Compound annual growth of revenue (Screener 'Sales'; banks: interest earned; insurers: premium + investment income) over 5 years. |
| `revenue_cagr_10y` | Revenue CAGR (full span, up to 10y) | pct | higher | ALL | scored (point) | (Revenue_t / Revenue_t-n)^(1/n) - 1, n = full available span <= 10; n/m if either value <= 0 | Compound annual growth of revenue (Screener 'Sales'; banks: interest earned; insurers: premium + investment income) over the longest available history (max 10 years; 9 with a 10-column export). |
| `ebitda_cagr_3y` | EBITDA CAGR 3y | pct | higher | NF | scored | (EBITDA_t / EBITDA_t-3)^(1/3) - 1; n/m if either value <= 0 | Compound annual growth of EBITDA (operating profit before other income) over 3 years. |
| `ebitda_cagr_5y` | EBITDA CAGR 5y | pct | higher | NF | scored | (EBITDA_t / EBITDA_t-5)^(1/5) - 1; n/m if either value <= 0 | Compound annual growth of EBITDA (operating profit before other income) over 5 years. |
| `ebitda_cagr_10y` | EBITDA CAGR (full span, up to 10y) | pct | higher | NF | scored (point) | (EBITDA_t / EBITDA_t-n)^(1/n) - 1, n = full available span <= 10; n/m if either value <= 0 | Compound annual growth of EBITDA (operating profit before other income) over the longest available history (max 10 years; 9 with a 10-column export). |
| `pat_cagr_3y` | PAT CAGR 3y | pct | higher | ALL | scored | (PAT_t / PAT_t-3)^(1/3) - 1; n/m if either value <= 0 | Compound annual growth of core PAT (owners' net profit excluding estimated exceptional items) over 3 years. |
| `pat_cagr_5y` | PAT CAGR 5y | pct | higher | ALL | scored | (PAT_t / PAT_t-5)^(1/5) - 1; n/m if either value <= 0 | Compound annual growth of core PAT (owners' net profit excluding estimated exceptional items) over 5 years. |
| `pat_cagr_10y` | PAT CAGR (full span, up to 10y) | pct | higher | ALL | scored (point) | (PAT_t / PAT_t-n)^(1/n) - 1, n = full available span <= 10; n/m if either value <= 0 | Compound annual growth of core PAT (owners' net profit excluding estimated exceptional items) over the longest available history (max 10 years; 9 with a 10-column export). |
| `eps_cagr_3y` | EPS CAGR 3y | pct | higher | ALL | scored | (EPS_t / EPS_t-3)^(1/3) - 1; n/m if either value <= 0 | Compound annual growth of EPS = core PAT / split-adjusted shares over 3 years. |
| `eps_cagr_5y` | EPS CAGR 5y | pct | higher | ALL | scored | (EPS_t / EPS_t-5)^(1/5) - 1; n/m if either value <= 0 | Compound annual growth of EPS = core PAT / split-adjusted shares over 5 years. |
| `eps_cagr_10y` | EPS CAGR (full span, up to 10y) | pct | higher | ALL | scored (point) | (EPS_t / EPS_t-n)^(1/n) - 1, n = full available span <= 10; n/m if either value <= 0 | Compound annual growth of EPS = core PAT / split-adjusted shares over the longest available history (max 10 years; 9 with a 10-column export). |
| `bvps_cagr_5y` | Book value per share CAGR 5y | pct | higher | FIN | scored | (BVPS_t / BVPS_t-5)^(1/5) - 1, BVPS = equity / adjusted shares | Compounding of book value per share, the core growth measure for lenders and insurers. |
| `assets_cagr_3y` | Total assets CAGR 3y | pct | higher | FIN | scored | (Total assets_t / Total assets_t-3)^(1/3) - 1 | Balance-sheet growth (loan book + investments) for financials. |
| `nii_cagr_3y` | Net interest income CAGR 3y | pct | higher | BL | scored | (NII_t / NII_t-3)^(1/3) - 1, NII = interest earned - interest expended | Growth of the spread business (interest earned - interest expended). |
| `revenue_growth_volatility` | Revenue growth volatility | ratio | lower | ALL | scored (point) | sd(g_t) / \|mean(g_t)\| over the last 10 annual growth rates (>= 4 needed); n/m if \|mean\| < 1% | How erratic annual revenue growth is: standard deviation of yearly growth divided by its mean (lower = steadier). |
| `pat_growth_volatility` | PAT growth volatility | ratio | lower | ALL | scored (point) | sd(g_t) / \|mean(g_t)\| of core PAT growth over the last 10 years (base year PAT > 0); n/m if \|mean\| < 1% | How erratic annual core-profit growth is (sd / mean of yearly growth). |
| `organic_capital_share_3y` | Organic share of capital deployed 3y | ratio | higher | NF | scored | sum3(capex) / (sum3(capex) + sum3(max(delta Investments, 0))) | Of the money put into long-term assets over 3 years, the share spent on own capex rather than on additions to investments (acquisitions, stakes in associates, treasury). Proxy for organic vs bought growth: the export has no goodwill line. |
| `q_revenue_yoy` | Latest quarter revenue YoY | pct | higher | ALL | scored (point) | Revenue_q / Revenue_q-4 - 1 | Revenue growth in the latest reported quarter versus the same quarter a year earlier. |
| `q_pat_yoy` | Latest quarter PAT YoY | pct | higher | ALL | scored (point) | PAT_q / PAT_q-4 - 1 (PAT_q-4 > 0) | Reported net profit growth in the latest quarter versus a year earlier (n/m if the year-ago quarter was a loss). |
| `q_revenue_yoy_trend` | Quarterly YoY growth trend | pp | higher | ALL | scored (point) | OLS slope of the last 4 values of (Revenue_q / Revenue_q-4 - 1), per quarter | Is quarterly growth accelerating or decelerating? Slope of the last 4 quarterly YoY revenue growth prints. |

## 2 Margins

| id | name | unit | direction | applies | role | equation | meaning |
|---|---|---|---|---|---|---|---|
| `gross_margin` | Gross margin | pct | higher | NF | scored | 1 - COGS / Revenue, COGS = (raw material - change in inventory) + power & fuel + other mfr. exp | Share of revenue left after the direct cost of making the product (materials, power & fuel, other manufacturing). n/m when such costs are under 2% of revenue (services). |
| `ebitda_margin` | EBITDA margin | pct | higher | NF | scored | EBITDA / Revenue, EBITDA = Revenue - (materials + employee + other opex) | Operating profit before depreciation, interest and other income, per rupee of revenue (Screener OPM). |
| `ebit_margin` | EBIT margin | pct | higher | NF | scored | EBIT / Revenue, EBIT = core PBT + interest = EBITDA - depreciation + core other income | Profit before interest and tax (including core other income, excluding exceptional items) per rupee of revenue. |
| `pat_margin` | PAT margin | pct | higher | ALL | scored | core PAT / Revenue | Owners' core net profit per rupee of revenue (net profit margin, NPM). |
| `materials_pct` | Materials % of sales | pct | lower | NF | scored | (Raw material - Change in inventory) / Revenue | Raw materials consumed (net of inventory change) as a share of revenue. |
| `employee_pct` | Employee cost % of sales | pct | lower | NF | scored | Employee cost / Revenue | Staff costs as a share of revenue. |
| `other_expenses_pct` | Other expenses % of sales | pct | lower | NF | scored | (Power & fuel + Other mfr. + Selling & admin + Other expenses) / Revenue | All other operating costs (power & fuel, other manufacturing, selling & admin, other) as a share of revenue. Summed because Screener reclassifies between these lines. |
| `dol` | Degree of operating leverage | x | neutral | NF | scored | %change EBIT / %change Revenue (n/m if \|%change revenue\| < 2% or prior EBIT <= 0) | How much EBIT moves for a 1% move in sales: high DOL magnifies both upturns and downturns. |
| `ebitda_margin_sd_10y` | EBITDA margin volatility (sd) | pp | lower | NF | scored (point) | sd(EBITDA margin_t) over the last 10 years (>= 4 needed, sample sd) | Standard deviation of the EBITDA margin over up to 10 years: pricing power and cost pass-through. |
| `other_income_to_pbt` | Other income / PBT | pct | lower | NF | scored | Other income (reported, incl. exceptional) / PBT (reported); n/m if PBT <= 0 | How much of pre-tax profit comes from other income (treasury, one-offs) rather than operations (reported basis). |
| `q_ebitda_margin_yoy_change` | Latest quarter EBITDA margin change YoY | pp | higher | NF | scored (point) | OPM_q - OPM_q-4, OPM = operating profit / revenue | Latest quarter's operating margin versus the same quarter a year earlier. |
| `dep_to_sales` | Depreciation / sales | pct | lower | NF | component | Depreciation / Revenue | Depreciation per rupee of revenue (bridge from EBITDA to EBIT margin). |
| `oi_core_to_sales` | Core other income / sales | pct | neutral | NF | component | (Other income - estimated exceptional items) / Revenue | Recurring other income per rupee of revenue (bridge from EBITDA to EBIT margin). |
| `operating_margin` | Operating (EBIT excl. other income) margin | pct | higher | NF | component | (EBITDA - Depreciation) / Revenue | Operating EBIT per rupee of revenue, excluding other income (used for NOPAT/ROIC). |
| `nii_to_assets` | NII / average assets (NIM proxy) | pct | higher | BL | scored | (Interest earned - Interest expended) / average total assets | Net interest margin on the whole balance sheet (RBI defines NIM as NII / average total assets). |
| `yield_on_assets` | Revenue / average assets | pct | neutral | FIN | scored | Revenue / average total assets | Gross yield of the balance sheet (banks: interest earned / assets; insurers: revenue / assets). |
| `cost_of_funds` | Cost of funds | pct | lower | BL | scored | Interest expended / average (deposits + borrowings) | Interest paid per rupee of deposits + borrowings. |
| `cost_to_income` | Cost (incl. provisions) / income | pct | lower | BL | scored | (Total opex incl. provisions + depreciation) / (NII + other income) | Operating costs including provisions per rupee of net income (Screener does not separate provisions, so this is higher than the reported cost-to-income ratio). |
| `other_income_share` | Fee & other income share | pct | neutral | BL | scored | Other income / (NII + other income) | Share of net income from fees and other non-interest sources. |
| `benefits_ratio` | Benefits ratio | pct | neutral | INS | scored | Benefits / Revenue | Benefits paid plus change in policy reserves per rupee of revenue (Screener 'Other Mfr. Exp' for insurers). |
| `expense_ratio` | Expense ratio | pct | lower | INS | scored | (Total opex - Benefits) / Revenue | Operating expenses other than benefits per rupee of revenue. |

## 3 Capital efficiency

| id | name | unit | direction | applies | role | equation | meaning |
|---|---|---|---|---|---|---|---|
| `asset_turnover` | Asset turnover | x | higher | NF | scored | Revenue / average total assets | Revenue generated per rupee of total assets (the AT in DuPont). |
| `fixed_asset_turnover` | Fixed-asset turnover | x | higher | NF | scored | Revenue / average net block | Revenue per rupee of net fixed assets (plant, property, equipment, intangibles). |
| `ic_turnover` | Invested-capital turnover | x | higher | NF | scored | Revenue / average invested capital, IC = equity + borrowings - cash - investments (n/m if IC <= 0) | Revenue per rupee of operating invested capital (the turnover half of ROIC). |
| `dso` | Receivable days (DSO) | days | lower | NF | scored | Receivables / Revenue x 365 | Days of sales tied up in customer receivables (year-end, as Screener's debtor days). |
| `dio` | Inventory days (DIO) | days | lower | NF | scored | Inventory / COGS x 365, COGS = materials + power & fuel + other mfr. | Days of production cost held as inventory (n/m when inventory < 0.5% of revenue or COGS < 2% of revenue). |
| `dpo` | Payable days (DPO) | days | higher | NF | scored | Trade payables (manual) / COGS x 365 | Days of production cost financed by suppliers. Needs trade_payables in data/manual (not in the Screener export). |
| `cash_conversion_cycle` | Cash conversion cycle | days | lower | NF | scored | DSO + DIO - DPO (DIO = 0 when inventory is immaterial) | Days between paying suppliers and collecting from customers. Needs manual trade payables. |
| `operating_cycle` | Operating cycle | days | lower | NF | scored | DSO + DIO (DIO = 0 when inventory is immaterial) | Days from buying inventory to collecting cash (before supplier credit): always computable from the export. |
| `nwc_days` | Net working capital days | days | lower | NF | scored | (Other assets - cash - other liabilities) / Revenue x 365 | Non-cash working capital in days of sales; includes payables and provisions implicitly (proxy for CCC). Negative = suppliers/customers fund the business. |
| `capex_to_sales` | Capex / sales | pct | neutral | NF | scored | Capex proxy / Revenue | Capital spending intensity (capex proxy from the balance sheet). |
| `capex_to_depreciation` | Capex / depreciation | x | neutral | NF | scored | Capex proxy / Depreciation | Above 1 = growing the asset base; persistently below 1 = under-investing (or asset-light). |
| `cwip_to_net_block` | CWIP / net block | pct | lower | NF | scored | CWIP / Net block | Capital work in progress relative to productive assets: high and persistent = capital locked in projects not yet earning. |
| `nb_to_sales` | Net block / sales | ratio | lower | NF | component | average Net block / Revenue | Average net block per rupee of revenue: a capital-intensity term in the asset-turnover / IC-turnover driver trees (x365 = days of sales). |
| `cwip_to_sales` | CWIP / sales | ratio | lower | NF | component | average CWIP / Revenue | Average cwip per rupee of revenue: a capital-intensity term in the asset-turnover / IC-turnover driver trees (x365 = days of sales). |
| `investments_to_sales` | Investments / sales | ratio | lower | NF | component | average Investments / Revenue | Average investments per rupee of revenue: a capital-intensity term in the asset-turnover / IC-turnover driver trees (x365 = days of sales). |
| `receivables_to_sales` | Receivables / sales | ratio | lower | NF | component | average Receivables / Revenue | Average receivables per rupee of revenue: a capital-intensity term in the asset-turnover / IC-turnover driver trees (x365 = days of sales). |
| `inventory_to_sales` | Inventory / sales | ratio | lower | NF | component | average Inventory / Revenue | Average inventory per rupee of revenue: a capital-intensity term in the asset-turnover / IC-turnover driver trees (x365 = days of sales). |
| `cash_to_sales` | Cash & bank / sales | ratio | lower | NF | component | average Cash & bank / Revenue | Average cash & bank per rupee of revenue: a capital-intensity term in the asset-turnover / IC-turnover driver trees (x365 = days of sales). |
| `other_assets_rest_to_sales` | Other assets (loans, advances, other) / sales | ratio | lower | NF | component | average Other assets (loans, advances, other) / Revenue | Average other assets (loans, advances, other) per rupee of revenue: a capital-intensity term in the asset-turnover / IC-turnover driver trees (x365 = days of sales). |
| `other_liabilities_to_sales` | Other liabilities / sales | ratio | neutral | NF | component | average Other liabilities / Revenue | Average other liabilities per rupee of revenue: a capital-intensity term in the asset-turnover / IC-turnover driver trees (x365 = days of sales). |
| `opex_to_assets` | Operating cost / average assets | pct | lower | FIN | scored | Total opex / average total assets | Operating costs (incl. provisions; insurers: incl. benefits) per rupee of balance sheet. |
| `credit_deposit_proxy` | Other assets / (deposits + borrowings) | ratio | neutral | BL | scored | Other assets / Borrowings (Screener: deposits + borrowings) | Proxy for the credit-deposit ratio: advances and other assets per rupee of deposits + borrowings. |
| `liquid_assets_ratio` | Cash + investments / assets | pct | neutral | FIN | scored | (Cash & bank + Investments) / Total assets | Share of the balance sheet in cash and investments (liquidity buffer vs yield). |

## 4 Returns

| id | name | unit | direction | applies | role | equation | meaning |
|---|---|---|---|---|---|---|---|
| `roe` | Return on equity | pct | higher | ALL | scored | core PAT / average equity (share capital + reserves) | Owners' core profit per rupee of shareholders' equity. |
| `roa` | Return on assets | pct | higher | ALL | scored | core PAT / average total assets | Owners' core profit per rupee of total assets. |
| `roce` | Return on capital employed | pct | higher | NF | scored | EBIT / average (equity + borrowings), EBIT = core PBT + interest | Pre-tax operating return on all funding (Screener's definition). |
| `roic` | Return on invested capital | pct | higher | NF | scored | NOPAT / average IC; NOPAT = (EBITDA - Dep) x (1 - ETR), ETR = core tax / core PBT clipped 0-40% (statutory if PBT <= 0); IC = equity + borrowings - cash - investments (+ manual minority interest); n/m if IC <= 0 | After-tax operating return on the capital actually tied up in operations (excludes cash, investments and the income they earn). |
| `roic_wacc_spread` | ROIC - WACC | pp | higher | NF | scored | ROIC - WACC (WACC from config/market.yaml, see capital_cost.py) | Value created per rupee of invested capital: positive = earns more than investors require. |
| `incremental_roic_3y` | Incremental ROIC 3y | pct | higher | NF | scored | (NOPAT_t - NOPAT_t-3) / (avg IC_t - avg IC_t-3); n/m if capital grew < 5% | Return on the capital added over the last 3 years: is new money earning as much as the old? |
| `roe_ke_spread` | ROE - cost of equity | pp | higher | FIN | scored | ROE - Ke, Ke = rf + beta x ERP | Value created per rupee of equity for a lender/insurer. |
| `attributable_factor` | Attributable-profit factor | ratio | neutral | ALL | component | core PAT / (core PBT - core tax) | Owners' share of after-tax profit: below 1 = minorities take a slice; above 1 = associate/JV income adds to it. |
| `tax_burden` | Tax burden | ratio | higher | ALL | component | (core PBT - core tax) / core PBT | Share of pre-tax profit kept after tax (1 - effective tax rate). |
| `interest_burden` | Interest burden | ratio | higher | NF | component | core PBT / EBIT | Share of EBIT left after interest. |
| `equity_multiplier` | Equity multiplier | x | neutral | ALL | component | average total assets / average equity | Assets per rupee of equity: the leverage term in DuPont. |
| `debt_to_equity_avg` | Borrowings / equity (average) | x | neutral | ALL | component | average borrowings / average equity | Debt part of the equity multiplier. |
| `other_liab_to_equity_avg` | Other liabilities / equity (average) | x | neutral | ALL | component | average other liabilities / average equity | Non-debt liabilities part of the equity multiplier. |
| `nopat_tax_factor` | NOPAT tax factor | ratio | higher | NF | component | 1 - ETR (as in ROIC) | Operating profit kept after tax. |
| `nopat_margin` | NOPAT margin | pct | higher | NF | component | NOPAT / Revenue | After-tax operating profit per rupee of revenue (the margin half of ROIC). |
| `interest_to_assets` | Interest expended / assets | pct | neutral | FIN | component | interest / average total assets | Interest paid per rupee of average assets. ROA = yield - interest + other income - opex - depreciation - tax + minority/associates. |
| `other_income_to_assets` | Other income / assets | pct | neutral | FIN | component | other_income / average total assets | Fee and other income per rupee of average assets. ROA = yield - interest + other income - opex - depreciation - tax + minority/associates. |
| `dep_to_assets` | Depreciation / assets | pct | neutral | FIN | component | depreciation / average total assets | Depreciation per rupee of average assets. ROA = yield - interest + other income - opex - depreciation - tax + minority/associates. |
| `tax_to_assets` | Tax / assets | pct | neutral | FIN | component | tax_core / average total assets | Tax per rupee of average assets. ROA = yield - interest + other income - opex - depreciation - tax + minority/associates. |
| `minority_to_assets` | Minority & associates / assets | pct | neutral | FIN | component | minority_and_associates / average total assets | Associate income less minority share per rupee of average assets. ROA = yield - interest + other income - opex - depreciation - tax + minority/associates. |

## 5 Cash and earnings quality

| id | name | unit | direction | applies | role | equation | meaning |
|---|---|---|---|---|---|---|---|
| `cfo_to_ebitda` | CFO / EBITDA | ratio | higher | NF | scored | CFO / EBITDA (EBITDA > 0) | How much of operating profit arrives as operating cash (after working capital and tax). |
| `fcf_to_pat` | FCF / PAT | ratio | higher | NF | scored | (CFO - capex proxy) / core PAT (PAT > 0) | Free cash flow per rupee of core profit in the year. |
| `fcf_to_pat_5y` | FCF / PAT (5y cumulative) | ratio | higher | NF | scored | sum5(CFO - capex proxy) / sum5(core PAT) | Free cash flow conversion over a full cycle (5 years), smoothing lumpy capex. |
| `cfo_to_pat_5y` | CFO / PAT (5y cumulative) | ratio | higher | NF | scored | sum5(CFO) / sum5(core PAT) | Operating cash flow conversion of profits over 5 years: below 60% means profits are not turning into cash. |
| `accruals_ratio` | Accruals ratio | pct | lower | NF | scored | (reported PAT - CFO) / average total assets | Profit not backed by operating cash, scaled by assets (Sloan-style total accruals): high = lower-quality earnings. |
| `receivables_vs_revenue_growth` | Receivables growth - revenue growth | pp | lower | NF | scored | (Rec_t / Rec_t-1 - 1) - (Rev_t / Rev_t-1 - 1); n/m if prior receivables < 0.5% of revenue | Receivables growing faster than sales can signal channel stuffing, looser credit or collection problems. |
| `exceptional_frequency_5y` | Exceptional items frequency (5y) | count | lower | NF | scored | count over last 5 years of [\|estimated exceptional\| > 5% x \|PBT\|] | In how many of the last 5 years profit contained a material exceptional item (|item| > 5% of PBT). |
| `exceptional_size_5y` | Exceptional items size (5y) | pct | lower | NF | scored | sum5(\|estimated exceptional\|) / sum5(\|reported PBT\|) | How big exceptional items were relative to profit over 5 years. |
| `beneish_dsri` | Beneish DSRI | ratio | lower | NF | component | (Rec_t/Sales_t) / (Rec_t-1/Sales_t-1) | Days-sales-in-receivables index: receivables/sales this year vs last. |
| `beneish_gmi` | Beneish GMI | ratio | lower | NF | component | GM_t-1 / GM_t, GM = 1 - COGS/Sales | Gross-margin index: last year's gross margin / this year's (>1 = deteriorating margins). |
| `beneish_aqi` | Beneish AQI | ratio | lower | NF | component | [1 - (CA_t + NB_t)/TA_t] / [1 - (CA_t-1 + NB_t-1)/TA_t-1], CA proxy = receivables + inventory + cash | Asset-quality index: share of 'soft' assets (not current assets or net block) this year vs last. |
| `beneish_sgi` | Beneish SGI | ratio | lower | NF | component | Sales_t / Sales_t-1 | Sales-growth index. |
| `beneish_depi` | Beneish DEPI | ratio | lower | NF | component | DepRate_t-1 / DepRate_t, DepRate = Dep / (Dep + Net block) | Depreciation index: last year's depreciation rate / this year's (>1 = slower depreciation). |
| `beneish_sgai` | Beneish SGAI | ratio | neutral | NF | component | (SGA_t/Sales_t) / (SGA_t-1/Sales_t-1), SGA proxy = selling & admin + other expenses (other opex if that is <= 0) | SG&A index: SG&A/sales this year vs last. |
| `beneish_lvgi` | Beneish LVGI | ratio | lower | NF | component | [(Borrowings_t + OL_t)/TA_t] / [(Borrowings_t-1 + OL_t-1)/TA_t-1] | Leverage index: (debt + other liabilities)/assets this year vs last. |
| `beneish_tata` | Beneish TATA | ratio | lower | NF | component | (reported PAT - CFO) / Total assets_t | Total accruals to total assets (year-end). |
| `beneish_m_score` | Beneish M-score (Screener proxies) | score | lower | NF | scored | -4.84 + 0.920 DSRI + 0.528 GMI + 0.404 AQI + 0.892 SGI + 0.115 DEPI - 0.172 SGAI + 4.679 TATA - 0.327 LVGI | Probability-style earnings-manipulation screen (Beneish 1999, 8 variables) built from Screener line items. Above -1.78 = profile resembles known manipulators; a screen, not proof. |

## 6 Balance sheet

| id | name | unit | direction | applies | role | equation | meaning |
|---|---|---|---|---|---|---|---|
| `net_debt_to_ebitda` | Net debt / EBITDA | x | lower | NF | scored | (Borrowings - Cash & bank) / EBITDA (EBITDA > 0) | Years of operating profit needed to repay net debt (negative = net cash). Borrowings include lease liabilities. |
| `net_debt_to_equity` | Net debt / equity | x | lower | NF | scored | (Borrowings - Cash & bank) / Equity | Net financial leverage on book equity. |
| `interest_cover` | Interest cover | x | higher | NF | scored | EBIT / Interest, EBIT = core PBT + interest; = 99 if interest ~ 0; clipped to [-99, 99] | How many times EBIT covers interest (capped at 99x when interest is negligible). |
| `current_ratio_proxy` | Current ratio (Screener proxy) | x | higher | NF | scored | Other assets / Other liabilities | Short-term liquidity proxy: the export has no current/non-current split, so other assets / other liabilities is used (Screener's own working-capital split). Excludes short-term debt (inside Borrowings). |
| `cash_to_st_borrowings` | Cash / short-term borrowings | x | higher | NF | scored | Cash & bank / short-term borrowings (manual) or / Borrowings; = 99 when there is no debt | Cash cover for debt falling due soon. Uses manual short_term_borrowings when supplied, otherwise total borrowings (conservative: treats all debt as short-term). |
| `debt_vs_ebitda_growth` | Debt growth - EBITDA growth | pp | lower | NF | scored | (Borrowings_t/Borrowings_t-1 - 1) - (EBITDA_t/EBITDA_t-1 - 1); n/m if prior debt < 1% of assets or prior EBITDA <= 0 | Debt growing faster than the profit that services it (n/m when debt was negligible). |
| `altman_x1` | Altman Z'' X1 | ratio | higher | NF | component | (Other assets - Other liabilities) / Total assets | Working capital (Screener split) / total assets |
| `altman_x2` | Altman Z'' X2 | ratio | higher | NF | component | Reserves / Total assets | Reserves (proxy for retained earnings; includes securities premium) / total assets |
| `altman_x3` | Altman Z'' X3 | ratio | higher | NF | component | EBIT / Total assets | Operating return on assets |
| `altman_x4` | Altman Z'' X4 | ratio | higher | NF | component | Equity / (Borrowings + Other liabilities) | Book equity / total liabilities (book value replaces market value in Z'') |
| `altman_z_india` | Altman Z''-EM (India-adapted) | score | higher | NF | scored | 3.25 + 6.56 X1 + 3.26 X2 + 6.72 X3 + 1.05 X4 (X1..X4 as defined in altman_x1..x4) | Distress score for emerging-market non-financials (Altman 2005 EM score: Z'' + 3.25) using Screener proxies. Above 5.85 safe, below 4.35 distress zone. |
| `equity_to_assets` | Equity / assets | pct | higher | FIN | scored | Equity / Total assets | Book capital cushion per rupee of assets (unweighted leverage; regulatory CRAR needs risk weights not in the export). |
| `funding_vs_equity_growth` | Funding growth - equity growth | pp | lower | BL | scored | (Borrowings_t/Borrowings_t-1 - 1) - (Equity_t/Equity_t-1 - 1) | Deposits + borrowings growing faster than capital = rising leverage. |
| `borrowings_to_equity` | Borrowings / equity | x | lower | NBFC | scored | Borrowings / Equity | NBFC leverage (RBI caps base-layer NBFCs at 7x outside liabilities / owned funds). |

## 7 Capital allocation

| id | name | unit | direction | applies | role | equation | meaning |
|---|---|---|---|---|---|---|---|
| `reinvestment_rate` | Reinvestment rate | ratio | neutral | NF | scored | (Capex proxy - Depreciation + change in NWC) / NOPAT (NOPAT > 0); NWC = other assets - cash - other liabilities | Share of after-tax operating profit ploughed back into fixed assets and working capital. Good only if incremental ROIC exceeds WACC. |
| `payout_ratio` | Dividend payout | ratio | neutral | ALL | scored | Dividend / core PAT (PAT > 0) | Share of core profit paid as dividends (Screener 'Dividend Amount', declared for the year). |
| `share_count_change` | Share count change | pct | lower | ALL | scored | Adjusted shares_t / Adjusted shares_t-1 - 1 | Net issuance (dilution, +) or buyback (-) of shares, adjusted for splits and bonuses. |
| `buyback_estimate` | Buyback (estimate) | inr_cr | neutral | ALL | scored | max(0, -(Adj shares_t - Adj shares_t-1)) x (Price_t + Price_t-1)/2 | Estimated rupees spent on buybacks: shares retired x average of the two year-end prices. |
| `shareholder_yield` | Shareholder yield | pct | neutral | ALL | scored | (Dividend + buyback estimate) / Market cap (FY-end) | Cash returned to shareholders (dividends + estimated buybacks) as a share of year-end market value. |
| `dividend_to_fcf` | Dividends / FCF | ratio | lower | NF | scored | Dividend / (CFO - capex proxy); 99 if FCF <= 0 and dividend > 0; 0 if no dividend | Dividends relative to free cash flow: above 1 = payouts funded from the balance sheet (99 = dividend paid with FCF <= 0). |
| `non_capex_investing_3y` | Non-capex investing (3y, % of IC) | pct | neutral | NF | scored | sum3(-CFI - capex proxy) / IC_t-3 (IC_t-3 > 0) | Investing outflows beyond capex over 3 years (acquisitions, stakes, treasury investments) relative to opening invested capital. |
| `acquisition_roic_delta_3y` | ROIC change after acquisition spend | pp | higher | NF | scored | ROIC_t - ROIC_t-3 if non_capex_investing_3y > 10%, else n/a | When a company spent materially beyond capex (> 10% of IC over 3 years), did ROIC subsequently rise or fall? |
| `promoter_holding` | Promoter holding | pct | neutral | ALL | scored | manual promoter_holding_pct (FY-end) | Promoter (controlling shareholder) stake. Not in the Screener export: supply promoter_holding_pct in data/manual. |
| `promoter_holding_change_3y` | Promoter holding change 3y | pp | higher | ALL | scored | Promoter holding_t - Promoter holding_t-3 | Change in promoter stake over 3 years (selling down = negative). |
| `promoter_pledge` | Promoter pledge | pct | lower | ALL | scored | manual promoter_pledge_pct (pledged shares / promoter shares) | Share of promoter holding pledged to lenders (forced-selling risk). Manual data only. |
| `internal_capital_generation` | Internal capital generation | pct | neutral | FIN | scored | ROE x (1 - payout) | Growth in equity a lender can fund from retained profit alone. |
| `growth_minus_icg` | Asset growth - internal capital generation | pp | lower | BL | scored | (Total assets_t / Total assets_t-1 - 1) - ROE x (1 - payout) | Balance-sheet growth beyond what retained earnings can support: must be funded by new equity or by higher leverage. |

## 8 Valuation

| id | name | unit | direction | applies | role | equation | meaning |
|---|---|---|---|---|---|---|---|
| `pe` | P/E | x | neutral | ALL | scored | Market cap / core PAT (current: TTM PAT when available) | P/E multiple. Series = FY-end values; the last value is the current multiple (export price) in a latest run. |
| `pe_percentile_10y` | P/E percentile vs own history | pct | lower | ALL | scored (point) | (# historical FY-end P/E below current + 0.5 x # equal) / # historical values | Where today's P/E sits within the company's own FY-end history (0% = cheapest ever, 100% = richest). Needs >= 5 years. |
| `pb` | P/B | x | neutral | ALL | scored | Market cap / book equity | P/B multiple. Series = FY-end values; the last value is the current multiple (export price) in a latest run. |
| `pb_percentile_10y` | P/B percentile vs own history | pct | lower | ALL | scored (point) | (# historical FY-end P/B below current + 0.5 x # equal) / # historical values | Where today's P/B sits within the company's own FY-end history (0% = cheapest ever, 100% = richest). Needs >= 5 years. |
| `ev_ebitda` | EV/EBITDA | x | neutral | NF | scored | EV / EBITDA, EV = market cap + borrowings - cash - investments | EV/EBITDA multiple. Series = FY-end values; the last value is the current multiple (export price) in a latest run. |
| `ev_ebitda_percentile_10y` | EV/EBITDA percentile vs own history | pct | lower | NF | scored (point) | (# historical FY-end EV/EBITDA below current + 0.5 x # equal) / # historical values | Where today's EV/EBITDA sits within the company's own FY-end history (0% = cheapest ever, 100% = richest). Needs >= 5 years. |
| `ev_sales` | EV/Sales | x | neutral | NF | scored | EV / Revenue | EV/Sales multiple. Series = FY-end values; the last value is the current multiple (export price) in a latest run. |
| `ev_sales_percentile_10y` | EV/Sales percentile vs own history | pct | lower | NF | scored (point) | (# historical FY-end EV/Sales below current + 0.5 x # equal) / # historical values | Where today's EV/Sales sits within the company's own FY-end history (0% = cheapest ever, 100% = richest). Needs >= 5 years. |
| `implied_growth_reverse_dcf` | Reverse-DCF implied FCF growth (10y) | pct | neutral | NF | scored (point) | solve g: EV = sum_{t=1..10} F0(1+g)^t/(1+WACC)^t + F10(1+gT)/((WACC-gT)(1+WACC)^10), F0 = NOPAT0 x (1 - gT/RONIC), RONIC = 3y avg ROIC (capped at 100%) | Annual free-cash-flow growth for the next 10 years that today's enterprise value implies, starting from the steady-state FCF the business generates at its 3-year average ROIC, then growing at the terminal rate. |
| `implied_minus_delivered_growth` | Implied - delivered growth | pp | lower | NF | scored (point) | implied_growth_reverse_dcf - 5y NOPAT CAGR (revenue CAGR 5y if NOPAT CAGR is n/m) | How much faster the market expects NOPAT to grow than it did over the last 5 years (positive = priced for acceleration). |
| `implied_growth_pb` | P/B-implied growth | pct | neutral | FIN | scored (point) | g = (Ke x P/B - ROE) / (P/B - 1); n/m if \|P/B - 1\| < 0.05 | Perpetual growth implied by today's P/B for a lender/insurer (justified P/B solved for g) at its 3-year average ROE. |
| `implied_pb_growth_minus_delivered` | P/B-implied - delivered growth | pp | lower | FIN | scored (point) | implied_growth_pb - BVPS CAGR 5y (PAT CAGR 5y if n/m) | Growth the market prices in versus the book-value compounding actually delivered over 5 years. |
| `justified_pb` | Justified P/B | x | neutral | ALL | scored (point) | (ROE - g) / (Ke - g); ROE = 3y avg, g = min(ROE x (1 - 3y avg payout), terminal g) | P/B a single-stage residual-income model supports: (ROE - g) / (Ke - g) with sustainable ROE and growth. |
| `pb_to_justified_pb` | P/B / justified P/B | x | lower | ALL | scored (point) | current P/B / justified P/B (justified > 0) | Market P/B relative to what returns justify: above 1 = paying for more than current ROE supports. |
| `ev_ic` | EV / invested capital | x | neutral | NF | scored (point) | current EV / IC (latest FY, IC > 0) | Market value of operations per rupee of capital invested in them. |
| `ev_ic_to_roic_wacc` | (EV/IC) / (ROIC/WACC) | x | lower | NF | scored (point) | (EV / IC) / (ROIC / WACC), ROIC = latest, WACC = current | In a no-growth steady state EV/IC = ROIC/WACC. Above 1 = the market pays for growth or improvement beyond today's returns; below 1 = priced for decline. |
