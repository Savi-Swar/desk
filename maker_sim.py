"""THE DESK #3: maker paper-quoter. Finds reward-eligible markets, simulates
quoting both sides inside the eligibility band, logs the quote + reward
parameters + midpoint. Successive snapshots measure adverse selection
(price moving through our quote = we'd have been filled by informed flow).
This is swisstony's game, measured before played."""
import datetime, json, urllib.request, pathlib
import pandas as pd
UA={"User-Agent":"research saviswarup@gmail.com"}
def get(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read())
D=pathlib.Path(__file__).parent/"collected"; D.mkdir(exist_ok=True)
now=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
rows=[]
mkts=get("https://gamma-api.polymarket.com/markets?closed=false&order=volume24hr&ascending=false&limit=200")
for m in mkts:
    try:
        cr=m.get("clobRewards") or []
        if not cr: continue
        rmax=float(m.get("rewardsMaxSpread") or 0); rmin=float(m.get("rewardsMinSize") or 0)
        bb,ba=float(m.get("bestBid") or 0),float(m.get("bestAsk") or 0)
        if not (0<bb<ba<1) or rmax<=0: continue
        mid=(bb+ba)/2
        if not 0.10<=mid<=0.90: continue
        daily_rate=sum(float(c.get("rewardsDailyRate") or 0) for c in cr)
        if daily_rate<=0: continue
        spread=ba-bb
        # our simulated quote: half the current spread, inside the band
        ours=min(spread/2, rmax/100 if rmax>1 else rmax)
        score=((max(rmax if rmax<1 else rmax/100,1e-6)-ours/2)/max(rmax if rmax<1 else rmax/100,1e-6))**2
        rows.append({"ts":now,"q":(m.get("question") or "")[:60],"mid":round(mid,3),
            "spread":round(spread,3),"reward_daily":daily_rate,"min_size":rmin,
            "our_spread":round(ours,3),"score_proxy":round(score,3)})
    except Exception: continue
f=D/"maker_book.csv"
if rows: pd.DataFrame(rows).to_csv(f,mode="a",header=not f.exists(),index=False)
tot=sum(r["reward_daily"] for r in rows)
print(f"reward-eligible quotable markets: {len(rows)} | combined daily reward pool ${tot:,.0f}")
for r in sorted(rows,key=lambda x:-x["reward_daily"])[:5]:
    print(f"  ${r['reward_daily']:.0f}/day pool | mid {r['mid']} spread {r['spread']} | {r['q'][:45]}")
