# Manual KPIs (optional)

The Screener export has no trade payables, current/non-current split, capex, shareholding or bank asset-quality
data. Put any of these in `data/manual/<TICKER>_kpis.csv` (long format, one value per row) and the engine uses them.
The file is optional. Without it, the metrics that need these inputs are reported as "not in export".

```
period,kpi,value,unit,source
FY25,trade_payables,1200,Rs cr,Annual report FY25 p.212
Q2FY26,promoter_holding_pct,50.2,%,BSE shareholding pattern
2025-09-30,promoter_pledge_pct,3.1,%,BSE shareholding pattern
```

- **`period`**: one of `FY25`, `Q2FY26` (April-March quarters) or a date. Dates and quarters map to their fiscal year, and the last observation in a fiscal year wins (= year-end value).
- **Percentages**: give them as percent numbers with `unit` = `%` (or a kpi name ending in `_pct`). They are divided by 100.
- **As-of runs** ignore rows after the as-of year.

| kpi | Used for |
|---|---|
| `trade_payables` (Rs cr) | DPO, cash conversion cycle |
| `short_term_borrowings` (Rs cr) | cash / short-term borrowings |
| `capex` (Rs cr) | replaces the balance-sheet capex proxy (FCF, reinvestment) |
| `exceptional_items` (Rs cr, pre-tax, + gain / - loss) | replaces the estimated exceptional item in other income |
| `minority_interest` (Rs cr, balance-sheet NCI) | added back to invested capital for ROIC |
| `promoter_holding_pct`, `promoter_pledge_pct` | promoter holding / pledge metrics and flags A02, A03 |
| `beta` | overrides the levered beta |
| anything else (e.g. `gnpa_pct`, `casa_pct`, `car_pct`) | carried in the data but not scored |
