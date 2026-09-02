# desk

![tests](https://github.com/Savi-Swar/desk/actions/workflows/tests.yml/badge.svg)

Measurement-first research platform for prediction-market microstructure.
The headline finding: at scale, this market is efficient — its apparent
inefficiencies price out as microstructure — and establishing that required
instruments rigorous enough to catch nine measurement artifacts that
standard backtesting would have shipped as edges. Everything below is
measured on real Polymarket data (live WebSocket capture plus the full
resolved-market history), every number survived an attempt to destroy it,
and the artifact ledger in [RESULTS.md](RESULTS.md) documents each catch
with receipts.
The methodology is extracted as a standalone stdlib-only library:
**[prereg](https://github.com/Savi-Swar/prereg)** — evidence bars, the
weighting-mirage catcher, locked adjudication, self-grading forward ledgers.
This repo is its case study.

**Start with [RESULTS.md](RESULTS.md)** (findings, 90 seconds) or
[ARCHITECTURE.md](ARCHITECTURE.md) (the systems view: zero-server design,
concurrency war stories, adversarial test suite).

## Findings (chronological)

1. **Book-shrinkage "fills" overcount real fills ~1,735×.** A fill model that
   treats disappearing book size as executions counts cancels, not trades.
   Validated against the RTDS trade firehose: 48,578 shrinkage "fills" vs 28
   real prints in the same window (`validate_fills.py`,
   `MARKOUT_GATE_INVALID.md`). Every markout built on it was noise.
2. **The favorable maker markout was a fill-at-touch artifact.** Realized
   markout on 1,506 real fills decomposed into +$522 spread capture − $39
   adverse selection; 9% of fills (wide esports books) carried 75% of the P&L.
   Repriced to a near-mid quote — the only quote that earns liquidity rewards —
   the markout edge is ≈ $0 (`markout_decomp.py`, `MARKOUT_DECOMP.md`).
   Independently consistent with Dubach 2026 (arXiv:2604.24366).
3. **What's left is the rebate.** Maker rebates (~20% of taker fees on your
   fills) are the one measurable, non-competed income line; adverse selection
   eats most of it. Daily accounting with effective-sample-size and
   significance gating: `maker_pnl_real.py` → `collected/maker_pnl_real.csv`.
   The liquidity-reward pools are size-gated and pro-dominated — modeled
   honestly, not capturable by a small quoter (`REWARD_CAPTURE_RESEARCH.md`).

## The instrument

- `firehose_recorder.py` — site-wide RTDS trade tape (~37 trades/s), deduped,
  full arb schema.
- `book_recorder.py` — order-book recording for a watchlist led by
  reward-eligible markets.
- `trade_markout.py` — joins real trades to book mids; per-fill markout at
  5s/30s/300s plus effective half-spread (so edges can be repriced to any
  quote distance, not booked at the touch).
- `maker_pnl_real.py` — daily P&L: near-mid repriced markout + realized
  rebate, capped at a realistic resting size; Kish effective-N; a day is only
  "significant" at |t| ≥ 2 with eff-N ≥ 30.
- `fetch_resolved.py` — full resolved-market history via Gamma (labels for
  calibration studies).
- Collectors for cross-venue comparisons (Kalshi, SX, Limitless, funding
  carry) under the same health ledger.

Runs on GitHub Actions cron ($0 infra): every script under
`run_with_health.py` → `collected/health.jsonl`; ledgers are committed by the
workflows (the repo is the database); recorder gzips are 30-day artifacts.
Failures self-report (auto-opened alarm issues) and self-clear on recovery.

## Ground rules

Paper only, by construction — measurement, not trading. Public APIs only; no
keys, no capital, nothing here executes. Ledger columns marked `ideal` are
deliberately kept as the counterfactual upper bound; only `live`-suffixed
numbers are defensible.
