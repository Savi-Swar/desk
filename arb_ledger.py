"""Shared schema for collected/arb_fills.csv.

Several samplers append to the same ledger (arb_watch, arb_executor_sim) and
they carry different extra fields. Appending with `header=not f.exists()`
silently writes those extras positionally, so a row from one writer lands
under another writer's column names. Every writer goes through append_fills()
instead, which reindexes to one canonical column order.
"""
import pathlib

import pandas as pd

COLUMNS = ["ts", "event", "type", "edge_pershare", "exec_size",
           "profit_at_depth", "n_legs", "near_res", "persist_min", "peak_edge"]


def append_fills(rows, path):
    """Append rows (list of dicts or DataFrame) under the canonical schema."""
    df = pd.DataFrame(rows)
    if df.empty:
        return
    f = pathlib.Path(path)
    df = df.reindex(columns=COLUMNS)
    fresh = not f.exists() or f.stat().st_size == 0
    df.to_csv(f, mode="a", header=fresh, index=False)
