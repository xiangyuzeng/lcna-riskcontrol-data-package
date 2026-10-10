#!/usr/bin/env python3
"""P2: join the exported config tables into analysis-ready views (no new DB reads).

Inputs : results/config_strategy.csv, config_strategy_relation.csv, config_rule.csv, config_third_feature.csv,
         config_list_feature.csv, config_tool.csv, config_scene.csv, p2_hits_7d.csv, p2_list_counts.csv
Outputs: results/config_strategy_expanded.csv   one row per strategy x rule (rule -> feature / parameter)
         results/config_fixed_strategies_check.csv   per enabled scene: cid702-PASS / whitelist-PASS / blacklist-REJECT present?
         results/config_counter_features.csv   counter-feature definitions (period, counter, dimension, countValue, conditions)
         results/config_status_vs_hits.csv   config status x hit-element status (7-day LKUS_push hits)
"""
import json, os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n))

s, rel, rule = rd("config_strategy.csv"), rd("config_strategy_relation.csv"), rd("config_rule.csv")
tf, lf, tool, scene = rd("config_third_feature.csv"), rd("config_list_feature.csv"), rd("config_tool.csv"), rd("config_scene.csv")

fname = dict(zip(tf.feature_id, tf.feature_name)) | dict(zip(lf.feature_id, lf.feature_name))
ftool = dict(zip(tf.feature_id, tf.tool_id))
tname = dict(zip(tool.tool_id, tool.tool_name))
x = s.merge(rel[["strategy_id", "rule_id"]], on="strategy_id", how="left") \
     .merge(rule[["rule_id", "rule_name", "status", "feature_type", "feature_id", "condition_type", "condition_value", "rule_express", "update_time"]]
            .rename(columns={"status": "rule_status", "update_time": "rule_update_time"}), on="rule_id", how="left")
x["feature_name"] = x.feature_id.map(fname)
x["feature_kind"] = x.feature_id.map(lambda f: "list" if f in set(lf.feature_id) else (tname.get(ftool.get(f), "third") if f in ftool else ("parameter" if isinstance(f, str) else None)))
cols = ["scene_id", "strategy_id", "strategy_name", "status", "result_code", "exec_priority", "rule_operator", "strategy_express",
        "strategy_type", "description", "operator", "update_time", "rule_id", "rule_name", "rule_status", "feature_type", "feature_id",
        "feature_kind", "feature_name", "condition_type", "condition_value", "rule_update_time"]
x[cols].sort_values(["scene_id", "status", "exec_priority", "strategy_id"], ascending=[True, False, False, True]) \
    .to_csv(os.path.join(R, "config_strategy_expanded.csv"), index=False)

# fixed strategies per enabled scene: rule on cid == '702' -> PASS; whitelist-feature rules -> PASS; blacklist-feature rules -> REJECT
wl = set(lf[lf.feature_name.str.contains("白名单")].feature_id)
bl = set(lf[lf.feature_name.str.contains("黑名单")].feature_id)
chk = []
for _, sc in scene[scene.status == 1].iterrows():
    xs = x[(x.scene_id == sc.scene_id) & (x.status == 1)]
    def find(mask, code):
        hit = xs[mask & (xs.result_code == code)].drop_duplicates("strategy_id")
        return ";".join(f"{r.strategy_id}(prio {r.exec_priority})" for r in hit.itertuples()) or "—"
    chk.append({"scene_id": sc.scene_id, "access_id": sc.access_id,
                "cid702_pass": find((xs.feature_id == "cid") & (xs.condition_value.astype(str) == "702"), "PASS"),
                "whitelist_pass": find(xs.feature_id.isin(wl), "PASS"),
                "blacklist_reject": find(xs.feature_id.isin(bl), "REJECT"),
                "online_strategies": xs.strategy_id.nunique()})
pd.DataFrame(chk).to_csv(os.path.join(R, "config_fixed_strategies_check.csv"), index=False)

# counter features
ctool = tool[tool.tool_classpath.str.contains("CommonCounterFeatureImpl")].tool_id.tolist()
rows = []
for _, r in tf[tf.tool_id.isin(ctool)].iterrows():
    j = json.loads(r.input_paras)
    rows.append({"feature_id": r.feature_id, "feature_name": r.feature_name, "status": r.status, "period_s": j.get("period"),
                 "counter": j.get("counter"), "dimension": j.get("dimension"), "count_value": j.get("countValue"),
                 "has_condition": j.get("hasCondition"), "conditions": json.dumps(j.get("conditions"), ensure_ascii=False),
                 "condition_express": j.get("conditionExpress"), "update_time": r.update_time})
cf = pd.DataFrame(rows)
cf["counter_kind"] = cf.counter.map({0: "PV(访问次数)", 1: "UV(去重个数)"})
cf.to_csv(os.path.join(R, "config_counter_features.csv"), index=False)

# config status vs status recorded in hit elements
h = rd("p2_hits_7d.csv")
m = h.groupby(["list", "strategy_id", "hit_status"]).pv.sum().reset_index().merge(s[["strategy_id", "status"]], on="strategy_id", how="left")
m.rename(columns={"status": "config_status_now"}).to_csv(os.path.join(R, "config_status_vs_hits.csv"), index=False)
print(pd.DataFrame(chk).to_string(index=False))
print(cf[cf.has_condition == True][["feature_id", "feature_name", "dimension", "counter_kind", "conditions"]].to_string(index=False))
print(m[(m.list == "preonline") & (m.status == 1)].to_string(index=False))
