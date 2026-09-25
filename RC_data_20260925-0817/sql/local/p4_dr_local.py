#!/usr/bin/env python3
"""P4: data requests answered from already-extracted data (no new DB reads).

Inputs : _local_only/raw/e1_a.csv.gz, e1_b.csv.gz (E1, row-level, local only), results/p4_daily_series.csv,
         results/config_rule.csv, results/p3_*.csv
Outputs: results/dr006_*.csv, dr008_*.csv, dr009_*.csv, dr010_*.csv, dr011_*.csv, dr012_*.csv (aggregates only)
Params : --start/--end NY window for E1-based answers; --baseline-days, --k for DR-010.
"""
import argparse, json, os
import numpy as np
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, RAW = os.path.join(PKG, "results"), os.path.join(PKG, "_local_only", "raw")
ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2026-09-18"); ap.add_argument("--end", default="2026-09-24")
ap.add_argument("--baseline-days", type=int, default=28); ap.add_argument("--k", default="3,5")
a = ap.parse_args()


def out(df, name):
    assert not [c for c in df.columns if str(c).endswith("_h")], name
    df.to_csv(os.path.join(R, name), index=False)
    return df


d = pd.concat([pd.read_csv(os.path.join(RAW, f), dtype=str) for f in ("e1_a.csv.gz", "e1_b.csv.gz")], ignore_index=True).drop_duplicates("id")
d["t"] = pd.to_datetime(d.create_time)
d["ny_date"] = d.t.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
d["cc"] = d.cc_raw.fillna("").str.lstrip("+")
d["cc_group"] = np.select([d.cc == "1", d.cc == "86", d.cc == ""], ["+1", "+86", "unknown"], "other")
d["app_state"] = np.where(d.app == "<absent>", "absent", "present")


def score(s):
    if not isinstance(s, str):
        return np.nan
    for e in json.loads(s):
        if e and e.get("score") is not None:
            return float(e["score"])
    return np.nan


d["v3_score"] = d.recaptcha_json.map(score)
W = d[(d.ny_date >= a.start) & (d.ny_date <= a.end) & (d.email_present == "0")].copy()

# ---------------- DR-006 cid 702 -------------------------------------------------------------------------
c7 = W[W.cid == "702"]
parts = []
for dim in ("app", "cid_origin", "ua_family", "ua_product", "version", "cc_group", "ip_country", "final_result", "token_state",
            "best_strategy_id", "n_features"):
    g = c7.groupby(dim, dropna=False).id.count().reset_index(name="rows").rename(columns={dim: "value"})
    g.insert(0, "dimension", dim); g["share"] = (g.rows / len(c7)).round(4)
    parts.append(g.sort_values("rows", ascending=False))
out(pd.concat(parts, ignore_index=True), "dr006_cid702_profile.csv")
out(pd.DataFrame([{"rows": len(c7), "distinct_phones": c7.phone_h.nunique(), "distinct_uids": c7.uid_h.nunique(),
                   "distinct_ip_c": c7.ip_c.nunique(), "days_present": c7.ny_date.nunique(),
                   "median_rows_per_day": float(c7.groupby("ny_date").size().median())}]), "dr006_cid702_summary.csv")

# ---------------- DR-008 time-of-day rules: which clock do they use? ----------------------------------------
rule = pd.read_csv(os.path.join(R, "config_rule.csv"))
tr = rule[rule.condition_type.isin(["TIME_AFTER", "TIME_BEFORE"])].set_index("rule_id")
rows = d[d.time_rules_json.notna()].copy()
tj = rows.time_rules_json.map(json.loads)
res, edge = [], []
for rid, r in tr.iterrows():
    obs = tj.map(lambda j, rid=rid: j.get(rid))
    m = obs.notna()
    if m.sum() == 0:
        continue
    o = (obs[m] == "true").values
    hh, mm = (int(x) for x in str(r.condition_value).split(":"))
    for off in range(-12, 15):
        lt = rows.loc[m, "t"] + pd.Timedelta(hours=off)
        sec = lt.dt.hour * 3600 + lt.dt.minute * 60 + lt.dt.second
        pred = (sec > hh * 3600 + mm * 60) if r.condition_type == "TIME_AFTER" else (sec < hh * 3600 + mm * 60)
        near = (np.abs(sec - (hh * 3600 + mm * 60)) <= 600).values
        res.append({"rule_id": rid, "condition": f"{r.condition_type} {r.condition_value}", "offset_hours_vs_utc": off, "rows": int(m.sum()),
                    "agreement": round(float((pred.values == o).mean()), 5), "rows_within_10min_of_boundary": int(near.sum()),
                    "agreement_within_10min": round(float((pred.values[near] == o[near]).mean()), 5) if near.sum() else np.nan})
res = pd.DataFrame(res)
out(res, "dr008_time_rule_offsets.csv")
best = res.sort_values("agreement", ascending=False).groupby("rule_id").head(3)
out(best, "dr008_time_rule_best_offsets.csv")
out(pd.DataFrame([{"push_rows_with_accessTime_key": 0, "note": "see results/p1_json_keys_summary.csv (para keys, all scenes)"}]), "dr008_note.csv")

# ---------------- DR-009 / DR-011 reCAPTCHA V3 score --------------------------------------------------------
s = W[W.v3_score.notna()].copy()
s["bucket"] = pd.cut(s.v3_score, [-0.01, 0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0], labels=["0-0.1", "0.1-0.3", "0.3-0.5", "0.5-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0"])
t11 = s.groupby(["cc_group", "cid", "bucket"], observed=False).id.count().reset_index(name="rows")
t11["share_within_ccgroup_cid"] = (t11.rows / t11.groupby(["cc_group", "cid"]).rows.transform("sum")).round(4)
out(t11[t11.groupby(["cc_group", "cid"]).rows.transform("sum") > 0], "dr011_v3_by_ccgroup_cid.csv")
q = s.groupby(["cc_group", "cid"]).v3_score.describe(percentiles=[.1, .25, .5, .75, .9]).reset_index()
out(q, "dr011_v3_quantiles.csv")
s["score_band"] = np.select([s.v3_score < 0.3, s.v3_score >= 0.8], ["low (<0.3)", "high (>=0.8)"], "mid")
parts = []
for dim in ("cc_group", "final_result", "cid", "app_state", "ip_country"):
    g = s.groupby(["score_band", dim]).id.count().reset_index(name="rows").rename(columns={dim: "value"})
    g.insert(1, "dimension", dim); g["share_within_band"] = (g.rows / g.groupby("score_band").rows.transform("sum")).round(4)
    parts.append(g)
out(pd.concat(parts, ignore_index=True).sort_values(["dimension", "score_band", "rows"], ascending=[True, True, False]), "dr009_low_vs_high_profile.csv")
out(W.assign(has=W.v3_score.notna()).groupby(["cc_group", "cid"]).agg(rows=("id", "count"), with_score=("has", "sum")).reset_index(),
    "dr011_score_coverage.csv")

# ---------------- DR-010 +1 SMS PASS daily baseline -------------------------------------------------------
ds = pd.read_csv(os.path.join(R, "p4_daily_series.csv"))
ds = ds[ds.email_key != 1]                             # SMS rule (DR-002): rows without an email key
day = ds.groupby("ny_date").apply(lambda g: pd.Series({
    "sms_requests": g.n.sum(),
    "plus1_requests": g.loc[g.cc_group == "+1", "n"].sum(),
    "plus1_pass": g.loc[(g.cc_group == "+1") & (g.result_col == "PASS"), "n"].sum(),
    "plus1_pass_distinct_phones": g.loc[(g.cc_group == "+1") & (g.result_col == "PASS"), "n_distinct_sharding_key"].sum(),
    "plus1_reject": g.loc[(g.cc_group == "+1") & (g.result_col == "REJECT"), "n"].sum(),
    "non_plus1_plus86_requests": g.loc[g.cc_group == "other", "n"].sum(),
    "plus86_requests": g.loc[g.cc_group == "+86", "n"].sum()}), include_groups=False).reset_index()
x = day.non_plus1_plus86_requests.astype(float).values
base = list(range(min(a.baseline_days, len(day))))
flags = {}
for k in (float(v) for v in a.k.split(",")):
    idx = set(base)
    for _ in range(10):                              # iterative exclusion of flagged baseline days
        b = x[sorted(idx)]
        med = np.median(b); mad = np.median(np.abs(b - med)) * 1.4826
        thr = med + k * mad
        new = {i for i in idx if x[i] <= thr}
        if new == idx:
            break
        idx = new
    day[f"attack_flag_k{k:g}"] = (x > thr).astype(int)
    day[f"threshold_k{k:g}"] = round(thr, 1)
    flags[k] = (med, mad, thr)
day["ny_week_monday"] = (pd.to_datetime(day.ny_date) - pd.to_timedelta(pd.to_datetime(day.ny_date).dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
out(day, "dr010_daily_plus1_pass.csv")
wk = day.groupby("ny_week_monday").agg(days=("ny_date", "count"), plus1_pass=("plus1_pass", "sum"), plus1_requests=("plus1_requests", "sum"),
                                       non_plus1_plus86_requests=("non_plus1_plus86_requests", "sum"),
                                       attack_days_k3=("attack_flag_k3", "sum"), attack_days_k5=("attack_flag_k5", "sum")).reset_index()
out(wk, "dr010_weekly_plus1_pass.csv")
out(pd.DataFrame([{"k": k, "baseline_first_days": a.baseline_days, "baseline_median": round(m, 1), "baseline_mad_scaled": round(s_, 1),
                   "threshold": round(t, 1), "first_flagged_day": day.loc[day[f"attack_flag_k{k:g}"] == 1, "ny_date"].min(),
                   "flagged_days": int(day[f"attack_flag_k{k:g}"].sum())} for k, (m, s_, t) in flags.items()]), "dr010_attack_rule.csv")

# ---------------- DR-012 empty app on cid 105/106 --------------------------------------------------------
e = W[W.cid.isin(["105", "106"])]
parts = []
for dim in ("ua_family", "ua_product", "cc_group", "ip_country", "final_result", "token_state", "cid_origin"):
    g = e.groupby(["cid", "app_state", dim]).id.count().reset_index(name="rows").rename(columns={dim: "value"})
    g.insert(2, "dimension", dim); g["share"] = (g.rows / g.groupby(["cid", "app_state"]).rows.transform("sum")).round(4)
    parts.append(g.sort_values(["cid", "app_state", "rows"], ascending=[True, True, False]))
out(pd.concat(parts, ignore_index=True), "dr012_empty_app_profile.csv")
vers = e.groupby(["cid", "app_state", "version"]).id.count().reset_index(name="rows")
vers["share"] = (vers.rows / vers.groupby(["cid", "app_state"]).rows.transform("sum")).round(4)
out(vers.sort_values(["cid", "app_state", "rows"], ascending=[True, True, False]), "dr012_versions.csv")
out(e.groupby(["cid", "app_state"]).agg(rows=("id", "count"), distinct_phones=("phone_h", "nunique"), distinct_uids=("uid_h", "nunique"),
                                        distinct_ip_c=("ip_c", "nunique")).reset_index(), "dr012_summary.csv")
print("done")
