"""Whale shadow-book. Diff successive top-wallet position snapshots,
paper-copy new positions at current price; the ledger grades them at
resolution."""
import pathlib, pandas as pd, datetime
D=pathlib.Path(__file__).parent/"collected"
f=D/"pm_top_positions.csv"
if not f.exists(): print("no positions data yet"); raise SystemExit
P=pd.read_csv(f)
snaps=sorted(P["ts"].unique())
if len(snaps)<2: print(f"{len(snaps)} snapshot(s) — need 2+ to diff"); raise SystemExit
prev,cur=P[P["ts"]==snaps[-2]],P[P["ts"]==snaps[-1]]
prev_keys=set(zip(prev["wallet"],prev["title"],prev["outcome"]))
new=cur[[ (w,t,o) not in prev_keys for w,t,o in zip(cur["wallet"],cur["title"],cur["outcome"])]]
new=new[pd.to_numeric(new["size"],errors="coerce")>500]   # meaningful positions only
# MAKER-NOISE FILTER: drop wallet+title pairs holding BOTH outcomes (inventory, not opinion)
both=new.groupby(["wallet","title"])["outcome"].nunique()
maker_pairs=set(both[both>1].index)
new=new[[ (w,t) not in maker_pairs for w,t in zip(new["wallet"],new["title"])]]
# also drop if the wallet held the OTHER side in the current full snapshot
cur_pairs=cur.groupby(["wallet","title"])["outcome"].nunique()
inv=set(cur_pairs[cur_pairs>1].index)
new=new[[ (w,t) not in inv for w,t in zip(new["wallet"],new["title"])]]
led=D/"shadow_ledger.csv"
if len(new):
    out=new[["ts","wallet","title","outcome","size","curPrice"]].copy()
    out["paper_stake"]=50.0     # flat $50 paper copy per signal
    out.to_csv(led,mode="a",header=not led.exists(),index=False)
print(f"snapshots {len(snaps)} | new whale positions this diff: {len(new)}")
for r in new.head(8).itertuples():
    print(f"  {str(r.wallet)[:8]}… {r.outcome} @{r.curPrice} '{str(r.title)[:50]}'")
