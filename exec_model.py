"""Execution and settlement model.

Turns a detected edge into a modelled round-trip P&L using the venue's real
primitives, so a paper "profit" reflects what execution would actually
capture. Verified mechanics (docs.polymarket.com, CTF/NegRiskAdapter, and
the on-chain tape dissection of the top arb wallets):

  mint (split)   1.00 USDC -> 1 YES + 1 NO of a condition. No fee.
  merge          1 YES + 1 NO -> 1.00 USDC. No fee. This is how both-sides
                 captures settle instantly instead of waiting for resolution.
  redeem         after resolution, the winning token -> 1.00 USDC. No fee.
  taker fill     fee = C * feeRate * p*(1-p), taker side only.
  maker fill     fee 0; earns a rebate (15-25% of the notional fee pool).

Two round-trips are modelled:

  single_condition_buy_both:
      buy YES @ ask_y (taker), buy NO @ ask_n (taker), merge -> $1.
      pnl = 1 - ask_y - ask_n - fee(ask_y) - fee(ask_n)   per set.

  maker_set_build (the patient game):
      rest to buy YES and NO as maker (fee 0, + rebate); merge fills to $1;
      unfilled legs are the cost of legging. pnl uses calibrated fill
      probabilities and markout from fill_model.csv when present.

Also carries the compliant live-path checklist (COMPLIANCE) so the go-live
gate is explicit and auditable. Nothing here places an order; it prices what
an order would do.
"""
import json
import pathlib

import pandas as pd

D = pathlib.Path(__file__).parent / "collected"

REBATE_FRAC = 0.15        # conservative end of the 15-25% maker rebate range


def taker_fee(price, rate, exponent=1.0, collateral=1.0):
    return collateral * rate * (price * (1.0 - price)) ** exponent


def single_condition_buy_both(ask_yes, ask_no, rate, size=1.0):
    """Taker buy of both legs, merged to $1. Returns per-set and total pnl."""
    cost = ask_yes + ask_no
    fee = taker_fee(ask_yes, rate) + taker_fee(ask_no, rate)
    per_set = 1.0 - cost - fee
    return {"per_set": round(per_set, 5), "total": round(per_set * size, 4),
            "cost": round(cost, 5), "fee": round(fee, 5), "settle": "merge"}


def maker_set_build(bid_yes, bid_no, rate, size=1.0,
                    fill_prob=None, markout=0.0):
    """Rest both legs as maker (fee 0 + rebate), merge fills to $1. Legging
    risk: only the joint-fill fraction settles cleanly; the rest carries
    one-sided inventory marked at `markout`. fill_prob defaults to the
    calibrated table if available."""
    if fill_prob is None:
        fill_prob = _calibrated_fill_prob()
    cost = bid_yes + bid_no
    gross_per_set = 1.0 - cost                    # buy both below $1, merge to $1
    rebate = REBATE_FRAC * (taker_fee(bid_yes, rate) + taker_fee(bid_no, rate))
    joint = fill_prob ** 2                        # both legs must fill to merge
    one_side = 2 * fill_prob * (1 - fill_prob)    # one leg fills -> inventory
    expected = joint * (gross_per_set + rebate) + one_side * markout
    return {"per_set_expected": round(expected, 5),
            "total_expected": round(expected * size, 4),
            "joint_fill_prob": round(joint, 3),
            "gross_if_both": round(gross_per_set, 5),
            "rebate": round(rebate, 5), "markout_used": markout}


def _calibrated_fill_prob():
    f = D / "fill_model.csv"
    if not f.exists():
        return 0.27          # first-capture prior until the table fills out
    try:
        df = pd.read_csv(f)
        return float(df["filled"].mean())
    except Exception:
        return 0.27


COMPLIANCE = {
    "venue_account": "opened by an eligible adult in a permitted jurisdiction, "
                     "full KYC, their own custody",
    "operation": "if a third party operates, use the venue's Rule 3.7(a) "
                 "power-of-attorney, not credential sharing",
    "capital": "sized to survive a weeks-long resolution lockup (2020 precedent)",
    "kill_test": "heartbeat + stale-quote kill switch verified before any live order",
    "per_set_cap": "<= 10% of bankroll in any single condition (UMA dispute tail)",
    "gate": "live only after the Sept markout gate passes AND explicit user go",
}


def _demo():
    # illustrate on a representative price-action leg pair
    print("single-condition taker (7% rate, both legs @ 0.02/0.977):")
    print(" ", single_condition_buy_both(0.024, 0.977, 0.07, size=1000))
    print("maker set build (4% rate, bids 0.44/0.55, calibrated fill):")
    print(" ", maker_set_build(0.44, 0.55, 0.04, size=1000, markout=0.015))
    print(f"calibrated joint-fill prior: {_calibrated_fill_prob():.3f}")


if __name__ == "__main__":
    _demo()
