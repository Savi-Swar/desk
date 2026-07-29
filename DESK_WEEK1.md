# THE DESK — Week 1 Verdict

*Paper prediction-market desk. Data window 2026-07-23 → 2026-07-29 (7 days). Everything below is depth-verified paper simulation on live Polymarket order books; no capital deployed. Instruments and parameters were frozen for the week.*

---

## Bottom line

One of the three legs makes money in paper, one is a confirmed loser, and one is still accruing toward a verdict.

| Leg | Week-1 result | Verdict |
|-----|---------------|---------|
| **Arb executor** | +$273.94 realized-at-depth, 46 fills | Real but tiny and decaying — a coin-machine, not a business |
| **Maker net** | **−$2,194.85** (rewards $828 − adverse fills $3,023) | **Losing.** Reward pool does not cover adverse selection |
| **Whale shadow-book** | 675 positions, $33.75k paper, 0 graded | Incomplete — verdict needs 6–8 weeks of resolutions |

The honest read after one week: **the maker-rebate thesis is falsified at these parameters, the arb edge is real but too thin to matter, and the copy-trade book is the only leg with a chance of a positive verdict — and it can't be graded yet.**

---

## 1. Arb fillability record

46 top-of-book arbs cleared depth verification and were "filled" over the week for **$273.94** total realized-at-depth profit.

| Day | Fills | Profit |
|-----|-------|--------|
| 07-23 | 1 | $0.29 |
| 07-24 | 14 | $40.07 |
| 07-25 | 5 | $128.09 |
| 07-26 | 5 | $68.70 |
| 07-27 | 3 | $15.87 |
| 07-28 | 15 | $14.77 |
| 07-29 | 3 | $6.15 |

Median fill 125 shares @ 1.0c edge; largest single fill $60. Two structural facts:

- **The edge is decaying.** After the 7/25 spike (a fat mispricing that paid $128), daily profit collapsed to single digits even as fill *count* stayed high (15 fills on 7/28 netted $14.77 — sub-dollar each). The book has been picked clean.
- **It's one market.** Nearly every recent fill is the recurring "Fed Decision in September?" contract. This is not a diversified arb stream; it's one repeatedly-mispriced market being harvested a cent at a time.

**Verdict:** the arb executor finds *real*, depth-verified edge — but at ~$40/day and falling, concentrated in a single contract, it is a proof-of-concept, not a strategy. Fees and any real-world latency would likely erase it.

## 2. Maker net curve — the decisive result

The maker leg quotes into reward-bearing markets and collects the daily liquidity-reward pool, against the cost of adverse fills (getting run over when the mid drifts through your quote). The week-long curve:

| Day | Cum. reward | Cum. fill/spread PnL | **NET** | Adverse intervals |
|-----|-------------|----------------------|---------|-------------------|
| 07-24 | $203 | −$618 | −$415 | 41% |
| 07-25 | $360 | −$1,250 | −$889 | 45% |
| 07-26 | $500 | −$1,684 | −$1,184 | 47% |
| 07-27 | $646 | −$2,211 | −$1,565 | 49% |
| 07-28 | $756 | −$2,734 | −$1,979 | 51% |
| 07-29 | $828 | −$3,023 | **−$2,195** | 52% |

Rewards accrue linearly (~$120/day). Adverse fills accrue *faster* (~$430/day) and the adverse-selection rate is climbing (41% → 52%). The gap widens every single day.

**Verdict — falsified.** The premise that liquidity rewards compensate for the risk of quoting is wrong at these markets and parameters. You are paid ~$120/day to lose ~$430/day. There is no snapshot in the week where the maker leg was net positive, and the trend is monotonically worse. This is the clearest finding of Week 1.

## 3. Whale shadow-book — incomplete

675 positions copied from 7 tracked whales, $33,750 in paper stake. **0 graded** — every position is awaiting market resolution, and the book is only a few days old.

Concentration is high: two wallets supply 587 of 675 positions —

- `0x204f72f353…` — 424 positions
- `0x076daa87c4…` — 163 positions
- `0x2c335066fe…` — 83 positions
- (four more wallets, 1–2 positions each)

**Verdict — pending.** This is the one leg that could still print a positive Week-N verdict, but copy-trading only reveals itself at resolution. Expect the first meaningful grades as July/August sports and event markets settle; a real read needs 6–8 weeks. Flagging now: the book is effectively a bet on *two* wallets, so the eventual verdict will say more about those two whales than about "whale copying" in general.

## 4. Wallet skill board (context)

Top realized-PnL wallets on the tracked leaderboard (30 wallets, snapshot 2026-07-29):

| Wallet | Realized PnL | Volume |
|--------|-------------|--------|
| swisstony | $8.91M | $396.7M |
| DEEDDIT | $8.05M | $72.1M |
| asparagus2012 | $3.66M | $2.42M |
| Sparkling8899 | $3.64M | $20.4M |
| Allezpapa | $2.84M | $12.6M |

`asparagus2012` is the standout by *efficiency* — $3.66M PnL on only $2.42M volume implies enormous edge-per-dollar, unlike the high-turnover names (swisstony: $8.9M on $397M ≈ 2.2% margin). If the shadow-book is going to copy anyone, efficiency-per-volume is the signal worth chasing — not raw PnL.

## 5. Calibration drill — pending

The 10-market drill (2026-07-23) scores the **house model** (`model_p` = market price shrunk toward 0.5 by the measured 0.87 calibration slope) against the raw market price, via Brier score, at resolution.

As of this report **no drill market has resolved.** The Fed July-2026 contracts are still trading 0.75 / 0.24 (not converged to 0/1 → FOMC decision not yet settled); the remaining eight are July-31-dated or "before GTA VI." First Brier scores expected 7/30–7/31. **No model-vs-market verdict this week.**

## 6. Pipeline health

Migration to GitHub Actions cron (Savi-Swar/desk) is stable: sims every 30 min, collect twice daily, all runs `success`, every health record rc=0, 88 snapshots banked over the week. One standing non-fatal issue — `funding.csv` has not updated since 07-24 (`ExchangeNotAvailable`, external, rc stays 0). No sampling gaps otherwise; the cloud cron has eliminated the local-launchd dropout problem.

---

## What Week 2 should answer

1. **Kill or shrink the maker leg?** It's the biggest loser and the result is unambiguous. Frozen params say leave it running as a control, but the thesis is dead — Week 2's job is to confirm the loss is structural (adverse selection) and not a parameter artifact.
2. **First shadow grades.** The only leg that can turn positive. Watch resolutions and whether the two dominant whales carry the book.
3. **Drill Brier scores.** Does shrinking market prices toward 0.5 (the 0.87 slope) actually beat raw market as a forecaster? First real data lands next week.
4. **Arb concentration.** Is there edge beyond the one Fed market, or is the $274 a single-contract fluke?

*— Desk, evening of 2026-07-29*
