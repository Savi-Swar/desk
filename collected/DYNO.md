# Dyno sheet — pre-drive performance metrics

Computed 2026-08-02 05:07 UTC. Percentile = where this metric sits vs the best a $0 patient-game operator could achieve. Metrics needing the live sample are PENDING with their target stated, not scored.

**Computable-metric composite: 93th percentile** (6 scored, 2 pending the 2-week sample)

| Metric | Status | Value | Target | Pct |
|---|---|---|---|---|
| fee-model accuracy | measured vs live schedule | 9930 checks, 0 mismatches, rates in 0-0.07 band: True | 0 mismatches, rates in band | 95th |
| detection precision | measured | 100% of 19 rechecked survived | >80% | 95th |
| fill-model calibration | PENDING (n=2569, need 3000) | fill rate 27.0% so far | |pred-realized| < 5%, n>3000 | — |
| markout / adverse selection (THE GATE) | PENDING (n=693 fills, need 3000) | +0.01542 early read (noise) | mean 30s markout >= 0 | — |
| detection latency | known | 60s sweep (CI-bound); pro tier is sub-second | <=60s for the patient game (speed race declined) | 90th |
| collection uptime | measured | 100.0% rc=0 over 355 runs | >98% | 95th |
| venue coverage | measured | Polymarket + Kalshi + cross-venue basis | 2+ venues + basis | 90th |
| risk controls | enforced | risk_guard.check() enforced (caps/drawdown/stale/kill); timeout-tolerant wrapper; two-fail alarm | caps+drawdown+stale+kill enforced in code | 95th |

## Still red / pending
- **PENDING** fill-model calibration: verdict at the Aug-16 gate
- **PENDING** markout / adverse selection (THE GATE): verdict at the Aug-16 gate
