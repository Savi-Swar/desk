"""Nightly: grade shadow-ledger entries against resolved markets (exact-title
match on recently-closed gamma markets). Appends verdicts to shadow_graded.csv."""
import datetime, pathlib
import pandas as pd
from gamma_resolved import resolved_between
D=pathlib.Path(__file__).parent/"collected"
led=D/"shadow_ledger.csv"; out=D/"shadow_graded.csv"
if not led.exists(): print("no ledger"); raise SystemExit
L=pd.read_csv(led)
done=set()
if out.exists():
    G=pd.read_csv(out); done=set(zip(G["ts"],G["title"],G["outcome"]))
todo=L[[ (t,ti,o) not in done for t,ti,o in zip(L["ts"],L["title"],L["outcome"])]]
if not len(todo): print("nothing to grade"); raise SystemExit
# resolved markets over the ledger's span, title->outcome map
first=pd.to_datetime(L["ts"],format="mixed",utc=True).min().date().isoformat()
today=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
res=resolved_between(f"{first}T00:00:00Z",f"{today}T23:59:59Z")
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
