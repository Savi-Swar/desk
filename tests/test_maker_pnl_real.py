"""Unit tests for maker_pnl_real: reprice() touch-strip math and summarize()
Kish effective-N / t-stat gating on hand-built fills. Pure stdlib, no I/O."""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import maker_pnl_real as mp


def _close(a, b, tol=1e-9):
    assert abs(a - b) < tol, f"{a} != {b}"


def test_reprice():
    off = mp.QUOTE_OFFSET                     # 0.001
    # eff_half absent -> raw markout unchanged
    _close(mp.reprice(0.02, None), 0.02)
    # wide book (eff > offset): strip the un-earnable spread beyond our offset
    _close(mp.reprice(0.02, 0.01), 0.02 - (0.01 - off))     # 0.011
    # tight book (0 < eff < offset): capture all of eff, markout unchanged
    _close(mp.reprice(0.01, 0.0005), 0.01)
    # eff exactly at the offset: unchanged
    _close(mp.reprice(0.01, off), 0.01)
    # negative eff (wrong-side/stale mid): captured clamps to 0,
    # repriced = m - eff (the negative "spread" is handed back)
    _close(mp.reprice(0.01, -0.002), 0.012)
    # zero eff: nothing stripped
    _close(mp.reprice(-0.005, 0.0), -0.005)
    print("  maker_pnl_real.reprice: eff>off / eff<off / eff<0 / eff None OK")


def test_summarize_uniform():
    # 4 identical small fills, eff None so markout passes through.
    # per fill: mo = 0.01*50 = 0.50, rebate = 0.2*1.0*1 = 0.20 -> net 0.70
    fills = [(0.01, 50.0, 1.0, None)] * 4
    s = mp.summarize(fills)
    assert s["n"] == 4
    _close(s["eff_n"], 4.0)                   # identical weights -> Kish N = n
    _close(s["mo_live"], 2.0)
    _close(s["rebate_live"], 0.8)
    _close(s["net_live"], 2.8)
    _close(s["net_ideal"], 2.8)               # no size over the cap: ideal==live
    _close(s["per_share"], 0.01)
    _close(s["adverse_pct"], 0.0)
    _close(s["t_live"], 0.0)                  # zero variance -> t defined as 0
    _close(s["top3_share"], 0.75)             # 3 of 4 equal fills
    assert s["significant"] is False
    print("  maker_pnl_real.summarize: uniform fills (Kish N=n, t=0) OK")


def test_summarize_whale_cap():
    # one 500-share whale: live fill capped at OUR_RESTING_SIZE=100 shares,
    # rebate scaled by the same cap fraction (0.2)
    s = mp.summarize([(0.01, 500.0, 2.0, None)])
    _close(s["mo_live"], 1.0)                 # 0.01 * 100, not 0.01 * 500
    _close(s["mo_ideal"], 5.0)                # uncapped paper number
    _close(s["rebate_live"], 0.2 * 2.0 * 0.2)  # frac * fee * cap = 0.08
    _close(s["net_ideal"], 5.0 + 0.4)
    print("  maker_pnl_real.summarize: whale capped to resting size OK")


def test_summarize_t_and_gate():
    # nets [1.0, 3.0]: mean 2, pstdev 1, se 1/sqrt(2) -> t = 2*sqrt(2) = 2.83
    fills = [(0.01, 100.0, 0.0, None), (0.03, 100.0, 0.0, None)]
    s = mp.summarize(fills)
    _close(s["t_live"], round(2 * math.sqrt(2), 2))
    # Kish: (1+3)^2 / (1+9) = 1.6 effective fills
    _close(s["eff_n"], 1.6)
    # |t| >= 2 but eff_n < MIN_EFF: the gate must refuse significance
    assert s["significant"] is False, "t alone must not make a day significant"
    _close(s["adverse_pct"], 0.0)
    _close(s["net_live"], 4.0)

    # negative-markout fill counts toward adverse_pct
    s2 = mp.summarize([(0.01, 100.0, 0.0, None), (-0.02, 100.0, 0.0, None)])
    _close(s2["adverse_pct"], 0.5)
    print("  maker_pnl_real.summarize: t=+2.83, Kish 1.6, MIN_EFF gate holds")


def test_num_and_day():
    assert mp.num("1.5") == 1.5
    assert mp.num("") is None and mp.num(None) is None
    assert mp.day_of("0") == "1970-01-01"
    print("  maker_pnl_real.num/day_of: tolerant parsing OK")


if __name__ == "__main__":
    test_reprice()
    test_summarize_uniform()
    test_summarize_whale_cap()
    test_summarize_t_and_gate()
    test_num_and_day()
    print("test_maker_pnl_real: PASS")
