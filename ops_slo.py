"""Measured platform SLOs from the health ledger — ops language for a system
that has actually operated.

Freshness SLO per collector: the gap between consecutive successful runs
(includes every real incident — the cron death, the auth lockouts, laptop
sleeps — nothing excluded). Reliability: success rate per script over its
whole life. Prints the table and, with --arch, the markdown block that
ARCHITECTURE.md embeds.

    python ops_slo.py
"""
import json
import pathlib
import sys
from collections import defaultdict

H = pathlib.Path(__file__).parent / "collected" / "health.jsonl"
KEY = ("firehose_recorder.py", "book_recorder.py", "collect_daily.py",
       "single_cond_watch.py", "weather_collect.py")


def pct(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    i = min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1)))
    return sorted_vals[i]


def main():
    runs = defaultdict(list)
    for line in H.open():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        runs[d.get("script")].append((d.get("ts", 0), d.get("rc", 1)))
    rows = []
    for script, rs in sorted(runs.items()):
        rs.sort()
        ok = [t for t, rc in rs if rc == 0]
        gaps = sorted(b - a for a, b in zip(ok, ok[1:]) if b - a > 0)
        if len(rs) < 10:
            continue
        span_d = (rs[-1][0] - rs[0][0]) / 86400
        rows.append({
            "script": script.replace(".py", ""),
            "runs": len(rs),
            "ok": sum(1 for _, rc in rs if rc == 0) / len(rs),
            "span_d": span_d,
            "p50_m": pct(gaps, 0.50) / 60,
            "p99_m": pct(gaps, 0.99) / 60,
            "worst_h": (gaps[-1] / 3600) if gaps else 0,
        })
    print(f"{'collector':22}{'runs':>6}{'ok%':>7}{'days':>6}"
          f"{'p50 gap':>9}{'p99 gap':>9}{'worst':>8}")
    for r in rows:
        print(f"{r['script']:22}{r['runs']:>6}{r['ok']*100:>6.1f}%"
              f"{r['span_d']:>6.0f}{r['p50_m']:>7.0f}m {r['p99_m']:>7.0f}m "
              f"{r['worst_h']:>6.1f}h")
    print("\n(gaps between successful runs; every incident included — cron "
          "death, auth lockouts, laptop sleep. Honest ops, not lab ops.)")
    print("CAVEAT: success rates here are survivorship-biased — a run that "
          "crashed hard enough to fail the workflow never committed its "
          "health row (e.g. the maker_sim2 crash days are absent). Failure "
          "counting lives in the alarm workflow's issue history, not here.")


if __name__ == "__main__":
    main()
