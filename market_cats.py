"""Market category from slug/question text.

Gamma stopped populating `category` years ago (only ~4k of 450k+ resolved
markets carry one), so studies derive it from text. Rules ordered specific ->
general; first hit wins. Returns one of:
crypto, sports, esports, politics, econ, geopolitics, culture, weather, other.
"""
RULES = [
    ("esports", ("lol-", "dota", "cs2", "csgo", "counter-strike", "valorant",
                 "league-of-legends", "esports", "map 1", "map 2")),
    ("crypto", ("bitcoin", "btc", "ethereum", "eth-", "solana", "xrp", "doge",
                "crypto", "up-or-down", "what-price-will", "fdv", "token",
                "coin", "nft", "opensea", "superrare", "defi", "tvl",
                "uniswap", "sushiswap", "aave", "yfi", "dao-", "airdrop",
                "binance", "coinbase", "staking", "chainlink")),
    ("weather", ("temperature", "highest-temp", "rainfall", "snowfall",
                 "inches-of-rain", "inches-of-snow", "-rain-", "-snow-",
                 "hurricane", "heatwave", "heat-wave", "weather", "degrees")),
    ("econ", ("fed-", "fed decision", "rate-cut", "rate-hike", "interest-rate",
              "cpi", "inflation", "gdp", "jobs-report", "recession", "treasury", "yield",
              "tariff", "stock", "s&p", "nasdaq", "ipo")),
    ("geopolitics", ("iran", "israel", "ukraine", "russia", "ceasefire",
                     "hormuz", "gaza", "nato", "invasion", "airspace",
                     "north-korea", "taiwan")),
    ("politics", ("election", "president", "senate", "congress", "governor",
                  "primary", "nominee", "impeach", "supreme-court", "mayor",
                  "parliament", "minister", "chancellor", "veto", "cabinet",
                  "confirmation", "midterm", "poll", "approval-rating",
                  "signed-into-law", "executive-order", "trump", "biden",
                  "kamala", "harris-", "obama", "desantis", "newsom", "vance",
                  "aoc-", "pardon", "government-shutdown", "white-house")),
    ("sports", ("nba", "nfl", "mlb", "nhl", "ufc", "premier-league", "epl",
                "champions-league", "la-liga", "serie-a", "bundesliga",
                "world-cup", "olympic", "grand-slam", "wimbledon", "f1-",
                "grand-prix", "boxing", "tennis", "golf", "super-bowl",
                "playoffs", "finals", "-win-on-", "spread:", "over/under",
                "total-rounds", "uel-", "ucl-", "chess", "poker",
                "match", "-draw", "btts", "matchup", "superbowl",
                "super-bowl", "beat-", "-beat", "wnba", "ncaa", "cwbb",
                "cbb-", "knockout", "relegat", "double-header", "totals",
                "-vs-")),
    ("culture", ("tweet", "musk-", "kardashian", "taylor-swift", "movie",
                 "box-office", "album", "grammy", "oscar", "spotify",
                 "youtube", "tiktok", "ronaldo", "messi-", "wedding",
                 "divorce", "time-person", "ballon-dor")),
]


def cat_of(slug="", question=""):
    text = f"{slug} {question}".lower()
    for cat, keys in RULES:
        if any(k in text for k in keys):
            return cat
    return "other"


def _validate():
    """coverage + agreement with the (ancient) labeled rows."""
    import csv
    import gzip
    import pathlib
    from collections import Counter
    D = pathlib.Path(__file__).parent / "data"
    dist = Counter()
    agree = tot = 0
    MAP = {"Sports": "sports", "NBA Playoffs": "sports", "Chess": "sports",
           "Poker": "sports", "Olympics": "sports", "Crypto": "crypto",
           "NFTs": "crypto", "US-current-affairs": "politics",
           "Global Politics": "politics", "Ukraine & Russia": "geopolitics",
           "Pop-Culture": "culture", "Business": "econ"}
    for fn in ("resolved_markets.csv.gz", "resolved_tail.csv.gz"):
        p = D / fn
        if not p.exists():
            continue
        try:
            for r in csv.DictReader(gzip.open(p, "rt")):
                c = cat_of(r.get("slug", ""), r.get("question", ""))
                dist[c] += 1
                want = MAP.get((r.get("category") or "").strip())
                if want:
                    tot += 1
                    agree += (c == want)
        except (EOFError, OSError):
            pass
    n = sum(dist.values())
    print(f"classified {n:,}: " +
          ", ".join(f"{c} {v/n:.0%}" for c, v in dist.most_common()))
    if tot:
        print(f"agreement with {tot:,} legacy labels: {agree/tot:.0%}")


if __name__ == "__main__":
    _validate()
