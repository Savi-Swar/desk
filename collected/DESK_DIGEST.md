
---

## 2026-07-29 — evening digest (Week 1, final daily)

**Pipeline health.** All cloud runs green. Last 12 Actions runs (sims-30min every 30 min, collect-2x-daily) all `success`; every health.jsonl record this cycle rc=0. 88 snapshots accumulated. One standing non-fatal gap: `funding.csv` last wrote 2026-07-24 — collector logs `funding fail: ExchangeNotAvailable` (external exchange down, not a code fault; rc stays 0). All other ledgers growing normally.

**Arb executor-sim.** 46 depth-verified fills, $273.94 total realized-at-depth profit. Median fill 125 shares @ 1.0c edge, largest single fill $60. Today: 3 fills, $6.15. The book is thin and shrinking — daily arb profit has decayed from $128 (7/25) to single digits (7/27–7/29). Nearly every fill now comes from one recurring market ("Fed Decision in September?").

**Maker net-sim.** Cumulative reward accrual $828.41, fill/spread PnL −$3,023.26, **NET −$2,194.85**. Adverse-selection runs 52% of intervals and rising. The reward pool does not come close to covering the cost of being run over — the market-making leg is a confirmed money-loser at these parameters.

**Whale shadow-book.** 675 paper-copied positions, 7 whales, $33,750 deployed. 0 graded — all awaiting resolution (verdict needs ~6–8 wks). Concentration high: two wallets (0x204f…, 0x076d…) account for 587 of 675 positions.

**Calibration drill.** Still pending. Fed July-2026 markets trading 0.75 / 0.24 as of 07-29 06:30 UTC — not converged to 0/1, so the FOMC decision has not resolved. All other drill markets are July-31 or before-GTA-VI dated. No Brier scores yet; expect first resolutions 7/30–7/31.

---

## 2026-07-29 12:15 UTC — close-of-day (supersedes the 06:38 UTC entry above)

**Pipeline health.** Green. All 12 most recent Actions runs `success`; every record in health.jsonl this cycle rc=0, 92 snapshots accumulated. Same standing non-fatal gap: `funding.csv` last wrote 2026-07-24, collector logs `funding fail: ExchangeNotAvailable` (external exchange, not a code fault — rc stays 0). Every other ledger growing.

**Arb executor-sim.** 49 depth-verified fills, **$283.92** cumulative realized-at-depth. Median fill 183 shares @ 1.0c, largest single fill $60. Today: 6 fills, $16.13. Daily curve $0.29 / $40.07 / $128.09 / $68.70 / $15.87 / $14.77 / $16.13 — the 7/25 peak has not repeated; the edge now lives almost entirely in one recurring market ("Fed Decision in September?").

**Maker net-sim.** Reward accrual $850.68, fill/spread PnL −$3,153.40, **NET −$2,302.72**. Adverse-selection 52% of 1,936 intervals overall, but the daily trend is the story: 57% → 40% → 52% → 56% → 60% → 62% → 58%. Rewards never covered more than ~27% of fill losses on any day.

**Whale shadow-book.** 675 positions, 7 whales, $33,750 deployed, **0 graded** (all awaiting resolution). Two wallets (swisstony 424, 0x076d… 163) are 87% of the book.

**Calibration drill.** All 10 markets exact-matched against live Gamma; **none formally resolved** (`closed=False` on all 10 — the earlier fuzzy-search read that showed them closed was matching the wrong markets). Five have collapsed to near-certainty, so provisional scoring on the 3 effectively decided (<0.10): **market Brier 0.2799 vs model 0.2740** — model ahead. Scoring all 10 against current price as a soft outcome: **market 0.1192 vs model 0.1145** — model ahead again. Shrinkage wins where the market was confidently wrong (WTI $95: 0.77 → 0.0735; NVIDIA largest: 0.86 → 0.195) and loses a little where the market was already right and low (Israel, Iran airspace). Hard grades land 7/30–8/01.
