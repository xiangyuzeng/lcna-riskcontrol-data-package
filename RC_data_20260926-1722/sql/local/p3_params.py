#!/usr/bin/env python3
"""P3: derive the feature / rule ID lists the E1 extract needs from the exported config (no DB reads, no hardcoded IDs).
  rc_ids        : features computed by the reCAPTCHA tool (any version) -> score taken by shape from their apiResp
  counter_ids   : features computed by the counter tool (status code + value per request)
  time_rule_ids : rules that compare a time of day (condition_type TIME_AFTER / TIME_BEFORE)
  cond_ids      : counter features with real filter conditions or a combined dimension now, or with a condition at any
                  time in t_operation_log (DR-003 standing list; `conditions: [""]` is an empty placeholder, not a condition)
Writes _local_only/p3_params.env (shell-sourceable) and results/p3_param_lists.csv."""
import json, os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
tf, tool, rule = (pd.read_csv(os.path.join(R, f)) for f in ("config_third_feature.csv", "config_tool.csv", "config_rule.csv"))
rc_tools = set(tool[tool.tool_classpath.fillna("").str.contains("Recaptcha", case=False)].tool_id)
cnt_tools = set(tool[tool.tool_classpath.fillna("").str.contains("Counter", case=False)].tool_id)
rc = sorted(tf[tf.tool_id.isin(rc_tools)].feature_id)
cnt = tf[tf.tool_id.isin(cnt_tools)].copy()
tr = sorted(rule[rule.condition_type.isin(["TIME_AFTER", "TIME_BEFORE"])].rule_id)

def cond_or_combo(s):
    try:
        j = json.loads(s)
    except Exception:
        return None
    dim = j.get("dimension")
    combo = isinstance(dim, list) and len(dim) > 1 or (isinstance(dim, str) and "|" in dim)
    real_conditions = [c for c in (j.get("conditions") or []) if str(c).strip()]   # [""] is the UI's empty placeholder
    return j.get("hasCondition") is True or bool(real_conditions) or combo

cnt["cond_or_combo"] = cnt.input_paras.map(cond_or_combo)
# plus counter features that had a condition at any time in the change log (incl. features deleted since)
op = pd.read_csv(os.path.join(R, "p2_oplog_changes.csv"))
op_cond = set(op[(op.toolId.isin(cnt_tools)) & (op.input_hasCondition.astype(str) == "True")].featureId.dropna())
op_counters = set(op[op.toolId.isin(cnt_tools)].featureId.dropna())
cond = sorted(set(cnt[cnt.cond_or_combo == True].feature_id) | op_cond)
cnt_all = sorted(set(cnt.feature_id) | op_counters)
q = lambda ids: ",".join(f"'{i}'" for i in ids)
with open(os.path.join(PKG, "_local_only", "p3_params.env"), "w") as fh:
    fh.write(f'RC_IDS="{q(rc)}"\nCOUNTER_IDS="{q(cnt_all)}"\nTIME_RULE_IDS="{q(tr)}"\nCOND_IDS="{q(cond)}"\n')
rows = [{"list": n, "n_ids": len(v), "ids": " ".join(v)} for n, v in
        (("rc_ids", rc), ("counter_ids (config + change log)", cnt_all), ("time_rule_ids", tr), ("cond_or_combo_counter_ids", cond))]
pd.DataFrame(rows).to_csv(os.path.join(R, "p3_param_lists.csv"), index=False)
for r in rows:
    print(r["list"], r["n_ids"])
