# desk

Live paper operation on prediction markets. Three mechanisms that can't be
backtested, sampled forward and graded against their own ledgers:

1. **Arb executor-sim** — checks mutually-exclusive outcome sets against real
   order-book depth every 30 minutes, logs executable size and profit.
2. **Maker sim** — quotes both sides on paper in reward-eligible markets and
   tracks reward accrual against adverse fills. Deliberately naive: it
   measures the toll a real maker has to dodge.
3. **Whale shadow-book** — snapshots the public on-chain positions of the top
   30 wallets twice a day and paper-copies new directional entries.

Runs on GitHub Actions cron (see `.github/workflows/`); every script goes
through `run_with_health.py`, which appends per-run records to
`collected/health.jsonl`. Ledgers are committed by the workflow — the repo
is the database.

Results and the research that led here: https://saviturswarup.com/vig/
(screen 06 is the research record, 07 is this desk).

Paper only. No live capital, no keys, no secrets — everything here reads
public APIs.
