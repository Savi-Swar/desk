"""Paper 0 figures — every number in the paper regenerates from here.

Reads only committed ledgers (collected/), writes PNGs next to this script.

    python papers/paper0/make_figures.py
"""
import csv
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
C = ROOT / "collected"
HERE = pathlib.Path(__file__).parent
QUOTE_OFFSETS = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fills():
    """fee-bearing fills with eff_half present (post-fix schema)."""
    out = []
    with (C / "trade_markout.csv").open() as f:
        for r in csv.DictReader(f):
            fee, m, s, e = (num(r.get("fee")), num(r.get("mo_30s")),
                            num(r.get("size")), num(r.get("eff_half")))
            if fee in (None, 0) or m is None or not s or e is None:
                continue
            out.append((m, s, e))
    return out


def fig1():
    """shrinkage vs real fill count (from the validation run)."""
    shrink, real = 48578, 28
    with (C / "fill_validation.csv").open() as f:
        rows = list(csv.DictReader(f))
    if rows:                      # sum the recorded validation windows
        shrink = int(sum(float(r.get("shrink_fills") or 0) for r in rows))
        real = int(sum(float(r.get("trade_prints") or 0) for r in rows))
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["shrinkage 'fills'", "real prints"], [shrink, real],
           color=["#c0392b", "#2c3e50"])
    ax.set_yscale("log")
    ax.set_ylabel("count (log)")
    ax.set_title(f"Same window: {shrink:,} shrinkage fills vs {real} real prints "
                 f"({shrink/max(real,1):,.0f}x)")
    fig.tight_layout()
    fig.savefig(HERE / "fig1_fill_overcount.png", dpi=200)
    print(f"fig1: {shrink:,} vs {real} ({shrink/max(real,1):,.0f}x)")


def fig2(data):
    """capture vs adverse impact by spread bucket (per-share, size-capped $)."""
    cap = 100.0
    buckets = [("<1c", 0, .005), ("1-3c", .005, .015), (">3c", .015, 9)]
    # eff_half approximates half-spread at fill; bucket by |eff_half|
    labels, caps, imps = [], [], []
    for name, lo, hi in buckets:
        b = [(m, s, e) for m, s, e in data if lo <= abs(e) < hi]
        if not b:
            continue
        capture = sum(max(e, 0) * min(s, cap) for _, s, e in b)
        realized = sum(m * min(s, cap) for m, s, _ in b)
        impact = capture - realized
        labels.append(f"{name}\n(n={len(b)})")
        caps.append(capture)
        imps.append(impact)
    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(labels))
    ax.bar([i - .2 for i in x], caps, .4, label="spread capture (touch)",
           color="#2980b9")
    ax.bar([i + .2 for i in x], imps, .4, label="adverse impact",
           color="#c0392b")
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("$ (fills capped at 100 sh)")
    ax.set_title("Markout decomposition by half-spread at fill")
    ax.legend()
    fig.tight_layout()
    fig.savefig(HERE / "fig2_decomposition.png", dpi=200)
    print(f"fig2: buckets {labels}")


def fig3(data):
    """repricing curve: markout edge vs our quote offset from mid."""
    cap = 100.0
    touch = sum(m * min(s, cap) for m, s, _ in data)
    ys = []
    for d in QUOTE_OFFSETS:
        edge = sum((m - (e - min(d, max(e, 0)))) * min(s, cap)
                   for m, s, e in data)
        ys.append(edge)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([d * 100 for d in QUOTE_OFFSETS], ys, "o-", color="#2c3e50",
            label="edge at our quote")
    ax.axhline(touch, ls="--", color="#c0392b",
               label=f"as-measured at touch (+${touch:,.0f})")
    ax.axhline(0, lw=.5, color="gray")
    ax.set_xlabel("quote offset from mid (cents)")
    ax.set_ylabel("markout edge ($)")
    ax.set_title("The edge exists only at the touch you never rest at")
    ax.legend()
    fig.tight_layout()
    fig.savefig(HERE / "fig3_reprice.png", dpi=200)
    print(f"fig3: touch ${touch:,.0f} -> 1-tick ${ys[0]:,.0f}")


def main():
    data = fills()
    print(f"fills with eff_half: {len(data):,}")
    fig1()
    if data:
        fig2(data)
        fig3(data)


if __name__ == "__main__":
    main()
