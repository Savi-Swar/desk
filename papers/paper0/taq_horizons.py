"""TAQ realized-spread HORIZON CURVE — the equity mirror of our markout curve.

Paper 0 measures Polymarket markout at 5s/30s/300s; this computes the same
curve on equities (one mega, one mid, one small cap), so Figure 3's repricing
story gets its yardstick over time-horizon too: equity realized spreads decay
toward zero as horizon grows; where they sit at each h anchors what a
"reasonable" markout looks like.

Run AFTER WRDS auth is restored (single connection, no retry loop — this
script must never probe):

    ~/lab/wrds-env/bin/python papers/paper0/taq_horizons.py
"""
import pathlib

import pandas as pd
import wrds

HERE = pathlib.Path(__file__).parent
DAY = "20260819"
SYMS = {"mega": "AAPL", "mid": "DKNG", "small": "SFIX"}
HORIZONS = (5, 30, 300)


def username():
    return open(pathlib.Path.home() / ".pgpass").read().split(":")[3]


def curve(db, sym):
    tr = db.raw_sql(f"""
        select time_m, price, size from taqmsec.ctm_{DAY}
        where sym_root='{sym}' and sym_suffix is null
          and time_m between '10:00' and '11:00'
          and price > 0 and tr_corr = '00'""")
    qu = db.raw_sql(f"""
        select time_m, best_bid, best_ask from taqmsec.complete_nbbo_{DAY}
        where sym_root='{sym}' and sym_suffix is null
          and time_m between '09:55' and '11:06'
          and best_bid > 0 and best_ask > best_bid""")
    if len(tr) < 50 or len(qu) < 50:
        return None
    for df in (tr, qu):
        df["t"] = pd.to_timedelta(df["time_m"].astype(str)).dt.total_seconds()
        df.sort_values("t", inplace=True)
    qu["mid"] = (qu["best_bid"] + qu["best_ask"]) / 2
    m = pd.merge_asof(tr, qu[["t", "mid"]], on="t", direction="backward")
    d = (m["price"] > m["mid"]).astype(int) - (m["price"] < m["mid"]).astype(int)
    tick = m["price"].diff().fillna(0)
    d = d.where(d != 0, (tick > 0).astype(int) - (tick < 0).astype(int))
    keep = d != 0
    m, d = m[keep], d[keep]
    w = m["size"] * m["price"]
    out = {"sym": sym,
           "eff_bps": float(1e4 * (d * (m["price"] - m["mid"]) / m["mid"] * w).sum() / w.sum())}
    for h in HORIZONS:
        fut = qu[["t", "mid"]].rename(columns={"mid": f"mid_{h}"})
        fut["t"] = fut["t"] - h
        mm = pd.merge_asof(m.sort_values("t"), fut.sort_values("t"),
                           on="t", direction="forward").dropna(subset=[f"mid_{h}"])
        dd = d.loc[mm.index]
        ww = w.loc[mm.index]
        real = dd * (mm["price"] - mm[f"mid_{h}"]) / mm["mid"]
        out[f"real_{h}s_bps"] = float(1e4 * (real * ww).sum() / ww.sum())
    return out


def main():
    db = wrds.Connection(wrds_username=username())
    rows = []
    for tier, sym in SYMS.items():
        r = curve(db, sym)
        if r:
            r["tier"] = tier
            rows.append(r)
            print(f"{tier:5s} {sym:5s} eff {r['eff_bps']:5.2f}  " +
                  "  ".join(f"real@{h}s {r[f'real_{h}s_bps']:+5.2f}" for h in HORIZONS))
    db.close()
    pd.DataFrame(rows).to_csv(HERE / "taq_horizons.csv", index=False)
    print("-> taq_horizons.csv (bps of price, $-weighted, 10-11am)")


if __name__ == "__main__":
    main()
