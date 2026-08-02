"""Funding-rate carry scanner — the small-market lane the smallmkt research
ranked best for a $0-then-small F-1 operator (fee-light, patient, free feed,
self-account financial rather than gambling).

The trade is delta-neutral carry, NOT a lock: when a perp's funding rate is
positive, short the perp and long the spot; you collect funding every 8h and
the price legs cancel. Edge = funding collected; risks = spot-perp basis
drift, funding flipping before you exit, and liquidation on the short if the
hedge slips. So this ranks and paper-tracks carry, it does not claim arb.

Only symbols with BOTH a perp and a spot market qualify (you need the spot
leg to be delta-neutral). Extreme rates cluster on tiny illiquid tokens
where basis/liquidation risk is worst, so a liquidity floor is applied.
Output: collected/funding_carry.csv.
"""
import datetime
import json
import os
import pathlib

import pandas as pd

D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
OUT = D / "funding_carry.csv"

MIN_ANN = 0.10          # ignore carry under 10%/yr — not worth the basis risk
MIN_QUOTE_VOL = 2_000_000   # perp 24h quote volume floor (liquidity)
TOP_N = 20


def main():
    import ccxt
    ex = ccxt.binance({"options": {"defaultType": "future"}})
    try:
        fr = ex.fetch_funding_rates()
        tick = ex.fetch_tickers()
        spot_ex = ccxt.binance()
        spot_syms = set(spot_ex.load_markets().keys())
    except Exception as e:
        print("funding_carry: fetch failed", type(e).__name__)
        return

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    rows = []
    for sym, v in fr.items():
        r = v.get("fundingRate")
        if r is None:
            continue
        spot = sym.split(":")[0]           # BTC/USDT:USDT -> BTC/USDT
        if spot not in spot_syms:
            continue                        # need a spot leg to hedge
        qv = (tick.get(sym) or {}).get("quoteVolume") or 0
        if qv < MIN_QUOTE_VOL:
            continue                        # skip illiquid: basis risk too high
        ann = r * 3 * 365                    # 8h funding -> annualized
        if abs(ann) < MIN_ANN:
            continue
        rows.append({
            "ts": now, "symbol": sym, "spot": spot,
            "funding_8h": round(r, 6), "annualized": round(ann, 4),
            "side": "short-perp/long-spot" if r > 0 else "long-perp/short-spot",
            "perp_quote_vol_24h": round(qv),
            "mark": v.get("markPrice"),
            "note": "carry trade, basis+liquidation risk, NOT a lock",
        })
    rows.sort(key=lambda x: -abs(x["annualized"]))
    rows = rows[:TOP_N]
    if rows:
        pd.DataFrame(rows).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
    print(f"funding_carry: {len(rows)} liquid delta-neutral carry candidates "
          f"(>{MIN_ANN:.0%} ann, >{MIN_QUOTE_VOL/1e6:.0f}M vol)")
    for r in rows[:10]:
        print(f"  {r['symbol']:20s} ann {r['annualized']*100:+7.1f}%  "
              f"{r['side']:20s} vol ${r['perp_quote_vol_24h']/1e6:.0f}M")


if __name__ == "__main__":
    main()
