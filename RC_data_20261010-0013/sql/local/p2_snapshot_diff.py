#!/usr/bin/env python3
"""P2: compare config snapshot #1 (results/config_*.csv, start of the DB phase) with snapshot #2 (results/s2_*.csv, end of the DB
phase) and list t_operation_log entries made between them. Output results/p2_snapshot_diff.csv (IDs, fields, times; free text as
exported, i.e. already masked)."""
import os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n), dtype=str)
KEY = {"config_strategy": "strategy_id", "config_rule": "rule_id", "config_strategy_relation": "id", "config_third_feature": "feature_id"}
rows = []
for t, k in KEY.items():
    a, b = rd(f"{t}.csv").set_index(k), rd(f"s2_{t}.csv").set_index(k)
    for x in sorted(set(b.index) - set(a.index)):
        rows.append({"table": t, "object_id": x, "change": "new in snapshot #2", "field": "", "snapshot_1": "", "snapshot_2": ""})
    for x in sorted(set(a.index) - set(b.index)):
        rows.append({"table": t, "object_id": x, "change": "gone in snapshot #2", "field": "", "snapshot_1": "", "snapshot_2": ""})
    for x in sorted(set(a.index) & set(b.index)):
        for c in [c for c in a.columns if c in b.columns]:
            va, vb = a.at[x, c], b.at[x, c]
            if not (pd.isna(va) and pd.isna(vb)) and str(va) != str(vb):
                rows.append({"table": t, "object_id": x, "change": "changed", "field": c, "snapshot_1": va, "snapshot_2": vb})
o1, o2 = rd("p2_oplog_changes.csv"), rd("s2_p2_oplog_changes.csv")
new_ops = sorted(set(o2.op_id) - set(o1.op_id))
for op in new_ops:
    r = o2[o2.op_id == op].iloc[0]
    rows.append({"table": "t_operation_log", "object_id": op, "change": "operation after snapshot #1", "field": r.get("module", ""),
                 "snapshot_1": "", "snapshot_2": r.get("operation_time", "")})
out = pd.DataFrame(rows, columns=["table", "object_id", "change", "field", "snapshot_1", "snapshot_2"])
out.to_csv(os.path.join(R, "p2_snapshot_diff.csv"), index=False)
print(f"differences: {len(out)}; new operations: {len(new_ops)}")
print(out.head(30).to_string(index=False))
