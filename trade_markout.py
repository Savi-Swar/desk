"""Trade-based markout — the real racecar engine.

Replaces the shrinkage fill model (which overcounted fills ~1,500x by
treating cancels as fills). Here a fill is a REAL trade from the firehose,
and markout is measured against the book mid reconstructed from the recorder.

Logic: a passive maker on the opposite side of a real trade is filled at the
trade price. For a BUY trade, the passive side SOLD at that price; adverse
selection = the mid rising afterward. We reconstruct mid(asset, t) from the
book recording, match each firehose trade on an asset we have a book for,
and measure mid movement at 5s/30s/300s after the trade — signed so that
negative always means the passive side got run over.

Reads the current run's book + trade recordings, appends per-trade markout
to collected/trade_markout.csv (the gate metric, now on real fills).

    python trade_markout.py           # newest book+trade dirs
"""
import glob
import gzip
import json
import pathlib
import sys
from bisect import bisect_left

D = pathlib.Path(__file__).parent / "collected"
OUT = D / "trade_markout.csv"
MARKOUTS = (5, 30, 300)


def read(path):
    try:
        for line in gzip.open(path, "rt"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            if "meta" not in d:
                yield d
    except (EOFError, OSError):
        return   # truncated/half-written gzip: use what we got, don't crash


def build_mids(book_paths):
    """asset -> sorted [(t, mid)] from book snapshots + price_change diffs."""
    best = {}                       # asset -> [bb, ba]
    mids = {}                       # asset -> list of (t, mid)
    for p in book_paths:
        for d in read(p):
            t = d["t"]
            m = d["m"]
            m = json.loads(m) if isinstance(m, str) else m
            for e in (m if isinstance(m, list) else [m]):
                et = e.get("event_type")
                if et == "book":
                    a = e.get("asset_id")
                    bids, asks = e.get("bids", []), e.get("asks", [])
                    bb = float(bids[-1]["price"]) if bids else 0.0
                    ba = float(asks[-1]["price"]) if asks else 1.0
                    best[a] = [bb, ba]
                elif et == "price_change":
                    for pc in e.get("price_changes", []):
                        a = pc.get("asset_id")
                        b = best.setdefault(a, [0.0, 1.0])
                        b[0] = float(pc.get("best_bid") or b[0])
                        b[1] = float(pc.get("best_ask") or b[1])
                a = e.get("asset_id") if et == "book" else None
                for a2, b in ([(a, best[a])] if a else
                              [(pc.get("asset_id"), best.get(pc.get("asset_id")))
                               for pc in e.get("price_changes", [])] if et == "price_change" else []):
                    if a2 and b and 0 < b[0] < b[1] <= 1:
                        mids.setdefault(a2, []).append((t, (b[0] + b[1]) / 2))
    for a in mids:
        mids[a].sort()
    return mids


def mid_at(series, t):
    """mid at-or-after t, or None if past the record."""
    i = bisect_left(series, (t,))
    return series[i][1] if i < len(series) else None


def main():
    bdir = sys.argv[1] if len(sys.argv) > 1 else None
    tdir = sys.argv[2] if len(sys.argv) > 2 else None
    books = sorted(glob.glob(bdir or str(D / "books" / "*" / "*.jsonl.gz")))
    trades = sorted(glob.glob(tdir or str(D / "trades" / "*" / "*.jsonl.gz")))
    if not books or not trades:
        print(f"trade_markout: need both book ({len(books)}) and trade ({len(trades)}) files")
        return
    mids = build_mids(books)
    rows = []
    for tp in trades:
        for d in read(tp):
            a = d.get("asset")
            if a not in mids:
                continue
            try:
                px = float(d["price"])
                # real trade timestamp for exact markout timing; fall back to
                # our receive time only if ts is missing
                t = float(d.get("ts") or d["t"])
            except (KeyError, TypeError, ValueError):
                continue
            fee = d.get("fee")
            series = mids[a]
            row = {"t": round(t, 1), "asset": a[:16], "side": d.get("side"),
                   "price": px, "size": d.get("size"),
                   "fee": fee, "slug": d.get("slug")}
            passive_sold = d.get("side") == "BUY"   # aggressor bought => maker sold
            for h in MARKOUTS:
                m = mid_at(series, t + h)
                if m is None:
                    row[f"mo_{h}s"] = None
                else:
                    # passive sold at px: adverse if mid rose -> negative markout
                    row[f"mo_{h}s"] = round((px - m) if passive_sold else (m - px), 5)
            if any(row.get(f"mo_{h}s") is not None for h in MARKOUTS):
                rows.append(row)
    if not rows:
        print("trade_markout: no trades matched a recorded book (asset overlap empty)")
        return
    import statistics as st
    OUT.parent.mkdir(exist_ok=True)
    import csv
    write_header = not OUT.exists()
    with OUT.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if write_header:
            w.writeheader()
        w.writerows(rows)
    for h in MARKOUTS:
        vals = [r[f"mo_{h}s"] for r in rows if r.get(f"mo_{h}s") is not None]
        if vals:
            adverse = sum(1 for v in vals if v < 0) / len(vals)
            print(f"  mo_{h}s  n={len(vals):5d}  mean {st.mean(vals):+.5f}  "
                  f"median {st.median(vals):+.5f}  adverse {adverse:.0%}")
    print(f"trade_markout: {len(rows)} real-trade markouts on overlapping assets")


if __name__ == "__main__":
    main()
