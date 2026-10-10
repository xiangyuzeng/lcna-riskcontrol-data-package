#!/usr/bin/env python3
"""Check an EXPLAIN result (results/<name>.csv) before a business-schema query runs: every table must be read through an
index (type range/ref/eq_ref/const) or be small (< 20000 estimated rows). Exit 1 = do not run (record 未能获取：会扫全表)."""
import sys
import pandas as pd
d = pd.read_csv(sys.argv[1])
bad = d[(~d["type"].isin(["range", "ref", "eq_ref", "const", "index_merge"])) & (pd.to_numeric(d["rows"], errors="coerce").fillna(0) >= 20000)]
print(d[["table", "type", "key", "rows"]].to_string(index=False))
sys.exit(1 if len(bad) else 0)
