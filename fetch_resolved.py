"""Resolved-market loader — the labels for the calibration studies.

Gamma's offset pagination 422s past ~2,000 rows, so a single closed=true sweep
cannot reach the full history. Instead we sweep END-DATE WINDOWS (markets whose
end_date falls in [a, b)), paging inside each window and recursively halving any
window that saturates the offset cap (ISO datetimes: splits go sub-day,
down to 15-minute windows, so dense hourly-market days survive). Dedup by market id. Output:
data/resolved_markets.csv.gz (data/ is gitignored — research input, not ledger).

Resolution label: final outcomePrices like ["1","0"]; exactly one outcome > .99
=> that index won. Ambiguous finals kept but flagged unresolved=1.

    python fetch_resolved.py                       # full history (2020 -> now)
    START=2026-01-01 python fetch_resolved.py      # smaller range
"""
import csv
import datetime as dt
import gzip
import json
import os
import pathlib
import time
import urllib.request

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "data"
OUT = D / "resolved_markets.csv.gz"
PAGE = 100
OFFSET_CAP = 1900          # stay under the ~2k 422 wall
START = os.environ.get("START", "2020-01-01")

FIELDS = ["id", "question", "slug", "conditionId", "category", "endDate",
          "closedTime", "volume", "liquidity", "outcomes", "final_prices",
          "winner_idx", "unresolved", "clobTokenIds", "createdAt", "negRisk"]


def get(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 422:
                raise                      # offset wall — caller splits window
            time.sleep(3 * (i + 1))
        except Exception:
            time.sleep(3 * (i + 1))        # DNS blips etc: retry, don't die
    raise RuntimeError(f"gave up: {url[:120]}")


def row_of(m):
    try:
        finals = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
    except (ValueError, TypeError):
        finals = []
    winners = [i for i, p in enumerate(finals) if p > 0.99]
    winner = winners[0] if len(winners) == 1 else None
    return {
        "id": m.get("id"),
        "question": (m.get("question") or "")[:120],
        "slug": (m.get("slug") or "")[:80],
        "conditionId": m.get("conditionId"),
        "category": (m.get("category") or "")[:40],
        "endDate": m.get("endDate"),
        "closedTime": m.get("closedTime"),
        "volume": m.get("volumeNum") or m.get("volume"),
        "liquidity": m.get("liquidityNum") or m.get("liquidity"),
        "outcomes": (m.get("outcomes") or "")[:120],
        "final_prices": json.dumps(finals),
        "winner_idx": winner,
        "unresolved": 0 if winner is not None else 1,
        "clobTokenIds": m.get("clobTokenIds"),
        "createdAt": m.get("createdAt"),
        "negRisk": 1 if m.get("negRisk") else 0,
    }


def window(a, b, seen, writer, depth=0):
    """Fetch closed markets with end_date in [a, b); split if saturated."""
    base = ("https://gamma-api.polymarket.com/markets?closed=true"
            f"&end_date_min={a:%Y-%m-%dT%H:%M:%SZ}&end_date_max={b:%Y-%m-%dT%H:%M:%SZ}"
            "&order=id&ascending=true")
    got, offset = 0, 0
    while True:
        try:
            batch = get(f"{base}&limit={PAGE}&offset={offset}")
        except urllib.error.HTTPError:
            batch = None                    # hit the wall mid-window
        if batch is None or (len(batch) == PAGE and offset + PAGE > OFFSET_CAP):
            mid = a + (b - a) / 2
            if mid <= a or (b - a).total_seconds() < 900:
                print(f"  !! window {a:%F}..{b:%F} unsplittable, truncated")
                return got
            print(f"  split {a:%F}..{b:%F} ({got} rows in, recursing)")
            return (got + window(a, mid, seen, writer, depth + 1)
                        + window(mid, b, seen, writer, depth + 1))
        for m in batch:
            if m.get("id") in seen:
                continue
            seen.add(m.get("id"))
            writer.writerow(row_of(m))
            got += 1
        offset += len(batch)
        time.sleep(0.3)
        if len(batch) < PAGE:
            return got


def main():
    D.mkdir(exist_ok=True)
    seen = set()
    a = dt.datetime.strptime(START, "%Y-%m-%d")
    end = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    total = 0
    with gzip.open(OUT, "wt", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        # quarter-sized top windows; recursion handles the dense recent months
        while a < end:
            b = min(a + dt.timedelta(days=92), end + dt.timedelta(days=1))
            n = window(a, b, seen, w)
            total += n
            print(f"{a:%Y-%m-%d} .. {b:%Y-%m-%d}: {n:,} (total {total:,})",
                  flush=True)
            a = b
    print(f"fetch_resolved: {total:,} unique markets -> {OUT.name}")


if __name__ == "__main__":
    main()
