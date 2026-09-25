#!/usr/bin/env python3
"""P5: cross-check every toolkit test output (results/toolkit_tests/) against the P3/P4 results computed another way.
Writes results/toolkit_tests/_test_summary.csv."""
import json, os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, T, RAW = os.path.join(PKG, "results"), os.path.join(PKG, "results", "toolkit_tests"), os.path.join(PKG, "_local_only", "raw")
rows = []
def add(test, a, b):
    rows.append({"test": test, "toolkit": a, "reference": b, "equal": a == b})
m = pd.read_csv(os.path.join(T, "tk01_merged.csv")); m["ny"] = (pd.to_datetime(m.window_start_utc) - pd.Timedelta(hours=4)).dt.strftime("%Y-%m-%d")
u = pd.read_csv(os.path.join(R, "p3_distinct_users.csv")).set_index("ny_date")
for day in u.index[u.index != "7d"]:
    r = m[m.ny == day].iloc[0]
    add(f"tk01 {day} SMS distinct phones", int(r.phones_sms), int(u.loc[day, "distinct_phones"]))
    add(f"tk01 {day} SMS PASS +1 distinct phones", int(r.phones_sms_pass_home), int(u.loc[day, "pass_plus1_distinct_phones"]))
ds = pd.read_csv(os.path.join(R, "p4_daily_series.csv")).groupby("ny_date").n.sum()
for day in m.ny:
    add(f"tk01 {day} requests (all push rows)", int(m[m.ny == day].requests.iloc[0]), int(ds.loc[day]))
t2 = pd.read_csv(os.path.join(T, "tk02_merged.csv")); h = pd.read_csv(os.path.join(R, "p2_hits_7d.csv"))
add("tk02 strategy_MGj5bfGOijOi pre-online PV 7d", int(t2.pv.sum()), int(h[(h.list == "preonline") & (h.strategy_id == "strategy_MGj5bfGOijOi")].pv.sum()))
e = pd.concat([pd.read_csv(os.path.join(RAW, f), dtype=str) for f in ("e1_a.csv.gz", "e1_b.csv.gz")]).drop_duplicates("id")
e["ny"] = (pd.to_datetime(e.create_time) - pd.Timedelta(hours=4)).dt.strftime("%Y-%m-%d")
hit = e.hits_preonline.fillna("[]").map(lambda s: any(x.split("|")[0] == "strategy_MGj5bfGOijOi" for x in json.loads(s)))
x = e[hit].groupby("ny").phone_h.nunique()
t2["ny"] = (pd.to_datetime(t2.window_start_utc) - pd.Timedelta(hours=4)).dt.strftime("%Y-%m-%d")
for r in t2.itertuples():
    add(f"tk02 {r.ny} distinct phones", int(r.distinct_phones), int(x.get(r.ny, 0)))
s = pd.read_csv(os.path.join(R, "p3_strategies.csv"))
add("tk03 strategy_MGj5bfGOijOi extra recall PV 7d", int(pd.read_csv(os.path.join(T, "tk03_merged.csv")).extra_recall_pv.sum()),
    int(s[(s.list == "preonline") & (s.strategy_id == "strategy_MGj5bfGOijOi")].extra_recall_pv.iloc[0]))
t4 = pd.read_csv(os.path.join(T, "tk04_pass_leakage.csv"))
add("tk04 non-+1 SMS PASS rows 7d", int(t4[t4.email_key == 0].rows_pass.sum()), int(pd.read_csv(os.path.join(R, "p3_pass_leakage.csv")).query("dimension == 'cid'").rows.sum()))
for extra in ("tk05_check.csv", "tk06_check.csv", "tk07_check.csv"):
    p = os.path.join(T, extra)
    if os.path.exists(p):
        rows += pd.read_csv(p).to_dict("records")
out = pd.DataFrame(rows); out.to_csv(os.path.join(T, "_test_summary.csv"), index=False)
print(out.to_string(index=False)); print("all equal:", bool(out.equal.all()))
