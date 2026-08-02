
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

---

## 2026-08-02 — evening digest

**Pipeline health.** 11 of 12 recent Actions runs green; all 355 health.jsonl records rc=0. One real failure: `collect-2x-daily` at 08-02T00:14Z died on a rebase conflict in `health.jsonl` / `maker_book.csv` / `maker_net.csv` — overlapping workflows raced on the same append-only ledgers, and that run's collected data was **discarded, not delayed**. Fixed: `.gitattributes` sets `merge=union` on `collected/*.csv|jsonl` (append-only files, so union is correct; `drill_graded.csv` and `desk.html` are rewritten whole and excluded), plus a 5-attempt pull/push retry in `collect.yml` and `sim.yml`. Separately, sims cadence is degraded — 15 runs in the last 24h against a nominal 48 (GitHub throttles `*/30` cron on public repos), including a 23.5-hour blackout from 07-31 04:58 to 08-01 04:26.

**Arb executor-sim.** 68 depth-verified fills, **$484.28** cumulative. Daily: 7/30 $159.84, 7/31 $24.31, then **nothing** — both 08-01 `arb_watch` sweeps returned 0 opportunities, and there are no fills at all on 08-01 or 08-02. `arb_census` puts the entire extractable pool at **$3.38**. The neg-risk edge that carried Week 1 has closed; what remained was concentrated almost entirely in one recurring market ("Fed Decision in September?", 41 of 68 fills).

**Maker net-sim.** v2 reward $1,243.18, fill/spread PnL −$4,963.28, **NET −$3,720.09**, adverse 52% of 2,697 intervals. Defended v3: reward $930.64, fill −$2,548.91, **NET −$1,618.27**, adverse 34%, pulled 20% of quotes. v3 recovers ~$2.1k of v2's loss but is still solidly negative. Rewards have never covered the cost of being run over.

**Whale shadow-book — first grades ever.** `shadow_grader` had reported "graded 0" every night since inception. Root cause was in the resolver, not the market data: it paged `closed=true` ordered by `endDate` **descending**, which surfaces 2028-dated markets first and never reaches anything that settled last week; gamma also 422s past offset ~2000, which the old code swallowed as end-of-data. Replaced with per-title `public-search` lookups (`gamma_resolved.resolve_titles`). Result: **534 of 1,386 positions graded, 346 wins (64.8%)**.

The headline PnL of +$196,230 is an artifact and should be ignored. Two positions entered at **$0.0005** that resolved YES contribute +$199,900 of it at 1999:1. Excluding those two, the book is **−$3,669.76 on $26,700 staked (−13.8%)** across 532 positions at a 64.7% hit rate — high hit rate, negative expectancy, i.e. the whales are being copied into short-odds favourites that don't pay enough when they land. Ex-outlier wallet board (n≥20): 0x2005d1… +$75.80 (+6.9%, n=22) is the only positive; 0x076daa… −$276 (−3.8%, n=144), 0x2c3350… −$930 (−33.8%, n=55), 0x204f72… −$1,744 (−13.0%, n=269). **Caveat: a $0.0005 resting fill on an eventual winner is not a realistic copy.** That is a fill-realism flaw in the shadow methodology, not alpha; flagged rather than patched, since parameters are frozen.

**Calibration drill — hard grades.** 7 of 10 resolved (the 3 pending are long-dated "before GTA VI?" markets, correctly excluded — they sit at 0.5/0.5 with placeholder end dates). **Market Brier 0.1673 vs model 0.1716 — market ahead by 0.0043.** Shrinkage did its job on the one big miss (WTI $95 resolved NO from a market price of 0.77: model 0.549 vs market 0.593) but gave back slightly more across the six the market called correctly. This reverses the 7/29 provisional read that had the model ahead; that read also had NVIDIA resolving NO when it resolved YES. At n=7 neither result is a verdict on the 0.87 calibration slope.

**Code repairs this cycle (no strategy or parameter changes).** (1) `arb_fills.csv` — three writers appended different column sets to one file under `header=not f.exists()`, so extra fields landed positionally and `desk_grade.py` crashed on a tokenizing error; added `arb_ledger.append_fills` with a canonical schema and realigned 2 corrupted rows. (2) The resolver fix above. (3) Ledger merge/retry above. Note `collected/DESK_REPORT.md` is opened `"w"` by `collect_daily.py` twice daily, so it cannot hold digest history — this digest goes to `DESK_DIGEST.md` instead.
