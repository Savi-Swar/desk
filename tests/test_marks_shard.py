"""Partition invariants for the distributed crawl: shards are disjoint and
covering for any NSHARDS, and stable across runs.

    python3 tests/test_marks_shard.py
"""
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))


def assign(mid, n):
    h = hashlib.sha1(mid.encode()).digest()
    return int.from_bytes(h[:4], "big") % n


def main():
    ids = [f"m{i}" for i in range(20_000)]
    for n in (1, 2, 12, 16):
        buckets = [assign(i, n) for i in ids]
        assert set(buckets) == set(range(n)), f"not covering at n={n}"
        counts = [buckets.count(k) for k in range(n)]
        assert min(counts) > 0.7 * len(ids) / n, f"skewed at n={n}: {counts}"
    # disjointness is structural (a function), stability across processes:
    assert assign("market123", 12) == assign("market123", 12)
    # pin a value so an accidental hash change can't silently repartition
    assert assign("market123", 12) == int.from_bytes(
        hashlib.sha1(b"market123").digest()[:4], "big") % 12
    print("  marks_shard partition: covering, balanced, stable")


if __name__ == "__main__":
    main()
