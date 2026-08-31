# Paper 1 — Is the crowd calibrated? Favorite-longshot structure in 880,000 prediction-market resolutions

*(Working outline. Voice: yours. Numbers as of 2026-08-31 — regenerate via
`python study_longshot.py` before any submission. OOS backtest and artifact
checks still pending; sections 5–6 are placeholders until they run.)*

## Abstract (draft skeleton)
The favorite-longshot bias — longshots overpriced, favorites underpriced —
has 75 years of racetrack evidence; prediction-market evidence is mixed and
small-sample. We build the largest calibration sample to date: ~880k resolved
Polymarket markets, ~90k with pre-resolution price marks at T-24/72/168h,
69,188 in the final verdict sample. Headline: naive bucket z-scores and even
day-clustered inference produce large spurious biases (a t=−4.2 crypto effect
that was entirely one crash month); month-clustered inference leaves 4 robust
cells — crypto favorites underpriced (+4.7 to +8.2pp), weather mispriced the
other way (−6.4 to −11.9pp). Calibration failures exist, are
category-specific, run in both directions — and most published
prediction-market "bias" at this scale is regime clustering.

## 1. Question + literature hook
- FL bias: Griffith 1949 → racetrack canon (Thaler & Ziemba 1988; Snowberg &
  Wolfers 2010: risk-love vs misperception).
- Prediction markets: mixed — early Iowa/Intrade calibration looked good;
  recent crypto-venue studies small or horizon-confounded.
- Contribution: (a) largest resolution sample; (b) horizon-explicit marks;
  (c) the clustering lesson as a named methodological warning.

## 2. Data & pipeline (all regenerable from repo)
- **Label universe** — `fetch_resolved.py`: Gamma API `closed=true` swept by
  end-date windows (offset pagination 422s past ~2k rows; windows recursively
  halve down to 15 min for dense hourly days). Dedup by id. ~880k markets,
  2020→now. Winner = the unique outcome with final price > 0.99; ambiguous
  finals flagged unresolved and dropped.
- **Price marks** — `fetch_price_marks.py`: CLOB `prices-history` for
  outcome-0's token, `interval=max&fidelity=720` (12-hour bars; fidelity 180
  and 60 return EMPTY on interval=max — undocumented quirk, worth a footnote).
  Mark = last price at-or-before T−24h/72h/168h from `endDate`. Filters:
  resolved, binary-labeled, volume ≥ $5k, lifetime ≥ 26h (excludes hourlies —
  most recent listings). 90k+ marked markets; resumable via done-file.
- **Categories** — `market_cats.py`: Gamma stopped populating `category`
  (~4k of 450k+ carry one), so slug/question keyword rules, specific→general,
  first hit wins, 9 buckets. Validation: 76% agreement with the legacy labels.
- **Stats** — Wilson 95% intervals per price bucket (fine edges at the tails:
  1/2/5/10%...), buckets reported only at n ≥ 30; verdict inference is
  month-clustered t (below).

## 3. Naive tables + why they lie
- Per-bucket z-scores treat markets sharing an underlying and a regime as
  independent. Show the naive flags table (many cells light up at |z| ≥ 2).
- **The November-2025 case study** (the paper's core warning): day-clustered
  inference put crypto-favorites bias at t = −4.2; clustering by
  (category, month) collapsed it to −0.3. The entire effect was the Nov-2025
  crash month — one regime event, thousands of correlated "observations".
- General lesson: unit of independence in event markets is the regime-month
  × category, not the market and not the day.

## 4. Month-clustered results (verdict rule pre-registered in
desk-year-plan.md, tightened 2026-08-30)
- Rule: per (horizon, category, side-of-0.5): |t| ≥ 2 on month-cluster mean
  gaps (cells need ≥ 5 obs; ≥ 6 cluster-months); verdict requires ≥ 2 cells
  across ≥ 2 category groups. Gap = realized win rate − price.
- Full sample (69,188 marked markets): **BIAS CANDIDATE**, 4 cells:

| horizon | category | side | gap | t | months |
|---|---|---|--:|--:|--:|
| T-168h | crypto | favorites | +8.2pp | +3.9 | 18 |
| T-24h | crypto | favorites | +4.7pp | +2.1 | 24 |
| T-24h | weather | favorites | −11.9pp | −2.6 | 13 |
| T-72h | weather | longshots | −6.4pp | −2.3 | 16 |

- Both directions: crypto favorites resolve MORE often than priced (classic
  FL direction); weather runs the reverse. No sports/politics cell survives —
  the biggest categories are calibrated under honest clustering.
- Caveats to state in-text: crypto cells at two horizons share markets (not
  independent evidence); 54 tests run (3 horizons × 9 cats × 2 sides), ~2.7
  hits expected by chance at |t| ≥ 2 — the ≥2-cells/≥2-groups rule and the
  magnitude/persistence of the crypto cells carry the claim, not the count.

## 5. Economic interpretation + artifacts still to exclude
- Fees at the tails ≈ feeRate·p(1−p): tiny; the crypto gap is nominally
  larger than fees. But two artifacts must die first:
  1. **Pinned near-resolution prices**: marks are relative to `endDate`, and
     markets that effectively resolve before endDate show post-resolution
     pinned prices at the "pre-resolution" mark — mechanically perfect
     calibration in the extreme buckets, mechanical gaps next to them. Check
     via `closedTime` vs `endDate` and mark-price distribution mass at
     0.99/0.01. Applies at all horizons, worst at T-24h.
  2. **Outcome-0 structure in multi-bucket families**: outcome index 0 is
     not a random draw in negRisk / price-bucket families (weather bins,
     "what-price-will" ladders) — win rate of outcome-0 embeds listing
     convention. Weather is exactly where this bites. Re-run with family
     dedup / random outcome selection.
- Until both pass: the cells are candidates, not edge.

## 6. What would settle it
- Pre-registered OOS economic verification through the backtest engine:
  trade the 4 cells at the marked horizons, taker fees on, capacity from
  actual book depth, months after 2026-08 only. Report net-of-fee P&L with
  month-clustered t, same bar (|t| ≥ 2, ≥ 6 months).
- Publish the verdict rule and thresholds before the OOS window closes.

## Figures (each regenerable)
1. `fig1_calibration_curves` — realized vs implied by category, Wilson bands,
   log-odds axis so the tails are readable.
2. `fig2_clustering_collapse` — the same crypto-favorites gap under day vs
   month clustering (t = −4.2 → −0.3), Nov-2025 highlighted.
3. `fig3_crypto_month_strip` — per-month gap strip for crypto favorites,
   T-168h: is +8.2pp broad or a few months?

## Venue
SSRN + site; arXiv q-fin if endorsement lands. ≤ 12 pages. Companion to
Paper 0 (measurement artifacts): Paper 0 killed a fake maker edge, Paper 1
disciplines a real-looking taker signal the same way.

## Open items before drafting
- [ ] Pinned-price artifact check (closedTime vs endDate; mass at extremes)
- [ ] Outcome-0 / negRisk family dedup rerun
- [ ] OOS backtest through the engine (fees, capacity)
- [ ] Kish effective-N per cell (claimed in the desk methodology; not yet
      computed in `study_longshot.py` — add or drop)
- [ ] Classifier validation is against ~4k ancient (AMM-era) labels — spot-
      check 200 modern slugs by hand for a current-era agreement number
- [ ] Reconcile 880k universe → 90k marks → 69,188 verdict funnel as an
      explicit table (vol filter, lifetime filter, empty histories)
