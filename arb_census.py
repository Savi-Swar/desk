"""Full mispricing census. Where arb_executor_sim samples a handful of the
biggest events, this sweeps every open negative-risk event on the venue,
depth-verifies every candidate, and records the total extractable pool at
this moment. Appends one row per opportunity to collected/arb_census.csv
and one summary row per run to collected/arb_pool.csv.
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
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

MIN_EDGE = 0.005      # ignore sums inside half a cent of fair
BOOK_SLEEP = 0.15     # stay polite with the CLOB


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


# every open neg-risk event, paginated
events, offset = [], 0
while True:
    page = get("https://gamma-api.polymarket.com/events?closed=false"
               f"&limit=100&offset={offset}")
    if not page:
        break
    events.extend(page)
    offset += 100
    if offset >= 2000:
        break

candidates = []
for ev in events:
    mkts = ev.get("markets", [])
    if len(mkts) < 3 or not ev.get("negRisk", False):
        continue
    try:
        bids = [float(m.get("bestBid") or 0) for m in mkts]
        asks = [float(m.get("bestAsk") or 0) for m in mkts]
    except (TypeError, ValueError):
        continue
    if not all(0 < a <= 1 for a in asks):
        continue
    sell_edge = sum(bids) - 1.0
    buy_edge = 1.0 - sum(asks)
    if max(sell_edge, buy_edge) >= MIN_EDGE:
        candidates.append((max(sell_edge, buy_edge), ev))

rows = []
for _, ev in sorted(candidates, key=lambda x: -x[0]):
    legs, ok = [], True
    for m in ev["markets"]:
        try:
            toks = json.loads(m.get("clobTokenIds", "[]"))
            book = get(f"https://clob.polymarket.com/book?token_id={toks[0]}")
            b, a = book.get("bids", []), book.get("asks", [])
            legs.append({
                "bid": float(b[-1]["price"]) if b else 0,
                "bid_sz": float(b[-1]["size"]) if b else 0,
                "ask": float(a[-1]["price"]) if a else 1,
                "ask_sz": float(a[-1]["size"]) if a else 0})
            time.sleep(BOOK_SLEEP)
        except Exception:
            ok = False
            break
    if not ok or not legs:
        continue
    tb, ta = sum(l["bid"] for l in legs), sum(l["ask"] for l in legs)
    near_res = int(max(l["bid"] for l in legs) >= 0.95)
    for kind, edge, size in (
            ("SELL-ALL", tb - 1.0, min(l["bid_sz"] for l in legs)),
            ("BUY-ALL", 1.0 - ta, min(l["ask_sz"] for l in legs))):
        if edge >= MIN_EDGE and size > 0:
            rows.append({"ts": now, "event": ev.get("title", "")[:60],
                         "type": kind, "edge_pershare": round(edge, 4),
                         "exec_size": round(size, 1),
                         "pool_dollars": round(edge * size, 2),
                         "n_legs": len(legs), "near_res": near_res})

# persistence check on the biggest opportunities: re-fetch every leg ~10s
# later. A sum-edge produced by non-synchronous quotes (a timing artifact)
# disappears on the second synchronized look; a real coordination failure
# survives it.
rows.sort(key=lambda r: -r["pool_dollars"])
recheck = {}
for r in rows[:5]:
    ev = next(e for _, e in candidates if e.get("title", "")[:60] == r["event"])
    time.sleep(10)
    tb2, ta2, ok = 0.0, 0.0, True
    for m in ev["markets"]:
        try:
            toks = json.loads(m.get("clobTokenIds", "[]"))
            book = get(f"https://clob.polymarket.com/book?token_id={toks[0]}")
            b, a = book.get("bids", []), book.get("asks", [])
            tb2 += float(b[-1]["price"]) if b else 0
            ta2 += float(a[-1]["price"]) if a else 1
            time.sleep(BOOK_SLEEP)
        except Exception:
            ok = False
            break
    if ok:
        edge2 = tb2 - 1.0 if r["type"] == "SELL-ALL" else 1.0 - ta2
        recheck[(r["event"], r["type"])] = round(edge2, 4)
for r in rows:
    r["edge_recheck"] = recheck.get((r["event"], r["type"]))

if rows:
    df = pd.DataFrame(rows)
    f = D / "arb_census.csv"
    df.to_csv(f, mode="a", header=not f.exists(), index=False)
else:
    df = pd.DataFrame(columns=["pool_dollars", "near_res"])

clean = df[df.get("near_res", 0) == 0]["pool_dollars"].sum() if len(df) else 0.0
total = df["pool_dollars"].sum() if len(df) else 0.0
summary = {"ts": now, "events_scanned": len(events),
           "negrisk_candidates": len(candidates), "opportunities": len(df),
           "pool_total": round(total, 2), "pool_ex_convergence": round(clean, 2)}
pf = D / "arb_pool.csv"
pd.DataFrame([summary]).to_csv(pf, mode="a", header=not pf.exists(), index=False)

print(f"census: {len(events)} events, {len(candidates)} neg-risk candidates, "
      f"{len(df)} depth-verified opportunities")
print(f"TOTAL EXTRACTABLE POOL RIGHT NOW: ${total:,.2f} "
      f"(${clean:,.2f} ex-convergence)")
for r in rows[:10]:
    print(f"  ${r['pool_dollars']:8.2f}  {r['type']:8s} {r['edge_pershare']*100:.1f}c x "
          f"{r['exec_size']:,.0f} sh  nr={r['near_res']}  {r['event']}")
