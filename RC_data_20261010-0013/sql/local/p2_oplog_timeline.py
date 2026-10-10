#!/usr/bin/env python3
"""P2 / DR-019 / DR-025: turn results/p2_oplog_changes.csv (before/after rows of t_operation_log, allow-listed fields,
free text masked, operator masked) into one row per changed field: results/p2_oplog_timeline.csv.
新增 / 删除 give one row per object ('created' / 'deleted'). Times are UTC (operation_time)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
o = pd.read_csv(os.path.join(R, "p2_oplog_changes.csv"), dtype=str)
FIELDS = ["featureName", "toolId", "thirdLabel", "input_hasCondition", "input_period", "input_conditionExpress", "input_dimension",
          "input_counter", "input_countValue", "input_conditions", "strategyName", "status", "resultName", "execPriority", "sceneId",
          "ruleOperator", "strategyExpress", "n_rules", "rule_ids", "ruleName", "ruleFeatureId", "conditionType", "conditionValue",
          "paraName", "resultCode", "priority", "sceneName", "globalStrategyBlockStatus", "sceneBlockStatus", "vaild"]


def obj(r):
    for c in ("strategyId", "ruleId", "featureId", "paraId", "resultCode"):
        if isinstance(r.get(c), str) and r.get(c):
            return c, r[c]
    return "sceneName", r.get("sceneName")


rows = []
for (op_id, idx), g in o.groupby(["op_id", "row_idx"], sort=False):
    b = g[g.src == "before"].iloc[0].to_dict() if (g.src == "before").any() else None
    a = g[g.src == "after"].iloc[0].to_dict() if (g.src == "after").any() else None
    ref = a or b
    kind, oid = obj(ref)
    base = {"op_id": int(op_id), "operation_time_utc": ref["operation_time"].replace("T", " "), "module": ref["module"],
            "operation_type": ref["operation_type"], "object_kind": kind, "object_id": oid,
            "scene_id": ref.get("sceneId") if isinstance(ref.get("sceneId"), str) else ""}
    if b is None or a is None:
        rows.append(dict(base, field="(object)", before="" if b is None else "exists", after="" if a is None else "exists"))
        continue
    for f in FIELDS:
        vb, va = b.get(f), a.get(f)
        vb = "" if not isinstance(vb, str) else vb
        va = "" if not isinstance(va, str) else va
        if vb != va:
            rows.append(dict(base, field=f, before=vb, after=va))
t = pd.DataFrame(rows).sort_values(["operation_time_utc", "op_id"])
t.to_csv(os.path.join(R, "p2_oplog_timeline.csv"), index=False)
print(len(t), "field changes;", t.op_id.nunique(), "operations;", t.operation_time_utc.min(), "..", t.operation_time_utc.max())
for k in ("strategy_sw3jC7bvFYEX", "strategy_43NaEzJmiQFk", "strategy_bTCEWBZggaAP", "strategy_AxAlIdejVA8m", "strategy_NrsClIxvGxWc",
          "feature_dqBHKec09Wwa", "feature_AemrK847uPtt", "feature_e1Kmz7JqzsWc", "strategy_tO7DZkJ1g0C2"):
    x = t[t.object_id == k]
    print("==", k); print(x[["operation_time_utc", "operation_type", "field", "before", "after"]].to_string(index=False)[:1500])
