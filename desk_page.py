"""Generates screen 07 PREDMKT for Vig (reports/dashboard/desk.html) from the
live paper-desk ledgers, using the same shell (header, tabs, surface, type)
as the rest of the terminal."""
import pathlib, json, datetime
import pandas as pd

D = pathlib.Path(__file__).parent / "collected"
OUT = pathlib.Path("/Users/swarup44891/Downloads/Quant/reports/dashboard/desk.html")

INK, MUT, DIM = "#e6e2d8", "#8a9199", "#6d747c"
GRN, RED, AMB = "#46ff9a", "#ff5d5d", "#ffb000"
SURF, LINE, TILE = "#0b0d10", "#22262c", "#0e1114"


def load(n):
    f = D / n
    try:
        return pd.read_csv(f) if f.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def age_lamp(ts_series, warn_h):
    """Freshness lamp from the newest timestamp in a ledger."""
    if ts_series is None or not len(ts_series):
        return DIM, "no data"
    newest = pd.to_datetime(ts_series, errors="coerce", utc=True, format="mixed").max()
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


# ── load everything ──────────────────────────────────────────────────────
a  = load("arb_fills.csv")
s  = load("shadow_ledger.csv")
g  = load("shadow_graded.csv")
m  = load("maker_book.csv")
mn = load("maker_net.csv")
lb = load("pm_leaderboard.csv")
dr = load("drill_2026-07-23.csv")

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# ── maker economics: per-snapshot sums -> cumulative curves ──────────────
curve_svg, gap_note, chart_json = '<p class="dim">needs 2+ snapshots…</p>', "", "[]"
mk_net_v, mk_rw, mk_fl, adverse_pct = 0.0, 0.0, 0.0, 0.0
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

    gaps = snap.index.to_series().diff()
    big = gaps[gaps > pd.Timedelta(hours=2)]
    if len(big):
        parts = [f"{i.strftime('%m-%d %H:%M')} (−{d.total_seconds()/3600:.1f}h)"
                 for i, d in big.items()]
        gap_note = ('<p class="dim">sampling gaps (machine asleep): '
                    + " · ".join(parts) + "</p>")

    if len(snap) >= 2:
        W, H, PL, PR, PT, PB = 860, 240, 46, 90, 14, 26
        xs = list(range(len(snap)))
        all_y = (list(snap["cum_rw"]) + list(snap["cum_fl"]) + list(snap["cum_net"]))
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
            + endlab("cum_rw", GRN, "rewards") + endlab("cum_fl", RED, "adverse fills")
            + endlab("cum_net", INK, "NET")
            + f'<line id="mkxh" y1="{PT}" y2="{H-PB}" stroke="{AMB}" stroke-width="1" opacity="0"/>'
            f'</svg><div id="mktip"></div></div>')
        chart_json = json.dumps({
            "t": [i.strftime("%m-%d %H:%M") for i in snap.index],
            "rw": [round(v, 2) for v in snap["cum_rw"]],
            "fl": [round(v, 2) for v in snap["cum_fl"]],
            "net": [round(v, 2) for v in snap["cum_net"]],
            "pl": PL, "pr": PR, "w": W})

# ── headline numbers ─────────────────────────────────────────────────────
arb_profit = a["profit_at_depth"].sum() if len(a) else 0.0
arb_sub = f"{len(a)} depth-verified fills" if len(a) else "0 fills — edges rarely survive real books"

sh_deployed = s["paper_stake"].sum() if len(s) else 0.0
sh_graded = f"{len(g)} graded, P&L ${g['pnl'].sum():+,.0f}" if len(g) else f"{len(s)} open · 0 resolved"

mk_latest = m[m["ts"] == m["ts"].max()] if len(m) else m
pool = mk_latest["reward_daily"].sum() if len(m) else 0.0

drill_rows = ""
if len(dr):
    for r in dr.itertuples():
        q = str(r.q)[:70]
        drill_rows += (f"<tr><td>{q}</td><td>{float(r.p):.2f}</td>"
                       f"<td>{float(r.model_p):.3f}</td><td class='dim'>pending</td></tr>")
drill_tbl = (f"<table><tr><th>question</th><th>market</th><th>model</th>"
             f"<th>brier</th></tr>{drill_rows}</table>") if drill_rows else '<p class="dim">no drill on record</p>'

# ── freshness lamps ──────────────────────────────────────────────────────
lamps = ""
for name, df_, col, warn in [("arb sampler", mn, "t0", 1.5),
                             ("collectors", lb, "ts", 14)]:
    c, lbl = age_lamp(df_[col] if len(df_) else None, warn)
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
      "<br>adverse $" + d.fl[i] + "<br>net <b>$" + d.net[i] + "</b>";
  });
  svg.addEventListener("mouseleave", () => {
    tip.style.display = "none"; xh.setAttribute("opacity", 0);
  });
})();
</script>"""

body = f"""
<div class="lamps" style="margin-bottom:4px">{lamps}</div>
<div class="htiles">
{tile("Arb realized at depth", f"${arb_profit:+,.2f}", arb_sub, GRN if arb_profit >= 0 else RED)}
{tile("Maker net (paper)", f"${mk_net_v:+,.2f}",
      f"rewards ${mk_rw:,.0f} · fills ${mk_fl:+,.0f} · {adverse_pct:.0f}% adverse",
      GRN if mk_net_v >= 0 else RED)}
{tile("Reward pools live", f"${pool:,.0f}/d", f"{len(mk_latest)} eligible markets", AMB)}
</div>

<h2>Maker economics <span class="dim">— cumulative, naive symmetric quoter (the control)</span></h2>
{curve_svg}
{gap_note}
<p class="dim">This quoter never pulls or skews — it measures the toll. The gap
between the red and green lines is what a viable maker must dodge.</p>

<h2>Arb executor <span class="dim">— every 30 min vs real order-book depth</span></h2>
{table(a.sort_values("ts", ascending=False) if len(a) else a,
       ["ts", "event", "type", "edge_pershare", "exec_size", "profit_at_depth"])}

<h2>Calibration drill <span class="dim">— house model (0.87 shrink) vs market · resolves Jul 28–31</span></h2>
{drill_tbl}

<h2>Maker snapshot <span class="dim">— largest live reward pools</span></h2>
{table(mk_latest.sort_values("reward_daily", ascending=False) if len(m) else m,
       ["reward_daily", "mid", "spread", "our_spread", "q"], n=8)}
"""

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="900">
<title>VIG · 06 PREDMKT</title><style>{CSS}</style></head><body>
<header>
  <div>
    <div class="wordmark">VIG</div>
    <div class="tagline">the house takes its cut — <b>live paper desk · prediction markets</b></div>
  </div>
  <div class="stamp-date">{now}</div>
</header>
<nav class="tabs">{tabs}</nav>
<div class="wrap">
<p class="dim">Mechanisms that cannot be backtested, running forward on
paper. Gates before dollars — the research that picked them is
<a href="research.html">06 RESEARCH</a>. Ledgers refresh on the collector
cycle; this page regenerates with them.</p>
{body}
</div>
<footer>keys: <b>1–7</b> screens · paper only — no live capital ·
every number traces to a ledger in moneymaker3000/collected/</footer>
<script>window.MK_DATA = {chart_json};</script>
{JS}
</body></html>"""

try:
    OUT.write_text(html)
    print(f"desk.html written to Vig dashboard ({len(html)} bytes)")
except Exception as e:
    (D / "desk.html").write_text(html)
    print(f"Vig dir unavailable ({type(e).__name__}); wrote collected/desk.html")
