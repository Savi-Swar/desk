"""OOS verification of the de-pinned finding: longshots overpriced everywhere.

The pinned-price fix (PINNED_PRICE_CHECK.md) left 12 month-clustered cells in
5 category groups, all one direction: realized below implied — buyers of
longshots overpay. Trade under test: when outcome-0 is priced in [0.03,0.35),
buy the NO side (the engine chooses it automatically when p_model < p_mkt).

Same protocol as the crypto-favorites test that DIED here (STUDY1_OOS.md):
train gap per (category, horizon) on endDate < 2025-07-01, freeze, test
after; pinned marks excluded on BOTH sides; bet-weighted; fees 0.07 worst
case; slip 100bps; one bet per market-horizon.

    python backtest/oos_longshots.py
"""
import math
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import engine
import study_longshot as S

SPLIT = "2025-07-01"
LO, HI = 0.03, 0.35
GROUPS = ("crypto", "politics", "geopolitics", "weather", "other")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def month_t(obs):
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
    rows = S.read_gz_tolerant(S.MARKS)
    S.SLUGS = S.load_slugs()
    for horizon in (24, 72):
        gaps = {}
        test_obs, bets = [], []
        per_group = {g: [] for g in GROUPS}
        for r in rows:
            p = num(r.get(f"p_{horizon}h"))
            if p is None or not LO <= p < HI or S.pinned(r, horizon):
                continue
            g = S.cat_group(r)
            if g not in GROUPS:
                continue
            ed = r.get("endDate") or ""
            won = 1.0 if r["winner_idx"] == "0" else 0.0
            if ed[:10] < SPLIT:
                per_group[g].append((ed[:7], won - p))
            else:
                test_obs.append((g, ed, p, won))
        for g in GROUPS:
            m, t, k = month_t(per_group[g])
            gaps[g] = m if (m is not None and t is not None and t <= -1) else None
        trained = {g: v for g, v in gaps.items() if v is not None}
        print(f"=== T-{horizon}h longshots [{LO},{HI}) — trained gaps: "
              + ", ".join(f"{g} {v:+.3f}" for g, v in trained.items()))

        te = [(ed[:7], won - p) for g, ed, p, won in test_obs if g in trained]
        m_te, t_te, k_te = month_t(te)
        bw = (sum(won - p for g, ed, p, won in test_obs if g in trained)
              / max(1, sum(1 for g, ed, p, won in test_obs if g in trained)))
        n_te = sum(1 for g, ed, p, won in test_obs if g in trained)
        print(f"  TEST raw gap: month-clustered {m_te:+.4f} (t={t_te:+.2f}, "
              f"{k_te} months)   bet-weighted {bw:+.4f}  (n={n_te:,})")

        for g, ed, p, won in test_obs:
            if g not in trained:
                continue
            bets.append({"date": ed[:10],
                         "p_model": max(0.001, p + trained[g]),
                         "p_mkt": p, "won": won == 1.0,
                         "fee_rate": 0.07, "slip_bps": 100})
        res = engine.run(bets)
        print(f"  ENGINE OOS: {engine.summary(res, f'short-longshots@{horizon}h')}\n")


if __name__ == "__main__":
    main()
