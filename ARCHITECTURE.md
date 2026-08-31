# Architecture — the platform as an engineering artifact

*(The research results live in [RESULTS.md](RESULTS.md); this is the systems
view: what runs, what breaks, and what broke us until we fixed it.)*

## Shape

Zero-server design: GitHub Actions cron is the scheduler, the git repo is the
database, artifacts are cold storage. Four workflows (recorder / sims /
collectors / alarm) run 2–48×/day; every script executes under a health
wrapper that appends per-run records to a ledger, and the alarm workflow
opens a GitHub issue after two consecutive failures and closes it on the
next green run. Total infra cost: $0.

```
 live venue APIs ──► recorders (WebSocket) ──► gzip'd jsonl (artifacts, 30d)
                     collectors (REST)     ──► append-only CSV ledgers (git)
                                                │
                     derivers (markout, P&L) ◄──┘   } committed by CI;
                     studies / backtests            } union-merge +
                     papers (figures regenerate)    } merge=ours drivers
```

## Real-time capture

- **Trade firehose** (site-wide WebSocket, ~37 msg/s): requires a 5s
  application-level PING or the feed silently stops after the connect burst
  (found by wondering why 24 minutes of capture held zero trades).
  Deduplication keys on (tx_hash, asset, side, price, size) — a tx can carry
  several legitimate legs, and reconnects replay the burst.
- **Order books**: snapshot + diff stream, watchdog reconnects on 60s of
  silence, size guardrails per run. Readers everywhere tolerate truncated
  gzip (a crashed writer mustn't poison the next reader).

## Concurrency without a database

Three workflows commit to one branch. Failure modes met and fixed, in order:
1. Two appenders → text-merge conflicts → **union merge driver** for
   append-only ledgers.
2. Whole-file regenerated outputs → union duplicates rows → **merge=ours
   driver** (either side is fine; the next run regenerates from full data).
3. Any conflict left a wedged rebase that failed all retries → **abort-
   before-retry** in every commit loop.
4. A shared concurrency group made workflows cancel each other → per-workflow
   groups (the commit loops already serialize the pushes).
5. GitHub silently drops cron schedules for disabled-then-re-enabled
   workflows → renaming the workflow files re-registers them (nothing else
   did).

## Batch ingestion at API scale

880k+ resolved markets and 129k price-history crawls against rate-limited
endpoints with a hard ~2k pagination cap:
- **Adaptive window splitting**: sweep by end-date windows; any window that
  saturates the cap recursively halves, down to 15-minute slices (dense
  hourly-market days).
- **Resumability as a contract**: done-ledgers rebuilt from what's actually
  on disk after a crash (never trust the intent log over the data); marks
  crawls survive process kills, laptop sleeps, and DNS flaps.
- **Fail-fast guards with control probes**: an all-empty crawl aborts after
  200 rows — but only after probing a known-good record, so a legitimately
  sparse stretch doesn't false-trip (both failure modes happened).
- Multi-member gzip readers (append mode writes a member per run; naive
  readers silently drop everything after the first).

## The backtest engine

Bet-level, walk-forward. Fractional Kelly with per-market caps, fees,
slippage, and a daily exposure cap. Its test suite is pre-registered and
adversarial:
- **Null test**: on an efficient synthetic market, any strategy must lose
  exactly its costs and never pass the evidence bar. (The first synthetic
  generator leaked value into the price level via additive noise — the null
  test caught its own harness.)
- **Known-edge recovery** and **cost monotonicity** tests.
- Two sizing modes (capped Kelly vs flat fraction) must agree on sign before
  any result is claimable — added after the capped mode alone turned a
  losing bet stream into a +150% "strategy" by overweighting sparse days.

## Forward experiments as CI jobs

Open claims are adjudicated by cron, not by argument: a self-grading ledger
records live executable quotes for every market entering a trade window,
joins outcomes after resolution, and prints the realized edge; a parallel
ledger does the same for weather forecasts vs live prices. Nobody has to
remember to run the decisive test — it is scheduled.

## Lessons that generalize

Reconcile every derived quantity against ground truth before trusting it
(the tape vs book-shrinkage reconciliation exposed a 1,700× overcount);
guards need control probes; readers must survive their writers' deaths;
schedulers lie; and instrumentation that can kill your own headline result
is the most valuable code in the repo — it fired eight times.
