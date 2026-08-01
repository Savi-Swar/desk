"""Single-condition arb watcher: the surface the tape says actually pays.

The fee-boundary study of the HuggingFace v1 tape (Mar 23 - Apr 6 2026)
found 97% of surviving post-fee arb in Price Action markets, captured as
single-condition pairs: one market, both outcomes bought for a combined
price under $1. That is a different structure from the neg-risk ladders
every other detector here scans, so it needs its own scanner.

Per market, the YES and NO books are pulled separately (they are distinct
CLOB tokens and quote independently):

    BUY-BOTH  profitable when ask_yes + ask_no < 1 - fees
    SELL-BOTH profitable when bid_yes + bid_no > 1 + fees

Fees are per leg at that leg's execution price from its own schedule, which
is why the tails of price-action ladders survive a 7% rate: the p(1-p) term
collapses near 0 and 1.

Sizing is the thinner leg. One row per opportunity per run with persistence,
appended to collected/single_cond.csv.
"""
import datetime
import json
import os
import pathlib
import time
import urllib.request

import pandas as pd

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
OUT = D / "single_cond.csv"

WATCH_MIN = float(os.environ.get("WATCH_MIN", 24))   # minutes; override per workflow
STEP_S = 60
MIN_NET = 0.002        # 0.2c/share net of fees — these captures are small
MIN_VOL24 = 5_000      # skip dead markets
BOOK_BUDGET = 24       # markets book-checked per sweep
PA_HINTS = ("bitcoin", "ethereum", "crypto", "solana", "xrp", "dogecoin",
            "price action", "token launch", "fdv")


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def leg_fee(m, price):
    if not m.get("feesEnabled"):
        return 0.0
    fs = m.get("feeSchedule") or {}
    rate = float(fs.get("rate") or 0.0)
    exp = float(fs.get("exponent") or 1.0)
    return rate * (price * (1.0 - price)) ** exp


def top(book_side, default):
    """CLOB books come best-last."""
    return (float(book_side[-1]["price"]), float(book_side[-1]["size"])) \
        if book_side else (default, 0.0)


def candidates():
    """Price-action markets by 24h volume, with both token ids."""
    evs = []
    for off in (0, 100, 200):
        evs += get("https://gamma-api.polymarket.com/events?closed=false"
                   f"&limit=100&offset={off}&order=volume24hr&ascending=false")
    out = []
    for ev in evs:
        vol = float(ev.get("volume24hr") or 0)
        if vol < MIN_VOL24:
            continue
        tags = " ".join((t.get("label") or "") for t in (ev.get("tags") or [])).lower()
        title = (ev.get("title") or "").lower()
        if not any(h in tags or h in title for h in PA_HINTS):
            continue
        for m in ev.get("markets", []):
            try:
                toks = json.loads(m.get("clobTokenIds", "[]"))
            except Exception:
                continue
            if len(toks) < 2:
                continue
            out.append((vol, m, toks))
    out.sort(key=lambda c: -c[0])
    return out[:BOOK_BUDGET]


def sweep():
    found = {}
    for vol, m, toks in candidates():
        try:
            by = get(f"https://clob.polymarket.com/book?token_id={toks[0]}")
            bn = get(f"https://clob.polymarket.com/book?token_id={toks[1]}")
        except Exception:
            continue
        ay, ay_sz = top(by.get("asks", []), 1.0)
        by_, by_sz = top(by.get("bids", []), 0.0)
        an, an_sz = top(bn.get("asks", []), 1.0)
        bn_, bn_sz = top(bn.get("bids", []), 0.0)
        q = (m.get("question") or "")[:60]

        buy_gross = 1.0 - (ay + an)
        buy_fee = leg_fee(m, ay) + leg_fee(m, an)
        sell_gross = (by_ + bn_) - 1.0
        sell_fee = leg_fee(m, by_) + leg_fee(m, bn_)

        for kind, gross, fee, size, px in (
                ("BUY-BOTH", buy_gross, buy_fee, min(ay_sz, an_sz), (ay, an)),
                ("SELL-BOTH", sell_gross, sell_fee, min(by_sz, bn_sz), (by_, bn_))):
            net = gross - fee
            if net >= MIN_NET and size > 0:
                found[(q, kind)] = {
                    "question": q, "type": kind,
                    "net_edge": round(net, 4), "gross_edge": round(gross, 4),
                    "fee_perpair": round(fee, 4),
                    "yes_px": px[0], "no_px": px[1],
                    "size": round(size, 1),
                    "profit_at_depth": round(net * size, 2),
                    "vol24h": round(vol),
                }
    return found


def main():
    start = time.monotonic()
    seen, sweeps = {}, 0
    while time.monotonic() - start < WATCH_MIN * 60:
        t0 = time.monotonic()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        for key, f in sweep().items():
            if key in seen:
                rec = seen[key]
                rec["persist_min"] = round((time.monotonic() - rec["_t0"]) / 60, 1)
                rec["peak_edge"] = max(rec["peak_edge"], f["net_edge"])
            else:
                f["ts"] = now
                f["persist_min"] = 0.0
                f["peak_edge"] = f["net_edge"]
                f["_t0"] = time.monotonic()
                seen[key] = f
        sweeps += 1
        time.sleep(max(0, STEP_S - (time.monotonic() - t0)))

    rows = []
    for rec in seen.values():
        rec.pop("_t0", None)
        rows.append(rec)
    if rows:
        pd.DataFrame(rows).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
    print(f"single_cond: {sweeps} sweeps, {len(rows)} opportunities net of fees")
    for r in sorted(rows, key=lambda x: -x["profit_at_depth"])[:10]:
        print(f"  ${r['profit_at_depth']:7.2f}  {r['type']:9s} net {r['net_edge']*100:.2f}c "
              f"(gross {r['gross_edge']*100:.2f}c fee {r['fee_perpair']*100:.2f}c) "
              f"x {r['size']:,.0f} sh  {r['persist_min']}m  {r['question']}")


if __name__ == "__main__":
    main()
