"""Hand-computed checks for EVERY metric in the registry, on synthetic companies (tests/synthetic.py).

Expected values are written as plain arithmetic on the literal fixture numbers. No engine helper is used to
compute an expectation. A meta-test fails if a registered metric has no expectation here.
"""
from __future__ import annotations

import math
import statistics as st

import pytest

from synthetic import BK, CO, TEST_BETA, TEST_ERP, TEST_RF, derive

T = 0.25168          # statutory tax rate in config/market.yaml (22% x 1.10 x 1.04)
KE = TEST_RF + TEST_BETA * TEST_ERP   # 0.13
AAA_SPREAD = 0.0040  # interest cover >= 8.5x -> Aaa/AAA in the synthetic-rating table (all synthetic years qualify)
REL = 1e-9


def avg(x, i):
    return (x[i] + x[i - 1]) / 2


def cagr(x, i, n):
    return (x[i] / x[i - n]) ** (1 / n) - 1


def ols(y):
    xs = list(range(len(y)))
    xm, ym = st.mean(xs), st.mean(y)
    return sum((a - xm) * (b - ym) for a, b in zip(xs, y)) / sum((a - xm) ** 2 for a in xs)


# ======================================================================================== SYNTHCO
D = derive(CO)
N = 10
rev, rm, ci, pf, om = CO["sales"], CO["raw_material"], CO["change_in_inventory"], CO["power_fuel"], CO["other_mfr"]
emp, sa, oe, oi, dep, intr = CO["employee"], CO["selling_admin"], CO["other_exp"], CO["other_income"], CO["depreciation"], CO["interest"]
res, bor, ol, nb, cwip, inv = CO["reserves"], CO["borrowings"], CO["other_liabilities"], CO["net_block"], CO["cwip"], CO["investments"]
rec, invn, cash, cfo, cfi = CO["receivables"], CO["inventory"], CO["cash"], CO["cfo"], CO["cfi"]
sh, price, div = CO["shares_cr"], CO["price"], CO["dividend"]

mat = [rm[i] - ci[i] for i in range(N)]
cogs = [mat[i] + pf[i] + om[i] for i in range(N)]
oopex = [pf[i] + om[i] + sa[i] + oe[i] for i in range(N)]
ebitda = [rev[i] - (mat[i] + emp[i] + oopex[i]) for i in range(N)]
pbt = D["pbt"]
tax = D["tax"]
pat = D["net_profit"]                       # reported owners' PAT = PBT - tax - 10
exc = [0, 0, 0, 0, 0, 100, 0, 0, 0, 0]      # FY22 other income 132 = 2% x 1600 + 100
pbt_c = [pbt[i] - exc[i] for i in range(N)]
tax_c = [tax[i] - exc[i] * T for i in range(N)]
pat_c = [pat[i] - exc[i] + exc[i] * T for i in range(N)]
ebit = [pbt_c[i] + intr[i] for i in range(N)]
opebit = [ebitda[i] - dep[i] for i in range(N)]
sc = [s * 10 for s in sh]
eq = [sc[i] + res[i] for i in range(N)]
ta = [sc[i] + res[i] + bor[i] + ol[i] for i in range(N)]
oa = [ta[i] - nb[i] - cwip[i] - inv[i] for i in range(N)]
oar = [oa[i] - rec[i] - invn[i] - cash[i] for i in range(N)]
ic = [eq[i] + bor[i] - cash[i] - inv[i] for i in range(N)]
nwc = [oa[i] - cash[i] - ol[i] for i in range(N)]
nd = [bor[i] - cash[i] for i in range(N)]
capex = [None] + [(nb[i] - nb[i - 1]) + (cwip[i] - cwip[i - 1]) + dep[i] for i in range(1, N)]
fcf = [None] + [cfo[i] - capex[i] for i in range(1, N)]
mcap = [price[i] * sh[i] for i in range(N)]
ev = [mcap[i] + bor[i] - cash[i] - inv[i] for i in range(N)]
eps = [pat_c[i] / sh[i] for i in range(N)]
t_n = [tax_c[i] / pbt_c[i] for i in range(N)]
nopat = [opebit[i] * (1 - t_n[i]) for i in range(N)]
roic = [None] + [nopat[i] / avg(ic, i) for i in range(1, N)]
roe = [None] + [pat_c[i] / avg(eq, i) for i in range(1, N)]
payout = [div[i] / pat_c[i] for i in range(N)]
KD_POST = (TEST_RF + AAA_SPREAD) * (1 - T)
wd = [bor[i] / (bor[i] + mcap[i]) for i in range(N)]
wacc = [(1 - wd[i]) * KE + wd[i] * KD_POST for i in range(N)]
MCAP_NOW = CO["current_price"] * sh[-1]                  # 220 x 10.0 = 2200
WD_NOW = bor[9] / (bor[9] + MCAP_NOW)
WACC_NOW = (1 - WD_NOW) * KE + WD_NOW * KD_POST
EV_NOW = MCAP_NOW + bor[9] - cash[9] - inv[9]            # 2200 + 400 - 105 - 190 = 2305
# quarters
qs, qx, qoi, qd, qi = CO["q_sales"], CO["q_expenses"], CO["q_other_income"], CO["q_depreciation"], CO["q_interest"]
qop = [qs[k] - qx[k] for k in range(10)]
qpbt = [qop[k] + qoi[k] - qd[k] - qi[k] for k in range(10)]
qnp = [0.75 * qpbt[k] - 2 for k in range(10)]
TTM_PAT, TTM_EBITDA, TTM_REV = sum(qnp[6:10]), sum(qop[6:10]), sum(qs[6:10])
# manual KPIs (tests/synthetic.py CO_MANUAL)
PAYABLES26 = 200.0


def pct_rank(hist, cur):
    return (sum(1 for h in hist if h < cur) + 0.5 * sum(1 for h in hist if h == cur)) / len(hist)


i = 9  # FY26
ca9, ca8 = rec[9] + invn[9] + cash[9], rec[8] + invn[8] + cash[8]
gm = [1 - cogs[k] / rev[k] for k in range(N)]
dsri = (rec[9] / rev[9]) / (rec[8] / rev[8])
gmi = gm[8] / gm[9]
aqi = (1 - (ca9 + nb[9]) / ta[9]) / (1 - (ca8 + nb[8]) / ta[8])
sgi = rev[9] / rev[8]
depi = (dep[8] / (dep[8] + nb[8])) / (dep[9] / (dep[9] + nb[9]))
sgai = ((sa[9] + oe[9]) / rev[9]) / ((sa[8] + oe[8]) / rev[8])
lvgi = ((bor[9] + ol[9]) / ta[9]) / ((bor[8] + ol[8]) / ta[8])
tata = (pat[9] - cfo[9]) / ta[9]
x1, x2, x3, x4 = (oa[9] - ol[9]) / ta[9], res[9] / ta[9], ebit[9] / ta[9], eq[9] / (bor[9] + ol[9])
ronic = st.mean(roic[7:10])
f0 = nopat[9] * (1 - 0.06 / ronic)
roe3, payout3 = st.mean(roe[7:10]), st.mean(payout[7:10])
g_j = min(roe3 * (1 - payout3), 0.06)
JPB = (roe3 - g_j) / (KE - g_j)
PB_NOW = MCAP_NOW / eq[9]
ncx3 = sum(-cfi[k] - capex[k] for k in (7, 8, 9)) / ic[6]
# acquisition-like spend: non-capex investing net of the change in (cash + investments) the net cash flow does not explain
ncf = [cfo[k] + cfi[k] + CO["cff"][k] for k in range(N)]
acq = [None] + [max(0.0, (-cfi[k] - capex[k]) - ((cash[k] + inv[k]) - (cash[k - 1] + inv[k - 1]) - ncf[k])) for k in range(1, N)]
acq3 = sum(acq[k] for k in (7, 8, 9)) / ic[6]          # (40 + 55 + 70) / IC_FY23 = 15.9%
# justified EV/IC (value driver): (ROIC3 - g) / (WACC - g), g = min(ROIC3 x avg reinvestment (clipped 0-1), 6%)
reinv = [None] + [(capex[k] - dep[k] + (nwc[k] - nwc[k - 1])) / nopat[k] for k in range(1, N)]
g_ev = min(ronic * st.mean(max(0.0, min(1.0, r)) for r in reinv[7:10]), 0.06)
growth = [rev[k] / rev[k - 1] - 1 for k in range(1, N)]
pgrowth = [pat_c[k] / pat_c[k - 1] - 1 for k in range(1, N)]
yoy = [qs[k] / qs[k - 4] - 1 for k in range(6, 10)]
ebm = [ebitda[k] / rev[k] for k in range(N)]
ROIC_EXPECTED_FY26 = nopat[9] / avg(ic, 9)
CO_FY = [f"FY{17 + j}" for j in range(10)]

CO_EXPECTED = {
    # ---- root
    "economic_profit": nopat[9] - wacc[9] * avg(ic, 9),
    # ---- growth
    "revenue_cagr_3y": cagr(rev, 9, 3), "revenue_cagr_5y": cagr(rev, 9, 5), "revenue_cagr_10y": (rev[9] / rev[0]) ** (1 / 9) - 1,
    "ebitda_cagr_3y": cagr(ebitda, 9, 3), "ebitda_cagr_5y": cagr(ebitda, 9, 5), "ebitda_cagr_10y": (ebitda[9] / ebitda[0]) ** (1 / 9) - 1,
    "pat_cagr_3y": cagr(pat_c, 9, 3), "pat_cagr_5y": cagr(pat_c, 9, 5), "pat_cagr_10y": (pat_c[9] / pat_c[0]) ** (1 / 9) - 1,
    "eps_cagr_3y": cagr(eps, 9, 3), "eps_cagr_5y": cagr(eps, 9, 5), "eps_cagr_10y": (eps[9] / eps[0]) ** (1 / 9) - 1,
    "revenue_growth_volatility": st.stdev(growth) / abs(st.mean(growth)),
    "pat_growth_volatility": st.stdev(pgrowth) / abs(st.mean(pgrowth)),
    "organic_capital_share_3y": sum(capex[7:10]) / (sum(capex[7:10]) + 3 * 10),   # investments +10 each year
    "q_revenue_yoy": 580 / 520 - 1,
    "q_pat_yoy": qnp[9] / qnp[5] - 1,
    "q_revenue_yoy_trend": ols(yoy),
    # ---- margins
    "gross_margin": 1 - cogs[9] / rev[9], "ebitda_margin": ebitda[9] / rev[9], "ebit_margin": ebit[9] / rev[9],
    "pat_margin": pat_c[9] / rev[9], "materials_pct": mat[9] / rev[9], "employee_pct": emp[9] / rev[9],
    "other_expenses_pct": oopex[9] / rev[9],
    "dol": (ebit[9] / ebit[8] - 1) / (rev[9] / rev[8] - 1),
    "ebitda_margin_sd_10y": st.stdev(ebm),
    "other_income_to_pbt": oi[9] / pbt[9],
    "q_ebitda_margin_yoy_change": qop[9] / qs[9] - qop[5] / qs[5],
    "dep_to_sales": dep[9] / rev[9], "oi_core_to_sales": (oi[9] - exc[9]) / rev[9], "operating_margin": opebit[9] / rev[9],
    # ---- capital efficiency
    "asset_turnover": rev[9] / avg(ta, 9), "fixed_asset_turnover": rev[9] / avg(nb, 9), "ic_turnover": rev[9] / avg(ic, 9),
    "dso": rec[9] / rev[9] * 365, "dio": invn[9] / cogs[9] * 365, "dpo": PAYABLES26 / cogs[9] * 365,
    "cash_conversion_cycle": rec[9] / rev[9] * 365 + invn[9] / cogs[9] * 365 - PAYABLES26 / cogs[9] * 365,
    "operating_cycle": rec[9] / rev[9] * 365 + invn[9] / cogs[9] * 365,
    "nwc_days": nwc[9] / rev[9] * 365,
    "capex_to_sales": capex[9] / rev[9], "capex_to_depreciation": capex[9] / dep[9], "cwip_to_net_block": cwip[9] / nb[9],
    "nb_to_sales": avg(nb, 9) / rev[9], "cwip_to_sales": avg(cwip, 9) / rev[9], "investments_to_sales": avg(inv, 9) / rev[9],
    "receivables_to_sales": avg(rec, 9) / rev[9], "inventory_to_sales": avg(invn, 9) / rev[9], "cash_to_sales": avg(cash, 9) / rev[9],
    "other_assets_rest_to_sales": avg(oar, 9) / rev[9], "other_liabilities_to_sales": avg(ol, 9) / rev[9],
    # ---- returns
    "roe": pat_c[9] / avg(eq, 9), "roa": pat_c[9] / avg(ta, 9), "roce": ebit[9] / (avg(eq, 9) + avg(bor, 9)),
    "roic": ROIC_EXPECTED_FY26, "roic_wacc_spread": ROIC_EXPECTED_FY26 - wacc[9],
    "incremental_roic_3y": (nopat[9] - nopat[6]) / (avg(ic, 9) - avg(ic, 6)),
    "attributable_factor": pat_c[9] / (pbt_c[9] - tax_c[9]), "tax_burden": (pbt_c[9] - tax_c[9]) / pbt_c[9],
    "interest_burden": pbt_c[9] / ebit[9], "equity_multiplier": avg(ta, 9) / avg(eq, 9),
    "debt_to_equity_avg": avg(bor, 9) / avg(eq, 9), "other_liab_to_equity_avg": avg(ol, 9) / avg(eq, 9),
    "nopat_tax_factor": 1 - t_n[9], "nopat_margin": nopat[9] / rev[9],
    # ---- cash and earnings quality
    "cfo_to_ebitda": cfo[9] / ebitda[9], "fcf_to_pat": fcf[9] / pat_c[9],
    "fcf_to_pat_5y": sum(fcf[5:10]) / sum(pat_c[5:10]), "cfo_to_pat_5y": sum(cfo[5:10]) / sum(pat_c[5:10]),
    "accruals_ratio": (pat[9] - cfo[9]) / avg(ta, 9),
    "receivables_vs_revenue_growth": (rec[9] / rec[8] - 1) - (rev[9] / rev[8] - 1),
    "exceptional_frequency_5y": 1.0, "exceptional_size_5y": 100 / sum(abs(p) for p in pbt[5:10]),
    "beneish_dsri": dsri, "beneish_gmi": gmi, "beneish_aqi": aqi, "beneish_sgi": sgi, "beneish_depi": depi,
    "beneish_sgai": sgai, "beneish_lvgi": lvgi, "beneish_tata": tata,
    "beneish_m_score": -4.84 + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi,
    # ---- balance sheet
    "net_debt_to_ebitda": nd[9] / ebitda[9], "net_debt_to_equity": nd[9] / eq[9], "interest_cover": ebit[9] / intr[9],
    "current_ratio_proxy": (oa[9] + inv[9]) / ol[9], "cash_to_st_borrowings": (cash[9] + inv[9]) / bor[9],
    "debt_vs_ebitda_growth": (bor[9] / bor[8] - 1) - (ebitda[9] / ebitda[8] - 1),
    "altman_x1": x1, "altman_x2": x2, "altman_x3": x3, "altman_x4": x4,
    "altman_z_india": 3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4,
    # ---- capital allocation
    "reinvestment_rate": (capex[9] - dep[9] + (nwc[9] - nwc[8])) / nopat[9],
    "payout_ratio": div[9] / pat_c[9], "share_count_change": 10.0 / 10.2 - 1,
    "buyback_estimate": (10.2 - 10.0) * (210 + 200) / 2,
    "shareholder_yield": (div[9] + (10.2 - 10.0) * (210 + 200) / 2) / mcap[9],
    "dividend_to_fcf": div[9] / fcf[9],
    "non_capex_investing_3y": ncx3, "acquisition_spend_3y": acq3,
    "acquisition_roic_delta_3y": roic[9] - roic[6],      # acq3 > 10% so the metric is defined
    "promoter_holding": 0.55, "promoter_holding_change_3y": 0.55 - 0.60, "promoter_pledge": 0.12,
    # ---- valuation
    "pe": MCAP_NOW / TTM_PAT,
    "pe_percentile_10y": pct_rank([mcap[k] / pat_c[k] for k in range(N)], MCAP_NOW / TTM_PAT),
    "pb": PB_NOW, "pb_percentile_10y": pct_rank([mcap[k] / eq[k] for k in range(N)], PB_NOW),
    "ev_ebitda": EV_NOW / TTM_EBITDA, "ev_ebitda_percentile_10y": pct_rank([ev[k] / ebitda[k] for k in range(N)], EV_NOW / TTM_EBITDA),
    "ev_sales": EV_NOW / TTM_REV, "ev_sales_percentile_10y": pct_rank([ev[k] / rev[k] for k in range(N)], EV_NOW / TTM_REV),
    "justified_pb": JPB, "pb_to_justified_pb": PB_NOW / JPB,
    "ev_ic": EV_NOW / ic[9], "ev_ic_to_roic_wacc": (EV_NOW / ic[9]) / ((ronic - g_ev) / (WACC_NOW - g_ev)),
    # implied_growth_reverse_dcf / implied_minus_delivered_growth: checked by re-pricing below
}
# a few checks in earlier years (series correctness, exceptional-item adjustment, opening balances)
CO_EXPECTED_SERIES = {
    ("roe", "FY22"): pat_c[5] / avg(eq, 5),
    ("pat_margin", "FY22"): (pat[5] - 100 + 100 * T) / rev[5],
    ("ebit_margin", "FY22"): (pbt[5] - 100 + intr[5]) / rev[5],
    ("other_income_to_pbt", "FY22"): 132 / pbt[5],
    ("dso", "FY25"): rec[8] / rev[8] * 365,
    ("roic", "FY18"): nopat[1] / avg(ic, 1),
    ("revenue_cagr_3y", "FY20"): cagr(rev, 3, 3),
    ("cfo_to_pat_5y", "FY21"): sum(cfo[0:5]) / sum(pat_c[0:5]),
    ("exceptional_frequency_5y", "FY21"): 0.0,
    ("debt_vs_ebitda_growth", "FY18"): (bor[1] / bor[0] - 1) - (ebitda[1] / ebitda[0] - 1),
    ("economic_profit", "FY22"): nopat[5] - wacc[5] * avg(ic, 5),
    ("pe", "FY20"): mcap[3] / pat_c[3],
}

# ======================================================================================== SYNTHBANK
BD = derive(BK)
bn = 6
b_rev, b_int, b_oi, b_dep, b_div = BK["sales"], BK["interest"], BK["other_income"], BK["depreciation"], BK["dividend"]
b_opex = [BK["employee"][k] + BK["selling_admin"][k] + BK["other_exp"][k] for k in range(bn)]
b_pbt, b_tax, b_pat = BD["pbt"], BD["tax"], BD["net_profit"]
b_eq = [50 + BK["reserves"][k] for k in range(bn)]
b_bor, b_ol, b_inv, b_cash, b_nb = BK["borrowings"], BK["other_liabilities"], BK["investments"], BK["cash"], BK["net_block"]
b_ta = [b_eq[k] + b_bor[k] + b_ol[k] for k in range(bn)]
b_oa = [b_ta[k] - b_nb[k] - b_inv[k] for k in range(bn)]
b_nii = [b_rev[k] - b_int[k] for k in range(bn)]
b_roe = [None] + [b_pat[k] / avg(b_eq, k) for k in range(1, bn)]
b_payout = [b_div[k] / b_pat[k] for k in range(bn)]
b_icg = b_roe[5] * (1 - b_payout[5])
B_MCAP_NOW = BK["current_price"] * 5      # 800
B_PB_NOW = B_MCAP_NOW / b_eq[5]
b_roe3 = st.mean(b_roe[3:6])
b_bvps_cagr5 = (b_eq[5] / b_eq[0]) ** (1 / 5) - 1
b_g = min(b_roe3 * (1 - st.mean(b_payout[3:6])), 0.06)
B_JPB = (b_roe3 - b_g) / (KE - b_g)
b_imp = (KE * B_PB_NOW - b_roe3) / (B_PB_NOW - 1)

BK_EXPECTED = {
    "roe": b_roe[5], "roa": b_pat[5] / avg(b_ta, 5), "roe_ke_spread": b_roe[5] - KE,
    "pat_margin": b_pat[5] / b_rev[5], "equity_multiplier": avg(b_ta, 5) / avg(b_eq, 5),
    "interest_to_assets": b_int[5] / avg(b_ta, 5), "other_income_to_assets": b_oi[5] / avg(b_ta, 5),
    "dep_to_assets": b_dep[5] / avg(b_ta, 5), "tax_to_assets": b_tax[5] / avg(b_ta, 5), "minority_to_assets": -5 / avg(b_ta, 5),
    "yield_on_assets": b_rev[5] / avg(b_ta, 5), "opex_to_assets": b_opex[5] / avg(b_ta, 5),
    "internal_capital_generation": b_icg, "equity_to_assets": b_eq[5] / b_ta[5],
    "liquid_assets_ratio": (b_cash[5] + b_inv[5]) / b_ta[5],
    "bvps_cagr_5y": b_bvps_cagr5, "assets_cagr_3y": (b_ta[5] / b_ta[2]) ** (1 / 3) - 1,
    "implied_growth_pb": b_imp, "implied_pb_growth_minus_delivered": b_imp - b_bvps_cagr5,
    "growth_minus_icg": (b_ta[5] / b_ta[4] - 1) - b_icg,
    "funding_vs_equity_growth": (b_bor[5] / b_bor[4] - 1) - (b_eq[5] / b_eq[4] - 1),
    "credit_deposit_proxy": b_oa[5] / b_bor[5],
    "nii_cagr_3y": (b_nii[5] / b_nii[2]) ** (1 / 3) - 1, "nii_to_assets": b_nii[5] / avg(b_ta, 5),
    "cost_of_funds": b_int[5] / avg(b_bor, 5),
    "cost_to_income": (b_opex[5] + b_dep[5]) / (b_nii[5] + b_oi[5]),
    "other_income_share": b_oi[5] / (b_nii[5] + b_oi[5]),
    "pe": B_MCAP_NOW / b_pat[5],                  # no quarters -> last FY PAT
    "pb": B_PB_NOW, "justified_pb": B_JPB, "pb_to_justified_pb": B_PB_NOW / B_JPB,
    "economic_profit": (b_roe[5] - KE) * avg(b_eq, 5),
    "pb_percentile_10y": pct_rank([BK["price"][k] * 5 / b_eq[k] for k in range(bn)], B_PB_NOW),
    "pe_percentile_10y": pct_rank([BK["price"][k] * 5 / b_pat[k] for k in range(bn)], B_MCAP_NOW / b_pat[5]),
    "payout_ratio": b_payout[5], "share_count_change": 0.0, "buyback_estimate": 0.0,
    "shareholder_yield": b_div[5] / (BK["price"][5] * 5),
    "revenue_cagr_10y": (b_rev[5] / b_rev[0]) ** (1 / 5) - 1,     # full span = 5 years for a 6-column export
}
NBFC_EXPECTED = {"borrowings_to_equity": b_bor[5] / b_eq[5]}
INS_EXPECTED = {"benefits_ratio": 0.0, "expense_ratio": b_opex[5] / b_rev[5]}

# Metrics checked by a dedicated test rather than a fixed number.
SPECIAL = {"implied_growth_reverse_dcf", "implied_minus_delivered_growth"}
# Not applicable / no data on the synthetic financials (checked to be NaN).
BK_NAN = {"promoter_holding", "promoter_holding_change_3y", "promoter_pledge", "q_revenue_yoy", "q_pat_yoy", "q_revenue_yoy_trend"}


@pytest.fixture(scope="module")
def computed(project_cfg):
    from engine.analysis import compute

    return {t: compute(t, project_cfg) for t in ("SYNTHCO", "SYNTHBANK", "SYNTHNBFC", "SYNTHINS")}


def _check(metrics, mid, exp, fy=None, ctx=None):
    s = metrics[mid] if mid in metrics else ctx.m(mid)  # switched-off metrics are still computable internally
    got = s.iloc[-1] if fy is None else s[fy]
    assert got == pytest.approx(exp, rel=REL, abs=1e-12), f"{mid} {fy or 'latest'}: got {got}, expected {exp}"


@pytest.mark.parametrize("mid", sorted(CO_EXPECTED))
def test_nonfinancial_metric(computed, mid):
    _check(computed["SYNTHCO"].metrics, mid, CO_EXPECTED[mid])


@pytest.mark.parametrize("key", sorted(CO_EXPECTED_SERIES))
def test_nonfinancial_series(computed, key):
    mid, fy = key
    _check(computed["SYNTHCO"].metrics, mid, CO_EXPECTED_SERIES[key], fy)


@pytest.mark.parametrize("mid", sorted(BK_EXPECTED))
def test_bank_metric(computed, mid):
    _check(computed["SYNTHBANK"].metrics, mid, BK_EXPECTED[mid], ctx=computed["SYNTHBANK"].ctx)


@pytest.mark.parametrize("mid", sorted(NBFC_EXPECTED))
def test_nbfc_metric(computed, mid):
    _check(computed["SYNTHNBFC"].metrics, mid, NBFC_EXPECTED[mid])


@pytest.mark.parametrize("mid", sorted(INS_EXPECTED))
def test_insurance_metric(computed, mid):
    _check(computed["SYNTHINS"].metrics, mid, INS_EXPECTED[mid])


def test_bank_missing_data_is_nan(computed):
    for mid in BK_NAN:
        assert computed["SYNTHBANK"].metrics[mid].isna().all(), mid


def test_reverse_dcf_reprices_ev(computed):
    """Plug the solved growth back into an independently written DCF: it must reproduce today's EV."""
    m = computed["SYNTHCO"].metrics
    g = m["implied_growth_reverse_dcf"].iloc[-1]
    assert not math.isnan(g)
    pv, f = 0.0, f0
    for t in range(1, 11):
        f *= 1 + g
        pv += f / (1 + WACC_NOW) ** t
    pv += f * 1.06 / (WACC_NOW - 0.06) / (1 + WACC_NOW) ** 10
    assert pv == pytest.approx(EV_NOW, rel=1e-8)
    delivered = (nopat[9] / nopat[4]) ** (1 / 5) - 1
    assert m["implied_minus_delivered_growth"].iloc[-1] == pytest.approx(g - delivered, rel=1e-9)


def test_reverse_dcf_closed_form():
    """With g = terminal g the DCF collapses to a Gordon model: EV = F0 (1+gT) / (WACC - gT)."""
    from engine.metrics.valuation import solve_implied_growth

    f0_, w, gT = 100.0, 0.12, 0.06
    ev_ = f0_ * (1 + gT) / (w - gT)
    g, msg = solve_implied_growth(ev_, f0_, w, gT, 10)
    assert msg == "solved" and g == pytest.approx(gT, abs=1e-9)


def test_every_registered_metric_has_a_hand_computed_check():
    """Engine (Python) metrics; sector metrics are covered in tests/test_sector_modules.py."""
    from engine.registry import load_all

    covered = set(CO_EXPECTED) | set(BK_EXPECTED) | set(NBFC_EXPECTED) | set(INS_EXPECTED) | SPECIAL
    engine_ids = {m for m, d in load_all().items() if d.origin == "engine"}
    missing = sorted(engine_ids - covered)
    assert not missing, f"metrics without a hand-computed expectation: {missing}"


def test_wacc_by_hand(computed):
    coc = computed["SYNTHCO"].coc
    assert coc.ke["FY26"] == pytest.approx(KE)
    assert coc.wacc["FY26"] == pytest.approx(wacc[9], rel=REL)
    assert coc.current["wacc"] == pytest.approx(WACC_NOW, rel=REL)
    assert coc.current["rating"] == "Aaa/AAA"


def test_dupont_identities_hold(computed):
    m = computed["SYNTHCO"].metrics
    for fy in ("FY22", "FY26"):
        three = m["pat_margin"][fy] * m["asset_turnover"][fy] * m["equity_multiplier"][fy]
        five = m["attributable_factor"][fy] * m["tax_burden"][fy] * m["interest_burden"][fy] * m["ebit_margin"][fy]
        assert three == pytest.approx(m["roe"][fy], rel=1e-12)
        assert five == pytest.approx(m["pat_margin"][fy], rel=1e-12)
        assert m["nopat_margin"][fy] * m["ic_turnover"][fy] == pytest.approx(m["roic"][fy], rel=1e-12)
