# Is the crowd calibrated? Favorite-longshot structure in 880,000 prediction-market resolutions

*Draft v0.1 — numbers final and regenerable (`study_longshot.py`,
`study_pinned_check.py`, `backtest/oos_longshots.py`); prose is a working
skeleton.*

## Abstract

We assemble the largest calibration sample yet studied on a prediction-market
venue: 880,324 resolved Polymarket markets (2020–2026), with pre-resolution
price marks at 24, 72, and 168 hours for 90,000+ of them. The raw answer to
"does an outcome priced p win a fraction p of the time" is dominated not by
crowd psychology but by measurement artifacts, and the paper's first
contribution is their anatomy: last-trade marks across multi-outcome families
that sum far above one; marks that postdate a market's effective resolution
(22–28% of all marks) and are therefore mechanically calibrated; category
labels the venue stopped populating; and inference that treats thousands of
same-underlying, same-regime markets as independent — a day-clustered
"reverse bias" of t = −4.2 collapses to t = −0.3 when clustered by month,
having been one crash month in disguise. After the artifacts: a single
coherent signature survives — longshots are systematically overpriced across
every category group (crypto, politics, geopolitics, weather, other; 12
month-clustered cells, |t| ≥ 2, spanning 22–32 months). The bias is real,
out-of-sample, and marginally tradeable: a short-longshot rule at T-24h
clears a pre-registered evidence bar (4,000 OOS bets, PSR 0.99) at base
execution costs and fails it when slippage doubles. Prediction-market
inefficiency, where it exists at scale, is small, tail-shaped, and lives or
dies on microstructure.

## 1. Question and setting

Racetrack economics has documented the favorite-longshot bias since Griffith
(1949): longshots win less often than their odds imply. Whether modern
prediction markets inherit it is contested, and the samples in prior work are
small. Polymarket's post-2024 scale — hundreds of thousands of resolved
binary markets — permits a calibration test with actual power, but its
microstructure (thin books, multi-outcome families, early effective
resolutions) plants traps that we show dominate naive estimates.

## 2. Data and pipeline

Labels: 880,324 unique resolved markets via adaptive end-date-window sweeps
of the venue's Gamma API (its offset pagination fails past ~2,000 rows;
windows split recursively to 15-minute granularity on dense hourly-market
days). Resolution is taken from final settled prices (exactly one outcome
above 0.99). Marks: last trade price at T-24/72/168h before scheduled end,
from the CLOB price-history endpoint at 720-minute fidelity (finer fidelities
return empty on long ranges — a quirk that silently voided an early crawl and
motivated an all-empty abort guard), for the 90,758 resolved markets with at
least $5,000 volume and a lifetime long enough to have a mark. Categories:
the venue stopped populating its category field in 2022 (~4k labeled of
880k), so categories derive from a keyword classifier over slug and question
text, at 79% agreement with the legacy labels; word-boundary rules matter
("ukRAINe" is not weather). Funnel from 880k to the verdict sample: volume
and lifetime filters, empty histories, unresolved finals, and the pinned-mark
exclusion below.

## 3. The artifact layer (why naive tables lie)

**Family vig.** Multi-outcome events decompose into binary markets whose
last-trade prices need not — and do not — sum to one: mean family sum 0.97 at
T-24h but 1.39 at T-72h, reaching 1.85. An "overpricing" computed against
raw marks reproduces, to the fourth decimal, an accounting identity in the
family sum. Any calibration claim on family members must renormalize or use
executable quotes.

**Pinned afterlife marks.** Markets resolve when events resolve, not when
their scheduled end arrives: for 22–28% of marks (by horizon), the venue's
`closedTime` precedes the mark time, so the "price" is a post-resolution
print pinned at 0.99 or 0.01 — mechanically perfectly calibrated. These
marks manufactured an apparent *underpricing of favorites* (they are
winners priced 0.99) that vanishes on exclusion, and — because pinned marks
are calibrated — diluted every real miscalibration toward zero. Two of the
four cells in our own interim verdict died this way; we report that
correction as a result, not a footnote.

**Regime clustering.** 477 crypto-favorite observations across 131
(underlying × day) clusters showed realized minus implied of −12.8pp,
t = −4.2. Clustered by (underlying × month): t = −0.33. The entire effect was
November 2025 — a crash month in which every "will BTC be above X" favorite
failed together; December's rebound shows +18pp. Prediction markets sharing
an underlying inherit its regimes; month-level clustering is the minimum
honest unit, and our verdict rule requires ≥6 cluster-months and ≥2 category
groups.

**Weighting.** Month-clustered means weight thin months equally with busy
ones. An interim crypto-favorites gap of +5pp (month-weighted) was +0.6pp
bet-weighted — below any cost model — because the effect lived in low-volume
months. Kish effective cluster counts are reported for every cell (one
headline cell's 16,236 observations amount to 6.2 effective months); a bias
is only tradeable if it survives the weighting money actually experiences.

## 4. The de-pinned result: longshots are overpriced everywhere

With pinned marks excluded and month-clustered inference, 12 cells clear
|t| ≥ 2 across five category groups — and every one points the same way:

| horizon | group | side | gap | t | months | Kish | n |
|---|---|---|--:|--:|--:|--:|--:|
| 24h | crypto | longshots | −5.3pp | −3.4 | 26 | 5.9 | 3,379 |
| 24h | politics | favorites | −4.9pp | −2.5 | 22 | 11.5 | 1,165 |
| 24h | weather | longshots | −4.5pp | −3.9 | 14 | 8.0 | 3,477 |
| 24h | weather | favorites | −20.3pp | −2.8 | 9 | 7.1 | 87 |
| 24h | other | longshots | −2.2pp | −2.1 | 32 | 8.2 | 5,389 |
| 72h | crypto | longshots | −3.4pp | −2.4 | 27 | 5.4 | 4,635 |
| 72h | crypto | favorites | −7.1pp | −2.1 | 21 | 5.7 | 3,463 |
| 72h | politics | longshots | −1.9pp | −2.3 | 27 | 14.9 | 1,785 |
| 72h | weather | longshots | −8.8pp | −4.2 | 12 | 9.8 | 456 |
| 168h | crypto | longshots | −5.4pp | −4.2 | 26 | 20.2 | 552 |
| 168h | politics | longshots | −2.9pp | −2.5 | 27 | 14.6 | 1,232 |
| 168h | geopolitics | longshots | −3.8pp | −2.7 | 25 | 14.2 | 514 |

Realized frequency sits below implied probability throughout: buyers of
low-probability outcomes overpay — the classic favorite-longshot signature,
cross-category and multi-horizon. (Negative "favorites" cells are consistent
with the same story on the complement side and with residual family-vig;
the longshot cells carry the weight of evidence.)

## 5. Out of sample, with money's weighting

Protocol (identical to the one that killed the crypto-favorites candidate):
train per-category gaps on resolutions before 2025-07-01, freeze, test
after; pinned marks excluded on both sides; one bet per market-horizon; taker
fee at the venue's worst category rate; the trade is buying the complement
(NO) whenever outcome-0 is priced in [0.03, 0.35).

T-24h: bet-weighted OOS gap −1.77pp (n = 4,000, 157 days). Through a
bet-level engine (fractional Kelly, 2% per-market cap, 25% daily exposure
cap, fees, 100bps slippage): +68%, annualized Sharpe 3.93, PSR 0.99 — the
first strategy in this project to pass its pre-registered evidence bar (≥300
bets, ≥120 days, PSR ≥ 0.95). The P&L is broad, not event-driven: Kish
effective day-count 102 of 157; the five largest days contribute 6%.
Deflated for the twelve strategy variants tried in the project's history:
DSR 0.81. Doubling slippage to 200bps yields SR 1.97 and PSR 0.90 — below
the bar. T-72h fails outright (−0.7pp bet-weighted): the bias, where
tradeable, is a last-day phenomenon.

The honest statement: a broad, out-of-sample longshot-overpricing edge
exists at T-24h whose economics are decided by execution costs in the
100–200bps range — and our entry prices are still last-trade marks. A
forward experiment at live executable quotes (recording the NO ask and depth
for every market entering the trade window, self-grading at resolution) is
running and is the registered decisive test.

## 6. Interpretation

Where the crowd is measurable at scale, it is far better calibrated than
folk accounts of retail prediction markets suggest: mid-range prices are
nearly unbiased in every liquid category; a bias-corrected D-1 GFS+ECMWF
forecast loses to the weather crowd's own prices (log-loss 0.388 vs 0.360, a
companion result); and the largest apparent miscalibrations in our own
interim analyses were, one after another, instruments lying. What survives
is thin, concentrated in tails, strongest in the final day, and consistent
with lottery-preference demand meeting inventory-averse liquidity provision.
The methodological ledger — seven documented ways a prediction-market
backtest fabricates edge — may be the more durable contribution.

## 7. What would change our minds

Pre-registered: (i) the forward live-quote experiment failing to reproduce a
positive net edge at real asks over ≥120 days; (ii) the bias failing
bet-weighted in the 2026 tail sample now being marked; (iii) an execution
study showing effective tail spreads persistently above 200bps, which prices
the anomaly as compensation rather than error.

## References (to finalize)

Griffith (1949); Thaler & Ziemba (1988); Snowberg & Wolfers (2010); Stoll
(2000); Harvey (2017); Bailey & López de Prado (2014); Dubach (2026)
arXiv:2604.24366; Polymarket API documentation.
