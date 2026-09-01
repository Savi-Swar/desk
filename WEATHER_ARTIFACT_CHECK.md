# Weather outcome-0 "overpricing": artifact check

2026-08-31. Question: Study 1 (`study_longshot.py`) found Polymarket weather markets'
outcome-0 resolving ~12pp below price for favorites at T-24h (t=-2.6) and ~6pp below
for longshots at T-72h — both sides negative, suggesting an outcome-0-specific
artifact. Is it real?

**Verdict: mostly artifact, with one real residual structure.** The headline gap is
(a) diluted by a category-tagging bug, (b) dominated by a marks-construction artifact
— last-trade price marks across a negRisk bucket family sum to well over 1, so every
"Yes" leg shows a mechanical negative gap that is not sellable at those prints. After
removing the family vig (renormalizing prices to sum to 1), the uniform "outcome-0
overpriced" effect disappears and is replaced by a classic **within-family
favorite-longshot pattern**: both temperature tails overpriced ~2.6x, middle buckets
underpriced +1.6pp (t=+3.5). Separately, a **price-free warm-side drift in outcomes
is real**: the high tail busts 3x as often as the low tail (t=+3.0), and it is only
partially priced.

Scripts (scratchpad, session-local): weather_check.py / _check2 / _check3 / _check4.
Inputs: `data/price_marks.csv.gz` (70,161 rows, 0 duplicate ids), label files
`resolved_markets.csv.gz` + `resolved_tail*.csv.gz` (880,324 ids; tail2 has a
truncated final member, read tolerantly).

---

## 1. What outcome-0 actually is

Every weather row is a **binary** market with `outcomes = ["Yes","No"]` (3,037 of
3,042 strict-weather rows; the 5 exceptions are Tulsa Golden Hurricane basketball
games leaking through the "hurricane" keyword). `winner_idx` semantics verified
against `final_prices` (winner_idx=1 ⇔ final ≈ [0,1]). So **outcome-0 = "Yes" on one
temperature-bucket statement** ("highest temperature in NYC between 51-52°F on
Nov 22"), one leg of a negRisk family (negRisk=1 for 3,014/3,042 rows). Theme split:
temperature 2,993, storms 37, precip 12.

## 2. Category contamination (bug in `market_cats.py`)

The weather rule matches substrings "rain", "snow", "heat" — which hit
"uk**rain**e", "t**rain**", "ref**rain**", "**Snow**den". Of 3,559 joined "weather"
marks, **517 (14.5%) are contaminants** — almost all Ukraine/Russia geopolitics,
plus How to Train Your Dragon box-office and a Snowden-pardon market.

Replication of Study 1's cells, old set vs contaminant-only vs strict weather
(gap = mean(1{outcome0 won} − p), month clusters, ≥5 obs/cluster):

| cell | OLD (contaminated) | contaminant only | strict weather |
|---|---|---|---|
| T-24h favorites (.5–.98) | −.119, t=−2.6 (13mo, n=256) | −.053, t=−1.3 (10mo, n=169) | −.198, t=−2.7 (9mo, n=87) |
| T-72h longshots (.02–.5) | −.064, t=−2.3 (16mo, n=636) | −.014, t=−0.5 (10mo, n=176) | −.090, t=−4.3 (12mo, n=460) |
| T-24h longshots | −.029, t=−1.4 | +.010, t=+0.4 | −.051, t=−4.5 (13mo, n=2,542) |

The contaminant shows no effect; it **diluted** the weather signal rather than
creating it. Fix worth making: word-boundary matching in `market_cats.py`.

## 3. Bucket-type split (the original hypothesis)

Classifying strict-weather markets from slug/question text: below-bucket ("X°F or
below") 460, above-bucket ("or higher") 548, exact/middle ("between 45-46°F") 2,034.

Month-clustered gap on raw marks, all 0<p<1 (`*` = ≥6 clusters and |t|≥2):

| horizon | below | above | exact |
|---|---|---|---|
| T-24h | −.056, t=−5.1, n=460 * | −.038, t=−2.2, n=548 * | −.044, t=−3.8, n=2,034 * |
| T-72h | −.151, t=−6.9, n=95 * | −.100, t=−2.9, n=94 * | −.079, t=−6.4, n=383 * |
| T-168h | n/a (1 month) | n/a | −.022, t=−1.1, n=92 |

**All three bucket types are negative** — the effect is NOT concentrated in a low-tail
or high-tail bucket type. That kills the "outcome-0 encodes the cold bucket"
hypothesis and points at a family-level mechanism instead.

## 4. The dominant artifact: family price sums ≫ 1 in the marks

Reconstructed 596 temperature families (city × date × high/low) from slugs; the full
label universe has 764 families, standard size 7 buckets (676 complete 7-bucket
families with exactly one Yes winner).

At T-24h, among 545 families with ≥2 priced buckets in the marks data:
- mean buckets priced per family: 5.20 (of 6.69 existing — $5k volume filter drops the rest)
- **mean Σp over priced buckets: 0.974; median 1.016** — despite covering only ~72%
  of buckets and only 69.2% of families containing the winning bucket
- scaled to a full 7-bucket family this implies Σp ≈ 1.25–1.4; one fully-priced
  example (NYC highest, Nov 22) sums to **1.845** at T-24h
- at T-72h (76 families): mean Σp = **1.393** over 5.55 priced buckets

Accounting identity check: per-row gap = (P(winner in sample) − E[Σp]) / k =
(0.692 − 0.974)/5.20 = **−0.0542** vs observed −0.0553 at T-24h; at T-72h
(0.697 − 1.393)/5.55 = **−0.1253** vs observed −0.1244. The raw "calibration gap"
is fully reproduced by the family price sum exceeding the family win coverage.

Why Σp > 1: `fetch_price_marks.py` marks each leg at the **last trade at-or-before
T−h with fidelity=720 (12h bars)** from `prices-history`. Legs of a family trade at
different times; a dying bucket's last print is from when it was still live (and
retail lifts asks on lottery legs), so cross-sectional sums of last-trade prints run
well above the simultaneous book. Only 1.4% of rows have p_24h == p_72h, so this is
not multi-day staleness — it is intra-day/last-print asymmetry plus ask-side prints.
**You cannot sell at these prices**, so the raw gap is not an edge estimate.
Winner-bucket missingness is roughly random (winner present 69.2% vs 72.3% expected
from bucket coverage), so the $5k volume filter is a minor secondary effect.

## 5. What survives after removing the vig

Renormalizing each family's marks to q = p/Σp (families with ≥6 priced buckets and
winner present; 239 families at T-24h) and re-running month-clustered gaps by bucket
position:

| position | n | mean q | win rate | clustered gap | t |
|---|---|---|---|---|---|
| low tail | 223 | .048 | .018 | −.032 | −1.8 (10mo) |
| middle | 1,129 | .189 | .204 | **+.016** | **+3.5** (11mo) |
| high tail | 236 | .065 | .025 | −.046 | **−3.2** (10mo) |

T-72h (48 families, weaker): mid +.029 t=+3.6; tails ≈−.06, t=−1.0/−1.4 (few months).

So vig-free, the structure is a **within-family favorite-longshot bias**: both tails
priced ~2.6–2.7x their realized win rate (low .048→.018, high .065→.025 — the
overpricing RATIO is symmetric), middle buckets underpriced by ~1.6pp. This is real
structure but small per contract, and renormalization strips the very vig you would
pay to trade it — economic viability requires a book-level backtest, not marks.

## 6. Real directional finding: warm-side drift in outcomes (price-free)

Across all 676 complete 7-bucket families (no prices involved — pure resolution
frequencies by bucket position, ordered cold→warm):

| position | low tail | mid1 | mid2 | mid3 (center) | mid4 | mid5 | high tail |
|---|---|---|---|---|---|---|---|
| win freq | .022 | .032 | .178 | .308 | .253 | .141 | .064 |

- Winner lands **above** the center bucket 45.8% vs **below** 23.2% — a 2:1 warm skew
  relative to where Polymarket centers the bucket ladder.
- **P(high-tail busts) − P(low-tail busts) = +4.4pp, month-clustered t=+3.0 (15
  months)** — high tail busts 6.4% vs low tail 2.2%, i.e. 3x.
- By city: NYC families bust warm 7–16% of the time vs London 2% — the drift is
  concentrated in US-listed NYC ladders.

Markets partially price this (high tail q=.065 vs low tail q=.048), and the residual
tail overpricing ratio is symmetric — so the naive trade "buy the warm tail" is NOT
supported; the drift is in outcomes vs ladder placement, not in net-of-price edge.
The supported directional statement: **the bucket ladders are systematically placed
cold** (or the source forecasts under-call daily highs), and middle-to-upper-middle
buckets carry the underpricing.

## 7. Conclusions

1. **Artifact, primarily.** The Study 1 weather cells fail as calibration evidence:
   the uniform outcome-0 negative gap is an accounting consequence of last-trade
   marks summing above 1 across negRisk families (plus 14.5% category contamination
   that happened to dilute it). Do not treat raw marks-based gaps as sellable edge
   on any negRisk family — this caveat applies beyond weather.
2. **Real structure #1 (weak-moderate):** within-family longshot bias — tails ~2.6x
   overpriced vig-free, middles +1.6pp underpriced (t=+3.5, 11 months). Candidate
   trade: buy middle buckets / structurally avoid tails. Needs order-book-level
   verification before sizing; the vig may consume it.
3. **Real structure #2 (solid, price-free):** warm-side outcome drift — winners land
   above ladder center 2:1, high tail busts 3x the low tail (t=+3.0, 15 months),
   NYC ≫ London. Not directly tradeable as "buy warm" (prices partially adjust),
   but useful as a prior for any weather model: center forecasts warm of the ladder.
4. **Fixes:** (a) word-boundary keywords in `market_cats.py` ("rain" currently
   matches "ukraine"); (b) any future calibration study on negRisk families should
   renormalize by family Σp or use simultaneous book snapshots, not per-leg
   last-trade history.
