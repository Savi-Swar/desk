"""Resolved-market lookup against the gamma API.

The obvious query — closed=true ordered by endDate descending — is useless for
grading: it sorts far-future endDates (2028+) first, so paging 800 markets deep
never reaches markets that actually settled last week. Both graders were
silently finding zero matches because of it. Window by end date instead.

A closed market is only counted as resolved when one outcome price has gone to
~1; long-dated "before GTA VI?" style markets carry a placeholder endDate and
still trade mid-book, so they must not be scored as settled.
"""
import datetime
import json
import time
import urllib.request

UA = {"User-Agent": "research saviswarup@gmail.com"}
DECISIVE = 0.99


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


MAX_OFFSET = 2000   # gamma returns HTTP 422 past this


def _page_window(start_iso, end_iso, res):
    """Page one date window into res. True if it hit the offset cap."""
    for off in range(0, MAX_OFFSET + 100, 100):
        url = ("https://gamma-api.polymarket.com/markets?closed=true"
               f"&end_date_min={start_iso}&end_date_max={end_iso}"
               f"&limit=100&offset={off}")
        mk = None
        for attempt in range(4):
            try:
                mk = get(url)
                break
            except Exception:
                time.sleep(1.5 * (attempt + 1))
        if mk is None:
            raise RuntimeError(f"gamma paging failed at offset {off}")
        if not mk:
            return False
        for m in mk:
            try:
                o = json.loads(m.get("outcomes", "[]"))
                p = [float(x) for x in json.loads(m.get("outcomePrices", "[]"))]
            except Exception:
                continue
            if len(o) < 2 or len(p) < 2 or max(p) < DECISIVE:
                continue
            title = (m.get("question") or "").strip()
            res[title] = {str(o[i]): p[i] > 0.5 for i in range(len(o))}
        time.sleep(0.1)
    return True


def resolved_between(start_iso, end_iso):
    """title -> {outcome_name: won_bool} for markets settled in the window.

    Walks the range one day at a time. A single wide window silently truncates:
    gamma refuses offsets past MAX_OFFSET, and the old code treated that error
    as end-of-data, so a busy range lost every market past the cap and the same
    market would match on one night and not the next.
    """
    start = datetime.datetime.fromisoformat(start_iso[:10]).replace(
        tzinfo=datetime.timezone.utc)
    end = datetime.datetime.fromisoformat(end_iso[:10]).replace(
        tzinfo=datetime.timezone.utc) + datetime.timedelta(days=1)
    res, capped = {}, []
    day = start
    while day < end:
        _scan(day, day + datetime.timedelta(days=1), res, capped)
        day += datetime.timedelta(days=1)
    if capped:
        print(f"  [warn] offset cap still hit on {len(capped)} slice(s) — "
              "some markets not scanned")
    return res


def _scan(lo, hi, res, capped, depth=0):
    """Scan [lo, hi); if the window overflows the offset cap, split and recurse."""
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    if not _page_window(lo.strftime(fmt), hi.strftime(fmt), res):
        return
    if depth >= 4:            # ~90-minute slices; give up rather than spin
        capped.append(lo.strftime(fmt))
        return
    mid = lo + (hi - lo) / 2
    _scan(lo, mid, res, capped, depth + 1)
    _scan(mid, hi, res, capped, depth + 1)
