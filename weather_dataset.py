#!/usr/bin/env python3
"""Build the Phase-2 weather backtest dataset.

One row per (temperature-market family, bucket): parsed bucket bounds, market
marks (p_24h/p_72h where the $5k-volume marks file has them), and the archived
D-1 model forecast + actual Tmax from open-meteo.

Families = Polymarket "Will the highest temperature in {city} be ... on {date}?"
negRisk ladders, grouped by (city, target date, unit). Only families with
exactly one winning bucket and >=5 parsed buckets are kept.

Inputs : data/resolved_markets.csv.gz, data/resolved_tail*.csv.gz,
         data/price_marks.csv.gz (multi-member gzip, via read_gz_tolerant)
Outputs: data/weather_families.csv.gz, data/weather_dataset_notes.md
Caches : data/city_geo2.json (geocoding), data/weather_wx_cache.json (API)

Stdlib only. Rerunnable: API results are cached, so reruns are cheap.
"""
import csv
import gzip
import io
import json
import math
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date as ddate
from datetime import datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import market_cats                          # noqa: E402
from study_longshot import read_gz_tolerant  # noqa: E402

D = pathlib.Path(__file__).parent / "data"
UA = {"User-Agent": "research saviswarup@gmail.com"}
RATE_S = 0.3          # seconds between API calls
CHUNK_DAYS = 92       # max days per ranged weather-API request
MAX_PAIRS = 6000      # trim to most-recent-N (city,date) pairs for API fetch
                      # (ranged per-city requests keep HTTP calls in the low
                      # hundreds, so the ~4000 budget cap is not binding here)

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}

# question-text bucket patterns (unit as stated in the question)
_Q_TAIL = (r"(.+?) on (january|february|march|april|may|june|july|august|"
           r"september|october|november|december) (\d{1,2})\?$")
RE_Q = re.compile(r"^will the highest temperature in (.+?) be " + _Q_TAIL, re.I)
# a handful of questions omit the word "be"
RE_Q2 = re.compile(r"^will the highest temperature in (.+?) " + _Q_TAIL, re.I)
RE_RANGE = re.compile(r"^(?:between )?(-?\d+)\s*[-–]\s*(-?\d+)\s*°([CF])$", re.I)
RE_BELOW = re.compile(r"^(-?\d+)\s*°([CF]) or (?:below|lower|less)$", re.I)
RE_ABOVE = re.compile(r"^(-?\d+)\s*°([CF]) or (?:above|higher|more)$", re.I)
RE_EXACT = re.compile(r"^(-?\d+)\s*°([CF])$", re.I)

CITY_NORM = {"nyc": "New York City"}
GEO_QUERY = {"New York City": "New York"}   # geocoder-friendly names


def parse_bucket(mid):
    """mid = the 'be X' clause. Returns (lo, hi, unit) with +-inf tails,
    lo==hi for exact single-degree buckets, stated bounds for ranges."""
    mid = mid.strip()
    m = RE_RANGE.match(mid)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if lo > hi:
            return None
        return lo, hi, m.group(3).upper()
    m = RE_BELOW.match(mid)
    if m:
        return float("-inf"), float(m.group(1)), m.group(2).upper()
    m = RE_ABOVE.match(mid)
    if m:
        return float(m.group(1)), float("inf"), m.group(2).upper()
    m = RE_EXACT.match(mid)
    if m:
        v = float(m.group(1))
        return v, v, m.group(2).upper()
    return None


def infer_date(month, day, slug, closed):
    """Year is absent from questions; take it from the slug when present,
    else pick the year that puts the target date nearest closedTime."""
    m = re.search(r"-(20\d\d)(?:-|$)", slug or "")
    if m:
        try:
            return ddate(int(m.group(1)), month, day)
        except ValueError:
            return None
    ref = None
    if closed:
        try:
            ref = ddate(int(closed[0:4]), int(closed[5:7]), int(closed[8:10]))
        except ValueError:
            ref = None
    if ref is None:
        return None
    best = None
    for y in (ref.year - 1, ref.year, ref.year + 1):
        try:
            d = ddate(y, month, day)
        except ValueError:
            continue
        if best is None or abs((d - ref).days) < abs((best - ref).days):
            best = d
    return best


def load_weather_binaries(stats):
    rows, seen = [], set()
    for fn in ("resolved_markets.csv.gz", "resolved_tail.csv.gz",
               "resolved_tail2.csv.gz"):
        p = D / fn
        if not p.exists():
            continue
        for r in read_gz_tolerant(p):
            rid = r.get("id")
            if not rid or rid in seen:
                continue
            seen.add(rid)
            q = (r.get("question") or "").strip()
            if market_cats.cat_of(r.get("slug", ""), q) != "weather":
                continue
            if not q.lower().startswith("will the highest temperature in "):
                if q.lower().startswith("will the lowest temperature in "):
                    stats["lowest_temp_skipped"] += 1
                continue
            rows.append(r)
    return rows


def http_json(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                out = json.loads(resp.read().decode("utf-8"))
            time.sleep(RATE_S)
            return out
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < tries - 1:
                time.sleep(2.0 * (i + 1))
                continue
            time.sleep(RATE_S)
            return None
        except Exception:
            if i < tries - 1:
                time.sleep(2.0 * (i + 1))
                continue
            return None
    return None


def geocode(city, cache):
    if city in cache:
        return cache[city]
    name = GEO_QUERY.get(city, city)
    url = ("https://geocoding-api.open-meteo.com/v1/search?" +
           urllib.parse.urlencode({"name": name, "count": 1}))
    j = http_json(url)
    hit = None
    if j and j.get("results"):
        r0 = j["results"][0]
        hit = {"lat": r0["latitude"], "lon": r0["longitude"],
               "name": r0.get("name"), "country": r0.get("country"),
               "tz": r0.get("timezone", "auto")}
    cache[city] = hit
    (D / "city_geo2.json").write_text(json.dumps(cache, indent=1))
    return hit


def chunks(dates):
    """contiguous [start,end] windows covering the sorted dates."""
    out, dates = [], sorted(dates)
    lo = prev = dates[0]
    for d in dates[1:]:
        if (d - lo).days >= CHUNK_DAYS or (d - prev).days > 14:
            out.append((lo, prev))
            lo = d
        prev = d
    out.append((lo, prev))
    return out


def fetch_city(city, geo, dates, cache, counters):
    """Fill cache['{city}|{date}'] = {'fc': d-1 forecast Tmax C, 'ac': actual
    Tmax C}. Ranged per-city calls; per-date max over hourly values."""
    need_fc = [d for d in dates if cache.get(f"{city}|{d}", {}).get("fc") is None
               or f"{city}|{d}" not in cache]
    need_ac = [d for d in dates if cache.get(f"{city}|{d}", {}).get("ac") is None
               or f"{city}|{d}" not in cache]
    base = {"latitude": geo["lat"], "longitude": geo["lon"], "timezone": geo["tz"]}
    if need_fc:
        for lo, hi in chunks(need_fc):
            q = dict(base, hourly="temperature_2m_previous_day1",
                     models="gfs_seamless", start_date=lo.isoformat(),
                     end_date=hi.isoformat())
            j = http_json("https://previous-runs-api.open-meteo.com/v1/forecast?"
                          + urllib.parse.urlencode(q))
            counters["calls"] += 1
            byday = defaultdict(list)
            if j and "hourly" in j:
                key = next((k for k in j["hourly"] if k.startswith("temperature")), None)
                if key:
                    for t, v in zip(j["hourly"]["time"], j["hourly"][key]):
                        if v is not None:
                            byday[t[:10]].append(v)
            for d in need_fc:
                if lo <= d <= hi:
                    vs = byday.get(d.isoformat(), [])
                    e = cache.setdefault(f"{city}|{d}", {})
                    e["fc"] = round(max(vs), 2) if len(vs) >= 12 else None
    if need_ac:
        for lo, hi in chunks(need_ac):
            q = dict(base, daily="temperature_2m_max", start_date=lo.isoformat(),
                     end_date=hi.isoformat())
            j = http_json("https://archive-api.open-meteo.com/v1/archive?"
                          + urllib.parse.urlencode(q))
            counters["calls"] += 1
            got = {}
            if j and "daily" in j:
                for t, v in zip(j["daily"]["time"], j["daily"]["temperature_2m_max"]):
                    got[t] = v
            for d in need_ac:
                if lo <= d <= hi:
                    e = cache.setdefault(f"{city}|{d}", {})
                    e["ac"] = got.get(d.isoformat())


def c_to_unit(v, unit):
    if v is None:
        return None
    return round(v * 9 / 5 + 32, 2) if unit == "F" else round(v, 2)


def fmt(v):
    if v is None:
        return ""
    if v == float("inf"):
        return "inf"
    if v == float("-inf"):
        return "-inf"
    return f"{v:g}"


def main():
    stats = defaultdict(int)
    rows = load_weather_binaries(stats)
    stats["highest_temp_binaries"] = len(rows)

    marks = {}
    for m in read_gz_tolerant(D / "price_marks.csv.gz"):
        marks[m["id"]] = m

    # ---- parse binaries into (family, bucket) records
    fams = defaultdict(list)
    for r in rows:
        if r.get("unresolved") not in ("0", "", None):
            stats["drop_unresolved"] += 1
            continue
        q = (r.get("question") or "").strip()
        m = RE_Q.match(q) or RE_Q2.match(q)
        if not m:
            stats["drop_question_parse"] += 1
            continue
        city = CITY_NORM.get(m.group(1).strip().lower(), m.group(1).strip())
        b = parse_bucket(m.group(2))
        if not b:
            stats["drop_bucket_parse"] += 1
            continue
        d = infer_date(MONTHS[m.group(3).lower()], int(m.group(4)),
                       r.get("slug"), r.get("closedTime") or r.get("endDate"))
        if not d:
            stats["drop_date_parse"] += 1
            continue
        lo, hi, unit = b
        mk = marks.get(r["id"], {})

        def _p(x):
            try:
                return float(x)
            except (TypeError, ValueError):
                return None
        try:
            vol = float(r.get("volume") or 0)
        except ValueError:
            vol = 0.0
        # "arch-" slugs are a second, separately-resolved ladder co-listed on
        # the same (city,date) with shifted bounds - keep them as own families
        tag = "arch" if (r.get("slug") or "").startswith("arch-") else "std"
        fams[(city, d, unit, tag)].append({
            "id": r["id"], "lo": lo, "hi": hi,
            "won": 1 if r.get("winner_idx") == "0" else 0,
            "p24": _p(mk.get("p_24h")), "p72": _p(mk.get("p_72h")),
            "vol": vol})

    # ---- family filters
    keep = {}
    for key, bs in fams.items():
        # duplicate bucket bounds: keep the higher-volume listing
        best = {}
        for b in bs:
            k = (b["lo"], b["hi"])
            if k not in best or b["vol"] > best[k]["vol"]:
                if k in best:
                    stats["dup_bucket_dropped"] += 1
                best[k] = b
            else:
                stats["dup_bucket_dropped"] += 1
        bs = sorted(best.values(), key=lambda b: (b["lo"], b["hi"]))
        nwin = sum(b["won"] for b in bs)
        if len(bs) < 5:
            stats["drop_family_lt5_buckets"] += 1
            continue
        if nwin != 1:
            stats["drop_family_bad_winner_count"] += 1
            continue
        keep[key] = bs
    stats["families_kept"] = len(keep)
    stats["families_total_grouped"] = len(fams)

    # ---- weather APIs
    geo_cache = {}
    gp = D / "city_geo2.json"
    if gp.exists():
        geo_cache = json.loads(gp.read_text())
    wx_path = D / "weather_wx_cache.json"
    wx = json.loads(wx_path.read_text()) if wx_path.exists() else {}
    counters = {"calls": 0}

    pairs = sorted({(c, d) for (c, d, u, t) in keep}, key=lambda p: p[1])
    if len(pairs) > MAX_PAIRS:
        stats["pairs_trimmed_for_fetch"] = len(pairs) - MAX_PAIRS
        pairs = pairs[-MAX_PAIRS:]
    fetch_set = set(pairs)
    bycity = defaultdict(list)
    for c, d in pairs:
        bycity[c].append(d)
    for city in sorted(bycity):
        geo = geocode(city, geo_cache)
        if not geo:
            stats["geocode_failed"] += 1
            print(f"[geo] FAILED {city}", file=sys.stderr)
            continue
        fetch_city(city, geo, bycity[city], wx, counters)
        wx_path.write_text(json.dumps(wx))
        done = sum(1 for d in bycity[city]
                   if wx.get(f"{city}|{d}", {}).get("fc") is not None)
        print(f"[wx] {city}: {done}/{len(bycity[city])} forecasts, "
              f"{counters['calls']} calls so far", file=sys.stderr)

    # ---- output
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["family_id", "city", "date", "unit", "k_buckets", "bucket_lo",
                "bucket_hi", "won", "p24", "p72", "volume", "fc_d1_tmax",
                "actual_tmax"])
    n_rows = 0
    for (city, d, unit, tag) in sorted(keep, key=lambda k: (k[1], k[0], k[2], k[3])):
        bs = keep[(city, d, unit, tag)]
        fid = f"{city.lower().replace(' ', '-')}_{d}_{unit}"
        if tag != "std":
            fid += f"_{tag}"
        e = wx.get(f"{city}|{d}", {}) if (city, d) in fetch_set else {}
        fc = c_to_unit(e.get("fc"), unit)
        ac = c_to_unit(e.get("ac"), unit)
        for b in bs:
            w.writerow([fid, city, d.isoformat(), unit, len(bs), fmt(b["lo"]),
                        fmt(b["hi"]), b["won"], fmt(b["p24"]), fmt(b["p72"]),
                        f"{b['vol']:.2f}", fmt(fc), fmt(ac)])
            n_rows += 1
    with gzip.open(D / "weather_families.csv.gz", "wt") as fh:
        fh.write(out.getvalue())
    stats["csv_rows"] = n_rows
    stats["api_calls_this_run"] = counters["calls"]

    write_notes(keep, wx, fetch_set, stats, geo_cache)
    print(json.dumps(stats, indent=1))


def write_notes(keep, wx, fetch_set, stats, geo_cache):
    have_fc = have_ac = have_marks = 0
    bias = defaultdict(list)          # city -> actual - forecast (C)
    resoff = defaultdict(list)        # city -> winner-bucket mid - ERA5 actual (C)
    inb = 0
    for (city, d, unit, tag), bs in keep.items():
        e = wx.get(f"{city}|{d}", {}) if (city, d) in fetch_set else {}
        ac = e.get("ac")
        if ac is not None:
            w = next(b for b in bs if b["won"])
            acu = ac * 9 / 5 + 32 if unit == "F" else ac
            if w["lo"] - 0.5 <= acu <= w["hi"] + 0.5:
                inb += 1
            if math.isfinite(w["lo"]) and math.isfinite(w["hi"]):
                mid = (w["lo"] + w["hi"]) / 2 - acu
                resoff[city].append(mid * 5 / 9 if unit == "F" else mid)
    for (city, d, unit, tag), bs in keep.items():
        e = wx.get(f"{city}|{d}", {}) if (city, d) in fetch_set else {}
        if e.get("fc") is not None:
            have_fc += 1
        if e.get("ac") is not None:
            have_ac += 1
        if e.get("fc") is not None and e.get("ac") is not None:
            bias[city].append(e["ac"] - e["fc"])
        if any(b["p24"] is not None or b["p72"] is not None for b in bs):
            have_marks += 1
    n = len(keep)
    L = []
    L.append("# weather_families dataset notes\n")
    L.append(f"Built {datetime.now():%Y-%m-%d %H:%M} by weather_dataset.py. "
             f"Output data/weather_families.csv.gz ({stats['csv_rows']} bucket rows).\n")
    L.append("## Counts\n")
    L.append(f"- highest-temp binaries in label files: {stats['highest_temp_binaries']} "
             f"(lowest-temp skipped: {stats['lowest_temp_skipped']})")
    L.append(f"- parse failures dropped: question {stats['drop_question_parse']}, "
             f"bucket {stats['drop_bucket_parse']}, date {stats['drop_date_parse']}, "
             f"unresolved {stats['drop_unresolved']}, "
             f"duplicate-bucket listings {stats['dup_bucket_dropped']}")
    L.append(f"- families grouped: {stats['families_total_grouped']}; kept "
             f"(>=5 buckets, exactly one winner): {n} "
             f"(dropped: <5 buckets {stats['drop_family_lt5_buckets']}, "
             f"winner-count!=1 {stats['drop_family_bad_winner_count']})")
    L.append(f"- families with any marks (p24 or p72): {have_marks}")
    L.append(f"- families with D-1 forecast: {have_fc}; with actual Tmax: {have_ac}")
    if stats.get("pairs_trimmed_for_fetch"):
        L.append(f"- (city,date) pairs trimmed from API fetch (kept most recent "
                 f"{MAX_PAIRS}): {stats['pairs_trimmed_for_fetch']}")
    L.append(f"- API calls this run: {stats['api_calls_this_run']} "
             f"(ranged per-city requests; results cached in data/weather_wx_cache.json)")
    L.append("\n## Forecast bias (actual - D-1 GFS forecast Tmax, degC)\n")
    L.append("| city | n | mean bias | note |")
    L.append("|---|---|---|---|")
    allb = []
    for city in sorted(bias, key=lambda c: -len(bias[c])):
        v = bias[city]
        allb += v
        g = geo_cache.get(city) or {}
        L.append(f"| {city} | {len(v)} | {sum(v)/len(v):+.2f} | "
                 f"{g.get('name','?')}, {g.get('country','?')} |")
    if allb:
        L.append(f"| **ALL** | {len(allb)} | {sum(allb)/len(allb):+.2f} | |")
    L.append("\n## Caveat: resolution source vs ERA5 'actual'\n")
    nres = sum(len(v) for v in resoff.values())
    L.append(f"Markets resolve on local station observations, not reanalysis. The "
             f"ERA5 grid actual_tmax lands inside the winning bucket (+-0.5deg "
             f"slack) in only {inb}/{len(keep)} families. Mean offset "
             f"(winner-bucket midpoint - ERA5 actual, degC, middle buckets only, "
             f"n={nres}): "
             f"{sum(v for vs in resoff.values() for v in vs)/max(nres,1):+.2f}. "
             f"Worst cities (n>=50):")
    for city in sorted(resoff, key=lambda c: -abs(sum(resoff[c])/len(resoff[c]))):
        v = resoff[city]
        if len(v) >= 50:
            L.append(f"- {city}: {sum(v)/len(v):+.2f} C (n={len(v)})")
    L.append("Any backtest should calibrate fc_d1_tmax to the resolution station "
             "(e.g. per-city offset fit on a training window), not use it raw.")
    L.append("\nBucket bound conventions: integer degrees as stated in the question; "
             "'X or below' -> (-inf, X], 'X or above/higher' -> [X, inf), "
             "'between A-B' -> [A, B] on integer degrees, exact 'X' -> lo=hi=X. "
             "won=1 means that binary's YES resolved (winner_idx==0). "
             "fc_d1_tmax = max over the 24 hourly temperature_2m_previous_day1 "
             "values (gfs_seamless, city-local tz), converted to the family unit; "
             "actual_tmax from archive daily temperature_2m_max. p24/p72 are "
             "last-trade marks (volume>=$5k only) and sum >1 across a family - "
             "renormalize before calibration use (see weather_artifact_check.md).")
    (D / "weather_dataset_notes.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
