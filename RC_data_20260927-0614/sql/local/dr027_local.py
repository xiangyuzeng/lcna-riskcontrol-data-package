#!/usr/bin/env python3
"""DR-027: why did non-+1 SMS PASS fall on NY 09-24 / 09-25? Local computation from the E1 extract, cross-checked
against the pure-SQL tk10 / tk08 results. Counts only; nothing row-level leaves this script.

Inputs : _local_only/raw/e1_a.csv.gz, e1_b.csv.gz (E1, row-level, salted hashes, local only)
         results/dr027_tk10_43na.csv, results/dr027_tk08_43na_hitStrategy.csv, results/dr027_tk08_43na_hitPreOnlineStrategy.csv
         results/config_resultcode.csv (REJECT- / REVIEW-class result names), results/p2_oplog_timeline.csv (switch time)
Params : --start / --end (NY dates, inclusive: DR-027's own window), --strategy
Outputs: results/dr027_e1_cells.csv            same cells as tk10, computed from E1
         results/dr027_crosscheck.csv          tk10 vs E1 and tk08 vs E1 (cells, mismatches)
         results/dr027_daily_decomposition.csv per NY day, SMS basis
         results/dr027_strategy_day_cid_geo.csv every strategy x day x cid x geo mismatch (online / pre-online), SMS basis
         results/dr027_period_rates.csv        per-24h rates over the exact pre-online / online periods (+ halves, 43Na-matching split)
         results/dr027_summary.csv             headline means, shares and their decomposition (derived, NY-day basis)
         results/dr027_baseline_sensitivity.csv the unique-block share of the drop under other before/after day sets
"""
import argparse, json, os
import numpy as np
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, RAW = os.path.join(PKG, "results"), os.path.join(PKG, "_local_only", "raw")
ap = argparse.ArgumentParser()
ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--strategy", required=True)
a = ap.parse_args()
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)


def out(df, name):
    assert not [c for c in df.columns if str(c).endswith("_h")], name
    df.to_csv(os.path.join(R, name), index=False)
    return df


rc = rd("config_resultcode.csv")
REJ = set(rc[rc.result_name.str.upper().str.startswith("REJECT")].result_name)
REV = set(rc[rc.result_name.str.upper().str.startswith("REVIEW")].result_name)
tl = rd("p2_oplog_timeline.csv")
sw = tl[(tl.object_id == a.strategy) & (tl.field == "status") & (tl.after.astype(str) == "1")].operation_time_utc.iloc[-1]
SW = pd.Timestamp(sw)
p0 = tl[(tl.object_id == a.strategy) & (tl.field == "status") & (tl.after.astype(str) == "2")].operation_time_utc
PRE0 = pd.Timestamp(p0.iloc[0]) if len(p0) else None          # when the strategy became pre-online (t_operation_log)

d = pd.concat([pd.read_csv(os.path.join(RAW, f), dtype=str) for f in ("e1_a.csv.gz", "e1_b.csv.gz")], ignore_index=True).drop_duplicates("id")
d["t"] = pd.to_datetime(d.create_time)
d["ny_date"] = d.t.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
d = d[(d.ny_date >= a.start) & (d.ny_date <= a.end)].copy()
cc = d.cc_raw.fillna("").str.lstrip("+")
d["cc_group"] = np.select([cc == "1", cc == "86", cc == ""], ["+1", "+86", "unknown"], "other")
d["sms"] = (d.email_present.astype(int) == 0).astype(int)
d["phase"] = np.where(d.t < SW, "before", "after")
lst = lambda s: [x.split("|") for x in json.loads(s)] if isinstance(s, str) else []
on, pre = d.hits_online.map(lst), d.hits_preonline.map(lst)
d["s_on"] = on.map(lambda l: int(any(h[0] == a.strategy for h in l)))
d["s_pre"] = pre.map(lambda l: int(any(h[0] == a.strategy for h in l)))
d["other_rej_on"] = on.map(lambda l: sum(1 for h in l if h[0] != a.strategy and h[1] in REJ))
d["other_rev_on"] = on.map(lambda l: sum(1 for h in l if h[0] != a.strategy and h[1] in REV))
d["uniq_on"] = ((d.s_on == 1) & (d.other_rej_on == 0)).astype(int)
d["uniq_pre"] = ((d.s_pre == 1) & (d.other_rej_on == 0)).astype(int)

keys = ["ny_date", "cc_group", "sms", "phase", "final_result"]
e1 = d.groupby(keys).agg(requests=("id", "count"), s_online_hits=("s_on", "sum"), s_preonline_hits=("s_pre", "sum"),
                         s_online_only_reject=("uniq_on", "sum"), s_preonline_no_online_reject=("uniq_pre", "sum"),
                         other_online_reject_hit=("other_rej_on", lambda x: int((x > 0).sum()))).reset_index()
out(e1, "dr027_e1_cells.csv")

cx = []
sq = rd("dr027_tk10_43na.csv")
sq = sq.groupby(keys)[[c for c in e1.columns if c not in keys]].sum()
j = pd.concat([sq.stack().rename("sql"), e1.set_index(keys).stack().rename("e1")], axis=1).fillna(0)
cx.append({"check": f"tk10 (pure SQL) vs E1: {a.strategy}, cells = day x cc group x sms x phase x final x metric", "cells": len(j),
           "mismatching_cells": int((j.sql != j.e1).sum()), "sql_requests": int(sq.requests.sum()), "e1_requests": int(e1.requests.sum())})
S = d[d.sms == 1]
for lname, flag in (("hitStrategy", "s_on"), ("hitPreOnlineStrategy", "s_pre")):
    t8 = rd(f"dr027_tk08_43na_{lname}.csv", dtype={"cid": str})
    t8["ny_date"] = (pd.to_datetime(t8.window_start_utc) - pd.Timedelta(hours=4)).dt.strftime("%Y-%m-%d")
    a8 = t8[t8.level == "group"].groupby(["ny_date", "cid", "geo_mismatch", "final_result"]).pv.sum()
    x = S[S[flag] == 1].assign(geo_mismatch=lambda z: (z.phone_country.fillna("") != z.ip_country.fillna("")).astype(int))
    b8 = x.groupby(["ny_date", "cid", "geo_mismatch", "final_result"]).id.count()
    jj = pd.concat([a8.rename("sql"), b8.rename("e1")], axis=1).fillna(0)
    cx.append({"check": f"tk08 (pure SQL) vs E1: {a.strategy} {lname} PV, cells = day x cid x geo x final", "cells": len(jj),
               "mismatching_cells": int((jj.sql != jj.e1).sum()), "sql_requests": int(a8.sum()), "e1_requests": int(b8.sum())})
out(pd.DataFrame(cx), "dr027_crosscheck.csv")

# ---- daily decomposition, SMS basis ------------------------------------------------------------------------
rows = []
for day, g in S.groupby("ny_date"):
    r = {"ny_date": day, "phase_on_day": "/".join(sorted(g.phase.unique(), reverse=True))}
    for grp in ("+1", "+86", "other"):
        gg = g[g.cc_group == grp]
        r[f"requests_{grp}"] = len(gg)
        r[f"pass_{grp}"] = int((gg.final_result == "PASS").sum())
    r["pass_non_plus1"] = r["pass_+86"] + r["pass_other"]
    nb = g[g.cc_group.isin(["+86", "other"])]
    ua = nb[(nb.uniq_on == 1)]                                   # online, only REJECT-class hit (after the switch)
    ub = nb[(nb.uniq_pre == 1) & (nb.phase == "before")]          # pre-online, no online REJECT-class hit (before the switch)
    r["s_online_only_reject_non_plus1"] = len(ua)
    r["s_online_only_reject_non_plus1_final_reject"] = int((ua.final_result == "REJECT").sum())
    r["s_online_only_reject_non_plus1_would_be_pass"] = int(((ua.final_result == "REJECT") & (ua.other_rev_on == 0)).sum())
    r["s_online_only_reject_non_plus1_would_be_review"] = int(((ua.final_result == "REJECT") & (ua.other_rev_on > 0)).sum())
    r["s_preonline_no_online_reject_non_plus1"] = len(ub)
    r["s_preonline_no_online_reject_non_plus1_final_pass"] = int((ub.final_result == "PASS").sum())
    r["s_preonline_no_online_reject_non_plus1_after_switch"] = int(((nb.uniq_pre == 1) & (nb.phase == "after")).sum())
    r["s_online_only_reject_non_plus1_would_be_pass_distinct_phones"] = int(ua[(ua.final_result == "REJECT") & (ua.other_rev_on == 0)].phone_h.nunique())
    r["other_online_reject_share_non_plus1"] = round(float((nb.other_rej_on > 0).mean()), 4) if len(nb) else None
    r["s_online_only_reject_plus1"] = int(((g.cc_group == "+1") & (g.uniq_on == 1)).sum())
    r["s_preonline_no_online_reject_plus1"] = int(((g.cc_group == "+1") & (g.uniq_pre == 1)).sum())
    r["pass_non_plus1_if_strategy_absent"] = r["pass_non_plus1"] + r["s_online_only_reject_non_plus1_would_be_pass"]
    r["pass_non_plus1_other_cc_only"] = r["pass_other"]
    rows.append(r)
dd = pd.DataFrame(rows)
dd["note"] = ("SMS basis; non_plus1 = +86 + other; 'if_strategy_absent' = actual PASS + requests the strategy alone rejected that "
              "had no other REVIEW-class online hit (derived: assumes the other strategies' verdicts unchanged; PV basis, a rejected "
              "phone may retry, so an upper bound); pre-online unique = before the switch only (after_switch column = the rest)")
out(dd, "dr027_daily_decomposition.csv")

# ---- per-24h rates over the exact pre-online and online periods (the strategy did not exist before PRE0) -----------
nb = S[S.cc_group.isin(["+86", "other"])]
end_utc = pd.Timestamp(pd.Timestamp(a.end) + pd.Timedelta(days=1, hours=4))       # NY day end in UTC (EDT window)
nb = nb.assign(match=((nb.s_on == 1) | (nb.s_pre == 1)).astype(int))   # the strategy's conditions held (hit in either list)
mid = pd.Timestamp(f"{SW.date()} 04:00:00")                                  # NY midnight (EDT) inside the pre-online period
per = [("pre-online (would-be unique REJECT)", PRE0, SW, "uniq_pre"), ("online (actual unique REJECT)", SW, end_utc, "uniq_on")]
if PRE0 is not None and PRE0 < mid < SW:
    per += [("pre-online, part 1 (before NY midnight)", PRE0, mid, "uniq_pre"), ("pre-online, part 2 (NY 09-23 morning)", mid, SW, "uniq_pre")]
rows = []
for name, t0, t1, col in per:
    if t0 is None:
        continue
    w = nb[(nb.t >= t0) & (nb.t < t1)]
    hrs = (t1 - t0).total_seconds() / 3600
    f = lambda v: round(v / hrs * 24, 1)
    m, u = w[w.match == 1], w[w.match == 0]
    rows.append({"period": name, "utc_from": str(t0), "utc_to": str(t1), "hours": round(hrs, 2), "non_plus1_sms_requests": len(w),
                 "non_plus1_sms_pass": int((w.final_result == "PASS").sum()), "unique_reject_hits": int(w[col].sum()),
                 "unique_reject_hits_per_24h": f(w[col].sum()), "non_plus1_requests_per_24h": f(len(w)),
                 "non_plus1_pass_per_24h": f((w.final_result == "PASS").sum()),
                 "strategy_match_requests": len(m), "strategy_match_requests_per_24h": f(len(m)),
                 "no_match_requests": len(u), "no_match_requests_per_24h": f(len(u)),
                 "no_match_pass": int((u.final_result == "PASS").sum()), "no_match_pass_per_24h": f((u.final_result == "PASS").sum())})
out(pd.DataFrame(rows).assign(basis="SMS basis, non-+1 (= +86 + other); periods from t_operation_log status changes; "
      "strategy_match = the strategy hit in either list (its conditions held); no_match = the rest"), "dr027_period_rates.csv")

# ---- headline means and their decomposition (NY days; derived) --------------------------------------------------
day = dd.set_index("ny_date")
days = sorted(day.index)
before = [x for x in days if day.loc[x, "phase_on_day"] == "before"]
after = [x for x in days if day.loc[x, "phase_on_day"] == "after"]
req = day["requests_+86"] + day["requests_other"]
def split(b, a_):
    pb, pa = day.loc[b, "pass_non_plus1"].mean(), day.loc[a_, "pass_non_plus1"].mean()
    rb, ra = req.loc[b].mean(), req.loc[a_].mean()
    un = day.loc[a_, "s_online_only_reject_non_plus1_would_be_pass"].mean()
    drop = pb - pa
    return {"before_days": f"{b[0]}..{b[-1]}" if len(b) > 1 else b[0], "after_days": f"{a_[0]}..{a_[-1]}" if len(a_) > 1 else a_[0],
            "pass_before_mean": round(pb, 2), "pass_after_mean": round(pa, 2), "drop": round(drop, 2), "unique_block_mean": round(un, 2),
            "unique_share_of_drop": round(un / drop, 4) if drop > 0 else None, "requests_before_mean": round(rb, 2), "requests_after_mean": round(ra, 2)}
hs = split(before, after)
rate_b = hs["pass_before_mean"] / hs["requests_before_mean"]
cf = hs["pass_after_mean"] + hs["unique_block_mean"]
vol = (hs["requests_before_mean"] - hs["requests_after_mean"]) * rate_b
summ = [("pass_non_plus1_before_mean", hs["pass_before_mean"]), ("pass_non_plus1_after_mean", hs["pass_after_mean"]), ("drop", hs["drop"]),
        ("unique_block_would_be_pass_mean_after", hs["unique_block_mean"]), ("pass_if_strategy_absent_mean_after", round(cf, 2)),
        ("unique_share_of_drop", hs["unique_share_of_drop"]), ("residual", round(hs["drop"] - hs["unique_block_mean"], 2)),
        ("residual_share_of_drop", round(1 - hs["unique_share_of_drop"], 4)),
        ("requests_non_plus1_before_mean", hs["requests_before_mean"]), ("requests_non_plus1_after_mean", hs["requests_after_mean"]),
        ("pass_rate_before", round(rate_b, 4)), ("pass_rate_after_if_strategy_absent", round(cf / hs["requests_after_mean"], 4)),
        ("volume_effect_at_before_pass_rate", round(vol, 2)), ("rate_effect_remaining_traffic", round(hs["drop"] - hs["unique_block_mean"] - vol, 2)),
        ("other_online_reject_share_before", round(float((nb[nb.ny_date.isin(before)].other_rej_on > 0).mean()), 4)),
        ("other_online_reject_share_after", round(float((nb[nb.ny_date.isin(after)].other_rej_on > 0).mean()), 4))]
out(pd.DataFrame(summ, columns=["metric", "value"]).assign(
    window=f"before = NY {hs['before_days']}, after = NY {hs['after_days']} (per-day means; the mixed day excluded)",
    basis="SMS basis, non-+1 (= +86 + other); derived arithmetic, not a causal estimate; rate effect = residual - volume effect"),
    "dr027_summary.csv")
sens = []
for b in (before, before[1:], before[2:], before[-1:], [x for x in before if x < "2026-09-22"], before[1:3]):
    for a_ in (after, after[:2]):
        if b and a_:
            sens.append(split(b, a_))
out(pd.DataFrame(sens).drop_duplicates(["before_days", "after_days"]).assign(basis="SMS basis, non-+1, per-day means; derived"),
    "dr027_baseline_sensitivity.csv")

# ---- every strategy x day x cid x geo mismatch, SMS basis (the E1 form of tk08) ---------------------------------
parts = []
for lname, col in (("online", on), ("preonline", pre)):
    ex = S[["id", "ny_date", "cid", "phone_h", "final_result", "phone_country", "ip_country"]].assign(h=col.loc[S.index]).explode("h").dropna(subset=["h"])
    ex["strategy_id"] = ex.h.str[0]
    ex["geo_mismatch"] = (ex.phone_country.fillna("") != ex.ip_country.fillna("")).astype(int)
    g = ex.groupby(["strategy_id", "ny_date", "cid", "geo_mismatch"]).agg(hit_pv=("id", "nunique"), distinct_phones=("phone_h", "nunique"),
                                                                         final_pass_pv=("final_result", lambda s: int((s == "PASS").sum()))).reset_index()
    g.insert(0, "list", lname); parts.append(g)
t = pd.concat(parts, ignore_index=True)
t["basis"] = f"SMS rule (email empty), LKUS_push, NY {a.start}..{a.end}; distinct_phones exact within each row, never add across rows"
out(t, "dr027_strategy_day_cid_geo.csv")
print(pd.DataFrame(cx).to_string(index=False)); print(dd.drop(columns=["note"]).to_string(index=False))
