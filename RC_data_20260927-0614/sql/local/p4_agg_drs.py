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
ap.add_argument("--fill-base", default=""); ap.add_argument("--fill-recent", default="")
ap.add_argument("--checkpoint-ref", default="", help="reference counts to compare with, e.g. rows_cc_filter=N,pass_cc_filter=N,... (given on the command line, never stored in code)")
a = ap.parse_args()
rd = lambda n: pd.read_csv(os.path.join(R, n))
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5


def out(df, name):
    assert not [c for c in df.columns if str(c).endswith("_h")], name
    df.to_csv(os.path.join(R, name), index=False)
    return df


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

# ---------------- DR-014 standing: sharding key per scene group on one NY day (DR-021 method) ------------------------
if ex("dr014_sharding_key_by_scene_20260926.csv") or [f for f in os.listdir(R) if f.startswith("dr014_sharding_key_by_scene_")]:
    f14 = sorted(f for f in os.listdir(R) if f.startswith("dr014_sharding_key_by_scene_") and f.endswith(".csv"))[-1]
    k = rd(f14)
    num = [c for c in k.columns if c.startswith(("sk_eq", "has_", "sk_empty", "sk_starts", "sk_all")) or c == "n"]
    g = k.groupby(["ny_date", "scene_id"])[num].sum().reset_index()
    for c in [c for c in num if c.startswith("sk_eq")]:
        g[c.replace("sk_eq_", "share_eq_")] = (g[c] / g.n).round(4)
    eq = [c for c in g.columns if c.startswith("share_eq_")]
    best = []
    for r in g.itertuples(index=False):
        rr = r._asdict(); mx = max(rr[c] for c in eq)
        at_max = sorted(c.replace("share_eq_", "") for c in eq if rr[c] == mx)
        nxt = sorted(((rr[c], c.replace("share_eq_", "")) for c in eq if rr[c] < mx), reverse=True)[:1]
        grp = "phone" if "fullPhoneNo" in at_max else ("userNo" if "userNo" in at_max else "other")
        best.append({"ny_date": r.ny_date, "scene_id": r.scene_id, "rows": r.n, "best_candidates": "+".join(at_max), "best_share": mx,
                     "scene_group": grp, "next_best": f"{nxt[0][1]} {nxt[0][0]}" if nxt else "", "sk_empty": r.sk_empty})
    out(g, "dr014_summary.csv"); out(pd.DataFrame(best), "dr014_best_candidate.csv")

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
