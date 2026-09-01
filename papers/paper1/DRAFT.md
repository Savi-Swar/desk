# Is the crowd calibrated? Favorite-longshot structure in 880,000 prediction-market resolutions

*Draft v0.2 — numbers refreshed 2026-08-31 against the regenerated pipeline
(`study_longshot.py`, `study_pinned_check.py`, `backtest/oos_longshots.py`);
the marks tail crawl is still appending 2026 months, so mark counts move;
prose is a working skeleton.*

## Abstract

We assemble the largest calibration sample yet studied on a prediction-market
venue: 880,326 resolved Polymarket markets (2020–2026), with pre-resolution
price marks at 24, 72, and 168 hours for 190,000+ of them. The raw answer to
"does an outcome priced p win a fraction p of the time" is dominated not by
crowd psychology but by measurement artifacts, and the paper's first
contribution is their anatomy: last-trade marks across multi-outcome families
that sum far above one; marks that postdate a market's effective resolution
(13–28% of marks, by horizon) and are therefore mechanically calibrated; category
labels the venue stopped populating; and inference that treats thousands of
same-underlying, same-regime markets as independent — a day-clustered
"reverse bias" of t = −4.2 collapses to t = −0.3 when clustered by month,
having been one crash month in disguise. After the artifacts: a single
coherent signature survives — longshots are systematically overpriced across
every category group (crypto, politics, geopolitics, weather, other; 13
month-clustered cells, |t| ≥ 2, spanning 11–33 months). The bias is a robust
statistical description of history; it is not, so far, a strategy. A
short-longshot rule at T-24h briefly cleared a pre-registered evidence bar
(4,000 OOS bets, PSR 0.99) and was retracted when two registered falsifiers
fired: the 2026 tail sample reversed the gap, and the engine's daily
exposure cap was itself reweighting P&L toward sparse days. One candidate —
politics favorites, overpriced on both sides of a train/test split and in
both marked 2026 months — was adjudicated by its pre-registered automated rule
on the full 2026 sample and failed (direction persistent at −2.0pp, but
month-t −1.35 and PSR 0.81, below the locked bars); a forward experiment at live executable quotes is the arbiter.
Prediction-market inefficiency, where it exists at scale, is small,
tail-shaped, and lives or dies on microstructure.

## 1. Question and setting

Racetrack economics has documented the favorite-longshot bias since Griffith
(1949): longshots win less often than their odds imply. Whether modern
prediction markets inherit it is contested, and the samples in prior work are
small. Polymarket's post-2024 scale — hundreds of thousands of resolved
binary markets — permits a calibration test with actual power, but its
microstructure (thin books, multi-outcome families, early effective
resolutions) plants traps that we show dominate naive estimates.

## 2. Data and pipeline

Labels: 880,326 unique resolved markets via adaptive end-date-window sweeps
of the venue's Gamma API (its offset pagination fails past ~2,000 rows;
windows split recursively to 15-minute granularity on dense hourly-market
days). Resolution is taken from final settled prices (exactly one outcome
above 0.99). Marks: last trade price at T-24/72/168h before scheduled end,
from the CLOB price-history endpoint at 720-minute fidelity (finer fidelities
return empty on long ranges — a quirk that silently voided an early crawl and
motivated an all-empty abort guard), for the 191,393 resolved markets (after a 12-shard distributed CI crawl completed the backfill) with at
least $5,000 volume and a lifetime long enough to have a mark (final canonical dataset). Categories:
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
their scheduled end arrives: for 13–28% of marks (by horizon), the venue's
`closedTime` precedes the mark time, so the "price" is a post-resolution
print pinned at 0.99 or 0.01 — mechanically perfectly calibrated. These
marks manufactured an apparent *underpricing of favorites* (they are
winners priced 0.99) that vanishes on exclusion, and — because pinned marks
are calibrated — diluted every real miscalibration toward zero. Three of the
six cells in our own interim verdict died this way; we report that
correction as a result, not a footnote.

**Regime clustering.** The worked example, regenerated from the current
crawl (crypto favorites: outcome-0 priced [0.60, 0.98) at T-72h, pinned
marks still *included* — the pre-filter world in which the interim mistake
was made): 1,801 observations across 721 (underlying × day) clusters show
realized minus implied of −4.3pp, t = −3.2. Clustered by
(underlying × month): 122 clusters, t = −0.1. The effect is the late-2025
crash regime, in which every "will BTC be above X" favorite failed together
— November 2025 alone shows −25.3pp across 284 observations, October
−7.2pp — and December's rebound shows +14pp. (An earlier, smaller crawl put
the same collapse at t = −4.2 → −0.3; the counts here supersede it.)
Prediction markets sharing an underlying inherit its regimes; month-level
clustering is the minimum honest unit, and our verdict rule requires ≥6
cluster-months and ≥2 category groups. The artifacts also compound: with
pinned marks excluded, December's 35 crypto-favorite marks vanish entirely
— every one is an afterlife print, so the "rebound" month is manufactured
by already-resolved markets — and what remains is overpriced even
month-clustered (−11.4pp, t = −3.4 by underlying × month; the corresponding
§4 cell, clustered by month alone, reads −7.3pp, t = −2.2). The clean
collapse-to-zero lives only in the pinned-included world.

**Weighting.** Month-clustered means weight thin months equally with busy
ones. An interim crypto-favorites gap of +5pp (month-weighted) was +0.6pp
bet-weighted — below any cost model — because the effect lived in low-volume
months. Kish effective cluster counts are reported for every cell (one
headline cell's 8,910 observations amount to 3.8 effective months); a bias
is only tradeable if it survives the weighting money actually experiences.

## 4. The de-pinned result: longshots are overpriced everywhere

With pinned marks excluded and month-clustered inference, 13 cells clear
|t| ≥ 2 across five category groups — and every one points the same way:

| horizon | group | side | gap | t | months | Kish | n |
|---|---|---|--:|--:|--:|--:|--:|
| 24h | crypto | longshots | −4.4pp | −3.3 | 32 | 11.3 | 7,079 |
| 24h | politics | favorites | −4.4pp | −2.7 | 28 | 17.4 | 1,686 |
| 24h | weather | longshots | −3.4pp | −3.3 | 20 | 5.5 | 13,621 |
| 72h | crypto | longshots | −3.3pp | −2.8 | 33 | 10.5 | 10,225 |
| 72h | crypto | favorites | −5.7pp | −2.1 | 27 | 10.2 | 5,270 |
| 72h | politics | longshots | −1.5pp | −2.2 | 32 | 18.6 | 3,135 |
| 72h | weather | longshots | −6.8pp | −4.1 | 19 | 5.1 | 1,633 |
| 72h | other | longshots | −1.7pp | −2.0 | 37 | 9.8 | 21,743 |
| 72h | esports | longshots | **+4.9pp** | +2.3 | 12 | 4.4 | 1,443 |
| 168h | crypto | favorites | −7.9pp | −2.9 | 16 | 5.1 | 329 |
| 168h | politics | longshots | −2.5pp | −2.4 | 32 | 15.7 | 2,491 |
| 168h | geopolitics | longshots | −3.2pp | −2.6 | 30 | 12.8 | 1,345 |
| 168h | weather | longshots | −6.2pp | −3.2 | 15 | 11.7 | 157 |

Twelve of thirteen cells point one way — buyers of low-probability outcomes
overpay. The exception is new in the full sample: esports longshots at T-72h
run UNDERpriced (+4.9pp), but on 12 months with Kish 4.4 and only 8
pre-split training observations the standard harness refuses an
out-of-sample test; the forward live-quote experiment covers the band and
will adjudicate it. For the twelve: — the classic favorite-longshot signature,
cross-category and multi-horizon. (Negative "favorites" cells are consistent
with the same story on the complement side and with residual family-vig;
the longshot cells carry the weight of evidence.)

## 5. Out of sample, with money's weighting — and a retraction

Protocol (identical to the one that killed the crypto-favorites candidate):
train per-category gaps on resolutions before 2025-07-01, freeze, test
after; pinned marks excluded on both sides; one bet per market-horizon; taker
fee at the venue's worst category rate; the trade is buying the complement
(NO) whenever outcome-0 is priced in [0.03, 0.35).

The first pass looked like the project's first quotable strategy. T-24h:
bet-weighted OOS gap −1.77pp (n = 4,000, 157 days); through a bet-level
engine (fractional Kelly, 2% per-market cap, 25% daily exposure cap, fees,
100bps slippage): +68%, annualized Sharpe 3.93, PSR 0.99 — past the
pre-registered evidence bar (≥300 bets, ≥120 days, PSR ≥ 0.95), with broad
P&L (Kish effective day-count 102 of 157; top-5 days 6%) and DSR 0.81 after
deflating for the twelve strategy variants tried. T-72h failed outright
(−0.7pp bet-weighted).

That claim is retracted. Two pre-registered falsifiers fired within hours
of each other:

1. **The 2026 tail sample reversed the gap.** The May–June 2026 test months
show +2.2 to +2.4pp — longshots winning *more* than priced — dominated by
weather families whose warm-side ladder drift runs opposite to generic
longshot bias; ex-weather the 2026 gap is +4.6pp, also reversed.
Bet-weighted across the enlarged test set: +0.6pp. The pooled trade does
not survive 2026.

2. **Mirage #8: day-budget reweighting.** The engine's daily exposure cap
scales bets down on crowded days and leaves sparse days at full size, so
its Sharpe is closer to an equal-day average than an equal-bet one: the
weather-2026 stream is −3.28c/share equal-weight yet printed +150% under
the cap. The engine now has a flat-fraction mode, and the standing rule is
that a strategy result is claimable only when the capped and flat modes
agree on sign; on the enlarged sample they agree only ex-weather, where the
sign is negative. The SR 3.93 was measured under the capped mode on the
smaller window and is retracted as a strategy claim, not merely weakened.

A subsequent one-night, six-candidate pre-registered hunt (family
middles-vs-tails, live-ask set-arb, forecast-conditioned warm buckets,
cross-venue ETH basis, sports moneyline dogs, politics longshots) left one
pending survivor: **politics favorites are overpriced** (sell side). Train
(<2025-07): −6.4pp, t = −2.4 (16 months). Test: bet-weighted −3.6pp,
month-t −2.1 (7 months); both engine sizing modes agree positive (capped SR
+2.3, flat +2.4); survives slippage at 100/200/300bps; held in both marked
2026 months (−7.3pp, −6.9pp) — the only category whose edge survived 2026.
Composition: Trump/election frontrunner overpricing (176+108 of 354 bets),
consistent with documented political-market behavior. It is *not* claimed:
PSR 0.88/0.91 < 0.95, 7 test months < 8, and top-5-day concentration is
142% of flat-mode P&L. The adjudication is locked in advance: when the
tail-marks crawl completes (adding the Jan–Apr 2026 politics months), the
test re-runs verbatim, and the candidate is claimed iff both modes are
positive with PSR ≥ 0.95, ≥8 test months, month-t ≤ −2, bet-weighted
≤ −1.5pp, and 200bps slippage survives; otherwise it becomes mirage #9. No
parameter may change between registration and adjudication.

The honest statement: no strategy claim currently stands. The de-pinned
calibration structure is a statistical description of history that no
single artifact explains away, but every implementation tried so far has
died under 2026 data plus honest weighting. One candidate awaits automated
adjudication, and the forward experiment at live executable quotes
(recording the NO ask and depth for every market entering the trade window,
self-grading at resolution) is the registered arbiter.

## 6. Interpretation

**Where the inefficiency lives — and where it doesn't.** The horizon study
(HORIZON_PERSISTENCE.md) resolves the results into one picture. In markets
that live a week or longer, the longshot overpricing is a long-horizon
phenomenon the crowd itself corrects: the pooled longshot gap runs −2.8pp
(t = −4.0) at T-168h, −2.5pp (t = −3.2) at T-72h, and −0.6pp (t = −0.7) at
T-24h. Given time, the market converges. The significant 24-hour cells in
Section 4 are therefore carried by the venue's short-fuse markets — those
that never had a week — and the surviving candidate cell is the cleanest
case: short-lived attention markets (median lifetime 3–6 days, dominated by
"will he say/do X" mention contracts) whose overpricing is *created in the
final days*, with prices drifting up into resolution even for eventual
losers. The pattern is consistent with last-day attention flow paying up in
markets too young for the correction mechanism to have operated, and it
makes a concrete prediction the forward experiment can refute: the edge, if
real, should be absent in long-lived markets and concentrated where market
age at trade time is days, not weeks.


Where the crowd is measurable at scale, it is far better calibrated than
folk accounts of retail prediction markets suggest: mid-range prices are
nearly unbiased in every liquid category; a bias-corrected D-1 GFS+ECMWF
forecast loses to the weather crowd's own prices (log-loss 0.388 vs 0.360, a
companion result); and the largest apparent miscalibrations in our own
interim analyses were, one after another, instruments lying. What survives
is thin, concentrated in tails, so far untradeable in every implementation
tried, and consistent with lottery-preference demand meeting
inventory-averse liquidity provision. The methodological ledger — eight
documented ways a prediction-market backtest fabricates edge — may be the
more durable contribution.

## 7. What would change our minds

Pre-registered: (i) the forward live-quote experiment failing to reproduce
a positive net edge at real asks over ≥120 days; (ii) the bias failing
bet-weighted in the 2026 tail sample — this one has already fired against
the pooled short-longshot trade (Section 5), and the same mechanism
adjudicates the politics-favorites candidate when the tail crawl completes;
(iii) an execution study showing effective tail spreads persistently above
200bps, which prices the anomaly as compensation rather than error.

## References (to finalize)

Griffith (1949); Thaler & Ziemba (1988); Snowberg & Wolfers (2010); Stoll
(2000); Harvey (2017); Bailey & López de Prado (2014); Dubach (2026)
arXiv:2604.24366; Polymarket API documentation.
