# Red-flag rules

Generated from `config/flags.yaml` by `python -m engine rules --markdown`.

| id | pillar | severity | applies | name | condition |
|---|---|---|---|---|---|
| G01 | growth | medium | ALL | Profit growth far ahead of revenue growth | `m('pat_cagr_3y') - m('revenue_cagr_3y') > 0.15` |
| G02 | growth | medium | ALL | Per-share growth lagging profit growth (dilution) | `m('pat_cagr_5y') - m('eps_cagr_5y') > 0.03` |
| G03 | growth | low | NF | Fast growth funded mostly outside own capex | `m('organic_capital_share_3y') < 0.5 and m('revenue_cagr_3y') > 0.15` |
| G04 | growth | low | ALL | Erratic revenue growth | `m('revenue_growth_volatility') > 1.5` |
| G05 | growth | medium | ALL | Quarterly growth decelerating | `m('q_revenue_yoy_trend') < -0.01 and m('q_revenue_yoy') < 0.05` |
| G06 | growth | medium | ALL | Revenue shrinking over 3 years | `m('revenue_cagr_3y') < 0` |
| M01 | margins | medium | NF | EBITDA margin down three years running | `falling('ebitda_margin', 3) and chg('ebitda_margin', 3) < -0.02` |
| M02 | margins | medium | NF | Profits leaning on other income | `m('other_income_to_pbt') > 0.25` |
| M03 | margins | medium | NF | Materials cost creeping up | `chg('materials_pct', 3) > 0.03` |
| M04 | margins | medium | NF | Employee cost creeping up | `chg('employee_pct', 3) > 0.03` |
| M05 | margins | low | NF | Other operating costs creeping up | `chg('other_expenses_pct', 3) > 0.03` |
| M06 | margins | medium | NF | Operating leverage working in reverse | `m('dol') > 3 and pchg('revenue', 1) < 0` |
| M07 | margins | low | NF | Volatile margins | `m('ebitda_margin_sd_10y') > 0.05` |
| M08 | margins | medium | BL | Net interest margin compressing | `chg('nii_to_assets', 2) < -0.005` |
| C01 | capital_efficiency | medium | NF | Receivable days up three years running | `rising('dso', 3) and chg('dso', 3) > 5` |
| C02 | capital_efficiency | medium | NF | Inventory days up three years running | `rising('dio', 3) and chg('dio', 3) > 5` |
| C03 | capital_efficiency | medium | NF | Capital stuck in work-in-progress | `all_last('cwip_to_net_block', 2, '>', 0.30)` |
| C04 | capital_efficiency | low | NF | Asset turnover slump | `pchg('asset_turnover', 3) < -0.20` |
| C05 | capital_efficiency | low | NF | Under-investment | `all_last('capex_to_depreciation', 3, '<', 0.8)` |
| C06 | capital_efficiency | medium | NF | Heavy capex with falling fixed-asset turnover | `m('capex_to_depreciation') > 3 and falling('fixed_asset_turnover', 2)` |
| C07 | capital_efficiency | medium | NF | Working capital bloating | `chg('nwc_days', 3) > 30` |
| R01 | returns | high | NF | ROIC below WACC for three years | `all_last('roic_wacc_spread', 3, '<', 0)` |
| R02 | returns | high | ALL | ROE rising on leverage while margins fall | `chg('roe', 3) > 0 and chg('equity_multiplier', 3) > 0 and chg('pat_margin', 3) < 0` |
| R03 | returns | medium | NF | New capital earning below its cost | `m('incremental_roic_3y') < wacc and pchg('invested_capital', 3) > 0.30` |
| R04 | returns | medium | ALL | ROE down three years running | `falling('roe', 3) and chg('roe', 3) < -0.05` |
| R05 | returns | high | FIN | ROE below cost of equity (financials) | `all_last('roe_ke_spread', 2, '<', 0)` |
| Q01 | cash_quality | high | NF | Profits not converting to cash (5y) | `sum_last('cfo', 5) < 0.6 * sum_last('pat_core', 5) and sum_last('pat_core', 5) > 0` |
| Q02 | cash_quality | medium | NF | Negative free cash flow despite profits | `all_last('fcf', 3, '<', 0) and all_last('pat_core', 3, '>', 0)` |
| Q03 | cash_quality | medium | NF | High accruals | `m('accruals_ratio') > 0.10` |
| Q04 | cash_quality | medium | NF | Receivables outpacing revenue | `all_last('receivables_vs_revenue_growth', 2, '>', 0.10)` |
| Q05 | cash_quality | medium | NF | Recurring 'exceptional' items | `m('exceptional_frequency_5y') >= 3` |
| Q06 | cash_quality | high | NF | Beneish M-score in manipulator zone | `m('beneish_m_score') > -1.78` |
| Q07 | cash_quality | medium | NF | Weak cash conversion of EBITDA | `all_last('cfo_to_ebitda', 2, '<', 0.5)` |
| B01 | balance_sheet | high | NF | Debt growing faster than EBITDA for three years | `all_last('debt_vs_ebitda_growth', 3, '>', 0)` |
| B02 | balance_sheet | high | NF | High leverage | `m('net_debt_to_ebitda') > 4` |
| B03 | balance_sheet | high | NF | Weak interest cover | `m('interest_cover') < 2` |
| B04 | balance_sheet | medium | NF | Liquidity squeeze | `m('current_ratio_proxy') < 1.0 and m('cash_to_st_borrowings') < 0.2` |
| B05 | balance_sheet | high | NF | Altman Z'' in distress zone | `m('altman_z_india') < 4.35` |
| B06 | balance_sheet | high | BL | Capital ratio falling while balance sheet balloons | `chg('equity_to_assets', 1) < -0.01 and pchg('total_assets', 1) > 0.25` |
| B07 | balance_sheet | medium | BL | Funding outgrowing equity | `m('funding_vs_equity_growth') > 0.20` |
| B08 | balance_sheet | medium | NBFC | NBFC leverage high | `m('borrowings_to_equity') > 6` |
| A01 | capital_allocation | medium | ALL | Dilution while ROE falls | `m('share_count_change') > 0.02 and chg('roe', 1) < 0` |
| A02 | capital_allocation | high | ALL | Rising promoter pledge | `rising('promoter_pledge', 2) or m('promoter_pledge') > 0.25` |
| A03 | capital_allocation | medium | ALL | Promoters selling down | `m('promoter_holding_change_3y') < -0.03` |
| A04 | capital_allocation | medium | NF | Dividends funded by debt | `all_last('dividend_to_fcf', 3, '>', 1) and chg('net_debt', 3) > 0` |
| A05 | capital_allocation | medium | NF | Acquisition spend followed by falling ROIC | `m('acquisition_roic_delta_3y') < -0.03` |
| A06 | capital_allocation | high | BL | Lender growing beyond its internal capital | `m('growth_minus_icg') > 0.15` |
| A07 | capital_allocation | medium | NF | Heavy reinvestment at sub-WACC returns | `m('reinvestment_rate') > 0.5 and m('incremental_roic_3y') < wacc` |
| V01 | valuation | medium | NF | Priced for acceleration | `m('implied_minus_delivered_growth') > 0.05` |
| V02 | valuation | low | NF | Rich versus its own history | `m('pe_percentile_10y') > 0.9 and m('ev_ebitda_percentile_10y') > 0.9` |
| V03 | valuation | medium | ALL | P/B well above what returns justify | `m('pb_to_justified_pb') > 1.5` |
| V04 | valuation | low | NF | EV/IC rich relative to ROIC/WACC | `m('ev_ic_to_roic_wacc') > 1.5` |
| V05 | valuation | low | FIN | Financial rich versus own history | `m('pe_percentile_10y') > 0.9 and m('pb_percentile_10y') > 0.9` |
| V06 | valuation | medium | FIN | P/B implies faster growth than delivered (financials) | `m('implied_pb_growth_minus_delivered') > 0.05` |
