"""Grade the calibration drill: house model_p vs raw market p, Brier scored.

The drill measures the MODEL (market price shrunk toward 0.5 by the measured
0.87 calibration slope), not the user. Resolves each drill question by exact
title match against recently-closed gamma markets, then writes per-question
and aggregate Brier scores to collected/drill_graded.csv.
"""
import pathlib

import pandas as pd

from gamma_resolved import resolve_titles

D = pathlib.Path(__file__).parent / "collected"
DRILL = D / "drill_2026-07-23.csv"
OUT = D / "drill_graded.csv"


def main():
    if not DRILL.exists():
        print("no drill file")
        return
    d = pd.read_csv(DRILL)
    res = resolve_titles(d["q"])
    rows, pending = [], []
    for r in d.itertuples():
        key = str(r.q).strip()
        legs = res.get(key)
        if not legs:
            pending.append(key)
            continue
        yes = next((v for k, v in legs.items() if k.strip().lower() == "yes"), None)
        if yes is None:
            pending.append(key)
            continue
        y = 1.0 if yes else 0.0
        rows.append({
            "drill_date": r.drill_date, "q": key, "resolved": int(y),
            "p_market": r.p, "p_model": r.model_p,
            "brier_market": round((r.p - y) ** 2, 4),
            "brier_model": round((r.model_p - y) ** 2, 4),
        })
    if not rows:
        print(f"drill: 0 of {len(d)} resolved ({len(pending)} pending)")
        return
    g = pd.DataFrame(rows)
    g.to_csv(OUT, index=False)
    bm, bd = g["brier_market"].mean(), g["brier_model"].mean()
    print(f"drill: {len(g)} of {len(d)} resolved ({len(pending)} pending)")
    print(f"  Brier market {bm:.4f} | model {bd:.4f} | "
          f"{'model' if bd < bm else 'market'} ahead by {abs(bm - bd):.4f}")
    for r in g.itertuples():
        print(f"  res={r.resolved}  mkt {r.p_market:.2f} ({r.brier_market:.3f})  "
              f"model {r.p_model:.3f} ({r.brier_model:.3f})  {r.q[:66]}")
    for q in pending:
        print(f"  [pending] {q[:80]}")


if __name__ == "__main__":
    main()
