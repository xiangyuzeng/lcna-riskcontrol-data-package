#!/usr/bin/env python3
"""P3: seven-day LKUS_push profile computed locally from the E1 extract.

Input  : _local_only/raw/e1_a.csv.gz, e1_b.csv.gz  (sql/e1_a.sql / sql/e1_b.sql; row-level, salted hashes, never packaged)
         results/config_third_feature.csv, config_tool.csv, config_strategy.csv (for IDs / names discovered at run time)
Params : --start / --end (NY dates, inclusive) of the profile window; --cuts (V3 score bucket edges)
Output : results/p3_*.csv (aggregates only; the runner-style privacy guard below refuses hash-like columns)
Cross-checks against pure-SQL aggregates: results/p4_daily_series.csv (daily result x cc group) and
results/p2_hits_7d.csv (strategy PV) -> results/p3_crosscheck.csv
"""
import argparse, json, os
import numpy as np
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, RAW = os.path.join(PKG, "results"), os.path.join(PKG, "_local_only", "raw")
ap = argparse.ArgumentParser()
ap.add_argument("--start", required=True); ap.add_argument("--end", required=True)
ap.add_argument("--cuts", default="0.3,0.8")
a = ap.parse_args()
LO, HI = (float(x) for x in a.cuts.split(","))


def out(df, name):
    bad = [c for c in df.columns if str(c).endswith("_h")]
    if bad:
        raise SystemExit(f"refusing to write hash columns {bad} to {name}")
    df.to_csv(os.path.join(R, name), index=False)
    return df


def load_e1():
    d = pd.concat([pd.read_csv(os.path.join(RAW, f), dtype=str) for f in ("e1_a.csv.gz", "e1_b.csv.gz")], ignore_index=True)
    d["create_time"] = pd.to_datetime(d.create_time)
    d = d.drop_duplicates("id")
    ny = d.create_time.dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    d["ny_date"], d["ny_hour"] = ny.dt.strftime("%Y-%m-%d"), ny.dt.hour
    d["cc"] = d.cc_raw.fillna("").str.lstrip("+")
    d["cc_form"] = np.where(d.cc_raw.fillna("") == "", "empty", np.where(d.cc_raw.fillna("").str.startswith("+"), "plus", "bare"))
    d["cc_group"] = np.select([d.cc == "1", d.cc == "86", d.cc == ""], ["+1", "+86", "unknown"], "other")
    d["sms"] = d.email_present.astype(int) == 0
    d["app_state"] = np.where(d.app == "<absent>", "absent", np.where(d.app == "<empty>", "empty", "present"))
    d["phone_ne_ip_country"] = (d.phone_country.fillna("") != d.ip_country.fillna("")).astype(int)
    d["ip_is_us"] = (d.ip_country == "美国").astype(int)

    def ver(v):
        try:
            p = [int("".join(ch for ch in x if ch.isdigit()) or 0) for x in str(v).split(".")[:3]]
            return p[0] * 1000000 + p[1] * 1000 + p[2] if len(p) == 3 else np.nan
        except Exception:
            return np.nan
    d["version_num"] = d.version.map(ver)
    return d


d = load_e1()
tf = pd.read_csv(os.path.join(R, "config_third_feature.csv")); tool = pd.read_csv(os.path.join(R, "config_tool.csv"))
strat = pd.read_csv(os.path.join(R, "config_strategy.csv"))
rtools = tool[tool.tool_classpath.str.contains("GoogleRecaptchaFeatureTool")].tool_id
V3 = set(tf[tf.tool_id.isin(rtools) & (tf.third_label == "riskAnalysis.score") & tf.feature_name.str.contains("V3")].feature_id)


def v3(row):
    """Score by SHAPE: any reCAPTCHA feature element whose apiResp carries riskAnalysis.score (the feature ID that
    carries it changed during the window); otherwise the status code of the configured V3 score feature."""
    if not isinstance(row, str):
        return (None, np.nan, None, None)
    els = [e for e in json.loads(row) if e]
    for e in els:
        if e.get("score") is not None:
            return (e.get("code"), float(e["score"]), e.get("valid"), e.get("fid"))
    for e in els:
        if e.get("fid") in V3:
            return (e.get("code"), np.nan, e.get("valid"), e.get("fid"))
    return (els[0].get("code"), np.nan, None, els[0].get("fid")) if els else (None, np.nan, None, None)


vv = d.recaptcha_json.map(v3)
d["v3_code"], d["v3_score"], d["v3_valid"], d["v3_fid"] = vv.str[0], vv.str[1], vv.str[2], vv.str[3]
d["v3_bucket"] = np.select([d.v3_score.isna(), d.v3_score < LO, d.v3_score < HI], ["missing", f"<{LO}", f"{LO}-{HI}"], f">={HI}")
lst = lambda s: [x.split("|") for x in json.loads(s)] if isinstance(s, str) else []
d["on"], d["pre"] = d.hits_online.map(lst), d.hits_preonline.map(lst)

W = d[(d.ny_date >= a.start) & (d.ny_date <= a.end)].copy()
S = W[W.sms]
print(f"window rows={len(W)} sms rows={len(S)} email-key rows={int((~W.sms).sum())}")

# --- T1 day x final result (all push rows and SMS rule) ----------------------------------------------
t1 = W.pivot_table(index="ny_date", columns="final_result", values="id", aggfunc="count", fill_value=0)
t1["total"] = t1.sum(axis=1)
t1s = S.pivot_table(index="ny_date", columns="final_result", values="id", aggfunc="count", fill_value=0).add_prefix("sms_")
t1 = t1.join(t1s).reset_index()
out(t1, "p3_daily_result.csv")

# --- T2 day x cc group x result; non-+1 share of PASS ------------------------------------------------
t2 = S.pivot_table(index=["ny_date", "cc_group"], columns="final_result", values="id", aggfunc="count", fill_value=0).reset_index()
out(t2, "p3_daily_ccgroup_result.csv")
p = S[S.final_result == "PASS"]
t2b = p.groupby("ny_date").agg(pass_total=("id", "count"), pass_plus1=("cc_group", lambda x: (x == "+1").sum()),
                               pass_plus86=("cc_group", lambda x: (x == "+86").sum()), pass_other=("cc_group", lambda x: (x == "other").sum()),
                               pass_unknown=("cc_group", lambda x: (x == "unknown").sum())).reset_index()
t2b["non_plus1_share_of_pass"] = ((t2b.pass_total - t2b.pass_plus1) / t2b.pass_total).round(4)
tot = t2b.sum(numeric_only=True); tot["non_plus1_share_of_pass"] = round((tot.pass_total - tot.pass_plus1) / tot.pass_total, 4)
t2b = pd.concat([t2b, pd.DataFrame([{"ny_date": "7d", **tot}])], ignore_index=True)
out(t2b, "p3_pass_by_ccgroup.csv")
out(W.groupby("cc_form").id.count().reset_index(name="rows"), "p3_cc_spelling.csv")

# --- T3 distinct users (exact, cross-shard) + DR-014 part 2 -----------------------------------------
rows = []
for day, g in list(S.groupby("ny_date")) + [("7d", S)]:
    gp = g[g.final_result == "PASS"]
    rows.append({"ny_date": day, "requests": len(g), "distinct_phones": g.phone_h.nunique(), "distinct_uids": g.uid_h.nunique(),
                 "pass_distinct_phones": gp.phone_h.nunique(), "pass_plus1_distinct_phones": gp[gp.cc_group == "+1"].phone_h.nunique(),
                 "sum_per_shard_distinct_uids": int(g.groupby("shard").uid_h.nunique().sum()),
                 "sum_per_shard_distinct_phones": int(g.groupby("shard").phone_h.nunique().sum())})
out(pd.DataFrame(rows), "p3_distinct_users.csv")
ps = W.groupby("phone_h").shard.nunique(); us = W.groupby("uid_h").shard.nunique()
out(pd.DataFrame([{"identity": "phone (sharding_key)", "distinct": len(ps), "in_more_than_one_shard": int((ps > 1).sum())},
                  {"identity": "gateway uid", "distinct": len(us), "in_more_than_one_shard": int((us > 1).sum()),
                   "max_shards_per_identity": int(us.max())}]), "p3_dr014_shard_spread.csv")

# --- T4 cid x app -----------------------------------------------------------------------------------
def prof(g):
    n = len(g)
    r = {"requests": n, "pass": int((g.final_result == "PASS").sum()), "reject": int((g.final_result == "REJECT").sum()),
         "review": int((g.final_result == "REVIEW").sum())}
    r["pass_share"] = round(r["pass"] / n, 4) if n else np.nan
    for t in ("absent", "empty", "present"):
        r[f"token_{t}_share"] = round((g.token_state == t).mean(), 4)
    for b in (f"<{LO}", f"{LO}-{HI}", f">={HI}", "missing"):
        r[f"v3_{b}_share"] = round((g.v3_bucket == b).mean(), 4)
    return pd.Series(r)
t4 = S.groupby(["cid", "cid_origin", "app"]).apply(prof, include_groups=False).reset_index().sort_values("requests", ascending=False)
out(t4, "p3_cid_app_profile.csv")

# --- T5 empty-app profile (DR-012) -------------------------------------------------------------------
ea = S[S.cid.isin(["105", "106"])]
parts = []
for dim in ("ua_family", "ua_product", "cc_group", "ip_country", "final_result", "token_state", "v3_bucket"):
    g = ea.groupby(["cid", "app_state", dim]).id.count().reset_index(name="rows")
    g["share_within_cid_app_state"] = (g.rows / g.groupby(["cid", "app_state"]).rows.transform("sum")).round(4)
    g.insert(2, "dimension", dim); g = g.rename(columns={dim: "value"})
    parts.append(g)
vq = ea.groupby(["cid", "app_state"]).version_num.describe(percentiles=[.05, .5, .95]).reset_index()
out(pd.concat(parts, ignore_index=True), "p3_empty_app_profile.csv")
out(vq, "p3_empty_app_version_stats.csv")
vv = ea.groupby(["cid", "app_state", "version"]).id.count().reset_index(name="rows").sort_values("rows", ascending=False)
out(vv, "p3_empty_app_versions.csv")

# --- T6 strategies -----------------------------------------------------------------------------------
def explode(col):
    e = S[["id", "phone_h", "final_result", "cc_group", col]].explode(col).dropna(subset=[col])
    e["strategy_id"], e["result_name"], e["exec_priority"] = e[col].str[0], e[col].str[1], e[col].str[2]
    return e
names = dict(zip(strat.strategy_id, strat.strategy_name))
res = []
for lst_name, col in (("online", "on"), ("preonline", "pre")):
    e = explode(col)
    g = e.groupby(["strategy_id", "result_name"]).agg(pv=("id", "nunique"), uv_phones=("phone_h", "nunique")).reset_index()
    # 额外召回 = hits whose outcome the strategy would change if it went online:
    #   non-PASS strategies (REJECT / REVIEW...) -> hits whose final result is PASS;
    #   PASS-class strategies -> hits whose final result is NOT already PASS (it would turn them into PASS).
    e["is_pass_class"] = e.result_name.astype(str).str.upper() == "PASS"
    ep = e[(e.is_pass_class & (e.final_result != "PASS")) | (~e.is_pass_class & (e.final_result == "PASS"))]
    x = ep.groupby("strategy_id").agg(extra_recall_pv=("id", "nunique"), extra_recall_phones=("phone_h", "nunique"),
                                      extra_recall_non_plus1_pv=("cc_group", lambda s: (s != "+1").sum()),
                                      extra_recall_plus1_pv=("cc_group", lambda s: (s == "+1").sum())).reset_index()
    fp = e[e.final_result == "PASS"].groupby("strategy_id").id.nunique().rename("hits_final_pass_pv").reset_index()
    g = g.merge(x, on="strategy_id", how="left").merge(fp, on="strategy_id", how="left").fillna(0)
    g["extra_recall_definition"] = g.result_name.astype(str).str.upper().map(lambda r: "hits with final result not PASS (PASS-class)" if r == "PASS" else "hits with final result PASS")
    g.insert(0, "list", lst_name)
    g["strategy_name"] = g.strategy_id.map(names)
    res.append(g.sort_values("pv", ascending=False))
t6 = pd.concat(res, ignore_index=True)
out(t6, "p3_strategies.csv")

# --- T7 PASS leakage (non-+1 SMS PASS) ---------------------------------------------------------------
lk = S[(S.final_result == "PASS") & (S.cc_group != "+1")]
parts = []
for dim in ("cc", "ip_country", "phone_ne_ip_country", "cid", "token_state", "app_state", "v3_bucket"):
    g = lk.groupby(dim).agg(rows=("id", "count"), distinct_phones=("phone_h", "nunique")).reset_index().rename(columns={dim: "value"})
    g.insert(0, "dimension", dim); g["share"] = (g.rows / len(lk)).round(4)
    parts.append(g.sort_values("rows", ascending=False))
out(pd.concat(parts, ignore_index=True), "p3_pass_leakage.csv")

# --- T8 counter feature status codes x day -----------------------------------------------------------
cj = S[["id", "ny_date", "counters_json"]].dropna()
recs = []
for rid, day, j in cj.itertuples(index=False):
    for fid, (code, _v) in json.loads(j).items():
        recs.append((day, fid, code))
cc = pd.DataFrame(recs, columns=["ny_date", "feature_id", "code"]).groupby(["feature_id", "code", "ny_date"]).size().reset_index(name="rows")
cc["feature_name"] = cc.feature_id.map(dict(zip(tf.feature_id, tf.feature_name)))
out(cc, "p3_counter_codes_daily.csv")
cc7 = cc.groupby(["feature_id", "feature_name", "code"]).rows.sum().reset_index()
cc7["share"] = (cc7.rows / cc7.groupby("feature_id").rows.transform("sum")).round(4)
out(cc7, "p3_counter_codes_7d.csv")

# --- T9 H5 A2 chain ----------------------------------------------------------------------------------
h5 = S[S.cid == "108"].sort_values("create_time")
rv = h5[h5.final_result == "REVIEW"][["phone_h", "create_time"]]
rr = h5[h5.review_repeat == "true"]
m = rr[["id", "phone_h", "create_time", "final_result", "engine_result"]].merge(rv, on="phone_h", how="left", suffixes=("", "_rev"))
m = m[(m.create_time_rev < m.create_time) & (m.create_time - m.create_time_rev <= pd.Timedelta(minutes=30))]
linked = set(m.id)
chain = {"h5_requests": len(h5), "final_review": int((h5.final_result == "REVIEW").sum()),
         "review_repeat_true": len(rr), "review_repeat_true_linked_to_prior_review_30min": len(linked),
         "review_repeat_true_final_review": int((rr.final_result == "REVIEW").sum()),
         "review_repeat_true_final_pass": int((rr.final_result == "PASS").sum()),
         "review_repeat_true_final_reject": int((rr.final_result == "REJECT").sum()),
         "engine_review_final_pass": int(((S.engine_result == "REVIEW") & (S.final_result == "PASS")).sum()),
         "engine_review_final_pass_with_review_repeat_true": int(((S.engine_result == "REVIEW") & (S.final_result == "PASS") & (S.review_repeat == "true")).sum()),
         "final_review_with_response_model": int(((S.final_result == "REVIEW") & (S.response_has_model == "1")).sum())}
out(pd.DataFrame([chain]), "p3_h5_a2_chain.csv")
out(S.groupby(["cid", "review_repeat", "engine_result", "final_result"], dropna=False).id.count().reset_index(name="rows"), "p3_review_matrix.csv")

# --- T10 V3 score distribution (DR-009 / DR-011) ------------------------------------------------------
t10 = S.groupby(["cc_group", "cid", "v3_bucket"]).agg(rows=("id", "count"), pass_rows=("final_result", lambda x: (x == "PASS").sum())).reset_index()
t10["share_within_ccgroup_cid"] = (t10.rows / t10.groupby(["cc_group", "cid"]).rows.transform("sum")).round(4)
out(t10, "p3_v3_by_ccgroup_cid.csv")
hist = S[S.v3_score.notna()].assign(score=lambda x: x.v3_score.round(1)).groupby(["cc_group", "score"]).id.count().reset_index(name="rows")
out(hist, "p3_v3_score_hist.csv")
out(S.groupby(["v3_fid", "v3_code", "v3_valid"], dropna=False).id.count().reset_index(name="rows"), "p3_v3_codes.csv")
out(S.groupby(["ny_date", "v3_fid"], dropna=False).agg(rows=("id", "count"), with_score=("v3_score", lambda x: x.notna().sum())).reset_index(), "p3_v3_fid_daily.csv")
sh = W.score_shaped_fids.fillna("[]").map(lambda s: ",".join(json.loads(s)) or "<none>")
out(W.assign(sh=sh).groupby(["ny_date", "sh"]).id.count().reset_index(name="rows"), "p3_v3_shape_match_daily.csv")

# --- cross-checks against pure SQL aggregates ---------------------------------------------------------
cx = []
ds = pd.read_csv(os.path.join(R, "p4_daily_series.csv"))
ds = ds[(ds.ny_date >= a.start) & (ds.ny_date <= a.end)]
sql_day = ds.groupby(["ny_date", "cc_group", "result_col"]).n.sum()
sql_day_sms = ds[ds.email_nonempty != 1].groupby(["ny_date", "cc_group", "result_col"]).n.sum()
e1_day = W.groupby(["ny_date", "cc_group", "final_result"]).id.count()
j = pd.concat([sql_day.rename("sql"), e1_day.rename("e1")], axis=1).fillna(0)
cx.append({"check": "day x cc_group x final_result (all push rows)", "cells": len(j), "mismatching_cells": int((j.sql != j.e1).sum()),
           "sql_total": int(j.sql.sum()), "e1_total": int(j.e1.sum())})
e1s = S.groupby(["ny_date", "cc_group", "final_result"]).id.count()
j = pd.concat([sql_day_sms.rename("sql"), e1s.rename("e1")], axis=1).fillna(0)
cx.append({"check": "day x cc_group x final_result (SMS rule: email empty)", "cells": len(j), "mismatching_cells": int((j.sql != j.e1).sum()),
           "sql_total": int(j.sql.sum()), "e1_total": int(j.e1.sum())})
hs = pd.read_csv(os.path.join(R, "p2_hits_7d.csv")).groupby(["list", "strategy_id"]).pv.sum()
e_on = W[["id", "on"]].explode("on").dropna(); e_pre = W[["id", "pre"]].explode("pre").dropna()
e1h = pd.concat([e_on.assign(list="online", strategy_id=e_on.on.str[0]), e_pre.assign(list="preonline", strategy_id=e_pre.pre.str[0])]) \
        .groupby(["list", "strategy_id"]).id.count()
j = pd.concat([hs.rename("sql"), e1h.rename("e1")], axis=1).fillna(0)
cx.append({"check": "strategy hit PV by list (all push rows)", "cells": len(j), "mismatching_cells": int((j.sql != j.e1).sum()),
           "sql_total": int(j.sql.sum()), "e1_total": int(j.e1.sum())})
out(pd.DataFrame(cx), "p3_crosscheck.csv")
print(pd.DataFrame(cx).to_string(index=False))
