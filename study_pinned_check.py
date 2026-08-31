"""Study 1 robustness — pinned-price / early-effective-resolution check.

Concern (papers/paper1/OUTLINE.md, open item 1): Study 1's marks are taken at
T-24/72/168h before `endDate`, but many markets EFFECTIVELY resolve earlier
("by DATE" markets resolve when the event happens; sports games end days
before a stale endDate). A mark taken after effective resolution is a pinned
price (~0.99 / ~0.01) that mechanically "wins" — inflating extreme-bucket
calibration and possibly contaminating the month-clustered verdict cells.

Tell: `closedTime` (when trading actually closed, from the label files)
earlier than the mark time (endDate - h hours) means the T-h "price" is an
afterlife print.

This script:
  1. joins marks -> labels, reports closedTime coverage + parse stats;
  2. quantifies the fraction of marks that postdate the close, per horizon;
  3. reruns the month-clustered verdict cells and the T-24h all-category
     bucket table with those marks EXCLUDED, and prints before/after.

Writes data/pinned_price_check.md.  stdlib only.

    python3 study_pinned_check.py
"""
import math
import pathlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from market_cats import cat_of
from study_longshot import EDGES, bucket, read_gz_tolerant, wilson

D = pathlib.Path(__file__).parent / "data"
HORIZONS = (24, 72, 168)
GROUPS = ("sports", "esports", "crypto", "politics", "econ",
          "geopolitics", "weather", "culture", "other")


def parse_dt(s):
    """Defensive datetime parse -> aware UTC datetime, or None.

    Seen in the wild: endDate '2026-01-13T12:00:00Z';
    closedTime '2021-01-02 21:20:34+00' (optionally fractional seconds);
    empty strings; one junk numeric value.
    """
    s = (s or "").strip()
    if not s:
        return None
    t = s.replace("Z", "+00:00")
    # bare '+00' / '+0000' offsets -> '+00:00' for pre-3.11 fromisoformat
    if len(t) >= 3 and t[-3] in "+-" and t[-2:].isdigit():
        t = t + ":00"
    for cand in (t, t.replace(" ", "T")):
        try:
            dt = datetime.fromisoformat(cand)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def load_labels():
    """id -> {closedTime(dt|None), raw_ct, slug, question} from label files.

    Uses read_gz_tolerant: the label files are multi-member / truncated gzips
    (gzip.open alone raises EOFError partway through, silently dropping rows
    in study_longshot.load_slugs)."""
    lab = {}
    n_rows = n_ct_present = n_ct_parsed = 0
    for fn in ("resolved_markets.csv.gz", "resolved_tail.csv.gz",
               "resolved_tail2.csv.gz"):
        p = D / fn
        if not p.exists():
            continue
        for r in read_gz_tolerant(p):
            n_rows += 1
            raw = (r.get("closedTime") or "").strip()
            ct = parse_dt(raw)
            if raw:
                n_ct_present += 1
            if ct:
                n_ct_parsed += 1
            lab[r["id"]] = {"ct": ct, "slug": r.get("slug", ""),
                            "q": r.get("question", "")}
    stats = {"label_rows": n_rows, "unique_ids": len(lab),
             "ct_present": n_ct_present, "ct_parsed": n_ct_parsed}
    return lab, stats


def verdict_cells(rows, labels, exclude_pinned):
    """Mirror study_longshot.main()'s month-clustered verdict section.

    Per (horizon, category, side-of-0.5): cluster mark errors by endDate[:7],
    keep clusters with >=5 obs, require >=6 clusters, flag |t| >= 2.
    With exclude_pinned, drop marks whose closedTime <= endDate - h hours."""
    hits = []
    for horizon in HORIZONS:
        for g in GROUPS:
            for lo, hi, side in ((0.02, 0.5, "longshots"),
                                 (0.5, 0.98, "favorites")):
                cl = defaultdict(lambda: [0.0, 0])
                for r in rows:
                    p = r.get(f"p_{horizon}h")
                    if p in (None, ""):
                        continue
                    p = float(p)
                    if not lo <= p < hi:
                        continue
                    if r["_cat"] != g:
                        continue
                    if exclude_pinned and r["_pin"][horizon]:
                        continue
                    c = cl[(r.get("endDate") or "")[:7]]
                    c[0] += (1.0 if r["winner_idx"] == "0" else 0.0) - p
                    c[1] += 1
                d = [c[0] / c[1] for c in cl.values() if c[1] >= 5]
                if len(d) < 6:
                    continue
                m = sum(d) / len(d)
                se = ((sum((x - m) ** 2 for x in d) / (len(d) - 1)) ** 0.5
                      / math.sqrt(len(d)))
                tt = m / se if se else 0.0
                if abs(tt) >= 2:
                    hits.append({"h": horizon, "g": g, "side": side,
                                 "gap": m, "t": tt, "months": len(d)})
    return hits


def bucket_table(rows, horizon, exclude_pinned):
    """Mirror study_longshot.run() (all categories) at one horizon."""
    agg = defaultdict(lambda: [0, 0, 0.0])
    for r in rows:
        p = r.get(f"p_{horizon}h")
        if p in (None, ""):
            continue
        p = float(p)
        if not 0 < p < 1:
            continue
        if exclude_pinned and r["_pin"][horizon]:
            continue
        b = bucket(p)
        if b is None:
            continue
        a = agg[b]
        a[0] += 1
        a[1] += 1 if r["winner_idx"] == "0" else 0
        a[2] += p
    out = []
    for b in sorted(agg):
        n, k, sp = agg[b]
        if n < 30:
            continue
        implied = sp / n
        ph, _, _ = wilson(k, n)
        se = math.sqrt(max(implied * (1 - implied), 1e-9) / n)
        out.append({"bucket": f"{EDGES[b]:.2f}-{EDGES[b+1]:.2f}", "n": n,
                    "implied": implied, "realized": ph,
                    "z": (ph - implied) / se})
    return out


def main():
    rows = read_gz_tolerant(D / "price_marks.csv.gz")
    labels, lstats = load_labels()

    # ---- annotate each mark row: category, per-horizon pinned flag ----
    joined = ct_ok = 0
    pin_n = Counter()      # horizon -> pinned count
    mark_n = Counter()     # horizon -> valid-mark count
    gap_hist = Counter()   # bucketed close-before-end gap, T-24h marks
    pin_price_mass = Counter()   # among pinned T-24h marks: extreme price?
    for r in rows:
        lb = labels.get(r.get("id"))
        end = parse_dt(r.get("endDate"))
        ct = lb["ct"] if lb else None
        if lb:
            joined += 1
            r["_cat"] = cat_of(lb["slug"], lb["q"] or r.get("category", ""))
        else:
            r["_cat"] = cat_of("", r.get("category", ""))
        if ct:
            ct_ok += 1
        r["_pin"] = {}
        for h in HORIZONS:
            valid = r.get(f"p_{h}h") not in (None, "")
            if valid:
                mark_n[h] += 1
            pinned = (ct is not None and end is not None
                      and ct <= end - timedelta(hours=h))
            r["_pin"][h] = pinned
            if valid and pinned:
                pin_n[h] += 1
                if h == 24:
                    p = float(r["p_24h"])
                    if p >= 0.95 or p <= 0.05:
                        pin_price_mass["extreme(<=0.05|>=0.95)"] += 1
                    else:
                        pin_price_mass["mid"] += 1
        if ct and end:
            gh = (end - ct).total_seconds() / 3600
            for lab_, th in (("<24h", 24), ("24-72h", 72), ("72-168h", 168)):
                if gh <= th:
                    gap_hist[lab_ if gh > 0 else "close>=end"] += 1
                    break
            else:
                gap_hist[">168h"] += 1

    before_hits = verdict_cells(rows, labels, exclude_pinned=False)
    after_hits = verdict_cells(rows, labels, exclude_pinned=True)
    tab_before = bucket_table(rows, 24, exclude_pinned=False)
    tab_after = bucket_table(rows, 24, exclude_pinned=True)

    # ---- report ----
    L = []
    say = lambda s="": (print(s), L.append(s))
    say("# Pinned-price / early-resolution robustness check (Study 1)")
    say()
    say(f"_Generated by `study_pinned_check.py` on "
        f"{datetime.now(timezone.utc):%Y-%m-%d}._")
    say()
    say("## Coverage")
    say()
    say(f"- price-mark rows: **{len(rows):,}**; joined to a label row "
        f"(id match): **{joined:,}** ({joined/len(rows):.1%})")
    say(f"- label rows read (tolerant reader): {lstats['label_rows']:,} "
        f"({lstats['unique_ids']:,} unique ids); closedTime present "
        f"{lstats['ct_present']:,}, parsed {lstats['ct_parsed']:,} "
        f"({lstats['ct_parsed']/max(1,lstats['ct_present']):.2%} of present)")
    say(f"- marked markets with a usable closedTime: **{ct_ok:,}** "
        f"({ct_ok/len(rows):.1%}) — the rest cannot be flagged and are "
        f"KEPT in the 'after' runs")
    say()
    say("## How often is the mark an afterlife price?")
    say()
    say("A T-h mark is 'pinned' when closedTime <= endDate - h hours (trading "
        "had already closed when the mark was taken).")
    say()
    say("| horizon | valid marks | pinned (post-close) | share |")
    say("|---|---|---|---|")
    for h in HORIZONS:
        say(f"| T-{h}h | {mark_n[h]:,} | {pin_n[h]:,} | "
            f"{pin_n[h]/max(1,mark_n[h]):.1%} |")
    say()
    tot_g = sum(gap_hist.values())
    say("Close-vs-end gap distribution (markets with both timestamps): " +
        ", ".join(f"{k} {v/tot_g:.0%}" for k, v in sorted(
            gap_hist.items(), key=lambda kv: -kv[1])))
    te = pin_price_mass["extreme(<=0.05|>=0.95)"]
    tm = pin_price_mass["mid"]
    say(f"Sanity: among pinned T-24h marks, {te:,}/{te+tm:,} "
        f"({te/max(1,te+tm):.0%}) sit at extreme prices (<=0.05 or >=0.95) — "
        "consistent with the pinned-price mechanism.")
    say()
    say("## Verdict cells (month-clustered), before vs after exclusion")
    say()

    def cell_key(c):
        return (c["h"], c["g"], c["side"])
    after_keys = {cell_key(c) for c in after_hits}
    before_keys = {cell_key(c) for c in before_hits}
    say("| cell | before: gap (t, months) | after: gap (t, months) | survives? |")
    say("|---|---|---|---|")
    amap = {cell_key(c): c for c in after_hits}
    for c in before_hits:
        a = amap.get(cell_key(c))
        say(f"| T-{c['h']}h {c['g']} {c['side']} | "
            f"{c['gap']:+.3f} (t={c['t']:+.1f}, {c['months']}) | "
            + (f"{a['gap']:+.3f} (t={a['t']:+.1f}, {a['months']}) | YES |"
               if a else "below threshold | NO |"))
    for c in after_hits:
        if cell_key(c) not in before_keys:
            say(f"| T-{c['h']}h {c['g']} {c['side']} | below threshold | "
                f"{c['gap']:+.3f} (t={c['t']:+.1f}, {c['months']}) | NEW |")
    if not before_hits and not after_hits:
        say("| (no cell reaches |t|>=2 in either run) | — | — | — |")
    say()
    bg = {c["g"] for c in before_hits}
    ag = {c["g"] for c in after_hits}
    say(f"Overall verdict rule (>=2 cells across >=2 groups): before = "
        f"**{'BIAS CANDIDATE' if len(before_hits) >= 2 and len(bg) >= 2 else 'NULL'}**"
        f" ({len(before_hits)} cells, {len(bg)} groups); after = "
        f"**{'BIAS CANDIDATE' if len(after_hits) >= 2 and len(ag) >= 2 else 'NULL'}**"
        f" ({len(after_hits)} cells, {len(ag)} groups).")
    say()
    say("## Headline calibration table, T-24h, all categories")
    say()
    say("| bucket | n before | realized-implied before (z) | n after | "
        "realized-implied after (z) |")
    say("|---|---|---|---|---|")
    amap2 = {t["bucket"]: t for t in tab_after}
    for t in tab_before:
        a = amap2.get(t["bucket"])
        say(f"| {t['bucket']} | {t['n']:,} | "
            f"{t['realized']-t['implied']:+.3f} (z={t['z']:+.1f}) | "
            + (f"{a['n']:,} | {a['realized']-a['implied']:+.3f} "
               f"(z={a['z']:+.1f}) |" if a else "n<30 | — |"))
    say()

    # ---- automated verdict paragraph ----
    lost = before_keys - after_keys
    ext = [b for b in ("0.95-0.98", "0.98-0.99", "0.01-0.02", "0.02-0.05")
           if b in amap2]
    say("## Verdict")
    say()
    pin24 = pin_n[24] / max(1, mark_n[24])
    say(f"- **Contamination is real but bounded**: {pin24:.1%} of T-24h marks "
        f"(per-horizon shares in the table above) are post-close afterlife "
        f"prices, {te/max(1,te+tm):.0%} of them at pinned extremes.")
    if lost:
        say(f"- **{len(lost)} of {len(before_hits)} verdict cells do NOT "
            f"survive** the exclusion: " +
            "; ".join(f"T-{h}h {g} {s}" for h, g, s in sorted(lost)) + ".")
    else:
        say(f"- **All {len(before_hits)} verdict cells survive** the "
            "exclusion (and the overall verdict is unchanged).")
    new = after_keys - before_keys
    if new:
        say(f"- **{len(new)} NEW cells emerge** after exclusion — pinned "
            "prices are mechanically perfectly calibrated, so they were "
            "DILUTING real gaps toward zero, not just inflating them: " +
            "; ".join(f"T-{h}h {g} {s}" for h, g, s in sorted(new)) + ".")
    say("- Extreme-bucket calibration shifts are shown in the T-24h table "
        "above; pinned marks concentrate exactly there, so any material "
        "change in 0.95-0.99 / 0.01-0.05 is attributable to this artifact.")
    say()
    say("## Recommended permanent filter")
    say()
    say("Adopt in `study_longshot.py`: join marks to labels, parse "
        "`closedTime` (formats: `YYYY-MM-DD HH:MM:SS[.ffffff]+00`, may be "
        "empty), and **drop a T-h mark when closedTime <= endDate - h hours**;"
        " keep marks with missing/unparseable closedTime (" +
        f"{len(rows)-ct_ok:,} markets, {1-ct_ok/len(rows):.1%}) but report "
        "the count. Optionally also cluster verdict cells by closedTime "
        "month rather than endDate month for early-resolvers.")

    out = D / "pinned_price_check.md"
    out.write_text("\n".join(L) + "\n")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
