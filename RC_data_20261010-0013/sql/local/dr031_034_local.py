#!/usr/bin/env python3
"""DR-034 (strategies created or changed after 2026-09-27, including those whose rules / features changed) and DR-031
(strategy_bYXaOJ4qXtW4's country codes split by the two IP conditions). E1 + config export + op-log timeline; counts only.

DR-034 outputs: dr034_strategies.csv (current definition), dr034_timeline.csv (every change, UTC), dr034_daily_hits.csv
  (NY day x strategy: online / pre-online / unique-REJECT hits and distinct phones per day, SMS basis; distinct counts are per
  day and must not be summed across days).
DR-031 outputs: dr031_code_versions.csv (code list versions of the shared country-code rule), dr031_daily.csv (NY day x cc x
  final result x IP class), dr031_period_rates.csv (per-24h rates per period, periods split at every switch in the span),
  dr031_after_switch_by_cc.csv (online hits, unique rejects, still-PASS per code after bYXa went online), dr031_ip_split_share.csv.
IP class: us = realIpCountry is the US value; eq_phone = realIpCountry equals phoneCountry; other = neither (both IP conditions of
  bYXa hold); unknown = no IP country."""
import os, re, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1lib import out, load_e1, unique_reject, R  # noqa: E402

SINCE, END = "2026-09-27", pd.Timestamp("2026-10-10 04:00:00")
rd = lambda n: pd.read_csv(os.path.join(R, n), dtype=str)
st, tl, x = rd("config_strategy.csv"), rd("p2_oplog_timeline.csv"), rd("config_strategy_expanded.csv")
push = st[(st.access_id == "LKUS") & (st.scene_id == "LKUS_push")]
tl_new = tl[tl.operation_time_utc >= SINCE]
direct = set(tl_new[tl_new.object_kind == "strategyId"].object_id)
rules_chg = set(tl_new[tl_new.object_kind == "ruleId"].object_id)
feats_chg = set(tl_new[tl_new.object_kind == "featureId"].object_id)
via = set(x[x.rule_id.isin(rules_chg) | x.feature_id.isin(feats_chg)].strategy_id) & set(push.strategy_id)
sel = sorted(direct | via)
S = push[push.strategy_id.isin(sel)].copy()
S["why"] = S.strategy_id.map(lambda s: "+".join(k for k, v in (("strategy changed", s in direct), ("rule/feature changed", s in via)) if v))
S["rules_changed_since_0927"] = S.strategy_id.map(lambda s: " ".join(sorted(set(x[(x.strategy_id == s) & x.rule_id.isin(rules_chg)].rule_id))))
S["features_changed_since_0927"] = S.strategy_id.map(lambda s: " ".join(sorted(set(x[(x.strategy_id == s) & x.feature_id.isin(feats_chg)].feature_id.dropna()))))
cols = ["strategy_id", "strategy_name", "status", "result_code", "exec_priority", "create_time", "update_time", "strategy_express", "why",
        "rules_changed_since_0927", "features_changed_since_0927"]
out(S[cols].sort_values("create_time"), "dr034_strategies.csv")
objs = set(sel) | {r for s in sel for r in re.findall(r"rule_[A-Za-z0-9]+", str(S.set_index("strategy_id").strategy_express.get(s, "")))}
tlx = tl[(tl.object_id.isin(objs)) & (tl.operation_time_utc >= "2026-09-02")].sort_values("operation_time_utc")
out(tlx[["operation_time_utc", "module", "operation_type", "object_kind", "object_id", "field", "before", "after"]], "dr034_timeline.csv")

d = load_e1()
d = d[(d.create_time < END)].copy()
sms = d[d.sms & (d.ny_date >= SINCE)]
rows = []
for sid in sel:
    only_on, pre_no_on, s_on, s_pre = unique_reject(sms, sid)
    g = sms.assign(s_on=s_on, s_pre=s_pre, u_on=only_on, u_pre=pre_no_on)
    for day, gg in g.groupby("ny_date"):
        rows.append({"ny_date": day, "strategy_id": sid, "online_hits": int(gg.s_on.sum()), "online_hit_phones": gg[gg.s_on].phone_h.nunique(),
                     "online_unique_reject": int(gg.u_on.sum()), "online_unique_reject_phones": gg[gg.u_on].phone_h.nunique(),
                     "preonline_hits": int(gg.s_pre.sum()), "preonline_hit_phones": gg[gg.s_pre].phone_h.nunique(),
                     "preonline_unique_recall": int(gg.u_pre.sum()),
                     "preonline_hits_final_pass": int((gg.s_pre & (gg.final_result == "PASS")).sum()),
                     "hits_non_plus1": int(((gg.s_on | gg.s_pre) & (gg.cc_group != "+1")).sum()),
                     "hits_plus1": int(((gg.s_on | gg.s_pre) & (gg.cc_group == "+1")).sum())})
out(pd.DataFrame(rows), "dr034_daily_hits.csv")

# ---------------- DR-031 ----------------
BY = "strategy_bYXaOJ4qXtW4"
cr = x[(x.strategy_id == BY) & (x.feature_id == "countryCode") & (x.condition_type == "INCLUDE")].rule_id.iloc[0]
vers = tl[(tl.object_id == cr) & (tl.field == "conditionValue")].sort_values("operation_time_utc")
cur = x[(x.rule_id == cr)].condition_value.iloc[0]
codes = lambda v: [c.strip().lstrip("+") for c in str(v).split(",") if c.strip()]
v_rows = []
if len(vers):
    v_rows.append({"rule_id": cr, "valid_from_utc": "(created)", "valid_to_utc": vers.operation_time_utc.iloc[0], "codes": " ".join(codes(vers.before.iloc[0])), "n": len(codes(vers.before.iloc[0]))})
    for i, r in enumerate(vers.itertuples()):
        to = vers.operation_time_utc.iloc[i + 1] if i + 1 < len(vers) else "(now)"
        v_rows.append({"rule_id": cr, "valid_from_utc": r.operation_time_utc, "valid_to_utc": to, "codes": " ".join(codes(r.after)), "n": len(codes(r.after))})
else:
    v_rows.append({"rule_id": cr, "valid_from_utc": "(created)", "valid_to_utc": "(now)", "codes": " ".join(codes(cur)), "n": len(codes(cur))})
out(pd.DataFrame(v_rows), "dr031_code_versions.csv")
C15 = set(v_rows[0]["codes"].split()); CNOW = set(codes(cur)); CADD = CNOW - C15
sw = lambda sid, v: pd.Timestamp(tl[(tl.object_id == sid) & (tl.field == "status") & (tl.after == v)].operation_time_utc.iloc[-1])
marks = sorted({("WvNG online", sw("strategy_WvNGjLMgoOyn", "1")), ("MZQk pre-online", sw("strategy_MZQkGORFiZbP", "2")),
                ("bYXa pre-online", sw(BY, "2")), ("bYXa online", sw(BY, "1"))} |
               ({("country rule widened", pd.Timestamp(vers.operation_time_utc.iloc[-1]))} if len(vers) else set()), key=lambda t: t[1])
B0 = pd.Timestamp("2026-10-02 04:00:00")
edges = [("NY 10-02 start", B0)] + marks + [("end NY 10-09", END)]
y = d[d.sms & d.cc.isin(CNOW)].copy()
y["code_set"] = np.where(y.cc.isin(C15), "15 original", "6 added")
dd = y[y.ny_date >= "2026-09-27"].groupby(["ny_date", "code_set", "cc", "final_result", "ip_geo"]).size().reset_index(name="requests")
out(dd, "dr031_daily.csv")
pr = []
for (n0, a), (n1, b) in zip(edges[:-1], edges[1:]):
    hrs = (b - a).total_seconds() / 3600
    if hrs <= 0:
        continue
    g = y[(y.create_time >= a) & (y.create_time < b)]
    for cs, gg in g.groupby("code_set"):
        for geo in ("other", "us", "eq_phone", "unknown"):
            g3 = gg[gg.ip_geo == geo]
            pr.append({"period": f"{n0} -> {n1}", "start_utc": a, "end_utc": b, "hours": round(hrs, 2), "code_set": cs, "ip_class": geo,
                       "requests_per_24h": round(len(g3) / hrs * 24, 1), "pass_per_24h": round((g3.final_result == "PASS").sum() / hrs * 24, 1)})
out(pd.DataFrame(pr), "dr031_period_rates.csv")
sh = y[(y.create_time >= B0)].groupby(["code_set", "ip_geo"]).agg(requests=("id", "size"), passes=("final_result", lambda s: (s == "PASS").sum())).reset_index()
for c in ("requests", "passes"):
    sh[c + "_share_within_code_set"] = (sh[c].astype(float) / sh.groupby("code_set")[c].transform("sum").astype(float)).round(4)
out(sh, "dr031_ip_split_share.csv")
pc = y[(y.create_time >= B0)].groupby(["cc", "ip_geo"]).agg(requests=("id", "size"), passes=("final_result", lambda s: (s == "PASS").sum())).reset_index()
out(pc, "dr031_ip_split_by_cc.csv")
SWB = sw(BY, "1")
a = y[y.create_time >= SWB].copy()
o, p, s_on, s_pre = unique_reject(a, BY)
a["on"], a["uniq"] = s_on, o
ab = a.groupby(["cc", "ip_geo"]).agg(requests=("id", "size"), online_hits=("on", "sum"), unique_rejects=("uniq", "sum"),
                                     still_pass=("final_result", lambda s: (s == "PASS").sum())).reset_index()
ab["in_15"] = ab.cc.isin(C15)
out(ab, "dr031_after_switch_by_cc.csv")
print(pd.DataFrame(v_rows).to_string(index=False))
print(sh.to_string(index=False))
print("after switch:", ab[["requests", "online_hits", "unique_rejects", "still_pass"]].sum().to_dict())
