#!/usr/bin/env python3
"""Merge the L1 parts (_local_only/raw/l1_*.csv.gz, counts only) into results/l1_long.csv after the runner's privacy check,
and write one consolidated SQL file sql/l1_long.sql (the per-week runner copies are folded into it)."""
import glob, os, re, sys
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PKG, "toolkit"))
from shard_runner import unsafe_cells  # noqa: E402

parts = sorted(glob.glob(os.path.join(PKG, "_local_only", "raw", "l1_*.csv.gz")))
d = pd.concat([pd.read_csv(p, dtype={"cc": str, "shard": str}) for p in parts], ignore_index=True)
bad = unsafe_cells(d.drop(columns=["n", "n_phones"]).astype(str).to_dict("records"))
if bad:
    raise SystemExit(f"refusing to merge L1: {sorted(bad)}")
d.to_csv(os.path.join(PKG, "results", "l1_long.csv"), index=False)
sqls = sorted(glob.glob(os.path.join(PKG, "sql", "l1_2026*.sql")))
if sqls:
    heads = []
    for p in sqls:
        t = open(p, encoding="utf-8").read()
        heads.append("\n".join(l for l in t.splitlines() if l.startswith("-- ") and re.match(r"-- (name|kind|run)", l)))
    body = open(sqls[0], encoding="utf-8").read().split("\n\n", 1)[1]
    open(os.path.join(PKG, "sql", "l1_long.sql"), "w", encoding="utf-8").write(
        "-- L1 long aggregate: the runner executed this template once per 7 NY days (8 shards per statement); runs:\n"
        + "\n".join(heads) + "\n\n" + body)
    for p in sqls:
        os.remove(p)
print(f"L1 parts={len(parts)} rows={len(d)} days={d.ny_date.nunique()} n_total={int(d[d.lvl == 'h'].n.sum())}")
