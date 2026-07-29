
---

## 2026-07-29 — evening digest (Week 1, final daily)

**Pipeline health.** All cloud runs green. Last 12 Actions runs (sims-30min every 30 min, collect-2x-daily) all `success`; every health.jsonl record this cycle rc=0. 88 snapshots accumulated. One standing non-fatal gap: `funding.csv` last wrote 2026-07-24 — collector logs `funding fail: ExchangeNotAvailable` (external exchange down, not a code fault; rc stays 0). All other ledgers growing normally.

**Arb executor-sim.** 46 depth-verified fills, $273.94 total realized-at-depth profit. Median fill 125 shares @ 1.0c edge, largest single fill $60. Today: 3 fills, $6.15. The book is thin and shrinking — daily arb profit has decayed from $128 (7/25) to single digits (7/27–7/29). Nearly every fill now comes from one recurring market ("Fed Decision in September?").

**Maker net-sim.** Cumulative reward accrual $828.41, fill/spread PnL −$3,023.26, **NET −$2,194.85**. Adverse-selection runs 52% of intervals and rising. The reward pool does not come close to covering the cost of being run over — the market-making leg is a confirmed money-loser at these parameters.

**Whale shadow-book.** 675 paper-copied positions, 7 whales, $33,750 deployed. 0 graded — all awaiting resolution (verdict needs ~6–8 wks). Concentration high: two wallets (0x204f…, 0x076d…) account for 587 of 675 positions.

**Calibration drill.** Still pending. Fed July-2026 markets trading 0.75 / 0.24 as of 07-29 06:30 UTC — not converged to 0/1, so the FOMC decision has not resolved. All other drill markets are July-31 or before-GTA-VI dated. No Brier scores yet; expect first resolutions 7/30–7/31.
