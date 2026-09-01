# The survivor hunt — pre-registered candidate tests (2026-08-31 – 2026-09-01)

Standing bar, applied BEFORE looking at any result: pinned-mark exclusion,
month-clustered inference, bet-weighting reported, BOTH engine sizing modes
(capped Kelly + flat fraction) must agree positive with PSR >= 0.95 each,
slippage sensitivity, composition inspection. One night, seven candidate tests:

| candidate | verdict | cause of death / status |
|---|---|---|
| family middles-vs-tails (vig-immune) | DEAD (both modes) | +1.6pp structure < fees on 229 fresh families |
| live-ask family set-arb | ABSENT | 26 full families: Sigma(asks) 1.008-1.02, never <1 — mint/merge keeps it shut |
| forecast-conditioned warm bucket | DEAD (both modes) | market prices its own cold-ladder drift better than a one-step rule |
| Kalshi-Polymarket ETH basis | EXISTS, UNTRADEABLE | +1c median executable basis, 19 days — under the ~2c fee wall; one underlying |
| sports moneyline dogs | NO SIGNAL | train gap +10.8pp (wrong direction, t=+1.7): rule fires no trade |
| politics longshots | DEAD | OOS reversed (+3.8pp, month-t +2.6) |
| **politics favorites (sell side)** | **PENDING SURVIVOR** | see below |

## The pending survivor: politics favorites are overpriced

Train (<2025-07): gap −6.4pp, t=−2.4 (16 months). Test: bet-weighted −3.6pp,
month-t −2.1 (7 months); BOTH engine modes agree positive (capped SR +2.3 /
flat +2.4); survives slippage at 100/200/300bps (NO-side entries make slip
cheap); held in BOTH 2026 months (−7.3pp, −6.9pp) — the only category whose
edge survived 2026. Composition: Trump/election frontrunner overpricing
(176+108 of 354), consistent with documented political-market behavior.

NOT CLAIMED, for two pre-registered reasons: PSR 0.88/0.91 < 0.95, and 7
test months < 8. Weakness on record: day concentration (top-5 days = 142% of
flat-mode P&L — political resolutions cluster).

AUTO-ADJUDICATION (pre-registered now): when the tail-marks crawl completes
(adds Jan-Apr 2026 politics months), re-run the politics-favorites test
verbatim. CLAIMED iff: both modes positive with PSR >= 0.95, >= 8 test
months, month-t <= −2, bet-weighted <= −1.5pp, and slip-200 survives.
Otherwise it joins the mirage ledger as #9. No parameter may change between
now and then.

## ADJUDICATION (2026-09-01, automated, full 191,393-mark dataset)

The distributed crawl delivered the missing Jan–Apr 2026 months (12 test
months, n=747). Against the locked rule: bet-weighted gap **−2.0pp** (direction
held), both sizing modes still positive (SR +1.22 capped / +1.17 flat) — but
month-t −1.35 and PSR 0.81/0.81, below the pre-registered −2 and 0.95 bars.

**VERDICT: MIRAGE #9 — directionally persistent, sub-threshold, not claimable.**
The honest reading: a real-looking tilt that never reached evidentiary
strength; the rule existed precisely so we would not round that up. The
forward live-ask experiment remains the only open arbiter of anything.
