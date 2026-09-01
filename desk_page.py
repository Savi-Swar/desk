"""Generates screen 07 PREDMKT for Vig from the desk repo's ledgers and
writeups, using the same shell (header, tabs, surface, type) as the rest of
the terminal. The screen leads with the research program's current state:
the mirage ledger (RESULTS.md), what survived, and the forward experiments
that are still running. Numbers are computed from the committed ledgers at
generation time; the mirage/survivor prose mirrors RESULTS.md / HUNT_LOG.md.

Writes collected/desk.html and, when the checkout exists, mirrors it to the
vig-pages working tree (deployed to saviturswarup.com/vig by the nightly
publish)."""
import pathlib, json, datetime
import pandas as pd

ROOT = pathlib.Path(__file__).parent
D = ROOT / "collected"
OUTS = [D / "desk.html",
        pathlib.Path("/Users/swarup44891/lab/vig-pages/desk.html")]

INK, MUT, DIM = "#e6e2d8", "#8a9199", "#6d747c"
GRN, RED, AMB = "#46ff9a", "#ff5d5d", "#ffb000"
SURF, LINE, TILE = "#0b0d10", "#22262c", "#0e1114"


def load(n, base=None):
    f = (base or D) / n
    try:
        return pd.read_csv(f) if f.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def age_lamp(ts_series, warn_h, epoch=False):
    """Freshness lamp from the newest timestamp in a ledger."""
    if ts_series is None or not len(ts_series):
        return DIM, "no data"
    if epoch:
        newest = pd.to_datetime(pd.to_numeric(ts_series, errors="coerce"),
                                unit="s", utc=True).max()
    else:
        newest = pd.to_datetime(ts_series, errors="coerce", utc=True,
                                format="mixed").max()
    if pd.isna(newest):
        return DIM, "no data"
    hrs = (pd.Timestamp.now(tz="UTC") - newest).total_seconds() / 3600
    label = f"{hrs:.1f}h ago"
    return (GRN if hrs <= warn_h else RED), label


def table(df, cols, n=12, headers=None):
    if not len(df):
        return '<p class="dim">accruing…</p>'
    heads = headers or cols
    h = "".join(f"<th>{c}</th>" for c in heads)
    rows = ""
    for r in df.head(n).itertuples():
        tds = ""
        for c in cols:
            v = getattr(r, c, "")
            if isinstance(v, float):
                v = f"{v:,.3f}".rstrip("0").rstrip(".")
            tds += f"<td>{v}</td>"
        rows += f"<tr>{tds}</tr>"
    return f"<table><tr>{h}</tr>{rows}</table>"


def tile(label, value, sub="", color=INK):
    return (f'<div class="htile"><div class="hlabel">{label}</div>'
            f'<div class="hval" style="color:{color}">{value}</div>'
            f'<div class="hsub">{sub}</div></div>')


# ── load ledgers ─────────────────────────────────────────────────────────
mn  = load("maker_net.csv")           # concluded v2/v3 forward experiment
mn3 = load("maker_net3.csv")
mp  = load("maker_pnl_real.csv")      # real-fill maker gate (daily)
lf  = load("longshot_fwd.csv")        # live-ask forward ledger
wo  = load("weather_obs.csv")         # weather collector
lb  = load("pm_leaderboard.csv")      # collector heartbeat
taq = load("benchmark_table.csv", ROOT / "papers" / "paper0")

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# ── mirage ledger (condensed from RESULTS.md — receipts live there) ──────
MIRAGES = [
    ("1", "maker &ldquo;fills&rdquo; from book shrinkage",
     "1,735&times; overcount — cancels, not trades (48,578 vs 28 on the tape)"),
    ("2", "+$483/day maker markout",
     "&asymp;$0 — spread booked at a touch a rewards-eligible maker never rests at"),
    ("3", "crypto &ldquo;reverse bias&rdquo;, day-clustered t=&minus;4.2",
     "one crash month; month-clustered t=&minus;0.3"),
    ("4", "+5pp crypto favorites gap, persists OOS",
     "+0.6pp bet-weighted — below costs"),
    ("5", "&minus;12pp weather &ldquo;miscalibration&rdquo;",
     "stale last-trade marks — family prices sum to 1.39"),
    ("6", "weather model +125%, SR 0.9",
     "&minus;79%, SR &minus;4.9 on books fresh enough to trade"),
    ("7", "crypto favorites underpriced (2 verdict cells)",
     "pinned afterlife prints — 22&ndash;28% of marks postdate the close"),
    ("8", "short-longshots OOS SR 3.9, PSR 0.99",
     "sizing artifact — same stream &minus;3.3c/share equal-weight; reversed in 2026; retracted"),
]
mirage_rows = "".join(
    f'<tr><td class="dim">{n}</td><td>{sed}</td><td>{truth}</td></tr>'
    for n, sed, truth in MIRAGES)
mirage_tbl = (f"<table><tr><th>#</th><th>the seductive number</th>"
              f"<th>the truth</th></tr>{mirage_rows}</table>")

# ── TAQ yardstick (papers/paper0/benchmark_table.csv) ────────────────────
taq_order = ["US equity mega-cap", "US equity mid-cap", "US equity small-cap",
             "Polymarket tight (<1c)", "Polymarket wide (>3c)"]
if len(taq):
    taq["venue"] = pd.Categorical(taq["venue"], categories=taq_order,
                                  ordered=True)
    taq = taq.sort_values("venue")
taq_tbl = table(taq, ["venue", "eff_bps", "real_bps", "impact_bps"],
                headers=["venue / book", "eff half-spread (bps)",
                         "realized (bps)", "impact (bps)"])

# ── maker gate from real fills (compute, don't quote) ────────────────────
mk_days, mk_cum, mk_t = 0, 0.0, 0.0
if len(mp):
    net = mp["net_live"].astype(float)
    mk_days, mk_cum = len(net), net.sum()
    se = net.std(ddof=1) / len(net) ** 0.5 if len(net) > 1 else float("inf")
    mk_t = net.mean() / se if se else 0.0
mk_pass = mk_t >= 2.0

# ── forward experiments ──────────────────────────────────────────────────
lf_n = lf["market_id"].nunique() if len(lf) else 0
lf_graded = int(lf["graded"].astype(float).sum()) if len(lf) else 0
wo_rows = len(wo)
wo_cities = wo["city"].nunique() if len(wo) else 0

# ── concluded maker v2/v3 experiment (chart) ─────────────────────────────
curve_svg, gap_note, chart_json = '<p class="dim">needs 2+ snapshots…</p>', "", "[]"
mk_net_v, mk_rw, mk_fl, adverse_pct = 0.0, 0.0, 0.0, 0.0
mk3_net_v = None
span_note = ""
if len(mn):
    mn["t0"] = pd.to_datetime(mn["t0"], errors="coerce", utc=True, format="mixed")
    mn = mn.dropna(subset=["t0"])
    snap = mn.groupby("t0").agg(reward=("reward", "sum"),
                                fill_pnl=("fill_pnl", "sum")).sort_index()
    snap["cum_rw"] = snap["reward"].cumsum()
    snap["cum_fl"] = snap["fill_pnl"].cumsum()
    snap["cum_net"] = snap["cum_rw"] + snap["cum_fl"]
    mk_rw, mk_fl = snap["cum_rw"].iloc[-1], snap["cum_fl"].iloc[-1]
    mk_net_v = snap["cum_net"].iloc[-1]
    adverse_pct = 100 * (mn["fill_pnl"] < 0).mean()
    span_note = (f"{snap.index.min().strftime('%b %d')} &ndash; "
                 f"{snap.index.max().strftime('%b %d')}")

    if len(mn3):
        mn3["t0"] = pd.to_datetime(mn3["t0"], errors="coerce", utc=True, format="mixed")
        s3 = mn3.dropna(subset=["t0"]).groupby("t0").agg(
            net=("reward", "sum")).join(
            mn3.dropna(subset=["t0"]).groupby("t0").agg(fp=("fill_pnl", "sum")))
        s3["net"] = (s3["net"] + s3["fp"]).cumsum()
        snap["cum_net3"] = s3["net"].reindex(snap.index).ffill().fillna(0.0)
        mk3_net_v = snap["cum_net3"].iloc[-1]

    if len(snap) >= 2:
        W, H, PL, PR, PT, PB = 860, 240, 46, 90, 14, 26
        xs = list(range(len(snap)))
        all_y = (list(snap["cum_rw"]) + list(snap["cum_fl"]) + list(snap["cum_net"])
                 + (list(snap["cum_net3"]) if "cum_net3" in snap else []))
        lo, hi = min(all_y + [0]), max(all_y + [0])
        rng = (hi - lo) or 1.0
        def X(i): return PL + (W - PL - PR) * i / max(len(xs) - 1, 1)
        def Y(v): return PT + (H - PT - PB) * (1 - (v - lo) / rng)
        def poly(col, color):
            pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(snap[col]))
            return (f'<polyline points="{pts}" fill="none" stroke="{color}" '
                    f'stroke-width="2" stroke-linejoin="round"/>')
        def endlab(col, color, text):
            return (f'<text x="{W-PR+6}" y="{Y(snap[col].iloc[-1])+4:.1f}" '
                    f'fill="{color}" font-size="11">{text}</text>')
        zero = f'<line x1="{PL}" y1="{Y(0):.1f}" x2="{W-PR}" y2="{Y(0):.1f}" stroke="{LINE}" stroke-dasharray="3 4"/>'
        ylabs = "".join(
            f'<text x="{PL-8}" y="{Y(v)+4:.1f}" fill="{DIM}" font-size="10" text-anchor="end">${v:,.0f}</text>'
            for v in (lo, 0, hi) if abs(v) > rng * 0.04 or v == 0)
        curve_svg = (
            f'<div id="mkwrap" style="position:relative">'
            f'<svg id="mkchart" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'style="max-width:100%">{zero}{ylabs}'
            + poly("cum_rw", GRN) + poly("cum_fl", RED) + poly("cum_net", INK)
            + (poly("cum_net3", AMB) if "cum_net3" in snap else "")
            + endlab("cum_rw", GRN, "rewards") + endlab("cum_fl", RED, "adverse fills")
            + endlab("cum_net", INK, "NET v2")
            + (endlab("cum_net3", AMB, "NET v3 defended") if "cum_net3" in snap else "")
            + f'<line id="mkxh" y1="{PT}" y2="{H-PB}" stroke="{AMB}" stroke-width="1" opacity="0"/>'
            f'</svg><div id="mktip"></div></div>')
        chart_json = json.dumps({
            "t": [i.strftime("%m-%d %H:%M") for i in snap.index],
            "rw": [round(v, 2) for v in snap["cum_rw"]],
            "fl": [round(v, 2) for v in snap["cum_fl"]],
            "net": [round(v, 2) for v in snap["cum_net"]],
            "n3": [round(v, 2) for v in snap["cum_net3"]] if "cum_net3" in snap else [],
            "pl": PL, "pr": PR, "w": W})

# ── freshness lamps (live collectors only) ───────────────────────────────
lamps = ""
for name, series, warn, epoch in [
        ("collectors", lb["ts"] if len(lb) else None, 14, False),
        ("longshot fwd", lf["t"] if len(lf) else None, 14, True),
        ("weather", wo["t"] if len(wo) and "t" in wo else None, 14, True)]:
    c, lbl = age_lamp(series, warn, epoch=epoch)
    lamps += (f'<span class="lamp"><i style="background:{c}"></i>{name} '
              f'<span class="dim">{lbl}</span></span>')

# ── shell (matches Vig) ──────────────────────────────────────────────────
TABS = [("index.html", "01", "DESK"), ("analysis.html", "02", "ANALYSIS"),
        ("screener.html", "03", "SCREENER"), ("past_trades.html", "04", "PAST TRADES"),
        ("portfolio.html", "05", "PORTFOLIO"), ("research.html", "06", "RESEARCH"),
        ("desk.html", "07", "PREDMKT")]
tabs = "".join(f'<a class="tab{" active" if h == "desk.html" else ""}" href="{h}">'
               f'<span class="k">{n}</span>{t}</a>' for h, n, t in TABS)

CSS = """
* { box-sizing: border-box; margin: 0 }
body { background: #0b0d10; color: #e6e2d8;
  font: 13px "SF Mono", ui-monospace, Menlo, monospace; }
header { display: flex; justify-content: space-between; align-items: flex-end;
  padding: 18px 26px 14px; }
.wordmark { font-size: 30px; font-weight: 800; letter-spacing: 3px; }
.tagline { color: #6d747c; font-size: 11px; letter-spacing: 1px; }
.tagline b { color: #8a9199 }
.stamp-date { color: #6d747c; font-size: 11px }
.tabs { display: flex; border-top: 1px solid #22262c; border-bottom: 1px solid #22262c;
  position: sticky; top: 0; background: #0b0d10; z-index: 5 }
.tab { padding: 11px 20px; color: #8a9199; text-decoration: none; font-size: 12px;
  letter-spacing: 1.5px; border-right: 1px solid #22262c }
.tab .k { color: #6d747c; margin-right: 7px; font-size: 10px }
.tab.active { color: #e6e2d8; background: #0e1114; box-shadow: inset 0 2px 0 #ffb000 }
.tab:hover { color: #e6e2d8 }
.wrap { padding: 20px 26px 60px; max-width: 1080px }
h2 { font-size: 11px; letter-spacing: 2.5px; color: #ffb000; margin: 30px 0 10px;
  text-transform: uppercase }
h2::before { content: "▚ " }
h2 .dim { text-transform: none; letter-spacing: 0.5px }
.dim { color: #6d747c; font-size: 12px }
.htiles { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px }
.htile { border: 1px solid #22262c; background: #0e1114; padding: 12px 16px;
  min-width: 200px; flex: 1 }
.hlabel { color: #6d747c; font-size: 10px; letter-spacing: 2px; text-transform: uppercase }
.hval { font-size: 24px; font-weight: 700; margin: 6px 0 3px }
.hsub { color: #8a9199; font-size: 11px }
table { border-collapse: collapse; width: 100%; margin: 8px 0 }
td, th { border-bottom: 1px solid #14171b; padding: 5px 10px; text-align: left;
  font-size: 12px }
th { color: #6d747c; font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase }
tr:hover td { background: #0e1114 }
.lamp { margin-right: 18px; color: #8a9199; font-size: 11px }
.lamp i { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  margin-right: 6px }
.surv { border-left: 2px solid #22262c; padding: 2px 0 2px 14px; margin: 12px 0 }
.surv b { color: #e6e2d8 }
.surv .tag { font-size: 10px; letter-spacing: 1.5px; padding: 1px 7px;
  border: 1px solid #22262c; margin-right: 8px }
#mktip { position: absolute; display: none; background: #0e1114;
  border: 1px solid #22262c; padding: 8px 10px; font-size: 11px; pointer-events: none;
  z-index: 10; white-space: nowrap }
footer { color: #6d747c; font-size: 11px; padding: 0 26px 40px }
a { color: #e6e2d8 }
"""

JS = """
<script>
(() => {
  const pages = { "1": "index.html", "2": "analysis.html", "3": "screener.html",
                  "4": "past_trades.html", "5": "portfolio.html",
                  "6": "research.html", "7": "desk.html" };
  document.addEventListener("keydown", e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target instanceof Element && e.target.matches("input,textarea")) return;
    if (pages[e.key]) location.href = pages[e.key];
  });
  const d = window.MK_DATA, svg = document.getElementById("mkchart");
  if (!d || !d.t || !svg) return;
  const tip = document.getElementById("mktip"), xh = document.getElementById("mkxh");
  svg.addEventListener("mousemove", e => {
    const r = svg.getBoundingClientRect();
    const sx = (e.clientX - r.left) * (d.w / r.width);
    const span = d.w - d.pl - d.pr;
    let i = Math.round((sx - d.pl) / span * (d.t.length - 1));
    i = Math.max(0, Math.min(d.t.length - 1, i));
    const px = d.pl + span * i / Math.max(d.t.length - 1, 1);
    xh.setAttribute("x1", px); xh.setAttribute("x2", px); xh.setAttribute("opacity", 1);
    tip.style.display = "block";
    tip.style.left = Math.min(px / d.w * r.width + 12, r.width - 170) + "px";
    tip.style.top = "18px";
    tip.innerHTML = "<b>" + d.t[i] + "</b><br>rewards $" + d.rw[i] +
      "<br>adverse $" + d.fl[i] + "<br>net v2 <b>$" + d.net[i] + "</b>" +
      (d.n3 && d.n3.length ? "<br>net v3 <b>$" + d.n3[i] + "</b>" : "");
  });
  svg.addEventListener("mouseleave", () => {
    tip.style.display = "none"; xh.setAttribute("opacity", 0);
  });
})();
</script>"""

body = f"""
<div class="lamps" style="margin-bottom:4px">{lamps}</div>

<h2>8 backtest mirages, found and killed <span class="dim">— in our own
results, each with the kill method on record</span></h2>
{mirage_tbl}
<p class="dim">Every seductive number the pipeline produced was attacked
until it died or survived. A number that hasn't survived an attempt to kill
it doesn't get quoted. Receipts (code + writeup per line): RESULTS.md in the
desk repo.</p>

<h2>What survived every attack</h2>

<div class="surv"><span class="tag" style="color:{GRN}">SURVIVOR</span>
<b>Polymarket vs the equity yardstick</b> — same Stoll (2000) decomposition,
equities from raw millisecond TAQ; $-weighted, 30s horizon, bps of price.
{taq_tbl}
<p class="dim">Tight prediction-market books trade like a somewhat-worse
small-cap (17.2 vs 8.6 bps effective half-spread). Wide books book a
&ldquo;realized spread&rdquo; ~80&times; a small-cap maker's take — the
fill-at-touch mirage in one row. Regenerable: papers/paper0.</p></div>

<div class="surv"><span class="tag" style="color:{GRN}">SURVIVOR</span>
<b>The crowd beats the model</b> — vig-stripped T-24h weather-ladder prices
are better calibrated than a bias-corrected D-1 GFS+ECMWF blend: log-loss
0.360 vs 0.388 over 2,972 buckets, walk-forward. Retail prediction markets
embed public NWP by the day before.</div>

<div class="surv"><span class="tag" style="color:{AMB}">PENDING</span>
<b>Politics favorites are overpriced (sell side)</b> — the one candidate
still standing from six pre-registered hunts: test bet-weighted
&minus;3.6pp, month-t &minus;2.1, both engine sizing modes agree, survives
slippage at 100/200/300bps, held in both 2026 months. <b>Not claimed</b>:
PSR 0.88/0.91 &lt; 0.95 and 7 test months &lt; 8. Adjudication is
pre-registered and pending the tail-marks crawl — pass the fixed bar and
it's claimed, fail and it becomes mirage #9. No parameter may change in
between (HUNT_LOG.md).</div>

<h2>Status <span class="dim">— what is running forward right now</span></h2>
<div class="htiles">
{tile("Longshot forward test", f"{lf_n} entries",
      f"{lf_graded} graded · live CLOB asks, CI 2&times;/day, self-grading — "
      "the sole remaining arbiter of the longshot story", AMB)}
{tile("Weather collector", f"{wo_rows:,} obs",
      f"{wo_cities} cities · ladder prices + GFS/ECMWF/ICON forecasts, accruing", AMB)}
{tile("Maker gate (real fills)", f"${mk_cum:+,.0f} · t={mk_t:.2f}",
      f"{mk_days} days, rebate-driven · {'passes' if mk_pass else 'below'} the "
      "t&ge;2.0 bar — says so here until it clears it",
      GRN if mk_pass else AMB)}
{tile("Papers", "0 + 1 drafted",
      "measurement artifacts in maker backtests · favorite-longshot structure "
      "in 880k resolutions", INK)}
</div>

<h2>Concluded experiment <span class="dim">— maker v2 naive control vs v3
defended quoter, cumulative · {span_note}</span></h2>
{curve_svg}
<p class="dim">v2 quotes symmetrically and never moves — it measures the toll.
v3 adds the standard defenses (drift skew, circuit-breaker pulls, inventory
caps) with parameters fixed a priori. The distance between the two NET lines
is what the defenses recover; the distance from v3 to zero is what is left.
Verdict (via the real-fill gate above): the only durable maker income is the
fee rebate, roughly cancelled by adverse selection at a realistic resting
size.</p>
"""

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="900">
<title>VIG · 07 PREDMKT</title><style>{CSS}</style></head><body>
<header>
  <div>
    <div class="wordmark">VIG</div>
    <div class="tagline">the house takes its cut — <b>prediction-market research desk · paper only</b></div>
  </div>
  <div class="stamp-date">{now}</div>
</header>
<nav class="tabs">{tabs}</nav>
<div class="wrap">
<p class="dim">A research program run like a desk: every backtest number is
attacked before it is believed, and the kills are the product. The research
that feeds this screen is <a href="research.html">06 RESEARCH</a>; forward
ledgers refresh on the collector cycle and this page regenerates with them.</p>
{body}
</div>
<footer>keys: <b>1–7</b> screens · paper only — no live capital, by
construction · every number regenerates from a committed ledger or writeup
in the desk repo · <code>ideal</code>-labeled columns are counterfactual
ceilings, never results</footer>
<script>window.MK_DATA = {chart_json};</script>
{JS}
</body></html>"""

wrote = []
for out in OUTS:
    try:
        if out.parent.exists():
            out.write_text(html)
            wrote.append(str(out))
    except Exception as e:
        print(f"skip {out}: {type(e).__name__}: {e}")
print(f"desk.html written ({len(html)} bytes) -> " + " · ".join(wrote))
