#!/usr/bin/env python3
"""E1 parameters from the exported config (no DB reads, no hardcoded IDs). Extends the 09-27 p3_params.py:
  RC_IDS / COUNTER_IDS / TIME_RULE_IDS / COND_IDS : as p3_params.py (run first; it writes _local_only/p3_params.env)
  RULE_IDS : TIME_RULE_IDS plus every rule of every LKUS_push strategy that is online (1) or pre-online (2) now, plus the rules
             of strategies created/changed since 2026-09-27 whatever their status (so DR-030/031/034 can test conditions).
Writes _local_only/e1_params.env and results/e1_param_lists.csv."""
import os, re, subprocess, sys
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
subprocess.run([sys.executable, os.path.join(PKG, "sql", "local", "p3_params.py")], check=True, stdout=subprocess.DEVNULL)
env = dict(re.findall(r'^(\w+)="(.*)"$', open(os.path.join(PKG, "_local_only", "p3_params.env")).read(), re.M))
st = pd.read_csv(os.path.join(R, "config_strategy.csv"), dtype=str)
push = st[(st.access_id == "LKUS") & (st.scene_id == "LKUS_push")]
changed = push[(push.update_time >= "2026-09-27") | (push.create_time >= "2026-09-27")]
keep = push[push.status.isin(["1", "2"])]
ids = set()
for e in pd.concat([keep, changed]).strategy_express.dropna():
    ids |= set(re.findall(r"rule_[A-Za-z0-9]+", e))
rel_p = os.path.join(R, "config_strategy_relation.csv")
if os.path.exists(rel_p):                                   # strategy <-> rule relation table, in case an expression omits a rule
    rel = pd.read_csv(rel_p, dtype=str)
    if {"strategy_id", "rule_id"} <= set(rel.columns):
        ids |= set(rel[rel.strategy_id.isin(set(keep.strategy_id) | set(changed.strategy_id))].rule_id.dropna())
time_rules = set(re.findall(r"rule_[A-Za-z0-9]+", env.get("TIME_RULE_IDS", "")))
rule_ids = sorted(ids | time_rules)
q = lambda v: ",".join(f"'{i}'" for i in v)
with open(os.path.join(PKG, "_local_only", "e1_params.env"), "w") as fh:
    for k in ("RC_IDS", "COUNTER_IDS", "TIME_RULE_IDS", "COND_IDS"):
        fh.write(f'{k}="{env.get(k, "")}"\n')
    fh.write(f'RULE_IDS="{q(rule_ids)}"\n')
rows = [{"list": "rule_ids (online/pre-online LKUS_push strategies + changed since 09-27 + time rules)", "n_ids": len(rule_ids), "ids": " ".join(rule_ids)},
        {"list": "strategies covered", "n_ids": len(set(keep.strategy_id) | set(changed.strategy_id)), "ids": " ".join(sorted(set(keep.strategy_id) | set(changed.strategy_id)))}]
pd.DataFrame(rows).to_csv(os.path.join(R, "e1_param_lists.csv"), index=False)
print("rule_ids", len(rule_ids), "strategies", rows[1]["n_ids"], "changed since 09-27:", sorted(changed.strategy_id))
