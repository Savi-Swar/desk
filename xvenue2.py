"""Strict semantic Kalshi <-> Polymarket cross-venue matcher (v2).

Replaces the loose text-signature matching in kalshi_xvenue.py (which paired
e.g. a September Polymarket fed question with KXFEDDECISION-28JAN — different
meetings). Here BOTH sides are parsed into a semantic tuple

    (underlying, direction, threshold/magnitude, deadline)

and a pair matches ONLY if underlying + direction + threshold are identical
and the deadlines are within 1 day (fed: same meeting month).

Kalshi side: swept per-series from the public keyless API (series enumerated
explicitly — the bare /markets endpoint is flooded with ~40k parlay markets).
Semantics come from structured fields (strike_type, floor/cap_strike) plus the
ticker's date segment (e.g. KXETHMAXY-27JAN01-6000.00 -> deadline 2027-01-01,
above 6000; KXFEDDECISION-26SEP-H25 -> Sep-2026 meeting, hike 25bps).

Polymarket side: gamma events sweep, questions parsed by regex
("will X reach/hit/dip to $N by DATE / in MONTH", fed per-meeting decisions).

Ledger: collected/xvenue2.csv, one row per matched pair per run, with both
venues' bid/ask, executable basis in both directions, and the parsed tuples
+ a confidence tag for auditability. Cross-venue basis is still NOT a lock
(settlement sources differ: Kalshi trimmed-mean/rulebook vs UMA), so this is
a measurement ledger, not a signal.
"""
import csv
import datetime
import json
import os
import pathlib
import re
import urllib.request

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
D.mkdir(exist_ok=True)
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
GAMMA = "https://gamma-api.polymarket.com"
POLY_PAGES = int(os.environ.get("POLY_PAGES", 20))      # 100 events/page

MON = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
MON_FULL = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}

# Kalshi series with unambiguous cross-venue semantics. MAX* = one-touch
# above (Poly "reach $N"), MIN* = one-touch below (Poly "dip to $N"),
# KXFEDDECISION = per-meeting decision ladder.
KALSHI_SERIES = [
    "KXFEDDECISION",
    # annual one-touch max/min
    "KXBTCMAXY", "KXETHMAXY", "KXSOLMAXY", "KXXRPMAXY", "KXDOGEMAXY",
    "KXBNBMAXY", "KXLTCMAXY", "KXLINKMAXY", "KXAVAXMAXY", "KXZECMAXY",
    "KXHYPEMAXY", "KXNEARMAXY",
    "KXBTCMINY", "KXETHMINY", "KXSOLMINY", "KXXRPMINY", "KXDOGEMINY",
    # monthly one-touch max/min
    "KXBTCMAXMON", "KXETHMAXMON", "KXSOLMAXMON", "KXXRPMAXMON",
    "KXDOGEMAXMON", "KXBNBMAXMON", "KXHYPEMAXMON",
    "KXBTCMINMON", "KXETHMINMON", "KXSOLMINMON", "KXXRPMINMON",
    "KXDOGEMINMON",
    "KXBTCMAXM", "KXETHMAXM", "KXSOLMAXM", "KXXRPMAXM", "KXDOGEMAXM",
    "KXBTCMAXQ",
]

SERIES_ASSET = re.compile(
    r"^KX(BTC|ETH|SOL|XRP|DOGE|BNB|LTC|LINK|AVAX|ZEC|HYPE|NEAR)"
    r"(MAX|MIN)(Y|MON|M|Q)$")

POLY_ASSET = {
    "bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH",
    "solana": "SOL", "sol": "SOL", "xrp": "XRP", "ripple": "XRP",
    "dogecoin": "DOGE", "doge": "DOGE", "bnb": "BNB", "litecoin": "LTC",
    "chainlink": "LINK", "avalanche": "AVAX", "zcash": "ZEC",
    "hyperliquid": "HYPE", "hype": "HYPE", "near": "NEAR",
}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())


def ticker_date(ticker):
    """Deadline date from the ticker's YYMONDD segment (e.g. 27JAN01)."""
    m = re.search(r"-(\d{2})([A-Z]{3})(\d{2})(?=-|$)", ticker)
    if not m or m.group(2) not in MON:
        return None
    return datetime.date(2000 + int(m.group(1)), MON[m.group(2)],
                         int(m.group(3)))


def parse_kalshi(m, series):
    """-> (key, deadline, parse_str) or None.
    key: crypto ('C', asset, dir, threshold) | fed ('F', action, mag, 'YYYY-MM')
    """
    tk = m.get("ticker") or ""
    if series == "KXFEDDECISION":
        g = re.search(r"-(\d{2})([A-Z]{3})-(H|C)(0|25|26)$", tk)
        if not g:
            return None
        yr, mon = 2000 + int(g.group(1)), MON.get(g.group(2))
        if not mon:
            return None
        side, code = g.group(3), g.group(4)
        if code == "0":
            act, mag = "nochange", "0"        # "Hike by 0bps" = no change
        else:
            act = "hike" if side == "H" else "cut"
            mag = "25" if code == "25" else "50plus"   # >25bps ≡ 50+ (25bp grid)
        meet = f"{yr:04d}-{mon:02d}"
        # deadline = meeting month; represent as close date for the ±1d report
        dl = (m.get("close_time") or "")[:10]
        return (("F", act, mag, meet), dl,
                f"FED|{act}|{mag}|{meet}")
    g = SERIES_ASSET.match(series)
    if not g:
        return None
    asset, direction = g.group(1), ("up" if g.group(2) == "MAX" else "down")
    st = m.get("strike_type")
    thr = m.get("floor_strike") if st == "greater" else (
        m.get("cap_strike") if st == "less" else None)
    if thr is None:
        return None
    dl = ticker_date(tk)
    if dl is None:  # fall back to expiration date
        try:
            dl = datetime.date.fromisoformat(
                (m.get("expected_expiration_time") or "")[:10])
        except ValueError:
            return None
    thr = round(float(thr), 2)
    return (("C", asset, direction, thr), dl,
            f"{asset}|{direction}|{thr}|{dl}")


FED_Q = re.compile(
    r"will the fed (increase|decrease) interest rates by (\d+)(\+)? ?bps? "
    r"after the ([a-z]+) (\d{4}) meeting", re.I)
FED_NC = re.compile(
    r"no change in fed interest rates after the ([a-z]+) (\d{4}) meeting",
    re.I)
CRYPTO_Q = re.compile(
    r"will (" + "|".join(POLY_ASSET) + r") (reach|hit|dip to) "
    r"\$([\d,]+(?:\.\d+)?)(k)?\b(.*)", re.I)
BY_DATE = re.compile(
    r"by ([a-z]+) (\d{1,2}),? (\d{4})", re.I)


def parse_poly(q, end_date):
    """-> (key, deadline, parse_str) or None. end_date: gamma endDate str."""
    ql = (q or "").strip()
    g = FED_Q.search(ql)
    if g:
        act = "hike" if g.group(1).lower() == "increase" else "cut"
        bps, plus = g.group(2), g.group(3)
        mag = "50plus" if (plus and bps == "50") else bps
        mon = MON_FULL.get(g.group(4).lower())
        if not mon or mag not in ("25", "50plus"):
            return None
        meet = f"{int(g.group(5)):04d}-{mon:02d}"
        return ("F", act, mag, meet), meet, f"FED|{act}|{mag}|{meet}"
    g = FED_NC.search(ql)
    if g:
        mon = MON_FULL.get(g.group(1).lower())
        if not mon:
            return None
        meet = f"{int(g.group(2)):04d}-{mon:02d}"
        return ("F", "nochange", "0", meet), meet, f"FED|nochange|0|{meet}"
    g = CRYPTO_Q.search(ql)
    if g:
        asset = POLY_ASSET[g.group(1).lower()]
        direction = "down" if g.group(2).lower() == "dip to" else "up"
        thr = float(g.group(3).replace(",", "")) * (1000 if g.group(4) else 1)
        thr = round(thr, 2)
        tail = g.group(5)
        d = BY_DATE.search(tail)
        if d and MON_FULL.get(d.group(1).lower()):
            dl = datetime.date(int(d.group(3)), MON_FULL[d.group(1).lower()],
                               int(d.group(2)))
        else:
            # "in August" / no explicit date -> structured endDate
            try:
                dl = datetime.date.fromisoformat((end_date or "")[:10])
            except ValueError:
                return None
        return (("C", asset, direction, thr), dl,
                f"{asset}|{direction}|{thr}|{dl}")
    return None


def kalshi_markets():
    out = []
    for s in KALSHI_SERIES:
        cur = ""
        while True:
            u = f"{KALSHI}/markets?series_ticker={s}&status=open&limit=1000"
            if cur:
                u += f"&cursor={cur}"
            try:
                d = get(u)
            except Exception:
                break
            for m in d.get("markets", []):
                out.append((s, m))
            cur = d.get("cursor")
            if not cur:
                break
    return out


def poly_markets():
    out = []
    for off in range(0, POLY_PAGES * 100, 100):
        try:
            evs = get(f"{GAMMA}/events?closed=false&limit=100&offset={off}"
                      "&order=volume24hr&ascending=false")
        except Exception:
            break
        if not evs:
            break
        for ev in evs:
            out.extend(ev.get("markets", []))
    return out


def fnum(x):
    try:
        v = float(x)
        return v if 0.0 <= v <= 1.0 else None
    except (TypeError, ValueError):
        return None


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds")
    kidx = {}   # key -> list of (ticker, deadline, parse, bid, ask)
    kms = kalshi_markets()
    for series, m in kms:
        p = parse_kalshi(m, series)
        if not p:
            continue
        key, dl, ps = p
        kidx.setdefault(key, []).append(
            (m.get("ticker"), dl, ps,
             fnum(m.get("yes_bid_dollars")), fnum(m.get("yes_ask_dollars"))))

    pms = poly_markets()
    pairs, seen = [], set()
    for m in pms:
        q = m.get("question") or ""
        p = parse_poly(q, m.get("endDate"))
        if not p:
            continue
        key, pdl, pps = p
        for kt, kdl, kps, kb, ka in kidx.get(key, []):
            if key[0] == "F":
                conf = ("exact" if key[2] in ("25", "0")
                        else "equiv_25bp_grid")   # >25bps <-> 50+bps
            else:
                try:
                    days = abs((kdl - pdl).days)
                except TypeError:
                    continue
                if days > 1:
                    continue
                conf = "exact" if days == 0 else "deadline_1d"
            if (kt, q) in seen:
                continue
            seen.add((kt, q))
            pb, pa = fnum(m.get("bestBid")), fnum(m.get("bestAsk"))
            bsk = round(kb - pa, 4) if (kb and pa) else None  # buy PM, sell KAL
            bsp = round(pb - ka, 4) if (pb and ka) else None  # buy KAL, sell PM
            cands = [b for b in (bsk, bsp) if b is not None]
            pairs.append({
                "ts": now, "key": "|".join(str(x) for x in key),
                "kalshi": kt, "poly_q": q[:90].replace("\n", " "),
                "kalshi_parse": kps, "poly_parse": pps, "confidence": conf,
                "kalshi_bid": kb, "kalshi_ask": ka,
                "poly_bid": pb, "poly_ask": pa,
                "basis_sell_kalshi": bsk, "basis_sell_poly": bsp,
                "best_basis": max(cands) if cands else None,
            })

    if pairs:
        f = D / "xvenue2.csv"
        cols = list(pairs[0])
        new = not f.exists()
        with open(f, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            if new:
                w.writeheader()
            w.writerows(pairs)

    live = [p for p in pairs if p["best_basis"] is not None]
    print(f"xvenue2: {len(kms)} kalshi mkts in {len(KALSHI_SERIES)} series, "
          f"{len(kidx)} parsed keys; {len(pms)} poly mkts; "
          f"{len(pairs)} strict pairs ({len(live)} two-sided)")
    for p in sorted(live, key=lambda x: -x["best_basis"])[:12]:
        print(f"  {p['best_basis']*100:+5.1f}c  {p['confidence']:<15s} "
              f"{p['kalshi']:<28s} PM {p['poly_bid']}/{p['poly_ask']} "
              f"KAL {p['kalshi_bid']}/{p['kalshi_ask']}  {p['poly_q'][:45]}")


if __name__ == "__main__":
    main()
