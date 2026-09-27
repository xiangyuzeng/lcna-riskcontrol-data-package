#!/usr/bin/env python3
"""P4 standing items DR-016 / DR-017 / DR-018, answered locally from the E1 extract, the config export and the 7-day hits
(no DB reads here).

Inputs : _local_only/raw/e1_a.csv.gz, e1_b.csv.gz (E1, LKUS_push, row-level with salted hashes, local only)
         _local_only/raw/dr026_captcha_extract.csv.gz (LKUS_captcha NY 2026-09-24, salted hashes, local only)
         results/dr0xx_*.csv from the runner, results/config_*.csv, results/p2_*.csv
Outputs: results/dr0xx_*.csv (aggregates only; no hash columns ever written)
Params : --start/--end NY window of E1 answers.
"""
import argparse, json, os
import numpy as np
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, RAW = os.path.join(PKG, "results"), os.path.join(PKG, "_local_only", "raw")
ap = argparse.ArgumentParser()
ap.add_argument("--start", required=True); ap.add_argument("--end", required=True)
ap.add_argument("--min-version", required=True)
a = ap.parse_args()
rd = lambda n: pd.read_csv(os.path.join(R, n))


def out(df, name):
    bad = [c for c in df.columns if str(c).endswith("_h")]
    assert not bad, (name, bad)
    df.to_csv(os.path.join(R, name), index=False)
    return df


def vnum(v):
    try:
        p = [int("".join(ch for ch in x if ch.isdigit()) or 0) for x in str(v).split(".")[:3]]
        return p[0] * 1000000 + p[1] * 1000 + p[2] if len(p) == 3 else np.nan
    except Exception:
        return np.nan


MINV = vnum(a.min_version)
d = pd.concat([pd.read_csv(os.path.join(RAW, f), dtype=str) for f in ("e1_a.csv.gz", "e1_b.csv.gz")], ignore_index=True).drop_duplicates("id")
d["t"] = pd.to_datetime(d.create_time)
d["ny_date"] = d.t.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
d["cc"] = d.cc_raw.fillna("").str.lstrip("+")
d["cc_group"] = np.select([d.cc == "1", d.cc == "86", d.cc == ""], ["+1", "+86", "unknown"], "other")
d["sms"] = d.email_present.astype(int) == 0
d["app_state"] = np.where(d.app == "<absent>", "absent", np.where(d.app == "<empty>", "empty", "present"))
d["version_num"] = d.version.map(vnum)
d["version_class"] = np.select([d.version_num.isna(), d.version_num >= MINV], ["no_version", f"ge_{a.min_version}"], f"lt_{a.min_version}")
d["geo_mismatch"] = (d.phone_country.fillna("") != d.ip_country.fillna("")).astype(int)
lst = lambda s: [x.split("|") for x in json.loads(s)] if isinstance(s, str) else []
d["on"], d["pre"] = d.hits_online.map(lst), d.hits_preonline.map(lst)
W = d[(d.ny_date >= a.start) & (d.ny_date <= a.end)].copy()
S = W[W.sms]
BASIS = f"SMS rule (email empty), LKUS_push, NY {a.start}..{a.end}"

# ---------------- DR-016: engine result vs final result (7 days, E1) ------------------------------------------
m = S.assign(engine_result=S.engine_result.fillna("<none>")).groupby(["cid", "review_repeat", "engine_result", "final_result"], dropna=False) \
     .agg(rows=("id", "count"), distinct_phones=("phone_h", "nunique")).reset_index()
out(m.assign(basis=BASIS), "dr016_engine_vs_final_7d.csv")
sm = pd.DataFrame([{"basis": BASIS, "sms_rows": len(S),
                    "engine_review_final_pass": int(((S.engine_result == "REVIEW") & (S.final_result == "PASS")).sum()),
                    "engine_review_final_review": int(((S.engine_result == "REVIEW") & (S.final_result == "REVIEW")).sum()),
                    "engine_review_total": int((S.engine_result == "REVIEW").sum()),
                    "engine_empty_rows": int((S.engine_result.fillna("") == "").sum()),
                    "engine_empty_final_pass": int(((S.engine_result.fillna("") == "") & (S.final_result == "PASS")).sum()),
                    "engine_review_final_pass_review_repeat_true": int(((S.engine_result == "REVIEW") & (S.final_result == "PASS") & (S.review_repeat == "true")).sum()),
                    "engine_review_final_pass_cid108": int(((S.engine_result == "REVIEW") & (S.final_result == "PASS") & (S.cid == "108")).sum())}])
out(sm, "dr016_summary_7d.csv")

# ---------------- DR-017: REJECT strategies above the whitelist ---------------------------------------------
st, lf, rel, rule = rd("config_strategy.csv"), rd("config_list_feature.csv"), rd("config_strategy_relation.csv"), rd("config_rule.csv")
wl_feat = set(lf[lf.feature_name.str.contains("白名单", na=False)].feature_id)
x = st.merge(rel[["strategy_id", "rule_id"]], on="strategy_id").merge(rule[["rule_id", "feature_id"]], on="rule_id")
wl_str = x[x.feature_id.isin(wl_feat) & (x.status == 1) & (x.result_code == "PASS")].groupby("scene_id").exec_priority.max()
h7 = rd("p2_hits_7d.csv")
rows = []
for sc, wp in wl_str.items():
    above = st[(st.scene_id == sc) & (st.exec_priority > wp) & (st.result_code != "PASS")]
    for r in above.itertuples():
        hh = h7[h7.strategy_id == r.strategy_id]
        rows.append({"scene_id": sc, "whitelist_pass_priority": int(wp), "strategy_id": r.strategy_id, "status": int(r.status),
                     "result_code": r.result_code, "exec_priority": int(r.exec_priority), "update_time_utc": r.update_time,
                     "hits_online_pv_7d_all_push_rows": int(hh[hh.list == "online"].pv.sum()),
                     "hits_preonline_pv_7d_all_push_rows": int(hh[hh.list == "preonline"].pv.sum()),
                     "hits_7d_sms_rows_e1": int(S.on.map(lambda l, s=r.strategy_id: any(h[0] == s for h in l)).sum())})
out(pd.DataFrame(rows), "dr017_reject_above_whitelist.csv")

# ---------------- DR-018: strategies that use UTC time-of-day rules -----------------------------------------
tr = rule[rule.condition_type.isin(["TIME_AFTER", "TIME_BEFORE"])]
y = x[x.rule_id.isin(tr.rule_id)].merge(tr[["rule_id", "condition_type", "condition_value"]], on="rule_id")
g = y.groupby(["scene_id", "strategy_id", "status", "result_code", "exec_priority", "update_time"]).apply(
    lambda q: " && ".join(f"{c} {v}" for c, v in zip(q.condition_type, q.condition_value)), include_groups=False).reset_index(name="time_conditions_utc")
g["hits_online_pv_7d_all_push_rows"] = g.strategy_id.map(lambda s: int(h7[(h7.strategy_id == s) & (h7.list == "online")].pv.sum()))
g["hits_preonline_pv_7d_all_push_rows"] = g.strategy_id.map(lambda s: int(h7[(h7.strategy_id == s) & (h7.list == "preonline")].pv.sum()))
g = g[g.status.isin([1, 2])]
out(g.sort_values(["status", "exec_priority"], ascending=[True, False]), "dr018_time_rule_strategies.csv")

print("done:", BASIS)
