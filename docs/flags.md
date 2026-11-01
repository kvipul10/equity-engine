# Red-flag rules

Generated from `config/flags.yaml` (generic) and `config/sectors/*.yaml` (sector rules) by `python -m engine rules --markdown`.

| id | pillar | severity | applies | origin | name | condition |
|---|---|---|---|---|---|---|
| G01 | growth | medium | ALL | config/flags.yaml | Profit growth far ahead of revenue growth | `m('pat_cagr_3y') - m('revenue_cagr_3y') > 0.15` |
| G02 | growth | medium | ALL | config/flags.yaml | Per-share growth lagging profit growth (dilution) | `m('pat_cagr_5y') - m('eps_cagr_5y') > 0.03` |
| G03 | growth | low | NF | config/flags.yaml | Fast growth funded mostly outside own capex | `m('organic_capital_share_3y') < 0.5 and m('revenue_cagr_3y') > 0.15` |
| G04 | growth | low | ALL | config/flags.yaml | Erratic revenue growth | `m('revenue_growth_volatility') > 1.5` |
| G05 | growth | medium | ALL | config/flags.yaml | Quarterly growth decelerating | `m('q_revenue_yoy_trend') < -0.01 and m('q_revenue_yoy') < 0.05` |
| G06 | growth | medium | ALL | config/flags.yaml | Revenue shrinking over 3 years | `m('revenue_cagr_3y') < 0` |
| M01 | margins | medium | NF | config/flags.yaml | EBITDA margin down three years running | `falling('ebitda_margin', 3) and chg('ebitda_margin', 3) < -0.02` |
| M02 | margins | medium | NF | config/flags.yaml | Profits leaning on other income | `m('other_income_to_pbt') > 0.25` |
| M03 | margins | medium | NF | config/flags.yaml | Materials cost creeping up | `chg('materials_pct', 3) > 0.03` |
| M04 | margins | medium | NF | config/flags.yaml | Employee cost creeping up | `chg('employee_pct', 3) > 0.03` |
| M05 | margins | low | NF | config/flags.yaml | Other operating costs creeping up | `chg('other_expenses_pct', 3) > 0.03` |
| M06 | margins | medium | NF | config/flags.yaml | Operating leverage working in reverse | `m('dol') > 3 and pchg('revenue', 1) < 0` |
| M07 | margins | low | NF | config/flags.yaml | Volatile margins | `m('ebitda_margin_sd_10y') > 0.05` |
| M08 | margins | medium | BL | config/flags.yaml | Net interest margin compressing | `chg('nii_to_assets', 2) < -0.005` |
| C01 | capital_efficiency | medium | NF | config/flags.yaml | Receivable days up three years running | `rising('dso', 3) and chg('dso', 3) > 5` |
| C02 | capital_efficiency | medium | NF | config/flags.yaml | Inventory days up three years running | `rising('dio', 3) and chg('dio', 3) > 5` |
| C03 | capital_efficiency | medium | NF | config/flags.yaml | Capital stuck in work-in-progress | `all_last('cwip_to_net_block', 2, '>', 0.30)` |
| C04 | capital_efficiency | low | NF | config/flags.yaml | Asset turnover slump | `pchg('asset_turnover', 3) < -0.20` |
| C05 | capital_efficiency | low | NF | config/flags.yaml | Under-investment | `all_last('capex_to_depreciation', 3, '<', 0.8)` |
| C06 | capital_efficiency | medium | NF | config/flags.yaml | Heavy capex with falling fixed-asset turnover | `m('capex_to_depreciation') > 3 and falling('fixed_asset_turnover', 2)` |
| C07 | capital_efficiency | medium | NF | config/flags.yaml | Working capital bloating | `chg('nwc_days', 3) > 30` |
| R01 | returns | high | NF | config/flags.yaml | ROIC below WACC for three years | `all_last('roic_wacc_spread', 3, '<', 0)` |
| R02 | returns | high | ALL (not INS) | config/flags.yaml | ROE rising on leverage while margins fall | `chg('roe', 3) > 0 and chg('equity_multiplier', 3) > 0 and chg('pat_margin', 3) < 0` |
| R03 | returns | medium | NF | config/flags.yaml | New capital earning below its cost | `m('incremental_roic_3y') < wacc and pchg('invested_capital', 3) > 0.30` |
| R04 | returns | medium | ALL | config/flags.yaml | ROE down three years running | `falling('roe', 3) and chg('roe', 3) < -0.05` |
| R05 | returns | high | FIN | config/flags.yaml | ROE below cost of equity (financials) | `all_last('roe_ke_spread', 2, '<', 0)` |
| Q01 | cash_quality | high | NF | config/flags.yaml | Profits not converting to cash (5y) | `sum_last('cfo', 5) < 0.6 * sum_last('pat_core', 5) and sum_last('pat_core', 5) > 0` |
| Q02 | cash_quality | medium | NF | config/flags.yaml | Negative free cash flow despite profits | `all_last('fcf', 3, '<', 0) and all_last('pat_core', 3, '>', 0)` |
| Q03 | cash_quality | medium | NF | config/flags.yaml | High accruals | `m('accruals_ratio') > 0.10` |
| Q04 | cash_quality | medium | NF | config/flags.yaml | Receivables outpacing revenue | `all_last('receivables_vs_revenue_growth', 2, '>', 0.10)` |
| Q05 | cash_quality | medium | NF | config/flags.yaml | Recurring 'exceptional' items | `m('exceptional_frequency_5y') >= 3` |
| Q06 | cash_quality | high | NF | config/flags.yaml | Beneish M-score in manipulator zone | `m('beneish_m_score') > -1.78` |
| Q07 | cash_quality | medium | NF | config/flags.yaml | Weak cash conversion of EBITDA | `all_last('cfo_to_ebitda', 2, '<', 0.5)` |
| B01 | balance_sheet | high | NF | config/flags.yaml | Debt growing faster than EBITDA for three years | `all_last('debt_vs_ebitda_growth', 3, '>', 0) and m('net_debt_to_ebitda') >= 0.5` |
| B02 | balance_sheet | high | NF | config/flags.yaml | High leverage | `m('net_debt_to_ebitda') > 4` |
| B03 | balance_sheet | high | NF | config/flags.yaml | Weak interest cover | `m('interest_cover') < 2` |
| B04 | balance_sheet | medium | NF | config/flags.yaml | Liquidity squeeze | `m('current_ratio_proxy') < 1.0 and m('cash_to_st_borrowings') < 0.2` |
| B05 | balance_sheet | high | NF (not telecom) | config/flags.yaml | Altman Z'' in distress zone | `m('altman_z_india') < 4.35` |
| B06 | balance_sheet | high | BL | config/flags.yaml | Capital ratio falling while balance sheet balloons; keeps crar, cet1 off the strengths list | `chg('equity_to_assets', 1) < -0.01 and pchg('total_assets', 1) > 0.25` |
| B07 | balance_sheet | medium | BL | config/flags.yaml | Funding outgrowing equity | `m('funding_vs_equity_growth') > 0.20` |
| B08 | balance_sheet | medium | NBFC | config/flags.yaml | NBFC leverage high | `m('borrowings_to_equity') > 6` |
| A01 | capital_allocation | medium | ALL | config/flags.yaml | Dilution while ROE falls | `m('share_count_change') > 0.02 and chg('roe', 1) < 0` |
| A02 | capital_allocation | high | ALL | config/flags.yaml | Rising promoter pledge | `rising('promoter_pledge', 2) or m('promoter_pledge') > 0.25` |
| A03 | capital_allocation | medium | ALL | config/flags.yaml | Promoters selling down | `m('promoter_holding_change_3y') < -0.03` |
| A04 | capital_allocation | medium | NF | config/flags.yaml | Dividends funded by debt | `all_last('dividend_to_fcf', 3, '>', 1) and chg('net_debt', 3) > 0` |
| A05 | capital_allocation | medium | NF | config/flags.yaml | Acquisition spend followed by falling ROIC | `m('acquisition_roic_delta_3y') < -0.03` |
| A06 | capital_allocation | high | BL | config/flags.yaml | Lender growing beyond its internal capital; keeps loan_growth, deposit_growth, aum_growth, revenue_cagr_3y, revenue_cagr_5y, revenue_cagr_10y off the strengths list | `m('growth_minus_icg') > 0.15` |
| A07 | capital_allocation | medium | NF | config/flags.yaml | Heavy reinvestment at sub-WACC returns | `m('reinvestment_rate') > 0.5 and m('incremental_roic_3y') < wacc` |
| V01 | valuation | medium | NF | config/flags.yaml | Priced for acceleration | `m('implied_minus_delivered_growth') > 0.05` |
| V02 | valuation | low | NF | config/flags.yaml | Rich versus its own history | `m('pe_percentile_10y') > 0.9 and m('ev_ebitda_percentile_10y') > 0.9` |
| V03 | valuation | medium | ALL (not real_estate) | config/flags.yaml | P/B well above what returns justify | `m('pb_to_justified_pb') > 1.5 and first_of(m('implied_minus_delivered_growth'), 1.0) > 0` |
| V04 | valuation | low | NF | config/flags.yaml | EV/IC rich relative to ROIC/WACC | `m('ev_ic_to_roic_wacc') > 1.5 and first_of(m('implied_minus_delivered_growth'), 1.0) > 0` |
| V05 | valuation | low | FIN | config/flags.yaml | Financial rich versus own history | `m('pe_percentile_10y') > 0.9 and m('pb_percentile_10y') > 0.9` |
| V06 | valuation | medium | FIN | config/flags.yaml | P/B implies faster growth than delivered (financials) | `m('implied_pb_growth_minus_delivered') > 0.05` |
| AU01 | capital_efficiency | medium | auto | config/sectors/auto.yaml | Volumes falling during a capex wave | `m('volume_growth_units') < 0 and m('capex_cycle') > 1.2` |
| AU02 | growth | medium | auto | config/sectors/auto.yaml | Realisation falling two years running | `all_last('realisation_growth', 2, '<', 0)` |
| BK01 | cash_quality | high | BL | config/sectors/bank.yaml | Gross NPAs rising and elevated | `rising('gnpa_ratio', 2) and m('gnpa_ratio') > 0.03` |
| BK02 | cash_quality | medium | BANK | config/sectors/bank.yaml | Thin provision cover | `m('pcr') < 0.60 or (falling('pcr', 2) and chg('pcr', 2) < -0.05)` |
| BK03 | balance_sheet | high | BL | config/sectors/bank.yaml | Capital near the regulatory floor | `m('crar') < 0.13` |
| BK04 | cash_quality | medium | BANK | config/sectors/bank.yaml | Credit costs eating the margin | `m('credit_cost') > 0.02` |
| BK05 | balance_sheet | high | BL | config/sectors/bank.yaml | Fast loan growth while capital falls | `m('loan_growth') > 0.25 and chg('crar', 1) < 0` |
| BK06 | balance_sheet | medium | BANK | config/sectors/bank.yaml | Low-cost deposits slipping | `chg('casa_ratio', 2) < -0.03` |
| BK07 | balance_sheet | medium | BANK | config/sectors/bank.yaml | Lending more than the deposit base supports | `m('cd_ratio') > 0.90` |
| BK08 | cash_quality | medium | BL | config/sectors/bank.yaml | Provisions consume most of operating profit | `m('provisions_to_ppop') > 0.50` |
| BK09 | cash_quality | high | BL | config/sectors/bank.yaml | Regulator found unreported bad loans (NPA divergence); keeps gnpa_ratio, nnpa_ratio, credit_cost, pcr, provisions_to_ppop, slippage_ratio, roa, roe, pat_cagr_3y, pat_cagr_5y, pat_cagr_10y, eps_cagr_3y, eps_cagr_5y, eps_cagr_10y off the strengths list | `m('npa_divergence_share') > 0.15` |
| CG01 | growth | medium | capital_goods_defence | config/sectors/capital_goods_defence.yaml | Orders not replacing revenue | `all_last('book_to_bill_orders', 2, '<', 1.0)` |
| CG02 | growth | medium | capital_goods_defence | config/sectors/capital_goods_defence.yaml | Thin order book | `m('order_book_to_revenue') < 2.0` |
| CG03 | capital_efficiency | low | capital_goods_defence | config/sectors/capital_goods_defence.yaml | Customer advances falling | `pchg('kpi:customer_advances_cr', 1) < -0.20` |
| CY01 | balance_sheet | high | metals, cement, chemicals | config/sectors/_cyclical.yaml | Leverage at the cycle trough | `m('leverage_at_trough') > 4` |
| CY02 | capital_allocation | medium | metals, cement, chemicals | config/sectors/_cyclical.yaml | Expanding at the top of the cycle | `m('peak_cycle_capex') > 2.0` |
| CY03 | capital_efficiency | medium | metals, cement, chemicals | config/sectors/_cyclical.yaml | Plants running below 70% | `m('capacity_utilisation') < 0.70` |
| CY04 | margins | medium | metals, cement, chemicals | config/sectors/_cyclical.yaml | Unit margins far below the cycle average | `m('ebitda_per_tonne_vs_avg') < -0.30` |
| FM01 | growth | medium | fmcg, consumer_manufacturing | config/sectors/fmcg.yaml | Price-led growth with falling volumes | `m('volume_growth') < 0 and m('price_mix_growth') > 0.08` |
| FM02 | margins | medium | fmcg, consumer_manufacturing | config/sectors/fmcg.yaml | Margin gain from cutting A&P | `chg('ad_spend_pct', 1) < -0.01 and chg('ebitda_margin', 1) > 0` |
| FM03 | capital_efficiency | low | fmcg | config/sectors/fmcg.yaml | Working capital turned positive | `m('nwc_days') > 0 and m('nwc_days', 1) <= 0` |
| FM04 | margins | medium | fmcg, consumer_manufacturing | config/sectors/fmcg.yaml | Gross margin down while commodities fell | `m('commodity_change_1y') < -0.05 and m('gross_margin_change_1y') < -0.01` |
| HC01 | balance_sheet | medium | holdco | config/sectors/holdco.yaml | Parent leverage rising | `chg('standalone_debt_to_equity', 1) > 0.2` |
| HC02 | balance_sheet | high | holdco | config/sectors/holdco.yaml | Large guarantees to group companies | `m('contingent_to_networth') > 0.50` |
| HC03 | returns | low | holdco | config/sectors/holdco.yaml | Subsidiaries diluting returns | `m('conso_minus_standalone_roe') < -0.05` |
| IN01 | balance_sheet | high | INS | config/sectors/insurance.yaml | Solvency cushion thinning; keeps solvency_ratio off the strengths list | `m('solvency_ratio') < 1.70 or chg('solvency_ratio', 1) < -0.15` |
| IN02 | cash_quality | medium | INS | config/sectors/insurance.yaml | 13th-month persistency slipping | `chg('persistency_13m', 2) < -0.03` |
| IN03 | margins | medium | INS | config/sectors/insurance.yaml | VNB margin compressing; keeps vnb_margin off the strengths list | `chg('vnb_margin', 1) < -0.01 or chg('vnb_margin', 2) < -0.02` |
| IN04 | valuation | low | INS | config/sectors/insurance.yaml | Rich P/EV with slow VNB growth | `m('p_ev') > 3.0 and m('vnb_growth') < 0.10` |
| IN05 | margins | medium | INS | config/sectors/insurance.yaml | Underwriting loss (general insurance) | `m('combined_ratio') > 1.0` |
| IT01 | capital_efficiency | medium | it_services | config/sectors/it_services.yaml | Attrition high or rising | `m('attrition') > 0.20 or (rising('attrition', 2) and m('attrition') > 0.12)` |
| IT02 | capital_efficiency | medium | it_services | config/sectors/it_services.yaml | Utilisation slipping | `m('utilisation') < 0.80 or chg('utilisation', 1) < -0.03` |
| IT03 | growth | medium | it_services | config/sectors/it_services.yaml | Weak constant-currency growth | `m('cc_growth') < 0.03` |
| IT04 | capital_efficiency | medium | it_services | config/sectors/it_services.yaml | Unbilled and receivable days rising | `rising('dso_incl_unbilled', 2) and chg('dso_incl_unbilled', 2) > 5` |
| IT05 | growth | medium | it_services | config/sectors/it_services.yaml | Deal wins falling | `m('deal_tcv_growth') < -0.10` |
| NB01 | balance_sheet | high | NBFC | config/sectors/nbfc.yaml | AUM outgrowing equity | `all_last('aum_vs_equity_growth', 2, '>', 0.15)` |
| NB02 | cash_quality | medium | NBFC | config/sectors/nbfc.yaml | Stage-2 book rising | `rising('stage2_ratio', 2)` |
| NB03 | balance_sheet | medium | NBFC | config/sectors/nbfc.yaml | Commercial-paper dependence | `m('cp_share') > 0.10` |
| NB04 | balance_sheet | high | NBFC | config/sectors/nbfc.yaml | Negative one-year ALM gap | `m('alm_gap_1y') < 0` |
| NB05 | margins | medium | NBFC | config/sectors/nbfc.yaml | Spread compressing | `chg('spread', 2) < -0.01` |
| NB06 | cash_quality | medium | NBFC | config/sectors/nbfc.yaml | Credit costs eating the spread | `m('credit_cost_aum') > 0.03` |
| PH01 | capital_allocation | medium | pharma | config/sectors/pharma.yaml | R&D cut | `chg('rd_pct', 1) < -0.01` |
| PH02 | growth | medium | pharma | config/sectors/pharma.yaml | US business shrinking with a thinning pipeline | `all_last('us_growth', 2, '<', 0) and chg('anda_pipeline', 2) < 0` |
| PH03 | cash_quality | high | pharma | config/sectors/pharma.yaml | Plants under FDA action | `m('kpi:fda_oai_count') > 0` |
| RE01 | cash_quality | high | real_estate | config/sectors/real_estate.yaml | Bookings not converting to cash | `m('collections_to_presales_3y') < 0.70` |
| RE02 | capital_efficiency | medium | real_estate | config/sectors/real_estate.yaml | Inventory piling up | `m('inventory_months') > 24 and rising('inventory_months', 1)` |
| RE03 | cash_quality | medium | real_estate | config/sectors/real_estate.yaml | Growth consuming cash | `m('cfo') < 0 and m('presales_growth') > 0` |
| RE04 | balance_sheet | high | real_estate | config/sectors/real_estate.yaml | Debt rising while bookings fall | `chg('net_debt', 1) > 0 and m('presales_growth') < 0` |
| RT01 | growth | medium | retail | config/sectors/retail.yaml | Same-store growth below inflation | `all_last('sssg', 2, '<', inflation_target)` |
| RT02 | capital_efficiency | medium | retail | config/sectors/retail.yaml | Productivity falling while expansion accelerates | `chg('revenue_per_sqft', 1) < 0 and chg('store_growth', 1) > 0` |
| RT03 | margins | medium | retail | config/sectors/retail.yaml | Lease-adjusted margin down two years | `falling('ebitda_margin_pre_ind_as116', 2)` |
| TC01 | growth | medium | telecom | config/sectors/telecom.yaml | ARPU falling | `m('arpu_growth') < 0` |
| TC02 | balance_sheet | high | telecom | config/sectors/telecom.yaml | Leverage high including leases and spectrum | `m('net_debt_to_ebitda') > 3.5` |
| TC03 | capital_efficiency | low | telecom | config/sectors/telecom.yaml | Capex intensity very high | `m('capex_to_sales') > 0.30` |
| UT01 | returns | medium | utilities | config/sectors/utilities.yaml | Regulated return leaking | `all_last('regulated_roe_gap', 2, '<', -0.03)` |
| UT02 | capital_efficiency | medium | utilities | config/sectors/utilities.yaml | Discoms paying slowly | `m('discom_receivable_days') > 90` |
| UT03 | balance_sheet | medium | utilities | config/sectors/utilities.yaml | Leverage above the tariff norm | `m('de_vs_normative') > 1.0` |
