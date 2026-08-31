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

Verdict rule (pre-registered in desk-year-plan.md, TIGHTENED 2026-08-30 after
the November-2025 lesson): naive per-bucket z-scores treat markets sharing an
underlying and a regime as independent — day-clustered inference put the
crypto-favorites "bias" at t=-4.2, but clustering by (category, month)
collapsed it to t=-0.3: the whole effect was the Nov-2025 crash month. So the
verdict now requires, per (horizon, category, side-of-0.5): |t| >= 2 with
month-level clusters, >= 6 cluster-months, in >= 2 category groups. Buckets
are still reported descriptively.

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
    """rows from a possibly-in-flight gzip. Handles MULTI-MEMBER files (append
    mode writes a new gzip member per run) and a truncated final member."""
    raw = path.read_bytes()
    parts = []
    while raw:
        o = zlib.decompressobj(31)
        try:
            parts.append(o.decompress(raw))
        except zlib.error:
            break
        if not o.unused_data or o.unused_data == raw:
            break
        raw = o.unused_data
    txt = b"".join(parts).decode("utf-8", "replace")
    # appended members repeat the header line; drop embedded ones
    lines = txt.splitlines()
    if lines:
        head = lines[0]
        lines = [head] + [l for l in lines[1:] if l != head]
        txt = "\n".join(lines)
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

    print("=== naive per-bucket flags (descriptive only — see docstring) ===")
    for (h, g), bs in sorted(flags.items()):
        print(f"  T-{h}h {g}: {bs}")

    print("\n=== verdict: month-clustered calibration gaps ===")
    hits = []
    for horizon in (24, 72, 168):
        for g in ("sports", "esports", "crypto", "politics", "econ",
                  "geopolitics", "weather", "culture", "other"):
            for lo, hi, side in ((0.02, 0.5, "longshots"), (0.5, 0.98, "favorites")):
                cl = defaultdict(lambda: [0.0, 0])
                for r in rows:
                    p = r.get(f"p_{horizon}h")
                    if p in (None, ""):
                        continue
                    p = float(p)
                    if not lo <= p < hi:
                        continue
                    if cat_group(r) != g:
                        continue
                    mo = (r.get("endDate") or "")[:7]
                    c = cl[mo]
                    c[0] += (1.0 if r["winner_idx"] == "0" else 0.0) - p
                    c[1] += 1
                d = [c[0] / c[1] for c in cl.values() if c[1] >= 5]
                if len(d) < 6:
                    continue
                m = sum(d) / len(d)
                se = (sum((x - m) ** 2 for x in d) / (len(d) - 1)) ** 0.5 / math.sqrt(len(d))
                tt = m / se if se else 0.0
                if abs(tt) >= 2:
                    hits.append((horizon, g, side, m, tt, len(d)))
                    print(f"  T-{horizon}h {g} {side}: gap {m:+.3f} "
                          f"t={tt:+.1f} ({len(d)} months)")
    groups_hit = {g for _, g, *_ in hits}
    real = len(hits) >= 2 and len(groups_hit) >= 2
    print(f"\n  {len(hits)} robust cells across {len(groups_hit)} groups -> "
          f"{'BIAS CANDIDATE (verify OOS)' if real else 'NULL — no calibration bias survives regime clustering'}")
    print("  (fees at the tails ~ feeRate*p(1-p) are tiny; economic viability "
          "assessed in the backtest phase, not here)")


if __name__ == "__main__":
    main()
