#!/usr/bin/env python3
"""Point 8 open exploration (NY 2026-09-25..10-09, SMS basis, E1; counts only leave this script).
  x1 codes      : non-+1 country codes, SMS requests / PASS per NY day; prior week (09-26..10-02) vs last week (10-03..10-09);
                  first day seen in E1; price-weighted PASS (prompt's public price list, ranking only)  -> x1_codes_weekly.csv
  x2 bypass     : requests in the current code list of the shared country rule after WvNG went online, by whether an online
                  10-08/10-09 strategy hit, IP class and final result                            -> x2_bypass_after_switch.csv
                  non-+1 PASS after bYXa went online by code: in list / not in list               -> x2_nonplus1_pass_after_byxa.csv
  x3 shifts     : week-on-week shares (non-+1 SMS): V3 bucket, cid, app state, version class, IP country (top), NY hour -> x3_shifts.csv
  x4 hourly     : non-+1 SMS requests and PASS per NY hour of day, both weeks                      -> x4_hour_of_day.csv"""
import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1lib import out, load_e1, unique_reject, R  # noqa: E402

d = load_e1()
S = d[d.sms & (d.ny_date >= "2026-09-25") & (d.ny_date <= "2026-10-09")].copy()
S["week"] = np.select([S.ny_date <= "2026-10-02", S.ny_date >= "2026-10-03"], ["prior 09-26..10-02", "last 10-03..10-09"], "")
S.loc[S.ny_date < "2026-09-26", "week"] = "09-25"
N = S[S.cc_group != "+1"]
price = pd.read_csv(os.path.join(R, "dr033_price_reference.csv"), dtype={"cc": str}).set_index("cc").usd_per_sms_public_max
first_seen = d[d.sms & (d.cc_group != "+1")].groupby("cc").ny_date.min()
w = N[N.week.str.startswith(("prior", "last"))].pivot_table(index="cc", columns="week", values="id", aggfunc="count", fill_value=0)
wp = N[N.week.str.startswith(("prior", "last")) & (N.final_result == "PASS")].pivot_table(index="cc", columns="week", values="id", aggfunc="count", fill_value=0)
x1 = w.add_prefix("requests ").join(wp.add_prefix("pass "), how="left").fillna(0).astype(int)
x1["first_seen_in_e1"] = first_seen.reindex(x1.index)
x1["usd_public_price"] = price.reindex(x1.index)
x1["rank_value_last_week"] = (x1.get("pass last 10-03..10-09", 0) * x1.usd_public_price).round(2)
x1["phone_country"] = N.groupby("cc").phone_country.agg(lambda s: s.mode().iat[0] if len(s.dropna()) else "")
cv = pd.read_csv(os.path.join(R, "dr031_code_versions.csv"), dtype=str)
CNOW = set(cv.codes.iloc[-1].split())
x1["in_current_country_rule"] = x1.index.isin(CNOW).astype(int)
out(x1.reset_index().sort_values("rank_value_last_week", ascending=False), "x1_codes_weekly.csv")

tl = pd.read_csv(os.path.join(R, "p2_oplog_timeline.csv"), dtype=str)
sw = lambda sid: pd.Timestamp(tl[(tl.object_id == sid) & (tl.field == "status") & (tl.after == "1")].operation_time_utc.iloc[-1])
SW_W, SW_B = sw("strategy_WvNGjLMgoOyn"), sw("strategy_bYXaOJ4qXtW4")
NEW = ["strategy_WvNGjLMgoOyn", "strategy_bYXaOJ4qXtW4"]
a = S[(S.create_time >= SW_W) & S.cc.isin(CNOW)].copy()
a["new_online_hit"] = a.on_ids.map(lambda s: bool(s & set(NEW)))
a["period"] = np.where(a.create_time >= SW_B, "after bYXa online", "WvNG online, before bYXa")
x2 = a.groupby(["period", "new_online_hit", "ip_geo", "final_result"]).size().reset_index(name="requests")
out(x2, "x2_bypass_after_switch.csv")
b = S[(S.create_time >= SW_B) & (S.cc_group != "+1") & (S.final_result == "PASS")]
x2b = b.groupby(["cc", "phone_country", "ip_geo"]).size().reset_index(name="pass_requests")
x2b["in_current_country_rule"] = x2b.cc.isin(CNOW).astype(int)
x2b["usd_public_price"] = x2b.cc.map(price)
out(x2b.sort_values("pass_requests", ascending=False), "x2_nonplus1_pass_after_byxa.csv")

rows = []
NN = N[N.week.str.startswith(("prior", "last"))].copy()
NN["version_class"] = np.select([NN.version_num.isna(), NN.version_num < 1004030], ["no version", "< 1.4.30"], ">= 1.4.30")
top_ip = NN.ip_country.value_counts().head(10).index
NN["ip_country_top"] = np.where(NN.ip_country.isin(top_ip), NN.ip_country.fillna(""), "other")
for dim in ("v3_bucket", "cid", "app_state", "version_class", "ip_country_top", "ip_geo", "token_state"):
    for basis, g in (("requests", NN), ("PASS", NN[NN.final_result == "PASS"])):
        t = g.groupby(["week", dim]).size().reset_index(name="n")
        t["share_within_week"] = (t.n / t.groupby("week").n.transform("sum")).round(4)
        t.insert(0, "dimension", dim); t.insert(1, "basis", basis)
        rows.append(t.rename(columns={dim: "value"}))
out(pd.concat(rows, ignore_index=True), "x3_shifts.csv")
x4 = NN.groupby(["week", "ny_hour"]).agg(requests=("id", "size"), passes=("final_result", lambda s: (s == "PASS").sum())).reset_index()
out(x4, "x4_hour_of_day.csv")
print(x1.reset_index().sort_values("rank_value_last_week", ascending=False).head(15).to_string(index=False))
print(x2.to_string(index=False))
