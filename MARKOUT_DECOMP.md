# Markout decomposition — the "favorable markout" was a fill-at-touch mirage

Deep dive, 2026-08-08/09. Aug 8's paper P&L jumped to +$819 on a big favorable
*markout* (not just rebate), concentrated in the new wide-spread esports/sports
markets. A maker profiting on ~78% of fills is backwards from adverse-selection
theory, so we decomposed it. It's an artifact. Here's the anatomy and the fix.

## What markout actually is

Our per-fill markout `D·(price − mid_{t+h})` is, formally, the **realized
half-spread** — it already nets spread capture against adverse selection out to
horizon h (Stoll 2000; SEC Rule 605). It is NOT raw spread. The identity:

    realized_markout = effective_half_spread − price_impact(adverse selection)
    effective_half_spread = |price − mid_at_fill|   (spread a TOUCH quoter earns)
    price_impact          = signed mid drift, fill → fill+h  (adverse selection)

## The decomposition (1,506 real Aug-8 fills, 100-sh cap)

| component | $ | meaning |
|---|--:|---|
| effective spread capture | **+522** | earned only if you fill at the touch |
| price impact (adverse) | +39 | the real tax |
| realized markout (= our mo) | **+483** | capture − impact |

By spread width — the tell:

| spread | fills | spread capture | realized markout |
|---|--:|--:|--:|
| tight <1¢ (crypto) | 687 | +28 | +28 |
| mid 1–3¢ | 688 | +110 | +93 |
| **wide >3¢ (esports/sports)** | 131 | **+383** | **+363** |

9% of fills (the wide ones) drive 75% of the P&L, entirely via spread capture.

## Why it's a mirage: fill-at-touch

Markout books the fill at the taker's **touch** — on a 3¢ book that's ~1.5¢ from
mid, so it credits a fat half-spread. But Polymarket liquidity rewards *require*
quoting near the mid (within `rewardsMaxSpread`). A near-mid maker never fills at
that wide touch — its own tight quote becomes best and fills first, at ~1 tick
from mid, capturing ~nothing. Crediting the wide touch to a near-mid strategy is
a counterfactual error. Repricing to our own quote offset:

| we quote at… | markout edge |
|---|--:|
| the touch (as measured) | +483 |
| **0.1¢ from mid (competitive)** | **−0.49** |
| 0.5¢ from mid | +117 |
| 1.0¢ from mid | +189 |

**A realistic near-mid quoter's markout edge is ≈ $0.** This independently
reproduces Dubach (2026, arXiv:2604.24366), who finds the honest median effective
half-spread on Polymarket is ≈0 and the wide-market edge is a measurement
artifact (order-book direction inference is ~59% accurate; wide-book mids are
unreliable — we saw 26% of fills with a wrong-side/negative effective spread).

## The fix (shipped)

- `trade_markout.py` now records `eff_half` (effective half-spread at fill) per
  fill, so the edge can be repriced instead of taken at the touch.
- `maker_pnl_real.py` reprices markout to a near-mid quote: captured spread =
  min(QUOTE_OFFSET, max(eff_half, 0)); repriced markout = mo − (eff_half −
  captured). QUOTE_OFFSET = 1 tick (0.001), the competitive near-mid quote.
- The `significant` gate is on the net-live distribution (markout repriced +
  rebate), so the flag reflects the real edge, not touch-spread noise.

## Bottom line

Markout is a wash. The entire real maker edge is the **rebate** (~20% of taker
fees on our fills, measurable, ~$100–150/day paper) minus a small adverse bleed.
The liquidity pool is a pro-bot game we'd lose (REWARD_CAPTURE_RESEARCH.md).
Every "markout edge" number before this fix was the fill-at-touch mirage; the
ledger now reprices to a near-mid quote and reports the honest number. The old,
inflated trade_markout ledger is archived on first run (self-heal on the new
schema); the honest series accumulates from here into the Aug-16 gate.

Caveat still standing: even the repriced net-live is capture-optimistic (assumes
we get our 100 shares front-of-queue). And 26% wrong-side mids mean the wide-book
mid itself is noisy — a micro-price would be the next refinement.
