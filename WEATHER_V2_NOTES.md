# Weather v2 pre-registered question: per-day ensemble sigma

Question (pre-registered in WEATHER_V1.md): does TRUE ensemble spread — a
per-DAY sigma from NWP ensemble members — close the calibration gap vs the
crowd? v1 baseline: bias-corrected GFS+ECMWF deterministic blend with a
per-city GLOBAL sigma lost 0.388 vs 0.360 crowd log-loss on 2,972 buckets.

## Verdict on backfill: NOT BACKFILLABLE

Member-level D-1 ensemble history does not exist at open-meteo. Probes
(2026-08-31, UA "research saviswarup@gmail.com", London 51.51/-0.13):

1. `ensemble-api.open-meteo.com/v1/ensemble` with `models=gfs025`,
   `start_date=2025-01-20`: rejected — "start_date out of allowed range
   from 2026-05-31 to 2026-10-06". Parameter validation implies ~92 days,
   but actual data is far shallower:
2. Same API, `past_days=7`, hourly `temperature_2m` + members: real values
   only for the last ~3 days (2026-08-28 partial, 08-29 onward full;
   08-25..08-27 all null). Absolute `start_date` past dates ≥4 days back
   also return all-null. So the ensemble API is a ~3-day rolling live
   window, not an archive — and those past hours are short-lead mosaic
   data anyway, not D-1 runs.
3. `previous-runs-api.open-meteo.com` with `models=gfs025`,
   `hourly=temperature_2m_previous_day1`: HTTP 200 but silently all null,
   units "undefined" — the previous-runs archive covers deterministic
   models only. No member-level variables exist there at all.
4. `ensemble-api` accepts `temperature_2m_previous_day1(_memberNN)` as
   variable names (returns °C units and 31 member keys) but every value
   is null at every lead — the previous_day mechanism is not wired up for
   ensembles.
5. `historical-forecast-api.open-meteo.com` with `models=gfs025`: 200,
   all null. Deterministic archive only.

What IS live: `ensemble-api` `daily=temperature_2m_max&models=gfs025` for
today/forecast dates returns 31 series (control + 30 GEFS members);
e.g. London 2026-09-01: mean 21.96 °C, member std 0.68 °C. ECMWF ensemble
(`ecmwf_ifs025`, 51 members) is also live-only.

Consequence: the Jan 2025 – Jun 2026 resolved-family dataset (4,125
families / 2,972 marked buckets) CANNOT be re-scored with true per-day
ensemble sigma. No log-loss triple was computed — any "ensemble sigma"
proxy built from deterministic model disagreement would answer a different
question than the pre-registered one. **v2 is gated to forward data.**

## What was done instead: forward capture (weather_collect.py)

The 2x-daily collector now records per-day ensemble spread next to each
city/date's deterministic forecasts and live bucket prices:

- New column `fc_ens_std_c`: sample std (°C) of GEFS `gfs025` member Tmax
  (control + 30 members, requires ≥10 non-null members) from one extra
  ensemble-API call per city-date, same UA and sleep discipline.
- Schema changed, so the ledger filename is bumped:
  `collected/weather_obs2.csv` (fresh header). `weather_obs.csv` is
  frozen — its header is never touched, so the accumulated v1 forward
  rows stay parseable.
- Local test run 2026-08-31: see run line in git log / CI once merged.

## The eventual v2 test (when ~8-12 weeks of weather_obs2 have accrued)

Same walk-forward scoring as backtest/weather_model.py, price-free only
(trading/engine/marks-P&L are settled dead per WEATHER_V1.md):
- mu: bias-corrected deterministic blend, per-city offset as in v1
- sigma_v1: per-city global robust residual std (floored 0.8)
- sigma_v2: a * fc_ens_std_c + b, a,b fit walk-forward per city (or a
  single global affine map), blended with the residual floor
- report crowd vs v1-sigma vs ensemble-sigma log-loss on identical
  buckets, T-24h snapshots from the collector (live books, not resolved
  prints).
