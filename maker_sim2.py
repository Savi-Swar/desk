"""Maker-sim v2: NET verdict. Simulated book across snapshots:
- We quote mid±our_spread in eligible markets (from maker_book.csv history).
- Fill detection: if next snapshot's mid crossed our old quote, we got filled
  at the quote (adverse flow); position marked to latest mid.
- Reward accrual: conservative share = score_proxy * daily_rate * SHARE_CAP
  per snapshot interval. NET = rewards + spread-capture - inventory losses."""
import pathlib, pandas as pd, numpy as np
D=pathlib.Path(__file__).parent/"collected"
f=D/"maker_book.csv"
if not f.exists(): print("no maker data"); raise SystemExit
M=pd.read_csv(f)
snaps=sorted(M["ts"].unique())
if len(snaps)<2: print(f"{len(snaps)} snapshot(s) — v2 needs 2+; accruing"); raise SystemExit
SHARE_CAP=0.02   # assume we capture max 2% of a market's reward pool (small quoter)
QUOTE_SIZE=100.0 # $100 notional per side
res=[]
for i in range(len(snaps)-1):
    a=M[M["ts"]==snaps[i]].set_index("q"); b=M[M["ts"]==snaps[i+1]].set_index("q")
    common=a.index.intersection(b.index)
    hours=max((pd.to_datetime(snaps[i+1])-pd.to_datetime(snaps[i])).total_seconds()/3600,0.5)
    for q in common:
        m0,m1=a.loc[q,"mid"],b.loc[q,"mid"]
        sp=a.loc[q,"our_spread"]; rate=a.loc[q,"reward_daily"]; score=a.loc[q,"score_proxy"]
        reward=rate*SHARE_CAP*score*(hours/24)
        pnl_fill=0.0; filled=""
        if m1>m0+sp/2:   # mid rose through our ask -> we sold at m0+sp/2, mark loss
            pnl_fill=-(m1-(m0+sp/2))*QUOTE_SIZE; filled="ask-run"
        elif m1<m0-sp/2: # mid fell through our bid -> we bought, mark loss
            pnl_fill=-((m0-sp/2)-m1)*QUOTE_SIZE; filled="bid-run"
        else:            # both quotes survived: assume one round-trip capture of half-spread
            pnl_fill=sp/2*QUOTE_SIZE*0.25   # conservative: 25% chance of benign two-way flow
        res.append({"t0":snaps[i],"q":q,"reward":reward,"fill_pnl":pnl_fill,"event":filled})
R=pd.DataFrame(res)
out=D/"maker_net.csv"; R.to_csv(out,index=False)
print(f"maker v2: {len(R)} market-intervals across {len(snaps)} snapshots")
print(f"reward accrual ${R['reward'].sum():.2f} | fill/spread pnl ${R['fill_pnl'].sum():+.2f} | NET ${R['reward'].sum()+R['fill_pnl'].sum():+.2f}")
print(f"adverse runs: {(R['event']!='').mean():.0%} of intervals")
