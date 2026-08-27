"""Resolved-market loader — the labels for the calibration studies.

Pages through Gamma's closed markets and lands one row per market with the
fields the favorite-longshot study needs: what it asked, when it closed, how it
resolved, and how big it was. Output is data/resolved_markets.csv.gz (data/ is
gitignored — this is research input, not a ledger).

Resolution label: Gamma reports final outcomePrices like ["1","0"] once a
market resolves; outcome 0 winning means outcomePrices[0] == "1". Markets with
ambiguous finals (e.g. 50/50 refunds) are kept but flagged unresolved=1 so the
study can drop them.

    python fetch_resolved.py            # full pull (resumable, appends)
    PAGES=5 python fetch_resolved.py    # smoke test
"""
import csv
import gzip
import json
import os
import pathlib
import time
import urllib.request

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "data"
OUT = D / "resolved_markets.csv.gz"
STATE = D / "resolved_offset.txt"      # resume point
PAGE = 100
MAX_PAGES = int(os.environ.get("PAGES", 10_000))

FIELDS = ["id", "question", "slug", "conditionId", "category", "endDate",
          "closedTime", "volume", "liquidity", "outcomes", "final_prices",
          "winner_idx", "unresolved", "clobTokenIds", "createdAt", "negRisk"]


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def row_of(m):
    try:
        finals = json.loads(m.get("outcomePrices") or "[]")
        finals = [float(x) for x in finals]
    except (ValueError, TypeError):
        finals = []
    # resolved = exactly one outcome priced ~1
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


def main():
    D.mkdir(exist_ok=True)
    offset = int(STATE.read_text()) if STATE.exists() else 0
    mode = "at" if OUT.exists() and offset else "wt"
    n = kept = 0
    with gzip.open(OUT, mode, newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if mode == "wt":
            w.writeheader()
        for page in range(MAX_PAGES):
            batch = get("https://gamma-api.polymarket.com/markets"
                        f"?closed=true&limit={PAGE}&offset={offset}"
                        "&order=id&ascending=true")
            if not batch:
                break
            for m in batch:
                r = row_of(m)
                w.writerow(r)
                kept += 1
            n += len(batch)
            offset += len(batch)
            STATE.write_text(str(offset))
            if page % 25 == 0:
                print(f"  offset {offset:,} ({kept:,} rows)", flush=True)
            time.sleep(0.35)          # be polite; full pull is a background job
            if len(batch) < PAGE:
                break
    print(f"fetch_resolved: {kept:,} markets -> {OUT.name} (offset {offset:,})")


if __name__ == "__main__":
    main()
