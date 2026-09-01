# Paper 1 numbers audit — 2026-08-31

Draft v0.1 → v0.2. Every number re-checked against regenerated outputs and
source docs. `study_longshot.py` re-run 2026-08-31 20:33 EDT with the
permanent pinned-mark filter; NOTE: `fetch_price_marks.py` tail crawl was
RUNNING during the audit (~40k/129,432 targets at the time), so mark counts
are a snapshot and will grow — re-run this audit when the crawl completes,
before submission. Label files unchanged (Aug 27–29).

## Changed

| # | location | was | now | source |
|---|---|---|---|---|
| 1 | header | Draft v0.1 | v0.2 + crawl-in-flight note | — |
| 2 | abstract, §2 | 880,324 universe | **880,326** | counted unique ids across all 3 label files with the tolerant multi-member reader (matches PINNED_PRICE_CHECK.md) |
| 3 | abstract | marks for 90,000+ | **105,000+** | study run: 105,527 marked markets |
| 4 | §2 | 90,758 marked markets | **105,527** (+ snapshot caveat) | study_longshot.py output |
| 5 | abstract, §3 | pinned 22–28% of marks | **13–28% (by horizon)** | recomputed on current marks: T-24h 20.7%, T-72h 27.8%, T-168h 13.1% (was 21.7/28.0/15.6 at the 74,568-mark snapshot in PINNED_PRICE_CHECK.md) |
| 6 | §3 | "Two of the four" interim cells died | **"Three of the six"** | PINNED_PRICE_CHECK.md: 3 of 6 pre-exclusion cells did not survive |
| 7 | §3 weighting | example cell "16,236 obs = 6.2 effective months" | **"8,910 obs = 3.8 effective months"** | old example matches no current cell; replaced with current T-24h weather longshots |
| 8 | abstract, §4 | 12 cells, spanning 22–32 months | **13 cells, spanning 11–33 months** | current verdict output (T-72h other longshots is new; month spans shifted) |
| 9 | §4 table | 12 rows (old data) | **13 rows, all cells refreshed** | study_longshot.py 2026-08-31 run, verbatim |
| 10 | abstract | "marginally tradeable... clears a pre-registered evidence bar" | retraction + politics-favorites pending + forward arbiter | STUDY1_OOS.md final revision, HUNT_LOG.md |
| 11 | §5 | positive quotable SR 3.93 / PSR 0.99 result | full arc: first pass → RETRACTION (2026 reversal +2.2/+2.4pp, ex-weather +4.6pp, enlarged bet-weighted +0.6pp; mirage #8 day-budget reweighting, −3.28c/share vs +150% capped; modes-must-agree rule) → six-candidate hunt → politics-favorites pending survivor with locked adjudication rule | STUDY1_OOS.md revision; HUNT_LOG.md |
| 12 | §6 | "seven documented ways" | **"eight"** | RESULTS.md mirage table (8 rows) |
| 13 | §6 | "strongest in the final day" (tied to retracted trade) | "so far untradeable in every implementation tried" | honest-state alignment |
| 14 | §7 | falsifier (ii) listed as pending | marked as FIRED for the pooled trade; politics-favorites adjudication noted | STUDY1_OOS.md, HUNT_LOG.md |

## Verified unchanged (source on disk)

- 24/72/168h horizons; $5,000 volume floor; fidelity=720; ~2,000-row offset
  wall; 15-minute window splits; "exactly one outcome > 0.99" —
  `fetch_price_marks.py`, `fetch_resolved.py`
- 2020–2026 span — label endDate range 2020-01-01 → 2026-06-23
- ~4k legacy category labels ("~4k of 880k": 4,335 rows carry one); 79%
  classifier agreement (re-ran `market_cats.py`: 79% on 4,060 legacy labels;
  note OUTLINE.md says 76% — stale there, not in the draft)
- family sums 0.97 (T-24h) / 1.39 (T-72h) / 1.85 max —
  `data/weather_artifact_check.md` (0.974 / 1.393 / 1.845)
- t = −4.2 → −0.3 clustering collapse — study_longshot.py docstring,
  RESULTS.md mirage #3
- log-loss 0.360 vs 0.388 (crowd vs model) — WEATHER_V1.md (0.3595 / 0.3875,
  2,972 buckets)
- +5pp month-weighted vs +0.6pp bet-weighted crypto-favorites —
  STUDY1_OOS.md (+5.3/+5.1pp vs +0.6pp)
- [0.03, 0.35) trade band — backtest/oos_longshots.py
- All §5 figures (−1.77pp, n=4,000, 157 days, +68%, SR 3.93, PSR 0.99, Kish
  102/157, top-5 6%, DSR 0.81/12 variants, SR 1.97 / PSR 0.90 at 200bps,
  −0.7pp T-72h; retraction figures; all politics-favorites figures and the
  adjudication thresholds) — STUDY1_OOS.md and HUNT_LOG.md verbatim

## Could NOT verify from disk (kept in draft as historical account, flagged)

1. **§3 regime-clustering detail**: "477 crypto-favorite observations across
   131 (underlying × day) clusters", gap "−12.8pp", month-clustered
   "t = −0.33" (docstring says −0.3), and "December's rebound shows +18pp".
   Only the t = −4.2 → −0.3 collapse itself is documented
   (study_longshot.py docstring, RESULTS.md); the counts, the −12.8pp, and
   the +18pp December figure appear nowhere outside the draft and predate
   the pinned filter, so they cannot be regenerated from current code.
   Either regenerate from a pre-filter branch or soften the prose to the
   documented collapse before submission.
   **RESOLVED 2026-08-31: regenerated from current data — see "§3 worked
   example regeneration" appendix below; §3 rewritten with the new numbers.**
2. **§3 family-vig caveat (minor)**: the 0.97 T-24h mean family sum is over
   *priced* buckets only (~72% coverage); the draft's phrasing "sum far
   above one" leans on the T-72h 1.39 and the scaled ~1.25–1.4 estimate.
   Accurate per weather_artifact_check.md but worth a wording pass.
3. **Universe discrepancy noted**: data/weather_artifact_check.md says
   880,324 ids, PINNED_PRICE_CHECK.md and this audit's direct count say
   880,326 — the older doc likely used a slightly different reader; draft
   now uses 880,326.
4. **Moving targets**: 105,527 marked markets, 13–28% pinned shares, and
   the entire §4 table will shift when the tail crawl finishes; the
   politics-favorites adjudication auto-fires at that point (HUNT_LOG.md).

## Appendix: §3 worked example regeneration (2026-08-31, descriptive only)

The old §3 figures (477 obs / 131 underlying×day clusters / −12.8pp /
t −4.2 → month t −0.33 / December +18pp) predate the pinned filter and the
tail crawl and could not be reproduced. Recomputed the same quantities from
`data/price_marks.csv.gz` (108,868 mark rows at run time; tail crawl still
appending) + the three label files, via `study_longshot.read_gz_tolerant`,
`load_slugs`, `pinned`, `cat_group`.

Definition: category = crypto (`cat_group`), outcome-0 `p_72h` in
[0.60, 0.98); gap = 1{outcome-0 won} − p. Underlying from slug tokens:
bitcoin/btc, ethereum/eth, solana/sol, xrp, doge/dogecoin, else "other".
Cluster t = mean of equal-weighted cluster means / SE across clusters (no
minimum cluster size; the §4 verdict pipeline instead clusters by month
alone with ≥5 obs per month — figures differ accordingly).

WITHOUT the pinned filter (the pre-filter world of the original example):

- n = 1,801; pooled bet-weighted gap −4.6pp
- day-clustered (underlying × day): 721 clusters, mean −4.3pp, t = −3.24
- month-clustered (underlying × month): 122 clusters, mean −0.2pp, t = −0.10
- per-month pooled gaps: Oct-2025 −7.2pp (n=402), Nov-2025 −25.3pp (n=284,
  16% of obs; underlying×month cluster means −39.1 to −10.2pp),
  Dec-2025 +14.1pp (n=35; cluster means −4.6 to +21.8pp)

WITH the pinned filter (current pipeline):

- n = 1,467; pooled bet-weighted gap −9.3pp
- day-clustered: 651 clusters, mean −7.4pp, t = −5.04
- month-clustered (underlying × month): 100 clusters, mean −11.4pp, t = −3.37
- per-month: Oct-2025 −9.2pp (n=371), Nov-2025 −28.4pp (n=264),
  **Dec-2025 n=0 — all 35 December observations are pinned afterlife
  prints**; the "December rebound" of the old example is itself a pinned
  artifact.

So the day→month clustering collapse (t −3.2 → −0.1) is real but lives only
in the pinned-included world; after the pinned filter the T-72h
crypto-favorites gap survives month clustering (underlying×month t −3.4;
the month-only ≥5-obs verdict clustering gives the §4 cell −7.3pp, t −2.2).
§3 now states which world the example inhabits. No strategy parameters were
touched; this is characterization of an already-reported artifact.

Mark counts are a snapshot (crawl in flight); re-run before submission.
