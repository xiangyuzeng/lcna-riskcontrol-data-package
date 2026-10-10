#!/usr/bin/env python3
"""P5: pick the strategies the toolkit tests use, from this run's data (nothing hardcoded):
  PRE  = pre-online strategy with the most 7-day hits (results/p2_hits_7d.csv)
  ON   = online REJECT strategy (not a fixed list/cid strategy) with the most 7-day hits
  TK06 = online strategy with exactly one rule, a counter feature with a numeric >/>= threshold; among those with
         >= 20 online hits in 7 days, the one whose counter window (period) is SHORTEST (smallest warm-up extract)
Prints shell assignments."""
import json, os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n))
h, st, x, cf = rd("p2_hits_7d.csv"), rd("config_strategy.csv"), rd("config_strategy_expanded.csv"), rd("config_counter_features.csv")
pv = h.groupby(["list", "strategy_id"]).pv.sum()
pre = pv["preonline"].sort_values(ascending=False).index[0]
lists = set(x[x.feature_kind == "list"].strategy_id) | set(x[x.feature_id == "cid"].strategy_id)
on_cand = st[(st.scene_id == "LKUS_push") & (st.status == 1) & (st.result_code == "REJECT") & (~st.strategy_id.isin(lists))].strategy_id
on = pv["online"].reindex(on_cand).dropna().sort_values(ascending=False).index[0]
cnt = set(cf[(cf.has_condition != True)].feature_id)
best = None
per = cf.set_index("feature_id").period_s
for sid, g in x[(x.scene_id == "LKUS_push") & (x.status == 1)].groupby("strategy_id"):
    c = g[g.feature_id.isin(cnt) & g.condition_type.isin([">", ">="])]
    if len(c) == 1 and len(g) == 1 and sid in pv["online"].index and pv["online"][sid] >= 20:
        r = c.iloc[0]; key = (int(per[r.feature_id]), -int(pv["online"][sid]))
        if best is None or key < best[4]:
            best = (sid, r.feature_id, r.condition_type, r.condition_value, key)
pre_disp = st.set_index("strategy_id").result_code.get(pre, "")
print(f"PRE={pre}\nPRE_PASS_CLASS={1 if str(pre_disp).upper() == 'PASS' else 0}\nON={on}")
if best:
    print(f"TK06_STRATEGY={best[0]}\nTK06_FEATURE={best[1]}\nTK06_OP='{best[2]}'\nTK06_THRESHOLD={best[3]}")
    p = int(cf.set_index("feature_id").loc[best[1]].period_s)
    print(f"TK06_PERIOD_S={p}")
