```
========================================================
THE DESK — status 2026-07-26 00:16
========================================================

[1] ARB EXECUTOR-SIM: 20 depth-verified fills logged
    total realized-at-depth profit: $168.45
    median fill size: 665 shares | median edge 0.7c

[2] WHALE SHADOW-BOOK: 387 paper-copied positions
    unique whales tracked: 5 | paper capital deployed: $19350
    (grades at resolution — accruing; verdict needs ~6-8 wks)

[2b] MAKER NET SIM: rewards $414.93 + fills $-1475.50 = NET $-1060.57 (100% adverse)

[3] MAKER PAPER-QUOTER: 14 eligible markets last snapshot
    combined reward pool: $7,288/day across all quoters
    adverse-selection check: 61% of quotes would have been run over by mid drift

========================================================

```

---

### Evening digest — 2026-07-26

- **Pipeline health:** all cloud runs green (sims-30min + collect-2x-daily), every health.jsonl record rc=0. One soft warning: funding fetch returned `ExchangeNotAvailable` on the latest collect_daily — transient exchange outage, not a code fault; `funding.csv` last row is 2026-07-24 and will backfill when the venue returns.
- **Arb executor-sim:** 20 depth-verified fills, $168.45 cumulative realized-at-depth profit (median 665 shares @ ~0.7c edge). New fill today: Philadelphia Union vs. Seattle Sounders SELL-ALL, +$16.52.
- **Maker net:** rewards $453.72 vs fill/spread pnl −$1,509.08 = **NET −$1,055.36** across 49 snapshots / 1,140 market-intervals. Adverse runs held at ~47% of intervals. Rewards keep accruing but nowhere near covering adverse fills — the maker book remains structurally underwater.
- **Whale shadow-book:** 387 paper-copied positions, 5 whales, $19,350 deployed. 0 newly resolved (all awaiting resolution; verdict ~6–8 wks out).
- **Calibration drill:** drill_2026-07-23 (10 markets, model_p vs market p) still unresolved — Fed July-meeting markets resolve ~Jul 28–31; Brier scores to follow.
