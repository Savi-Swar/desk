"""CRSP validation sleeve (desk-year-plan.md Amendment 1).

Reproduce the classic 12-2 cross-sectional momentum anomaly on CRSP monthly
data, and run the resulting long-short return series through this repo's own
statistics module (backtest/stats.py), to show the machinery generalizes
beyond prediction markets.

Run inside the WRDS venv (uses ~/.pgpass; username parsed from it):

    ~/lab/wrds-env/bin/python backtest/crsp_momentum.py

Design (classic Jegadeesh-Titman / French "Prior 2-12"):
- Holding month h: signal = cumulative return over months h-12 .. h-2
  (11 months, skipping h-1, the month immediately before holding).
- Formation = end of month h-1: filters (share code, exchange, price,
  size breakpoint) use month h-1 data.
- Equal-weighted deciles on the signal; strategy = top decile - bottom decile,
  held for month h. Holding months: 2015-01 .. 2025-12 (as available).

Filters at formation:
- shrcd in (10, 11) — common shares
- exchcd in (1, 2, 3) — NYSE / AMEX / NASDAQ
- |prc| >= $5
- market cap (|prc| * shrout) >= NYSE-only 20th percentile that month

Deviations from a full-dress replication are listed in the output .md.

NOTE on stats.py: its sharpe() annualizes with sqrt(365) because the desk's
convention is daily prediction-market returns. These are MONTHLY returns, so
the annualized Sharpe here is computed as mean/std*sqrt(12). psr() is
annualization-agnostic internally (it divides the sqrt(365) back out), so it
is used directly on the monthly series.
"""
import math
import os
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import psr, sharpe  # noqa: E402  (repo stats module)

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT_MD = REPO / "data" / "crsp_momentum_result.md"
OUT_CSV = REPO / "data" / "crsp_momentum_returns.csv"

HOLD_START = pd.Period("2015-01", "M")
HOLD_END = pd.Period("2025-12", "M")
# need 12 months of history before the first formation month (2014-12)
PULL_START = "2013-11-01"
PULL_END = "2025-12-31"

SQL = f"""
select a.permno, a.date, a.ret, a.prc, a.shrout, b.exchcd
from crsp.msf a
join crsp.msenames b
  on a.permno = b.permno
 and b.namedt <= a.date
 and a.date <= b.nameendt
where a.date between '{PULL_START}' and '{PULL_END}'
  and b.shrcd in (10, 11)
  and b.exchcd in (1, 2, 3)
"""

SQL_DELIST = f"""
select permno, dlstdt, dlret
from crsp.msedelist
where dlstdt between '{PULL_START}' and '{PULL_END}'
  and dlret is not null
"""


def username():
    """4th colon-separated field of the first ~/.pgpass line (never the password)."""
    line = open(pathlib.Path.home() / ".pgpass").read().splitlines()[0]
    return line.split(":")[3]


def connect(retries=7, wait_s=600):
    """WRDS pgdata sometimes drops SSL or temp-locks after failed attempts;
    retry on a slow schedule rather than hammering it."""
    import time
    import wrds
    last = None
    for i in range(retries):
        try:
            db = wrds.Connection(wrds_username=username(), autoconnect=False)
            db._Connection__make_sa_engine_conn(raise_err=True)
            return db
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  connect attempt {i + 1}/{retries} failed: "
                  f"{type(e).__name__}: {str(e)[:120]}", flush=True)
            if i < retries - 1:
                time.sleep(wait_s)
    raise last


def pull():
    db = connect()
    msf = db.raw_sql(SQL, date_cols=["date"])
    dl = db.raw_sql(SQL_DELIST, date_cols=["dlstdt"])
    db.close()
    return msf, dl


def build_panel(msf, dl):
    msf["m"] = msf["date"].dt.to_period("M")
    dl["m"] = dl["dlstdt"].dt.to_period("M")

    # fold delisting returns into the delist month: (1+ret)*(1+dlret)-1,
    # or dlret alone when ret is missing that month
    dl = dl.groupby(["permno", "m"], as_index=False)["dlret"].apply(
        lambda s: (1 + s).prod() - 1)
    msf = msf.merge(dl, on=["permno", "m"], how="left")
    both = msf["ret"].notna() & msf["dlret"].notna()
    msf.loc[both, "ret"] = (1 + msf.loc[both, "ret"]) * (1 + msf.loc[both, "dlret"]) - 1
    only_dl = msf["ret"].isna() & msf["dlret"].notna()
    msf.loc[only_dl, "ret"] = msf.loc[only_dl, "dlret"]

    # a permno can straddle two msenames rows in a month; keep last record
    msf = msf.sort_values(["permno", "date"]).drop_duplicates(["permno", "m"], keep="last")

    msf["prc_abs"] = msf["prc"].abs()
    msf["cap"] = msf["prc_abs"] * msf["shrout"]  # shrout in thousands; fine for ranking

    months = pd.period_range(msf["m"].min(), msf["m"].max(), freq="M")
    ret_w = msf.pivot(index="m", columns="permno", values="ret").reindex(months)
    prc_w = msf.pivot(index="m", columns="permno", values="prc_abs").reindex(months)
    cap_w = msf.pivot(index="m", columns="permno", values="cap").reindex(months)
    exch_w = msf.pivot(index="m", columns="permno", values="exchcd").reindex(months)
    return ret_w, prc_w, cap_w, exch_w


def backtest(ret_w, prc_w, cap_w, exch_w):
    # signal at holding month h: cum return over h-12..h-2 (all 11 months required)
    logr = np.log1p(ret_w)
    sig = np.expm1(logr.rolling(11, min_periods=11).sum()).shift(2)

    # formation-month (h-1) characteristics
    prc_f, cap_f, exch_f = prc_w.shift(1), cap_w.shift(1), exch_w.shift(1)

    rows = []
    hold_months = [m for m in ret_w.index if HOLD_START <= m <= HOLD_END]
    for h in hold_months:
        s, p, c, e, r = sig.loc[h], prc_f.loc[h], cap_f.loc[h], exch_f.loc[h], ret_w.loc[h]
        nyse_caps = c[e == 1].dropna()
        if nyse_caps.empty:
            continue
        nyse20 = nyse_caps.quantile(0.20)
        elig = s.notna() & (p >= 5) & (c >= nyse20)
        if elig.sum() < 100:
            continue
        se = s[elig]
        dec = pd.qcut(se.rank(method="first"), 10, labels=False)
        winners = r[se.index[dec == 9]].mean()
        losers = r[se.index[dec == 0]].mean()
        rows.append({"month": str(h), "n_stocks": int(elig.sum()),
                     "winner": winners, "loser": losers,
                     "ls": winners - losers})
    return pd.DataFrame(rows).set_index("month")


def max_drawdown(rets):
    wealth = (1 + rets).cumprod()
    dd = wealth / wealth.cummax() - 1
    trough = dd.idxmin()
    return dd.min(), trough


def main():
    print("pulling CRSP monthly file from WRDS ...")
    msf, dl = pull()
    print(f"  msf rows: {len(msf):,}   delist rows: {len(dl):,}")
    ret_w, prc_w, cap_w, exch_w = build_panel(msf, dl)
    print(f"  panel: {ret_w.shape[0]} months x {ret_w.shape[1]:,} permnos "
          f"({ret_w.index.min()} .. {ret_w.index.max()})")

    port = backtest(ret_w, prc_w, cap_w, exch_w)
    ls = port["ls"].dropna()
    n = len(ls)
    mu, sd = ls.mean(), ls.std(ddof=1)

    ann_mean = mu * 12
    ann_vol = sd * math.sqrt(12)
    sr = (mu / sd) * math.sqrt(12)                 # correct monthly annualization
    sr_repo_raw = sharpe(list(ls))                 # repo sharpe() (sqrt(365) daily conv.)
    sr_repo_rescaled = sr_repo_raw * math.sqrt(12 / 365)
    tstat = mu / (sd / math.sqrt(n))
    p = psr(list(ls))                              # annualization-agnostic
    mdd, trough = max_drawdown(ls)

    crash = {m: (port["ls"].get(m), port["winner"].get(m), port["loser"].get(m))
             for m in ("2020-03", "2020-04", "2020-11")}

    port.to_csv(OUT_CSV)

    lines = [
        "# CRSP validation sleeve: 12-2 cross-sectional momentum",
        "",
        "Amendment-1 validation run (desk-year-plan.md): the repo's backtest",
        "statistics applied to a known equity anomaly on CRSP monthly data.",
        f"Generated by `backtest/crsp_momentum.py` on {pd.Timestamp.now():%Y-%m-%d}.",
        "Rerun: `~/lab/wrds-env/bin/python backtest/crsp_momentum.py`",
        "",
        "## Strategy",
        "",
        "Classic Jegadeesh-Titman momentum (French \"Prior 2-12\"). For holding",
        "month *h*: rank on cumulative return over months *h*-12..*h*-2 (11",
        "months, skipping *h*-1); equal-weighted deciles; long top decile,",
        "short bottom decile, hold one month. Formation filters use month",
        "*h*-1 data: common shares (shrcd 10/11), NYSE/AMEX/NASDAQ (exchcd",
        "1/2/3), |prc| >= $5, market cap >= NYSE-only 20th percentile.",
        "Delisting returns (crsp.msedelist) are compounded into delist months.",
        "",
        f"Holding months: {ls.index[0]} .. {ls.index[-1]} "
        f"({n} months; avg {port['n_stocks'].mean():.0f} eligible stocks/month).",
        "",
        "## Results (monthly long-short, equal-weighted, gross)",
        "",
        "| metric | value |",
        "|---|---|",
        f"| annualized mean | {ann_mean:+.2%} |",
        f"| annualized vol | {ann_vol:.2%} |",
        f"| Sharpe (mean/std x sqrt(12)) | {sr:.2f} |",
        f"| t-stat of monthly mean | {tstat:.2f} |",
        f"| PSR vs SR=0 (repo `stats.psr`) | {p:.3f} |",
        f"| worst drawdown | {mdd:.1%} (trough {trough}) |",
        f"| best month | {ls.max():+.1%} ({ls.idxmax()}) |",
        f"| worst month | {ls.min():+.1%} ({ls.idxmin()}) |",
        "",
        "### Momentum-crash months",
        "",
        "| month | long-short | winner decile | loser decile |",
        "|---|---|---|---|",
    ]
    for m, (v, w, l) in crash.items():
        if v is None or (isinstance(v, float) and math.isnan(v)):
            lines.append(f"| {m} | n/a | n/a | n/a |")
        else:
            lines.append(f"| {m} | {v:+.1%} | {w:+.1%} | {l:+.1%} |")
    lines += [
        "",
        "## Stats-module usage",
        "",
        "- `stats.psr` used directly: it converts to per-period SR internally,",
        "  so its sqrt(365) convention cancels and it is valid on monthly data.",
        "- `stats.sharpe` annualizes daily with sqrt(365) (desk convention), so",
        "  it is NOT quoted as-is for monthly returns. Cross-check: repo",
        f"  sharpe() raw = {sr_repo_raw:.2f}; rescaled x sqrt(12/365) =",
        f"  {sr_repo_rescaled:.2f}, matching the manual {sr:.2f} (tiny gap is",
        "  pstdev vs. ddof=1).",
        "",
        "## SQL and filters",
        "",
        "```sql",
        SQL.strip(),
        "```",
        "",
        "```sql",
        SQL_DELIST.strip(),
        "```",
        "",
        "## Deviations / notes",
        "",
        f"- Data pulled from {PULL_START} (not 2015-01) purely to supply the",
        "  12-month lookback for the first 2015 holding months.",
        "- Signal requires all 11 lookback returns non-missing (stricter than",
        "  the common min-8-months rule).",
        "- Equal-weighted deciles (per spec); value-weighting would lower the",
        "  numbers somewhat.",
        "- Gross returns: no transaction costs, no shorting fees.",
        "- Where a permno spans two msenames rows in one month, the later row",
        "  is kept.",
        "",
        f"Full monthly series: `data/{OUT_CSV.name}`.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n")

    print(f"\nmonths={n}  ann_mean={ann_mean:+.2%}  ann_vol={ann_vol:.2%}  "
          f"Sharpe={sr:.2f}  t={tstat:.2f}  PSR={p:.3f}  maxDD={mdd:.1%} ({trough})")
    for m, (v, w, l) in crash.items():
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            print(f"  {m}: L/S {v:+.1%}  (W {w:+.1%} / L {l:+.1%})")
    print(f"\nwrote {OUT_MD}\nwrote {OUT_CSV}")


if __name__ == "__main__":
    main()
