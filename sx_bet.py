"""SX Bet snapshot collector.

SX Bet is a keyless on-chain sports betting exchange. Whether cross-venue
sports arb (SX Bet vs Polymarket vs a sharp book) is reachable after fees is
an open research question; single-venue Polymarket sports arb was measured
fee-negative. So this only SNAPSHOTS the surface — sport, league, teams,
line, and best two-way prices — so a matched dataset exists if the research
says go. No arb claimed. Output: collected/sx_markets.csv.
"""
import datetime
import json
import os
import pathlib
import urllib.request

import pandas as pd

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
OUT = D / "sx_markets.csv"


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    try:
        ms = get("https://api.sx.bet/markets/active")["data"]["markets"]
    except Exception as e:
        print("sx_bet: fetch failed", type(e).__name__)
        return
    rows = []
    for m in ms:
        rows.append({
            "ts": now, "sport": m.get("sportLabel"), "league": m.get("leagueLabel"),
            "team1": m.get("teamOneName"), "team2": m.get("teamTwoName"),
            "outcome1": m.get("outcomeOneName"), "outcome2": m.get("outcomeTwoName"),
            "line": m.get("line"), "type": m.get("type"),
            "market_hash": m.get("marketHash"),
        })
    if rows:
        pd.DataFrame(rows).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
    import collections
    sports = collections.Counter(r["sport"] for r in rows)
    print(f"sx_bet: {len(rows)} active markets | {dict(sports.most_common(5))}")


if __name__ == "__main__":
    main()
