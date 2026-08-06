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

# ── paper->real fidelity ──────────────────────────────────────────────────
# The single biggest lie in maker paper P&L is assuming we fill 100% of the
# observed taker flow. In a live CLOB we are one of several makers in a queue,
# and we can never fill more than the size we actually had resting. So the
# live-realistic fill on any trade is capped at OUR_RESTING_SIZE. This
# surgically deflates the whale fills (a 16k-share print we'd never fully get)
# while leaving small fills near-intact — turning "ideal paper" into an
# estimate that would actually survive contact with the book.
OUR_RESTING_SIZE = 100.0   # shares we realistically rest per quote (~$50-100)
# Maker rebate: a filled maker order earns a category share of the taker fee
# (crypto 20%, sports 15%, politics/finance/etc 25%). Our fills skew crypto;
# 20% is the conservative blend. Rebate scales with the size we actually fill,
# so it's capped the same way markout is.
REBATE_FRAC = 0.20
MIN_EFF = 30       # min effective (Kish) sample size before a day can be "significant"


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def day_of(ts):
    return dt.datetime.fromtimestamp(float(ts), dt.timezone.utc).strftime("%Y-%m-%d")


def summarize(fills):
    """fills: list of (markout, size, fee) at the primary horizon. Returns the
    honest stats — ideal vs live-realistic P&L, plus effective sample size,
    significance, and outlier concentration all computed on the SAME quantity
    we gate on: the per-fill NET LIVE P&L (capped markout + capped rebate)."""
    net_live = []          # per-fill realistic P&L — the thing we actually judge
    mo_ideal = mo_live = reb_ideal = reb_live = 0.0
    for m, s, f in fills:
        cap = min(s, OUR_RESTING_SIZE) / s if s else 0.0
        mo_l, rb_l = m * min(s, OUR_RESTING_SIZE), REBATE_FRAC * f * cap
        net_live.append(mo_l + rb_l)
        mo_live += mo_l
        reb_live += rb_l
        mo_ideal += m * s
        reb_ideal += REBATE_FRAC * f
    total = sum(net_live)
    mean = st.mean(net_live)
    se = st.pstdev(net_live) / len(net_live) ** 0.5 if len(net_live) > 1 else float("inf")
    t = mean / se if se else 0.0
    # Kish effective sample size on the SAME distribution we gate on
    absn = [abs(p) for p in net_live]
    eff = (sum(absn) ** 2) / sum(p * p for p in absn) if any(absn) else 0.0
    top3 = sum(sorted(net_live, key=abs, reverse=True)[:3])
    return {
        "n": len(net_live),
        "eff_n": round(eff, 1),
        "mo_ideal": round(mo_ideal, 2),
        "mo_live": round(mo_live, 2),
        "rebate_live": round(reb_live, 2),
        "net_live": round(total, 2),
        "net_ideal": round(mo_ideal + reb_ideal, 2),
        "per_share": round(mo_ideal / sum(s for _, s, _ in fills), 6),
        "adverse_pct": round(sum(1 for m, _, _ in fills if m < 0) / len(fills), 3),
        "t_live": round(t, 2),
        "top3_share": round(top3 / total, 3) if total else 0.0,
        # a t-stat is meaningless on a handful of effective bets: require BOTH a
        # real effective-N and |t|>=2 before ever calling a day significant.
        "significant": abs(t) >= 2 and eff >= MIN_EFF,
    }


def main():
    if not LEDGER.exists():
        print("maker_pnl_real: no trade_markout.csv yet")
        return
    rows = list(csv.DictReader(LEDGER.open()))
    # maker fills = the taker's fee-bearing legs (we are the resting counterparty)
    days = {}
    for r in rows:
        fee = num(r.get("fee"))
        if fee in (None, 0):
            continue
        m, s, ts = num(r.get(PRIMARY)), num(r.get("size")), r.get("t")
        if m is None or not s or ts is None:
            continue
        try:
            days.setdefault(day_of(ts), []).append((m, s, fee))
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

    fields = ["date", "n", "eff_n", "mo_ideal", "mo_live", "rebate_live",
              "net_live", "net_ideal", "per_share", "adverse_pct", "t_live",
              "top3_share", "significant"]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for o in out:
            w.writerow({k: o[k] for k in fields})

    print(f"maker P&L (real fills, {PRIMARY}) — live = fill capped at "
          f"{OUR_RESTING_SIZE:.0f} sh, rebate @ {REBATE_FRAC:.0%} of taker fee:")
    for o in out:
        flag = "" if o["significant"] else "  [markout NOT significant]"
        print(f"  {o['date']}  n={o['n']:5d} (eff {o['eff_n']:5.1f})  "
              f"markout {o['mo_live']:+7.2f} + rebate {o['rebate_live']:+6.2f} "
              f"= NET LIVE {o['net_live']:+7.2f}  (t_mo {o['t_live']:+.2f}){flag}")
    tl = sum(o["net_live"] for o in out)
    sig = [o for o in out if o["significant"]]
    print(f"  ── net-live {tl:+.2f} over {len(out)} day(s); markout significant on "
          f"{len(sig)}. Edge rides on the rebate; the liquidity pool is a "
          f"pro-bot game we'd lose (see REWARD_CAPTURE_RESEARCH.md).")


if __name__ == "__main__":
    main()
