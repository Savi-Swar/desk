"""Grades the three desk ledgers against resolved outcomes + reports state.
Arb: sum realized profit_at_depth. Shadow: grade closed positions vs
resolution (needs market resolution lookup). Maker: reward accrual estimate
minus adverse-selection cost (quote crossed by later mid move)."""
import pathlib, json, urllib.request
import pandas as pd, numpy as np
UA={"User-Agent":"research saviswarup@gmail.com"}
D=pathlib.Path(__file__).parent/"collected"
def load(n):
    f=D/n
    return pd.read_csv(f) if f.exists() else pd.DataFrame()

print("="*56)
print("THE DESK — status", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))
print("="*56)

# 1. ARB
a=load("arb_fills.csv")
if len(a):
    print(f"\n[1] ARB EXECUTOR-SIM: {len(a)} depth-verified fills logged")
    print(f"    total realized-at-depth profit: ${a['profit_at_depth'].sum():.2f}")
    print(f"    median fill size: {a['exec_size'].median():.0f} shares | median edge {a['edge_pershare'].median()*100:.1f}c")
else:
    print("\n[1] ARB: 0 depth-verified fills yet (summary edges dying at real books — the expected early signal)")

# 2. SHADOW (whale copy)
s=load("shadow_ledger.csv")
if len(s):
    print(f"\n[2] WHALE SHADOW-BOOK: {len(s)} paper-copied positions")
    print(f"    unique whales tracked: {s['wallet'].nunique()} | paper capital deployed: ${s['paper_stake'].sum():.0f}")
    print("    (grades at resolution — accruing; verdict needs ~6-8 wks)")
    g=load("shadow_graded.csv")
    if len(g):
        print(f"    GRADED so far: {len(g)} | P&L ${g['pnl'].sum():+.0f} | hit {g['won'].mean():.0%}")
        byw=g.groupby("wallet").agg(n=("won","size"),hit=("won","mean"),pnl=("pnl","sum"))
        byw=byw[byw["n"]>=5].sort_values("pnl",ascending=False)
        if len(byw): print("    wallet skill board (n>=5):"); print(byw.round(2).to_string())
else:
    print("\n[2] SHADOW: no copies logged yet")

# 2b. MAKER NET (v2)
mn=load("maker_net.csv")
if len(mn):
    print(f"\n[2b] MAKER NET SIM: rewards ${mn['reward'].sum():.2f} + fills ${mn['fill_pnl'].sum():+.2f} = NET ${mn['reward'].sum()+mn['fill_pnl'].sum():+.2f} ({(mn['event']!='').mean():.0%} adverse)")

# 3. MAKER
m=load("maker_book.csv")
if len(m):
    latest=m[m["ts"]==m["ts"].max()]
    print(f"\n[3] MAKER PAPER-QUOTER: {len(latest)} eligible markets last snapshot")
    print(f"    combined reward pool: ${latest['reward_daily'].sum():,.0f}/day across all quoters")
    # adverse selection proxy: for repeat markets, did mid move > our_spread?
    if m["ts"].nunique()>=2:
        piv=m.sort_values("ts").groupby("q").agg(first_mid=("mid","first"),last_mid=("mid","last"),sp=("our_spread","mean"))
        piv["crossed"]=(piv["last_mid"]-piv["first_mid"]).abs()>piv["sp"]
        print(f"    adverse-selection check: {piv['crossed'].mean():.0%} of quotes would have been run over by mid drift")
else:
    print("\n[3] MAKER: no snapshots yet")
print("\n" + "="*56)
