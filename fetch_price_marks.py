"""Pre-resolution price marks — the x-axis of the calibration study.

For each resolved market (from fetch_resolved.py), pull the CLOB price history
of outcome-0's token and record the last trade price at fixed horizons before
the market's end: 24h, 72h, and 7d. Study 1 then compares price-at-horizon to
the resolution outcome: perfectly calibrated markets resolve YES a fraction p
of the time when priced p; the favorite-longshot bias is a systematic gap.

Filters: resolved binary markets with volume >= MIN_VOL (default $5k) — the
bias question is about tradeable markets, not dust. Resumable: done ids are
tracked in data/price_marks_done.txt; safe to rerun after a crash.

    python fetch_price_marks.py                 # full sweep of the label file
    MIN_VOL=50000 python fetch_price_marks.py   # bigger markets only
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
LABEL_FILES = ("resolved_markets.csv.gz", "resolved_tail.csv.gz",
               "resolved_tail2.csv.gz")
OUT = D / "price_marks.csv.gz"
DONE = D / "price_marks_done.txt"
MIN_VOL = float(os.environ.get("MIN_VOL", 5000))
HORIZONS_H = (24, 72, 168)          # hours before endDate

FIELDS = ["id", "endDate", "category", "volume", "winner_idx", "negRisk",
          "p_24h", "p_72h", "p_168h"]


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
    """last price at-or-before t (None if history starts later)."""
    best = None
    for pt in history:
        if pt["t"] <= t:
            best = pt["p"]
        else:
            break
    return best


def main():
    label_paths = [D / fn for fn in LABEL_FILES if (D / fn).exists()]
    if not label_paths:
        print("run fetch_resolved.py first")
        return
    done = set(DONE.read_text().split()) if DONE.exists() else set()
    def lifetime_ok(r):
        """a market must live >= ~26h to have any T-24h mark at 12h fidelity;
        hourlies (the bulk of recent listings) can never contribute."""
        try:
            c = dt.datetime.fromisoformat((r["createdAt"] or "").replace("Z", "+00:00"))
            e = dt.datetime.fromisoformat((r["endDate"] or "").replace("Z", "+00:00"))
            return (e - c).total_seconds() >= 26 * 3600
        except (ValueError, TypeError):
            return True                     # unknown lifetime: try it
    rows, seen = [], set()
    for lp in label_paths:
        try:
            for r in csv.DictReader(gzip.open(lp, "rt")):
                if (r["id"] in seen or r["unresolved"] != "0"
                        or float(r["volume"] or 0) < MIN_VOL
                        or r["clobTokenIds"] in ("", "[]", None)
                        or r["id"] in done or not lifetime_ok(r)):
                    continue
                seen.add(r["id"])
                rows.append(r)
        except (EOFError, OSError):
            pass
    # newest first: recent markets definitely have CLOB history (pre-2023 was
    # AMM-era and often has none, which would false-trip the all-empty guard),
    # and the recent regime is the one the studies weight most.
    rows.sort(key=lambda r: r.get("endDate") or "", reverse=True)
    print(f"to fetch: {len(rows):,} markets (>= ${MIN_VOL:,.0f} vol, "
          f"{len(done):,} already done)")

    mode = "at" if OUT.exists() and done else "wt"
    n_ok = n_empty = 0
    with gzip.open(OUT, mode, newline="") as f, DONE.open("a") as df:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if mode == "wt":
            w.writeheader()
        for i, r in enumerate(rows):
            end_ts = parse_end(r["endDate"])
            if end_ts is None:
                df.write(r["id"] + "\n")
                continue
            try:
                tok = json.loads(r["clobTokenIds"])[0]
            except (ValueError, IndexError):
                df.write(r["id"] + "\n")
                continue
            d = get("https://clob.polymarket.com/prices-history"
                    f"?market={tok}&interval=max&fidelity=720")
            hist = (d or {}).get("history") or []
            row = {k: r.get(k) for k in
                   ("id", "endDate", "category", "volume", "winner_idx", "negRisk")}
            got_any = False
            for h in HORIZONS_H:
                p = mark_at(hist, end_ts - h * 3600)
                row[f"p_{h}h"] = p
                got_any = got_any or p is not None
            if got_any:
                w.writerow(row)
                n_ok += 1
            else:
                n_empty += 1
            df.write(r["id"] + "\n")
            if i == 200 and n_ok == 0:
                # before declaring the endpoint broken, probe a token known to
                # have history (hourly-market runs can be legitimately empty)
                ctrl = get("https://clob.polymarket.com/prices-history"
                           "?market=21742633143463906290569050155826241533067272736897614950488156847949938836455"
                           "&interval=max&fidelity=720")
                if not ((ctrl or {}).get("history")):
                    raise SystemExit("ABORT: control token empty too — "
                                     "endpoint/params broken")
                print("  (200 empties but control healthy — continuing)")
            if i % 250 == 0:
                print(f"  {i:,}/{len(rows):,}  marks {n_ok:,}  empty {n_empty:,}",
                      flush=True)
                f.flush()
            time.sleep(0.25)
    print(f"price marks: {n_ok:,} markets with data, {n_empty:,} empty histories")


if __name__ == "__main__":
    main()
