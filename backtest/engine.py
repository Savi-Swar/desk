"""Bet-level backtest engine for prediction markets.

A strategy hands the engine BETS; the engine owns everything a strategy would
love to fudge: sizing, fees, slippage, bankroll accounting, and the statistics
(via stats.py). Nothing here knows how a signal was made — that separation is
what keeps the Sharpe honest.

A bet is a dict:
    date       ISO day the position RESOLVES (P&L lands that day)
    p_model    our probability for YES
    p_mkt      market price for YES at entry
    won        True/False resolution
    fee_rate   venue taker fee rate (fee = rate * p * (1-p) per share), default 0.02
    slip_bps   extra cost of crossing, bps of price, default 50

Sizing: fractional Kelly on the model edge, capped per bet — small and boring
on purpose. Returns are daily on a fixed bankroll (no compounding, so one hot
week can't disguise a thin edge).
"""
import math
from collections import defaultdict

import stats

BANKROLL = 10_000.0
KELLY_FRAC = 0.25
MAX_BET_FRAC = 0.02        # never more than 2% of bankroll on one market
DAY_EXPOSURE_CAP = 0.25    # never more than 25% of bankroll at risk per day:
                           # same-day prediction-market bets are heavily
                           # correlated (one BTC path resolves them all), so
                           # uncapped daily deployment turns a 5pp edge into
                           # ruin — the OOS crypto test proved it at -852%


def side_and_edge(p_model, p_mkt):
    """bet YES if model > market, else NO; returns (is_yes, entry price, model prob of winning)."""
    if p_model >= p_mkt:
        return True, p_mkt, p_model
    return False, 1.0 - p_mkt, 1.0 - p_model


def kelly_fraction(p_win, price):
    """Kelly for a binary contract bought at `price` paying 1: f* on bankroll."""
    if not 0 < price < 1:
        return 0.0
    b = (1.0 - price) / price               # net odds
    f = (p_win * (b + 1) - 1) / b if b > 0 else 0.0
    return max(0.0, f)


def run(bets, flat=None):
    """-> dict with daily returns, per-bet records, and the honest stats.

    flat: if set (e.g. 0.0025), EVERY bet risks that fixed bankroll fraction
    and the daily exposure cap is bypassed. Kelly + the day cap is a real
    capital-allocation policy, but it reweights P&L toward sparse days —
    a losing bet stream can print a positive capped Sharpe (mirage #8; the
    weather-2026 stream was -3.3c/share equal-weight yet +150% capped).
    A result is only claimable when BOTH modes agree on sign."""
    # pass 1: raw fractions per day, to scale into the daily exposure cap
    day_f = defaultdict(float)
    sized = []
    for bet in bets:
        yes, price, p_win = side_and_edge(bet["p_model"], bet["p_mkt"])
        f = flat if flat is not None else \
            min(KELLY_FRAC * kelly_fraction(p_win, price), MAX_BET_FRAC)
        if f > 0:
            sized.append((bet, yes, price, f))
            day_f[bet["date"]] += f
    scale = ({d: 1.0 for d in day_f} if flat is not None else
             {d: min(1.0, DAY_EXPOSURE_CAP / tot) for d, tot in day_f.items()})

    daily = defaultdict(float)
    records = []
    for bet, yes, price, f in sized:
        f *= scale[bet["date"]]
        dollars = f * BANKROLL
        shares = dollars / price
        fee = bet.get("fee_rate", 0.02) * price * (1 - price) * shares
        slip = bet.get("slip_bps", 50) / 1e4 * price * shares
        won_side = bet["won"] if yes else (not bet["won"])
        pnl = (shares * (1.0 - price) if won_side else -dollars) - fee - slip
        daily[bet["date"]] += pnl / BANKROLL
        records.append({"date": bet["date"], "yes": yes, "price": price,
                        "f": f, "pnl": pnl})
    days = sorted(daily)
    rets = [daily[d] for d in days]
    out = {
        "n_bets": len(records),
        "n_days": len(days),
        "total_return": sum(rets),
        "sharpe": stats.sharpe(rets),
        "psr": stats.psr(rets),
        "daily": dict(zip(days, rets)),
        "records": records,
    }
    ok, reasons = stats.evidence_bar(len(records), rets)
    out["quotable"] = ok
    out["bar_failures"] = reasons
    return out


def summary(res, name="strategy"):
    line = (f"{name}: {res['n_bets']} bets / {res['n_days']} days  "
            f"ret {res['total_return']*100:+.1f}%  SR {res['sharpe']:+.2f}  "
            f"PSR {res['psr']:.2f}  "
            f"{'QUOTABLE' if res['quotable'] else 'NOT QUOTABLE: ' + '; '.join(res['bar_failures'])}")
    return line
