"""Websocket-driven real-time detector.

We already receive Polymarket's market channel (book_recorder), but detection
polled REST every 60s. This reacts to the stream itself: maintain live book
state per asset and re-check the arb predicate on every price_change, so an
opportunity is seen within milliseconds of the book moving instead of up to
60 seconds later.

This is detection speed, not execution speed. It does NOT try to beat the
sub-100ms taker bots to a fill — that race needs colocation and we decline
it. It makes us first to SEE, which is what the patient games need: rest a
maker quote the instant a reward market qualifies, catch a relations lock as
it appears, spot the newborn-market birth window. You cannot react faster
than the event arriving on the stream without colocating, so for a $0
operator this is the latency floor.

Runs inside a CI window like the recorder. Logs every detection with its
reaction latency to collected/ws_detections.csv.
"""
import datetime
import json
import os
import pathlib
import time
import urllib.request

import pandas as pd
import websocket

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
OUT = D / "ws_detections.csv"
WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

RUN_MIN = float(os.environ.get("WS_MIN", 24))
MAX_TOKENS = 40
STALE_S = 60
MIN_NET = 0.002


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def leg_fee(rate, price, exp=1.0):
    return rate * (price * (1.0 - price)) ** exp


def build_watch():
    """Price-action binaries (both tokens) + neg-risk legs, with the fee rate
    and the paired token so single-condition checks can run on the stream."""
    evs = get("https://gamma-api.polymarket.com/events?closed=false"
              "&limit=300&order=volume24hr&ascending=false")
    toks, meta = [], {}      # token -> {rate, pair, kind, q}
    PA = ("bitcoin", "ethereum", "crypto", "solana", "xrp", "dogecoin")
    for ev in evs:
        for m in ev.get("markets", []):
            tags = " ".join((x.get("label") or "") for x in (ev.get("tags") or [])).lower()
            title = (ev.get("title") or "").lower()
            is_pa = any(h in tags or h in title for h in PA)
            if not is_pa:
                continue
            try:
                tk = json.loads(m.get("clobTokenIds", "[]"))
            except Exception:
                continue
            if len(tk) < 2:
                continue
            fs = m.get("feeSchedule") or {}
            rate = float(fs.get("rate") or 0) if m.get("feesEnabled") else 0.0
            q = (m.get("question") or "")[:50]
            for i, t in enumerate(tk[:2]):
                if len(toks) >= MAX_TOKENS:
                    break
                toks.append(t)
                meta[t] = {"rate": rate, "pair": tk[1 - i], "q": q}
    return toks, meta


def main():
    toks, meta = build_watch()
    if not toks:
        print("ws_detect: empty watchlist")
        return
    best = {}                # asset -> (best_bid, best_ask)
    detections = []
    deadline = time.monotonic() + RUN_MIN * 60
    reconnects = 0

    while time.monotonic() < deadline:
        try:
            ws = websocket.create_connection(WS_URL, timeout=15)
            ws.send(json.dumps({"type": "market", "assets_ids": toks}))
            last = time.monotonic()
            while time.monotonic() < deadline:
                if time.monotonic() - last > STALE_S:
                    break
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                if not raw:
                    continue
                last = time.monotonic()
                recv_t = time.time()
                msg = json.loads(raw)
                for e in (msg if isinstance(msg, list) else [msg]):
                    et = e.get("event_type")
                    if et == "book":
                        a = e.get("asset_id")
                        bids = e.get("bids", []); asks = e.get("asks", [])
                        bb = float(bids[-1]["price"]) if bids else 0.0
                        ba = float(asks[-1]["price"]) if asks else 1.0
                        best[a] = (bb, ba)
                    elif et == "price_change":
                        for pc in e.get("price_changes", []):
                            a = pc.get("asset_id")
                            bb = float(pc.get("best_bid") or 0)
                            ba = float(pc.get("best_ask") or 1)
                            best[a] = (bb, ba)
                            # single-condition check the instant this leg moved
                            mt = meta.get(a)
                            if not mt or mt["pair"] not in best:
                                continue
                            pb, pa = best[a]
                            qb, qa = best[mt["pair"]]
                            rate = mt["rate"]
                            # BUY-BOTH: this ask + pair ask < 1 - fees
                            buy = 1.0 - (pa + qa) - leg_fee(rate, pa) - leg_fee(rate, qa)
                            sell = (pb + qb) - 1.0 - leg_fee(rate, pb) - leg_fee(rate, qb)
                            net = max(buy, sell)
                            if net >= MIN_NET:
                                detections.append({
                                    "ts": datetime.datetime.fromtimestamp(
                                        recv_t, datetime.timezone.utc).isoformat(timespec="milliseconds"),
                                    "q": mt["q"], "type": "BUY-BOTH" if buy > sell else "SELL-BOTH",
                                    "net_edge": round(net, 4),
                                    "react_ms": round((time.time() - recv_t) * 1000, 1)})
            ws.close()
        except Exception:
            reconnects += 1
            if reconnects > 20:
                break
            time.sleep(min(2 * reconnects, 30))

    if detections:
        pd.DataFrame(detections).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
    react = [d["react_ms"] for d in detections]
    med = sorted(react)[len(react) // 2] if react else None
    print(f"ws_detect: {len(detections)} stream detections, "
          f"{reconnects} reconnects, median react {med}ms")
    for d in detections[:6]:
        print(f"  {d['type']} net {d['net_edge']*100:.2f}c in {d['react_ms']}ms  {d['q']}")


if __name__ == "__main__":
    main()
