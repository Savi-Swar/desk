# Reward capture — does maker income beat the adverse-selection bleed?

Deep research on Polymarket maker incentives, run 2026-08-05. The question the
whole maker thesis rests on: at a realistic quote size, does reward income clear
the adverse-selection cost we measured on real fills? Short answer: **the maker
rebate does; the liquidity pool almost certainly does not.**

Everything here is paper. No compliant account exists (F-1, no SSN), so this is
a research verdict, not a trading plan.

## Two programs, both live, that stack

The March 2026 taker-fee rollout did not replace the old rewards program — it
added a second one. As of mid-2026 a resting maker order can earn from both:

1. **Liquidity rewards** — a per-market daily USDC pool paid for *resting* orders
   near the mid, fill or not. Per-order score is quadratic in spread utilization
   times size: `((v − s)/v)² × size`, gated by `rewardsMaxSpread` (v) and
   `rewardsMinSize`, two-sided via `min(Q_one, Q_two)` (single-sided earns 1/3).
   Sampled every minute, **split pro-rata**: your payout = pool × (your score /
   total score in that market). Competitive and zero-sum within a market.

2. **Maker rebates** — new with the fees. On a filled maker order the taker pays
   `feeRate × p(1−p)`; the maker receives a rebate that is a category share of
   that fee (**crypto 20%, sports 15%, politics/finance/etc 25%**; geopolitics is
   fee-free). Also per-market pro-rata, but its magnitude scales with *our own
   filled volume*, which is why we can measure it directly.

Source: docs.polymarket.com/market-makers/{liquidity-rewards,maker-rebates,
market-details}. Full sourcing + the parts that couldn't be verified are in the
research log appended below.

## What we can MEASURE (the rebate) — it covers the bleed

The rebate is computable from real fills: we are the maker on every fee-bearing
row (the taker paid the fee), so our rebate ≈ 20% of that fee, scaled by the
fraction of the fill we could realistically capture. Capping both markout and
rebate at a 100-share quote (you cannot fill — or be rebated on — size you never
rested):

| day | markout (live) | rebate (live) | **net live** | note |
|-----|---------------:|--------------:|-------------:|------|
| Aug 4 | −$15.12 | +$46.55 | **+$31.43** | 831 fills, ~47 effective |
| Aug 5 | −$5.29 | +$2.89 | **−$2.40** | 32 fills, thin |

On the busy day the rebate is ~3× the adverse-selection loss and flips the live
maker P&L positive. This is the first non-inflated positive the desk has found.
Caveats that keep it honest: ~47 effective bets (not significant), measured on
crypto markets, and paper-only.

## What we can only MODEL (the pool) — a game we'd lose

We recorded 350 reward-eligible markets, **~$128k/day in pools**, concentrated in
Counter-Strike esports (~$41k/day) and geopolitics (~$12k). But:

- **Size-gated.** A 250-share quote reaches 98% of the pool; a 100-share quote
  sees 6%. Playing seriously needs ≥250-share two-sided quotes — more capital and
  more adverse-selection exposure per fill.
- **Wrong markets.** The pools are in esports/geopolitics; our adverse-selection
  data is on crypto up-downs, which carry ~$0 pool. We have almost no markout on
  the markets where the pool money is — and esports adverse selection is likely
  *worse* (spiky, informed, fast-resolving).
- **Pro-dominated.** A naive pool-capture model (capture = pool / competition)
  returns 300–5000%/month — and is therefore wrong. The community-sourced reality
  is ~$200–300/day on $10k in the early days, "diminished" since toward ~10% APY
  (~$3/day on $10k). The quadratic-near-mid + latency scoring lets professional
  bots quoting at the mid with size take the vast majority of score; an off-mid
  min-size quote earns quadratic scraps. Realistic pool capture for a
  latency-disadvantaged small maker is small and unreliable — do not bank on it.

## Verdict

- The maker **rebate** is the real, measurable edge and it covers the bleed on
  active days (+$31 live, Aug 4). It is not competitive in magnitude the way the
  pool is — it scales with our own fills — so it is the piece worth building on.
- The liquidity **pool** is a pro-bot game we would structurally lose; its
  headline size is a mirage once the quadratic scoring and latency gap are
  priced in.
- The honest open question is now narrower and answerable: **measure markout on
  the rebate-bearing markets over enough days to get effective-N up**, and let
  the rebate-vs-adverse net accumulate to significance. If net-live stays
  positive across ~2 weeks with effective-N in the hundreds, that is a real
  (paper) edge. If it doesn't, "the small-market maker edge dies at the queue" is
  itself a clean finding.

Next data step: nothing to build on the pool. Keep the fill recorder running,
add the rebate to the daily P&L ledger next to markout, and watch net-live and
effective-N climb. The thesis lives on the rebate, not the pool.
