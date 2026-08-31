# Results index — what was measured, what died, what survived

*The 90-second version. Every number regenerates from this repo; each line
links the code and writeup behind it.*

## The seven backtest mirages (found, measured, killed — in our own results)

| # | the seductive number | the truth | how it died | receipts |
|---|---|---|---|---|
| 1 | maker "fills" from book shrinkage | 1,735× overcount — cancels, not trades | matched vs the on-chain trade tape: 48,578 vs 28 | `validate_fills.py`, `MARKOUT_GATE_INVALID.md` |
| 2 | +$483/day maker markout | ≈$0 — spread booked at a touch a rewards-eligible maker never rests at | repriced to near-mid quote; matches Dubach 2026 | `markout_decomp.py`, `MARKOUT_DECOMP.md` |
| 3 | crypto "reverse bias", day-clustered t=−4.2 | one crash month (Nov-2025) | month-level clustering → t=−0.3 | `study_longshot.py` docstring |
| 4 | +5pp crypto favorites gap, persists OOS | +0.6pp bet-weighted — below costs | month-mean vs bet-weighted weighting | `STUDY1_OOS.md` |
| 5 | −12pp weather "miscalibration" | stale last-trade marks: family prices sum to 1.39 | accounting identity reproduces the gap exactly | `data/weather_artifact_check.md` |
| 6 | weather model +125%, SR 0.9 | −79%, SR −4.9 on books fresh enough to trade | freshness gate Σmarks∈[0.95,1.10] | `WEATHER_V1.md` |
| 7 | crypto favorites underpriced (2 verdict cells) | pinned afterlife prints — 22-28% of marks postdate the market's actual close | closedTime exclusion; cells died, and a broader real signal emerged | `PINNED_PRICE_CHECK.md` |

## Findings that survived every attack

- **Longshots are overpriced, everywhere** (de-pinned): 12 month-clustered
  cells across crypto/politics/geopolitics/weather/other, all one direction,
  22–32 months. OOS at T-24h: bet-weighted −1.77pp on 4,000 bets — the
  evidence bar's first pass (SR 3.9/PSR 0.99 at base costs, SR ~1.5–2 at
  pessimistic slippage; cost-conditional by construction). The decisive test
  runs forward at LIVE executable book prices (`longshot_forward.py`, in CI
  2×daily, self-grading). `STUDY1_OOS.md`.

- **Polymarket vs the equity yardstick** (same Stoll decomposition, theirs from
  raw millisecond TAQ): tight prediction-market books ≈ a somewhat-worse
  small-cap (17 vs 8.6 bps effective half-spread); wide books book "realized
  spread" ~80× a small-cap maker's take — the fill-at-touch mirage in one row.
  `papers/paper0/` (table + figures regenerable).
- **The crowd beats the model**: vig-stripped T-24h weather-ladder prices are
  better calibrated than a bias-corrected D-1 GFS+ECMWF blend (log-loss 0.360
  vs 0.388, 2,972 buckets, walk-forward). Retail prediction markets embed
  public NWP by the day before. `backtest/weather_model.py`.
- **Warm-side ladder drift is real** (winners above ladder center 45.8% vs
  23.2%, month-clustered t=+3.0, 15 months) — but prices already adjust for
  it; the residual is not tradeable at D-1.
- **The only durable maker income is the fee rebate**: ~20% of taker fees on
  fills, measured from realized fees, roughly cancelled by adverse selection
  at a realistic resting size (12-day paper series: +$815, t=1.95 — below the
  2.0 bar, says so on the ledger). `maker_pnl_real.py`.

## The instrument

Live order-book + site-wide trade-tape capture on $0 infra (GitHub Actions,
self-healing, alarm issues auto-open/close) · 880k-market resolved-label
universe · 90k pre-resolution price marks · walk-forward backtest engine with
pre-registered exit tests (null strategies must fail; planted Sharpe must
recover; costs must bite; daily exposure capped after test #6 above tried to
deploy 186%/day) · Sharpe/PSR/deflated-Sharpe evidence bar: nothing is
"quotable" below 300 bets / 120 days / PSR 0.95 · WRDS sleeves: TAQ
benchmark, CRSP momentum reproduction, OptionMetrics calibration yardstick.

## Standing rules

Paper only, by construction. `ideal`-labeled columns are counterfactual
ceilings, never results. A number that hasn't survived an attempt to kill it
doesn't get quoted.
