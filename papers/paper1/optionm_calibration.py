"""Paper 1 yardstick — are SPX option-implied digital probabilities calibrated?

Runs the SAME calibration test we ran on Polymarket (study_longshot.py) on the
institutional benchmark: risk-neutral P(S_T > K) = N(d2) extracted from the
OptionMetrics standardized 30-day volatility surface for SPX (secid 108105),
observed weekly (Wednesdays), scored against the realized index level 30
calendar days later.

Known wedge, stated up front: option prices give RISK-NEUTRAL probabilities;
realized frequencies are PHYSICAL. The variance/equity risk premium implies a
systematic gap even for a perfectly functioning market (e.g. low-prob
downside states are priced "too high" vs realized frequency). The point of
this script is the SIZE and SHAPE of that deviation next to Polymarket's, not
a fair race.

Method (each step documented in data/optionm_calibration.md):
  1. optionm.vsurfd{yyyy}: secid=108105, days=30, cp_flag='C', deltas 20-80.
     The surface supplies impl_volatility AND impl_strike, so no delta
     inversion is needed.
  2. r: optionm.zerocd zero curve, nearest-to-30d tenor per date (cont. comp).
     q: optionm.idxdvd SPX dividend yield per date.
     S: optionm.secprd{yyyy} SPX close.
  3. P(S_T > K) = N(d2), d2 = [ln(S/K) + (r - q - s^2/2)T] / (s sqrt(T)),
     T = 30/365, N() via math.erf (venv has no scipy).
  4. Outcome = 1 if SPX close on the trading day nearest obs_date + 30cd
     (within +/-3cd) exceeds K.
  5. Buckets = the exact EDGES list from study_longshot.py; Wilson 95% CIs;
     naive z with se = sqrt(implied(1-implied)/n) — same formulas.
  6. Verdict cells mirror the study: mean gap (realized - implied) clustered
     by EXPIRY MONTH (weekly-sampled overlapping 30d outcomes are heavily
     dependent), for implied in [0.02, 0.5) and [0.5, 0.98).

WRDS access: username parsed from ~/.pgpass field 4 (password never read).
Raw pulls are cached in papers/paper1/data/optionm_raw.csv.gz so reruns are
offline. On WRDS OperationalError (parallel-job lockout): sleep 600s, retry,
up to 6 attempts, ONE connection, few large queries, closed promptly.

    /Users/swarup44891/lab/wrds-env/bin/python optionm_calibration.py
"""
import datetime as dt
import gzip
import math
import pathlib
import sys
import time
from collections import defaultdict

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
CACHE = DATA / "optionm_raw.csv.gz"
AUX_CACHE = DATA / "optionm_aux.csv.gz"
MD_OUT = DATA / "optionm_calibration.md"

SECID = 108105                      # SPX in OptionMetrics
START, END = "2018-01-01", "2025-06-30"
YEARS = range(2018, 2026)
TENOR_DAYS = 30
T = TENOR_DAYS / 365.0

# EDGES copied verbatim from study_longshot.py (the Polymarket study)
EDGES = [0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50,
         0.60, 0.70, 0.80, 0.90, 0.95, 0.98, 0.99]


def N(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


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


# ---------------------------------------------------------------- WRDS pull

def wrds_username():
    """4th colon-field of ~/.pgpass line 1. The password field is never read."""
    line = (pathlib.Path.home() / ".pgpass").read_text().splitlines()[0]
    return line.split(":")[3]


def connect_with_retry():
    """Probe with psycopg2 first (real OperationalError, no interactive
    fallback), retrying through WRDS's temporary connection-lockout, which
    presents as 'PAM authentication failed'. Then hand off to wrds.Connection
    (probe is closed first — one live connection at a time)."""
    import psycopg2
    import wrds
    user = wrds_username()
    for attempt in range(1, 7):
        try:
            c = psycopg2.connect(host="wrds-pgdata.wharton.upenn.edu",
                                 port=9737, dbname="wrds", user=user,
                                 sslmode="require")
            c.close()
            break
        except psycopg2.OperationalError as e:
            print(f"[wrds] probe attempt {attempt}/6 failed: "
                  f"{str(e).strip()[:120]}; sleeping 600s", flush=True)
            if attempt == 6:
                raise
            time.sleep(600)
    return wrds.Connection(wrds_username=user)


def pull():
    """One connection, few large queries, cached to CSVs."""
    db = connect_with_retry()
    try:
        tables = set(db.list_tables(library="optionm"))
        print(f"[wrds] optionm tables: {len(tables)}", flush=True)

        # 1) standardized 30d surface, calls, deltas 20-80
        surf = []
        for y in YEARS:
            t = f"vsurfd{y}"
            if t not in tables:
                print(f"[wrds] {t} missing — skipped", flush=True)
                continue
            q = (f"select date, days, delta, impl_volatility, impl_strike, "
                 f"cp_flag from optionm.{t} "
                 f"where secid = {SECID} and days = {TENOR_DAYS} "
                 f"and cp_flag = 'C' and delta between 20 and 80 "
                 f"and date between '{START}' and '{END}'")
            df = db.raw_sql(q)
            print(f"[wrds] {t}: {len(df):,} rows", flush=True)
            surf.append(df)
        surf = pd.concat(surf, ignore_index=True)

        # 2) SPX daily closes (need beyond END for expiries)
        px = []
        for y in list(YEARS) + [2026]:
            t = f"secprd{y}"
            if t not in tables:
                print(f"[wrds] {t} missing — skipped", flush=True)
                continue
            df = db.raw_sql(f"select date, close from optionm.{t} "
                            f"where secid = {SECID}")
            px.append(df)
        if not px and "secprd" in tables:
            px = [db.raw_sql(f"select date, close from optionm.secprd "
                             f"where secid = {SECID} and date >= '{START}'")]
        px = pd.concat(px, ignore_index=True)
        print(f"[wrds] secprd: {len(px):,} rows", flush=True)

        # 3) zero curve, tenors bracketing 30d
        zc = db.raw_sql(f"select date, days, rate from optionm.zerocd "
                        f"where date between '{START}' and '{END}' "
                        f"and days between 5 and 120")
        print(f"[wrds] zerocd: {len(zc):,} rows", flush=True)

        # 4) SPX dividend yield
        dv = db.raw_sql(f"select * from optionm.idxdvd "
                        f"where secid = {SECID} "
                        f"and date between '{START}' and '{END}' limit 500000")
        print(f"[wrds] idxdvd: {len(dv):,} rows, cols={list(dv.columns)}",
              flush=True)
    finally:
        db.close()

    surf.to_csv(CACHE, index=False, compression="gzip")
    aux = {"px": px, "zc": zc, "dv": dv}
    with gzip.open(AUX_CACHE, "wt") as f:
        for name, df in aux.items():
            f.write(f"### {name}\n")
            df.to_csv(f, index=False)
    return surf, px, zc, dv


def load_cached():
    surf = pd.read_csv(CACHE)
    blocks = {}
    with gzip.open(AUX_CACHE, "rt") as f:
        name, lines = None, []
        for line in f:
            if line.startswith("### "):
                if name:
                    blocks[name] = lines
                name, lines = line[4:].strip(), []
            else:
                lines.append(line)
        if name:
            blocks[name] = lines
    import io
    aux = {k: pd.read_csv(io.StringIO("".join(v))) for k, v in blocks.items()}
    return surf, aux["px"], aux["zc"], aux["dv"]


# ------------------------------------------------------------------ compute

def build_panel(surf, px, zc, dv):
    for df in (surf, px, zc, dv):
        df["date"] = pd.to_datetime(df["date"])

    # Wednesdays only (weekly sampling, per the Polymarket-marks analogy)
    surf = surf[surf["date"].dt.dayofweek == 2].copy()

    # spot on obs date
    px = px.sort_values("date").drop_duplicates("date")
    spot = px.set_index("date")["close"]

    # r: nearest-to-30d zero tenor per date (annualized %, cont. comp.)
    zc = zc.dropna(subset=["rate"])
    zc["gap"] = (zc["days"] - TENOR_DAYS).abs()
    r30 = (zc.sort_values(["date", "gap"]).groupby("date").first()["rate"]
           / 100.0)

    # q: idxdvd — column name for the yield is 'rate' (annualized %)
    dvcol = "rate" if "rate" in dv.columns else [
        c for c in dv.columns if c not in ("secid", "date", "expiration")][0]
    if "expiration" in dv.columns:      # term structure: nearest ~30d expiry
        dv["gap"] = (pd.to_datetime(dv["expiration"]) - dv["date"]
                     ).dt.days.sub(TENOR_DAYS).abs()
        q30 = (dv.sort_values(["date", "gap"]).groupby("date").first()[dvcol]
               / 100.0)
    else:
        q30 = dv.sort_values("date").drop_duplicates("date").set_index(
            "date")[dvcol] / 100.0

    # realized: SPX close on nearest trading day to obs+30cd, within +/-3cd
    trading_days = spot.index.to_numpy()

    def s_at_expiry(target):
        idx = trading_days.searchsorted(pd.Timestamp(target).to_numpy())
        best, bgap = None, None
        for j in (idx - 1, idx):
            if 0 <= j < len(trading_days):
                g = abs((pd.Timestamp(trading_days[j]) - target).days)
                if bgap is None or g < bgap:
                    best, bgap = trading_days[j], g
        if best is None or bgap > 3:
            return None, None
        return spot.loc[pd.Timestamp(best)], pd.Timestamp(best)

    rows, dropped = [], defaultdict(int)
    for date, grp in surf.groupby("date"):
        if date not in spot.index:
            dropped["no_spot"] += len(grp)
            continue
        S = spot.loc[date]
        r = r30.get(date)
        if r is None or pd.isna(r):
            dropped["no_rate"] += len(grp)
            continue
        q = q30.get(date)
        if q is None or pd.isna(q):
            q = 0.0
            dropped["q_defaulted_rows"] += len(grp)
        target = date + pd.Timedelta(days=TENOR_DAYS)
        ST, expiry = s_at_expiry(target)
        if ST is None:
            dropped["no_expiry_px"] += len(grp)
            continue
        for _, rr in grp.iterrows():
            K, sig = rr["impl_strike"], rr["impl_volatility"]
            if not (K > 0 and sig > 0):
                dropped["bad_surface"] += 1
                continue
            d2 = ((math.log(S / K) + (r - q - 0.5 * sig * sig) * T)
                  / (sig * math.sqrt(T)))
            p = N(d2)
            rows.append({"date": date, "expiry": expiry,
                         "exp_month": expiry.strftime("%Y-%m"),
                         "delta": rr["delta"], "K": K, "iv": sig,
                         "S": S, "ST": ST, "r": r, "q": q,
                         "implied": p, "won": 1 if ST > K else 0})
    panel = pd.DataFrame(rows)
    return panel, dict(dropped)


def bucket_table(panel):
    agg = defaultdict(lambda: [0, 0, 0.0])
    for _, r in panel.iterrows():
        b = bucket(r["implied"])
        if b is None:
            continue
        a = agg[b]
        a[0] += 1
        a[1] += r["won"]
        a[2] += r["implied"]
    out = []
    for b in sorted(agg):
        n, k, sp = agg[b]
        if n < 30:                       # same reporting floor as the study
            continue
        implied = sp / n
        ph, lo, hi = wilson(k, n)
        se = math.sqrt(max(implied * (1 - implied), 1e-9) / n)
        out.append({"bucket": f"{EDGES[b]:.2f}-{EDGES[b+1]:.2f}", "n": n,
                    "implied": implied, "realized": ph, "lo": lo, "hi": hi,
                    "z": (ph - implied) / se})
    return out


def clustered(panel, lo, hi):
    """Month-clustered mean gap (realized - implied), like the study verdict."""
    sub = panel[(panel["implied"] >= lo) & (panel["implied"] < hi)]
    g = sub.assign(g=sub["won"] - sub["implied"]).groupby("exp_month")["g"]
    means = g.mean()[g.size() >= 5]      # cells need >= 5 obs, per study
    d = means.tolist()
    if len(d) < 6:
        return None
    m = sum(d) / len(d)
    se = ((sum((x - m) ** 2 for x in d) / (len(d) - 1)) ** 0.5
          / math.sqrt(len(d)))
    return {"gap": m, "t": m / se if se else 0.0, "months": len(d),
            "n": len(sub)}


# ------------------------------------------------------------------- report

def main():
    if CACHE.exists() and AUX_CACHE.exists() and "--refresh" not in sys.argv:
        print("[cache] using cached WRDS pulls (pass --refresh to re-query)")
        surf, px, zc, dv = load_cached()
    else:
        surf, px, zc, dv = pull()

    panel, dropped = build_panel(surf, px, zc, dv)
    print(f"panel: {len(panel):,} obs, "
          f"{panel['date'].nunique()} Wednesdays, "
          f"{panel['date'].min().date()} .. {panel['date'].max().date()}; "
          f"dropped: {dropped}")

    tbl = bucket_table(panel)
    print(f"\n{'bucket':12}{'n':>6}{'implied':>9}{'realized':>9}"
          f"{'lo':>7}{'hi':>7}{'z':>7}")
    for t in tbl:
        mark = " *" if abs(t["z"]) >= 2 else ""
        print(f"{t['bucket']:12}{t['n']:>6}{t['implied']:>9.3f}"
              f"{t['realized']:>9.3f}{t['lo']:>7.3f}{t['hi']:>7.3f}"
              f"{t['z']:>7.1f}{mark}")

    verdict = {}
    for lo, hi, side in ((0.02, 0.5, "longshots [0.02,0.50)"),
                         (0.5, 0.98, "favorites [0.50,0.98)")):
        v = clustered(panel, lo, hi)
        verdict[side] = v
        if v:
            print(f"\n{side}: month-clustered gap {v['gap']:+.3f} "
                  f"t={v['t']:+.1f} ({v['months']} expiry-months, "
                  f"n={v['n']:,})")

    write_md(panel, dropped, tbl, verdict)
    print(f"\nwrote {MD_OUT}")


def write_md(panel, dropped, tbl, verdict):
    qdef = dropped.get("q_defaulted_rows", 0)
    lines = [
        "# SPX option-implied digital probabilities — calibration yardstick",
        "",
        f"*Generated by `optionm_calibration.py` on "
        f"{dt.date.today().isoformat()}. Rerunnable; raw WRDS pulls cached "
        "in `optionm_raw.csv.gz` / `optionm_aux.csv.gz` (pass `--refresh` "
        "to re-query).*",
        "",
        "## What this is",
        "",
        "The institutional benchmark for Paper 1: the SAME calibration test "
        "run on Polymarket in `study_longshot.py` — bucket implied "
        "probabilities on the study's exact EDGES, compare to realized "
        "frequencies with Wilson intervals and naive z, then a "
        "month-clustered verdict — applied to SPX index options.",
        "",
        "**The honest wedge:** option prices give *risk-neutral* "
        "probabilities; realized frequencies are *physical*. The equity and "
        "variance risk premia guarantee a systematic gap even in a "
        "frictionless, perfectly-functioning market: downside states carry "
        "high state prices, so low-strike (high-P) digitals should look "
        "\"underpriced\" vs realized frequency and OTM-put-region "
        "probabilities \"overpriced\". This is NOT a fair race against "
        "Polymarket — the yardstick is the *size and shape* of the "
        "deviation, not its existence.",
        "",
        "## Data and method",
        "",
        f"- **Universe:** OptionMetrics standardized volatility surface "
        f"(`optionm.vsurfd2018..2025`), SPX `secid={SECID}`, tenor "
        f"`days=30`, calls, deltas 20–80. The surface supplies both "
        "`impl_volatility` and `impl_strike`, so no delta-to-strike "
        "inversion was needed.",
        f"- **Sampling:** Wednesdays, {START} to {END}. "
        f"{panel['date'].nunique()} observation dates, "
        f"{len(panel):,} (date, strike) points.",
        "- **Implied probability:** P(S_T > K) = N(d2), "
        "d2 = [ln(S/K) + (r − q − σ²/2)T] / (σ√T), T = 30/365 "
        "(calendar-day tenor, matching the surface's calendar-day `days`). "
        "N(·) via `math.erf` (venv has no scipy).",
        "- **r:** `optionm.zerocd` zero rate at the tenor nearest 30 "
        "calendar days per date (continuously compounded; /100).",
        "- **q:** `optionm.idxdvd` SPX annualized dividend yield per date "
        "(nearest ~30d expiration when the table carries a term structure)"
        + (f"; defaulted to 0 on {qdef} rows with no match." if qdef
           else "; matched on every retained row."),
        "- **Spot and outcome:** SPX close from `optionm.secprd{yyyy}`. "
        "Outcome = 1 if the close on the trading day nearest obs+30cd "
        "(within ±3cd, else dropped) exceeds K.",
        f"- **Drops:** {dropped if dropped else 'none'}.",
        "- **Stats:** buckets are the verbatim `EDGES` list from "
        "`study_longshot.py`; n ≥ 30 reporting floor; Wilson 95% CI; naive "
        "z = (realized − implied)/√(implied(1−implied)/n) — all identical "
        "formulas to the study.",
        "- **Clustering:** weekly-sampled 30-day outcomes overlap ~4×, and "
        "every same-date strike shares one index path — naive z is badly "
        "anticonservative here. Verdict cells cluster by EXPIRY MONTH "
        "(mean per-month gap, months with ≥ 5 obs, t across months), "
        "mirroring the study's month-clustered verdict.",
        "",
        "## Calibration table (naive, descriptive)",
        "",
        "| bucket | n | implied | realized | Wilson 95% | naive z |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for t in tbl:
        lines.append(
            f"| {t['bucket']} | {t['n']} | {t['implied']:.3f} | "
            f"{t['realized']:.3f} | [{t['lo']:.3f}, {t['hi']:.3f}] | "
            f"{t['z']:+.1f}{' *' if abs(t['z']) >= 2 else ''} |")
    lines += [
        "",
        "`*` = |z| ≥ 2 naive — descriptive only; see clustering note.",
        "",
        "## Verdict cells (month-clustered, mirrors study_longshot.py)",
        "",
        "| side | n | expiry-months | mean gap (real − impl) | t |",
        "|---|---:|---:|---:|---:|",
    ]
    for side, v in verdict.items():
        if v:
            lines.append(f"| {side} | {v['n']:,} | {v['months']} | "
                         f"{v['gap']:+.3f} | {v['t']:+.1f} |")
        else:
            lines.append(f"| {side} | — | <6 months | — | — |")
    lines += [
        "",
        "## Reading it next to Polymarket",
        "",
        "- Any significant gap here is the *risk-premium wedge*, not market "
        "failure: SPX digitals are the most liquid, most arbitraged "
        "probability quotes in existence. Their deviation from realized "
        "frequency is the floor a risk-neutral quote pays for insurance "
        "value.",
        "- The comparison for the paper: Polymarket's month-clustered gaps "
        "in the same [0.02,0.5) / [0.5,0.98) cells vs these. If the crowd's "
        "gaps are of the same order as the institutional risk-premium wedge "
        "— on outcomes with far less systematic-risk exposure — that is the "
        "calibration story.",
        "- Shape check: under the standard equity/variance-premium account, "
        "expect realized > implied in low-P(S_T>K) call-region buckets to "
        "be *absent* and the drift-driven realized > implied to concentrate "
        "in mid/high buckets (index drifts up under P but not under Q).",
        "",
    ]
    MD_OUT.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
