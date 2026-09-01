"""Unit tests for fetch_resolved: row_of() winner extraction and window()
split/dedup logic. Pure stdlib; network is stubbed."""
import datetime as dt
import pathlib
import sys
import urllib.error
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import fetch_resolved as fr


def test_row_of():
    # single winner > 0.99 -> that index, resolved
    r = fr.row_of({"id": "1", "outcomePrices": '["1", "0"]'})
    assert r["winner_idx"] == 0 and r["unresolved"] == 0, r
    r = fr.row_of({"id": "2", "outcomePrices": '["0.001", "0.999"]'})
    assert r["winner_idx"] == 1 and r["unresolved"] == 0, r
    # exactly 0.99 is NOT a winner (strict >)
    r = fr.row_of({"id": "3", "outcomePrices": '["0.99", "0.01"]'})
    assert r["winner_idx"] is None and r["unresolved"] == 1, r
    # ambiguous final (50/50) -> unresolved
    r = fr.row_of({"id": "4", "outcomePrices": '["0.5", "0.5"]'})
    assert r["winner_idx"] is None and r["unresolved"] == 1, r
    # two "winners" (both > .99) -> unresolved, no arbitrary pick
    r = fr.row_of({"id": "5", "outcomePrices": '["1", "1"]'})
    assert r["winner_idx"] is None and r["unresolved"] == 1, r
    # malformed / missing prices -> unresolved, no crash
    r = fr.row_of({"id": "6", "outcomePrices": "not json"})
    assert r["winner_idx"] is None and r["unresolved"] == 1, r
    r = fr.row_of({"id": "7"})
    assert r["winner_idx"] is None and r["unresolved"] == 1, r
    # negRisk flag normalizes to 0/1
    assert fr.row_of({"id": "8", "negRisk": True})["negRisk"] == 1
    assert fr.row_of({"id": "9"})["negRisk"] == 0
    print("  fetch_resolved.row_of: winner/ambiguous/malformed OK")


class _Writer:
    def __init__(self):
        self.rows = []

    def writerow(self, r):
        self.rows.append(r)


def _params(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return {k: v[0] for k, v in q.items()}


def _patched(fake_get, cap=50):
    """(old state, apply) — saturate on the first full page to keep tests tiny."""
    return (fr.get, fr.time.sleep, fr.OFFSET_CAP), (fake_get, lambda s: None, cap)


def test_window_floor():
    """An always-saturated window must recurse, halve down to the 15-minute
    floor, and terminate — never loop. (A saturated page is discarded before
    the split, so a window truncated at the floor contributes 0 rows.)"""
    calls = {"n": 0}
    widths = []

    def fake_get(url, tries=5):
        calls["n"] += 1
        assert calls["n"] < 500, "window() looks like an infinite loop"
        p = _params(url)
        a = dt.datetime.strptime(p["end_date_min"], "%Y-%m-%dT%H:%M:%SZ")
        b = dt.datetime.strptime(p["end_date_max"], "%Y-%m-%dT%H:%M:%SZ")
        widths.append((b - a).total_seconds())
        return [{"id": f"m{i}", "outcomePrices": '["1","0"]'}
                for i in range(fr.PAGE)]           # always a full page

    old, new = _patched(fake_get)
    fr.get, fr.time.sleep, fr.OFFSET_CAP = new
    try:
        w = _Writer()
        a = dt.datetime(2026, 1, 1)
        got = fr.window(a, a + dt.timedelta(hours=1), set(), w)
    finally:
        fr.get, fr.time.sleep, fr.OFFSET_CAP = old

    # halved 3600 -> 1800 -> 900 -> 450 and stopped: no sub-floor splits
    assert min(widths) >= 450, f"split below the 15-min floor: {min(widths)}"
    assert {3600.0, 1800.0, 900.0} <= set(widths), f"no halving: {widths}"
    assert got == 0 and w.rows == [], "truncated windows must drop, not dupe"
    print(f"  fetch_resolved.window: saturation halved to the 15-min floor and "
          f"terminated ({calls['n']} pages)")


def test_window_split_dedup():
    """Wide windows saturate and split; narrow ones return short pages whose
    overlapping ids must be written exactly once."""
    widths = []

    def fake_get(url, tries=5):
        p = _params(url)
        a = dt.datetime.strptime(p["end_date_min"], "%Y-%m-%dT%H:%M:%SZ")
        b = dt.datetime.strptime(p["end_date_max"], "%Y-%m-%dT%H:%M:%SZ")
        width = (b - a).total_seconds()
        widths.append(width)
        if width >= 1800:                          # wide: saturated full page
            return [{"id": f"x{i}", "outcomePrices": '["1","0"]'}
                    for i in range(fr.PAGE)]
        # narrow: short page, SAME 60 ids in every leaf window
        return [{"id": f"m{i}", "outcomePrices": '["1","0"]'}
                for i in range(60)]

    old, new = _patched(fake_get)
    fr.get, fr.time.sleep, fr.OFFSET_CAP = new
    try:
        w = _Writer()
        seen = set()
        a = dt.datetime(2026, 1, 1)
        got = fr.window(a, a + dt.timedelta(hours=1), seen, w)
    finally:
        fr.get, fr.time.sleep, fr.OFFSET_CAP = old

    # 3600 split -> 2x1800 split -> 4x900 leaves, each offering the same ids
    assert widths.count(900.0) == 4, widths
    ids = [r["id"] for r in w.rows]
    assert len(ids) == len(set(ids)), "duplicate ids written"
    assert got == len(w.rows) == len(seen) == 60, (got, len(w.rows), len(seen))
    print("  fetch_resolved.window: split to 4 leaves, 240 offered -> "
          "60 unique rows (dedup by id)")


def test_window_no_split():
    """A short page ends the window without recursion; 422 forces a split."""
    def small_get(url, tries=5):
        return [{"id": f"s{i}", "outcomePrices": '["0","1"]'} for i in range(3)]

    old_get, old_sleep = fr.get, fr.time.sleep
    fr.get, fr.time.sleep = small_get, lambda s: None
    try:
        w = _Writer()
        a = dt.datetime(2026, 1, 1)
        got = fr.window(a, a + dt.timedelta(days=1), set(), w)
        assert got == 3 and len(w.rows) == 3

        # a 422 mid-window (batch None) splits; halves then return short pages
        state = {"first": True, "n": 0}

        def get_422_once(url, tries=5):
            if state["first"]:
                state["first"] = False
                raise urllib.error.HTTPError(url, 422, "wall", None, None)
            state["n"] += 1
            return [{"id": f"h{state['n']}", "outcomePrices": '["1","0"]'}]

        fr.get = get_422_once
        w2 = _Writer()
        got2 = fr.window(a, a + dt.timedelta(days=1), set(), w2)
        assert got2 == 2, f"422 should split into two halves, got {got2}"
    finally:
        fr.get, fr.time.sleep = old_get, old_sleep
    print("  fetch_resolved.window: short-page stop + 422 split OK")


if __name__ == "__main__":
    test_row_of()
    test_window_floor()
    test_window_split_dedup()
    test_window_no_split()
    print("test_fetch_resolved: PASS")
