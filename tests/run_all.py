"""Repo test suite — run by CI on every push and locally via `make test`.

Aggregates the pre-registered engine/stats tests plus smoke tests for the
load-bearing utilities (classifier, tolerant readers).
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backtest"))


def test_classifier():
    from market_cats import cat_of
    cases = [
        ("bitcoin-above-on-august-5", "", "crypto"),
        ("highest-temperature-in-nyc-on-september-1", "", "weather"),
        ("will-trump-win", "", "politics"),
        ("lal-vs-bos-2026-01-01", "", "sports"),
        ("lol-t1-geng", "", "esports"),
        ("ukraine-ceasefire-by-march", "", "geopolitics"),
        ("will-the-10-year-treasury-yield-hit-4pt5", "", "econ"),
    ]
    for slug, q, want in cases:
        got = cat_of(slug, q)
        assert got == want, f"cat_of({slug!r}) = {got!r}, want {want!r}"
    print("  classifier smoke: 7/7")


def test_tolerant_reader():
    """multi-member + truncated gzip must both read fully."""
    import csv
    import gzip
    import io
    import tempfile
    from study_longshot import read_gz_tolerant
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "x.csv.gz"
        with gzip.open(p, "wt", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "winner_idx"])
            w.writerow(["1", "0"])
        with gzip.open(p, "at", newline="") as f:   # second member
            csv.writer(f).writerow(["2", "1"])
        rows = read_gz_tolerant(p)
        assert len(rows) == 2, f"multi-member read {len(rows)} rows, want 2"
        raw = p.read_bytes()
        p.write_bytes(raw[:-8])                     # truncate the end marker
        rows = read_gz_tolerant(p)
        assert len(rows) >= 1, "truncated member should still yield rows"
    print("  tolerant reader: multi-member + truncation OK")


def main():
    print("== unit/smoke ==")
    test_classifier()
    test_tolerant_reader()
    print("== pre-registered engine & stats tests ==")
    for f in ("backtest/test_stats.py", "backtest/test_engine.py"):
        r = subprocess.run([sys.executable, str(ROOT / f)], cwd=ROOT)
        if r.returncode != 0:
            sys.exit(1)
    print("ALL TESTS PASS")


if __name__ == "__main__":
    main()
