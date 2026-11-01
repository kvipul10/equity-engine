# Expected strengths and weaknesses (pre-registered)

Written from published analyst and press commentary found by web search in Session 4, **before** the
engine was run or compared. The commit that adds this file precedes every comparison (see `git log`).
`validation/expected.yaml` is the machine-readable twin; this file is generated from it.

- **Scope:** the 16 `test` companies as of FY26; the 4 `peer` companies (ICICI Bank, Infosys, Nestle,
  HAL) as a holdout scored only before and after fixing; Yes Bank as of FY18 (warning signs before the collapse).
- **Signals** are engine metric ids and flag ids chosen in advance from `docs/metrics.md` and `docs/flags.md`
  by meaning. A strength counts as found if a signal metric is GREEN; a weakness if a signal metric is RED,
  or AMBER and deteriorating, or a signal flag fires.
- **Tags:** `financial` (visible in the Screener financials), `kpi` (needs a manual KPI), `qualitative`
  (not a number in the data; reported separately).
- **Disclosure:** earlier sessions produced reports, and parts of the TCS, HDFC Bank, DLF, Tata Steel and
  Yes Bank outputs were seen then. Every item below rests on the cited sources.
- **Sources** are mostly results coverage and brokerage notes as reported by media; figures in them vary
  slightly between outlets. They were taken from search extracts, not from the primary documents.

## TCS (it_services, as of FY26)

**Strengths**

S1. Industry-leading operating margin (about 25% EBIT in Q4 FY26, a four-year high) — *financial*. Signals: `ebit_margin`, `ebitda_margin`, `operating_margin`, `pat_margin`. Sources: [operating margin at a four-year high of 25.3%](https://www.outlookbusiness.com/markets/tcs-shares-fall-2-despite-strong-q4-results) (2026-04-10); [margin outlook debated after a strong quarter](https://www.whalesbook.com/news/English/tech/TCS-Q4-AI-Revenue-Soars-But-Analysts-Split-on-Margin-Outlook/69d86b4ae0ea10058db5365a) (2026-04-10)
S2. Strong cash generation (operating cash flow above 100% of net profit) — *financial*. Signals: `cfo_to_pat_5y`, `fcf_to_pat_5y`, `fcf_to_pat`, `cfo_to_ebitda`. Sources: [OCF about 107% of Q4 net profit](https://blog.liquide.life/tcs-q4-results-2026-dividend-share-price-target-analysis/) (2026-04-10)
S3. Record deal wins: Q4 TCV about USD 12 bn, FY26 order book TCV about USD 40.7 bn — *kpi*. Signals: `book_to_bill`, `deal_tcv_growth`. Sources: [record deal wins vs weak BFSI](https://www.swastika.co.in/blog/tcs-q4-fy26-review-record-deal-wins-vs-weak-bfsi---what-should-investors-focus-on) (2026-04)

**Weaknesses**

W1. Revenue growth stalled: FY26 USD revenue -0.5%, constant currency -2.4% — *financial*. Signals: `revenue_cagr_3y`, `cc_growth`, `q_revenue_yoy`, `revenue_cagr_5y`, flag `IT03`, flag `G06`. Sources: [brokerages flag growth concerns; FY26 dollar revenue down 0.5%](https://www.outlookbusiness.com/markets/tcs-shares-fall-2-despite-strong-q4-results) (2026-04-10); [18 brokerages on growth visibility](https://www.businesstoday.in/amp/markets/stocks/story/tcs-share-price-target-at-rs-3350-15-brokerages-share-views-post-q4-results-524986-2026-04-10) (2026-04-10)
W2. BFSI weakness and uncertain demand recovery (flat BFSI deal bookings) — *qualitative*. Signals: none (qualitative). Sources: [weak BFSI](https://www.swastika.co.in/blog/tcs-q4-fy26-review-record-deal-wins-vs-weak-bfsi---what-should-investors-focus-on) (2026-04)
W3. Attrition back up to about 13.7% (LTM) with rising AI and wage costs — *kpi*. Signals: `attrition`, `employee_pct`, flag `IT01`, flag `M04`. Sources: [rising AI costs and attrition raise concerns](https://www.whalesbook.com/news/English/tech/TCS-Q4-Results-Strong-But-Rising-AI-Costs-and-Attrition-Raise-Concerns/69d799bfe1f61dfbf512b8b3) (2026-04-09)

## HDFCBANK (bank, as of FY26)

**Strengths**

S1. Robust and improving asset quality (GNPA about 1.15%) — *kpi*. Signals: `gnpa_ratio`, `nnpa_ratio`, `credit_cost`. Sources: [GNPA 1.15%](https://www.jmfinancialservices.in/blogs-and-articles/hdfc-bank-q4-fy26-results-profit-jumps-9percent-indian-rupee13-dividend-announced) (2026-04-18); [MOFSL: asset quality robust](https://www.businesstoday.in/markets/stocks/story/buy-hdfc-bank-shares-chairman-exit-behind-us-target-prices-post-q4-results-526399-2026-04-20) (2026-04-20)
S2. Strong deposit mobilisation (deposits +14.4% YoY), bringing the CD ratio down — *kpi*. Signals: `deposit_growth`. Sources: [deposits grew 14.4% YoY; CD ratio fell to 94.6%](https://www.businesstoday.in/markets/stocks/story/buy-hdfc-bank-shares-chairman-exit-behind-us-target-prices-post-q4-results-526399-2026-04-20) (2026-04-20)
S3. Well capitalised: CRAR about 19.7%, CET1 about 17.3% — *kpi*. Signals: `crar`, `cet1`, `equity_to_assets`. Sources: [bank's Q4 FY26 release: CRAR 19.7%, CET1 17.3%](https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/discover-more/news-room/press-release/2026/press-release-march-2026.pdf) (2026-04-18)

**Weaknesses**

W1. Net interest margin compression and weak NII growth (NIM about 3.4%, NII +3-4% YoY) — *financial*. Signals: `nii_to_assets`, `nim_reported`, `nii_cagr_3y`, flag `M08`. Sources: [PL Capital cuts core profit forecasts on NIM miss and softer fees](https://www.plindia.com/?p=28866) (2026-04-20); [NIM 3.38%, NII growth 3.2%](https://www.jmfinancialservices.in/blogs-and-articles/hdfc-bank-q4-fy26-results-profit-jumps-9percent-indian-rupee13-dividend-announced) (2026-04-18)
W2. Loan growth slow versus peers (ICICI advances +15.8%), retail growth modest — *kpi*. Signals: `loan_growth`, `q_revenue_yoy`. Sources: [slowing income growth; loan growth slower than ICICI](https://www.whalesbook.com/news/English/bankingfinance/HDFC-Bank-Profit-Rises-91percent-Shares-Slip-on-Slowing-Income-Growth/69e5d4e3bca97ee1069353ca) (2026-04-18)
W3. Credit-deposit ratio still high (about 95%) after the HDFC merger — *kpi*. Signals: `cd_ratio`, flag `BK07`. Sources: [CD ratio 94.6%](https://www.businesstoday.in/markets/stocks/story/buy-hdfc-bank-shares-chairman-exit-behind-us-target-prices-post-q4-results-526399-2026-04-20) (2026-04-20)

## BAJFINANCE (nbfc, as of FY26)

**Strengths**

S1. AUM growth of about 22% to Rs 5.1 lakh crore, guided 22-24% for FY27 — *kpi*. Signals: `aum_growth`, `assets_cagr_3y`, `revenue_cagr_3y`. Sources: [PAT +22%, AUM Rs 5.1 lakh crore](https://www.plindia.com/news/bajaj-finance-q4fy26-net-profit-rises-22/) (2026-04-29); [analysts bullish on earnings growth and stable FY27 outlook](https://upstox.com/news/market-news/stocks/bajaj-finance-shares-jump-over-4-post-q4-earnings-what-is-driving-street-optimism/article-192960/) (2026-04-30)
S2. Asset quality improving: credit cost down to about 1.6% of AUM, lower GNPA — *kpi*. Signals: `credit_cost_aum`, `gnpa_ratio`, `nnpa_ratio`. Sources: [Sharekhan: annualised credit cost 1.57%, down 66 bps YoY](https://pre.sharekhan.com/news/earning/details/bajaj-finance-q4fy2026/all) (2026-04-29)
S3. Strong earnings growth and returns (PAT +22%, high ROE/ROA) — *financial*. Signals: `pat_cagr_3y`, `pat_cagr_5y`, `roe`, `roa`, `eps_cagr_3y`. Sources: [strong earnings growth](https://upstox.com/news/market-news/stocks/bajaj-finance-shares-jump-over-4-post-q4-earnings-what-is-driving-street-optimism/article-192960/) (2026-04-30)

**Weaknesses**

W1. NIM compression (about 9.5%, slipping) as borrowing costs rise — *financial*. Signals: `nii_to_assets`, `spread`, flag `NB05`, flag `M08`. Sources: [growth marred by NIM squeeze](https://www.whalesbook.com/news/English/bankingfinance/Bajaj-Finance-Growth-Marred-by-NIM-Squeeze-and-Succession-Woes/69f8b4359d1c906648247fb1) (2026-05); [PL Capital expects NIM compression as bond yields harden](https://www.plindia.com/?p=30130) (2026-04-30)
W2. Rising cost of borrowing and a shrinking deposit book (deposits -4% YoY) — *kpi*. Signals: `cost_of_borrowing`, `cost_of_funds`, `deposit_share`, flag `NB05`. Sources: [sector headwinds, rising borrowing costs](https://www.whalesbook.com/news/English/bankingfinance/Bajaj-Finance-Sees-22percent-Q4-Profit-Jump-Sector-Headwinds-Test-Growth/69f355f108235f0c2a21825b) (2026-04-30); [deposit book declined 4% YoY](https://www.business-standard.com/markets/capital-market-news/bajaj-finance-q4-deposits-drop-4-yoy-aum-crosses-rs-5-lakh-crore-126040400204_1.html) (2026-04-04)
W3. Valuation rich relative to returns; growth/return targets seen as optimistic (Macquarie, Bernstein underperform) — *financial*. Signals: `pb_to_justified_pb`, `implied_pb_growth_minus_delivered`, `pb_percentile_10y`, flag `V03`, flag `V05`, flag `V06`. Sources: [valuation and sector worries](https://www.whalesbook.com/news/English/bankingfinance/Bajaj-Finance-Reports-Strong-Profit-Amid-Valuation-and-Sector-Worries/69f2e8e208235f0c2a1d337b) (2026-04-30)

## HDFCLIFE (insurance, as of FY26)

**Strengths**

S1. Embedded value growth of about 12% with operating RoEV about 15% — *kpi*. Signals: `ev_growth`, `operating_roev`. Sources: [EV Rs 62,139 crore; operating RoEV 15.0%](https://www.hdfclife.com/content/dam/hdfclifeinsurancecompany/about-us/pdf/investor-relations/financial-information/Quarterly-financial-results/HDFC-Life-12M-FY2026-Press-Release.pdf) (2026-04-16)
S2. Stable persistency (13th month about 85%, 61st month about 64%) — *kpi*. Signals: `persistency_13m`, `persistency_61m`. Sources: [persistency ratios stable](https://www.hdfclife.com/content/dam/hdfclifeinsurancecompany/about-us/pdf/investor-relations/financial-information/Quarterly-financial-results/HDFC-Life-12M-FY2026-Press-Release.pdf) (2026-04-16)
S3. Protection sales surged — *qualitative*. Signals: none (qualitative). Sources: [protection sales surge](https://www.whalesbook.com/news/undefined/insurance/HDFC-Life-falls-on-Q4-miss-protection-sales-surge-capital-boost-planned/69e0cdc67bc5659bb5b08c8c) (2026-04-16)

**Weaknesses**

W1. VNB margin compressed to 24.2% from 25.6% (surrender rules, GST ITC, non-par mix) — *kpi*. Signals: `vnb_margin`, flag `IN03`. Sources: [FY26 VNB margin 24.2% vs 25.6%](https://www.businesstoday.in/markets/stocks/story/up-to-36-upside-hdfc-life-share-price-target-raised-post-q4-results-dividend-2026-heres-why-526125-2026-04-17) (2026-04-17); [margin contraction of 140 bps](https://www.barodaetrade.com/Reports/HDFCLife-Q4FY26ResultReview17Apr26-Research.pdf) (2026-04-17)
W2. Weak growth: FY26 VNB +2%, Q4 APE +0.4% (JPMorgan), Q4 VNB -8% — *kpi*. Signals: `vnb_growth`, `ape_growth`, flag `IN04`. Sources: [VNB growth missed; JPMorgan cut target](https://upstox.com/news/market-news/stocks/hdfc-life-shares-fall-4-on-missing-vnb-growth-estimate-dividend-declared-check-q4-numbers/article-192298/) (2026-04-17)
W3. Solvency down to 177% (from 194%), requiring a capital raise — *kpi*. Signals: `solvency_ratio`, flag `IN01`. Sources: [solvency 177%; capital raise planned](https://www.multibagg.ai/market-pulse/articles/hdfc-life-q4-fy26-solvency-cmo2ehetjr3ibph0jmxnyzy73) (2026-04-16)

## HINDUNILVR (fmcg, as of FY26)

**Strengths**

S1. Volume recovery: underlying volume growth about 6% in Q4 FY26 (best in 12 quarters), 4% for FY26 — *kpi*. Signals: `volume_growth`. Sources: [volume growth 6%](https://chanakyanipothi.com/latest-news/hul-q4-results-fy26-profit-volume-growth-analysis/) (2026-04-30); [highest quarterly growth in 12 quarters](https://scanx.trade/stock-market-news/companies/hul-q4-fy26-earnings-call-8-revenue-growth-marks-highest-quarterly-performance-in-12-quarters/39734794) (2026-04-30)
S2. High and resilient EBITDA margin (about 23.7%), Q4 margin beat — *financial*. Signals: `ebitda_margin`, `ebit_margin`, `gross_margin`. Sources: [margin surprise; EBITDA margin 23.7%](https://www.whalesbook.com/news/English/consumer-products/HUL-Beats-Q4-Estimates-With-Margin-Surprise-Declares-Dividend/69f2e40108235f0c2a1d20e2) (2026-04-30)
S3. Revenue growth accelerating (Q4 +8% YoY) — *financial*. Signals: `q_revenue_yoy`, `q_revenue_yoy_trend`. Sources: [revenue +8%](https://www.whalesbook.com/corporate-news/English/consumer-products/HUL-Q4-FY26-Revenue-Rises-8percent-Profit-Jumps-20percent-Driven-by-Strong-Volumes/69f2e6ce08235f0c2a1d2b63) (2026-04-30)

**Weaknesses**

W1. Core profit growth weak (about +4% excluding the Nutritionalab stake-sale gain); headline PAT flattered by exceptional items — *financial*. Signals: `pat_cagr_3y`, `eps_cagr_3y`, `exceptional_size_5y`, `exceptional_frequency_5y`, flag `Q05`. Sources: [profit surges 21% on exceptional gains; core PAT up about 4%](https://chanakyanipothi.com/latest-news/hul-q4-results-fy26-profit-volume-growth-analysis/) (2026-04-30)
W2. Margin pressure from input costs (palm oil, crude-linked) and higher expenses — *financial*. Signals: `gross_margin_change_1y`, `q_ebitda_margin_yoy_change`, `materials_pct`, `gm_commodity_pass_through`, flag `M01`, flag `M03`, flag `FM04`. Sources: [margin squeeze](https://www.whalesbook.com/news/English/brokerage-reports/HUL-Revenue-Jumps-8percent-Amid-Margin-Squeeze-and-Valuation-Worries/69f5f79f9d1c9066481da574) (2026-05); [Nuvama cut target on higher expenses and lower margin](https://www.multibagg.ai/market-pulse/articles/hul-target-2026-nuvama-cuts-cmoqmofb378u5p50jnmj78yg8) (2026-05)
W3. Valuation elevated relative to growth (Systematix Hold) — *financial*. Signals: `pe_percentile_10y`, `ev_ebitda_percentile_10y`, `implied_minus_delivered_growth`, `ev_ic_to_roic_wacc`, flag `V01`, flag `V02`, flag `V04`. Sources: [high valuation worries](https://www.whalesbook.com/news/English/consumer-products/HUL-Posts-Strong-6percent-Growth-Amid-High-Valuation-Worries/69f9b3f0d87e3288bea9388a) (2026-05)

## ASIANPAINT (consumer_manufacturing, as of FY26)

**Strengths**

S1. Margin expansion: consolidated PBDIT margin 19.4% vs 17.2% (cost discipline, raw-material deflation) — *financial*. Signals: `ebitda_margin`, `gross_margin`, `q_ebitda_margin_yoy_change`, `gross_margin_change_1y`. Sources: [margin expansion](https://www.whalesbook.com/news/English/consumer-products/Asian-Paints-Q4-Surge-Margin-Expansion-vs-Sector-Reality/6a1cf0f9cc8b4288bbd01ca7) (2026-05); [PL: steady growth outlook](https://www.plindia.com/pl-research/asian-paints-apnt-in-q4fy26-result-update-steady-growth-outlook-but-margins-have-peaked-out-hold/) (2026-05)
S2. Decorative volume growth recovered to about 12% in Q4 FY26 — *kpi*. Signals: `volume_growth`. Sources: [volume growth 12.4%, value 10.2%](https://www.indmoney.com/blog/stocks/is-asian-paints-growth-making-a-comeback) (2026-05)
S3. Strong Q4 profit rebound (net profit up about 69%) — *financial*. Signals: `q_pat_yoy`. Sources: [Q4 profit +69%](https://www.whalesbook.com/news/English/consumer-products/Asian-Paints-Q4-Profit-Jumps-69percent-Amidst-Geopolitical-Caution/6a19661949974139aecee88f) (2026-05)

**Weaknesses**

W1. Value growth lagging volume (price cuts, downtrading): weak multi-year revenue growth — *financial*. Signals: `revenue_cagr_3y`, `revenue_cagr_5y`, `price_mix_growth`, `ebitda_cagr_3y`, `pat_cagr_3y`, flag `G06`. Sources: [volume 12.4% vs value 10.2%; growth comeback question](https://www.indmoney.com/blog/stocks/is-asian-paints-growth-making-a-comeback) (2026-05)
W2. Unprecedented competition (Birla Opus, JSW Paints) threatening market share and pricing — *qualitative*. Signals: none (qualitative). Sources: [competition from Birla Opus, JSW Akzo, JK Cement has not eased](https://www.plindia.com/pl-research/asian-paints-apnt-in-q4fy26-result-update-steady-growth-outlook-but-margins-have-peaked-out-hold/) (2026-05)
W3. Premium valuation hard to justify; margins seen as having peaked (PL Hold) — *financial*. Signals: `pe_percentile_10y`, `ev_ebitda_percentile_10y`, `implied_minus_delivered_growth`, `ev_ic_to_roic_wacc`, flag `V01`, flag `V02`, flag `V04`. Sources: [premium valuation some analysts find hard to justify](https://www.whalesbook.com/news/English/brokerage-reports/Asian-Paints-Rally-Hits-Resistance-Analysts-Weigh-Margin-Risks/6a1d149dcc8b4288bbd03856) (2026-05)

## TATASTEEL (metals, as of FY26)

**Strengths**

S1. Earnings rebound led by India (Q4 PAT more than doubled; India EBITDA margin at a 15-year high) — *financial*. Signals: `q_pat_yoy`, `q_ebitda_margin_yoy_change`, `ebitda_per_tonne_vs_avg`, `ebitda_cagr_3y`. Sources: [India growth powers results](https://www.whalesbook.com/news/English/industrial-goodsservices/Tata-Steel-India-Growth-Powers-Results-Europe-Woes-Loom-Valuation-Focus/6a0a654c591776c1328943be) (2026-05-18); [PAT +147%](https://insights.dsij.in/appmindshare/tata-group-backed-steel-company-reports-q4fy26-results-pat-jumps-147-announces-rs-4-per-share-dividend-id021-57166) (2026-05-15)
S2. Deleveraging: net debt cut by Rs 2,285 crore to Rs 80,144 crore; net debt/EBITDA 2.3x — *financial*. Signals: `debt_vs_ebitda_growth`, `net_debt_to_ebitda`. Sources: [net debt down to Rs 80,144 crore, 2.3x EBITDA](https://www.inkl.com/news/tata-steel-q4-net-more-than-doubles-on-india-strength-europe-recovery) (2026-05-15)
S3. European turnaround under way (Netherlands EBITDA Rs 624 crore vs Rs 132 crore) — *qualitative*. Signals: none (qualitative). Sources: [Europe recovery](https://www.inkl.com/news/tata-steel-q4-net-more-than-doubles-on-india-strength-europe-recovery) (2026-05-15)

**Weaknesses**

W1. UK business still loss-making (EBITDA loss Rs 591 crore in Q4) — *qualitative*. Signals: none (qualitative). Sources: [UK losses narrowed but large; Europe risk](https://www.multibagg.ai/market-pulse/articles/tata-steel-q4-fy26-europe-risk-cmpb1zy960brlnv0jjcu8868o) (2026-05)
W2. Dutch emissions/permit and steel-price risks in Europe — *qualitative*. Signals: none (qualitative). Sources: [Dutch permit risk](https://www.whalesbook.com/news/English/industrial-goodsservices/Tata-Steel-India-Profit-Surge-Meets-Dutch-Permit-Risk/6a07f6d1e125a601ebe2d766) (2026-05-16)
W3. Valuation high relative to the pace of Europe's recovery — *financial*. Signals: `pb_percentile_10y`, `ev_ebitda_percentile_10y`, `pe_percentile_10y`, `implied_minus_delivered_growth`, `ev_ic_to_roic_wacc`, flag `V01`, flag `V02`, flag `V04`. Sources: [high valuation needs careful assessment](https://www.whalesbook.com/news/English/industrial-goodsservices/Tata-Steel-India-Growth-Powers-Results-Europe-Woes-Loom-Valuation-Focus/6a0a654c591776c1328943be) (2026-05-18)

## ULTRACEMCO (cement, as of FY26)

**Strengths**

S1. Volume growth about 9% YoY (record quarter), helped by acquisitions and capacity crossing 200 mtpa — *financial*. Signals: `revenue_cagr_3y`, `q_revenue_yoy`, `revenue_cagr_5y`. Sources: [volume +9% YoY to 44.7 mt; JM Financial: strong operating performance](https://www.business-standard.com/markets/news/ultratech-cement-q4-results-analyst-outlook-cost-pressure-risks-126042800361_1.html) (2026-04-28)
S2. EBITDA per tonne up 11% YoY to about Rs 1,253 (better realisations, cost cuts of Rs 185/t) — *kpi*. Signals: `ebitda_per_tonne`, `ebitda_per_tonne_vs_avg`. Sources: [EBITDA/t Rs 1,253, +11% YoY](https://www.business-standard.com/markets/news/ultratech-cement-q4-results-analyst-outlook-cost-pressure-risks-126042800361_1.html) (2026-04-28)
S3. Conservative balance sheet (debt/equity about 0.33x) — *financial*. Signals: `net_debt_to_equity`, `net_debt_to_ebitda`, `interest_cover`. Sources: [debt-to-equity conservative at 0.33-0.34x](https://www.whalesbook.com/news/English/industrial-goodsservices/UltraTech-Cement-Posts-Strong-Quarter-Amid-Sector-Headwinds/69f239b108235f0c2a1be34b) (2026-04-29)

**Weaknesses**

W1. Cost pressure squeezing margins (operating margin 20% vs 22%; fuel and packaging costs to rise) — *financial*. Signals: `q_ebitda_margin_yoy_change`, `ebitda_margin`, flag `M01`, flag `M05`. Sources: [profit squeezed by rising costs](https://www.whalesbook.com/news/English/industrial-goodsservices/UltraTech-Cement-Q4-Sales-Surge-Profit-Squeezed-by-Rising-Costs/69f02f2735c37de4af34d945) (2026-04-28)
W2. Acquisition integration risk: India Cements EBITDA only about Rs 497/t, diluting returns — *financial*. Signals: `incremental_roic_3y`, `acquisition_roic_delta_3y`, `roic_wacc_spread`, `roce`, flag `A05`, flag `R03`. Sources: [integration of acquired companies carries execution risk](https://www.whalesbook.com/news/English/industrial-goodsservices/UltraTech-Cement-Posts-Strong-Quarter-Amid-Sector-Headwinds/69f239b108235f0c2a1be34b) (2026-04-29)
W3. Industry overcapacity fears and weak cement prices in some regions — *qualitative*. Signals: none (qualitative). Sources: [overcapacity fears rise](https://www.whalesbook.com/news/English/industrial-goodsservices/UltraTech-Cement-Tops-Q4-Estimates-Record-Dividend-Overcapacity-Fears-Rise/69f239b108235f0c2a1be34b) (2026-04-29)

## SUNPHARMA (pharma, as of FY26)

**Strengths**

S1. Specialty (innovative medicines: Ilumya, Winlevi, Cequa, Leqselvi) scaling up — *qualitative*. Signals: none (qualitative). Sources: [HDFC Securities: specialty scale-up to offset soft US generics](https://www.businesstoday.in/amp/markets/stocks/story/sun-pharma-shares-near-52-week-high-still-a-buy-post-q4-results-532983-2026-05-23) (2026-05-23)
S2. India formulations growing well (new launches, in-licensing; FY26 India sales +14%) — *kpi*. Signals: `india_growth`, `india_share`. Sources: [India business: new launches, in-licensing](https://www.businesstoday.in/amp/markets/stocks/story/sun-pharma-shares-near-52-week-high-still-a-buy-post-q4-results-532983-2026-05-23) (2026-05-23); [India formulation sales up 14%](https://sunpharma.com/wp-content/uploads/2026/05/Press-Release-Sun-Pharma-Q4FY26-Financial-Result.pdf) (2026-05-22)
S3. Gross margin expanded (+118 bps YoY) and Q4 profit up 26% — *financial*. Signals: `gross_margin`, `q_pat_yoy`, `materials_pct`. Sources: [gross margin +118 bps](https://www.businesstoday.in/amp/markets/stocks/story/sun-pharma-shares-near-52-week-high-still-a-buy-post-q4-results-532983-2026-05-23) (2026-05-23); [net profit +26% in Q4](https://www.freepressjournal.in/business/sun-pharma-reports-14-revenue-growth-to-14612-crore-net-profit-up-26-in-q4) (2026-05-22)

**Weaknesses**

W1. US generics declining (pricing pressure; FY26 US sales about -1%) — *kpi*. Signals: `us_growth`, flag `PH02`. Sources: [US generics pressure](https://www.whalesbook.com/news/English/brokerage-reports/Sun-Pharma-Faces-US-Generics-Pressure-Despite-Specialty-Growth/6a139e34b979113840c96686) (2026-05-22); [US sales dip](https://www.sahi.com/news/sun-pharma-posts-26-q4-profit-jump-to-2-710-crore-us-sales-dip-1-1-1685-PE1_COR) (2026-05-22)
W2. FDA compliance issues at Halol, Mohali and Dadra limit US launches — *qualitative*. Signals: flag `PH03`. Sources: [compliance issues at three key sites](https://www.whalesbook.com/news/English/healthcarebiotech/Sun-Pharma-Q4-Profit-Rises-But-Margin-Pressure-and-US-Stalls-Dampen-Outlook/6a13d33eb979113840c98625) (2026-05-22)
W3. EBITDA growth lagging sales (EBITDA +3% vs sales +13%) on higher R&D and specialty costs; muted FY27 guidance — *financial*. Signals: `q_ebitda_margin_yoy_change`, `ebitda_cagr_3y`, `rd_pct`, `other_expenses_pct`, flag `M05`, flag `M06`, flag `M01`. Sources: [EBITDA +3% YoY despite 13% sales growth](https://www.businesstoday.in/amp/markets/stocks/story/sun-pharma-shares-near-52-week-high-still-a-buy-post-q4-results-532983-2026-05-23) (2026-05-23); [declining margins, conservative guidance](https://www.whalesbook.com/news/English/healthcarebiotech/Sun-Pharma-Q4-Profit-Rises-But-Margin-Pressure-and-US-Stalls-Dampen-Outlook/6a13d33eb979113840c98625) (2026-05-22)

## MARUTI (auto, as of FY26)

**Strengths**

S1. Record volumes and revenue (Q4 revenue +29%; highest-ever quarterly volume) — *financial*. Signals: `q_revenue_yoy`, `revenue_cagr_3y`, `volume_growth_units`. Sources: [revenue up 28.9%](https://www.bajajbroking.in/share-market-news/maruti-suzuki-q4-fy26-results-revenue-up-28-9-percent-profit-under-pressure-rs140-dividend) (2026-04-28); [record FY26 revenue](https://www.autocarpro.in/NEWS/maruti-suzuki-posts-record-fy26-revenue-but-profit-stays-flat-as-costs-climb-132294) (2026-04-28)
S2. Exports surging (+61% in Q4, 30%+ in FY26) — *qualitative*. Signals: none (qualitative). Sources: [exports +61.3%](https://www.businesstoday.in/markets/stocks/story/should-you-buy-maruti-suzuki-shares-post-q4-results-check-target-price-recommendation-rationale-528008-2026-04-29) (2026-04-29)
S3. Debt-free balance sheet with strong cash generation (CFO about Rs 19,100 crore) — *financial*. Signals: `net_debt_to_equity`, `net_debt_to_ebitda`, `interest_cover`, `cfo_to_pat_5y`, `altman_z_india`. Sources: [debt-free; strong cash generation gives flexibility](https://www.autocarpro.in/news/maruti-suzuki-reports-record-year-costs-dent-profit-132282) (2026-04-28)

**Weaknesses**

W1. Margin squeeze and profit decline despite revenue growth (Q4 EBITDA margin 12.3%, PAT -7%; FY26 profit flat) — *financial*. Signals: `q_ebitda_margin_yoy_change`, `q_pat_yoy`, `pat_cagr_3y`, flag `M01`, flag `M06`, flag `G05`. Sources: [profit dips on margin squeeze](https://www.whalesbook.com/news/English/auto/Maruti-Suzuki-Revenue-Soars-Profit-Dips-on-Margin-Squeeze/69f2251608235f0c2a18505e) (2026-04-28); [margin pressure](https://www.multibagg.ai/market-pulse/articles/maruti-suzuki-q4-margins-pressure-cmok7b2fqahnipg0j3aui4x38) (2026-04-29)
W2. Domestic market share near a 13-year low as demand shifts to SUVs (Jefferies) — *qualitative*. Signals: none (qualitative). Sources: [Jefferies: market share at a 13-year low](https://www.businesstoday.in/markets/stocks/story/should-you-buy-maruti-suzuki-shares-post-q4-results-check-target-price-recommendation-rationale-528008-2026-04-29) (2026-04-29)
W3. Rising costs: shrinking gross margin, heavy capex (Rs 10,400 crore) and depreciation up 20% — *financial*. Signals: `gross_margin`, `materials_pct`, `dep_to_sales`, `capex_to_depreciation`, `capex_to_sales`, flag `M03`, flag `C06`. Sources: [profit shrinks on rising costs; shrinking gross margins](https://www.whalesbook.com/news/English/auto/Maruti-Suzuki-Q4-Revenue-Soars-But-Profit-Shrinks-on-Rising-Costs/69f1d79908235f0c2a16ddd9) (2026-04-28); [capex Rs 10,397.6 crore; depreciation +20.2%](https://www.autocarpro.in/news/maruti-suzuki-reports-record-year-costs-dent-profit-132282) (2026-04-28)

## BEL (capital_goods_defence, as of FY26)

**Strengths**

S1. Strong order book (about Rs 73,900 crore, about 2.7x revenue) giving 2-3 years of visibility — *kpi*. Signals: `order_book_to_revenue`, `book_to_bill_orders`, `opening_order_book`. Sources: [order book 2.7x; Goldman Buy](https://www.whalesbook.com/news/English/industrial-goods-and-services/BEL-Stock-Gains-Goldman-Sachs-Reiterates-Buy-Sets-Rs-475-Target/6a0d2f6d920520825bc62061) (2026-05-20)
S2. High margins (EBITDA about 29%; guided above 28%) — *financial*. Signals: `ebitda_margin`, `ebit_margin`, `pat_margin`. Sources: [Q4 EBITDA margin 29.2%](https://ticker.finology.in/discover/market-update/bel-q4-fy26-results-analysis) (2026-05-19)
S3. Steady revenue growth (FY26 about +16%; FY27 guidance above 15%) — *financial*. Signals: `revenue_cagr_3y`, `revenue_cagr_5y`, `q_revenue_yoy`. Sources: [16% revenue growth](https://www.psuconnect.in/financial/bel-results-2026-what-investors-should-know-after-navratna-psus-16-revenue-growtth) (2026-05-19)

**Weaknesses**

W1. Margin dip (Q4 EBITDA margin 29.2% vs 30.8%) on mix and costs — *financial*. Signals: `q_ebitda_margin_yoy_change`, flag `M01`. Sources: [share falls on margin and cost concerns](https://hdfcsky.com/news/bel-share-price-falls-q4-results-margin-cost-concerns) (2026-05-19)
W2. Working capital deteriorated: receivables up from 127 to 146 days — *financial*. Signals: `dso`, `nwc_days`, `receivables_vs_revenue_growth`, `cash_conversion_cycle`, flag `C01`, flag `C07`, flag `Q04`. Sources: [receivables 127 -> 146 days](https://bsmedia.business-standard.com/_media/bs/data/market-reports/equity-brokertips/2026-05/17792538440.04051900.pdf) (2026-05)
W3. Premium valuation a risk for FY27 — *financial*. Signals: `pe_percentile_10y`, `ev_ebitda_percentile_10y`, `implied_minus_delivered_growth`, `ev_ic_to_roic_wacc`, flag `V01`, flag `V02`, flag `V04`. Sources: [premium valuations a risk](https://blog.liquide.life/bel-q4-results-2026-share-price-target-dividend/) (2026-05-19)

## DLF (real_estate, as of FY26)

**Strengths**

S1. Net cash of Rs 14,155 crore; development arm debt-free — *financial*. Signals: `net_debt_to_equity`, `net_debt_to_presales`, `net_debt_to_ebitda`, `interest_cover`. Sources: [net cash Rs 14,155 crore](https://www.whalesbook.com/corporate-news/English/real-estate/DLF-Hits-indian-rupee14155-Cr-Net-Cash-as-Development-Arm-Goes-Debt-Free-in-FY26/6a0b2b1acfe07c0307e6a068) (2026-05-18)
S2. Record collections (over Rs 13,500 crore, +15%) and strong cash generation — *kpi*. Signals: `cfo_to_collections`, `collections_to_presales`, `cfo_to_presales`, `cfo_to_pat_5y`, `fcf_to_pat_5y`. Sources: [record collections over Rs 13,500 crore, +15%](https://quartr.com/companies/dlf-ltd_4901) (2026-05); [Nuvama Buy on improved cash generation](https://www.whalesbook.com/news/English/real-estate/DLF-Pivots-to-Profit-Cash-Focus-Amidst-Soft-FY26-Bookings/6a070b5ee125a601ebdb6c2f) (2026-05-15)
S3. Large bookings base (FY26 new sales bookings about Rs 20,100 crore) and profit growth (FY26 PAT +16%) — *kpi*. Signals: `presales_to_revenue`, `pat_cagr_3y`, `eps_cagr_3y`. Sources: [FY26 net profit +16%](https://www.angelone.in/news/stocks/dlf-share-price-in-focus-net-profit-rises-in-fy26-results-dividend-increased) (2026-05-14); [FY26 sales bookings Rs 20,143 crore](https://www.investywise.com/?p=85283) (2026-05)

**Weaknesses**

W1. Pre-sales soft: FY26 bookings down about 5% and at the low end of guidance (Citi) — *kpi*. Signals: `presales_growth`, flag `RE04`. Sources: [soft FY26 bookings, -5%](https://www.whalesbook.com/news/English/real-estate/DLF-Pivots-to-Profit-Cash-Focus-Amidst-Soft-FY26-Bookings/6a070b5ee125a601ebdb6c2f) (2026-05-15)
W2. Revenue recognition lagging bookings (Q4 revenue down about 42% YoY) — *financial*. Signals: `q_revenue_yoy`, `revenue_cagr_3y`, `revenue_growth_volatility`, flag `G04`, flag `G05`. Sources: [Q4 revenue drop about 42% YoY](https://www.whalesbook.com/news/English/real-estate/DLF-Navigates-Q4-Dip-Full-Year-Strength-Signals-Resilience/6a04d0249444064ed0882904) (2026-05-14)
W3. EBITDA margin dipped — *financial*. Signals: `q_ebitda_margin_yoy_change`, `ebitda_margin`, flag `M01`, flag `M07`. Sources: [margin dip sparks concern](https://www.whalesbook.com/corporate-news/English/real-estate/DLF-FY26-indian-rupee20143-Cr-Bookings-indian-rupee4408-Cr-Profit-Margin-Dip-Sparks-Concern/6a04b3ba9444064ed077b84d) (2026-05-14)

## NTPC (utilities, as of FY26)

**Strengths**

S1. Capacity growth: group added 9.6 GW in FY26; regulated equity up to Rs 1.20 trillion — *kpi*. Signals: `capacity_growth_mw`, `regulated_equity_growth`, `renewable_share`. Sources: [group additions 9.62 GW; regulated equity Rs 1.20 tn](https://informistmedia.com/EquityWire/51292/Earnings-Review-NTPC-Q4-PAT-growth-highest-in-20-qtrs-aided-by-tax-writeback) (2026-05-23)
S2. Steady regulated core RoE of 16-17% (Nuvama top pick) — *financial*. Signals: `roe`, `regulated_roe_gap`, `roic_wacc_spread`. Sources: [Nuvama: steady-state core RoE 16-17%](https://www.businesstoday.in/markets/stocks/story/engineers-india-shares-climb-5-ntpc-green-ntpc-drop-up-to-4-targets-for-three-psus-post-q4-results-533092-2026-05-25) (2026-05-25)
S3. Profit beat with improving efficiency (Q4 PAT +34%) — *financial*. Signals: `q_pat_yoy`, `pat_cagr_3y`. Sources: [profit +34% on efficiency](https://www.whalesbook.com/news/English/energy/NTPC-Profit-Jumps-34percent-on-Strong-Efficiency-Beats-Estimates/6a11957be28c1d234359f338) (2026-05-23)

**Weaknesses**

W1. Profit beat flattered by a one-off tax write-back; core earnings growth modest — *financial*. Signals: `exceptional_size_5y`, `tax_burden`, `eps_cagr_3y`, flag `Q05`, flag `G01`. Sources: [PAT aided by tax write-back of INR 87.37 bn](https://informistmedia.com/EquityWire/51292/Earnings-Review-NTPC-Q4-PAT-growth-highest-in-20-qtrs-aided-by-tax-writeback) (2026-05-23)
W2. Flat revenue (Q4 revenue -0.3%); near-term growth challenges — *financial*. Signals: `q_revenue_yoy`, `revenue_cagr_3y`, flag `G05`, flag `G06`. Sources: [revenue dipped 0.3%](https://www.whalesbook.com/news/English/energy/NTPC-Profit-Jumps-34percent-on-Strong-Efficiency-Beats-Estimates/6a11957be28c1d234359f338) (2026-05-23)
W3. Heavy capex funded by borrowing (group capex Rs 49,000 crore) raising finance costs — *financial*. Signals: `net_debt_to_ebitda`, `net_debt_to_equity`, `capex_to_sales`, `debt_vs_ebitda_growth`, `interest_cover`, flag `B01`, flag `B02`, flag `UT03`. Sources: [group capex INR 490.68 bn](https://informistmedia.com/EquityWire/51292/Earnings-Review-NTPC-Q4-PAT-growth-highest-in-20-qtrs-aided-by-tax-writeback) (2026-05-23); [finance costs as NTPC borrows to fund capex](https://univest.in/blogs/ntpc-q4-results-2026) (2026-05)

## DMART (retail, as of FY26)

**Strengths**

S1. Revenue growth about 19% driven by expansion — *financial*. Signals: `q_revenue_yoy`, `revenue_cagr_3y`, `revenue_cagr_5y`. Sources: [revenue +18.9%, PAT +19%](https://www.angelone.in/news/stocks/avenue-supermarts-q4-fy26-results-net-profit-rises-19-percent-yoy-to-rs-657-crore-revenue-jumps-to-rs-17684-crore) (2026-05-02); [revenue up 19% on expansion](https://www.whalesbook.com/news/English/brokerage-reports/D-Mart-Revenue-Up-19percent-on-Expansion-Valuation-Margin-Pressures-Persist/69f822069d1c90664820b42a) (2026-05-04)
S2. Fastest store-addition year: crossed 500 stores (58 added in Q4, 85 in FY26) — *kpi*. Signals: `store_growth`, `store_additions`. Sources: [hits 500 stores](https://www.whalesbook.com/news/English/consumer-products/DMarts-Q4-Revenue-Jumps-19percent-Hits-500-Stores-Amid-Valuation-Worries/69f4645008235f0c2a3ec8c1) (2026-05-02)
S3. Profit growth about 19% with stable-to-better margins (EBITDA margin up about 37 bps per one brokerage) — *financial*. Signals: `q_pat_yoy`, `q_ebitda_margin_yoy_change`. Sources: [brokerage note: EBITDA margin +37 bps; execution intact](https://bsmedia.business-standard.com/_media/bs/data/market-reports/equity-brokertips/2026-05/17778740390.12902300.pdf) (2026-05)

**Weaknesses**

W1. Valuation worries (Jefferies and ICICI Securities Hold) — *financial*. Signals: `pe_percentile_10y`, `ev_ebitda_percentile_10y`, `implied_minus_delivered_growth`, `ev_ic_to_roic_wacc`, flag `V01`, flag `V02`, flag `V04`. Sources: [valuation worries divide analysts](https://www.whalesbook.com/news/English/consumer-products/DMart-Q4-Results-Show-Strong-Growth-But-Valuation-Worries-Divide-Analysts/69d279ac31d4f2ab48091d4f) (2026-05); [Jefferies Hold](https://www.zeebiz.com/markets/stocks/news-dmart-shares-slip-4-despite-19-profit-jump-is-it-a-buying-opportunity-394799) (2026-05-04)
W2. Costs and competition (incl. quick commerce) squeezing gross margins — *financial*. Signals: `gross_margin`, `ebitda_margin`, `ebitda_margin_pre_ind_as116`, flag `M01`, flag `M05`, flag `RT03`. Sources: [costs and competition squeeze margins](https://www.whalesbook.com/news/English/consumer-products/DMart-Sees-19percent-Revenue-Jump-But-Costs-and-Competition-Squeeze-Margins/69d3cfe131d4f2ab480c8082) (2026-05)
W3. Rising debt, higher inventory and slower turnover / store productivity — *financial*. Signals: `dio`, `inventory_to_sales`, `asset_turnover`, `revenue_per_sqft`, `net_debt_to_equity`, flag `C02`, flag `C04`, flag `RT02`. Sources: [debt and inventory concerns; slower turnover](https://www.whalesbook.com/news/English/consumer-products/Avenue-Supermarts-DMART-Stock-Dips-Amid-Debt-and-Inventory-Concerns/69f9bbd8d87e3288bea977bb) (2026-05)

## ADANIENT (holdco, as of FY26)

**Strengths**

S1. EBITDA growth led by airports (now the largest EBITDA contributor); consolidated FY26 EBITDA about Rs 16,464 crore — *financial*. Signals: `ebitda_cagr_3y`, `ebitda_cagr_5y`. Sources: [FY26 consolidated EBITDA](https://www.adanienterprises.com/-/media/Project/Enterprises/Investors/Investor-Downloads/Result-Press-Release-Dynamic/Q4-FY26---Press-Release.pdf) (2026-04-30); [airports largest EBITDA contributor](https://ticker.finology.in/discover/market-update/adani-enterprises-q3-fy26-results-analysis) (2026-02)
S2. Headline FY26 net profit up about 31% — *financial*. Signals: `pat_cagr_3y`, `eps_cagr_3y`, `pat_cagr_5y`. Sources: [FY26 net profit +31%](https://www.newkerala.com/news/a/adani-enterprises-posts-31-pc-net-profit-growth-621.htm) (2026-04-30)
S3. Revenue growth (Q4 revenue +20%) — *financial*. Signals: `q_revenue_yoy`, `revenue_cagr_3y`. Sources: [revenue up 20%](https://www.outlookbusiness.com/corporate/adani-enterprises-q4-fy26-revenue-up-20-new-assets-drag-company-to-221-cr-net-loss) (2026-04-30)

**Weaknesses**

W1. Heavy capex strains free cash flow and needs continuous external funding (rights issue Rs 24,930 crore, QIP Rs 15,000 crore) — *financial*. Signals: `fcf_to_pat_5y`, `fcf_to_pat`, `capex_to_sales`, `organic_capital_share_3y`, `share_count_change`, flag `Q02`, flag `G03`, flag `C06`. Sources: [capex will continue to strain FCF and need funding](https://www.whalesbook.com/news/English/industrial-goodsservices/Adani-Enterprises-Posts-March-Quarter-Loss-on-Higher-Infrastructure-Costs/69f3527a08235f0c2a214112) (2026-04-30)
W2. Debt-laden balance sheet; net external debt rose in FY26 to fund record capex — *financial*. Signals: `net_debt_to_ebitda`, `net_debt_to_equity`, `debt_vs_ebitda_growth`, `standalone_debt_to_equity`, `interest_cover`, flag `B01`, flag `B02`, flag `B03`, flag `HC01`. Sources: [record capex; net debt rose](https://upstox.com/news/market-news/stocks/adani-group-firms-post-record-16-bn-capex-all-time-high-ebitda-in-fy-26-check-how-stocks-fared/article-194682/) (2026-05); [debt-laden balance sheet warrants close monitoring](https://www.pulse.bot/finance/news/adani-enterprises-posts-22071-crore-loss-in-q4-fy26-034f82a8-b5f8-4b95-a85e-1d9e35d857f7/) (2026-04-30)
W3. New assets not yet earning: Q4 net loss of Rs 221 crore on higher depreciation and interest; low returns on capital — *financial*. Signals: `q_pat_yoy`, `roic_wacc_spread`, `incremental_roic_3y`, `roce`, `interest_cover`, flag `R01`, flag `R03`, flag `A07`, flag `B03`. Sources: [new assets drag company to a net loss](https://www.outlookbusiness.com/corporate/adani-enterprises-q4-fy26-revenue-up-20-new-assets-drag-company-to-221-cr-net-loss) (2026-04-30)

## BHARTIARTL (telecom, as of FY26)

**Strengths**

S1. ARPU growth (Rs 257 vs Rs 245) on tariff hikes and premiumisation — *kpi*. Signals: `arpu_growth`, `arpu`. Sources: [ARPU Rs 257 vs Rs 245](https://www.business-standard.com/markets/capital-market-news/bharti-airtel-q4-pat-tumbles-34-yoy-to-rs-7-325-cr-126051301273_1.html) (2026-05-13); [premiumisation and tariff hikes sustain momentum](https://www.business-standard.com/markets/news/premiumisation-tariff-hikes-expected-to-sustain-airtel-s-earnings-momentum-126080601588_1.html) (2026-08-06)
S2. High and growing EBITDA (consolidated margin about 58%, revenue +16%) — *financial*. Signals: `ebitda_margin`, `ebitda_cagr_3y`, `revenue_cagr_3y`. Sources: [EBITDA Rs 32,038 crore, 57.8% margin; revenue +15.7%](https://www.business-standard.com/markets/capital-market-news/bharti-airtel-q4-pat-tumbles-34-yoy-to-rs-7-325-cr-126051301273_1.html) (2026-05-13)
S3. Strong free cash flow and deleveraging (Motilal: about Rs 1.3 trillion FCF over FY26-28, net cash ex-leases by FY28) — *financial*. Signals: `fcf_to_pat_5y`, `fcf_to_pat`, `debt_vs_ebitda_growth`, `cfo_to_ebitda`. Sources: [Motilal Oswal FCF and net-cash view](https://www.business-standard.com/markets/news/bharti-airtel-share-price-nse-bse-correction-overdone-say-analysts-tariff-hikes-jio-ipo-key-triggers-126030200184_1.html) (2026-03-02)

**Weaknesses**

W1. Q4 profit down about 34% YoY (exceptional-gain base effect) — *financial*. Signals: `q_pat_yoy`, `exceptional_frequency_5y`, `exceptional_size_5y`, flag `Q05`. Sources: [Q4 PAT tumbles 34% YoY](https://www.business-standard.com/markets/capital-market-news/bharti-airtel-q4-pat-tumbles-34-yoy-to-rs-7-325-cr-126051301273_1.html) (2026-05-13)
W2. High capex intensity (Q4 capex about Rs 13,500 crore; expected to moderate only in FY27) — *financial*. Signals: `capex_intensity_reported`, `capex_to_sales`, `capex_to_depreciation`, flag `TC03`. Sources: [BNP: capex to moderate in FY27](https://www.business-standard.com/markets/news/bharti-airtel-dips-4-sees-sharpest-intra-day-fall-in-3-months-here-s-why-126022400248_1.html) (2026-02-24)
W3. Leverage including leases and spectrum dues still significant (net cash ex-leases only expected by FY28) — *financial*. Signals: `net_debt_to_ebitda`, `net_debt_to_equity`, `lease_share_of_debt`, `spectrum_share_of_debt`, flag `TC02`, flag `B02`. Sources: [net cash excluding leases only by FY28](https://www.business-standard.com/markets/news/bharti-airtel-share-price-nse-bse-correction-overdone-say-analysts-tariff-hikes-jio-ipo-key-triggers-126030200184_1.html) (2026-03-02)

## ICICIBANK (bank, as of FY26) — holdout

**Strengths**

S1. Best-in-class asset quality (NNPA about 0.33%, GNPA about 1.4%, low credit costs) — *kpi*. Signals: `gnpa_ratio`, `nnpa_ratio`, `credit_cost`, `pcr`. Sources: [NNPA 0.33%; asset quality](https://blog.liquide.life/icici-bank-q4-results-2026-analysis-share-price-target/) (2026-04-18); [GNPA declined](https://www.angelone.in/news/stocks/icici-bank-q4-fy26-results-net-profit-rises-8-5-percent-rs-2-dividend-announced) (2026-04-18)
S2. High profitability (RoA above 2.3%) — *financial*. Signals: `roa`, `roe`, `roe_ke_spread`. Sources: [Buy thesis on RoA above 2.3%](https://www.multibagg.ai/market-pulse/articles/icici-bank-q4fy26-brokerage-targets-cmo6qy52g8lpiph0jhhrzuxg7) (2026-04-19)
S3. Loan growth rebounded to about 15.8% YoY — *kpi*. Signals: `loan_growth`, `assets_cagr_3y`. Sources: [credit growth about 15.8%](https://www.jmfinancialservices.in/market-news-and-insights/1686241) (2026-04-18)

**Weaknesses**

W1. Margin pressure (NIM expected to decline as rates fall) — *financial*. Signals: `nii_to_assets`, `nim_reported`, `nii_cagr_3y`, flag `M08`. Sources: [faces margin pressure](https://www.whalesbook.com/news/English/brokerage-reports/ICICI-Bank-Q4-Profit-Surges-85percent-Faces-Margin-Pressure/69e5b1afbca97ee10692fe45) (2026-04-19)
W2. Weak operating profit growth (about +3% YoY) as expenses jumped 12% — *financial*. Signals: `cost_to_income`, `bank_opex_to_assets`, `opex_to_assets`, `q_pat_yoy`. Sources: [operating profit growth about 3% YoY](https://www.kotakneo.com/uploads/ICICI_Bank_One_Pager_Q4_Result_Update_29_May26_14fdb794a1.pdf) (2026-05-29); [expenses jump 12%](https://www.whalesbook.com/news/English/bankingfinance/ICICI-Bank-Profit-Rises-85percent-as-Expenses-Jump-12percent/69e3778371f6be70c53c4a80) (2026-04-18)
W3. High market expectations hard to meet (valuation) — *financial*. Signals: `pb_to_justified_pb`, `implied_pb_growth_minus_delivered`, `pb_percentile_10y`, flag `V03`, flag `V05`, flag `V06`. Sources: [high expectations that are hard to meet](https://www.kotakneo.com/uploads/ICICI_Bank_One_Pager_Q4_Result_Update_29_May26_14fdb794a1.pdf) (2026-05-29)

## INFY (it_services, as of FY26) — holdout

**Strengths**

S1. Healthy operating margin (about 21%; FY27 guided 20-22%) — *financial*. Signals: `ebit_margin`, `operating_margin`, `ebitda_margin`. Sources: [margins expanding to 21%](https://www.outlookbusiness.com/corporate/infosys-posts-28-qoq-jump-in-profit-to-8501-cr-in-q4-fy26) (2026-04-23)
S2. Large deal wins of USD 14.9 bn in FY26 (+24%) — *kpi*. Signals: `deal_tcv_growth`, `book_to_bill`. Sources: [USD 14.9 bn deals, +24%](https://www.bajajbroking.in/share-market-news/infosys-ltd-q4-fy26-profit-up-20-91-percent-14-9-billion-dollar-deals-revenue-guidance-at-1-5-percent-to-3-5-percent-for-fy27) (2026-04-23)
S3. Profit growth (Q4 net profit +21% YoY) — *financial*. Signals: `q_pat_yoy`. Sources: [net profit +21%](https://www.angelone.in/news/stocks/infosys-q4-results-net-profit-jumps-21-percent-to-rs-8501-crore-announced-final-dividend-rs-25) (2026-04-23)

**Weaknesses**

W1. Slow growth: FY26 constant-currency growth about 3%, weak FY27 guidance of 1.5-3.5% — *financial*. Signals: `revenue_cagr_3y`, `cc_growth`, `q_revenue_yoy`, flag `IT03`. Sources: [weak guidance offsets profit growth](https://www.outlookbusiness.com/markets/infosys-slides-5-post-results-weak-guidance-offsets-profit-growth) (2026-04-24)
W2. Margin pressure ahead from wage hikes and AI productivity pass-through ('AI deflation') — *qualitative*. Signals: none (qualitative). Sources: [AI deflation begins to bite; margin pressure](https://bsmedia.business-standard.com/_media/bs/data/market-reports/equity-brokertips/2026-04/17770201200.85965100.pdf) (2026-04)
W3. Rising competitive intensity in AI-led services; weakness at a large European client — *qualitative*. Signals: none (qualitative). Sources: [competitive intensity; large European manufacturing client](https://finance.yahoo.com/markets/stocks/articles/infosys-ltd-infy-q4-2026-070516803.html) (2026-04-24)

## NESTLEIND (fmcg, as of FY26) — holdout

**Strengths**

S1. Volume-led revenue growth (FY26 sales +14.9%; Q4 +22.6% with mid-teens volume growth) — *financial*. Signals: `q_revenue_yoy`, `revenue_cagr_3y`, `volume_growth`. Sources: [volume surge drives 23% revenue growth](https://www.whalesbook.com/news/English/consumer-products/Nestle-Indias-Volume-Surge-Drives-23percent-Revenue-Growth-Amid-Margin-Fears/69e85fdbbca97ee1069e8deb) (2026-04-22); [FY26 sales +14.9%](https://www.whalesbook.com/corporate-news/English/consumer-products/Nestle-India-FY26-Sales-Rise-149percent-to-indian-rupee23071-Cr-PAT-Grows-69percent/6a22a352c75ed156cfa19c13) (2026-06)
S2. High EBITDA margin (Q4 26.3%, beat expectations of compression) — *financial*. Signals: `ebitda_margin`, `ebit_margin`, `pat_margin`. Sources: [EBITDA margin 26.3%](https://www.outlookbusiness.com/markets/nestle-india-hits-52-week-high-as-q4-profit-jumps-27) (2026-04-22)
S3. Q4 profit up about 26-27% — *financial*. Signals: `q_pat_yoy`. Sources: [Q4 profit +27%](https://www.outlookbusiness.com/markets/nestle-india-hits-52-week-high-as-q4-profit-jumps-27) (2026-04-22)

**Weaknesses**

W1. Gross margin down about 140 bps in FY26 (palm oil and input costs absorbed for volume); FY26 PAT only +6.9% — *financial*. Signals: `gross_margin`, `gross_margin_change_1y`, `materials_pct`, `pat_cagr_3y`, flag `M03`, flag `FM04`. Sources: [gross margins down 140 bps YoY in FY26 to 55.3%](https://bsmedia.business-standard.com/_media/bs/data/market-reports/equity-brokertips/2026-04/17770200120.33680300.pdf) (2026-04); [absorbs costs for volume](https://www.whalesbook.com/news/English/consumer-products/Nestle-India-Absorbs-Costs-for-Volume-Ignoring-Peers-Price-Hikes/69fb600ed27867b982d4cff6) (2026-05)
W2. Valuation a concern (Jefferies) — *financial*. Signals: `pe_percentile_10y`, `ev_ebitda_percentile_10y`, `implied_minus_delivered_growth`, `ev_ic_to_roic_wacc`, flag `V01`, flag `V02`, flag `V04`. Sources: [Jefferies cites valuations as a concern](https://www.sahi.com/blogs/nestle-india-shares-surge-over-8-after-q4-fy-26-results-beat-estimates-5-final-dividend-announced) (2026-04-23)
W3. Heavy capacity capex (about Rs 3,900 crore, new Odisha factory) weighing on near-term margins and returns — *financial*. Signals: `capex_to_sales`, `capex_to_depreciation`, `cwip_to_net_block`, `fcf_to_pat`, flag `C03`, flag `C06`. Sources: [Rs 3,900 crore manufacturing investment weighs on near-term margins](https://www.business-standard.com/amp/markets/news/near-term-recovery-margin-expansion-key-for-nestle-india-125072501402_1.html) (2025-07-25)

## HAL (capital_goods_defence, as of FY26) — holdout

**Strengths**

S1. Massive order book (about Rs 2.54 lakh crore, about 7.7x revenue) — *kpi*. Signals: `order_book_to_revenue`, `book_to_bill_orders`, `order_book_growth`. Sources: [order book about Rs 2.54 lakh crore vs revenue about Rs 33,000 crore](https://www.indmoney.com/blog/stocks/can-hal-convert-its-massive-order-book-into-revenue-what-q4-fy-26-numbers-really-tell-investors) (2026-05)
S2. Profit growth (FY26 PAT Rs 9,116 crore vs Rs 8,364 crore) — *financial*. Signals: `pat_cagr_3y`, `pat_cagr_5y`, `eps_cagr_3y`. Sources: [FY26 net profit Rs 9,116 crore](https://www.indmoney.com/blog/stocks/can-hal-convert-its-massive-order-book-into-revenue-what-q4-fy-26-numbers-really-tell-investors) (2026-05)
S3. Programme mix (LCA Tejas, ALH, engine MRO) supports revenue visibility — *qualitative*. Signals: none (qualitative). Sources: [order book composition](https://www.indmoney.com/blog/stocks/can-hal-convert-its-massive-order-book-into-revenue-what-q4-fy-26-numbers-really-tell-investors) (2026-05)

**Weaknesses**

W1. Slow conversion of the order book (Q4 revenue +2%, FY26 about +7%): execution bottlenecks — *financial*. Signals: `q_revenue_yoy`, `revenue_cagr_3y`, `execution_rate`, flag `CG01`. Sources: [rising order book with slow revenue growth signals execution bottlenecks](https://www.indmoney.com/blog/stocks/can-hal-convert-its-massive-order-book-into-revenue-what-q4-fy-26-numbers-really-tell-investors) (2026-05)
W2. Engine supply (deliveries) constraining production — *qualitative*. Signals: none (qualitative). Sources: [engine deliveries critical](https://www.indmoney.com/blog/stocks/can-hal-convert-its-massive-order-book-into-revenue-what-q4-fy-26-numbers-really-tell-investors) (2026-05)
W3. Lumpy, year-end-loaded revenue recognition (Q4 profit +125% QoQ) — *financial*. Signals: `revenue_growth_volatility`, `pat_growth_volatility`, flag `G04`. Sources: [sequential profit surge from year-end recognition of large contracts](https://www.indmoney.com/blog/stocks/can-hal-convert-its-massive-order-book-into-revenue-what-q4-fy-26-numbers-really-tell-investors) (2026-05)

## YESBANK (bank, as of FY18) — blow-up

Warning signs visible in reported financials up to FY18, before the 2019-20 collapse (moratorium March 2020).

**Warning signs**

W1. Hyper loan growth far ahead of capital: advances +54% in FY18; loan book +81% since the March 2017 equity raise — *financial*. Signals: `loan_growth`, `assets_cagr_3y`, `growth_minus_icg`, `funding_vs_equity_growth`, flag `A06`, flag `BK05`, flag `B06`, flag `B07`. Sources: [advances up about 54% in FY18, mainly corporate](https://www.angelone.in/get-html-report/AngelBrokingResearch_YES%20Bank_IC_180718.html) (2018-07-18); [IDFC: loan book +81% since last equity issue; CET1 at 9%](https://app.researchpool.com/provider/idfc-securities/yes-bank-yesb-yes-banks-q2fy19-results-underperformer-miss-even-without-the-diverg) (2018-10)
W2. Thin core capital for that growth (CET1 about 9-9.7%), dependent on fresh equity raising — *kpi*. Signals: `cet1`, `crar`, `equity_to_assets`, flag `BK03`, flag `B06`. Sources: [CET1 at 9%: must raise capital or slow growth](https://app.researchpool.com/provider/idfc-securities/yes-bank-yesb-yes-banks-q2fy19-results-underperformer-miss-even-without-the-diverg) (2018-10); [CET1 8.4% vs 7.375% mandated](https://www.scribd.com/document/587744136/Yes-Bank) (2020)
W3. Reported asset quality unreliable: RBI divergence for FY16 (NPA Rs 749 crore reported vs Rs 4,926 crore assessed) and FY17 (Rs 6,355 crore under-reported) — *kpi*. Signals: `gnpa_ratio`, `nnpa_ratio`, `pcr`, flag `BK01`, flag `BK02`. Sources: [divergence in 2016, 2017 and 2019](https://ir.iimcal.ac.in:8443/jspui/bitstream/123456789/3996/1/Yes%20Bank%2c%20No%20Governance.pdf) (2020); [crisis apparent for years; FY16 NPA revised from Rs 749 crore to Rs 4,926 crore](https://www.outlookindia.com/amp/story/business/business-news-yes-bank-crisis-was-apparent-for-years-but-regulatory-oversight-was-lacking-news-302945) (2020-03)
W4. Credit-deposit ratio climbing (70% in Mar-13 to about 100%+ by FY18-19): funding stretched — *financial*. Signals: `cd_ratio`, flag `BK07`. Sources: [CD ratio 70% (Mar-13) to 106% (Mar-19)](https://ir.iimcal.ac.in:8443/jspui/bitstream/123456789/3996/1/Yes%20Bank%2c%20No%20Governance.pdf) (2020)
W5. Concentration in large, stressed corporate borrowers — *qualitative*. Signals: none (qualitative). Sources: [large corporate exposures](https://www.isas.nus.edu.sg/wp-content/uploads/2020/03/ISAS-Briefs-No.-756.pdf) (2020-03); [over-dependence on a few large borrowers](https://ifsa-network.com/publications/from-trust-to-turmoil-the-yes-bank-financial-scam/) (2020)
