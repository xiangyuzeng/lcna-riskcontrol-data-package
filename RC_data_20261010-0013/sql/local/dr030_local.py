#!/usr/bin/env python3
"""DR-030: strategy_43NaEzJmiQFk before / after it went online — hourly shape and retries of the numbers it alone rejected.

Inputs : E1 (e1lib.load_e1), results/config_strategy.csv (its expression), results/p2_oplog_timeline.csv (status timeline),
         results/config_resultcode.csv (REJECT-class names). Nothing about the strategy is hardcoded except its ID.
Basis  : SMS rule (email empty); window = from its creation (t_operation_log) to the end of NY 2026-10-09.
Condition met = its rule composition evaluated on the per-request rule results (ruleDetail); 'unknown' when a rule result
is missing. Unique reject = tk10 semantics (online hit with no other online REJECT-class hit; before the switch:
pre-online hit with no online REJECT-class hit).
Retries: numbers (salted phone hash, local only) the strategy alone rejected after the switch; every later request of the same
number in the window is a retry. Counts only leave this script.
Outputs: results/dr030_timeline.csv, dr030_hourly.csv, dr030_period_rates.csv, dr030_retries_summary.csv,
         dr030_retry_distribution.csv, dr030_crosscheck_tk10.csv"""
import os, re, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1lib import out, load_e1, unique_reject, R  # noqa: E402

SID = "strategy_43NaEzJmiQFk"
END = pd.Timestamp("2026-10-10 04:00:00")
st = pd.read_csv(os.path.join(R, "config_strategy.csv"), dtype=str).set_index("strategy_id")
tl = pd.read_csv(os.path.join(R, "p2_oplog_timeline.csv"), dtype=str)
x = tl[tl.object_id == SID].sort_values("operation_time_utc")
out(x[["operation_time_utc", "module", "operation_type", "object_id", "field", "before", "after"]], "dr030_timeline.csv")
created = pd.Timestamp(x[x.field == "(object)"].operation_time_utc.iloc[0])
to_pre = x[(x.field == "status") & (x.after == "2")].operation_time_utc
to_on = x[(x.field == "status") & (x.after == "1")].operation_time_utc
SW = pd.Timestamp(to_on.iloc[-1])
PRE0 = pd.Timestamp(to_pre.iloc[0]) if len(to_pre) else created
expr = st.loc[SID, "strategy_express"]
rids = re.findall(r"rule_[A-Za-z0-9]+", expr)
py = expr.replace("&&", " and ").replace("||", " or ")


def cond(rules):
    vals = {}
    for r in rids:
        v = rules.get(r)
        if v not in ("true", "false"):
            return "unknown"
        vals[r] = v == "true"
    return "met" if eval(re.sub(r"rule_[A-Za-z0-9]+", lambda m: str(vals[m.group(0)]), py)) else "not_met"


d = load_e1()
d = d[(d.create_time >= created) & (d.create_time < END) & d.sms].copy()
d["cond"] = d.rules.map(cond)
only_on, pre_no_on, s_on, s_pre = unique_reject(d, SID)
d["phase"] = np.where(d.create_time < SW, "pre_online", "online")
d["unique_reject"] = np.where(d.phase == "online", only_on, pre_no_on)
d["hit"] = np.where(d.phase == "online", s_on, s_pre)

# hourly shape by UTC hour x cc group
h = d.groupby(["utc_hour", "cc_group"]).agg(requests=("id", "size"), cond_met=("cond", lambda s: (s == "met").sum()),
                                             cond_unknown=("cond", lambda s: (s == "unknown").sum()), hits=("hit", "sum"),
                                             unique_rejects=("unique_reject", "sum"),
                                             final_pass=("final_result", lambda s: (s == "PASS").sum())).reset_index()
h["phase"] = np.where(pd.to_datetime(h.utc_hour + ":00:00") < SW.floor("h"), "pre_online", np.where(pd.to_datetime(h.utc_hour + ":00:00") == SW.floor("h"), "switch_hour", "online"))
out(h, "dr030_hourly.csv")

# per-24h rates per exact period and per half (time midpoint); online period also split at the 7-day marks of the run windows
periods = [("pre_online", PRE0, SW), ("online_first_24h", SW, SW + pd.Timedelta(hours=24)),
           ("online_day2_to_09-26", SW + pd.Timedelta(hours=24), pd.Timestamp("2026-09-27 04:00:00")),
           ("online_NY_09-27_to_10-02", pd.Timestamp("2026-09-27 04:00:00"), pd.Timestamp("2026-10-03 04:00:00")),
           ("online_NY_10-03_to_10-09", pd.Timestamp("2026-10-03 04:00:00"), END)]
rows = []
for name, a, b in periods:
    mid = a + (b - a) / 2
    for part, lo, hi in ((name, a, b), (name + " / 1st half", a, mid), (name + " / 2nd half", mid, b)):
        g = d[(d.create_time >= lo) & (d.create_time < hi)]
        hrs = (hi - lo).total_seconds() / 3600
        for grp in ("other", "+86", "+1"):
            gg = g[g.cc_group == grp]
            rows.append({"period": part, "start_utc": lo, "end_utc": hi, "hours": round(hrs, 2), "cc_group": grp,
                         "requests_per_24h": round(len(gg) / hrs * 24, 1),
                         "cond_met_per_24h": round((gg.cond == "met").sum() / hrs * 24, 1),
                         "cond_not_met_per_24h": round((gg.cond == "not_met").sum() / hrs * 24, 1),
                         "unique_rejects_per_24h": round(gg.unique_reject.sum() / hrs * 24, 1),
                         "final_pass_per_24h": round((gg.final_result == "PASS").sum() / hrs * 24, 1)})
out(pd.DataFrame(rows), "dr030_period_rates.csv")

# retries of numbers the strategy alone rejected after the switch
on = d[d.phase == "online"].sort_values("create_time")
ur = on[on.unique_reject & on.phone_h.notna()]
first = ur.groupby("phone_h").create_time.min()
later = on[on.phone_h.isin(first.index)].merge(first.rename("first_ur"), left_on="phone_h", right_index=True)
later = later[later.create_time > later.first_ur]
n_retry = later.groupby("phone_h").size().reindex(first.index, fill_value=0)
nxt = later.groupby("phone_h").create_time.min()
gap_min = ((nxt - first.reindex(nxt.index)).dt.total_seconds() / 60)
span_h = ((later.groupby("phone_h").create_time.max() - first.reindex(later.phone_h.unique())).dt.total_seconds() / 3600)
later_pass = later[later.final_result == "PASS"].phone_h.nunique()
ccg = ur.groupby("phone_h").cc_group.first()
summ = {"window_utc": f"[{SW}, {END})", "basis": "SMS", "numbers_uniquely_rejected": int(len(first)),
        "numbers_with_any_later_request": int((n_retry > 0).sum()), "share_with_later_request": round(float((n_retry > 0).mean()), 4) if len(first) else None,
        "later_requests_total": int(n_retry.sum()), "median_retries_per_number": float(n_retry.median()) if len(first) else None,
        "median_minutes_to_next_request": round(float(gap_min.median()), 2) if len(gap_min) else None,
        "p90_minutes_to_next_request": round(float(gap_min.quantile(0.9)), 2) if len(gap_min) else None,
        "median_hours_first_to_last_retry": round(float(span_h.median()), 2) if len(span_h) else None,
        "numbers_later_passed": int(later_pass),
        "numbers_with_later_request_after_24h": int(((later.create_time - later.first_ur) > pd.Timedelta(hours=24)).groupby(later.phone_h).any().sum())}
out(pd.DataFrame([summ]), "dr030_retries_summary.csv")
bins = [-1, 0, 1, 2, 5, 10, 20, 50, 10 ** 9]
labels = ["0", "1", "2", "3-5", "6-10", "11-20", "21-50", "51+"]
dist = pd.DataFrame({"retries": pd.cut(n_retry, bins=bins, labels=labels), "cc_group": ccg.reindex(n_retry.index)}) \
    .groupby(["cc_group", "retries"], observed=False).size().reset_index(name="numbers")
out(dist, "dr030_retry_distribution.csv")

# cross-check against pure-SQL tk10 (results/dr030_tk10_43na.csv) per NY day x cc group x phase x final result (SMS)
p = os.path.join(R, "dr030_tk10_43na.csv")
if os.path.exists(p):
    tk = pd.read_csv(p)
    tk = tk[tk.sms == 1]
    tk["phase"] = tk.phase.map({"before": "pre_online", "after": "online"})
    sq = tk.groupby(["ny_date", "cc_group", "phase", "final_result"]).agg(requests=("requests", "sum"),
                                                                          only=("s_online_only_reject", "sum"),
                                                                          pre=("s_preonline_no_online_reject", "sum"))
    sq["unique"] = np.where(sq.index.get_level_values("phase") == "online", sq.only, sq.pre)
    # E1 starts at creation: compare from the first full NY day after creation
    e = load_e1()
    e = e[e.sms & (e.create_time < END)].copy()
    o2, p2, _, _ = unique_reject(e, SID)
    e["phase"] = np.where(e.create_time < SW, "pre_online", "online")
    e["unique"] = np.where(e.phase == "online", o2, p2)
    ee = e.groupby(["ny_date", "cc_group", "phase", "final_result"]).agg(requests=("id", "size"), unique=("unique", "sum"))
    j = sq[["requests", "unique"]].join(ee, how="outer", lsuffix="_sql", rsuffix="_e1").fillna(0)
    j = j[j.index.get_level_values("ny_date") >= "2026-09-23"]
    out(pd.DataFrame([{"check": "tk10 vs E1, NY 09-23..10-09, SMS, ny_date x cc_group x phase x final_result",
                       "cells": len(j), "requests_mismatch": int((j.requests_sql != j.requests_e1).sum()),
                       "unique_mismatch": int((j.unique_sql != j.unique_e1).sum()),
                       "sql_requests": int(j.requests_sql.sum()), "e1_requests": int(j.requests_e1.sum()),
                       "sql_unique": int(j.unique_sql.sum()), "e1_unique": int(j.unique_e1.sum())}]), "dr030_crosscheck_tk10.csv")
print(pd.DataFrame([summ]).T.to_string(header=False))
print(pd.DataFrame(rows).query("cc_group == 'other'")[["period", "hours", "requests_per_24h", "cond_met_per_24h", "unique_rejects_per_24h", "final_pass_per_24h"]].to_string(index=False))
