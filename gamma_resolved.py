"""Resolved-market lookup against the gamma API.

Both graders used to scan `closed=true` ordered by endDate descending. That is
useless for grading: it sorts far-future endDates (2028+) first, so paging never
reached markets that settled last week, and gamma refuses offsets past ~2000
with a 422 that the old code swallowed as end-of-data. Result — shadow_grader
reported "graded 0" every night regardless of what had resolved.

Look titles up directly instead: one public-search call per distinct title, no
paging, no truncation.

A closed market counts as resolved only when one outcome price has gone to ~1.
Long-dated "before GTA VI?" style markets sit at 0.5/0.5 with a placeholder end
date and must not be scored as settled.
"""
import json
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "research saviswarup@gmail.com"}
DECISIVE = 0.99
SEARCH = "https://gamma-api.polymarket.com/public-search"


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _legs(market):
    """{outcome_name: won_bool} if decisively resolved, else None."""
    try:
        o = json.loads(market.get("outcomes", "[]"))
        p = [float(x) for x in json.loads(market.get("outcomePrices", "[]"))]
    except Exception:
        return None
    if len(o) < 2 or len(p) < 2 or max(p) < DECISIVE:
        return None
    return {str(o[i]): p[i] > 0.5 for i in range(len(o))}


def resolve_titles(titles, pause=0.15):
    """title -> {outcome_name: won_bool} for those that have settled."""
    res = {}
    for title in sorted({str(t).strip() for t in titles if str(t).strip()}):
        url = f"{SEARCH}?q={urllib.parse.quote(title)}&limit_per_type=10"
        data = None
        for attempt in range(3):
            try:
                data = get(url)
                break
            except Exception:
                time.sleep(1.0 * (attempt + 1))
        if data is None:
            continue
        for ev in data.get("events", []):
            for m in ev.get("markets", []):
                if (m.get("question") or "").strip() != title:
                    continue
                legs = _legs(m)
                if legs:
                    res[title] = legs
        time.sleep(pause)
    return res
