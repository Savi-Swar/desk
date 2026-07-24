"""Nightly: grade shadow-ledger entries against resolved markets (exact-title
match on recently-closed gamma markets). Appends verdicts to shadow_graded.csv."""
import json, urllib.request, pathlib, time
import pandas as pd
UA={"User-Agent":"research saviswarup@gmail.com"}
def get(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read())
D=pathlib.Path(__file__).parent/"collected"
led=D/"shadow_ledger.csv"; out=D/"shadow_graded.csv"
if not led.exists(): print("no ledger"); raise SystemExit
L=pd.read_csv(led)
done=set()
if out.exists():
    G=pd.read_csv(out); done=set(zip(G["ts"],G["title"],G["outcome"]))
todo=L[[ (t,ti,o) not in done for t,ti,o in zip(L["ts"],L["title"],L["outcome"])]]
if not len(todo): print("nothing to grade"); raise SystemExit
# resolved markets last 14 days, title->outcome map
res={}
for off in range(0,800,100):
    try: mk=get(f"https://gamma-api.polymarket.com/markets?closed=true&order=endDate&ascending=false&limit=100&offset={off}")
    except Exception: break
    if not mk: break
    for m in mk:
        try:
            o=json.loads(m.get("outcomes","[]")); p=json.loads(m.get("outcomePrices","[]"))
            if len(o)>=2 and len(p)>=2:
                res[(m.get("question") or "").strip()]={o[i]:float(p[i])>0.5 for i in range(len(o))}
        except Exception: continue
    time.sleep(0.1)
rows=[]
for r in todo.itertuples():
    key=str(r.title).strip()
    if key in res and str(r.outcome) in res[key]:
        won=res[key][str(r.outcome)]
        entry=float(r.curPrice) if pd.notna(r.curPrice) else None
        if entry and 0<entry<1:
            pnl=r.paper_stake*((1-entry)/entry) if won else -r.paper_stake
            rows.append({"ts":r.ts,"wallet":r.wallet,"title":key,"outcome":r.outcome,
                         "entry":entry,"won":int(won),"pnl":round(pnl,2)})
if rows:
    pd.DataFrame(rows).to_csv(out,mode="a",header=not out.exists(),index=False)
print(f"graded {len(rows)} shadow positions ({len(todo)-len(rows)} awaiting resolution)")
