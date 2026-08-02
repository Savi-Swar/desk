"""Queue-calibrated fill model, measured from recorded books.

The implementation research flagged our maker sims' fill rule as the weak
link: they assume a resting order fills whenever the price touches it. That
is optimistic in a way that biases P&L upward, because fill probability is
negatively coupled to post-fill returns — the fills you get are the ones you
did not want (arXiv 2502.18625).

This replays book_recorder captures and measures the real thing:

  queue      shares resting at a price level when a hypothetical order joins
  consumed   how much of that level trades through afterwards
  filled     consumed >= queue_ahead + our size, i.e. the queue cleared past us
  markout    mid move at 5s / 30s / 300s after the fill; negative = adverse

Usage:
    python fill_model.py <capture.jsonl.gz> [more.jsonl.gz ...]

Writes collected/fill_model.csv (one row per simulated resting order) and
prints the calibration table the sims consume: fill rate and mean markout by
distance-from-mid bucket.
"""
import glob
import gzip
import json
import pathlib
import sys
from collections import defaultdict

import pandas as pd

D = pathlib.Path(__file__).parent / "collected"
OUT = D / "fill_model.csv"

OUR_SIZE = 100.0                 # shares we would rest
MARKOUTS = (5, 30, 300)          # seconds
JOIN_EVERY_S = 30                # how often we hypothetically place an order


def events(path):
    """Yield (t, event_dict) in recorded order."""
    for line in gzip.open(path, "rt"):
        d = json.loads(line)
        if "meta" in d:
            continue
        m = d["m"]
        m = json.loads(m) if isinstance(m, str) else m
        for e in (m if isinstance(m, list) else [m]):
            yield d["t"], e


def replay(path):
    """Reconstruct per-asset books, place hypothetical resting asks on a
    timer, and follow each one until filled or the capture ends."""
    books = defaultdict(lambda: {"bids": {}, "asks": {}})
    mids = defaultdict(list)                  # asset -> [(t, mid)]
    pending = []                              # live hypothetical orders
    done = []
    next_join = None

    for t, e in events(path):
        et = e.get("event_type")
        if et == "book":
            a = e.get("asset_id")
            books[a]["bids"] = {float(x["price"]): float(x["size"])
                                for x in e.get("bids", [])}
            books[a]["asks"] = {float(x["price"]): float(x["size"])
                                for x in e.get("asks", [])}
        elif et == "price_change":
            for pc in e.get("price_changes", []):
                a = pc.get("asset_id")
                px, sz = float(pc["price"]), float(pc["size"])
                side = "bids" if pc.get("side") == "BUY" else "asks"
                prev = books[a][side].get(px, 0.0)
                books[a][side][px] = sz
                # a level shrinking is the observable proxy for trade-through
                if sz < prev:
                    consumed = prev - sz
                    for o in pending:
                        if o["asset"] == a and o["side"] == side and \
                                o["price"] == px and not o["filled"]:
                            o["consumed"] += consumed
                            if o["consumed"] >= o["queue_ahead"] + OUR_SIZE:
                                o["filled"] = True
                                o["fill_t"] = t
        elif et == "last_trade_price":
            pass

        # track mid for markout
        for a, bk in books.items():
            if bk["bids"] and bk["asks"]:
                bb, ba = max(bk["bids"]), min(bk["asks"])
                if bb < ba:
                    if not mids[a] or t - mids[a][-1][0] > 1:
                        mids[a].append((t, (bb + ba) / 2))

        # place a new hypothetical order set every JOIN_EVERY_S
        if next_join is None:
            next_join = t
        if t >= next_join:
            next_join = t + JOIN_EVERY_S
            for a, bk in books.items():
                if not (bk["bids"] and bk["asks"]):
                    continue
                bb, ba = max(bk["bids"]), min(bk["asks"])
                if not (bb < ba):
                    continue
                mid = (bb + ba) / 2
                # join the best ask (passive sell) — the maker's default
                pending.append({
                    "asset": a, "side": "asks", "price": ba,
                    "queue_ahead": bk["asks"].get(ba, 0.0),
                    "consumed": 0.0, "filled": False, "t0": t,
                    "mid0": mid, "dist": round(ba - mid, 4),
                    "fill_t": None})

        # retire orders that filled long enough ago to score markout
        still = []
        for o in pending:
            if o["filled"] and t - o["fill_t"] >= max(MARKOUTS):
                for h in MARKOUTS:
                    tgt = o["fill_t"] + h
                    series = mids[o["asset"]]
                    m_at = next((m for (tm, m) in series if tm >= tgt), None)
                    # we sold at o["price"]; adverse if mid rose after
                    o[f"markout_{h}s"] = None if m_at is None else round(o["price"] - m_at, 5)
                done.append(o)
            elif t - o["t0"] > 900:      # unfilled after 15 min: expire
                done.append(o)
            else:
                still.append(o)
        pending = still

    for o in pending:
        done.append(o)
    return done


def main():
    paths = sys.argv[1:] or sorted(glob.glob(str(D / "books" / "*" / "*.jsonl.gz")))
    if not paths:
        print("fill_model: no captures found")
        return
    rows = []
    for p in paths:
        for o in replay(p):
            rows.append({
                "capture": pathlib.Path(p).name, "asset": o["asset"][:16],
                "rest_price": o["price"], "dist_from_mid": o["dist"],
                "queue_ahead": round(o["queue_ahead"], 1),
                "consumed": round(o["consumed"], 1),
                "filled": int(o["filled"]),
                "secs_to_fill": None if not o["filled"] else round(o["fill_t"] - o["t0"], 1),
                **{f"markout_{h}s": o.get(f"markout_{h}s") for h in MARKOUTS},
            })
    df = pd.DataFrame(rows)
    if not len(df):
        print("fill_model: no orders simulated")
        return
    df.to_csv(OUT, mode="a", header=not OUT.exists(), index=False)

    df["bucket"] = pd.cut(df["dist_from_mid"],
                          [-1, 0.002, 0.005, 0.01, 0.02, 1],
                          labels=["<=0.2c", "0.2-0.5c", "0.5-1c", "1-2c", ">2c"])
    tbl = df.groupby("bucket", observed=True).agg(
        orders=("filled", "size"),
        fill_rate=("filled", "mean"),
        med_queue=("queue_ahead", "median"),
        med_secs=("secs_to_fill", "median"),
        mo_5s=("markout_5s", "mean"),
        mo_30s=("markout_30s", "mean"),
        mo_300s=("markout_300s", "mean"),
    ).round(4)
    print(f"fill_model: {len(df)} simulated resting orders from {len(paths)} capture(s)")
    print(tbl.to_string())
    f = df[df["filled"] == 1]
    if len(f):
        print(f"\nfilled {len(f)} ({len(f)/len(df):.1%}) | "
              f"mean markout 5s {f['markout_5s'].mean():+.5f} "
              f"30s {f['markout_30s'].mean():+.5f} "
              f"300s {f['markout_300s'].mean():+.5f}")
        print("negative markout = the mid moved against the fill (adverse selection)")


if __name__ == "__main__":
    main()
