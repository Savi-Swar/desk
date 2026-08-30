# Paper 0 — The maker edge that wasn't: two measurement artifacts in prediction-market backtests

*(Working outline. Voice: yours. Every number regenerates via `python papers/paper0/make_figures.py`.)*

## Abstract (draft skeleton)
Naive passive-fill backtests on Polymarket produce large, false maker edges.
We document two artifacts using live capture (order books + site-wide trade
tape): (1) fill models based on book shrinkage overcount executions ~1,500×
by booking cancellations as fills; (2) markout measured at the trade price
credits the taker's full crossing distance to a maker who — under the venue's
liquidity-reward rules — must quote near the mid and can never capture it.
Correcting both reduces a paper edge of hundreds of dollars per day to ≈0,
consistent with Dubach (2026). What survives is the maker rebate net of
adverse selection, which we measure directly.

## 1. Setup
- Polymarket CLOB mechanics; fees (taker `f·p(1−p)`), maker rebates,
  liquidity-reward eligibility (near-mid, min-size).
- Data: RTDS firehose (site-wide prints, dedup by (tx,asset,side,px,sz)),
  book recording (snapshots + diffs), joined at real trade timestamps.

## 2. Artifact I — shrinkage fills
- The tempting shortcut: book level loses size ⇒ "fill".
- Ground truth: 28 real prints vs 48,578 shrinkage fills in the same window
  (0.06% precision). Fig 1.
- Consequence: any markout on shrinkage fills measures cancel dynamics.

## 3. Artifact II — fill-at-touch markout
- Markout = realized half-spread (Stoll 2000): capture − impact.
- Decomposition on real fills: capture dominates and concentrates in
  wide-spread books (esports). Table/Fig 2 by spread bucket.
- The counterfactual error: reward-eligible quotes rest near the mid; the
  touch fill was never available. Repricing curve (edge vs quote offset):
  ≈0 at one tick. Fig 3.
- Corroboration: Dubach 2026 (arXiv:2604.24366) — honest effective
  half-spread ≈0; our wrong-side-mid rate (26%) on wide books.

## 4. What's actually left
- Rebate income (measured from realized fees × category rebate share),
  adverse selection at 30s, both capped at a realistic resting size.
- Daily ledger with Kish effective-N and significance gating; days with
  |t|≥2 & eff-N≥30 only. Honest read: rebate ~ covers adverse selection;
  net is small and market-dependent.

## 5. Practitioner checklist
- Fill = a print you were resting for, at your price, within your size.
- Mark against your own quote, not the trade price.
- Wide-book mids are unreliable (micro-price or exclude).
- Report effective-N, not row count; cap fills at resting size;
  keep the "ideal" column only as a labeled counterfactual.

## 3b. Cross-venue benchmark (raw millisecond TAQ via WRDS, same decomposition)
$-weighted, 30s horizon, bps of price; equities 10-11am Aug 18-19 2026,
Lee-Ready signed, crossed quotes excluded; Polymarket wrong-side mids excluded
to match. Regenerate: `taq_benchmark.py` (WRDS venv) then `benchmark_table.py`.

| venue / book | eff half | realized | impact |
|---|--:|--:|--:|
| US equity mega-cap | 1.0 | +0.8 | 0.2 |
| US equity mid-cap | 3.2 | +1.2 | 1.9 |
| US equity small-cap | 8.6 | +2.8 | 5.8 |
| Polymarket tight (<1c) | 17.2 | +6.3 | 10.9 |
| Polymarket wide (>3c) | 560.8 | +235.5 | 325.3 |

The hook: tight Polymarket books trade like a somewhat-worse small-cap. Wide
books book a "realized spread" ~80x what an equity small-cap maker actually
keeps — the fill-at-touch mirage in one row, against a 25-year-old yardstick
(Stoll 2000; SEC Rule 605 conventions).

## Figures (all from committed ledgers)
1. `fig1_fill_overcount` — shrinkage vs real fills (log scale).
2. `fig2_decomposition` — capture vs impact by spread bucket.
3. `fig3_reprice` — markout edge vs quote offset (touch → 1 tick).

## Venue
SSRN + site; arXiv q-fin.TR if endorsement lands. ≤12 pages.
