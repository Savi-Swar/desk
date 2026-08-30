"""Paper 0's comparison table: Polymarket vs equity microstructure, same units.

Equity side: taq_benchmark.csv (raw millisecond TAQ, Stoll decomposition,
10-11am, dollar-weighted, bps of price). Polymarket side: the same quantities
from real fills in collected/trade_markout.csv — eff_half relative to price,
realized = 30s markout, impact = eff - realized — split tight (crypto-style)
vs wide (esports-style) books.

    python papers/paper0/benchmark_table.py
"""
import csv
import pathlib

HERE = pathlib.Path(__file__).parent
C = HERE.parents[1] / "collected"


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def polymarket_rows():
    out = {"tight (<1c)": [], "wide (>3c)": []}
    with (C / "trade_markout.csv").open() as f:
        for r in csv.DictReader(f):
            fee, m, s, e, px = (num(r.get("fee")), num(r.get("mo_30s")),
                                num(r.get("size")), num(r.get("eff_half")),
                                num(r.get("price")))
            if fee in (None, 0) or None in (m, e) or not s or not px:
                continue
            if e <= 0:
                # wrong-side mid (26% of fills on wide books): the equity side
                # excludes crossed/locked quotes, so the comparison must too
                continue
            key = ("tight (<1c)" if e < 0.005 else
                   "wide (>3c)" if e >= 0.015 else None)
            if key is None:
                continue
            w = s * px                                # dollar weight
            out[key].append((e / px, m / px, (e - m) / px, w))
    table = {}
    for key, rows in out.items():
        if not rows:
            continue
        W = sum(w for *_, w in rows)
        table[key] = {
            "n": len(rows),
            "eff_bps": 1e4 * sum(e * w for e, _, _, w in rows) / W,
            "real_bps": 1e4 * sum(m * w for _, m, _, w in rows) / W,
            "impact_bps": 1e4 * sum(i * w for _, _, i, w in rows) / W,
        }
    return table


def taq_rows():
    table = {}
    agg = {}
    with (HERE / "taq_benchmark.csv").open() as f:
        for r in csv.DictReader(f):
            a = agg.setdefault(r["tier"], [0, 0.0, 0.0, 0.0])
            a[0] += 1
            a[1] += float(r["eff_bps"])
            a[2] += float(r["real_bps"])
            a[3] += float(r["impact_bps"])
    for tier, (k, e, re_, im) in agg.items():
        table[f"US equity {tier}-cap"] = {
            "n": k, "eff_bps": e / k, "real_bps": re_ / k, "impact_bps": im / k}
    return table


def main():
    rows = {}
    rows.update({f"Polymarket {k}": v for k, v in polymarket_rows().items()})
    rows.update(taq_rows())
    print(f"{'venue / book':26} {'eff half':>9} {'realized':>9} {'impact':>8}"
          f"   (bps of price, $-weighted, 30s horizon)")
    for k, v in rows.items():
        print(f"{k:26} {v['eff_bps']:9.1f} {v['real_bps']:+9.1f} "
              f"{v['impact_bps']:8.1f}")
    with (HERE / "benchmark_table.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["venue", "eff_bps", "real_bps", "impact_bps"])
        for k, v in rows.items():
            w.writerow([k, round(v["eff_bps"], 1), round(v["real_bps"], 1),
                        round(v["impact_bps"], 1)])


if __name__ == "__main__":
    main()
