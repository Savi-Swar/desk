# Phase 2 v1 verdict — the weather crowd beats the D-1 model

Walk-forward test on 4,125 resolved temperature-ladder families (52 cities,
Jan 2025 - Jun 2026), backfilled D-1 GFS+ECMWF forecasts (open-meteo
previous-runs), per-city offset/sigma fit on prior months only
(backtest/weather_model.py; dataset weather_dataset.py + fetch_ecmwf_d1.py).

Price-free skill, 2,972 marked buckets:
  crowd (vig-renormalized T-24h marks) log-loss 0.3595
  model (bias-corrected 2-model D-1)    log-loss 0.3875  -> CROWD BETTER

Trading, engine, fee 0.05 + slip 150bps, edge>=5pp long-only:
  all books:    +125%  SR +0.90   <- looks great, isn't
  FRESH books (family sum-of-marks in [0.95,1.10]):
                -79%   SR -4.9    <- the truth

The +125% was entirely stale prints: unsellable last-trade quotes far from
the live book fake exactly the model-vs-price divergences the strategy
selects on (mirage #6, same family as the Sigma-p calibration artifact). On
books fresh enough to trade, the model loses decisively — consistent with
the skill diagnostic: at T-24h the ladder prices already embed the D-1 NWP
runs plus resolution-station knowledge.

Also killed en route: an F/C unit bug in the first ensemble join (ECMWF °C
averaged into °F families; log-loss 0.47) — caught by the per-unit error
split, worth keeping as a checklist item.

What a v2 would need (pre-registered before any new backtest):
1. LIVE book prices, not resolved-market prints — the forward collector
   (weather_obs.csv, 2x daily in CI) is accumulating exactly this; the honest
   v2 test is forward, on collector data, after ~8-12 weeks.
2. True ensemble SPREAD (GEFS/ECMWF members) for per-day sigma instead of a
   global per-city residual sigma.
3. Or a different clock: D-0 intraday updates racing the crowd, which is a
   latency game, not a calibration game.

Status: Phase 2's calibration-vs-crowd question is ANSWERED (crowd wins at
D-1 with public deterministic models). The strategy thesis survives only in
v2 form, gated on forward collector data.
