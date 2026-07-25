```
========================================================
THE DESK — status 2026-07-25 00:18
========================================================

[1] ARB EXECUTOR-SIM: 15 depth-verified fills logged
    total realized-at-depth profit: $40.36
    median fill size: 638 shares | median edge 0.7c

[2] WHALE SHADOW-BOOK: 240 paper-copied positions
    unique whales tracked: 4 | paper capital deployed: $12000
    (grades at resolution — accruing; verdict needs ~6-8 wks)

[2b] MAKER NET SIM: rewards $287.47 + fills $-993.53 = NET $-706.05 (100% adverse)

[3] MAKER PAPER-QUOTER: 20 eligible markets last snapshot
    combined reward pool: $10,804/day across all quoters
    adverse-selection check: 64% of quotes would have been run over by mid drift

========================================================

```

## 2026-07-25 — evening check-in

**Pipeline health:** all 12 recent Actions runs success (sims-30min + collect-2x-daily); every health.jsonl rc=0. Funding pull hit intermittent `ExchangeNotAvailable` on last collect_daily (exchange-side, not code) — funding.csv still current to 2026-07-24. Ledgers all growing: maker_net 815 rows, shadow_ledger 241, pm_top_positions 3523, arb_fills 16, funding 5095.

**[1] Arb executor-sim:** 15 depth-verified fills cumulative, $40.36 realized-at-depth (median 638 sh @ 0.7c). Recent snapshots surfaced SELL-ALL top-of-book edges (Hong Kong temp market) but 0 shares executable — edges did not survive real books. No new fillable arbs today.

**[2b] Maker net sim:** rewards $291.06 + fill/spread pnl $-992.56 = **NET $-701.51** over 814 market-intervals / 31 snapshots. Adverse runs 44% of intervals. Reward accrual keeps rising linearly (~$10/snapshot) but adverse fills outrun it ~3.4×; net continues to deepen.

**[2] Whale shadow-book:** 240 paper positions, 4 whales, $12k deployed. 0 graded this cycle (240 awaiting resolution) — verdict still ~6-8 wks out.

**[3] Maker paper-quoter:** 20 eligible markets, $10,804/day combined pool; 64% of quotes would have been run over by mid drift.

**Drill:** 10 model_p markets (Fed / geopolitics), unresolved — resolve July 28-31, Brier scoring to follow. Week-1 verdict (DESK_WEEK1.md) due on the July 29 run.
