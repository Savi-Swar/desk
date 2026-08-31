"""Phase 2 flagship: does a D-1 NWP forecast beat the weather-market crowd?

Model v0, deliberately simple and fully walk-forward:
  For each calendar month m, fit per-city (offset, sigma) on all families
  ENDING BEFORE m: offset = median(winner_mid − forecast) maps the GFS grid
  point onto the market's resolution station (the dataset notes show up to
  5°C station-vs-grid gaps, so this is load-bearing, not a nicety); sigma =
  robust std of the residual. Then price month-m buckets as Normal(fc +
  offset, sigma) probabilities, and bet marked families through the engine.

Marks are last-trade prints and sum >1 per family (see
weather_artifact_check.md), so entry prices are haircut via engine slippage
and we also report the price-free skill diagnostic (log-loss vs the
vig-renormalized crowd) which no stale print can fake.

    python backtest/weather_model.py
"""
import csv
import gzip
import math
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import os

import engine
import stats

D = pathlib.Path(__file__).parents[1] / "data"
MIN_FIT = 30          # min prior families per city before we trade it
EDGE_MIN = 0.05       # only bet buckets where model - price >= 5pp
FEE = 0.05
SLIP = int(os.environ.get("SLIP", 150))       # thin-book slippage bps
FRESH_LO = float(os.environ.get("FRESH_LO", 0.0))   # family Σmarks freshness gate
FRESH_HI = float(os.environ.get("FRESH_HI", 9.9))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


ECMWF = {}


def load():
    fams = defaultdict(list)
    with gzip.open(D / "weather_families.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            fams[r["family_id"]].append(r)
    try:
        with gzip.open(D / "weather_ecmwf_d1.csv.gz", "rt") as f:
            for r in csv.DictReader(f):
                ECMWF[(r["city"], r["date"])] = float(r["fc_ecmwf_d1"])
    except FileNotFoundError:
        pass
    return fams


def family_meta(rows):
    r0 = rows[0]
    fc, act = num(r0["fc_d1_tmax"]), num(r0["actual_tmax"])
    win = [r for r in rows if r["won"] == "1"]
    if fc is None or len(win) != 1:
        return None
    # ensemble mean with ECMWF when the sidecar has it (ECMWF is the stronger
    # deterministic model; GFS-only was v0 and lost to the crowd). The sidecar
    # is °C; fc_d1_tmax is already in FAMILY units — convert before averaging
    # (the unconverted version averaged °F with °C and cost 0.06 log-loss).
    ec = ECMWF.get((r0["city"], r0["date"]))
    if ec is not None:
        if (r0.get("unit") or "").upper() == "F":
            ec = ec * 9 / 5 + 32
        fc = (fc + ec) / 2
    lo, hi = num(win[0]["bucket_lo"]), num(win[0]["bucket_hi"])
    if lo is None and hi is None:
        return None
    mid = (lo if hi is None or hi > 1e8 else
           hi if lo is None or lo < -1e8 else (lo + hi) / 2)
    return {"city": r0["city"], "date": r0["date"], "fc": fc,
            "winner_mid": mid, "rows": rows}


def bucket_prob(lo, hi, mu, sigma):
    lo = -1e9 if lo is None or lo < -1e8 else lo
    hi = 1e9 if hi is None or hi > 1e8 else hi
    # exact one-degree ladders are stored lo==hi: continuity-correct
    if abs(hi - lo) < 1e-9:
        lo, hi = lo - 0.5, hi + 0.5
    return max(1e-6, phi((hi - mu) / sigma) - phi((lo - mu) / sigma))


def main():
    fams = load()
    metas = [m for m in (family_meta(v) for v in fams.values()) if m]
    metas.sort(key=lambda m: m["date"])
    print(f"families usable: {len(metas):,}")

    bets, ll_model, ll_crowd, n_ll = [], 0.0, 0.0, 0
    hist = defaultdict(list)          # city -> [(date, resid)]
    by_month_fit = defaultdict(lambda: defaultdict(list))
    for m in metas:
        by_month_fit[m["date"][:7]][m["city"]].append(m)

    months = sorted(by_month_fit)
    for mi, month in enumerate(months):
        # fit on everything strictly before this month
        fit = defaultdict(list)
        for pm in months[:mi]:
            for city, ms in by_month_fit[pm].items():
                fit[city].extend(m["winner_mid"] - m["fc"] for m in ms)
        for city, ms in by_month_fit[month].items():
            resid = fit.get(city, [])
            if len(resid) < MIN_FIT:
                continue
            resid_s = sorted(resid)
            off = resid_s[len(resid_s) // 2]
            dev = sorted(abs(x - off) for x in resid_s)
            sigma = max(0.8, 1.4826 * dev[len(dev) // 2])   # robust, floored
            for m in ms:
                mu = m["fc"] + off
                # per-bucket model probs + marks
                probs, marks = [], []
                for r in m["rows"]:
                    p_mod = bucket_prob(num(r["bucket_lo"]), num(r["bucket_hi"]),
                                        mu, sigma)
                    probs.append((r, p_mod, num(r["p24"])))
                tot = sum(p for _, p, _ in probs)
                probs = [(r, p / tot, mk) for r, p, mk in probs]
                mk_tot = sum(mk for _, _, mk in probs if mk is not None)
                fresh = mk_tot and FRESH_LO <= mk_tot <= FRESH_HI
                for r, p_mod, mk in probs:
                    won = r["won"] == "1"
                    # log-loss vs vig-free crowd (needs full family marks)
                    if mk is not None and mk_tot and mk_tot > 0.5:
                        q = max(1e-6, min(1 - 1e-6, mk / mk_tot))
                        pm_ = max(1e-6, min(1 - 1e-6, p_mod))
                        y = 1.0 if won else 0.0
                        ll_model += -(y * math.log(pm_) + (1 - y) * math.log(1 - pm_))
                        ll_crowd += -(y * math.log(q) + (1 - y) * math.log(1 - q))
                        n_ll += 1
                    # trade only clear model-vs-price edges, long only
                    if fresh and mk is not None and 0.02 <= mk <= 0.95 and \
                            p_mod - mk >= EDGE_MIN:
                        bets.append({"date": m["date"], "p_model": p_mod,
                                     "p_mkt": mk, "won": won,
                                     "fee_rate": FEE, "slip_bps": SLIP})

    print(f"\nprice-free skill (vig-renormalized crowd vs model, {n_ll:,} buckets):")
    if n_ll:
        print(f"  mean log-loss  model {ll_model/n_ll:.4f}   crowd {ll_crowd/n_ll:.4f}"
              f"   -> {'MODEL BETTER' if ll_model < ll_crowd else 'crowd better'}"
              f" by {(ll_crowd-ll_model)/n_ll:+.4f}")

    res = engine.run(bets)
    print(f"\nengine (long model-edge>= {EDGE_MIN:.0%}, fee {FEE}, slip {SLIP}bps):")
    print(" ", engine.summary(res, "weather-v0"))
    if res["n_days"]:
        rets = list(res["daily"].values())
        pos = sum(1 for x in rets if x > 0)
        print(f"  positive days {pos}/{len(rets)}  "
              f"avg daily {sum(rets)/len(rets)*1e4:+.1f} bps of bankroll")


if __name__ == "__main__":
    main()
