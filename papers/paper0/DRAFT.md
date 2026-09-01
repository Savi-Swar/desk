# The maker edge that wasn't: two measurement artifacts in prediction-market backtests

*Draft v0.1 — every number regenerates from the repo (`make_figures.py`,
`taq_benchmark.py`, `benchmark_table.py`). Prose is a working skeleton.*

## Abstract

Passive-fill backtests on Polymarket produce large, false maker edges. Using
live capture of the venue's order books and site-wide trade tape, we document
two artifacts. First, fill models based on order-book shrinkage overcount
executions by three orders of magnitude — 48,578 inferred "fills" against 28
real prints in the same window — because cancellations dwarf trades at the
touch. Second, markout measured at the trade price credits the maker with the
taker's full crossing distance; on wide books this books a "realized spread"
roughly 80 times what a US small-cap equity maker actually keeps, an edge
that vanishes when fills are repriced to the near-mid quotes the venue's
liquidity-reward rules actually require. Correcting both reduces a paper P&L
of several hundred dollars per day to approximately zero, consistent with
Dubach (2026). What survives is the maker rebate net of adverse selection —
measurable, small, and rebate-driven. We provide a practitioner checklist and
benchmark the venue's microstructure against millisecond TAQ.

## 1. Setting

Polymarket operates a central limit order book for binary outcome tokens
priced in (0,1). Since March 2026 takers pay `f·p(1−p)` per share (f ≈
0.02–0.07 by category); makers pay nothing and receive (a) a pro-rata rebate
of 15–25% of taker fees on their fills and (b) pro-rata shares of per-market
daily liquidity-reward pools, eligibility for which requires resting
two-sided size within a maximum spread of the mid. Data: the RTDS activity
firehose (site-wide matched trades, ~37/s, deduplicated on transaction hash ×
asset × side × price × size) joined to recorded book snapshots and diffs at
real trade timestamps. 23,470 fee-bearing maker fills, Aug 2026.

## 2. Artifact I: shrinkage fills

The tempting shortcut: when a book level loses size, count a fill. The trade
tape falsifies it — in a matched window the shrinkage model produced 48,578
fills; the venue printed 28 trades on those books (precision 0.06%,
overcount ~1,735×). Cancels, not fills (Fig 1). Every markout statistic built
on shrinkage fills — including our own early "+$2,500 paper" — measured
cancellation dynamics, not execution quality.

## 3. Artifact II: fill-at-touch markout

Markout `D·(p − mid_{t+h})` is the realized half-spread (Stoll 2000, SEC Rule
605): effective half-spread minus adverse selection to horizon h. Measured at
the trade price on 1,506 real fills (30s horizon, sizes capped at a realistic
100-share resting quote), the decomposition is +$522 spread capture − $39
price impact = +$483 "edge" — with 75% of it earned on the 9% of fills in
wide (>3¢) esports books (Fig 2).

The error is counterfactual: the trade price is the *touch the taker
crossed*. A reward-eligible maker rests near the mid; its tighter quote would
have become best and filled first at ~one tick. Repricing every fill to a
quote δ from mid — captured spread = min(δ, effective half-spread), adverse
selection unchanged — the edge is −$0.49 at δ = 0.1¢ (Fig 3). The entire
markout edge was spread the strategy could never touch. Corroborating:
Dubach (2026) finds median honest effective half-spreads ≈ 0 on Polymarket
and a ~59% order-book direction-inference accuracy; we additionally find 26%
of wide-book fills carry a wrong-side mid, so the naive mid is itself
unreliable exactly where the "edge" concentrated.

## 3b. The equity yardstick

Same decomposition, raw millisecond TAQ (Lee-Ready signed, crossed quotes
excluded; 10–11am, Aug 18–19 2026; dollar-weighted bps of price; Polymarket
wrong-side mids excluded to match):

| venue / book | effective half | realized | impact |
|---|--:|--:|--:|
| US equity mega-cap | 1.0 | +0.8 | 0.2 |
| US equity mid-cap | 3.2 | +1.2 | 1.9 |
| US equity small-cap | 8.6 | +2.8 | 5.8 |
| Polymarket tight (<1¢) | 17.2 | +6.3 | 10.9 |
| Polymarket wide (>3¢) | 560.8 | +235.5 | 325.3 |

Tight prediction-market books trade like somewhat-worse small-caps. The wide
books' +235 bps "realized spread" — the number a fill-at-touch backtest pays
itself — is ~80× a small-cap maker's take, a magnitude that should fail any
smell test calibrated on equities.

## 4. What actually remains

With fills capped at resting size, markout repriced to the near-mid quote,
and rebates computed from realized taker fees (fee-bearing rows identify the
taker's leg; the maker is the counterparty): over 12 recorded days, rebate
income +$1,264 against repriced markout −$449 — net +$815 paper, daily-mean
t = 1.95 on a Kish effective sample of ~2,300 bets. Statistically unresolved
at the 2.0 bar, still capture-optimistic (front-of-queue assumption), and
concentrated in the rebate: the daily ledger gates significance on |t| ≥ 2
with effective-N ≥ 30, and no day's markout alone clears it. The economics
that survive measurement are a subsidy net of adverse selection, not spread
capture.

## 5. Practitioner checklist

1. A fill is a print you were resting for, at your price, within your size —
   never book-shrinkage.
2. Mark against your own hypothetical quote, not the observed trade price;
   only accrue trades whose crossing distance reaches your quote.
3. Wide-book mids are unreliable (26% wrong-side here): use a micro-price or
   exclude, and exclude locked/crossed books as equity studies do.
4. Cap fills at resting size; keep the uncapped column only as a labeled
   counterfactual ceiling.
5. Report Kish effective-N, not row count — one whale is not 831 samples —
   and cluster inference at the regime level (an earlier day-clustered
   "bias" of ours, t = −4.2, was one crash month; monthly clusters gave
   t = −0.3).
6. Sanity-check magnitudes against the equity yardstick: retail venues are
   worse than small-caps, not 100× better.

## References (to fill)

Stoll (2000); Huang & Stoll (1996); Bessembinder (2003); SEC Rule 605;
Bailey & López de Prado (2014); Dubach (2026) arXiv:2604.24366; Polymarket
liquidity-rewards & maker-rebates documentation.
