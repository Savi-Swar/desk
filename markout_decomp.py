"""Markout decomposition — is the favorable markout real edge or spread capture?

Splits each real maker fill's markout into the two microstructure components:

  realized_markout = effective_half_spread  -  price_impact(adverse selection)

  effective_half_spread = |fill_price - mid_at_fill|   (what a TOUCH maker earns
      by selling at the ask / buying at the bid — the taker crossed to us)
  price_impact          = signed mid drift from fill to fill+h  (adverse if the
      mid runs through where we filled)

The catch this exposes: our markout books the fill at the TRADE price (the
touch, which on wide markets is far from mid), so it credits the full effective
half-spread. But a reward-earning maker must quote NEAR THE MID (within
rewardsMaxSpread), so it never fills at that wide touch and never captures that
spread. So we also reprice the edge for a near-mid quoter resting at offset d
from mid: captured spread = min(d, eff_half), edge = that - price_impact.

    python markout_decomp.py            # newest local book+trade capture
"""
import glob
import gzip
import json
import pathlib
import statistics as st
import sys
from bisect import bisect_left

D = pathlib.Path(__file__).parent / "collected"
H = 30                      # markout horizon (s) — matches the gate's mo_30s
CAP = 100.0                 # our realistic quote size (shares)
QUOTE_OFFSETS = (0.001, 0.005, 0.01)   # near-mid quote distances to reprice at


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
        return


def build_books(book_paths):
    """asset -> sorted [(t, bid, ask)] — keep the full touch, not just mid."""
    best, series = {}, {}
    for p in book_paths:
        for d in read(p):
            t = d["t"]
            m = d["m"]
            m = json.loads(m) if isinstance(m, str) else m
            for e in (m if isinstance(m, list) else [m]):
                et = e.get("event_type")
                touched = []
                if et == "book":
                    a = e.get("asset_id")
                    bids, asks = e.get("bids", []), e.get("asks", [])
                    bb = float(bids[-1]["price"]) if bids else 0.0
                    ba = float(asks[-1]["price"]) if asks else 1.0
                    best[a] = [bb, ba]
                    touched = [a]
                elif et == "price_change":
                    for pc in e.get("price_changes", []):
                        a = pc.get("asset_id")
                        b = best.setdefault(a, [0.0, 1.0])
                        b[0] = float(pc.get("best_bid") or b[0])
                        b[1] = float(pc.get("best_ask") or b[1])
                        touched.append(a)
                for a in touched:
                    b = best.get(a)
                    if b and 0 < b[0] < b[1] <= 1:
                        series.setdefault(a, []).append((t, b[0], b[1]))
    for a in series:
        series[a].sort()
    return series


def at(series, t):
    """(bid, ask) at-or-after t, or None."""
    i = bisect_left(series, (t,))
    return (series[i][1], series[i][2]) if i < len(series) else None


def main():
    books = sorted(glob.glob(str(D / "books" / "*" / "*.jsonl.gz")))
    trades = sorted(glob.glob(str(D / "trades" / "*" / "*.jsonl.gz")))
    if not books or not trades:
        print(f"need book ({len(books)}) and trade ({len(trades)}) files")
        return
    books_ser = build_books(books)

    recs = []
    for tp in trades:
        for d in read(tp):
            if d.get("fee") in (None, 0) or not d.get("fee"):
                continue                       # only fee-bearing (real maker) fills
            a = d.get("asset")
            ser = books_ser.get(a)
            if not ser:
                continue
            try:
                px = float(d["price"])
                t = float(d.get("ts") or d["t"])
                sz = float(d["size"])
            except (KeyError, TypeError, ValueError):
                continue
            f0 = at(ser, t)
            fh = at(ser, t + H)
            if not f0 or not fh:
                continue
            m0 = (f0[0] + f0[1]) / 2
            mh = (fh[0] + fh[1]) / 2
            half_spread = (f0[1] - f0[0]) / 2
            sold = d.get("side") == "BUY"      # taker bought -> maker sold
            eff_half = (px - m0) if sold else (m0 - px)   # spread captured at touch
            impact = (mh - m0) if sold else (m0 - mh)     # adverse if positive
            realized = eff_half - impact                  # == existing markout
            recs.append({"sz": min(sz, CAP), "spread": half_spread * 2,
                         "eff_half": eff_half, "impact": impact, "realized": realized})
    if not recs:
        print("no fills matched a recorded book")
        return

    def dollars(key):
        return sum(r[key] * r["sz"] for r in recs)

    print(f"maker fills decomposed: {len(recs)}  (horizon {H}s, size capped {CAP:.0f})\n")
    print(f"  spread capture (eff_half) : {dollars('eff_half'):+9.2f}   <- vanishes if we quote near mid")
    print(f"  price impact (adverse)    : {dollars('impact'):+9.2f}   <- the real tax, stays")
    print(f"  realized markout (=mo)    : {dollars('realized'):+9.2f}   = capture - impact\n")

    # by spread width — the inflation should concentrate in wide markets
    buckets = (("tight <1c", 0, .01), ("mid 1-3c", .01, .03), ("wide >3c", .03, 9))
    print("  by spread width:      n    capture$   impact$   realized$")
    for name, lo, hi in buckets:
        b = [r for r in recs if lo <= r["spread"] < hi]
        if not b:
            continue
        cap = sum(r["eff_half"] * r["sz"] for r in b)
        imp = sum(r["impact"] * r["sz"] for r in b)
        rea = sum(r["realized"] * r["sz"] for r in b)
        print(f"    {name:10s} {len(b):6d}  {cap:+9.2f} {imp:+9.2f} {rea:+9.2f}")

    # reprice for a near-mid quoter: captured spread = min(offset, eff_half)
    print("\n  near-mid reprice (edge = captured_spread - adverse, per fill):")
    print(f"    {'as measured (fill at touch)':32s} {dollars('realized'):+9.2f}")
    for d in QUOTE_OFFSETS:
        edge = sum((min(d, max(r['eff_half'], 0)) - r['impact']) * r['sz'] for r in recs)
        print(f"    quote {d*100:.1f}c from mid{'':17s} {edge:+9.2f}")
    print("\n  (rebate income is separate and additive to all of the above.)")


if __name__ == "__main__":
    main()
