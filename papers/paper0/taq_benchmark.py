"""Equity microstructure benchmark for Paper 0 — from raw millisecond TAQ.

Same decomposition as the Polymarket table (markout_decomp.py), on NYSE/Nasdaq
names across liquidity tiers: effective half-spread at the trade, realized
half-spread at +30s, price impact = effective - realized. Lee-Ready signing
(midpoint test, tick fallback). One fixed liquid hour (10:00-11:00) so tiers
are compared on the same clock.

Run inside the WRDS venv (uses ~/.pgpass; username parsed from it):

    ~/lab/wrds-env/bin/python papers/paper0/taq_benchmark.py

Writes taq_benchmark.csv next to this script; the paper's comparison table
regenerates from that plus collected/trade_markout.csv.
"""
import pathlib

import pandas as pd
import wrds

HERE = pathlib.Path(__file__).parent
DAYS = ("20260818", "20260819")
TIERS = {"mega": ("AAPL", "NVDA", "MSFT"),
         "mid": ("DKNG", "RBLX", "ETSY"),
         "small": ("SFIX", "BGFV", "GPRO")}
H = 30            # realized-spread horizon, seconds


def username():
    return open(pathlib.Path.home() / ".pgpass").read().split(":")[3]


def one(db, day, sym):
    tr = db.raw_sql(f"""
        select time_m, price, size from taqmsec.ctm_{day}
        where sym_root='{sym}' and sym_suffix is null
          and time_m between '10:00' and '11:00'
          and price > 0 and tr_corr = '00'""")
    if len(tr) < 50:
        return None
    qu = db.raw_sql(f"""
        select time_m, best_bid, best_ask from taqmsec.complete_nbbo_{day}
        where sym_root='{sym}' and sym_suffix is null
          and time_m between '09:55' and '11:01'
          and best_bid > 0 and best_ask > best_bid""")
    if len(qu) < 50:
        return None
    for df in (tr, qu):
        df["t"] = pd.to_timedelta(df["time_m"].astype(str)).dt.total_seconds()
        df.sort_values("t", inplace=True)
    qu["mid"] = (qu["best_bid"] + qu["best_ask"]) / 2

    m = pd.merge_asof(tr, qu[["t", "mid"]], on="t", direction="backward")
    fut = qu[["t", "mid"]].rename(columns={"mid": "mid_fut"})
    fut["t"] = fut["t"] - H                     # trade at t sees quote at t+H
    m = pd.merge_asof(m.sort_values("t"), fut.sort_values("t"),
                      on="t", direction="forward")
    m = m.dropna(subset=["mid", "mid_fut"])

    # Lee-Ready: midpoint test, tick test on at-mid trades
    d = (m["price"] > m["mid"]).astype(int) - (m["price"] < m["mid"]).astype(int)
    tick = m["price"].diff().fillna(0)
    d = d.where(d != 0, (tick > 0).astype(int) - (tick < 0).astype(int))
    m = m[d != 0]
    d = d[d != 0]

    eff = d * (m["price"] - m["mid"]) / m["mid"]        # relative half-spreads
    real = d * (m["price"] - m["mid_fut"]) / m["mid"]
    imp = eff - real
    w = m["size"] * m["price"]
    return {"sym": sym, "day": day, "n": len(m),
            "eff_bps": 1e4 * (eff * w).sum() / w.sum(),
            "real_bps": 1e4 * (real * w).sum() / w.sum(),
            "impact_bps": 1e4 * (imp * w).sum() / w.sum()}


def main():
    db = wrds.Connection(wrds_username=username())
    rows = []
    for tier, syms in TIERS.items():
        for sym in syms:
            for day in DAYS:
                try:
                    r = one(db, day, sym)
                except Exception as e:
                    print(f"  {sym} {day}: {type(e).__name__}")
                    r = None
                if r:
                    r["tier"] = tier
                    rows.append(r)
                    print(f"  {tier:5s} {sym:5s} {day}  n={r['n']:6,}  "
                          f"eff {r['eff_bps']:5.2f}  real {r['real_bps']:+5.2f}  "
                          f"impact {r['impact_bps']:5.2f} bps")
    db.close()
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "taq_benchmark.csv", index=False)
    print("\ndollar-weighted by tier (bps of price):")
    print(df.groupby("tier")[["eff_bps", "real_bps", "impact_bps"]]
            .mean().round(2).to_string())


if __name__ == "__main__":
    main()
