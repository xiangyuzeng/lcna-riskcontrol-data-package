#!/usr/bin/env python3
"""Standing items and DR checks answered from E1 (local, salted hashes; counts only leave this script).
  DR-016 : engine result vs final result, 7 days (SMS)            -> dr016_summary_7d.csv, dr016_engine_vs_final_7d.csv
  DR-017 : strategies ranked above the whitelist PASS strategy, status and 7-day hits -> dr017_above_whitelist.csv
  DR-018 : strategies using time-of-day rules (TIME_AFTER / TIME_BEFORE), status and 7-day hits -> dr018_time_rule_strategies.csv
  DR-012 : cid 105/106 requests without app, and App versions < 1.4.30 (numeric), 7 days: volume, version, cc group, result,
           strategies hit                                         -> dr012_*.csv
  DR-036 b/c/d: the 10-08 group-chat numbers re-computed           -> dr036bcd.csv
  DR-003 : counter status codes 7 days per feature (combo-dimension features flagged) -> dr003_counter_codes_7d.csv
Windows: 7 日 = NY 2026-10-03..10-09; DR-036 b = NY 10-01..10-07 (the week before 10-08) and NY 10-08; c, d = NY 10-08."""
import json, os, re, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1lib import out, load_e1, R  # noqa: E402

A, B = "2026-10-03", "2026-10-09"
rd = lambda n: pd.read_csv(os.path.join(R, n), dtype=str)
st, x, rule = rd("config_strategy.csv"), rd("config_strategy_expanded.csv"), rd("config_rule.csv")
names = dict(zip(st.strategy_id, st.strategy_name))
d = load_e1()
W = d[(d.ny_date >= A) & (d.ny_date <= B)]
S = W[W.sms]

# DR-016
m = S.groupby(["cid", "engine_result", "final_result"], dropna=False).size().reset_index(name="rows")
out(m, "dr016_engine_vs_final_7d.csv")
er = S.engine_result.fillna("<none>")
rv = er.str.upper().str.startswith("REVIEW")
summ = {"window": f"NY {A}..{B}", "basis": "SMS", "sms_requests": len(S), "engine_review_class": int(rv.sum()),
        "engine_review_final_pass": int((rv & (S.final_result == "PASS")).sum()),
        "engine_review_final_review": int((rv & (S.final_result == "REVIEW")).sum()),
        "engine_review_cids": " ".join(sorted(S[rv].cid.dropna().unique())),
        "engine_review_final_pass_review_repeat_true": int((rv & (S.final_result == "PASS") & (S.review_repeat == "true")).sum()),
        "engine_no_result": int(er.isin(["<none>", "", "null"]).sum()),
        "engine_no_result_final_pass": int((er.isin(["<none>", "", "null"]) & (S.final_result == "PASS")).sum())}
out(pd.DataFrame([summ]), "dr016_summary_7d.csv")

# DR-017: priority above the whitelist PASS strategy of the same scene
fixed_wl = x[(x.scene_id == "LKUS_push") & (x.feature_kind == "list") & (x.result_code == "PASS")]
wl_prio = pd.to_numeric(st[st.strategy_id.isin(fixed_wl.strategy_id)].exec_priority).max()
pp = st[(st.scene_id == "LKUS_push") & (pd.to_numeric(st.exec_priority) > wl_prio)].copy()
hits = pd.read_csv(os.path.join(R, "p2_hits_7d.csv"))
hv = hits.groupby(["strategy_id", "list"]).agg(pv=("pv", "sum")).reset_index().pivot(index="strategy_id", columns="list", values="pv")
pp = pp.merge(hv, left_on="strategy_id", right_index=True, how="left").fillna({"online": 0, "preonline": 0})
pp["whitelist_priority"] = wl_prio
pp["hits_7d_basis"] = "all LKUS_push rows, NY 10-03..10-09 (p2_hits_7d)"
out(pp[["strategy_id", "strategy_name", "status", "result_code", "exec_priority", "whitelist_priority", "update_time"] + [c for c in ("online", "preonline") if c in pp] + ["hits_7d_basis"]], "dr017_above_whitelist.csv")

# DR-018
tr = set(rule[rule.condition_type.isin(["TIME_AFTER", "TIME_BEFORE"])].rule_id)
ts_ = x[x.rule_id.isin(tr)].groupby("strategy_id").agg(rules=("rule_id", lambda s: " ".join(sorted(set(s)))),
                                                         conditions=("condition_value", lambda s: " ".join(sorted(set(s.dropna()))))).reset_index()
ts_ = ts_.merge(st[["strategy_id", "strategy_name", "scene_id", "status", "result_code", "exec_priority"]], on="strategy_id", how="left") \
         .merge(hv, left_on="strategy_id", right_index=True, how="left").fillna({"online": 0, "preonline": 0})
ts_["ny_window_until_10_31_EDT"] = "UTC 02:00-09:00 = NY 22:00-05:00 (EDT)"
ts_["ny_window_from_11_01_EST"] = "UTC 02:00-09:00 = NY 21:00-04:00 (EST)"
out(ts_, "dr018_time_rule_strategies.csv")

# DR-012 refresh
app = S[S.cid.isin(["105", "106"])].copy()
app["group"] = np.select([app.app_state != "present", app.version_num < 1004030], ["no app field", "app present, version < 1.4.30"], "app present, version >= 1.4.30")
out(app.groupby(["cid", "group", "final_result"]).size().reset_index(name="rows"), "dr012_cid_group_result.csv")
out(app.groupby(["cid", "group", "version"]).size().reset_index(name="rows").sort_values("rows", ascending=False), "dr012_versions.csv")
out(app.groupby(["cid", "group", "cc_group"]).size().reset_index(name="rows"), "dr012_ccgroup.csv")
out(app.groupby(["cid", "group", "token_state"]).size().reset_index(name="rows"), "dr012_token.csv")
out(app.groupby(["cid", "group", "ny_date"]).agg(rows=("id", "size"), phones=("phone_h", "nunique")).reset_index(), "dr012_daily.csv")
rows = []
for (cid, grp), g in app.groupby(["cid", "group"]):
    for lst, col in (("online", "on"), ("preonline", "pre")):
        e = g[["id", col, "final_result"]].explode(col).dropna(subset=[col])
        if len(e):
            e["sid"], e["rn"] = e[col].str[0], e[col].str[1]
            for (sid, rn), gg in e.groupby(["sid", "rn"]):
                rows.append({"cid": cid, "group": grp, "list": lst, "strategy_id": sid, "result_name": rn, "hits": gg.id.nunique(),
                             "final_pass": int((gg.final_result == "PASS").sum()), "strategy_name": names.get(sid, "")})
out(pd.DataFrame(rows).sort_values(["cid", "group", "hits"], ascending=[True, True, False]), "dr012_strategies_hit.csv")
tot = app.groupby(["cid", "group"]).agg(requests=("id", "size"), phones_7d=("phone_h", "nunique"),
                                        pass_=("final_result", lambda s: (s == "PASS").sum()),
                                        non_plus1=("cc_group", lambda s: (s != "+1").sum()),
                                        no_online_hit=("on_ids", lambda s: s.map(len).eq(0).sum())).reset_index()
out(tot.rename(columns={"pass_": "pass"}), "dr012_summary.csv")

# DR-036 b, c, d
rows = []
for lab, a_, b_ in (("NY 10-01..10-07", "2026-10-01", "2026-10-07"), ("NY 10-08", "2026-10-08", "2026-10-08")):
    g = d[d.sms & (d.ny_date >= a_) & (d.ny_date <= b_) & (d.final_result == "PASS") & (d.cc_group != "+1")]
    nd = g.ny_date.nunique()
    top = g.groupby(["cc", "phone_country"]).size().sort_values(ascending=False).head(8)
    rows.append({"claim": "b", "window": lab, "metric": "non-+1 SMS PASS per day", "value": round(len(g) / max(nd, 1), 1)})
    for (cc, pc), n in top.items():
        rows.append({"claim": "b", "window": lab, "metric": f"top codes: +{cc} ({pc}) share of non-+1 PASS", "value": round(n / len(g), 4)})
    rows.append({"claim": "b", "window": lab, "metric": "V3 score >= 0.8 share of non-+1 PASS", "value": round(float((g.v3_score >= 0.8).mean()), 4)})
    rows.append({"claim": "b", "window": lab, "metric": "V3 score = 0.8 exactly (1 dp) share of non-+1 PASS", "value": round(float((g.v3_score.round(1) == 0.8).mean()), 4)})
g = d[d.sms & (d.ny_date == "2026-10-08") & (d.final_result == "PASS") & (d.cc_group != "+1")]
rows += [{"claim": "c", "window": "NY 10-08", "metric": "non-+1 SMS PASS", "value": len(g)},
         {"claim": "c", "window": "NY 10-08", "metric": "share with non-US IP (IP country known and not US)", "value": round(float(g.ip_geo.isin(["other", "eq_phone"]).mean()), 4)},
         {"claim": "c", "window": "NY 10-08", "metric": "share with non-US IP and IP country != phone country", "value": round(float((g.ip_geo == "other").mean()), 4)},
         {"claim": "c", "window": "NY 10-08", "metric": "share with no IP country", "value": round(float((g.ip_geo == "unknown").mean()), 4)}]
g = d[d.sms & (d.ny_date == "2026-10-08") & (d.final_result == "PASS")]
for h0 in (4, 8, 12, 16, 20):
    gg = g[g.ny_hour >= h0]
    rows.append({"claim": "d", "window": f"NY 10-08 {h0:02d}:00..24:00", "metric": "share of SMS PASS with +1", "value": round(float((gg.cc_group == "+1").mean()), 4) if len(gg) else None})
rows.append({"claim": "d", "window": "NY 10-08 00:00..04:00", "metric": "share of SMS PASS with +1", "value": round(float((g[g.ny_hour < 4].cc_group == "+1").mean()), 4)})
out(pd.DataFrame(rows), "dr036bcd.csv")

# DR-003 counters (7 days, SMS)
recs = []
for day, j in S[["ny_date", "counters_json"]].dropna().itertuples(index=False):
    for fid, v in json.loads(j).items():
        recs.append((day, fid, v[0] if isinstance(v, list) else None))
cc = pd.DataFrame(recs, columns=["ny_date", "feature_id", "code"]).groupby(["feature_id", "code", "ny_date"]).size().reset_index(name="rows")
cf = rd("config_counter_features.csv")
cc = cc.merge(cf[["feature_id", "feature_name", "dimension"]], on="feature_id", how="left")
cc["combo_dimension"] = cc.dimension.fillna("").str.contains(r"\|").astype(int)
out(cc, "dr003_counter_codes_daily.csv")
c7 = cc.groupby(["feature_id", "feature_name", "dimension", "combo_dimension", "code"]).rows.sum().reset_index()
c7["share"] = (c7.rows / c7.groupby("feature_id").rows.transform("sum")).round(4)
out(c7, "dr003_counter_codes_7d.csv")
# break-strategy hits over the whole E1 window (all LKUS_push rows)
bk = d[pd.to_numeric(d.n_break_hits, errors="coerce").fillna(0) > 0]
out(bk.groupby(["ny_date"]).size().reset_index(name="rows") if len(bk) else pd.DataFrame({"ny_date": [], "rows": []}), "p3_break_hits.csv")
print(pd.DataFrame([summ]).T.to_string(header=False))
print(c7[c7.combo_dimension == 1].to_string(index=False))
print(pd.DataFrame(rows).to_string(index=False))
