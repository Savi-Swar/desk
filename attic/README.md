# attic/

Retired scripts, preserved for the record. Convention: when a root script is no
longer referenced by any workflow, test, Makefile target, doc, or live code
path, it moves here via `git mv` (never deleted — history and receipts stay
reachable). Nothing in this directory is run by CI; scripts may have stale
imports of root modules and are kept as-is. Doc-cited paper receipts (e.g.
`validate_fills.py`, `markout_decomp.py`) stay at the root — they are evidence,
not clutter.

- `arb_executor_sim.py` — neg-risk set executor-simulator (paper-fills at real book depth). Superseded by the maker pipeline; nothing executed it.
- `drill_grade.py` — Brier-scored calibration drill grader (model_p vs market p). The drill was retired; no workflow or code invoked it.
- `firehose_audit.py` — one-off firehose capture quality scorer (/10). Its verdict was recorded; auditing is not part of the recurring pipeline.
- `kalshi_sweep.py` — early keyless Kalshi ladder-arb/xvenue sweeper. Replaced by `kalshi_xvenue.py`, which the collectors workflow runs.
- `wrds_setup.py` — one-time interactive WRDS credential setup + subscription inventory. Setup was completed; script had no remaining callers.
