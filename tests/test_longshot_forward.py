"""Unit tests for longshot_forward: grade() outcome joins and summarize()
edge arithmetic. Pure stdlib; network stubbed, ledger is a temp CSV."""
import csv
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import longshot_forward as lf


def _ledger_row(mid, end, graded="0", won="", no_ask="0.80"):
    return {"t": "1.0", "market_id": mid, "conditionId": "c" + mid,
            "slug": "s-" + mid, "endDate": end, "p_last": "0.10",
            "yes_bid": "0.05", "yes_ask": "0.20", "no_bid": "0.75",
            "no_ask": no_ask, "no_ask_size": "100", "volume": "9000",
            "graded": graded, "won_no": won}


def test_grade():
    past, future = "2026-01-01T00:00:00Z", "2099-01-01T00:00:00Z"
    rows = [
        _ledger_row("10", past),            # due, NO wins (winner_idx 1)
        _ledger_row("11", past),            # due, YES wins (winner_idx 0)
        _ledger_row("12", past),            # due but market still ambiguous
        _ledger_row("13", future),          # not due yet
        _ledger_row("14", past, graded="1", won="1"),   # already graded
    ]
    finals = {"10": '["0", "1"]', "11": '["1", "0"]', "12": '["0.5", "0.5"]'}
    fetched = []

    def fake_get(url, tries=3):
        mid = url.rstrip("/").rsplit("/", 1)[-1]
        fetched.append(mid)
        return {"outcomePrices": finals.get(mid, "[]")}

    with tempfile.TemporaryDirectory() as td:
        out = pathlib.Path(td) / "longshot_fwd.csv"
        grades = pathlib.Path(td) / "longshot_fwd_grades.csv"
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=lf.FIELDS)
            w.writeheader()
            w.writerows(rows)
        # market 14 already graded in the append-only grades ledger
        with grades.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["market_id", "won_no", "graded_at"])
            w.writerow(["14", "1", "0"])
        old = lf.OUT, lf.GRADES, lf.get, lf.time.sleep
        lf.OUT, lf.GRADES, lf.get, lf.time.sleep =             out, grades, fake_get, lambda s: None
        try:
            graded, got = lf.grade()
            gmap = lf.load_grades()
        finally:
            lf.OUT, lf.GRADES, lf.get, lf.time.sleep = old

    assert graded == 2, f"graded {graded}, want 2"
    assert sorted(fetched) == ["10", "11", "12"], fetched  # only due+ungraded hit
    # winner_idx 1 (YES loses) -> NO won; winner_idx 0 -> NO lost
    assert gmap["10"] == "1", gmap
    assert gmap["11"] == "0", gmap
    # ambiguous final not appended; already-graded untouched; not-due absent
    assert "12" not in gmap and "13" not in gmap
    assert gmap["14"] == "1"
    print("  longshot_forward.grade: append-only grades + due filter OK")


def test_grade_no_ledger():
    old = lf.OUT
    lf.OUT = pathlib.Path(tempfile.gettempdir()) / "nope_longshot_fwd_x.csv"
    try:
        graded, rows = lf.grade()
    finally:
        lf.OUT = old
    assert graded == 0 and rows == []
    print("  longshot_forward.grade: missing ledger -> (0, []) OK")


def test_summarize():
    past = "2026-01-01T00:00:00Z"
    # 25 graded fills at ask 0.75: 24 NO wins (+0.25 each), 1 loss (-0.75)
    # mean pnl = (24*0.25 - 0.75) / 25 = 0.21 -> +21.00c/share
    rows = [_ledger_row(str(i), past, graded="1",
                        won="1" if i < 24 else "0", no_ask="0.75")
            for i in range(25)]
    s = lf.summarize(rows)
    assert "25 trades" in s and "+21.00c/share" in s, s

    # asks outside [0.5, 0.99] are excluded from the priced set
    rows2 = rows + [_ledger_row("98", past, graded="1", won="1", no_ask="0.30"),
                    _ledger_row("99", past, graded="1", won="1", no_ask="0.995")]
    s2 = lf.summarize(rows2)
    assert "25 trades" in s2 and "+21.00c/share" in s2, s2

    # under 20 graded -> explicit "need more" message, no fake number
    s3 = lf.summarize(rows[:5])
    assert "graded 5" in s3 and "c/share" not in s3, s3

    # graded but no live ask recorded -> not countable
    rows4 = [_ledger_row(str(i), past, graded="1", won="1", no_ask="")
             for i in range(25)]
    s4 = lf.summarize(rows4)
    assert "need" in s4 or "no priceable" in s4, s4
    print("  longshot_forward.summarize: edge math + ask filters OK")


if __name__ == "__main__":
    test_grade()
    test_grade_no_ledger()
    test_summarize()
    print("test_longshot_forward: PASS")
