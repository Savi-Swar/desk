
## Desk gate verdict — 2026-08-30 (2-week maker gate, evaluated late: the Aug-17 scheduled run never fired and workflows were down Aug 17-27)

Metric: net_live from collected/maker_pnl_real.csv — markout REPRICED to a 0.1c
near-mid quote (fill-at-touch spread stripped) + realized maker rebate at 20%
of taker fees, both capped at a 100-share resting quote. The discredited
ledgers (fill_model, maker_net*) played no part.

Sample: 12 recorded days (Aug 9-17, Aug 28-30; 10-day CI outage between),
25,494 maker fills, effective sample 2,318 bets.

  cumulative net_live : +815.29 paper
    = rebate +1,263.89  +  repriced markout -448.59
  daily mean          : +67.94  (sd 120.62)
  daily-mean t-stat   : +1.95  (8/12 days individually significant)
  positive days       : 11/12

VERDICT: INCONCLUSIVE

The edge, such as it is, is the maker REBATE: repriced markout is ~zero-to-
negative (as microstructure predicts for a near-mid quoter), and the rebate
covers it with ~$70/day paper left over. Honest limits, unchanged: capture-
optimistic (assumes front-of-queue fill of a 100-sh quote on every print),
paper-only (no compliant account exists on F-1/no-SSN — this is measurement,
not a trading recommendation), and the t sits right at the bar. The desk keeps
recording; the number self-updates in maker_pnl_real.csv.
