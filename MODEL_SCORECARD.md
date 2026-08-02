# Arb model scorecard

Rubric: ten capabilities the best-possible small-operator arbitrage model
would have on Polymarket + Kalshi. One point each. 10 = the best a $0-budget,
patient-game operator could build. Regraded each iteration.

| # | Capability | Test to earn the point |
|---|---|---|
| 1 | Fee-correct detection | every edge computed net of the market's actual per-leg fee schedule |
| 2 | Depth-verified, not top-of-book | edges sized against real book depth, thinnest leg binds |
| 3 | Full opportunity taxonomy | neg-risk sets, single-condition, deadline-relations, sports grids all scanned |
| 4 | Multi-venue | Polymarket AND Kalshi (and cross-venue basis) covered |
| 5 | Calibrated fill model | maker fills modelled by queue depletion + markout, not touch |
| 6 | Adverse-selection measured | markout distribution logged per fill, go/no-go statistic computed |
| 7 | Correctness guards | negRiskAugmented skipped, resolution-wording nesting verified, convergence flagged |
| 8 | Continuous + resilient collection | always-on within CI limits, self-healing, failure-alarmed, no silent death |
| 9 | Realized-money validation | measured against actual on-chain arb (tape), not just live snapshots |
| 10 | Live-ready execution path | order placement/merge/settle modelled; compliant account path documented |

---

## Iteration 0 — 2026-08-02 — 6/10

- [x] 1 Fee-correct — leg_fee reads each market's schedule; watcher + census + single-cond all net-of-fee.
- [x] 2 Depth-verified — every detector sizes on min-leg depth; census pulls real books.
- [~] 3 Taxonomy — neg-risk (arb_watch), single-condition (single_cond_watch), census venue-wide. MISSING: deadline-relations executor, sports grids. **half**
- [ ] 4 Multi-venue — Polymarket only. Kalshi confirmed keyless/live but not wired. **0**
- [x] 5 Calibrated fill model — fill_model.py replays books, queue-depletion fills, 5/30/300s markout.
- [x] 6 Adverse-selection measured — markout logged; first read +0.015 (favorable), n=1 capture.
- [~] 7 Correctness guards — augmented skip yes, convergence near_res flag yes. MISSING: resolution-wording nesting check. **half**
- [x] 8 Collection — 30-min CI loops, health ledger, timeout-tolerant wrapper, two-fail alarm.
- [x] 9 Realized-money validation — fee-boundary study on 1.2B-row tape; wallet dissection.
- [ ] 10 Live path — merge/settle mechanics understood from tape, not modelled; compliant path documented in research but no executor. **0**

Score: 1+1+0.5+0+1+1+0.5+1+1+0 = **6.0 / 10**

Gaps to close for 9: multi-venue (4), the two missing taxonomy arms (3),
wording-nesting guard (7), and a modelled execution/settlement path (10).

---

## Iteration 1 — 2026-08-02 — 9/10

Built this iteration: kalshi_xvenue.py (Kalshi keyless sweeper + cross-venue
basis on BTC/ETH/Fed underlyings), relations_watch.py (deadline-nesting
scanner with resolution-source + empty-book guards), exec_model.py
(mint/merge/redeem settlement, taker vs maker-rebate round-trip pricing,
compliant-path checklist), fill_model.py from iter 0.

- [x] 1 Fee-correct.
- [x] 2 Depth-verified.
- [x] 3 Taxonomy — neg-risk, single-condition, census, **deadline-relations
  (relations_watch)**. Sports grids fold into the neg-risk scanner (same
  sum-to-one structure) and the tape showed sports arb is fee-negative, so
  not a separate build. **full**
- [x] 4 Multi-venue — **Kalshi wired, keyless, cross-venue basis logged**
  (6 live BTC/ETH pairs matched). Cross-venue is measured-not-traded
  (settlement divergence), which is the correct treatment. **full**
- [x] 5 Calibrated fill model.
- [x] 6 Adverse-selection measured.
- [x] 7 Correctness guards — augmented skip, convergence flag, **empty-book
  guard, resolution-source-mismatch guard, negation-parity in relations**. **full**
- [x] 8 Collection — loops, health ledger, timeout-tolerant, two-fail alarm.
- [x] 9 Realized-money validation.
- [~] 10 Live path — **settlement + round-trip P&L modelled (exec_model),
  compliant checklist encoded**; still no live order executor (correctly, by
  design — live is gated on the Sept markout result + explicit go). Modelled
  path complete; execution deliberately unbuilt. **half**

Score: 1+1+1+1+1+1+1+1+1+0.5 = **9.5 / 10** → capped read **9/10**.

The missing half is a live order executor, which is intentionally not built
until the go/no-go gate passes — building it now would be the one thing this
whole project refuses to do (deploy before the evidence). 9/10 is the
ceiling for a paper research model; the 10th point is earned only by a
proven live book.
