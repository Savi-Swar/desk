"""Websocket book recorder.

Order-book states are the one dataset that cannot be reconstructed later:
REST gives current books only, and the fill/markout questions need the
book path around events. This records Polymarket's market channel for a
watchlist of ladder legs and writes gzip'd jsonl per run.

Watchlist per run: legs of the maker sim's active target, every Fed
Decision ladder, and the richest neg-risk ladders by top-of-book edge,
capped at MAX_TOKENS. Output: collected/books/YYYY-MM-DD/<runstamp>.jsonl.gz
(one line per message: {"t": epoch, "m": raw message}). Size guardrails:
MAX_MSGS and MAX_MB per run, whichever hits first.
"""
import datetime
import gzip
import json
import os
import pathlib
import time
import urllib.request

import websocket

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

RECORD_MIN = float(os.environ.get("RECORD_MIN", 24))   # minutes; override per workflow
MAX_TOKENS = 120
MAX_MSGS = 200_000
MAX_MB = 45
STALE_S = 60


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def build_watchlist():
    toks, why = [], []
    evs = get("https://gamma-api.polymarket.com/events?closed=false"
              "&limit=300&order=volume24hr&ascending=false")

    state_f = D / "maker_arb_state.json"
    active_title = None
    if state_f.exists():
        try:
            act = json.loads(state_f.read_text()).get("active")
            active_title = act and act.get("event")
        except Exception:
            pass

    PA_HINTS = ("bitcoin", "ethereum", "crypto", "solana", "xrp",
                "dogecoin", "price action")
    ranked = []
    for ev in evs:
        mkts = ev.get("markets", [])
        if not mkts:
            continue
        title = (ev.get("title") or "")[:60]
        tags = " ".join((x.get("label") or "") for x in (ev.get("tags") or [])).lower()
        is_pa = any(h in tags or h in title.lower() for h in PA_HINTS)
        # price-action markets carry 97% of measured post-fee arb and their
        # dislocations are sub-minute; ladders only qualify if neg-risk
        if not is_pa and (len(mkts) < 3 or not ev.get("negRisk")
                          or ev.get("negRiskAugmented")):
            continue
        try:
            asks = [float(m.get("bestAsk") or 0) for m in mkts]
            bids = [float(m.get("bestBid") or 0) for m in mkts]
        except (TypeError, ValueError):
            continue
        if not all(0 < a <= 1 for a in asks):
            continue
        edge = max(sum(bids) - 1.0, sum(asks) - 1.0)
        vol = float(ev.get("volume24hr") or 0)
        pri = 3 if is_pa and vol > 50_000 else (
            2 if title == active_title else (1 if is_pa else 0))
        ranked.append((pri, edge, title, mkts))

    ranked.sort(key=lambda r: (-r[0], -r[1]))
    for pri, edge, title, mkts in ranked:
        if len(toks) >= MAX_TOKENS:
            break
        ids = []
        for m in mkts:
            try:
                tk = json.loads(m.get("clobTokenIds", "[]"))
                ids.extend(tk[:2] if len(mkts) <= 2 else tk[:1])
            except Exception:
                pass
        if ids and len(toks) + len(ids) <= MAX_TOKENS:
            toks.extend(ids)
            why.append(title)
    return toks, why


def main():
    toks, why = build_watchlist()
    if not toks:
        print("book_recorder: empty watchlist, nothing to record")
        return
    day = datetime.datetime.now(datetime.timezone.utc)
    outdir = D / "books" / day.strftime("%Y-%m-%d")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{day.strftime('%H%M%S')}.jsonl.gz"

    n, bytes_out, reconnects = 0, 0, 0
    deadline = time.monotonic() + RECORD_MIN * 60
    with gzip.open(outfile, "wt") as f:
        f.write(json.dumps({"t": time.time(), "meta": {
            "tokens": len(toks), "events": why}}) + "\n")
        while time.monotonic() < deadline and n < MAX_MSGS and bytes_out < MAX_MB * 1e6:
            try:
                ws = websocket.create_connection(WS_URL, timeout=15)
                ws.send(json.dumps({"type": "market", "assets_ids": toks}))
                last_msg = time.monotonic()
                while time.monotonic() < deadline and n < MAX_MSGS and bytes_out < MAX_MB * 1e6:
                    if time.monotonic() - last_msg > STALE_S:
                        break        # data-inactivity watchdog: reconnect
                    try:
                        msg = ws.recv()
                    except websocket.WebSocketTimeoutException:
                        continue
                    if not msg:
                        continue
                    last_msg = time.monotonic()
                    line = json.dumps({"t": round(time.time(), 3), "m": msg},
                                      separators=(",", ":")) + "\n"
                    f.write(line)
                    n += 1
                    bytes_out += len(line)
                ws.close()
            except Exception as exc:
                reconnects += 1
                if reconnects > 20:
                    print(f"book_recorder: giving up after 20 reconnects ({type(exc).__name__})")
                    break
                time.sleep(min(2 * reconnects, 30))

    print(f"book_recorder: {n} messages, {bytes_out/1e6:.1f} MB raw, "
          f"{reconnects} reconnects, {len(why)} events -> {outfile.name}")
    for w in why[:6]:
        print(f"  watching: {w}")


if __name__ == "__main__":
    main()
