"""Deadline-relations scanner with a wording-nesting guard.

Two markets on the same subject with different deadlines are logically
nested: "X by July" implies "X by August", so YES(July) can never be worth
more than YES(August). When bid(earlier) > ask(later) + fees there is a
lock: sell the earlier, buy the later.

The trap (MSTR May/June 2026): two markets look nested by calendar but
resolve on different *criteria* — the May leg lost when a June-1 filing
disclosed a May event. So a candidate is only emitted if it passes a
nesting guard:

  - same subject stem (title with the date phrase removed must match)
  - earlier deadline strictly before later
  - negation parity (both positive or both negated — "NOT by later"
    implies "NOT by earlier", the reverse direction)
  - resolution-source agreement where the description exposes it

Anything that fails the guard is logged to relations_rejected.csv with the
reason, never to the tradable ledger. Locks go to collected/relations.csv.
This is measurement only — deadline locks tie capital up for months, so
they are paper-flagged, not executed.
"""
import datetime
import json
import os
import pathlib
import re
import urllib.request
from collections import defaultdict

import pandas as pd

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
MIN_LOCK = float(os.environ.get("MIN_LOCK", 0.01))

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}
DATE_RE = re.compile(
    r"\b(?:by|before|in|on|through)\s+(january|february|march|april|may|june|"
    r"july|august|september|october|november|december)\s*(\d{1,2})?,?\s*(\d{4})?",
    re.I)
NEG_RE = re.compile(r"\b(not|no|won'?t|fail|without)\b", re.I)


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def parse(q):
    """Return (subject_stem, (y,m,d), negated) or None."""
    m = DATE_RE.search(q or "")
    if not m:
        return None
    mon = MONTHS[m.group(1).lower()]
    day = int(m.group(2)) if m.group(2) else 28
    year = int(m.group(3)) if m.group(3) else 2026
    stem = DATE_RE.sub(" <DL> ", q).lower()
    stem = re.sub(r"[^a-z0-9<> ]", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    negated = bool(NEG_RE.search(q or ""))
    return stem, (year, mon, day), negated


def res_source(m):
    d = (m.get("description") or "").lower()
    for key in ("coingecko", "coinbase", "binance", "espn", "ap ", "reuters",
                "official", "sec filing", "press release"):
        if key in d:
            return key
    return ""


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    evs = []
    for off in (0, 100, 200, 300, 400):
        try:
            evs += get("https://gamma-api.polymarket.com/events?closed=false"
                       f"&limit=100&offset={off}")
        except Exception:
            break

    fam = defaultdict(list)
    for ev in evs:
        for m in ev.get("markets", []):
            p = parse(m.get("question"))
            if not p:
                continue
            stem, dl, neg = p
            try:
                bid = float(m.get("bestBid") or 0)
                ask = float(m.get("bestAsk") or 0)
            except (TypeError, ValueError):
                continue
            if not (0 < ask <= 1):
                continue
            # a real, quoted book on both sides; an ask defaulting to 1 or a
            # bid at 0 means an empty book — the illiquidity mirage, not a leg
            if ask >= 0.999 or bid <= 0.001:
                continue
            fam[(stem, neg)].append({
                "dl": dl, "bid": bid, "ask": ask,
                "q": (m.get("question") or "")[:60], "src": res_source(m)})

    locks, rejects = [], []
    for (stem, neg), legs in fam.items():
        if len({l["dl"] for l in legs}) < 2:
            continue
        legs.sort(key=lambda l: l["dl"])
        for i in range(len(legs)):
            for j in range(i + 1, len(legs)):
                early, late = legs[i], legs[j]
                if early["dl"] == late["dl"]:
                    continue
                # nesting: for positive events YES(early) <= YES(late), so a
                # lock is bid(early) > ask(late). Negated reverses which side.
                if not neg:
                    gross = early["bid"] - late["ask"]
                    sell_q, buy_q = early, late
                else:
                    gross = late["bid"] - early["ask"]
                    sell_q, buy_q = late, early
                if gross < MIN_LOCK:
                    continue
                # guard: resolution-source disagreement is the MSTR trap
                if early["src"] and late["src"] and early["src"] != late["src"]:
                    rejects.append({"ts": now, "reason": "res_source_mismatch",
                                    "gross": round(gross, 3),
                                    "a": sell_q["q"], "b": buy_q["q"],
                                    "src_a": early["src"], "src_b": late["src"]})
                    continue
                locks.append({
                    "ts": now, "stem": stem[:40], "negated": int(neg),
                    "gross_lock": round(gross, 4),
                    "sell": sell_q["q"], "sell_bid": sell_q["bid"],
                    "buy": buy_q["q"], "buy_ask": buy_q["ask"],
                    "lockup_days": (late["dl"][0]-early["dl"][0])*365
                                   + (late["dl"][1]-early["dl"][1])*30,
                })

    if locks:
        f = D / "relations.csv"
        pd.DataFrame(locks).to_csv(f, mode="a", header=not f.exists(), index=False)
    if rejects:
        f = D / "relations_rejected.csv"
        pd.DataFrame(rejects).to_csv(f, mode="a", header=not f.exists(), index=False)

    print(f"relations: {len(fam)} deadline families, {len(locks)} guarded locks, "
          f"{len(rejects)} rejected by guard")
    for l in sorted(locks, key=lambda x: -x["gross_lock"])[:8]:
        print(f"  lock {l['gross_lock']*100:.1f}c ({l['lockup_days']}d capital) "
              f"SELL '{l['sell'][:34]}' @ {l['sell_bid']:.2f} / "
              f"BUY '{l['buy'][:34]}' @ {l['buy_ask']:.2f}")


if __name__ == "__main__":
    main()
