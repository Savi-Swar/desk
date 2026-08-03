# The markout gate was measuring noise — reset (2026-08-03)

validate_fills.py cross-checked the fill model against ground-truth trade
prints (last_trade_price) over two 24-min recordings:

- shrinkage "fills" the model counted: 48,578
- real trade prints (ground truth):        28
- shrink events matching a real trade:     ~0.1%
- => the fill model overcounts fills by ~1,500x

## What this means

The fill model infers a fill whenever an order-book level loses size. But a
level shrinks on a CANCEL just as much as on a TRADE — and on these markets
cancels outnumber trades ~1,500:1. So the +0.011 markout / 1-2% adverse
result was almost entirely measuring cancels, which are benign by nature
(nobody cancels to run you over). The number looked like a screaming pass;
it was an artifact.

## The gate is reset, not passed

The maker markout question is UNANSWERED. The prior "encouraging early read"
is withdrawn. Do not treat any markout figure from the shrinkage-based fill
model as evidence.

## The fix

Real fills must come from real trades. Two paths:
1. Rebuild the fill model to count a fill ONLY when a last_trade_price print
   crosses the resting quote. Problem: last_trade_price on the per-market
   channel is sparse (~14 trades / 24 min / 120 tokens here) — too thin.
2. Capture the RTDS trade firehose (wss://ws-live-data.polymarket.com,
   site-wide trades) so the trade sample is large enough to measure markout
   on genuine executions. This is the required next build.

Until a trade-based markout exists, the gate cannot pass. Caught by asking
"what do our samples actually look like" and validating against ground truth.
