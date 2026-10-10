#!/usr/bin/env python3
"""DRs answered from the L1 long aggregate (results/l1_long.csv; counts only, LKUS_push, NY 2026-06-01..10-09).
  DR-010 : daily series, fixed 28-day baseline (first 28 days), median + k x scaled MAD (iterative), k = 5 and 3
  bridge  : NY 2026-09-27..10-09 daily SMS result x cc group, non-+1 PASS share, max rolling-24h SMS PASS (alert > 5000)
  DR-033 : NY week (Sunday start) x cc SMS PASS from 2026-08-01, partial weeks flagged; first PASS NY day per cc (since 06-01)
  DR-032 : country codes of the shared country rule (first version, 15 codes; and the 6 added) x realIpProvince class x result,
           baseline NY 06-01..08-31 (alt 08-01..08-31) vs attack NY 09-03..10-09; +1 control
  DR-036a: UTC day SMS totals / PASS vs the Doris numbers given in the run prompt (results/dr036a_doris_reference.csv)
  DR-036e: 20 NY days ending 2026-10-08: share of the 15 codes' SMS requests whose IP province is New York / New Jersey
Filters: scene LKUS_push and tenant LKUS (tenant_lkus = 1) — the same as the 09-27 DR-010 series. SMS = sms == 1."""
import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1lib import out, R  # noqa: E402

L = pd.read_csv(os.path.join(R, "l1_long.csv"), dtype={"cc": str, "shard": str})
L["cc"] = L.cc.fillna("")
tn = L[L.lvl == "h"].groupby("tenant_lkus").n.sum()
out(tn.reset_index(name="rows"), "l1_tenant_check.csv")
L = L[L.tenant_lkus == 1]
H, D = L[L.lvl == "h"].copy(), L[L.lvl == "d"].copy()
grp = lambda cc: np.select([cc == "1", cc == "86", cc == ""], ["+1", "+86", "unknown"], "other")
H["cc_group"], D["cc_group"] = grp(H.cc), grp(D.cc)
Hs, Ds = H[H.sms == 1], D[D.sms == 1]

# ---------------- DR-010 ----------------
def daily(g, gd):
    return pd.Series({
        "sms_requests": int(g.n.sum()),
        "plus1_requests": int(g.loc[g.cc_group == "+1", "n"].sum()),
        "plus1_pass": int(g.loc[(g.cc_group == "+1") & (g.final_result == "PASS"), "n"].sum()),
        "plus1_pass_distinct_phones": int(gd.loc[gd.cc_group == "+1", "n_phones_pass"].sum()),
        "plus1_reject": int(g.loc[(g.cc_group == "+1") & (g.final_result == "REJECT"), "n"].sum()),
        "non_plus1_plus86_requests": int(g.loc[g.cc_group == "other", "n"].sum()),
        "non_plus1_pass": int(g.loc[(g.cc_group != "+1") & (g.final_result == "PASS"), "n"].sum()),
        "plus86_requests": int(g.loc[g.cc_group == "+86", "n"].sum()),
        "sms_distinct_phones": int(gd.n_phones.sum())})
days = sorted(Hs.ny_date.unique())
day = pd.DataFrame([dict(ny_date=x, **daily(Hs[Hs.ny_date == x], Ds[Ds.ny_date == x])) for x in days])
xv = day.non_plus1_plus86_requests.astype(float).values
base = list(range(min(28, len(day))))
rule_rows = []
for k in (5.0, 3.0):
    idx = set(base)
    for _ in range(20):
        b = xv[sorted(idx)]
        med = np.median(b); mad = np.median(np.abs(b - med)) * 1.4826
        thr = med + k * mad
        new = {i for i in base if xv[i] <= thr}
        if new == idx:
            break
        idx = new
    day[f"attack_flag_k{k:g}"] = (xv > thr).astype(int)
    fl = day[day[f"attack_flag_k{k:g}"] == 1]
    rule_rows.append({"k": k, "baseline": f"first {len(base)} days ({day.ny_date.iloc[0]}..{day.ny_date.iloc[len(base) - 1]})",
                      "baseline_days_kept": len(idx), "baseline_median": round(med, 1), "baseline_mad_scaled": round(mad, 1),
                      "threshold": round(thr, 1), "first_flagged_day": fl.ny_date.min(), "last_flagged_day": fl.ny_date.max(),
                      "flagged_days": int(len(fl)), "flagged_days_since_09_03": int((fl.ny_date >= "2026-09-03").sum()),
                      "days_since_09_03": int((day.ny_date >= "2026-09-03").sum()),
                      "flagged_days_last_7": int(day[f"attack_flag_k{k:g}"].tail(7).sum())})
out(day, "dr010_daily_series.csv")
out(pd.DataFrame(rule_rows), "dr010_attack_rule.csv")
day["month"] = day.ny_date.str[:7]
day["period"] = np.where(day.attack_flag_k5 == 1, "attack_day_k5", "normal_day_k5")
per = day.groupby(["month", "period"]).agg(days=("ny_date", "count"), plus1_pass_mean=("plus1_pass", "mean"),
                                           plus1_pass_distinct_phones_mean=("plus1_pass_distinct_phones", "mean"),
                                           non_plus1_plus86_mean=("non_plus1_plus86_requests", "mean")).round(1).reset_index()
out(per, "dr010_period_summary.csv")
day["ny_week_sun"] = (pd.to_datetime(day.ny_date) - pd.to_timedelta((pd.to_datetime(day.ny_date).dt.dayofweek + 1) % 7, unit="D")).dt.strftime("%Y-%m-%d")
wk = day.groupby("ny_week_sun").agg(days=("ny_date", "count"), plus1_pass=("plus1_pass", "sum"), plus1_pass_per_day=("plus1_pass", "mean")).round(1).reset_index()
out(wk, "dr010_plus1_pass_weekly.csv")

# ---------------- bridge window ----------------
br = Hs[Hs.ny_date >= "2026-09-27"]
b1 = br.pivot_table(index="ny_date", columns=["cc_group", "final_result"], values="n", aggfunc="sum", fill_value=0)
b1.columns = [f"{g}_{r}" for g, r in b1.columns]
b1["sms_requests"] = br.groupby("ny_date").n.sum()
p_ = br[br.final_result == "PASS"].groupby("ny_date")
b1["pass_total"] = p_.n.sum()
b1["pass_non_plus1"] = br[(br.final_result == "PASS") & (br.cc_group != "+1")].groupby("ny_date").n.sum()
b1["non_plus1_share_of_pass"] = (b1.pass_non_plus1 / b1.pass_total).round(4)
hh = Hs[Hs.final_result == "PASS"].groupby("utc_hour").n.sum()
hh.index = pd.to_datetime(hh.index + ":00:00")
hh = hh.reindex(pd.date_range(hh.index.min(), hh.index.max(), freq="h"), fill_value=0)
roll = hh.rolling(24).sum()
ny_of = lambda t: t.tz_localize("UTC").tz_convert("America/New_York").strftime("%Y-%m-%d")
r24 = pd.DataFrame({"end_hour_utc": roll.index, "pass_24h": roll.values})
r24["ny_date_of_end"] = [ny_of(t) for t in r24.end_hour_utc]
b1["max_rolling_24h_sms_pass"] = r24.groupby("ny_date_of_end").pass_24h.max()
b1 = b1.fillna(0).reset_index()
out(b1, "bridge_daily_series.csv")
out(pd.DataFrame([{"window": "NY 2026-06-01..10-09 (hourly, SMS, tenant LKUS)", "max_rolling_24h_sms_pass": int(roll.max()),
                   "at_end_hour_utc": roll.idxmax(), "hours_above_5000": int((roll > 5000).sum()),
                   "max_since_09_27": int(roll[roll.index >= pd.Timestamp("2026-09-27 04:00:00")].max())}]), "bridge_alert_check.csv")

# ---------------- DR-033 ----------------
pz = Hs[(Hs.final_result == "PASS")].copy()
pz["ny_week_sun"] = (pd.to_datetime(pz.ny_date) - pd.to_timedelta((pd.to_datetime(pz.ny_date).dt.dayofweek + 1) % 7, unit="D")).dt.strftime("%Y-%m-%d")
w = pz[pz.ny_date >= "2026-08-01"].groupby(["ny_week_sun", "cc"]).agg(pass_sms=("n", "sum"), days_with_pass=("ny_date", "nunique")).reset_index()
wd = pz[pz.ny_date >= "2026-08-01"].groupby("ny_week_sun").ny_date.agg(["min", "max", "nunique"]).rename(columns={"min": "first_day_in_window", "max": "last_day_in_window", "nunique": "days_in_window"})
w = w.merge(wd, left_on="ny_week_sun", right_index=True)
w["partial_week"] = (w.days_in_window < 7).astype(int)
w["pass_per_day"] = (w.pass_sms / w.days_in_window).round(2)
out(w, "dr033_weekly_pass_by_cc.csv")
first = pz.groupby("cc").ny_date.min().rename("first_pass_ny_date").reset_index()
first["left_censored_at_06_01"] = (first.first_pass_ny_date == days[0]).astype(int)
last7 = pz[pz.ny_date >= "2026-10-03"].groupby("cc").n.sum().rename("pass_last_7d")
first = first.merge(last7, left_on="cc", right_index=True, how="left").fillna({"pass_last_7d": 0})
pr = pd.read_csv(os.path.join(R, "dr033_price_reference.csv"), dtype={"cc": str})
first = first.merge(pr[["cc", "usd_per_sms_public_max"]], on="cc", how="left")
first["rank_value_last_7d"] = (first.pass_last_7d * first.usd_per_sms_public_max).round(2)
out(first.sort_values("rank_value_last_7d", ascending=False), "dr033_first_pass_and_rank.csv")

# ---------------- DR-032 ----------------
cv = pd.read_csv(os.path.join(R, "dr031_code_versions.csv"), dtype=str)
C15 = set(cv.codes.iloc[0].split()); CNOW = set(cv.codes.iloc[-1].split())
H["code_set"] = np.select([H.cc.isin(C15), H.cc.isin(CNOW), H.cc == "1"], ["15 original", "6 added", "+1 control"], "")
z = H[(H.sms == 1) & (H.code_set != "")]
periods = {"baseline NY 06-01..08-31": ("2026-06-01", "2026-08-31"), "alt baseline NY 08-01..08-31": ("2026-08-01", "2026-08-31"),
           "attack NY 09-03..10-09": ("2026-09-03", "2026-10-09"), "last 7 NY days 10-03..10-09": ("2026-10-03", "2026-10-09")}
rows = []
for pn, (a, b) in periods.items():
    g = z[(z.ny_date >= a) & (z.ny_date <= b)]
    for (cs, pc, fr), n in g.groupby(["code_set", "prov_class", "final_result"]).n.sum().items():
        rows.append({"period": pn, "code_set": cs, "prov_class": pc, "final_result": fr, "requests": int(n)})
t = pd.DataFrame(rows)
t["share_of_code_set_period"] = (t.requests / t.groupby(["period", "code_set"]).requests.transform("sum")).round(4)
out(t, "dr032_province_split.csv")
bycc = z[(z.ny_date >= "2026-06-01") & (z.ny_date <= "2026-08-31")].groupby(["cc", "prov_class"]).n.sum().unstack(fill_value=0)
out(bycc.reset_index(), "dr032_baseline_by_cc.csv")
mo = z.assign(month=z.ny_date.str[:7]).groupby(["month", "prov_class"]).n.sum().unstack(fill_value=0).reset_index()
out(mo, "dr032_province_presence_by_month.csv")

# ---------------- DR-036 (a) and (e) ----------------
ref = pd.read_csv(os.path.join(R, "dr036a_doris_reference.csv"), dtype={"utc_date": str})
H["utc_date"] = H.utc_hour.str[:10]
u_sms = H[H.sms == 1].groupby("utc_date").agg(mysql_total=("n", "sum"), mysql_pass=("n", lambda s: s[H.loc[s.index, "final_result"] == "PASS"].sum()))
u_all = H.groupby("utc_date").agg(mysql_total_all_rows=("n", "sum"))
j = ref.merge(u_sms, left_on="utc_date", right_index=True, how="left").merge(u_all, left_on="utc_date", right_index=True, how="left")
j["diff_total"], j["diff_pass"] = j.mysql_total - j.doris_total, j.mysql_pass - j.doris_pass
nyd = Hs.groupby("ny_date").agg(mysql_total_ny_day=("n", "sum"))
j = j.merge(nyd, left_on="utc_date", right_index=True, how="left")
out(j, "dr036a_utc_daily_vs_doris.csv")
e = H[(H.sms == 1) & (H.ny_date >= "2026-09-19") & (H.ny_date <= "2026-10-08")]
rows = []
for basis, g in (("all results", e), ("PASS", e[e.final_result == "PASS"])):
    for cs in ("15 original", "15 + 6 added"):
        gg = g[g.cc.isin(C15)] if cs == "15 original" else g[g.cc.isin(CNOW)]
        tot = gg.n.sum(); ny = gg[gg.prov_class == "nynj"].n.sum()
        rows.append({"window": "NY 2026-09-19..10-08 (20 days)", "basis": basis, "code_set": cs, "requests": int(tot), "nynj": int(ny),
                     "nynj_share": round(ny / tot, 4) if tot else None, "province_missing": int(gg[gg.prov_class == "missing"].n.sum())})
out(pd.DataFrame(rows), "dr036e_nynj_share.csv")
print(pd.DataFrame(rule_rows).to_string(index=False))
print(b1[["ny_date", "sms_requests", "pass_total", "non_plus1_share_of_pass", "max_rolling_24h_sms_pass"]].to_string(index=False))
