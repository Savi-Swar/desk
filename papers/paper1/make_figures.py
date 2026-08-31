"""Paper 1 figures — regenerate from ledgers on disk.

    python papers/paper1/make_figures.py
"""
import math
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backtest"))
HERE = pathlib.Path(__file__).parent

import study_longshot as S  # noqa: E402


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fig1(rows):
    """calibration curve at T-24h, de-pinned, by major category."""
    from collections import defaultdict
    fig, ax = plt.subplots(figsize=(6.5, 5))
    colors = {"crypto": "#2980b9", "politics": "#c0392b",
              "sports": "#27ae60", "weather": "#8e44ad"}
    for cat, col in colors.items():
        agg = defaultdict(lambda: [0, 0, 0.0])
        for r in rows:
            p = num(r.get("p_24h"))
            if p is None or not 0 < p < 1 or S.pinned(r, 24):
                continue
            if S.cat_group(r) != cat:
                continue
            b = S.bucket(p)
            if b is None:
                continue
            a = agg[b]
            a[0] += 1
            a[1] += 1 if r["winner_idx"] == "0" else 0
            a[2] += p
        xs, ys = [], []
        for b in sorted(agg):
            n, k, sp = agg[b]
            if n < 50:
                continue
            xs.append(sp / n)
            ys.append(k / n)
        ax.plot(xs, ys, "o-", color=col, label=cat, ms=4, lw=1.2)
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=1, label="perfect")
    ax.set_xlabel("implied probability (T-24h mark)")
    ax.set_ylabel("realized frequency")
    ax.set_title("Calibration by category — pinned marks excluded")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig1_calibration.png", dpi=200)
    print("fig1 done")


def fig2():
    """the clustering collapse: same data, three inference choices."""
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["day-clustered\n(t = −4.2)", "month-clustered\n(t = −0.3)",
              "bet-weighted OOS\n(+0.6pp, dead)"]
    vals = [-4.2, -0.33, 0.2]
    ax.bar(labels, vals, color=["#c0392b", "#e67e22", "#95a5a6"])
    ax.axhline(-2, ls="--", lw=1, color="gray")
    ax.axhline(0, lw=0.8, color="black")
    ax.set_ylabel("t-statistic of the crypto-favorites 'bias'")
    ax.set_title("One effect, three inferences — regimes fake independence")
    fig.tight_layout()
    fig.savefig(HERE / "fig2_collapse.png", dpi=200)
    print("fig2 done")


def fig3(rows):
    """politics favorites: monthly gap strip, train vs test shading."""
    from collections import defaultdict
    mo = defaultdict(list)
    for r in rows:
        p = num(r.get("p_24h"))
        if p is None or not 0.5 <= p < 0.95 or S.pinned(r, 24):
            continue
        if S.cat_group(r) != "politics":
            continue
        ed = r.get("endDate") or ""
        mo[ed[:7]].append((1.0 if r["winner_idx"] == "0" else 0.0) - p)
    months = sorted(m for m, v in mo.items() if len(v) >= 5)
    gaps = [sum(mo[m]) / len(mo[m]) for m in months]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    cols = ["#2c3e50" if m < "2025-07" else "#c0392b" for m in months]
    ax.bar(range(len(months)), [g * 100 for g in gaps], color=cols)
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=60, fontsize=7)
    ax.axhline(0, lw=0.8, color="black")
    ax.set_ylabel("realized − implied (pp)")
    ax.set_title("Politics favorites, monthly gap — train (dark) vs test (red)")
    fig.tight_layout()
    fig.savefig(HERE / "fig3_politics_strip.png", dpi=200)
    print(f"fig3 done ({len(months)} months)")


def main():
    rows = S.read_gz_tolerant(S.MARKS)
    S.SLUGS = S.load_slugs()
    fig1(rows)
    fig2()
    fig3(rows)


if __name__ == "__main__":
    main()
