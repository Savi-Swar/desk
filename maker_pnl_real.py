"""Trustworthy maker P&L, built on real fills — not the shrinkage model.

The old maker_net/maker_net3 ledgers counted book shrinkage as fills, which
overcounted ~1,500x (cancels ≫ trades). This computes maker markout P&L from
the firehose's REAL matched trades (trade_markout.csv), and it identifies the
maker side correctly:

  On Polymarket the TAKER pays the fee. So a trade row that carries a fee is
  the taker's leg — which means WE, as the resting maker, are the counterparty.
  trade_markout already signs markout from the passive/maker perspective, so
  the fee-bearing rows give the maker's adverse selection with the right sign.
  (Using all rows averages both symmetric legs to ~0 and hides the signal.)

Just as important: the number never ships naked. Each daily line carries the
size-weighted mean, a t-stat, and how concentrated the P&L is in its top few
fills — because on thin data a "profit" is usually a couple of whales, not an
edge. A day is only 'significant' when |t| >= 2.

    python maker_pnl_real.py     # recompute per-day summary over the whole ledger
"""
import csv
import datetime as dt
import pathlib
import statistics as st

D = pathlib.Path(__file__).parent / "collected"
LEDGER = D / "trade_markout.csv"
OUT = D / "maker_pnl_real.csv"
HORIZONS = ("mo_5s", "mo_30s", "mo_300s")
PRIMARY = "mo_30s"


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def day_of(ts):
    return dt.datetime.fromtimestamp(float(ts), dt.timezone.utc).strftime("%Y-%m-%d")


def summarize(fills):
    """fills: list of (markout, size) at the primary horizon. Returns the
    honest stats — total $, per-share, significance, outlier concentration."""
    pnl = [m * s for m, s in fills]
    total = sum(pnl)
    sw = total / sum(s for _, s in fills)
    mean = st.mean(pnl)
    se = st.pstdev(pnl) / len(pnl) ** 0.5 if len(pnl) > 1 else float("inf")
    t = mean / se if se else 0.0
    top3 = sum(sorted(pnl, key=abs, reverse=True)[:3])
    return {
        "n": len(pnl),
        "pnl": round(total, 2),
        "per_share": round(sw, 6),
        "adverse_pct": round(sum(1 for p in pnl if p < 0) / len(pnl), 3),
        "t_stat": round(t, 2),
        "top3_share": round(top3 / total, 3) if total else 0.0,
        "significant": abs(t) >= 2,
    }


def main():
    if not LEDGER.exists():
        print("maker_pnl_real: no trade_markout.csv yet")
        return
    rows = list(csv.DictReader(LEDGER.open()))
    # maker fills = the taker's fee-bearing legs (we are the resting counterparty)
    days = {}
    for r in rows:
        if num(r.get("fee")) in (None, 0):
            continue
        m, s, ts = num(r.get(PRIMARY)), num(r.get("size")), r.get("t")
        if m is None or not s or ts is None:
            continue
        try:
            days.setdefault(day_of(ts), []).append((m, s))
        except (ValueError, OverflowError, OSError):
            continue
    if not days:
        print("maker_pnl_real: no fee-bearing maker fills in ledger yet")
        return

    out = []
    for day in sorted(days):
        stats = summarize(days[day])
        stats["date"] = day
        out.append(stats)

    fields = ["date", "n", "pnl", "per_share", "adverse_pct",
              "t_stat", "top3_share", "significant"]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for o in out:
            w.writerow({k: o[k] for k in fields})

    print(f"maker P&L (real fills, {PRIMARY}) — {len(out)} day(s):")
    for o in out:
        flag = "" if o["significant"] else "  [NOT significant — noise]"
        print(f"  {o['date']}  n={o['n']:5d}  P&L {o['pnl']:+8.2f}  "
              f"({o['per_share']:+.5f}/sh, {o['adverse_pct']:.0%} adverse)  "
              f"t={o['t_stat']:+.2f}  top3={o['top3_share']:+.0%}{flag}")
    tot = sum(o["pnl"] for o in out)
    sig = [o for o in out if o["significant"]]
    print(f"  ── total paper markout P&L {tot:+.2f} over {len(out)} day(s); "
          f"{len(sig)} day(s) statistically significant. "
          f"Reward income is separate and additive.")


if __name__ == "__main__":
    main()
