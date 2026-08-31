"""Engine exit-criteria tests (plan §2): the engine must refuse to
manufacture edge from noise, and must faithfully pass through a planted one
net of the costs it charges.

    python backtest/test_engine.py
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import engine


class LCG:
    def __init__(self, seed=42):
        self.x = seed
    def u(self):
        self.x = (self.x * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return self.x / (1 << 64)


def synth(rng, n_days=400, per_day=8, model_skill=0.0):
    """markets with true prob q; market prices q + noise; model knows
    q + skill*(q_true - p_mkt) worth of the gap."""
    bets = []
    for d in range(n_days):
        date = f"2025-{1 + d // 30:02d}-{1 + d % 28:02d}-{d}"
        for _ in range(per_day):
            q = 0.15 + 0.7 * rng.u()                     # true prob
            p_mkt = min(0.97, max(0.03, q + 0.08 * (rng.u() - 0.5)))
            p_model = p_mkt + model_skill * (q - p_mkt)   # skill in [0,1]
            won = rng.u() < q
            bets.append({"date": date, "p_model": p_model, "p_mkt": p_mkt,
                         "won": won})
    return bets


def test_null():
    """EFFICIENT market (price = true prob exactly) + noise model: every trade
    is EV-zero gross, so the engine must show a LOSS of about the costs and
    never quote it. (An earlier version used additive price noise around truth
    — that leaks value into the price level itself, which Kelly's 1/price
    sizing then harvests; the test was broken, not the engine.)"""
    rng = LCG(9)
    bets = []
    for d in range(400):
        date = f"d{d}"
        for _ in range(8):
            q = 0.15 + 0.7 * rng.u()
            noise_model = min(0.99, max(0.01, q + 0.06 * (rng.u() - 0.5)))
            bets.append({"date": date, "p_model": noise_model, "p_mkt": q,
                         "won": rng.u() < q})
    res = engine.run(bets)
    print(" ", engine.summary(res, "null(efficient mkt)"))
    assert res["total_return"] < 0, "must lose its costs on an efficient market"
    assert not res["quotable"], "null must never pass the bar"


def test_skill():
    """a model that closes 60% of the gap to truth must be strongly positive
    and quotable; halving skill must not increase the Sharpe."""
    res6 = engine.run(synth(LCG(4), model_skill=0.6))
    res3 = engine.run(synth(LCG(4), model_skill=0.3))
    print(" ", engine.summary(res6, "skill 0.6"))
    print(" ", engine.summary(res3, "skill 0.3"))
    assert res6["sharpe"] > 1.5, f"real skill only SR {res6['sharpe']:.2f}"
    assert res6["quotable"], f"real skill failed bar: {res6['bar_failures']}"
    assert res6["sharpe"] > res3["sharpe"], "more skill must not lower SR"


def test_costs_bite():
    """the same skilled strategy with heavier costs must earn less."""
    cheap = synth(LCG(7), model_skill=0.5)
    dear = [dict(b, slip_bps=400, fee_rate=0.07) for b in cheap]
    r1, r2 = engine.run(cheap), engine.run(dear)
    print(f"  costs: SR {r1['sharpe']:+.2f} -> {r2['sharpe']:+.2f} with 8x costs")
    assert r2["sharpe"] < r1["sharpe"], "costs must reduce Sharpe"


if __name__ == "__main__":
    test_null()
    test_skill()
    test_costs_bite()
    print("all engine tests pass")
