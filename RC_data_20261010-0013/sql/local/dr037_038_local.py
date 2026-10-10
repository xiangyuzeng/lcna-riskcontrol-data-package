#!/usr/bin/env python3
"""DR-037 and DR-038 summaries from aggregate-only query results (no identifiers anywhere).
DR-037: results/dr037_crm_members.csv (per registration month x area code x status) is summed locally into one row per area code;
  cells below 5 are written as '<5'. Compared with SMS requests / PASS per country code from L1 — different units (members are
  people, PASS are requests); never a conversion rate. Paying users per order phone code (salesorder) per 30-day window; distinct
  counts are not additive across windows.
DR-038: results/dr038_sw3j_20260921.csv and dr038_sw3j_7d.csv (strategy_sw3jC7bvFYEX hits vs the whitelist, matched in SQL)."""
import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1lib import out, R, PKG  # noqa: E402

ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
sup = lambda v: "<5" if 0 < v < 5 else int(v)
if os.path.exists(os.path.join(PKG, "_local_only", "raw", "dr037_crm_members.csv")):
    m = pd.read_csv(os.path.join(PKG, "_local_only", "raw", "dr037_crm_members.csv"), dtype={"cc": str})
    m["cc"] = m.cc.fillna("")
    num = ["members", "new_30d", "with_first_pay", "with_first_order", "last_order_in_90d", "with_finished_order", "no_profile_row"]
    act = m[m.user_status.astype(str) == "1"].groupby("cc")[num].sum()
    allm = m.groupby("cc")[num].sum().add_prefix("all_status_")
    t = act.join(allm, how="outer").fillna(0).astype(int)
    t = t.drop(columns=[c for c in t.columns if c.startswith("all_status_")])   # differences to the status-1 columns could reveal small counts
    a1 = m[m.user_status.astype(str) == "1"]
    t["members_registered_before_0901"] = a1[a1.month_start_utc < "2026-09-01"].groupby("cc").members.sum().reindex(t.index).fillna(0).astype(int)
    t["members_registered_since_0901"] = t.members - t.members_registered_before_0901
    cv = pd.read_csv(os.path.join(R, "dr031_code_versions.csv"), dtype=str)
    C15, CNOW = set(cv.codes.iloc[0].split()), set(cv.codes.iloc[-1].split())
    L = pd.read_csv(os.path.join(R, "l1_long.csv"), dtype={"cc": str})
    L = L[(L.lvl == "h") & (L.sms == 1) & (L.tenant_lkus == 1)]
    L["cc"] = L.cc.fillna("")
    for lab, a, b in (("last 7 NY days 10-03..10-09", "2026-10-03", "2026-10-09"), ("attack NY 09-03..10-09", "2026-09-03", "2026-10-09"),
                      ("pre-attack NY 06-01..09-02", "2026-06-01", "2026-09-02")):
        g = L[(L.ny_date >= a) & (L.ny_date <= b)]
        t[f"sms_requests {lab}"] = g.groupby("cc").n.sum().reindex(t.index).fillna(0).astype(int)
        t[f"sms_pass {lab}"] = g[g.final_result == "PASS"].groupby("cc").n.sum().reindex(t.index).fillna(0).astype(int)
    t["code_set"] = [("+1" if c == "1" else "15 original" if c in C15 else "6 added" if c in CNOW else "other") for c in t.index]
    t = t.reset_index().rename(columns={"index": "cc"})
    keep = (t.code_set != "other") | (t.members >= 5) | (t[[c for c in t.columns if c.startswith("sms_pass")]].sum(axis=1) > 0)
    t = t[keep]
    sb, ss = t.members_registered_before_0901.copy(), t.members_registered_since_0901.copy()
    for c in num + ["members_registered_before_0901", "members_registered_since_0901"]:
        t[c] = t[c].map(sup)
    # complementary suppression: before + since = members, so when one part is <5 the other is written as '>=5'
    t.loc[(ss > 0) & (ss < 5) & (sb >= 5), "members_registered_before_0901"] = ">=5"
    t.loc[(sb > 0) & (sb < 5) & (ss >= 5), "members_registered_since_0901"] = ">=5"
    out(t.sort_values(["code_set", "cc"]), "dr037_members_by_cc.csv")
    tot = m[m.user_status.astype(str) == "1"][num].sum()
    out(pd.DataFrame([{"scope": "LKUS members with status 1, all area codes", **{k: int(v) for k, v in tot.items()}}]), "dr037_members_total.csv")
if ex("dr037_order_paying.csv"):
    o = pd.read_csv(os.path.join(R, "dr037_order_paying.csv"), dtype={"cc": str})
    o["cc"] = o.cc.fillna("")
    g = o.groupby(["window_start_utc", "window_end_utc", "cc"]).agg(paid_orders=("paid_orders", "sum"), paying_users=("paying_users", "sum")).reset_index()
    g["paying_users"] = g.paying_users.map(sup); g["paid_orders"] = g.paid_orders.map(sup)
    out(g, "dr037_paying_by_phone_code.csv")
for f in ("dr038_sw3j_20260921.csv", "dr038_sw3j_20260921_v2.csv", "dr038_sw3j_7d.csv"):
    if ex(f):
        s = pd.read_csv(os.path.join(R, f))
        k = ["ny_date", "hit_list", "sms", "final_result", "ipc_format", "ipc_in_whitelist_now", "ipc_in_whitelist_asof", "phone_in_whitelist_now"]
        g = s.groupby(k).agg(hits=("hits", "sum"), distinct_phones=("distinct_phones", "sum")).reset_index()
        out(g, f.replace(".csv", "_summary.csv"))
        print(f, g.to_string(index=False))
