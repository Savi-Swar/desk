"""Resolved-market lookup against the gamma API.

The obvious query — closed=true ordered by endDate descending — is useless for
grading: it sorts far-future endDates (2028+) first, so paging 800 markets deep
never reaches markets that actually settled last week. Both graders were
silently finding zero matches because of it. Window by end date instead.

A closed market is only counted as resolved when one outcome price has gone to
~1; long-dated "before GTA VI?" style markets carry a placeholder endDate and
still trade mid-book, so they must not be scored as settled.
"""
import json
import time
import urllib.request

UA = {"User-Agent": "research saviswarup@gmail.com"}
DECISIVE = 0.99


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def resolved_between(start_iso, end_iso, max_pages=60):
    """title -> {outcome_name: won_bool} for markets settled in the window.

    A transient error on one page must not end paging: bailing out early was
    dropping several hundred markets per run, so the same market matched on one
    night and not the next. Retry the page, and only stop on a genuinely empty
    one.
    """
    res = {}
    for off in range(0, max_pages * 100, 100):
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
            break
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
    return res
