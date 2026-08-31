# Study 1 OOS verdict — the crypto-favorites candidate fails economically

Split: train < 2025-07-01, test >= (frozen gap). T-24h crypto favorites
[0.50,0.95), pinned prices excluded (p<0.95), fee 0.07 worst-case, 100bps slip,
daily exposure cap 25%.

| | train | test |
|---|--:|--:|
| month-clustered gap | +5.3pp (t 1.8, 18mo) | +5.1pp (t 1.7, 7mo) |
| **bet-weighted gap** | | **+0.6pp** (n 13,911) |
| engine net | | **SR −2.2, not quotable** |

The resolution: the month-clustered mean weights thin months equally with
busy ones. Bet-weighted — the only weighting money gets — the gap is +0.6pp,
below costs. Month means by test month: +2.7, +0.5, +1.5, +0.9, −3.0pp for
Jul–Nov 2025 (thousands of bets each); the fat positive months are tiny
(n≈34). The calibration structure is real as a monthly average and untradeable
as a strategy. T-168h fails the same way (train +9.6pp → test +5.5pp t=1.2,
engine SR −3.1).

Caveats cutting both ways: test months 2026-01..08 are still being marked
(tail crawl), so this re-runs when they land; and the engine's daily exposure
cap (added after this test exposed uncapped same-path deployment at −852%) is
now a permanent engine feature. Chalk up mirage #4: month-clustered
calibration significance does not imply bet-weighted tradeability. The paper
gets a cleaner finding than an edge: the weighting between "statistically
real" and "economically real" is itself the result.
