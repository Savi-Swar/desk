"""Maker-sim v3: the defended quoter. Same book data and fill model as v2
(which keeps running as the undefended control), plus the three defenses
documented in the market-making literature:

1. Drift skew — quote center moves with the previous interval's mid drift,
   so we stop selling into informed buying at a stale price.
2. Circuit breaker — if the previous drift exceeded a multiple of the
   spread (news proxy), pull quotes for the interval: no reward, no fill.
3. Inventory cap — net position per market is capped; at the cap we quote
   only the reducing side.

Parameters are fixed a priori from the literature, not tuned on our week:
SKEW=1.0, PULL_MULT=2.0 (and an absolute 2c floor), INV_CAP=300 shares.
Writes maker_net3.csv next to v2's maker_net.csv for the same intervals.
"""
import pathlib

import pandas as pd

D = pathlib.Path(__file__).parent / "collected"
f = D / "maker_book.csv"
if not f.exists():
    print("no maker data")
    raise SystemExit
M = pd.read_csv(f)
snaps = sorted(M["ts"].unique())
if len(snaps) < 3:
    print(f"{len(snaps)} snapshot(s) — v3 needs 3+; accruing")
    raise SystemExit

SHARE_CAP = 0.02     # same reward share assumption as v2
QUOTE_SIZE = 100.0   # same $100 notional per side as v2
SKEW = 1.0           # quote center moves by 1x the previous drift
PULL_MULT = 2.0      # pull if |prev drift| > max(2*spread, 0.02)
PULL_FLOOR = 0.02
INV_CAP = 300.0      # max net shares per market

res = []
inv = {}             # market -> net shares (positive = long from bid fills)
prev_mid = {}
for i in range(len(snaps) - 1):
    a = M[M["ts"] == snaps[i]].set_index("q")
    b = M[M["ts"] == snaps[i + 1]].set_index("q")
    common = a.index.intersection(b.index)
    hours = max((pd.to_datetime(snaps[i + 1]) - pd.to_datetime(snaps[i]))
                .total_seconds() / 3600, 0.5)
    for q in common:
        m0, m1 = a.loc[q, "mid"], b.loc[q, "mid"]
        sp = a.loc[q, "our_spread"]
        rate = a.loc[q, "reward_daily"]
        score = a.loc[q, "score_proxy"]
        drift = m0 - prev_mid.get(q, m0)
        prev_mid[q] = m0
        held = inv.get(q, 0.0)

        # defense 2: circuit breaker on the news proxy
        if abs(drift) > max(PULL_MULT * sp, PULL_FLOOR):
            res.append({"t0": snaps[i], "q": q, "reward": 0.0,
                        "fill_pnl": 0.0, "event": "pulled"})
            continue

        # defense 1: skew the quote center with the drift (capped inside spread)
        center = m0 + max(-sp / 2, min(sp / 2, SKEW * drift))
        bid, ask = center - sp / 2, center + sp / 2

        # defense 3: at the inventory cap, quote the reducing side only
        quote_bid = held < INV_CAP
        quote_ask = held > -INV_CAP

        reward = rate * SHARE_CAP * score * (hours / 24)
        if not (quote_bid and quote_ask):
            reward *= 0.5        # one-sided quoting earns half the reward share

        pnl, event = 0.0, ""
        if quote_ask and m1 > ask:
            pnl = -(m1 - ask) * QUOTE_SIZE
            inv[q] = held - QUOTE_SIZE
            event = "ask-run"
        elif quote_bid and m1 < bid:
            pnl = -(bid - m1) * QUOTE_SIZE
            inv[q] = held + QUOTE_SIZE
            event = "bid-run"
        else:
            pnl = sp / 2 * QUOTE_SIZE * 0.25   # same benign-flow assumption as v2
        res.append({"t0": snaps[i], "q": q, "reward": reward,
                    "fill_pnl": pnl, "event": event})

R = pd.DataFrame(res)
R.to_csv(D / "maker_net3.csv", index=False)
net3 = R["reward"].sum() + R["fill_pnl"].sum()
print(f"maker v3: {len(R)} market-intervals across {len(snaps)} snapshots")
print(f"reward ${R['reward'].sum():.2f} | fill pnl ${R['fill_pnl'].sum():+.2f} "
      f"| NET ${net3:+.2f} | pulled {(R['event']=='pulled').mean():.0%} "
      f"| adverse {(R['event'].isin(['ask-run','bid-run'])).mean():.0%}")

v2f = D / "maker_net.csv"
if v2f.exists():
    V = pd.read_csv(v2f)
    net2 = V["reward"].sum() + V["fill_pnl"].sum()
    print(f"control v2 NET ${net2:+.2f} -> defended v3 NET ${net3:+.2f} "
          f"(recovered ${net3-net2:+.2f})")
