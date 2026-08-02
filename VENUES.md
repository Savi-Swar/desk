# Venue map (live-probed 2026-08-02)

| Venue | Access | Money | Wired | Surface |
|---|---|---|---|---|
| Polymarket | keyless | real | yes | everything (primary) |
| Kalshi | keyless | real | yes | BTC/ETH/Fed, depth-verified cross-venue |
| Limitless | keyless | real (on-chain) | yes | crypto up/down — same markets as Polymarket |
| SX Bet | keyless | real (on-chain) | snapshot | sports exchange (NFL/football) |
| Manifold | keyless | PLAY money | no | reference/sentiment only |
| Overtime/Thales | API key now | real | no | on-chain sports |
| Drift BET | auth | real | no | Solana sports/PM |
| PredictIt | 403 from server | real | no | US politics |
| Metaculus | 403 | none (forecast) | no | — |
| Insight Prediction | 302/redirect | real | no | — |

Cross-venue collectors treat basis as MEASUREMENT, not a lock, until
resolution-source + snapshot equivalence is verified per pair (the
"same event?" hazard). Limitless<->Polymarket crypto up/down and
Kalshi<->Polymarket BTC/ETH/Fed are logged with that flag.
