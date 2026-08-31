"""Candidate: forecast-conditioned warm-adjacent bucket.

Prior (price-free, artifact-checked): temperature ladders are placed cold —
winners land above ladder center 45.8% vs 23.2% below (t=+3.0, 15 months).
Prices partially adjust; the open question is whether the residual lives in
the bucket just WARMER than where the model points.

Pre-registered trade, before any results were seen:
  For each family with a D-1 forecast, >=5 marked buckets, and freshness
  Sigma(p24) in [0.90, 1.20]: fit per-city offset on PRIOR months only
  (median winner_mid - fc, >=30 prior families). Find the bucket containing
  (fc + offset); BUY YES on the bucket one step warmer, iff its p24 <= 0.35.
  One bet per family. Fees 0.07*p*(1-p); slip 100 (and 200 reported).
  VERDICT RULE: claimable only if capped AND flat modes both positive with
  PSR >= 0.95, month-clustered family t >= 2 over >= 8 months, and the sign
  survives slip 200.

    python backtest/warm_bucket.py
"""
import csv
import gzip
import math
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import engine

D = pathlib.Path(__file__).parents[1] / "data"
MIN_FIT = 30


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    fams = defaultdict(list)
    with gzip.open(D / "weather_families.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            fams[r["family_id"]].append(r)

    metas = []
    for fid, rows in fams.items():
        r0 = rows[0]
        fc = num(r0["fc_d1_tmax"])
        win = [r for r in rows if r["won"] == "1"]
        if fc is None or len(win) != 1:
            continue
        lo, hi = num(win[0]["bucket_lo"]), num(win[0]["bucket_hi"])
        mid = (lo if hi is None or hi > 1e8 else
               hi if lo is None or lo < -1e8 else (lo + hi) / 2)
        metas.append({"city": r0["city"], "date": r0["date"], "fc": fc,
                      "wmid": mid, "rows": rows})
    metas.sort(key=lambda m: m["date"])
    by_month = defaultdict(lambda: defaultdict(list))
    for m in metas:
        by_month[m["date"][:7]][m["city"]].append(m)
    months = sorted(by_month)

    for slip in (100, 200):
        bets, fam_月 = [], defaultdict(list)
        for mi, month in enumerate(months):
            fit = defaultdict(list)
            for pm in months[:mi]:
                for c, ms in by_month[pm].items():
                    fit[c].extend(x["wmid"] - x["fc"] for x in ms)
            for c, ms in by_month[month].items():
                resid = sorted(fit.get(c, []))
                if len(resid) < MIN_FIT:
                    continue
                off = resid[len(resid) // 2]
                for m in ms:
                    mu = m["fc"] + off
                    # order buckets, find model bucket, take one warmer
                    bs = []
                    for r in m["rows"]:
                        lo, hi = num(r["bucket_lo"]), num(r["bucket_hi"])
                        klo = -1e9 if lo is None or lo < -1e8 else lo
                        bs.append((klo, lo, hi, r))
                    bs.sort()
                    tot = sum(num(r["p24"]) or 0 for *_x, r in bs)
                    if not 0.90 <= tot <= 1.20:
                        continue
                    idx = None
                    for i, (_k, lo, hi, r) in enumerate(bs):
                        L = -1e9 if lo is None or lo < -1e8 else lo
                        H = 1e9 if hi is None or hi > 1e8 else hi
                        if abs(H - L) < 1e-9:
                            L, H = L - 0.5, H + 0.5
                        if L <= mu < H:
                            idx = i
                            break
                    if idx is None or idx + 1 >= len(bs):
                        continue
                    r = bs[idx + 1][3]
                    p = num(r["p24"])
                    if p is None or not 0.02 <= p <= 0.35:
                        continue
                    won = r["won"] == "1"
                    bets.append({"date": m["date"], "p_model": min(0.99, p + 0.06),
                                 "p_mkt": p, "won": won,
                                 "fee_rate": 0.07, "slip_bps": slip})
                    fam_月[month].append((1 - p) if won else -p)
        capped = engine.run(bets)
        flat = engine.run(bets, flat=0.0025)
        d = [sum(v) / len(v) for v in fam_月.values() if len(v) >= 3]
        mt = 0.0
        if len(d) >= 4:
            mm = sum(d) / len(d)
            se = (sum((x - mm) ** 2 for x in d) / (len(d) - 1)) ** 0.5 / math.sqrt(len(d))
            mt = mm / se if se else 0.0
        both_pos = capped["total_return"] > 0 and flat["total_return"] > 0
        ok = (both_pos and capped["psr"] >= 0.95 and flat["psr"] >= 0.95
              and mt >= 2 and len(d) >= 8)
        print(f"slip {slip}: {len(bets)} bets over {len(fam_月)} months")
        print(f"  capped SR {capped['sharpe']:+.2f} PSR {capped['psr']:.2f} "
              f"ret {capped['total_return']*100:+.0f}%   "
              f"flat SR {flat['sharpe']:+.2f} PSR {flat['psr']:.2f} "
              f"ret {flat['total_return']*100:+.0f}%")
        print(f"  month-clustered t={mt:+.2f} ({len(d)} months)  ->  "
              f"{'CLAIMABLE' if ok else 'not claimable'}\n")


if __name__ == "__main__":
    main()
