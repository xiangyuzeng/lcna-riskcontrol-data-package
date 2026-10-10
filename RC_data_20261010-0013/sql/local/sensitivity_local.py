#!/usr/bin/env python3
"""Baseline sensitivity for the strategy-effect DRs (P4 rules): the same before/after comparison with every baseline tried.
DR-030 (43Na): per-24h rate of non-+1/+86 SMS requests meeting / not meeting its condition, each "after" period vs each baseline
         (pre-online whole, 1st half, 2nd half) -> results/dr030_baseline_sensitivity.csv
DR-031 (bYXa): per-24h SMS requests and PASS of the 15 original codes by IP class, after it went online (after the country rule was
         widened) vs each earlier period -> results/dr031_baseline_sensitivity.csv
Counts only; a ratio < 1 means fewer per 24 h than in that baseline. 计数分解，非因果."""
import os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
pr = pd.read_csv(os.path.join(R, "dr030_period_rates.csv")); o = pr[pr.cc_group == "other"].set_index("period")
rows = []
for base in ("pre_online", "pre_online / 1st half", "pre_online / 2nd half"):
    for aft in ("online_first_24h", "online_day2_to_09-26", "online_NY_09-27_to_10-02", "online_NY_10-03_to_10-09"):
        for m in ("cond_met_per_24h", "cond_not_met_per_24h", "final_pass_per_24h"):
            b, a = o.loc[base, m], o.loc[aft, m]
            rows.append({"baseline": base, "after": aft, "metric": m, "baseline_rate": b, "after_rate": a, "ratio_after_to_baseline": round(a / b, 3) if b else None})
pd.DataFrame(rows).to_csv(os.path.join(R, "dr030_baseline_sensitivity.csv"), index=False)
p = pd.read_csv(os.path.join(R, "dr031_period_rates.csv"))
p = p[(p.code_set == "15 original") & (p.hours >= 6)]           # periods shorter than 6 hours are too thin for a rate
after = p[p.period.str.startswith("country rule widened")]
rows = []
for bp in sorted(set(p.period) - set(after.period)):
    for geo in ("other", "us", "eq_phone"):
        b = p[(p.period == bp) & (p.ip_class == geo)].iloc[0]; a = after[after.ip_class == geo].iloc[0]
        for m in ("requests_per_24h", "pass_per_24h"):
            rows.append({"baseline": bp, "baseline_hours": b.hours, "after": a.period, "after_hours": a.hours, "ip_class": geo, "metric": m,
                         "baseline_rate": b[m], "after_rate": a[m], "ratio_after_to_baseline": round(a[m] / b[m], 3) if b[m] else None})
pd.DataFrame(rows).to_csv(os.path.join(R, "dr031_baseline_sensitivity.csv"), index=False)
print(pd.DataFrame(rows).to_string(index=False))
