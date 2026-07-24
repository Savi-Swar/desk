"""Unified daily collectors — the moat. Each run appends timestamped
snapshots. 1) Polymarket arb monitor  2) Binance funding rates
3) Polymarket leaderboard + top-wallet positions (corrected insider tracker:
forward-tracking, no pagination trap)."""
import datetime, json, urllib.request, pathlib
import pandas as pd
UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())
def append(name, df):
    f = D / f"{name}.csv"
    df.to_csv(f, mode="a", header=not f.exists(), index=False)

# 1) arb monitor (neg-risk sets mispriced)
try:
    rows = []
    evs = get("https://gamma-api.polymarket.com/events?closed=false&limit=300&order=volume24hr&ascending=false")
    for ev in evs:
        mkts = ev.get("markets", [])
        if len(mkts) < 3 or not ev.get("negRisk", False): continue
        try:
            asks = [float(m.get("bestAsk") or 0) for m in mkts]
            bids = [float(m.get("bestBid") or 0) for m in mkts]
        except (TypeError, ValueError): continue
        if not all(0 < a <= 1 for a in asks): continue
        sa, sb = sum(asks), sum(bids)
        if sa < 0.995 or sb > 1.005:
            rows.append({"ts": now, "event": ev.get("title","")[:70],
                         "buy_edge": round(max(0,1-sa),4), "sell_edge": round(max(0,sb-1),4),
                         "n": len(mkts)})
    if rows: append("predmkt_arbs", pd.DataFrame(rows))
    print(f"arbs: {len(rows)}")
except Exception as e: print("arb monitor fail:", type(e).__name__)

# 2) funding rates
try:
    import ccxt
    fr = ccxt.binance().fetch_funding_rates()
    df = pd.DataFrame([{"ts": now, "symbol": k, "rate": v.get("fundingRate")}
                       for k, v in fr.items()])
    append("funding", df)
    print(f"funding: {len(df)} perps")
except Exception as e: print("funding fail:", type(e).__name__)

# 3) leaderboard + top-wallet positions (forward insider tracking)
try:
    lb = None
    for url in ("https://data-api.polymarket.com/v1/leaderboard?timePeriod=month&orderBy=pnl&limit=30",):
        try:
            lb = get(url); break
        except Exception: continue
    wallets = []
    if isinstance(lb, list):
        for e in lb:
            w = e.get("proxyWallet")
            if w: wallets.append({"ts": now, "wallet": w, "pnl": e.get("pnl"), "vol": e.get("vol"),
                                  "name": (e.get("userName") or "")[:30]})
    if wallets:
        append("pm_leaderboard", pd.DataFrame(wallets))
        pos_rows = []
        for w in wallets[:15]:
            try:
                ps = get(f"https://data-api.polymarket.com/positions?user={w['wallet']}&limit=50&sortBy=CURRENT")
                for p in ps:
                    pos_rows.append({"ts": now, "wallet": w["wallet"],
                                     "title": (p.get("title") or "")[:60],
                                     "outcome": p.get("outcome"), "size": p.get("size"),
                                     "avgPrice": p.get("avgPrice"), "curPrice": p.get("curPrice")})
            except Exception: continue
        if pos_rows: append("pm_top_positions", pd.DataFrame(pos_rows))
        print(f"leaderboard: {len(wallets)} wallets, positions rows: {len(pos_rows)}")
    else:
        print("leaderboard: no data (endpoint shape changed?)")
except Exception as e: print("leaderboard fail:", type(e).__name__)

# Desk #2: whale shadow-book diff (runs after position snapshot)
try:
    import subprocess, sys, pathlib
    subprocess.run([sys.executable, str(pathlib.Path(__file__).parent/"whale_shadow.py")], timeout=120)
except Exception as e:
    print("shadow diff fail:", type(e).__name__)

# Desk #3: maker paper-quoter snapshot
try:
    import subprocess, sys, pathlib
    subprocess.run([sys.executable, str(pathlib.Path(__file__).parent/"maker_sim.py")], timeout=120)
except Exception as e:
    print("maker sim fail:", type(e).__name__)

# Desk grading + morning report
try:
    import subprocess, sys, pathlib
    subprocess.run([sys.executable, str(pathlib.Path(__file__).parent/"shadow_grader.py")], timeout=300)
    with open(pathlib.Path(__file__).parent/"collected"/"DESK_REPORT.md","w") as fh:
        import io, contextlib
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(open(pathlib.Path(__file__).parent/"desk_grade.py").read())
        fh.write("```\n"+buf.getvalue()+"\n```\n")
except Exception as e:
    print("grade/report fail:", type(e).__name__)

# Desk #3b: maker NET simulation across snapshots
try:
    import subprocess, sys, pathlib
    subprocess.run([sys.executable, str(pathlib.Path(__file__).parent/"maker_sim2.py")], timeout=120)
except Exception as e:
    print("maker v2 fail:", type(e).__name__)

# Vig DESK page refresh
try:
    import subprocess, sys, pathlib
    subprocess.run([sys.executable, str(pathlib.Path(__file__).parent/"desk_page.py")], timeout=60)
except Exception as e:
    print("desk page fail:", type(e).__name__)
