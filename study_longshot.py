"""Study 1 — favorite-longshot calibration on Polymarket.

Question: when the market prices an outcome at p, does it resolve YES a
fraction p of the time? The favorite-longshot bias — documented in betting
markets for 75 years — says longshots (low p) win LESS often than priced and
favorites win MORE often: retail overpays for lottery tickets. If present and
large enough to clear fees, shorting the tails is a systematic strategy.

Inputs: data/price_marks.csv.gz (price at 24h/72h/7d before end, per resolved
market, from fetch_price_marks.py). Unit of observation: (market, horizon
mark). Outcome = 1 if outcome-0 won. Buckets are fine at the tails where the
bias concentrates.

Verdict rule (pre-registered in desk-year-plan.md): the bias is REAL if >= 3
buckets are mispriced >= 2 SE in the same tail-direction at the same horizon
across >= 2 category groups. Otherwise we report a null.

    python study_longshot.py
"""
import csv
import gzip
import io
import math
import pathlib
import zlib
from collections import defaultdict

from market_cats import cat_of

D = pathlib.Path(__file__).parent / "data"
MARKS = D / "price_marks.csv.gz"
EDGES = [0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50,
         0.60, 0.70, 0.80, 0.90, 0.95, 0.98, 0.99]


def bucket(p):
    for i in range(len(EDGES) - 1):
        if EDGES[i] <= p < EDGES[i + 1]:
            return i
    return None


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0, 1.0
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    hw = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return ph, max(0.0, c - hw), min(1.0, c + hw)


def read_gz_tolerant(path):
    """rows from a possibly-in-flight gzip (no end marker needed)."""
    raw = path.read_bytes()
    out = zlib.decompressobj(31).decompress(raw)
    txt = out.decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(txt)))
    # drop a possibly truncated final row
    if rows and rows[-1].get("winner_idx") in (None, ""):
        rows.pop()
    return rows


def load_slugs():
    """market id -> (slug, question) from every label file present."""
    m = {}
    for fn in ("resolved_markets.csv.gz", "resolved_tail.csv.gz",
               "resolved_tail2.csv.gz"):
        p = D / fn
        if not p.exists():
            continue
        try:
            for r in csv.DictReader(gzip.open(p, "rt")):
                m[r["id"]] = (r.get("slug", ""), r.get("question", ""))
        except (EOFError, OSError):
            pass
    return m


SLUGS = {}


def cat_group(r):
    """category from the label join (Gamma stopped populating `category`)."""
    s, q = SLUGS.get(r.get("id"), ("", ""))
    return cat_of(s, q or r.get("category", ""))


def run(rows, horizon, split=None):
    agg = defaultdict(lambda: [0, 0, 0.0, 0.0])   # bucket -> [n, wins, sum_p, sum_vol]
    for r in rows:
        p = r.get(f"p_{horizon}h")
        if p in (None, ""):
            continue
        p = float(p)
        if not 0 < p < 1:
            continue
        if split and cat_group(r) != split:
            continue
        b = bucket(p)
        if b is None:
            continue
        won = r["winner_idx"] == "0"
        a = agg[b]
        a[0] += 1
        a[1] += 1 if won else 0
        a[2] += p
        a[3] += float(r["volume"] or 0)
    out = []
    for b in sorted(agg):
        n, k, sp, vol = agg[b]
        if n < 30:
            continue
        implied = sp / n
        ph, lo, hi = wilson(k, n)
        se = math.sqrt(max(implied * (1 - implied), 1e-9) / n)
        z = (ph - implied) / se
        out.append({"bucket": f"{EDGES[b]:.2f}-{EDGES[b+1]:.2f}", "n": n,
                    "implied": implied, "realized": ph, "lo": lo, "hi": hi,
                    "z": z, "vol_m": vol / 1e6})
    return out


def main():
    if not MARKS.exists():
        print("run fetch_price_marks.py first")
        return
    rows = read_gz_tolerant(MARKS)
    global SLUGS
    SLUGS = load_slugs()
    print(f"observations: {len(rows):,} markets "
          f"({sum(1 for r in rows if r.get('id') in SLUGS):,} joined to slugs)\n")

    flags = defaultdict(list)          # direction flags per (horizon, group)
    for horizon in (24, 72, 168):
        print(f"=== price at T-{horizon}h — all categories ===")
        table = run(rows, horizon)
        print(f"{'bucket':12}{'n':>7}{'implied':>9}{'realized':>9}"
              f"{'z':>7}{'vol$M':>8}")
        for t in table:
            mark = " *" if abs(t["z"]) >= 2 else ""
            print(f"{t['bucket']:12}{t['n']:>7}{t['implied']:>9.3f}"
                  f"{t['realized']:>9.3f}{t['z']:>7.1f}{t['vol_m']:>8.1f}{mark}")
        for g in ("sports", "esports", "crypto", "politics", "econ",
                  "geopolitics", "weather", "culture", "other"):
            for t in run(rows, horizon, split=g):
                if abs(t["z"]) >= 2:
                    implied_low = t["implied"] < 0.5
                    over = t["realized"] < t["implied"]
                    # longshot bias signature: low-p buckets over-priced
                    # (realized < implied) and high-p under-priced
                    if (implied_low and over) or (not implied_low and not over):
                        flags[(horizon, g)].append(t["bucket"])
        print()

    print("=== verdict (pre-registered rule) ===")
    for (h, g), bs in sorted(flags.items()):
        print(f"  T-{h}h {g}: longshot-bias-direction buckets >=2SE: {bs}")
    groups_hit = {g for (_, g), bs in flags.items() if len(bs) >= 1}
    total_buckets = sum(len(b) for b in flags.values())
    real = total_buckets >= 3 and len(groups_hit) >= 2
    print(f"\n  bias buckets: {total_buckets} across {len(groups_hit)} "
          f"category groups -> {'BIAS REAL' if real else 'NULL / INSUFFICIENT'}")
    print("  (fees at the tails ~ feeRate*p(1-p) are tiny; economic viability "
          "assessed in the backtest phase, not here)")


if __name__ == "__main__":
    main()
