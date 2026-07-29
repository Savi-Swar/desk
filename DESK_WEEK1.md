# THE DESK — Week 1 Verdict

*Paper prediction-market desk. Data window 2026-07-23 → 2026-07-29 (7 days, 92 snapshots). Everything below is depth-verified paper simulation on live Polymarket order books; no capital deployed. Instruments and parameters were frozen for the week.*

*Final close-of-day version, 2026-07-29 12:15 UTC. Supersedes the draft written at 06:38 UTC — figures below are the week-end numbers.*

---

## Bottom line

Of the four legs, **one makes money and does not scale, one loses money and should be shut off, and two have not produced a gradable result yet.**

| Leg | Week-1 result | Verdict |
|-----|---------------|---------|
| **Arb executor** | +$283.92 realized-at-depth, 49 fills | Real but tiny, decaying, and concentrated in one market complex |
| **Maker net** | **−$2,302.72** (rewards $850.68 − fill/spread $3,153.40) | **Falsified.** Reward pool does not cover adverse selection |
| **Whale shadow-book** | 675 positions, $33.75k paper, 0 graded | Incomplete — verdict needs 6–8 weeks of resolutions |
| **Calibration drill** | Model ahead on both provisional scorings | Provisional only — nothing has formally resolved |

The honest read after one week: **the maker-rebate thesis is falsified at these parameters, the arb edge is real but too thin to matter, the copy-trade book is the only leg that could still print a positive verdict and can't be graded yet, and the house calibration model is provisionally beating the raw market on a sample far too small to trust.**

---

## 1. Arb fillability record

49 top-of-book arbs cleared depth verification and were "filled" over the week for **$283.92** total realized-at-depth profit. This is the number that matters: each was verified executable against the actual book, not against a quote that would vanish on contact.

| Day | Fills | Profit | Cumulative |
|-----|-------|--------|------------|
| 07-23 | 1 | $0.29 | $0.29 |
| 07-24 | 14 | $40.07 | $40.36 |
| 07-25 | 5 | $128.09 | $168.45 |
| 07-26 | 5 | $68.70 | $237.15 |
| 07-27 | 3 | $15.87 | $253.02 |
| 07-28 | 15 | $14.77 | $267.79 |
| 07-29 | 6 | $16.13 | $283.92 |

Median fill 183 shares @ 1.0c edge; largest single fill $60. Two structural facts:

- **Count and value have decoupled.** After the 7/25 spike (a fat mispricing that paid $128), daily profit settled into the $14–16 range and stayed there regardless of activity — 15 fills on 7/28 netted $14.77, under a dollar each. The opportunities left are smaller, not scarcer. The week's total is one good day plus noise.
- **It's one market complex.** Nearly every recent fill traces to the recurring "Fed Decision in September?" contract, with occasional appearances from "How many Fed rate cuts in 2026?". This is not a diversified arb stream; it is one structurally mispriced Fed complex being harvested a cent at a time. When it resolves, the leg likely goes quiet.

**Verdict:** the arb executor finds *real*, depth-verified edge — but at a ~$15/day run-rate concentrated in a single contract family, before fees, gas, or any real-world latency disadvantage, it is a proof-of-concept, not a strategy. It clears the bar for continuing to watch, not for capital.

## 2. Maker net curve — the decisive result

The maker leg quotes into reward-bearing markets and collects the daily liquidity-reward pool, against the cost of adverse fills (getting run over when the mid drifts through your quote). The week-long curve, by day:

| Day | Intervals | Reward | Fill PnL | **Cum. NET** | Adverse |
|-----|-----------|--------|----------|--------------|---------|
| 07-23 | 211 | $96.64 | −$380.20 | −$283.56 | 57% |
| 07-24 | 584 | $190.83 | −$613.32 | −$706.05 | 40% |
| 07-25 | 315 | $131.43 | −$488.18 | −$1,062.79 | 52% |
| 07-26 | 276 | $148.14 | −$526.83 | −$1,441.47 | 56% |
| 07-27 | 225 | $128.37 | −$471.75 | −$1,784.85 | 60% |
| 07-28 | 230 | $103.25 | −$469.66 | −$2,151.26 | 62% |
| 07-29 | 95 | $52.00 | −$203.46 | **−$2,302.72** | 58% |

Rewards recovered between 20% and 31% of fill losses on **every single day**. There is no day where the leg came close to break-even, and the cumulative net curve is close to a straight line down at roughly −$330/day. Across all 1,936 intervals the adverse rate is 52%, but the daily trend is the mechanism: after 07-24 it climbs monotonically 40% → 62%.

**Verdict — falsified.** The premise that liquidity rewards compensate for the risk of quoting is wrong at these markets and parameters. The quotes are not being filled by uninformed flow; they are being run over by mid drift, exactly the failure mode this sim existed to detect. Widening the quote would cut fills but also cut reward-pool share, and the pool would need to grow roughly 4x to close a gap this size. **Retire the maker leg from the live-candidate list**; keep the sim as a cheap monitor in case pools expand or spreads widen.

## 3. Whale shadow-book — incomplete

675 positions copied from 7 tracked whales, $33,750 in paper stake. **0 graded** — every position is awaiting market resolution. This is expected, not a failure: prediction-market positions resolve on event timelines.

Concentration is high — two wallets supply 587 of 675 positions:

- `0x204f72f353…` (swisstony) — 424 positions
- `0x076daa87c4…` — 163 positions
- `0x2c335066fe…` — 83 positions
- (four more wallets, 1–2 positions each)

**Verdict — pending.** This is the one leg that could still print a positive Week-N verdict, but copy-trading only reveals itself at resolution; a real read needs 6–8 weeks. Flagging now: the book is effectively a bet on *two* wallets, so the eventual verdict will say more about those two whales than about "whale copying" in general. Note also that the wallets being up is not the same as the copy working — leaderboard PnL is realized on their own entries and sizing, while the shadow-book enters later at a worse price with flat sizing. That divergence is the actual experiment.

## 4. Wallet skill board

**By week-over-week PnL change** (16 snapshots, 07-23 → 07-29):

| Wallet | Week ΔPnL | Total PnL | Edge (PnL/vol) | Shadowed |
|--------|-----------|-----------|----------------|----------|
| swisstony | +$387,196 | $8.91M | 2.25% | ✓ |
| RN1 | +$321,470 | $1.48M | 0.79% | |
| pada | +$230,685 | $1.37M | 111.51% | |
| 0x2c3350… | +$217,905 | $2.31M | 0.68% | ✓ |
| highnetworth | +$203,060 | $1.51M | 38.24% | |
| BreakTheBank | +$23,592 | $2.32M | 2.86% | ✓ |
| 0x076d… | +$22,864 | $1.69M | 4.93% | ✓ |
| Jsram | +$7,576 | $2.74M | 10.25% | ✓ |
| ndb1 | +$394 | $2.05M | 12.92% | ✓ |
| ramadamaramadam | −$6,147 | $2.61M | 16.17% | ✓ |
| 0x3DFb15… | −$127,125 | $1.01M | 1.63% | |

6 of the 7 shadowed wallets were up on the week, +$653k aggregate realized.

**By efficiency** (edge = PnL/volume, latest snapshot, volume > $1M) — a better skill proxy than raw PnL:

| Wallet | PnL | Volume | Edge |
|--------|-----|--------|------|
| asparagus2012 | $3.66M | $2.42M | 151.4% |
| pada | $1.37M | $1.23M | 111.5% |
| 0x75973C66… | $0.92M | $1.60M | 57.5% |
| FootballFan98 | $1.55M | $3.60M | 43.1% |
| highnetworth | $1.51M | $3.94M | 38.2% |

**The shadow set is not the top of the skill board.** Two of the week's three biggest gainers (RN1, pada) are not being copied, and not one of the top-5 efficiency wallets is in the shadow book — the copied set is mid-pack on edge-per-dollar and is anchored by swisstony, whose 2.25% margin on $397M volume is high-turnover grinding rather than sharp selection. If the shadow-book underperforms, **wallet selection is the first thing to re-examine**, ahead of the copy mechanics.

## 5. Calibration drill — provisional, model ahead

The 10-market drill (2026-07-23) scores the **house model** (`model_p` = market price shrunk toward 0.5 by the measured 0.87 calibration slope) against the raw market price, via Brier score, at resolution. It grades the model, not the user.

All 10 markets were exact-matched against live Gamma today. **None has formally resolved** — `closed=False` on all ten, with the Fed pair dated 07-29 and the rest 07-31/08-01. (A fuzzy title search initially reported several as closed and trading at 0.0005; that search was matching different, older markets and is not the basis for anything here. The Fed pair is still live at 0.7675 / 0.231.)

Five have nonetheless collapsed to near-certainty, which permits provisional scoring:

| Scoring | Market Brier | Model Brier | Winner |
|---------|--------------|-------------|--------|
| Hard — 3 effectively decided (p < 0.10) | 0.2799 | **0.2740** | model |
| Soft — all 10, outcome = current price | 0.1192 | **0.1145** | model |

The model wins on both, and the *why* matters more than the margin. Shrinkage toward 0.5 pays off where the market was confidently wrong:

- **WTI $95 in July:** market 0.77 → now 0.0735. Market Brier 0.5929, model 0.5491.
- **NVIDIA largest by July 31:** market 0.86 → now 0.195. Market 0.7396, model 0.6872.

And costs a little where the market was already right and already low:

- **Israel airspace by 7/31:** market 0.32 → 0.0485. Market 0.1024, model 0.1170.
- **Iran airspace by 7/31:** market 0.38 → 0.061. Market 0.1444, model 0.1560.

That is the shrinkage trade in miniature: insurance against the market's overconfident tails, paid for with a premium on its well-calibrated middle. Week 1 happened to contain two large overconfident tails, so it paid. **Ten markets and three near-decisions cannot validate the 0.87 slope.** Hard grades land 07-30 through 08-01 and this table should be re-scored then; it is not a result until it is.

## 6. Pipeline health

Migration to GitHub Actions cron (Savi-Swar/desk) has held. Sims every 30 min, collect twice daily; **all 12 most recent runs `success`, every health record rc=0**, 92 snapshots banked over the week. The sampling dropouts of the local-launchd era have not recurred in six days of unattended operation.

One standing non-fatal issue: `funding.csv` has not updated since 07-24 — the collector logs `funding fail: ExchangeNotAvailable` and exits rc=0. External exchange outage, not a code fault, and contained (no other ledger affected). Worth a fallback venue if it persists another week.

Standing operational risk: GitHub disables scheduled workflows after 60 days of repository inactivity. Daily commits currently keep that clock reset; a `workflow_dispatch` revives the cron if it ever goes quiet.

---

## What Week 2 should answer

1. **Kill or shrink the maker leg.** −$2,302.72 over 1,936 intervals with a monotonically rising adverse rate is unambiguous. Frozen params say leave it running as a control, but the thesis is dead; Week 2's job is to confirm the loss is structural adverse selection and not a parameter artifact.
2. **Stress the arb leg's concentration.** Measure what survives when the Fed complex is excluded. If the answer is near zero, the leg's real capacity is far below its $284 headline.
3. **Re-score the drill on hard resolutions** (07-30 → 08-01) and seed a second cohort. Ten markets cannot validate a calibration slope, and the provisional win came from exactly two big tail calls.
4. **Revisit shadow-wallet selection.** The copied set is not the skill board's top and contains none of the efficiency leaders. Explain that before the 6–8 week verdict lands and confounds selection with mechanics.
5. **Add a funding fallback venue** if `ExchangeNotAvailable` persists.

*All figures paper. Nothing in this document is a recommendation to trade.*

*— Desk, close of 2026-07-29*
