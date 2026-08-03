"""RTDS trade firehose recorder — the real-fills feed.

The per-market last_trade_price channel is too sparse to measure fills
(~5 trades / 24 min), which is why the shrinkage-based markout was 1,500x
inflated by cancels. This records the site-wide activity firehose
(wss://ws-live-data.polymarket.com), which streams real matched TRADES
across the whole venue (~tens/sec). Those are ground-truth executions: the
data a trustworthy markout must be built on.

Writes gzip'd jsonl of trade records to collected/trades/YYYY-MM-DD/*.jsonl.gz
— one line per real trade: {t, asset, conditionId, price, size, side, slug}.
Downstream, a fill is real only when a trade crosses a hypothetical resting
quote; markout is measured off these, not off book shrinkage.
"""
import datetime
import gzip
import json
import os
import pathlib
import time

import websocket

D = pathlib.Path(__file__).parent / "collected"
WS = "wss://ws-live-data.polymarket.com"
# the single subscribe shape verified to stream trades (lowercase "trades");
# sending extra/malformed subscribes makes the server drop the connection
SUB = '{"action":"subscribe","subscriptions":[{"topic":"activity","type":"trades"}]}'
RECORD_MIN = float(os.environ.get("FH_MIN", 24))
MAX_MB = 45
STALE_S = 60


def is_trade(p):
    """A payload is a real trade if it carries price, size, side and an asset."""
    if not isinstance(p, dict):
        return False
    t = str(p.get("type", "")).upper()
    has = all(k in p for k in ("price", "size", "asset"))
    return has and (t in ("TRADE", "") or "side" in p)


def trade_row(t, p):
    """Full universal trade record — one feed, every arb. Fields chosen so a
    single trade stream serves all tier-4+ detectors:
      markout/maker   : price, size, side, ts (REAL trade time), fee (realized)
      neg-risk set    : cid + outcomeIndex (group a market's outcomes)
      single-condition: cid + outcome (YES/NO of one condition)
      whale-following : wallet (proxyWallet) + name
      dedup / id      : tx (transactionHash) — the on-chain trade id
      category/venue  : slug
    ts is the venue's own trade timestamp (not our receive time), so markout
    timing is exact; fee is the realized taker fee (ground truth vs modeled)."""
    return {"t": round(t, 3), "ts": p.get("timestamp"),
            "tx": p.get("transactionHash"),
            "asset": p.get("asset"), "cid": p.get("conditionId"),
            "price": p.get("price"), "size": p.get("size"),
            "side": p.get("side"), "fee": p.get("fee"),
            "outcome": p.get("outcome"), "oidx": p.get("outcomeIndex"),
            "wallet": p.get("proxyWallet"), "name": p.get("name"),
            "slug": (p.get("eventSlug") or p.get("slug") or "")[:40]}


def main():
    day = datetime.datetime.now(datetime.timezone.utc)
    outdir = D / "trades" / day.strftime("%Y-%m-%d")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{day.strftime('%H%M%S')}.jsonl.gz"

    n, raw, bytes_out, reconnects, dups = 0, 0, 0, 0, 0
    seen_tx = set()          # dedup on transactionHash (a trade can echo,
                             # and reconnects replay the connect burst)
    deadline = time.monotonic() + RECORD_MIN * 60
    with gzip.open(outfile, "wt") as f:
        f.write(json.dumps({"t": time.time(), "meta": {"feed": "RTDS activity"}}) + "\n")
        while time.monotonic() < deadline and bytes_out < MAX_MB * 1e6:
            try:
                ws = websocket.create_connection(WS, timeout=15)
                ws.send(SUB)
                last = time.monotonic()
                last_ping = time.monotonic()
                while time.monotonic() < deadline and bytes_out < MAX_MB * 1e6:
                    # keepalive: without a ~5s PING the RTDS feed goes silent
                    # after the connect burst (that was the 0-trades bug)
                    if time.monotonic() - last_ping > 5:
                        try:
                            ws.send("PING")
                        except Exception:
                            break
                        last_ping = time.monotonic()
                    if time.monotonic() - last > STALE_S:
                        break
                    try:
                        msg = ws.recv()
                    except websocket.WebSocketTimeoutException:
                        continue
                    if not msg or msg == "PONG":
                        continue
                    last = time.monotonic()
                    raw += 1
                    try:
                        d = json.loads(msg)
                    except Exception:
                        continue
                    p = d.get("payload")
                    if not is_trade(p):
                        continue
                    # dedup: a (tx, asset, side) is one fill; drop echoes/replays.
                    # (tx alone can cover several legs of one on-chain tx, so key
                    # on tx+asset+side+price to keep distinct legs, drop true dups)
                    tx = p.get("transactionHash")
                    key = (tx, p.get("asset"), p.get("side"), p.get("price"),
                           p.get("size")) if tx else None
                    if key is not None:
                        if key in seen_tx:
                            dups += 1
                            continue
                        seen_tx.add(key)
                    line = json.dumps(trade_row(time.time(), p),
                                      separators=(",", ":")) + "\n"
                    f.write(line)
                    n += 1
                    bytes_out += len(line)
                ws.close()
            except Exception as exc:
                reconnects += 1
                if reconnects > 20:
                    print(f"firehose: giving up after 20 reconnects ({type(exc).__name__})")
                    break
                time.sleep(min(2 * reconnects, 30))

    print(f"firehose: {n:,} real trades ({dups:,} dups dropped, {raw:,} raw msgs), "
          f"{bytes_out/1e6:.1f} MB, {reconnects} reconnects -> {outfile.name}")


if __name__ == "__main__":
    main()
