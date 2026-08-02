# Open-source stack evaluation (2026-08-02)

Hands-on evaluation of the giants — cloned, installed, and run where feasible,
not judged by star count. Verdict per tool plus how the desk stands on it.

## Tested and standing

| Tool | Verdict | Evidence |
|---|---|---|
| **ccxt** | ✅ core substrate | 43k★, MIT, pushed today. Already powers funding_carry. 100+ exchanges, one API. |
| **nautilus_trader** | ✅ production engine | 25k★, LGPL, pushed today. `pip install` clean, `BacktestEngine` imports. Rust-native, backtest==live parity. The serious choice for a unified bot. |
| **vectorbt** | ✅ research/backtest, with a caveat | 8.5k★, pushed today. **Breaks on NumPy 2.x** (`np.unicode_` removed) — must pin `numpy<2` in a venv. Once pinned, ran a real dual-MA backtest (Sharpe 0.27, 5 trades). Fast for sweeps. |
| **freqtrade** | ✅ turnkey, paper from day one | 53k★, GPL-3, pushed today. `dry_run` (paper) is built in and default-safe; ships strategy templates incl. FreqAI (ML). The natural first thing to actually run. |
| **hummingbot** | ✅✅ the standout | 19k★, Apache-2, pushed 2d. `paper_trade` built in, and it **ships `avellaneda_market_making`** — the exact academic maker model our implementation research said we needed — plus `amm_arb`. This is our maker lane, already written and maintained. |

## Reference / study only

| Tool | Verdict |
|---|---|
| **microsoft/qlib** | 47k★, MIT — the heavyweight AI-quant *investment* platform (the clean passive-financial category). Study reference for the cross-asset ML lane, not a bot to run as-is. |
| **FinRL** | 16k★, MIT — RL-for-finance ecosystem. Educational; RL-trading backtests are famously non-reproducible live (our own falsification ethos: treat as study, not strategy). |
| **aoki-h-jp/funding-rate-arbitrage** | 308★, **1,001 days stale = dead**. Do not build on it. BUT its `get_large_divergence_multi_exchange` approach is a useful *reference* for extending our funding_carry from single-venue to cross-exchange divergence. |
| **pybroker** | 3.5k★ — clean ML-backtest framework, lighter alternative to qlib. |

## The standout finding

**hummingbot ships the Avellaneda-Stoikov market maker as a maintained
strategy.** Our whole maker-lane research (the implementation report, the
maker sims, the markout gate) was reconstructing this model from papers.
It already exists, battle-tested, with paper-trade mode. We do not need to
build the maker engine — we need to (1) validate the edge with our own
markout gate, then (2) configure hummingbot's avellaneda strategy on the
markets our research selected. Build the evidence, borrow the engine.

## How the desk stands on the giants

- **Substrate:** ccxt (have it) for all venue data/execution.
- **Maker lane:** hummingbot `avellaneda_market_making`, paper mode, on the
  markets our research picks — gated on the markout result, not run blind.
- **Funding-carry / directional lane:** freqtrade dry-run, our funding_carry
  logic as a strategy; multi-exchange divergence per the dead repo's pattern.
- **Serious unified bot (later):** nautilus_trader — one codebase,
  backtest==live, if/when a compliant account exists.
- **Research/sweeps:** vectorbt (pinned numpy<2); qlib as the ML reference.

The desk's own code stays the **measurement and gate** layer (census,
markout, dyno, risk_guard). The giants supply the **execution engines**.
We never hand a giant capital until our own gate says the edge is real —
the engines are borrowed, the evidence is ours.
