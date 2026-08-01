"""Continuous arb watch. Runs inside each 30-minute CI slot and samples the
venue every ~60 seconds for WATCH_MIN minutes, so coverage is near-constant
instead of one glance per half hour.

Logging model fixes the old sampler's double count: one row per opportunity
per run — first-seen edge and size, plus how many minutes it persisted and
its peak edge — rather than one row per glance at the same resting orders.
Appends to collected/arb_fills.csv with the same columns plus persistence.
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

WATCH_MIN = float(os.environ.get("WATCH_MIN", 24))   # minutes; override per workflow
STEP_S = 60           # seconds between sweeps
MIN_EDGE = 0.005
BOOK_BUDGET = 6       # events depth-checked per sweep


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())




def leg_fee(m, price):
    """Taker fee per share at execution price, from the market's fee schedule
    (economics fees, Mar 2026: rate * p*(1-p), takerOnly). Zero if disabled."""
    if not m.get("feesEnabled"):
        return 0.0
    fs = m.get("feeSchedule") or {}
    rate = float(fs.get("rate") or 0.0)
    exp = float(fs.get("exponent") or 1.0)
    return rate * (price * (1.0 - price)) ** exp

def sweep():
    """One pass: candidates from top-of-book, depth-verify the best few.
    Returns {(event, type): fill_dict}."""
    out = {}
    try:
        evs = get("https://gamma-api.polymarket.com/events?closed=false"
                  "&limit=300&order=volume24hr&ascending=false")
    except Exception:
        return out
    # rank candidates before spending the book budget: fee-free events first
    # (the only surface where taker arb still works at ~1c edges), then by
    # top-of-book edge
    cands = []
    for ev in evs:
        mkts = ev.get("markets", [])
        if len(mkts) < 3 or not ev.get("negRisk", False):
            continue
        if ev.get("negRiskAugmented"):
            continue      # placeholder outcomes make sell-all a false lock
        try:
            bids = [float(m.get("bestBid") or 0) for m in mkts]
            asks = [float(m.get("bestAsk") or 0) for m in mkts]
        except (TypeError, ValueError):
            continue
        if not all(0 < a <= 1 for a in asks):
            continue
        top_edge = max(sum(bids) - 1.0, 1.0 - sum(asks))
        if top_edge < MIN_EDGE:
            continue
        fee_free = not any(m.get("feesEnabled") for m in mkts)
        cands.append((fee_free, top_edge, ev))
    cands.sort(key=lambda c: (not c[0], -c[1]))
    for fee_free, top_edge, ev in cands[:BOOK_BUDGET]:
        mkts = ev.get("markets", [])
        legs, ok = [], True
        for m in mkts:
            try:
                toks = json.loads(m.get("clobTokenIds", "[]"))
                book = get(f"https://clob.polymarket.com/book?token_id={toks[0]}")
                b, a = book.get("bids", []), book.get("asks", [])
                bid = float(b[-1]["price"]) if b else 0
                ask = float(a[-1]["price"]) if a else 1
                legs.append({
                    "bid": bid, "ask": ask,
                    "bid_sz": float(b[-1]["size"]) if b else 0,
                    "ask_sz": float(a[-1]["size"]) if a else 0,
                    "fee_sell": leg_fee(m, bid), "fee_buy": leg_fee(m, ask)})
            except Exception:
                ok = False
                break
        if not ok or not legs:
            continue
        tb, ta = sum(l["bid"] for l in legs), sum(l["ask"] for l in legs)
        fee_sell = sum(l["fee_sell"] for l in legs)
        fee_buy = sum(l["fee_buy"] for l in legs)
        near_res = int(max(l["bid"] for l in legs) >= 0.95)
        title = ev.get("title", "")[:60]
        for kind, gross, fee, size in (
                ("SELL-ALL", tb - 1.0, fee_sell, min(l["bid_sz"] for l in legs)),
                ("BUY-ALL", 1.0 - ta, fee_buy, min(l["ask_sz"] for l in legs))):
            net = gross - fee
            if net >= MIN_EDGE and size > 0:
                out[(title, kind)] = {
                    "event": title, "type": kind,
                    "edge_pershare": round(net, 4),
                    "gross_edge": round(gross, 4),
                    "fee_perset": round(fee, 4),
                    "exec_size": round(size, 1),
                    "profit_at_depth": round(net * size, 2),
                    "n_legs": len(legs), "near_res": near_res}
    return out


def main():
    start = time.monotonic()
    seen = {}    # (event, type) -> first fill dict + persistence tracking
    sweeps = 0
    while time.monotonic() - start < WATCH_MIN * 60:
        t0 = time.monotonic()
        now_iso = datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds")
        for key, fill in sweep().items():
            if key in seen:
                rec = seen[key]
                rec["persist_min"] = round((time.monotonic()
                                            - rec["_t0"]) / 60, 1)
                rec["peak_edge"] = max(rec["peak_edge"], fill["edge_pershare"])
            else:
                fill["ts"] = now_iso
                fill["persist_min"] = 0.0
                fill["peak_edge"] = fill["edge_pershare"]
                fill["_t0"] = time.monotonic()
                seen[key] = fill
        sweeps += 1
        time.sleep(max(0, STEP_S - (time.monotonic() - t0)))

    rows = []
    for rec in seen.values():
        rec.pop("_t0", None)
        rows.append(rec)
    if rows:
        f = D / "arb_fills.csv"
        pd.DataFrame(rows).to_csv(f, mode="a", header=not f.exists(),
                                  index=False)
    print(f"arb_watch: {sweeps} sweeps over {WATCH_MIN} min, "
          f"{len(rows)} distinct opportunities")
    for r in rows:
        print(f"  ${r['profit_at_depth']:8.2f}  {r['type']:8s} "
              f"{r['edge_pershare']*100:.1f}c x {r['exec_size']:,.0f} sh  "
              f"persisted {r['persist_min']}m  nr={r['near_res']}  {r['event']}")


if __name__ == "__main__":
    main()
