"""Distributed marks crawl — one shard of the price-history backfill.

The serial crawl runs ~20h on one machine; this shards it across ephemeral CI
workers (.github/workflows/marks-crawl.yml). Coordination is deliberately
minimal and idempotent:

  partition  sha1(market_id) % NSHARDS == SHARD  (deterministic, disjoint,
             covering — pinned by tests/test_marks_shard.py)
  input      data-release/marks_worklist.csv.gz, committed (one compact row
             per market: id, token, endDate, labels)
  output     marks_shard_{SHARD}.csv.gz, uploaded as a CI artifact
  shuffle    the merge job downloads all shard artifacts, dedups by id, and
             commits the release file — shards never talk to each other
  failure    a dead shard loses only its partition; rerunning the workflow
             re-crawls idempotently (dedup at merge)

    SHARD=3 NSHARDS=12 python marks_shard.py
"""
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import pathlib
import time
import urllib.request

UA = {"User-Agent": "research saviswarup@gmail.com"}
ROOT = pathlib.Path(__file__).parent
WORKLIST = ROOT / "data-release" / "marks_worklist.csv.gz"
SHARD = int(os.environ.get("SHARD", 0))
NSHARDS = int(os.environ.get("NSHARDS", 12))
SLEEP = float(os.environ.get("SLEEP", 0.3))
HORIZONS_H = (24, 72, 168)

FIELDS = ["id", "endDate", "category", "volume", "winner_idx", "negRisk",
          "p_24h", "p_72h", "p_168h"]


def mine(market_id):
    h = hashlib.sha1(market_id.encode()).digest()
    return int.from_bytes(h[:4], "big") % NSHARDS == SHARD


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(2 * (i + 1))


def parse_end(s):
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError, TypeError):
        return None


def mark_at(history, t):
    best = None
    for pt in history:
        if pt["t"] <= t:
            best = pt["p"]
        else:
            break
    return best


def main():
    rows = [r for r in csv.DictReader(gzip.open(WORKLIST, "rt"))
            if mine(r["id"])]
    out = ROOT / f"marks_shard_{SHARD}.csv.gz"
    n_ok = n_empty = 0
    with gzip.open(out, "wt", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for i, r in enumerate(rows):
            end_ts = parse_end(r["endDate"])
            if end_ts is None:
                continue
            d = get("https://clob.polymarket.com/prices-history"
                    f"?market={r['token']}&interval=max&fidelity=720")
            hist = (d or {}).get("history") or []
            row = {k: r.get(k) for k in
                   ("id", "endDate", "category", "volume", "winner_idx",
                    "negRisk")}
            got = False
            for h in HORIZONS_H:
                p = mark_at(hist, end_ts - h * 3600)
                row[f"p_{h}h"] = p
                got = got or p is not None
            if got:
                w.writerow(row)
                n_ok += 1
            else:
                n_empty += 1
            if i == 200 and n_ok == 0:
                ctrl = get("https://clob.polymarket.com/prices-history"
                           "?market=21742633143463906290569050155826241533067272736897614950488156847949938836455"
                           "&interval=max&fidelity=720")
                if not ((ctrl or {}).get("history")):
                    raise SystemExit("ABORT: control token empty — endpoint down")
            if i % 500 == 0:
                print(f"shard {SHARD}/{NSHARDS}: {i:,}/{len(rows):,} "
                      f"marks {n_ok:,} empty {n_empty:,}", flush=True)
            time.sleep(SLEEP)
    print(f"shard {SHARD}: DONE {n_ok:,} marks, {n_empty:,} empty -> {out.name}")


if __name__ == "__main__":
    main()
