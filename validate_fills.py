"""Trade-print validator for the fill model.

The fill model infers fills from order-book level shrinkage (a price_change
where size dropped). But a level can shrink because it TRADED or because it
was CANCELLED, and only trades are real fills. This validator replays the
raw recordings and cross-checks shrinkage against the ground truth — the
`last_trade_price` prints, which fire only on actual matched trades.

It answers the one question that decides whether the markout is trustworthy:
of the "fills" the model counts, how many coincide with a real trade at that
price and time? A low ratio means the markout is measuring cancels (benign
by nature), which would explain a too-clean adverse rate.

    python validate_fills.py <books.jsonl.gz ...>   (defaults to all local)

Writes collected/fill_validation.csv.
"""
import glob
import gzip
import json
import pathlib
import sys

import pandas as pd

D = pathlib.Path(__file__).parent / "collected"


def events(path):
    for line in gzip.open(path, "rt"):
        d = json.loads(line)
        if "meta" in d:
            continue
        m = d["m"]
        m = json.loads(m) if isinstance(m, str) else m
        for e in (m if isinstance(m, list) else [m]):
            yield d["t"], e


def analyze(path):
    shrink_events = 0        # price_change where a level lost size (proxy fill)
    trade_prints = 0         # real trades
    trade_matched = 0        # shrink events with a trade at same asset+price within 2s
    prev_size = {}           # (asset, side, price) -> size
    recent_trades = []       # (t, asset, price)

    for t, e in events(path):
        et = e.get("event_type")
        if et == "last_trade_price":
            trade_prints += 1
            recent_trades.append((t, e.get("asset_id"), float(e.get("price") or 0)))
            recent_trades = [x for x in recent_trades if t - x[0] <= 2.0]
        elif et == "price_change":
            for pc in e.get("price_changes", []):
                a = pc.get("asset_id")
                side = pc.get("side")
                px = float(pc.get("price") or 0)
                sz = float(pc.get("size") or 0)
                key = (a, side, px)
                if key in prev_size and sz < prev_size[key]:
                    shrink_events += 1
                    # was there a real trade at this asset+price in the last 2s?
                    if any(abs(tp - px) < 1e-9 and ta == a
                           for (_, ta, tp) in recent_trades):
                        trade_matched += 1
                prev_size[key] = sz
    return {"file": pathlib.Path(path).name,
            "shrink_fills": shrink_events, "trade_prints": trade_prints,
            "shrink_matched_to_trade": trade_matched,
            "match_ratio": round(trade_matched / shrink_events, 4) if shrink_events else None}


def main():
    paths = sys.argv[1:] or sorted(glob.glob(str(D / "books" / "*" / "*.jsonl.gz")))
    if not paths:
        # fall back to any local scratch recordings
        paths = sorted(glob.glob(str(pathlib.Path.home() /
                       ".claude/**/scratchpad/**/*.jsonl.gz"), recursive=True))
    if not paths:
        print("validate_fills: no recordings found")
        return
    rows = [analyze(p) for p in paths]
    df = pd.DataFrame(rows)
    if len(df):
        df.to_csv(D / "fill_validation.csv", mode="a",
                  header=not (D / "fill_validation.csv").exists(), index=False)
    tot_shrink = df["shrink_fills"].sum()
    tot_trade = df["trade_prints"].sum()
    tot_match = df["shrink_matched_to_trade"].sum()
    print(f"validate_fills: {len(paths)} recording(s)")
    print(f"  shrinkage 'fills' (what the model counts): {tot_shrink:,}")
    print(f"  real trade prints (ground truth):          {tot_trade:,}")
    print(f"  shrink events matched to a real trade:     {tot_match:,}")
    if tot_shrink:
        print(f"  => only {tot_match/tot_shrink:.1%} of counted fills coincide with a real trade")
        print(f"  => the fill model overcounts fills by ~{tot_shrink/max(tot_match,1):.0f}x")


if __name__ == "__main__":
    main()
