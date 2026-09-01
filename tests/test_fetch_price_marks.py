"""Unit tests for fetch_price_marks: mark_at() horizon lookup and parse_end().
(lifetime_ok is a closure inside main() and is not importable; its lifetime
rule is not unit-testable without a refactor.) Pure stdlib, no I/O."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import fetch_price_marks as fpm

HIST = [{"t": 100, "p": 0.10}, {"t": 200, "p": 0.20}, {"t": 300, "p": 0.30}]


def test_mark_at():
    # before any history -> None (no mark, not a zero)
    assert fpm.mark_at(HIST, 50) is None
    # exactly on a point -> that point (at-or-before is inclusive)
    assert fpm.mark_at(HIST, 100) == 0.10
    # mid-history -> last trade at-or-before t, not the next one
    assert fpm.mark_at(HIST, 250) == 0.20
    assert fpm.mark_at(HIST, 200) == 0.20
    # after the last point -> final price carries forward
    assert fpm.mark_at(HIST, 10_000) == 0.30
    # empty history -> None
    assert fpm.mark_at([], 250) is None
    print("  fetch_price_marks.mark_at: before/mid/after-history OK")


def test_parse_end():
    ts = fpm.parse_end("2026-01-01T00:00:00Z")
    assert ts == 1767225600.0, ts             # 2026-01-01 UTC epoch
    assert fpm.parse_end("2026-01-01T00:00:00+00:00") == ts
    assert fpm.parse_end("garbage") is None
    assert fpm.parse_end(None) is None
    assert fpm.parse_end("") is None
    print("  fetch_price_marks.parse_end: ISO/Z/garbage OK")


if __name__ == "__main__":
    test_mark_at()
    test_parse_end()
    print("test_fetch_price_marks: PASS")
