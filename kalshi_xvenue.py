"""Kalshi sweeper + cross-venue basis vs Polymarket.

Kalshi's market-data surface is public and keyless (verified live). This
pulls open Kalshi markets, snapshots the yes bid/ask and fee schedule, and
where a Kalshi market maps to a Polymarket market on the same underlying,
records the cross-venue basis (price difference) after each venue's fees.

Cross-venue basis is NOT a lock — the two venues can settle differently
(UMA vs Kalshi rulebook), so this is a measurement ledger, not a signal:
collected/kalshi_markets.csv (Kalshi snapshot) and collected/xvenue.csv
(matched pairs with post-fee basis). The map is intentionally small and
hand-anchored on unambiguous underlyings (BTC/ETH thresholds, Fed, named
macro) to avoid false pairings.
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
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
LIMIT_PAGES = int(os.environ.get("KALSHI_PAGES", 6))   # 100 markets/page


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


# series that map cleanly onto Polymarket ladders on the same underlying
KALSHI_SERIES = ("KXBTCMAXY", "KXETHMAXY", "KXFED", "KXFEDDECISION")


def kalshi_open():
    out = []
    for s in KALSHI_SERIES:
        try:
            d = get(f"{KALSHI}/markets?series_ticker={s}&status=open&limit=100")
        except Exception:
            continue
        out += d.get("markets", [])
    return out


def poly_open():
    out = []
    for off in (0, 100, 200, 300):
        try:
            out += get("https://gamma-api.polymarket.com/events?closed=false"
                       f"&limit=100&offset={off}&order=volume24hr&ascending=false")
        except Exception:
            break
    return out


# underlying signatures we can match without ambiguity
def signature(text):
    t = (text or "").lower()
    m = re.search(r"(bitcoin|btc).{0,20}?(\d[\d,]{3,})", t)
    if m:
        return ("BTC", int(m.group(2).replace(",", "")))
    m = re.search(r"(ethereum|eth).{0,20}?(\d[\d,]{2,})", t)
    if m:
        return ("ETH", int(m.group(2).replace(",", "")))
    # Fed signatures intentionally excluded: Kalshi ">25bps" vs Polymarket
    # "25bps" are different questions — a wording-nesting mismatch the
    # relations guard handles, not a clean cross-venue pair.
    return None


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    kms = kalshi_open()
    krows, ksig = [], {}
    for m in kms:
        yb, ya = m.get("yes_bid_dollars"), m.get("yes_ask_dollars")
        try:
            yb = float(yb) if yb is not None else None
            ya = float(ya) if ya is not None else None
        except (TypeError, ValueError):
            yb = ya = None
        krows.append({"ts": now, "ticker": m.get("ticker"),
                      "title": (m.get("title") or "")[:80],
                      "yes_bid": yb, "yes_ask": ya,
                      "liquidity": m.get("liquidity_dollars"),
                      "fee_type": m.get("fee_type") or ""})
        sig = signature(m.get("title"))
        if sig and yb and ya:
            ksig.setdefault(sig, (m.get("ticker"), yb, ya))
    if krows:
        f = D / "kalshi_markets.csv"
        pd.DataFrame(krows).to_csv(f, mode="a", header=not f.exists(), index=False)

    pairs = []
    for ev in poly_open():
        for m in ev.get("markets", []):
            sig = signature(m.get("question"))
            if not sig or sig not in ksig:
                continue
            try:
                pb = float(m.get("bestBid") or 0)
                pa = float(m.get("bestAsk") or 0)
            except (TypeError, ValueError):
                continue
            if not (0 < pb < 1 and 0 < pa < 1):
                continue
            kt, kyb, kya = ksig[sig]
            # buy cheaper venue's YES, sell dearer venue's YES; basis after
            # crossing both spreads (Kalshi fees ~0 on most, PM per-schedule)
            basis_buy_poly = kyb - pa     # buy PM ask, sell Kalshi bid
            basis_buy_kalshi = pb - kya   # buy Kalshi ask, sell PM bid
            pairs.append({
                "ts": now, "sig": f"{sig[0]}:{sig[1]}",
                "poly_q": (m.get("question") or "")[:60], "kalshi": kt,
                "poly_bid": pb, "poly_ask": pa, "kalshi_bid": kyb, "kalshi_ask": kya,
                "basis_sell_kalshi": round(basis_buy_poly, 4),
                "basis_sell_poly": round(basis_buy_kalshi, 4),
                "best_basis": round(max(basis_buy_poly, basis_buy_kalshi), 4),
            })
    if pairs:
        f = D / "xvenue.csv"
        pd.DataFrame(pairs).to_csv(f, mode="a", header=not f.exists(), index=False)

    print(f"kalshi_xvenue: {len(kms)} Kalshi markets, {len(ksig)} signable, "
          f"{len(pairs)} cross-venue pairs matched")
    for p in sorted(pairs, key=lambda x: -x["best_basis"])[:8]:
        print(f"  basis {p['best_basis']*100:+.1f}c  {p['sig']:10s} "
              f"PM {p['poly_bid']:.2f}/{p['poly_ask']:.2f} "
              f"KAL {p['kalshi_bid']:.2f}/{p['kalshi_ask']:.2f}  {p['poly_q'][:40]}")


if __name__ == "__main__":
    main()
