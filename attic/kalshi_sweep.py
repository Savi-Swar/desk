"""Kalshi sweeper: second venue, keyless.

Kalshi's market-data REST surface needs no account or auth (verified live).
Two jobs per run:

1. Ladder arb scan: group open markets by event_ticker; for mutually
   exclusive events, sum the YES asks/bids across legs and price the same
   buy-all / sell-all locks we scan on Polymarket, net of Kalshi taker fees
   (0.07 * C * p * (1-p), rounded up per contract — the general schedule;
   series-specific multipliers exist and are logged, not assumed).
2. Cross-venue map: for topics both venues carry (Fed decisions, BTC/ETH
   levels, midterms control), log both venues' prices side by side into a
   basis ledger. Basis is NOT a lock (settlement sources differ); this is
   measurement only.

Appends collected/kalshi_arb.csv and collected/xvenue_basis.csv.
"""
import datetime
import json
import math
import pathlib
import urllib.request

import pandas as pd

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
KX = "https://api.elections.kalshi.com/trade-api/v2"

FEE_RATE = 0.07          # Kalshi general taker schedule
MIN_EDGE = 0.005


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def taker_fee(p):
    """Kalshi fees round up per contract; per-share approximation here,
    logged alongside gross so the rounding never hides in the net."""
    return FEE_RATE * p * (1.0 - p)


def pull_markets(pages=6):
    out, cursor = [], None
    for _ in range(pages):
        url = f"{KX}/markets?limit=1000&status=open"
        if cursor:
            url += f"&cursor={cursor}"
        d = get(url)
        out += d.get("markets", [])
        cursor = d.get("cursor")
        if not cursor:
            break
    return out


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    mkts = pull_markets()
    rows, basis = [], []

    # group by event; only binary legs with two-sided dollar quotes
    events = {}
    for m in mkts:
        yb, ya = m.get("yes_bid_dollars"), m.get("yes_ask_dollars")
        if yb is None or ya is None:
            continue
        try:
            yb, ya = float(yb), float(ya)
        except (TypeError, ValueError):
            continue
        if not (0 < ya <= 1 and 0 <= yb < 1):
            continue
        events.setdefault(m.get("event_ticker"), []).append(
            {"t": m.get("ticker"), "title": (m.get("title") or "")[:60],
             "yb": yb, "ya": ya,
             "vol": float(m.get("volume") or 0)})

    for ev, legs in events.items():
        if len(legs) < 3:
            continue
        tb = sum(l["yb"] for l in legs)
        ta = sum(l["ya"] for l in legs)
        fee_sell = sum(taker_fee(l["yb"]) for l in legs)
        fee_buy = sum(taker_fee(l["ya"]) for l in legs)
        for kind, gross, fee in (("SELL-ALL", tb - 1.0, fee_sell),
                                 ("BUY-ALL", 1.0 - ta, fee_buy)):
            net = gross - fee
            if net >= MIN_EDGE:
                rows.append({"ts": now, "event": ev, "n_legs": len(legs),
                             "type": kind, "gross": round(gross, 4),
                             "fee": round(fee, 4), "net": round(net, 4),
                             "title": legs[0]["title"],
                             "note": "mutual-exclusivity NOT verified from event flag; check before trusting"})

    # cross-venue basis on shared topics
    try