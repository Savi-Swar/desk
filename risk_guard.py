"""Risk guard: the enforced controls a live book needs, as code, not a
checklist. Every sim and any future executor calls check() before sizing a
position; it returns the allowed size (possibly 0) and the reason. Pure
functions, unit-tested, so the same limits bind in paper and live.

Limits (from the implementation research + UMA dispute base rates):
  - per-set cap: no single condition above PER_SET_FRAC of bankroll
  - cluster cap: correlated conditions (same subject stem) capped together
  - daily drawdown halt: stop opening once realized+MTM loss breaches DD_HALT
  - stale-quote guard: refuse to act on a book older than STALE_S
  - kill file: a KILL sentinel in collected/ halts everything
"""
import pathlib
import time

HERE = pathlib.Path(__file__).parent
KILL = HERE / "collected" / "KILL"

PER_SET_FRAC = 0.10        # <=10% of bankroll in one condition (UMA tail)
CLUSTER_FRAC = 0.20        # <=20% across correlated conditions
DD_HALT = 0.15            # halt new positions at -15% on the day
STALE_S = 30             # a book older than this is not tradable


def check(bankroll, want_notional, *, condition_exposure=0.0,
          cluster_exposure=0.0, day_pnl=0.0, book_age_s=0.0):
    """Return (allowed_notional, reason). allowed<=want; 0 means blocked."""
    if KILL.exists():
        return 0.0, "kill-file present"
    if book_age_s > STALE_S:
        return 0.0, f"stale book {book_age_s:.0f}s > {STALE_S}s"
    if day_pnl <= -DD_HALT * bankroll:
        return 0.0, f"daily drawdown halt ({day_pnl/bankroll:.1%})"
    per_set_room = max(0.0, PER_SET_FRAC * bankroll - condition_exposure)
    cluster_room = max(0.0, CLUSTER_FRAC * bankroll - cluster_exposure)
    allowed = min(want_notional, per_set_room, cluster_room)
    if allowed <= 0:
        return 0.0, "position/cluster cap reached"
    if allowed < want_notional:
        return allowed, "trimmed to cap"
    return allowed, "ok"


def _selftest():
    B = 10_000.0
    assert check(B, 500)[0] == 500                       # normal
    assert check(B, 5000)[0] == 1000                     # per-set cap 10%
    assert check(B, 500, condition_exposure=1000)[0] == 0  # cap already full
    assert check(B, 500, cluster_exposure=2000)[0] == 0    # cluster full
    assert check(B, 500, day_pnl=-1600)[0] == 0          # drawdown halt
    assert check(B, 500, book_age_s=60)[0] == 0          # stale
    print("risk_guard selftest: all pass")


if __name__ == "__main__":
    _selftest()
