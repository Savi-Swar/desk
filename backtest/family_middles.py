"""Candidate: within-family middles-vs-tails (vig-immune relative value).

The weather artifact check found, AFTER vig renormalization: tail buckets
~2.6x overpriced, middle buckets underpriced +1.6pp (t=+3.5). That was a
description; this is the trade, pre-registered BEFORE looking at results:

  Universe: temperature-ladder families with >=5 marked buckets and family
  Sigma(p24) in [0.90, 1.20] (freshness gate — stale-print families excluded,
  mirage #5/#6 lesson).
  Trade per family: BUY YES on interior buckets (ladder positions strictly
  between the outermost two on each side) at the p24 mark; BUY NO on the two
  outermost buckets on each side at (1 - p24). Equal stake per leg.
  Costs: taker fee 0.07*p*(1-p) per share; slippage 100bps (and 200 report).
  Walk-forward: no training needed (structural, parameter-free).
  VERDICT RULE (pre-registered): claimable only if capped AND flat engine
  modes agree on positive sign, PSR >= 0.95 in both, month-clustered mean
  family P&L t >= 2 with >= 8 months, and it survives slip 200.

    python backtest/family_middles.py
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

    for slip in (100, 200):
        bets = []
        fam_pnl_month = defaultdict(list)
        n_fam = 0
        for fid, rows in fams.items():
            marked = [(r, num(r["p24"])) for r in rows]
            marked = [(r, p) for r, p in marked if p is not None and 0 < p < 1]
            if len(marked) < 5:
                continue
            tot = sum(p for _, p in marked)
            if not 0.90 <= tot <= 1.20:
                continue
            # order buckets by lo bound (tails at ends)
            def key(rp):
                lo = num(rp[0]["bucket_lo"])
                return -1e9 if lo is None or lo < -1e8 else lo
            marked.sort(key=key)
            date = rows[0]["date"]
            n_fam += 1
            fam_p = 0.0
            for i, (r, p) in enumerate(marked):
                won = r["won"] == "1"
                is_tail = i < 2 or i >= len(marked) - 2
                if is_tail:
                    b = {"date": date, "p_model": max(0.001, p - 0.05),
                         "p_mkt": p, "won": won,
                         "fee_rate": 0.07, "slip_bps": slip}
                else:
                    b = {"date": date, "p_model": min(0.999, p + 0.05),
                         "p_mkt": p, "won": won,
                         "fee_rate": 0.07, "slip_bps": slip}
                bets.append(b)
                # equal-stake family P&L for the clustered test (pre-cost sign
                # check on renormalized q)
                q = p / tot
                fam_p += ((1 - q) if won else -q) if not is_tail else \
                         ((-q) if won else (1 - q) * q / max(1e-6, 1 - q) * 0)
            fam_pnl_month[date[:7]].append(fam_p)

        capped = engine.run(bets)
        flat = engine.run(bets, flat=0.0025)
        d = [sum(v) / len(v) for v in fam_pnl_month.values() if len(v) >= 3]
        mt = 0.0
        if len(d) >= 4:
            m = sum(d) / len(d)
            se = (sum((x - m) ** 2 for x in d) / (len(d) - 1)) ** 0.5 / math.sqrt(len(d))
            mt = m / se if se else 0.0
        agree = (capped["total_return"] > 0) == (flat["total_return"] > 0)
        both_pos = capped["total_return"] > 0 and flat["total_return"] > 0
        ok = (both_pos and capped["psr"] >= 0.95 and flat["psr"] >= 0.95
              and mt >= 2 and len(d) >= 8)
        print(f"slip {slip}: {n_fam} families, {len(bets)} legs")
        print(f"  capped: SR {capped['sharpe']:+.2f} PSR {capped['psr']:.2f} "
              f"ret {capped['total_return']*100:+.0f}%")
        print(f"  flat  : SR {flat['sharpe']:+.2f} PSR {flat['psr']:.2f} "
              f"ret {flat['total_return']*100:+.0f}%   modes "
              f"{'AGREE' if agree else 'DISAGREE'}")
        print(f"  month-clustered family-P&L t={mt:+.2f} ({len(d)} months)")
        print(f"  PRE-REGISTERED VERDICT: "
              f"{'CLAIMABLE' if ok else 'not claimable'}\n")


if __name__ == "__main__":
    main()
