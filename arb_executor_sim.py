"""Arb executor-simulator. Detect neg-risk set mispricings, pull the
real order book for every leg, compute executable size and net profit at
actual depth, paper-fill, log. Measures live extraction rate."""
import datetime, json, urllib.request, pathlib
import pandas as pd
UA={"User-Agent":"research saviswarup@gmail.com"}
def get(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read())
D=pathlib.Path(__file__).parent/"collected"; D.mkdir(exist_ok=True)
now=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
fills=[]
evs=get("https://gamma-api.polymarket.com/events?closed=false&limit=300&order=volume24hr&ascending=false")
checked=0
for ev in evs:
    mkts=ev.get("markets",[])
    if len(mkts)<3 or not ev.get("negRisk",False): continue
    try:
        bids=[float(m.get("bestBid") or 0) for m in mkts]
        asks=[float(m.get("bestAsk") or 0) for m in mkts]
    except (TypeError,ValueError): continue
    if not all(0<a<=1 for a in asks): continue
    sell_edge=sum(bids)-1.0; buy_edge=1.0-sum(asks)
    if max(sell_edge,buy_edge)<0.005: continue
    checked+=1
    if checked>6: break          # book-fetch budget per run
    # pull real books for every leg
    legs=[]
    ok=True
    for m in mkts:
        try:
            toks=json.loads(m.get("clobTokenIds","[]"))
            book=get(f"https://clob.polymarket.com/book?token_id={toks[0]}")
            b=book.get("bids",[]); a=book.get("asks",[])
            legs.append({"q":(m.get("question") or "")[:40],
                "bid":float(b[-1]["price"]) if b else 0,"bid_sz":float(b[-1]["size"]) if b else 0,
                "ask":float(a[-1]["price"]) if a else 1,"ask_sz":float(a[-1]["size"]) if a else 0})
        except Exception: ok=False; break
    if not ok or not legs: continue
    # SELL-ALL: sell YES on every leg at bid -> guaranteed cost 1 payout sum(bids)
    tb=sum(l["bid"] for l in legs); ta=sum(l["ask"] for l in legs)
    if tb>1.005:
        size=min(l["bid_sz"] for l in legs)         # executable shares across ALL legs
        profit=(tb-1.0)*size
        fills.append({"ts":now,"event":ev.get("title","")[:60],"type":"SELL-ALL",
            "edge_pershare":round(tb-1,4),"exec_size":round(size,1),
            "profit_at_depth":round(profit,2),"n_legs":len(legs)})
    if ta<0.995:
        size=min(l["ask_sz"] for l in legs)
        profit=(1.0-ta)*size
        fills.append({"ts":now,"event":ev.get("title","")[:60],"type":"BUY-ALL",
            "edge_pershare":round(1-ta,4),"exec_size":round(size,1),
            "profit_at_depth":round(profit,2),"n_legs":len(legs)})
f=D/"arb_fills.csv"
if fills:
    pd.DataFrame(fills).to_csv(f,mode="a",header=not f.exists(),index=False)
print(f"top-of-book candidates checked: {checked}")
for x in fills:
    print(f"  [{x['type']}] {x['edge_pershare']*100:.1f}c/share x {x['exec_size']} shares executable = ${x['profit_at_depth']:.2f} REAL profit | {x['event']}")
if not fills: print("  no depth-verified arbs this snapshot (top-of-book edges did not survive real books)")
