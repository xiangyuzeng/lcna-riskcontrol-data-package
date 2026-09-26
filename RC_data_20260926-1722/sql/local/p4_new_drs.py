#!/usr/bin/env python3
"""P4: data requests answered locally from this run's extracts and aggregates (no DB reads here).

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
ap.add_argument("--dr026-day", required=True); ap.add_argument("--min-version", required=True)
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

# ---------------- DR-012: cid 105 version distribution with vs without app ----------------------------------
e = S[S.cid == "105"]
v = e.groupby(["app_state", "version"]).agg(rows=("id", "count"), distinct_phones=("phone_h", "nunique")).reset_index()
v["share_within_app_state"] = (v.rows / v.groupby("app_state").rows.transform("sum")).round(4)
v["version_num"] = v.version.map(vnum)
out(v.sort_values(["app_state", "rows"], ascending=[True, False]).assign(basis=BASIS), "dr012_cid105_versions_by_app.csv")
vs = e.groupby("app_state").agg(rows=("id", "count"), distinct_phones=("phone_h", "nunique"), distinct_versions=("version", "nunique"),
                                version_num_min=("version_num", "min"), version_num_median=("version_num", "median"), version_num_max=("version_num", "max"),
                                share_ge_min=("version_num", lambda x: round(float((x >= MINV).mean()), 4)),
                                share_plus1=("cc_group", lambda x: round(float((x == "+1").mean()), 4)),
                                share_token_present=("token_state", lambda x: round(float((x == "present").mean()), 4)),
                                share_pass=("final_result", lambda x: round(float((x == "PASS").mean()), 4))).reset_index()
out(vs.assign(basis=BASIS), "dr012_cid105_app_vs_noapp_summary.csv")

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

# ---------------- DR-023: strategy x NY day x cid x (phoneCountry != realIpCountry) --------------------------
parts = []
for lname, col in (("online", "on"), ("preonline", "pre")):
    ex = S[["id", "ny_date", "cid", "geo_mismatch", "phone_h", "final_result", col]].explode(col).dropna(subset=[col])
    ex["strategy_id"] = ex[col].str[0]
    gg = ex.groupby(["strategy_id", "ny_date", "cid", "geo_mismatch"]).agg(hit_pv=("id", "nunique"), distinct_phones=("phone_h", "nunique"),
                                                                        final_pass_pv=("final_result", lambda s: int((s == "PASS").sum()))).reset_index()
    gg.insert(0, "list", lname)
    parts.append(gg)
t23 = pd.concat(parts, ignore_index=True)
t23["basis"] = BASIS + "; distinct_phones exact within each row (sharding_key), never add across rows"
out(t23, "dr023_strategy_day_cid_geo.csv")

# ---------------- DR-026: LKUS_captcha vs SMS final REVIEW on one NY day ------------------------------------
cp = os.path.join(RAW, "dr026_captcha_extract.csv.gz")
if os.path.exists(cp):
    c = pd.read_csv(cp, dtype=str).drop_duplicates("id")
    c["t"] = pd.to_datetime(c.create_time)
    c["ny_date"] = c.t.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
    c = c[c.ny_date == a.dr026_day]
    rv = d[(d.ny_date == a.dr026_day) & d.sms & (d.final_result == "REVIEW")][["id", "t", "phone_h", "uid_h", "ip_h", "cid"]]
    res = []
    for key_r, key_c in (("phone_h", "phone_h"), ("uid_h", "uid_h"), ("ip_h", "ip_h")):
        mm = rv.dropna(subset=[key_r]).merge(c.dropna(subset=[key_c])[[key_c, "t", "final_result", "captcha_scene", "event_name", "v2_token_state"]]
                                               .rename(columns={key_c: key_r, "t": "t_c", "final_result": "captcha_result"}), on=key_r, how="left")
        mm["dt_s"] = (mm.t_c - mm.t).dt.total_seconds()
        matched = mm.dropna(subset=["dt_s"])
        res.append({"match_key": key_r.replace("_h", "") + " (salted hash, local only)", "sms_final_review_rows": len(rv),
                    "review_rows_with_any_captcha_same_key_same_day": int(matched.id.nunique()),
                    "captcha_rows_day": len(c), "captcha_rows_matching_a_review": int(c[c[key_c].isin(set(rv[key_r].dropna()))].id.nunique())})
        if key_r == "phone_h":
            best = matched.assign(adt=matched.dt_s.abs()).sort_values("adt").drop_duplicates("id")
            bins = [-86400, -3600, -600, -60, 0, 60, 600, 3600, 86400]
            labels = ["<-1h", "-1h..-10m", "-10m..-1m", "-1m..0", "0..+1m", "+1m..+10m", "+10m..+1h", ">+1h"]
            best["dt_bucket"] = pd.cut(best.dt_s, bins=bins, labels=labels, include_lowest=True)
            out(best.groupby(["dt_bucket", "captcha_result"], observed=True).id.count().reset_index(name="review_rows")
                .assign(note="nearest LKUS_captcha row with the same phone (captcha time - REVIEW time); NY " + a.dr026_day),
                "dr026_time_diff_buckets.csv")
            q = best.dt_s.describe(percentiles=[.1, .25, .5, .75, .9])
            out(pd.DataFrame([{"stat": k_, "seconds": round(float(v_), 1)} for k_, v_ in q.items()]), "dr026_time_diff_stats.csv")
    out(pd.DataFrame(res), "dr026_match_summary.csv")
    out(c.groupby(["cid", "captcha_scene", "event_name", "verify_code_type_name", "v2_token_state", "final_result"], dropna=False).id.count()
        .reset_index(name="rows"), "dr026_captcha_profile.csv")
# ---------------- DR-007: extra recall on an OTP-fill basis (derived, needs results/dr007_fill_rate_by_cc.csv) ----------
fp = os.path.join(R, "dr007_fill_rate_by_cc.csv")
if os.path.exists(fp):
    fr = pd.read_csv(fp, dtype={"cc": str})
    base = sorted(fr.period.unique())[0]                     # the earlier (pre-gap) period, chosen on the command line of p4_agg_drs.py
    rate = fr[fr.period == base].set_index("cc").fill_rate
    ex_ = S[S.final_result == "PASS"][["id", "cc", "pre"]].explode("pre").dropna(subset=["pre"])
    ex_["strategy_id"], ex_["result_name"] = ex_.pre.str[0], ex_.pre.str[1]
    ex_ = ex_[ex_.result_name != "PASS"]
    g = ex_.groupby(["strategy_id", "cc"]).id.nunique().reset_index(name="extra_recall_pv")
    g["cc_fill_rate_base"] = g.cc.map(rate)
    g["est_filled_if_same_rate"] = (g.extra_recall_pv * g.cc_fill_rate_base).round(1)
    t = g.groupby("strategy_id").agg(extra_recall_pv=("extra_recall_pv", "sum"),
                                     pv_with_rate=("cc_fill_rate_base", lambda x: int(g.loc[x.index][x.notna()].extra_recall_pv.sum())),
                                     est_filled_if_same_rate=("est_filled_if_same_rate", "sum")).reset_index()
    t["est_filled_share"] = (t.est_filled_if_same_rate / t.pv_with_rate.replace(0, np.nan)).round(4)
    t["basis"] = BASIS + f"; extra recall = pre-online non-PASS strategy hit with final PASS; fill rate per cc from upush stats {base} (UTC days); DERIVED: assumes hits fill like all sends of that cc"
    out(t.sort_values("extra_recall_pv", ascending=False), "dr007_otp_basis.csv")
    out(g.sort_values(["strategy_id", "extra_recall_pv"], ascending=[True, False]), "dr007_otp_basis_by_cc.csv")
print("done:", BASIS)
