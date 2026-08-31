"""OOS verification of Study 1's crypto-favorites candidate.

Claim under test: crypto outcome-0 priced in [0.5, 0.95] at T-h resolves ABOVE
its price (favorites underpriced). Design:

  TRAIN  endDate <  2025-07-01: estimate the gap (that's all we take from it)
  TEST   endDate >= 2025-07-01: (a) did the raw gap persist? (month-clustered)
                                (b) does BUYING the favorite make money net of
                                    fees through the engine?

Artifact guards, pre-committed: p_mkt capped at 0.95 (near-resolution pinning
is correct pricing, not edge), one bet per market per horizon, crypto only via
the slug classifier. Fees: taker feeRate 0.07 (worst category rate — if the
edge dies at the worst fee it was never real); slippage 100bps.

    python backtest/oos_crypto_fav.py
"""
import math
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import engine
from market_cats import cat_of
from study_longshot import read_gz_tolerant, load_slugs, D

SPLIT = "2025-07-01"
LO, HI = 0.50, 0.95


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def month_t(obs):
    """month-clustered mean gap and t. obs: (month, gap)."""
    cl = defaultdict(list)
    for mo, g in obs:
        cl[mo].append(g)
    d = [sum(v) / len(v) for v in cl.values() if len(v) >= 5]
    if len(d) < 4:
        return None, None, len(d)
    m = sum(d) / len(d)
    se = (sum((x - m) ** 2 for x in d) / (len(d) - 1)) ** 0.5 / math.sqrt(len(d))
    return m, (m / se if se else 0.0), len(d)


def main():
    rows = read_gz_tolerant(D / "price_marks.csv.gz")
    slugs = load_slugs()
    for horizon in (24, 168):
        train, test, bets = [], [], []
        for r in rows:
            p = num(r.get(f"p_{horizon}h"))
            if p is None or not LO <= p < HI:
                continue
            s, q = slugs.get(r.get("id"), ("", ""))
            if cat_of(s, q) != "crypto":
                continue
            ed = r.get("endDate") or ""
            won = 1.0 if r["winner_idx"] == "0" else 0.0
            if ed[:10] < SPLIT:
                train.append((ed[:7], won - p))
            else:
                test.append((ed[:7], won - p))
                bets.append({"date": ed[:10], "p_mkt": p, "won": won == 1.0,
                             "fee_rate": 0.07, "slip_bps": 100})
        g_tr, t_tr, m_tr = month_t(train)
        g_te, t_te, m_te = month_t(test)
        print(f"=== T-{horizon}h crypto favorites [{LO},{HI}) ===")
        print(f"  TRAIN n={len(train):5d}  gap {g_tr:+.4f}  t={t_tr:+.2f}  ({m_tr} months)")
        print(f"  TEST  n={len(test):5d}  gap {g_te:+.4f}  t={t_te:+.2f}  ({m_te} months)"
              f"   <- OOS {'PERSISTS' if (t_te or 0) >= 2 and (g_te or 0) > 0 else 'FAILS'}")
        # engine backtest on the TEST period: model = market + trained gap
        for b in bets:
            b["p_model"] = min(0.99, b["p_mkt"] + (g_tr or 0.0))
        res = engine.run(bets)
        print(f"  ENGINE OOS: {engine.summary(res, f'buy-crypto-fav@{horizon}h')}\n")


if __name__ == "__main__":
    main()
