"""Maker-side set-builder simulator.

The fees research left one unmeasured number: adverse-selection markout on
resting orders. This sim measures it. Strategy simulated, per the hybrid
spec: pick the richest fee-enabled neg-risk ladder by ask-sum, rest asks
(join, not improve — conservative queue assumption) on the fat legs
(0.15 <= p <= 0.85), sell the tails immediately as taker where the p(1-p)
fee is negligible. A resting ask counts as filled only when the best bid
crosses it on a later observation (trade-through), which understates fills.

Ledger: collected/maker_arb_fills.csv, one row per fill with markout_30m
(mid move after the fill; negative markout = adverse selection). Set
accounting in collected/maker_arb_sets.csv. State in
collected/maker_arb_state.json. Sizing 100 shares/leg. Legs still open
after MAX_HOURS are closed at market as taker, fees paid — legging risk
realized, not ignored.
"""
import datetime
import json
import pathlib
import time
import urllib.request

import pandas as pd

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
STATE = D / "maker_arb_state.json"
FILLS = D / "maker_arb_fills.csv"
SETS = D / "maker_arb_sets.csv"

QTY = 100.0
FAT_LO, FAT_HI = 0.15, 0.85
MIN_ASK_EDGE = 0.005        # sum(asks) - 1 to open a set build
MAX_HOURS = 6.0             # give up and close remaining legs at market
MARKOUT_MIN = 30.0


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def leg_fee(m, price):
    if not m.get("feesEnabled"):
        return 0.0
    fs = m.get("feeSchedule") or {}
    return float(fs.get("rate") or 0) * (price * (1 - price)) ** float(fs.get("exponent") or 1)


def books_for(ev):
    legs = []
    for m in ev["markets"]:
        toks = json.loads(m.get("clobTokenIds", "[]"))
        book = get(f"https://clob.polymarket.com/book?token_id={toks[0]}")
        b, a = book.get("bids", []), book.get("asks", [])
        legs.append({
            "q": (m.get("question") or "")[:60], "m": m,
            "bid": float(b[-1]["price"]) if b else 0.0,
            "ask": float(a[-1]["price"]) if a else 1.0})
        time.sleep(0.12)
    return legs


def pick_target(evs):
    """Richest fee-enabled ladder by top-of-book ask-sum edge."""
    best = None
    for ev in evs:
        mkts = ev.get("markets", [])
        if len(mkts) < 3 or not ev.get("negRisk") or ev.get("negRiskAugmented"):
            continue
        if not any(m.get("feesEnabled") for m in mkts):
            continue           # fee-free ladders belong to the taker watcher
        try:
            asks = [float(m.get("bestAsk") or 0) for m in mkts]
        except (TypeError, ValueError):
            continue
        if not all(0 < a <= 1 for a in asks):
            continue
        edge = sum(asks) - 1.0
        if edge >= MIN_ASK_EDGE and (best is None or edge > best[0]):
            best = (edge, ev)
    return best


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat(timespec="seconds")
    st = json.loads(STATE.read_text()) if STATE.exists() else {}

    evs = get("https://gamma-api.polymarket.com/events?closed=false"
              "&limit=300&order=volume24hr&ascending=false")
    by_title = {(e.get("title") or "")[:60]: e for e in evs}

    fills_out, sets_out = [], []

    # 1) advance any active build
    if st.get("active"):
        act = st["active"]
        ev = by_title.get(act["event"])
        age_h = (now - datetime.datetime.fromisoformat(act["started"])).total_seconds() / 3600
        if ev is None:
            act["abort"] = "event gone"
        else:
            legs_now = books_for(ev)
            legmap = {l["q"]: l for l in legs_now}
            for leg in act["legs"]:
                lnow = legmap.get(leg["q"])
                if lnow is None:
                    continue
                # markout updates for past fills
                if leg.get("filled") and leg.get("markout_30m") is None:
                    mins = (now - datetime.datetime.fromisoformat(leg["fill_ts"])).total_seconds() / 60
                    if mins >= MARKOUT_MIN:
                        mid = (lnow["bid"] + lnow["ask"]) / 2
                        # we SOLD at rest price; adverse = mid rose after fill
                        leg["markout_30m"] = round(leg["rest"] - mid, 4)
                        fills_out.append({
                            "ts": leg["fill_ts"], "event": act["event"],
                            "leg": leg["q"], "side": "maker_ask",
                            "price": leg["rest"], "mid_at_fill": leg["mid_at_fill"],
                            "markout_30m": leg["markout_30m"]})
                # fill detection: bid crossed our resting ask
                if not leg.get("filled") and leg["role"] == "maker":
                    if lnow["bid"] >= leg["rest"]:
                        leg["filled"] = True
                        leg["fill_ts"] = now_iso
                        leg["mid_at_fill"] = round((lnow["bid"] + lnow["ask"]) / 2, 4)
            unfilled = [l for l in act["legs"] if l["role"] == "maker" and not l.get("filled")]
            pending_markout = [l for l in act["legs"]
                               if l.get("filled") and l.get("markout_30m") is None]
            if (not unfilled and not pending_markout) or age_h > MAX_HOURS or act.get("abort"):
                # settle: filled maker legs at rest price (no fee), unfilled
                # legs closed at current bid as taker (fee paid)
                proceeds, fees = 0.0, 0.0
                for leg in act["legs"]:
                    lnow = legmap.get(leg["q"], {"bid": leg.get("rest", 0), "ask": 1})
                    if leg["role"] == "tail" or (leg["role"] == "maker" and not leg.get("filled")):
                        px = lnow["bid"]
                        fee = leg_fee(next((m["m"] for m in legs_now if m["q"] == leg["q"]),
                                           {}), px) if legs_now else 0.0
                        proceeds += px * QTY
                        fees += fee * QTY
                        leg["closed_taker"] = px
                    else:
                        proceeds += leg["rest"] * QTY
                pnl = proceeds - 1.0 * QTY - fees
                sets_out.append({
                    "ts": now_iso, "event": act["event"],
                    "opened": act["started"], "hours": round(age_h, 1),
                    "maker_fills": sum(1 for l in act["legs"]
                                       if l["role"] == "maker" and l.get("filled")),
                    "maker_unfilled": len(unfilled),
                    "taker_fees": round(fees, 2), "pnl": round(pnl, 2),
                    "outcome": act.get("abort") or ("complete" if not unfilled else "timeout")})
                st["active"] = None
            else:
                st["active"] = act

    # 2) open a new build if idle
    if not st.get("active"):
        tgt = pick_target(evs)
        if tgt:
            edge, ev = tgt
            legs = books_for(ev)
            build = {"event": (ev.get("title") or "")[:60], "started": now_iso,
                     "ask_edge_at_open": round(edge, 4), "legs": []}
            for l in legs:
                p = l["ask"]
                role = "maker" if FAT_LO <= p <= FAT_HI else "tail"
                build["legs"].append({"q": l["q"], "role": role,
                                      "rest": p if role == "maker" else l["bid"]})
            st["active"] = build

    STATE.write_text(json.dumps(st, indent=1))
    if fills_out:
        pd.DataFrame(fills_out).to_csv(FILLS, mode="a", header=not FILLS.exists(), index=False)
    if sets_out:
        pd.DataFrame(sets_out).to_csv(SETS, mode="a", header=not SETS.exists(), index=False)

    act = st.get("active")
    print(f"maker_arb: active={'none' if not act else act['event']} "
          f"| fills logged {len(fills_out)} | sets settled {len(sets_out)}")
    if SETS.exists():
        S = pd.read_csv(SETS)
        print(f"  lifetime: {len(S)} sets, pnl ${S['pnl'].sum():+.2f}, "
              f"{(S['outcome'] == 'complete').mean():.0%} complete")
    if FILLS.exists():
        F = pd.read_csv(FILLS)
        if len(F):
            print(f"  markout_30m mean {F['markout_30m'].mean():+.4f} "
                  f"({(F['markout_30m'] < 0).mean():.0%} adverse), n={len(F)}")


if __name__ == "__main__":
    main()
