# Horizon persistence: does the mispricing survive the approach to resolution?

*2026-08-31. Descriptive study for Paper 1's interpretation section — NO
trading rules, no engine, no parameter tuning. Question: is the T-168h
price's error still there at T-72h and T-24h, or does the market converge
as resolution approaches?*

*Snapshot caveat: the marks tail-crawl was appending DURING this run — the
file grew from 110,969 to 111,438 rows across the three reads of this
session. Headline tables below are from the 111,192-row read (universe
29,022); a re-read minutes later gave universe 29,053 with all conclusions
unchanged to the reported precision. Every count moves when the crawl
completes.*

## Universe

Resolved markets with **all three** horizon marks (`p_24h`, `p_72h`,
`p_168h`) present and in (0,1), **unpinned at each respective horizon**
(`pinned(r, h)` evaluated per horizon), volume ≥ 5k (the marks file is
already volume-filtered; min volume in universe = 5,000). Categories via
`cat_group` (label join). Month-clustered t's use the pipeline convention:
clusters = endDate month, months with ≥ 5 obs kept; "mw" = mean of month
means, "raw" = pooled mean. Gap = won − p (negative = overpriced).

n = 29,022 of 111,192 raw rows. Dropped: 61,267 missing/invalid a mark
(mostly markets that lived < 7 days and so have no T-168h mark — see the
selection caveat in §4), 20,903 pinned at ≥ 1 horizon, 0 for volume.

**The 168h-mark requirement conditions the whole study on lifetime ≥ 7
days.** Short-lived markets — including the Trump mention markets that
dominate the politics-favorites survivor cell (SURVIVOR_PROFILE.md: median
lifetime 3–6 days) — are outside this universe by construction. Results
speak to *long-lived* markets only.

## 1. Convergence: the longshot gap decays to ~zero by T-24h

Longshot band = p ∈ [0.03, 0.35) **at the respective horizon** (so the set
changes across horizons; §2 holds the set fixed).

| group | n (univ) | mean \|p24−p168\| | med | gap@168h (mw, t, mo, n) | gap@72h | gap@24h |
|---|--:|--:|--:|---|---|---|
| sports | 6,575 | .066 | .025 | +.007 (t +0.5, 21mo, 3032) | +.026 (t +2.6, 18mo, 3454) | +.008 (t +0.5, 18mo, 3473) |
| esports | 408 | .059 | .035 | +.054 (t +0.8, 2mo, 76) | +.043 (t +0.5, 2mo, 90) | −.025 (t −3.7, 2mo, 92) |
| crypto | 1,495 | .098 | .019 | **−.076 (t −5.6, 27mo, 415)** | **−.068 (t −6.0, 22mo, 348)** | −.033 (t −1.4, 14mo, 214) |
| politics | 4,087 | .050 | .010 | −.014 (t −1.1, 25mo, 1140) | −.024 (t −1.8, 25mo, 1008) | −.006 (t −0.4, 23mo, 880) |
| econ | 648 | .052 | .015 | **−.051 (t −2.8, 12mo, 198)** | −.010 (t −0.3, 11mo, 181) | −.030 (t −0.9, 11mo, 151) |
| geopolitics | 1,131 | .066 | .020 | **−.048 (t −3.7, 23mo, 482)** | **−.033 (t −2.2, 15mo, 405)** | −.017 (t −1.1, 13mo, 320) |
| weather | 175 | .073 | .030 | −.051 (2mo, 54) | −.153 (2mo, 42) | −.045 (1mo, 34) |
| culture | 1,148 | .079 | .024 | **+.032 (t +2.5, 12mo, 502)** | +.000 (11mo, 341) | +.007 (10mo, 204) |
| other | 13,355 | .079 | .034 | −.005 (t −0.5, 30mo, 4544) | +.004 (29mo, 4971) | +.022 (t +1.8, 28mo, 4731) |
| **ALL** | **29,022** | **.072** | **.025** | **−.028 (t −4.0, 35mo, 10,443)** | **−.025 (t −3.2, 34mo, 10,840)** | **−.006 (t −0.7, 32mo, 10,099)** |

The pooled longshot overpricing is real a week out (mw −2.8pp, t = −4.0)
and essentially **gone by 24h** (−0.6pp, t = −0.7). The path 168→72→24 is
−2.8 → −2.5 → −0.6: most of the decay happens in the last two days. It is
carried by crypto and geopolitics (and econ at 168h); none of the
significant-at-168h cells stays significant at 24h. Esports/weather t's sit
on ≤ 2 cluster-months — ignore them. Prices themselves move: mean
|p24 − p168| = 0.072 universe-wide (median 0.025 — the mean is fat-tailed).

## 2. Within-market persistence: the 168h gap does NOT predict a 24h gap

Contingency for the 10,443 markets longshot-priced at 168h, by their 24h
price:

| at 24h | n | share | mean p168 | mean p24 | win rate | fair? |
|---|--:|--:|--:|--:|--:|---|
| still longshot [0.03,0.35) | 7,514 | 72.0% | .196 | .173 | .181 | ≈ p24 |
| exited below 0.03 | 2,149 | 20.6% | .087 | .012 | .008 | ≈ p24 |
| exited above 0.35 | 780 | 7.5% | .255 | .494 | .479 | ≈ p24 |

Conditional on the 24h price, every path cell resolves close to that
price. Month-clustered 24h gaps:

| set | n | raw | mw | t | months |
|---|--:|--:|--:|--:|--:|
| still-longshot-at-24h (LS at both 168h & 24h) | 7,514 | +.008 | −.005 | −0.5 | 31 |
| ALL 24h longshots | 10,099 | +.012 | −.006 | −0.7 | 32 |
| fresh 24h longshots (not LS at 168h) | 2,585 | +.023 | −.017 | −1.1 | 24 |

Being overpriced-band at 168h carries **no** residual 24h miscalibration:
the still-longshot subset is indistinguishable from the full 24h longshot
set (−0.5pp vs −0.6pp, both t ≈ −0.5). Per-category still-longshot 24h
gaps: the only cells that keep sign and significance are **crypto**
(mw −6.2pp, t −2.9, n = 124, 9mo) and **econ** (mw −5.6pp, t −2.2,
n = 124, 11mo) — small n, but consistent with §1's crypto being the
slowest-converging category. Sports +0.0 (t −0.1, n 2,738), politics +1.0pp
(t +0.6, n 710), other +2.3pp (t +1.6, n 3,314).

## 3. Price-path direction: dying longshots get marked about halfway down

Among the 10,443 168h longshots (overall win rate .168 vs mean p168 .178):

| drift by 24h (Δ = p24 − p168) | n | share | win rate | mean p168 → p24 | 24h gap |
|---|--:|--:|--:|---|--:|
| UP (Δ > +0.005) | 3,195 | 30.6% | .288 | .198 → .285 | +.003 |
| DOWN (Δ < −0.005) | 6,428 | 61.6% | .107 | .169 → .103 | +.004 |
| flat | 820 | 7.9% | .173 | .167 → .167 | +.007 |

Direction is informative (up-drifters win 2.7x as often as down-drifters)
but the *destination* price is calibrated in every direction cell — the
drift itself is the correction.

By eventual outcome:

| outcome | n | mean p168 → p24 | med p24 | p24 < 0.03 | sticky (p24 ≥ p168 − .01) | drifted up |
|---|--:|---|--:|--:|--:|--:|
| losers | 8,693 | .166 → .138 | .105 | 24.5% | 42.4% | 26.2% |
| winners | 1,750 | .237 → .291 | .265 | 1.0% | 69.8% | 52.6% |

Dying longshots do **not** glide smoothly to zero: only a quarter are below
0.03 by 24h, and 42% haven't moved down at all a day before resolution.
But — combined with the direction table — this stickiness is not
mispricing: the residual price at 24h is fair for the residual
uncertainty, and resolution itself does the final markdown. The market's
job at the tails is mostly done by 24h (consistent with §1's gap decay).

## 4. The politics-favorites survivor cell: an event-window phenomenon (in this universe)

**Selection caveat first.** This universe's 168h-mark requirement keeps
only 455 of the survivor cell's ~1,238 markets (SURVIVOR_PROFILE.md
2026-08-31 snapshot): the excluded majority are exactly the short-lived
Trump mention markets (median lifetime 3–6 days) where the overpricing is
concentrated, per the survivor profile's lifetime gradient. Everything
below describes the **long-lived (≥ 7 day) slice** of the cell.

**(a) Same-markets view** — cell defined at 24h (politics, p24 ∈
[0.50, 0.95), n = 455, win rate .721), gap measured against that market's
own price at each horizon:

| horizon | mean p_h | raw gap | mw gap | t | months |
|---|--:|--:|--:|--:|--:|
| T-168h | .672 | +.049 | +.035 | +1.08 | 19 |
| T-72h | .709 | +.012 | −.009 | −0.29 | 19 |
| T-24h | .742 | −.021 | −.042 | −1.46 | 19 |

The 24h overpricing does **not** exist a week out. For the identical
markets, the 168h price sits *below* the eventual win rate (+3.5pp, n.s.);
the gap turns negative only because the price drifts **up** ~7pp into
resolution while the win rate is fixed. Decisively: eventual **losers** in
this cell drift up too — mean .573 → .611 → .668 (n = 127) — the wrong
direction, while winners go .710 → .747 → .771 (n = 328). The overpricing
is created in the final ~3 days: a last-day run-up that overshoots. The
24h point estimate (mw −4.2pp) matches the full survivor cell's magnitude
(−4.7pp bet-weighted / −6.4pp month-weighted, HUNT_LOG/SURVIVOR_PROFILE)
but is not significant at n = 455 / 19 months on its own.

Where the 24h cell was priced at 168h: 78.7% already in [0.50, 0.95),
19.6% below 0.50, 1.8% above.

**(b) Respective-horizon view** — cell re-defined at each horizon:

| horizon | n | raw gap | mw gap | t | months |
|---|--:|--:|--:|--:|--:|
| T-168h | 509 | −.027 | −.074 | −2.37 | 22 |
| T-72h | 457 | −.018 | −.057 | −1.88 | 19 |
| T-24h | 455 | −.021 | −.042 | −1.46 | 19 |

Read naively this says "politics favorites are overpriced at every
horizon, worst a week out." But decomposing the 168h cell by 24h
destination shows the 168h overpricing lives in **different markets**:

| 168h cell (n = 509) by 24h position | n | win rate | p168 → p24 | gap@168 raw | mw | t | months |
|---|--:|--:|---|--:|--:|--:|--:|
| still in [0.50,0.95) | 358 | .771 | .747 → .765 | +.024 | −.011 | −0.3 | 16 |
| fell below 0.50 | 94 | .309 | .592 → .278 | −.284 | −.341 | −3.8 | 7 |
| rose ≥ 0.95 | 57 | .947 | .876 → .967 | +.071 | +.122 | (2mo) | 2 |

The whole 168h-cell overpricing is carried by the ~18% of favorites that
subsequently collapse out of the band (win 30.9% vs p168 .592). Markets
still favorites at 24h were essentially fairly priced at 168h (−1.1pp,
t −0.3, and in-band-at-all-three-horizons markets show mw −0.6/−1.7/−1.8pp,
all |t| < 0.5, n = 334).

**(c) Test period** (endDate ≥ 2025-07-01, cell at 24h, n = 229): same
shape — gap vs p168 +1.2pp, vs p72 −1.2pp, vs p24 −4.9pp (mw; t −0.91,
6 months). The last-day emergence replicates out-of-sample in sign,
underpowered alone.

**For the paper:** within long-lived markets, the survivor cell's 24h
overpricing is an **event-window phenomenon** — it appears in the final
day(s) as prices (losers included) run up toward resolution — not a
misjudgment already embedded a week out. The complementary 168h-horizon
overpricing among favorites-that-die is a different animal (slow markdown
of collapsing favorites, cousin of §3's stickiness). Whether the dominant
short-lived (< 7d) mention markets behave the same way is **unanswerable
from this marks file**: they have no 168h price to compare. Their entire
lifetime *is* the event window, which is itself consistent with the
event-window reading.

## Reproduction

Script: session scratchpad `horizon_persistence.py` (imports
`read_gz_tolerant`, `load_slugs`, `pinned`, `cat_group` from
`study_longshot.py`); run from the repo root against
`data/price_marks.csv.gz`. All numbers regenerate from the marks snapshot;
expect small drifts while the tail crawl completes.
