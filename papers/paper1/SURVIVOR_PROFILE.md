# Descriptive profile: the politics-favorites pending survivor

*2026-08-31. Characterization only — no trading rules, no parameter
selection; the HUNT_LOG.md adjudication spec is LOCKED and nothing here
feeds back into it. Sample definition is the survivor's own: category =
politics (`cat_group`), outcome-0 `p_24h` in [0.50, 0.95), pinned marks
excluded, split on endDate at 2025-07-01. Marks are the 2026-08-31 snapshot
(108,868 rows; tail crawl in flight), so every count below moves when the
crawl completes. Gap = realized − implied (negative = favorites overpriced).*

## Headline

n = 1,238 (train 832 / test 406). Train: bet-weighted −4.7pp,
month-weighted −6.4pp, month-t −2.37 over 16 months (the month-weighted
figure reproduces HUNT_LOG's train −6.4pp / t −2.4 / 16 months exactly).
Test: bet-weighted −3.1pp, month-t −1.79 over 7 months (HUNT_LOG snapshot:
−3.6pp / −2.1 — small drift consistent with crawl growth).

The overpricing is NOT a deadline-market story: "will X happen by DATE"
markets are almost absent from the favorites band (1 train obs, 4 test).
It is concentrated in short-lived event markets — dominated by Trump
"will he say/do X on DATE" mention markets (median lifetime 3–6 days) —
with a monotone lifetime gradient in train (−7.4pp under 7 days →
+6.7pp at 90–365 days). Long-dated election favorites are flat-to-positive
in train (+0.5pp) but negative in test (−5.1pp).

## Subtype breakdown

Subtypes classified from slug + question text, mutually exclusive,
precedence: election → nomination/confirmation → deadline → Trump-other →
other. Month-t uses month clusters with ≥5 obs (pipeline convention);
blank/nan where <2 qualifying months.

### Train (endDate < 2025-07-01; n = 832)

| subtype | n | gap (pp) | month-t | months | days-to-resolution (created→closed) |
|---|--:|--:|--:|--:|---|
| election | 198 | +0.5 | −1.99 | 10 | med 40d [q25 15, q75 93, q90 250] |
| nomination/confirmation | 2 | −29.9 | — | 0 | med 74d |
| deadline ("by DATE") | 1 | −91.5 | — | 0 | 63d |
| Trump-other | 531 | −5.9 | −1.03 | 14 | med 3d [q25 2, q75 5, q90 7] |
| other | 69 | −4.8 | −1.22 | 5 | med 7d [q25 4, q75 11, q90 61] |
| non-politics leak | 31 | −12.9 | −1.20 | 3 | med 17d [q25 4, q75 22, q90 34] |
| ALL | 832 | −4.7 | −2.37 | 16 | |
| ALL excl. leaks | 801 | −4.4 | −2.19 | 15 | |
| (mentions Trump) | 546 | −5.3 | −0.92 | 14 | |
| (no Trump mention) | 286 | −3.6 | −2.31 | 13 | |

### Test (endDate ≥ 2025-07-01; n = 406)

| subtype | n | gap (pp) | month-t | months | days-to-resolution |
|---|--:|--:|--:|--:|---|
| election | 129 | −5.1 | −0.48 | 5 | med 44d [q25 19, q75 146, q90 197] |
| nomination/confirmation | 38 | −4.4 | −0.37 | 2 | med 158d [q25 61, q75 191, q90 216] |
| deadline ("by DATE") | 4 | +5.5 | — | 0 | med 29d |
| Trump-other | 189 | −4.8 | −2.43 | 7 | med 6d [q25 4, q75 8, q90 14] |
| other | 17 | +3.9 | — | 1 | med 10d |
| non-politics leak | 29 | +12.8 | +4.53 | 3 | med 5d [q25 4, q75 117, q90 119] |
| ALL | 406 | −3.1 | −1.79 | 7 | |
| ALL excl. leaks | 377 | −4.3 | −2.36 | 7 | |
| (mentions Trump) | 192 | −4.8 | −2.44 | 7 | |
| (no Trump mention) | 214 | −1.7 | +0.57 | 6 | |

## Gap by market lifetime (created → closed)

| lifetime | train n | train gap | test n | test gap |
|---|--:|--:|--:|--:|
| 0–7d | 516 | −7.4pp | 140 | −3.1pp |
| 7–30d | 167 | −4.3pp | 133 | −5.6pp |
| 30–90d | 88 | +2.4pp | 43 | −2.4pp |
| 90–365d | 61 | +6.7pp | 90 | +0.2pp |

Train is monotone: the shorter-lived the market, the more overpriced its
favorite. Test keeps the short-vs-long direction (negative under 30 days,
~zero beyond 90) without strict monotonicity.

## Test months (pooled gaps)

| month | n | gap |
|---|--:|--:|
| 2025-07 | 39 | +1.5pp |
| 2025-08 | 17 | −17.1pp |
| 2025-09 | 65 | −1.4pp |
| 2025-10 | 40 | −0.8pp |
| 2025-11 | 89 | −2.4pp |
| 2025-12 | 1 | +15.5pp |
| 2026-05 | 78 | −2.3pp |
| 2026-06 | 77 | −6.9pp |

The Jan–Apr 2026 hole is the tail crawl still in flight — exactly the
months whose arrival triggers the locked adjudication.

## What the data says about the mechanism

The hope-premium/time-decay hypothesis (buyers of "will X happen by
DATE" markets under-discount deadline expiry) predicts the overpricing
concentrates in deadline markets. It cannot be tested in this cell:
deadline markets essentially never appear as favorites at T-24h (5 of
1,238 obs) — they live on the longshot side of these prices. What the
favorites-side data actually shows is concentration in **short-horizon
novelty/event markets** (Trump mention markets: n=720 across splits,
gap −5.9/−4.8pp, median lifetime 3–6 days; the only subtype with a
month-t ≤ −2 in test), plus a train-side lifetime gradient in the same
direction. Election favorites — the "frontrunner overpricing" of the
composition note — carry the test-side gap (−5.1pp) but were flat in
train (+0.5pp bet-weighted; their negative month-t comes from thin
months). Description, not adjudication: the survivor is better read as
"quick-resolution event favorites are overpriced, Trump events above
all" than as a deadline/time-decay effect.

## Composition caveat: classifier leaks in the cell

The politics cell is defined by `market_cats.cat_of`, whose substring
keywords admit non-politics markets: `vance` matches "Ad**vance**s"
(FIDE chess World Cup match markets) and "Thera**vance**"; `poll`
matches "A**poll**o" (earnings markets). 60 of 1,238 obs (~4.8%) are such
leaks: train −12.9pp (n=31, slightly inflating the gap), test +12.8pp
(n=29, diluting it — excluding leaks, test is −4.3pp / month-t −2.36
vs −3.1pp / −1.79 with them). The locked adjudication runs on the cell
as defined, so the leak stays in until it fires; this note is for the
paper's composition discussion and for any post-adjudication cleanup.

## Reproduction

Computed from `data/price_marks.csv.gz` + the three resolved-label files
with `study_longshot.read_gz_tolerant / load_slugs / pinned / cat_group`;
days-to-resolution = closedTime (fallback endDate) − createdAt from the
label files. Subtype regexes and the leak detector are in the analysis
script (session scratchpad, `desc_tasks.py`); month-t = mean of
equal-weighted month-cluster means / SE, clusters with ≥5 obs.
