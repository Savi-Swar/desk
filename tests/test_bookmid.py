"""Pin the C++ bookmid reconstructor against the Python hot path.

Builds tools/bookmid, generates a synthetic recording in the recorder's exact
envelope format (escaped inner JSON, snapshots + diffs, single- and
multi-event messages), runs both implementations, and requires identical
(t, asset, bid, ask) sequences. Also times both on a larger file.

    python3 tests/test_bookmid.py
"""
import gzip
import json
import pathlib
import random
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TOOL = ROOT / "tools" / "bookmid"


def make_fixture(path, n_msgs=200, seed=7):
    rng = random.Random(seed)
    assets = [f"asset{i}" for i in range(4)]
    t = 1_700_000_000.0
    with gzip.open(path, "wt") as f:
        f.write(json.dumps({"t": t, "meta": {"fixture": True}}) + "\n")
        for a in assets:
            snap = {"event_type": "book", "asset_id": a,
                    "bids": [{"price": "0.40", "size": "10"},
                             {"price": "0.45", "size": "5"}],
                    "asks": [{"price": "0.60", "size": "9"},
                             {"price": "0.55", "size": "4"}]}
            t += 0.5
            f.write(json.dumps({"t": round(t, 3),
                                "m": json.dumps(snap)}) + "\n")
        for _ in range(n_msgs):
            t += rng.random()
            evs = []
            for _ in range(rng.choice([1, 1, 1, 2])):
                a = rng.choice(assets)
                bb = round(0.30 + 0.3 * rng.random(), 3)
                evs.append({"event_type": "price_change", "price_changes": [
                    {"asset_id": a, "best_bid": str(bb),
                     "best_ask": str(round(bb + 0.02 + 0.1 * rng.random(), 3))}]})
            m = evs[0] if len(evs) == 1 else evs
            f.write(json.dumps({"t": round(t, 3),
                                "m": json.dumps(m)}) + "\n")


def python_mids(path):
    from trade_markout import build_mids
    out = []
    mids = build_mids([str(path)])
    for a, series in sorted(mids.items()):
        for t, mid in series:
            out.append((round(float(t), 3), a, round(mid, 6)))
    return sorted(out)


def cpp_mids(binary, path):
    r = subprocess.run([str(binary), str(path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = []
    for line in r.stdout.splitlines()[1:]:
        t, a, bid, ask = line.split(",")
        out.append((round(float(t), 3), a,
                    round((float(bid) + float(ask)) / 2, 6)))
    return sorted(out)


def main():
    binary = TOOL / "bookmid"
    subprocess.run(["g++", "-O2", "-std=c++17", "-o", str(binary),
                    str(TOOL / "bookmid.cpp"), "-lz"], check=True)
    with tempfile.TemporaryDirectory() as td:
        fx = pathlib.Path(td) / "book.jsonl.gz"
        make_fixture(fx)
        py = python_mids(fx)
        cc = cpp_mids(binary, fx)
        assert len(py) > 100, f"fixture too small: {len(py)}"
        assert py == cc, (f"MISMATCH: python {len(py)} rows vs c++ {len(cc)};"
                          f" first diff: "
                          f"{next((a, b) for a, b in zip(py, cc) if a != b)}")
        print(f"  bookmid parity: {len(py)} top-of-book updates identical")

        big = pathlib.Path(td) / "big.jsonl.gz"
        make_fixture(big, n_msgs=60_000, seed=11)
        t0 = time.perf_counter()
        python_mids(big)
        t_py = time.perf_counter() - t0
        t0 = time.perf_counter()
        subprocess.run([str(binary), str(big)], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
        t_cc = time.perf_counter() - t0
        n_lines = 60_000
        print(f"  bookmid bench (60k msgs): python {t_py:.2f}s, "
              f"c++ binary {t_cc:.2f}s  ({t_py / t_cc:.1f}x, "
              f"{n_lines / t_cc / 1e3:.0f}k msg/s)")


if __name__ == "__main__":
    main()
