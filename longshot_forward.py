"""Forward validation of the longshot edge — the decisive experiment.

STUDY1_OOS.md's headline (T-24h short-longshots, SR 3.9 at base costs) rests
on last-trade marks: optimistic entry proxies. This ledger removes that crutch
going forward. Each run finds markets ENTERING THE TRADE WINDOW — ending
within 12-36h, outcome-0 last price in [0.02, 0.40) — and records the LIVE
CLOB book for both tokens: best bid/ask and depth. The paper trade is buying
NO at its real ask. After resolution, grade_longshots() joins outcomes and
computes the realized edge at executable prices.

Runs in the collectors workflow (2x daily). Ledger: collected/longshot_fwd.csv
(entry rows; graded in place later — the `won` and `graded` columns fill in).

    python longshot_forward.py           # record current window + grade due rows
"""
import csv
import datetime as dt
import json
import pathlib
import time
import urllib.request

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
OUT = D / "longshot_fwd.csv"
P_LO, P_HI = 0.02, 0.40
H_LO, H_HI = 12, 36            # hours to endDate

FIELDS = ["t", "market_id", "conditionId", "slug", "endDate", "p_last",
          "yes_bid", "yes_ask", "no_bid", "no_ask", "no_ask_size",
          "volume", "graded", "won_no"]


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(2 * (i + 1))


def book_top(token):
    d = get(f"https://clob.polymarket.com/book?token_id={token}")
    if not d:
        return None, None, None
    bids, asks = d.get("bids") or [], d.get("asks") or []
    bb = float(bids[-1]["price"]) if bids else None
    ba = float(asks[-1]["price"]) if asks else None
    ba_sz = float(asks[-1]["size"]) if asks else None
    return bb, ba, ba_sz


def record():
    now = dt.datetime.now(dt.timezone.utc)
    lo = (now + dt.timedelta(hours=H_LO)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hi = (now + dt.timedelta(hours=H_HI)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for off in (0, 500, 1000):
        mkts = get("https://gamma-api.polymarket.com/markets?closed=false"
                   f"&end_date_min={lo}&end_date_max={hi}"
                   f"&limit=500&offset={off}") or []
        if not mkts:
            break
        for m in mkts:
            try:
                p_last = float(json.loads(m.get("outcomePrices") or "[]")[0])
                toks = json.loads(m.get("clobTokenIds") or "[]")
            except (ValueError, IndexError, TypeError):
                continue
            if not P_LO <= p_last < P_HI or len(toks) < 2:
                continue
            yb, ya, _ = book_top(toks[0])
            nb, na, nsz = book_top(toks[1])
            rows.append({"t": round(time.time(), 1), "market_id": m.get("id"),
                         "conditionId": m.get("conditionId"),
                         "slug": (m.get("slug") or "")[:70],
                         "endDate": m.get("endDate"), "p_last": p_last,
                         "yes_bid": yb, "yes_ask": ya, "no_bid": nb,
                         "no_ask": na, "no_ask_size": nsz,
                         "volume": m.get("volumeNum") or m.get("volume"),
                         "graded": 0, "won_no": ""})
            time.sleep(0.2)
    return rows


def grade():
    """fill in outcomes for past entries whose markets have resolved."""
    if not OUT.exists():
        return 0, []
    with OUT.open() as f:
        rows = list(csv.DictReader(f))
    due = [r for r in rows if r["graded"] == "0"
           and r["endDate"] < dt.datetime.now(dt.timezone.utc).isoformat()]
    graded = 0
    for r in due[:150]:                      # rate-bound per run
        m = get(f"https://gamma-api.polymarket.com/markets/{r['market_id']}")
        if not m:
            continue
        try:
            finals = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
        except (ValueError, TypeError):
            continue
        winners = [i for i, p in enumerate(finals) if p > 0.99]
        if len(winners) != 1:
            continue
        r["won_no"] = 1 if winners[0] != 0 else 0
        r["graded"] = 1
        graded += 1
        time.sleep(0.2)
    return graded, rows


def summarize(rows):
    g = [r for r in rows if r["graded"] == "1" or r["graded"] == 1]
    fills = [r for r in g if r.get("no_ask") not in (None, "", "None")]
    if len(fills) < 20:
        return f"graded {len(g)} (need ~20+ with live asks for a read)"
    pnl = []
    for r in fills:
        ask = float(r["no_ask"])
        if not 0.5 <= ask <= 0.99:
            continue
        won = str(r["won_no"]) == "1"
        pnl.append((1 - ask) if won else -ask)
    if not pnl:
        return "no priceable fills yet"
    m = sum(pnl) / len(pnl)
    return (f"LIVE-BOOK edge so far: {len(pnl)} trades, mean {m*100:+.2f}c/share"
            f" at the real NO ask (pre-fee)")


def main():
    graded, rows = grade()
    new = record()
    all_rows = rows + new if rows else new
    if all_rows:
        with OUT.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_rows)
    print(f"longshot_fwd: +{len(new)} entries, graded {graded}; "
          f"{summarize(all_rows)}")


if __name__ == "__main__":
    main()
