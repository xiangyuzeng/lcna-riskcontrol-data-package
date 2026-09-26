#!/usr/bin/env python3
"""P4: data requests answered from this run's pure-SQL aggregates (runner outputs in results/). No DB reads here.
Outputs results/dr0xx_*_summary.csv etc. Params: --baseline-days / --k for DR-010; --fill-base A:B (UTC dates) for DR-007."""
import argparse, os
import numpy as np
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
ap = argparse.ArgumentParser()
ap.add_argument("--baseline-days", type=int, default=28); ap.add_argument("--k", default="3,5")
ap.add_argument("--fill-base", required=True); ap.add_argument("--fill-recent", required=True)
ap.add_argument("--checkpoint-ref", default="", help="reference counts to compare with, e.g. rows_cc_filter=N,pass_cc_filter=N,... (given on the command line, never stored in code)")
a = ap.parse_args()
rd = lambda n: pd.read_csv(os.path.join(R, n))
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5


def out(df, name):
    assert not [c for c in df.columns if str(c).endswith("_h")], name
    df.to_csv(os.path.join(R, name), index=False)
    return df


# ---------------- DR-003 standing: status codes of conditional / combo counter features per NY day -----------------
if ex("dr003_codes_daily.csv"):
    c = rd("dr003_codes_daily.csv")
    tf = rd("config_third_feature.csv").set_index("feature_id").feature_name
    p = c.groupby(["feature_id", "ny_date", "code"]).n.sum().unstack("code", fill_value=0).reset_index()
    p["rows"] = p.drop(columns=["feature_id", "ny_date"]).sum(axis=1)
    p.insert(1, "feature_name_now", p.feature_id.map(tf).fillna("<已删除>"))
    out(p, "dr003_codes_daily_pivot.csv")
    s = c.groupby(["feature_id", "code"]).n.sum().unstack("code", fill_value=0)
    s["rows"] = s.sum(axis=1)
    for col in s.columns:
        if col != "rows":
            s[col + "_share"] = (s[col] / s["rows"]).round(4)
    s["first_day"] = c.groupby("feature_id").ny_date.min(); s["last_day"] = c.groupby("feature_id").ny_date.max()
    s.insert(0, "feature_name_now", s.index.map(tf).fillna("<已删除>"))
    out(s.reset_index(), "dr003_codes_summary.csv")

# ---------------- DR-010 standing: daily series, +1 SMS PASS baseline and attack days --------------------------------
if ex("p4_daily_series.csv"):
    ds = rd("p4_daily_series.csv")
    ds = ds[ds.email_nonempty != 1]                           # SMS rule (DR-002): $.para.email empty or absent
    day = ds.groupby("ny_date").apply(lambda g: pd.Series({
        "sms_requests": g.n.sum(),
        "plus1_requests": g.loc[g.cc_group == "+1", "n"].sum(),
        "plus1_pass": g.loc[(g.cc_group == "+1") & (g.result_col == "PASS"), "n"].sum(),
        "plus1_pass_distinct_phones": g.loc[(g.cc_group == "+1") & (g.result_col == "PASS"), "n_distinct_sharding_key"].sum(),
        "plus1_reject": g.loc[(g.cc_group == "+1") & (g.result_col == "REJECT"), "n"].sum(),
        "non_plus1_plus86_requests": g.loc[g.cc_group == "other", "n"].sum(),
        "non_plus1_pass": g.loc[(g.cc_group != "+1") & (g.result_col == "PASS"), "n"].sum(),
        "plus86_requests": g.loc[g.cc_group == "+86", "n"].sum()}), include_groups=False).reset_index()
    x = day.non_plus1_plus86_requests.astype(float).values
    base = list(range(min(a.baseline_days, len(day))))
    rule_rows = []
    for k in (float(v) for v in a.k.split(",")):
        idx = set(base)
        for _ in range(20):
            b = x[sorted(idx)]
            med = np.median(b); mad = np.median(np.abs(b - med)) * 1.4826
            thr = med + k * mad
            new = {i for i in base if x[i] <= thr}
            if new == idx:
                break
            idx = new
        day[f"attack_flag_k{k:g}"] = (x > thr).astype(int)
        rule_rows.append({"k": k, "baseline": f"first {len(base)} days ({day.ny_date.iloc[0]}..{day.ny_date.iloc[len(base) - 1]})",
                          "baseline_days_kept": len(idx), "baseline_median": round(med, 1), "baseline_mad_scaled": round(mad, 1),
                          "threshold": round(thr, 1), "first_flagged_day": day.loc[day[f"attack_flag_k{k:g}"] == 1, "ny_date"].min(),
                          "flagged_days": int(day[f"attack_flag_k{k:g}"].sum()),
                          "flagged_days_last_30": int(day[f"attack_flag_k{k:g}"].tail(30).sum())})
    out(day, "dr010_daily_series.csv")
    out(pd.DataFrame(rule_rows), "dr010_attack_rule.csv")
    day["month"] = day.ny_date.str[:7]
    day["period"] = np.where(day.attack_flag_k5 == 1, "attack_day_k5", "normal_day_k5")
    per = day.groupby(["month", "period"]).agg(days=("ny_date", "count"), plus1_pass_mean=("plus1_pass", "mean"),
                                               plus1_pass_distinct_phones_mean=("plus1_pass_distinct_phones", "mean"),
                                               non_plus1_plus86_mean=("non_plus1_plus86_requests", "mean")).round(1).reset_index()
    out(per, "dr010_period_summary.csv")

# ---------------- DR-024: engine vs final by cid x version class (31 days) ------------------------------------------
if ex("dr024_engine_vs_final.csv"):
    e = rd("dr024_engine_vs_final.csv")
    e = e[e.sms == 1]
    g = e.groupby(["cid", "app_state", "version_class", "engine_result", "final_result"]).n.sum().reset_index()
    out(g.assign(basis="SMS rule, LKUS_push, NY 2026-08-25..2026-09-24; version_class ge_min = version >= 1.4.30 compared numerically"),
        "dr024_summary_31d.csv")
    dd = e.groupby(["ny_date", "cid", "engine_result", "final_result"]).n.sum().reset_index()
    out(dd, "dr024_daily_cid.csv")
    ar = e[e.cid.astype(str).isin(["105", "106"]) & (e.engine_result.str.startswith("REVIEW") | e.final_result.str.startswith("REVIEW"))]
    out(ar.groupby(["ny_date", "cid", "app_state", "version_class", "engine_result", "final_result"]).n.sum().reset_index(), "dr024_app_review_by_day.csv")

# ---------------- DR-022: per minute around NY midnight 09-18/19 -------------------------------------------------
if ex("dr022_reject_per_minute.csv"):
    m = rd("dr022_reject_per_minute.csv")
    p = m.groupby(["utc_minute", "final_result"]).n.sum().unstack(fill_value=0).reset_index()
    ps = m[m.sms == 1].groupby(["utc_minute", "final_result"]).n.sum().unstack(fill_value=0).add_prefix("sms_").reset_index()
    p = p.merge(ps, on="utc_minute", how="left").fillna(0)
    p.insert(1, "ny_minute", (pd.to_datetime(p.utc_minute) - pd.Timedelta(hours=4)).dt.strftime("%Y-%m-%d %H:%M"))
    out(p, "dr022_per_minute_summary.csv")

# ---------------- DR-025: hourly hits of named strategies ------------------------------------------------------------
if ex("dr025_hourly_hits.csv"):
    h = rd("dr025_hourly_hits.csv")
    hh = h.groupby(["strategy_id", "list", "utc_hour"]).agg(pv=("pv", "sum"), pass_pv=("pv", lambda s: 0)).reset_index()
    hp = h[h.final_result == "PASS"].groupby(["strategy_id", "list", "utc_hour"]).pv.sum().rename("final_pass_pv")
    hh = hh.drop(columns="pass_pv").merge(hp, on=["strategy_id", "list", "utc_hour"], how="left").fillna({"final_pass_pv": 0})
    out(hh, "dr025_hourly_summary.csv")
    h["utc_date"] = h.utc_hour.str[:10]
    out(h.groupby(["strategy_id", "list", "utc_date"]).pv.sum().unstack("list", fill_value=0).reset_index(), "dr025_daily_summary.csv")
    h["ny_date"] = (pd.to_datetime(h.utc_hour) - pd.Timedelta(hours=4)).dt.strftime("%Y-%m-%d")      # EDT window (no DST change inside)
    out(h.groupby(["strategy_id", "list", "ny_date"]).pv.sum().unstack("list", fill_value=0).reset_index(), "dr025_ny_daily_summary.csv")

# ---------------- DR-021: sharding key by scene -------------------------------------------------------------------
parts = [rd(f).assign(src=f) for f in ("dr021_sharding_key_by_scene.csv", "dr021_sharding_key_by_scene_0922.csv", "dr021_sharding_key_by_scene_0925.csv") if ex(f)]
if parts:
    k = pd.concat(parts, ignore_index=True)
    num = [c for c in k.columns if c.startswith(("sk_eq", "has_", "sk_empty", "sk_starts", "sk_all")) or c == "n"]
    g = k.groupby(["ny_date", "scene_id"])[num].sum().reset_index()
    g["sk_len_min"] = k.groupby(["ny_date", "scene_id"]).sk_len_min.min().values
    g["sk_len_max"] = k.groupby(["ny_date", "scene_id"]).sk_len_max.max().values
    for c in [c for c in num if c.startswith("sk_eq")]:
        g[c.replace("sk_eq_", "share_eq_")] = (g[c] / g.n).round(4)
    out(g, "dr021_summary.csv")
    eq = [c for c in g.columns if c.startswith("share_eq_")]
    best = []
    for r in g.itertuples(index=False):
        rr = r._asdict()
        mx = max(rr[c] for c in eq)
        at_max = sorted(c.replace("share_eq_", "") for c in eq if rr[c] == mx)
        nxt = sorted(((rr[c], c.replace("share_eq_", "")) for c in eq if rr[c] < mx), reverse=True)[:1]
        best.append({"ny_date": r.ny_date, "scene_id": r.scene_id, "rows": r.n, "best_candidates": "+".join(at_max), "best_share": mx,
                     "next_best": f"{nxt[0][1]} {nxt[0][0]}" if nxt else "", "sk_empty": r.sk_empty})
    out(pd.DataFrame(best), "dr021_best_candidate.csv")

# ---------------- DR-007: upush daily fill statistics vs risk SMS PASS by UTC day x cc ------------------------------
if ex("dr007_upush_daily.csv") and ex("dr007_risk_utc_daily.csv"):
    u = rd("dr007_upush_daily.csv"); u["cc"] = u.cc.astype(str)
    rk = rd("dr007_risk_utc_daily.csv").rename(columns={"utc_day": "utc_date"}); rk["cc"] = rk.cc.astype(str)
    rk = rk[rk.sms == 1]
    rp = rk[rk.final_result == "PASS"].groupby(["utc_date", "cc"]).agg(risk_sms_pass=("n", "sum"), risk_sms_pass_distinct_phones=("n_distinct_phones", "sum")).reset_index()
    ra = rk.groupby(["utc_date", "cc"]).n.sum().rename("risk_sms_requests").reset_index()
    uu = u.groupby(["statistic_date", "cc"]).agg(upush_sent=("sent_num", "sum"), upush_filled=("filled_num", "sum")).reset_index().rename(columns={"statistic_date": "utc_date"})
    j = ra.merge(rp, on=["utc_date", "cc"], how="outer").merge(uu, on=["utc_date", "cc"], how="outer").fillna(0)
    j["upush_fill_rate"] = np.where(j.upush_sent > 0, (j.upush_filled / j.upush_sent).round(4), np.nan)
    j["upush_sent_per_risk_pass"] = np.where(j.risk_sms_pass > 0, (j.upush_sent / j.risk_sms_pass).round(3), np.nan)
    out(j.sort_values(["utc_date", "risk_sms_requests"], ascending=[True, False]), "dr007_join_utc_day_cc.csv")
    j["ccg"] = np.select([j.cc == "1", j.cc == "86"], ["+1", "+86"], "other")
    d = j.groupby(["utc_date", "ccg"])[["risk_sms_requests", "risk_sms_pass", "upush_sent", "upush_filled"]].sum().reset_index()
    d["upush_fill_rate"] = (d.upush_filled / d.upush_sent.replace(0, np.nan)).round(4)
    d["upush_sent_per_risk_pass"] = (d.upush_sent / d.risk_sms_pass.replace(0, np.nan)).round(3)
    out(d, "dr007_daily_ccgroup.csv")
    rows = []
    for name, rng in (("base", a.fill_base), ("recent", a.fill_recent)):
        f0, f1 = rng.split(":")
        q = j[(j.utc_date >= f0) & (j.utc_date <= f1)].groupby("cc")[["risk_sms_pass", "upush_sent", "upush_filled"]].sum()
        q["fill_rate"] = (q.upush_filled / q.upush_sent.replace(0, np.nan)).round(4)
        q["sent_per_risk_pass"] = (q.upush_sent / q.risk_sms_pass.replace(0, np.nan)).round(3)
        q = q.reset_index(); q.insert(0, "period", f"{name} UTC {f0}..{f1}")
        rows.append(q)
    out(pd.concat(rows, ignore_index=True).sort_values(["period", "upush_sent"], ascending=[True, False]), "dr007_fill_rate_by_cc.csv")

# ---------------- checkpoint --------------------------------------------------------------------------------------
if ex("p5_checkpoint.csv"):
    c = rd("p5_checkpoint.csv")
    tot = c[["rows_no_cc_filter", "rows_cc_filter", "pass_cc_filter", "reject_cc_filter", "review_cc_filter"]].sum()
    ref = {kv.split("=")[0]: int(kv.split("=")[1]) for kv in a.checkpoint_ref.split(",") if "=" in kv}
    rows = [{"metric": m, "this_run": int(tot[m]), "reference": ref.get(m, ""), "diff": int(tot[m]) - ref[m] if m in ref else ""} for m in tot.index]
    for f in ("p5_checkpoint_edges.csv", "p5_checkpoint_edges_end.csv"):
        if ex(f):
            e = rd(f)
            rows.append({"metric": f"{f[:-4]} (10 min around the edge, rows_cc_filter)", "this_run": int(e.rows_cc_filter.sum()), "reference": "", "diff": ""})
    out(pd.DataFrame(rows), "p5_checkpoint_summary.csv")
print("agg DRs done")
