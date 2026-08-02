"""Limitless <-> Polymarket cross-venue collector on the crypto up/down surface.

Limitless (on-chain PM, keyless) runs the same "ASSET Up or Down" markets as
Polymarket. Where the same asset + same resolution date appear on both, this
logs the cross-venue price basis.

CRITICAL CAVEAT, enforced in the output: two "Bitcoin up or down" markets are
the same tradable event ONLY if they resolve on the same price oracle at the
same snapshot time. That is not yet verified (it is a live research question),
so every row is stamped resolution_verified=False and the basis is a
MEASUREMENT, not a tradable signal. No lock is claimed until oracle + snapshot
equivalence is confirmed. Output: collected/limitless_xvenue.csv.
"""
import datetime
import json
import os
import pathlib
import re
import urllib.request

import pandas as pd

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
OUT = D / "limitless_xvenue.csv"

ASSETS = {"bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH",
          "solana": "SOL", "sol": "SOL", "xrp": "XRP", "dogecoin": "DOGE",
          "doge": "DOGE"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def asset_of(text):
    t = (text or "").lower()
    for k, v in ASSETS.items():
        if k in t:
            return v
    return None


def limitless_updown():
    """asset -> (yes_price, no_price) for DAILY up/down markets."""
    try:
        d = get("https://api.limitless.exchange/markets/active")
    except Exception:
        return {}
    ms = d.get("data", d) if isinstance(d, dict) else d
    out = {}
    for m in ms:
        title = m.get("title") or m.get("proxyTitle") or ""
        if "up or down" not in title.lower() or "daily" not in title.lower():
            continue
        a = asset_of(title)
        pr = m.get("prices") or []
        if a and len(pr) >= 2:
            out[a] = (float(pr[0]) / (100 if pr[0] > 1 else 1),
                      float(pr[1]) / (100 if pr[1] > 1 else 1))
    return out


def poly_updown():
    """asset -> (yes_bid, yes_ask) for today's up/down markets."""
    evs = get("https://gamma-api.polymarket.com/events?closed=false"
              "&limit=200&order=volume24hr&ascending=false")
    out = {}
    for ev in evs:
        if "up or down" not in (ev.get("title") or "").lower():
            continue
        a = asset_of(ev.get("title"))
        for m in ev.get("markets", []):
            try:
                b = float(m.get("bestBid") or 0)
                k = float(m.get("bestAsk") or 0)
            except (TypeError, ValueError):
                continue
            if a and 0 < b < 1 and 0 < k < 1:
                out[a] = (b, k)
    return out


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    lim, pol = limitless_updown(), poly_updown()
    rows = []
    for a in set(lim) & set(pol):
        ly, ln = lim[a]
        pb, pa = pol[a]
        # basis both directions (a lock ONLY if resolution-equivalent)
        basis_buy_poly = ly - pa       # buy PM ask, sell Limitless yes
        basis_buy_lim = pb - (1 - ln)  # buy Limitless (1-no as ask proxy), sell PM bid
        rows.append({
            "ts": now, "asset": a,
            "poly_bid": pb, "poly_ask": pa, "lim_yes": ly, "lim_no": ln,
            "basis": round(max(abs(basis_buy_poly), abs(basis_buy_lim)), 4),
            # FALSIFIED 2026-08-02: not a lock. Limitless resolves on Pyth Pro
            # BTC/USD, Polymarket on Binance BTC/USDT 1-min candle — different
            # source AND different denomination (USD vs USDT). Same ~16:00 UTC
            # snapshot but the prices can diverge, so both legs can resolve the
            # same way. This is a correlated SPREAD with basis risk, not arb.
            "oracle_identical": False,
            "poly_source": "binance-btcusdt-1m", "lim_source": "pyth-pro-btcusd",
        })
    if rows:
        pd.DataFrame(rows).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
    print(f"limitless_xvenue: {len(lim)} Limitless daily up/down, {len(pol)} Polymarket, "
          f"{len(rows)} matched")
    for r in sorted(rows, key=lambda x: -x["basis"]):
        print(f"  {r['asset']}: PM {r['poly_bid']:.3f}/{r['poly_ask']:.3f} "
              f"LIM {r['lim_yes']:.3f} | basis {r['basis']*100:.1f}c "
              f"(resolution-equivalence UNVERIFIED — measurement only)")


if __name__ == "__main__":
    main()
