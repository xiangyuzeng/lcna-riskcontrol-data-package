#!/usr/bin/env python3
"""DR-031 / DR-034 strategy-effect rates (P4 rules: timeline first, per-24h rates over exact periods and their halves, baseline
sensitivity; 计数分解，非因果). E1, SMS basis, requests in the strategy's current country-code list.
  results/dr034_rates.csv            : for strategy_WvNGjLMgoOyn and strategy_bYXaOJ4qXtW4 — per exact period (and each half):
                                       requests, PASS, online hits, unique REJECT per 24 h in the target codes
  results/dr034_baseline_sensitivity.csv : each strategy's after-switch rates vs every baseline period tried
  results/dr031_period_halves.csv    : the DR-031 periods of >= 6 h split into halves (15 original codes x IP class)"""
import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1lib import out, load_e1, unique_reject, R  # noqa: E402

END = pd.Timestamp("2026-10-10 04:00:00"); B0 = pd.Timestamp("2026-10-02 04:00:00")
tl = pd.read_csv(os.path.join(R, "p2_oplog_timeline.csv"), dtype=str)
sw = lambda sid, v: pd.Timestamp(tl[(tl.object_id == sid) & (tl.field == "status") & (tl.after == v)].operation_time_utc.iloc[-1])
cv = pd.read_csv(os.path.join(R, "dr031_code_versions.csv"), dtype=str)
C15, CNOW = set(cv.codes.iloc[0].split()), set(cv.codes.iloc[-1].split())
WIDEN = pd.Timestamp(cv.valid_from_utc.iloc[-1]) if cv.valid_from_utc.iloc[-1][0].isdigit() else None
d = load_e1()
d = d[d.sms & (d.create_time >= B0) & (d.create_time < END) & d.cc.isin(CNOW)].copy()
SW = {"strategy_WvNGjLMgoOyn": sw("strategy_WvNGjLMgoOyn", "1"), "strategy_bYXaOJ4qXtW4": sw("strategy_bYXaOJ4qXtW4", "1")}
for sid in SW:
    o, _, s_on, _ = unique_reject(d, sid)
    d[f"on_{sid}"], d[f"uq_{sid}"] = s_on, o


def rates(g, hrs, sid):
    k = 24 / hrs
    return {"requests_per_24h": round(len(g) * k, 1), "pass_per_24h": round((g.final_result == "PASS").sum() * k, 1),
            "online_hits_per_24h": round(g[f"on_{sid}"].sum() * k, 1), "unique_reject_per_24h": round(g[f"uq_{sid}"].sum() * k, 1)}


rows = []
for sid, t_sw in SW.items():
    periods = [("before: NY 10-02 start -> WvNG online", B0, SW["strategy_WvNGjLMgoOyn"])]
    if sid == "strategy_bYXaOJ4qXtW4":
        periods.append(("before: WvNG online -> bYXa online", SW["strategy_WvNGjLMgoOyn"], t_sw))
    periods.append(("after: switch -> end NY 10-09", t_sw, END))
    for name, a, b in periods:
        mid = a + (b - a) / 2
        for part, lo, hi in ((name, a, b), (name + " / 1st half", a, mid), (name + " / 2nd half", mid, b)):
            g = d[(d.create_time >= lo) & (d.create_time < hi)]
            hrs = (hi - lo).total_seconds() / 3600
            rows.append({"strategy_id": sid, "period": part, "start_utc": lo, "end_utc": hi, "hours": round(hrs, 2), **rates(g, hrs, sid)})
r = pd.DataFrame(rows)
out(r, "dr034_rates.csv")
sens = []
for sid in SW:
    x = r[r.strategy_id == sid].set_index("period")
    aft = "after: switch -> end NY 10-09"
    for base in [p for p in x.index if p.startswith("before")]:
        for m in ("requests_per_24h", "pass_per_24h"):
            b, a = x.loc[base, m], x.loc[aft, m]
            sens.append({"strategy_id": sid, "baseline": base, "after": aft, "metric": m, "baseline_rate": b, "after_rate": a,
                         "ratio_after_to_baseline": round(a / b, 3) if b else None})
out(pd.DataFrame(sens), "dr034_baseline_sensitivity.csv")
# DR-031 halves (15 original codes x IP class) for periods of at least 6 hours
p = pd.read_csv(os.path.join(R, "dr031_period_rates.csv"))
y = d[d.cc.isin(C15)]
hv = []
for per in p[p.hours >= 6].drop_duplicates("period").itertuples():
    a, b = pd.Timestamp(per.start_utc), pd.Timestamp(per.end_utc); mid = a + (b - a) / 2
    for half, lo, hi in (("1st half", a, mid), ("2nd half", mid, b)):
        g = y[(y.create_time >= lo) & (y.create_time < hi)]; hrs = (hi - lo).total_seconds() / 3600
        for geo in ("other", "us", "eq_phone", "unknown"):
            gg = g[g.ip_geo == geo]
            hv.append({"period": per.period, "half": half, "hours": round(hrs, 2), "ip_class": geo,
                       "requests_per_24h": round(len(gg) / hrs * 24, 1), "pass_per_24h": round((gg.final_result == "PASS").sum() / hrs * 24, 1)})
out(pd.DataFrame(hv), "dr031_period_halves.csv")
print(r.to_string(index=False))
print(pd.DataFrame(sens).to_string(index=False))
