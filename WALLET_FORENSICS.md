# Wallet forensics: what the "top arb wallets" actually do

Reconstructed from the on-chain tape (HuggingFace TimeSeventeen/Polymarket-v1),
wallet 0xe1D6b51521Bd4365769199f392F9818661BD907c — the #1 name on the
post-fee realized-arb leaderboard — on a representative day (2026-04-02).

## The headline: it is not an arbitrageur

Everyone (our own research included) called these "arb wallets." The tape
says otherwise.

- **86,809 taker fills that day, but only 6 were clean both-sides-under-$1
  arb round-trips, worth $2.75 total.** Single-condition arb is a rounding
  error in its activity.
- **Its taker legs LOSE money.** Across 1,346 round-tripped outcomes the
  median sell-minus-buy spread was **−3.48c/share**; share-weighted −7.4c;
  gross taker round-trip P&L **−$8,483** on the day. It flips at a positive
  spread only 46% of the time — worse than a coin flip.
- Yet the wallet is hugely net profitable (~$2M/month on the leaderboard).

The only way both are true: **the entire edge is on the MAKER side** —
liquidity rebates plus passive fills — and the money-losing taker flow is
inventory management for that maker book. This is a high-frequency
**market-making / rebate-farming** operation, not arbitrage.

## Where it operates

Concentrated entirely in newborn crypto up/down markets: btc-updown-5m
(28k fills), eth-updown-5m (14k), btc-updown-15m (11k), eth/sol variants.
Polymarket spawns a fresh 5-minute market ~every 5 minutes per asset; the
wallet quotes them from birth, all day, ~50k fills/day.

## Why this matters for us

1. **It confirms the maker thesis with hard evidence.** The richest player
   on this venue makes its money exactly where our maker sims are pointed:
   rebates + passive spread, not taker locks. The taker side is a cost.
2. **It confirms the race we declined is the right one to decline.** Being
   this wallet needs sub-second quoting on ~1,500 newborn markets/day and
   rebate-tier volume — colocation-class infrastructure. Unreachable at $0,
   and the taker bleed shows it is unforgiving.
3. **It re-scores "the best arb wallet made $6k/week."** That framing was
   wrong. It is the best HFT market-maker, and its edge is structural
   (rebate program) + speed, not an arbitrage anyone can replicate patiently.
4. **The lesson repeats:** believe the tape, not the label. The wallet
   labeled "arbitrageur" is a market-maker whose taker book loses money.

## Limits of this measurement

Maker-side P&L (rebates + passive fill prices) is not fully reconstructible
from the trade tape alone — it needs the rebate schedule and maker fill
attribution. The inference (maker/rebate is the whole edge) rests on:
net profit large + taker legs measured negative -> the maker side carries
all of it and then some. Directionally certain; exact split unmeasured.
