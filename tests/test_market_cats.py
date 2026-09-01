"""Contamination regressions for market_cats.cat_of — substring collisions
that actually bit (uk-RAIN-e, miami-HEAT, treasury yield, pewdiepie viEWS).
Extends the basic smoke in run_all.py. Pure stdlib, no I/O."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

from market_cats import cat_of


def test_contamination():
    cases = [
        # "ukraine" contains "rain": must NOT trip the weather rules
        ("will-ukraine-regain-territory-in-2026", "geopolitics"),
        ("ukraine-drone-strikes-in-march", "geopolitics"),
        # "miami-heat" contains "heat": NOT weather (heatwave/heat-wave only)
        ("miami-heat-vs-boston-celtics", "sports"),
        # treasury yield is econ, and nothing in it may leak to sports
        ("will-the-treasury-yield-hit-4pt5", "econ"),
        ("10-year-treasury-yield-above-4pt5-in-2026", "econ"),
    ]
    for slug, want in cases:
        got = cat_of(slug)
        assert got == want, f"cat_of({slug!r}) = {got!r}, want {want!r}"
    # "views" contains "vs": must NOT trip the sports "-vs-" rule.
    # (pewdiepie has no rule of his own; anything but sports/weather is fine.)
    got = cat_of("pewdiepie-hits-1-billion-views")
    assert got not in ("sports", "weather"), f"views leaked to {got!r}"
    print("  market_cats contamination: ukraine/heat/treasury/views OK")


def test_precedence_and_default():
    # first-hit-wins ordering: esports beats sports even with sporty words
    assert cat_of("lol-t1-vs-geng-finals") == "esports"
    # crypto beats econ ("bitcoin-etf" has both flavors)
    assert cat_of("bitcoin-etf-approved") == "crypto"
    # nothing matches -> other, and empty input is safe
    # (n.b. "unmatched"/"rematch" would hit the sports key "match" — that
    # contamination is live, so pick a genuinely unmatched slug here)
    assert cat_of("zebra-crossing-painted-purple") == "other"
    assert cat_of("", "") == "other"
    # question text participates, not just the slug
    assert cat_of("", "Will the highest temperature in NYC exceed 90 degrees?") == "weather"
    print("  market_cats precedence/default: OK")


if __name__ == "__main__":
    test_contamination()
    test_precedence_and_default()
    print("test_market_cats: PASS")
