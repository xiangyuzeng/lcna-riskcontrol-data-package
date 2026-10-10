#!/usr/bin/env python3
"""DR-035: fill rates from the upush daily statistics table (results/dr035_upush_daily.csv; aggregate only).
1. Fit: which grouping reproduces the "其他地区" sheet of the run prompt (results/dr035_reference_other_region_sheet.csv,
   07-01..09-21): tenant (LKUS / all) x project (each / all) x provider (each / all) x code set counted as 其他地区
   (not +1 / not +1 and not +86) x date shift (statistic_date = sheet date + s, s in -1, 0, +1). Score = days matching exactly
   (sent and filled), then total absolute difference.
2. With the best definition: per-code daily sent / filled 08-01..last day; fill rate = SUM(filled) / SUM(sent) (ratio of sums).
3. Completeness: stats sent / risk-control SMS PASS per day for +1 / +86 / other, risk side from results/l1_long.csv, with the
   stats date read as a UTC day and as a NY day (the table's time zone is unconfirmed, DR-007); flags the gap days.
4. The country codes of the shared country rule (15 first version, 6 added): pre-attack (<= 09-02) vs attack (>= 09-03)."""
import itertools, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1lib import out, R  # noqa: E402

u = pd.read_csv(os.path.join(R, "dr035_upush_daily.csv"), dtype={"cc": str})
u["cc"] = u.cc.fillna("")
u["statistic_date"] = pd.to_datetime(u.statistic_date)
ref = pd.read_csv(os.path.join(R, "dr035_reference_other_region_sheet.csv"))
ref["sheet_date"] = pd.to_datetime(ref.sheet_date)
out(u.groupby(["project", "provider", "tenant"]).agg(rows=("n_stat_rows", "sum"), sent=("sent_num", "sum"), filled=("filled_num", "sum"),
                                                    first=("statistic_date", "min"), last=("statistic_date", "max")).reset_index(), "dr035_dimensions.csv")
fits = []
opts = lambda col: [None] + sorted(u[col].dropna().unique())
for ten, proj, prov, cs, sh in itertools.product([None, "LKUS"], opts("project"), opts("provider"), ["not +1", "not +1 and not +86"], [-1, 0, 1]):
    g = u
    if ten: g = g[g.tenant == ten]
    if proj: g = g[g.project == proj]
    if prov: g = g[g.provider == prov]
    g = g[g.cc != "1"] if cs == "not +1" else g[~g.cc.isin(["1", "86"])]
    s = g.groupby("statistic_date")[["sent_num", "filled_num"]].sum()
    r = ref.set_index(ref.sheet_date + pd.Timedelta(days=sh))[["sent", "filled"]]
    j = r.join(s, how="left").fillna(0)
    fits.append({"tenant": ten or "(all)", "project": proj or "(all)", "provider": prov or "(all)", "code_set": cs, "date_shift_days": sh,
                 "days": len(j), "days_exact": int(((j.sent == j.sent_num) & (j.filled == j.filled_num)).sum()),
                 "days_sent_exact": int((j.sent == j.sent_num).sum()), "abs_diff_sent": int((j.sent - j.sent_num).abs().sum()),
                 "abs_diff_filled": int((j.filled - j.filled_num).abs().sum()), "sheet_sent": int(j.sent.sum()), "table_sent": int(j.sent_num.sum())})
f = pd.DataFrame(fits).sort_values(["days_exact", "days_sent_exact", "abs_diff_sent", "abs_diff_filled"], ascending=[False, False, True, True])
out(f.head(40), "dr035_fit_candidates.csv")
best = f.iloc[0]
B = u.copy()
if best.tenant != "(all)": B = B[B.tenant == best.tenant]
if best.project != "(all)": B = B[B.project == best.project]
if best.provider != "(all)": B = B[B.provider == best.provider]
bd = B.copy()
bd["day"] = bd.statistic_date - pd.Timedelta(days=int(best.date_shift_days))      # sheet / statistic day after the fitted shift
pc = bd[bd.day >= "2026-08-01"].groupby(["day", "cc"])[["sent_num", "filled_num"]].sum().reset_index()
pc["fill_rate"] = (pc.filled_num / pc.sent_num.replace(0, np.nan)).round(4)
out(pc.assign(day=pc.day.dt.strftime("%Y-%m-%d")), "dr035_daily_by_cc.csv")

cv = pd.read_csv(os.path.join(R, "dr031_code_versions.csv"), dtype=str)
C15, CNOW = set(cv.codes.iloc[0].split()), set(cv.codes.iloc[-1].split())
bd["set"] = np.select([bd.cc == "1", bd.cc == "86", bd.cc.isin(C15), bd.cc.isin(CNOW)], ["+1", "+86", "15 original", "6 added"], "other codes")
per = {"pre-attack 06-01..09-02": ("2026-06-01", "2026-09-02"), "attack 09-03..09-20 (before the stats gap)": ("2026-09-03", "2026-09-20"),
       "09-21..09-28 (receipt gap)": ("2026-09-21", "2026-09-28"), "09-29..last day": ("2026-09-29", "2026-12-31"),
       "10-08 (WvNG online, MZQk pre-online)": ("2026-10-08", "2026-10-08")}
rows = []
for pn, (a, b) in per.items():
    g = bd[(bd.day >= a) & (bd.day <= b)]
    for s_, gg in g.groupby("set"):
        rows.append({"period": pn, "code_set": s_, "days": gg.day.nunique(), "sent": int(gg.sent_num.sum()), "filled": int(gg.filled_num.sum()),
                     "fill_rate": round(gg.filled_num.sum() / gg.sent_num.sum(), 4) if gg.sent_num.sum() else None})
    for c in sorted(CNOW):
        gg = g[g.cc == c]
        rows.append({"period": pn, "code_set": "+" + c, "days": gg.day.nunique(), "sent": int(gg.sent_num.sum()), "filled": int(gg.filled_num.sum()),
                     "fill_rate": round(gg.filled_num.sum() / gg.sent_num.sum(), 4) if gg.sent_num.sum() else None})
out(pd.DataFrame(rows), "dr035_fill_rate_periods.csv")

# completeness vs the risk-control SMS PASS (L1), stats date as UTC day and as NY day
L = pd.read_csv(os.path.join(R, "l1_long.csv"), dtype={"cc": str})
L = L[(L.lvl == "h") & (L.sms == 1) & (L.tenant_lkus == 1) & (L.final_result == "PASS")].copy()
L["cc"] = L.cc.fillna("")
L["g"] = np.select([L.cc == "1", L.cc == "86"], ["+1", "+86"], "other")
L["utc_day"] = L.utc_hour.str[:10]
risk_u = L.groupby(["utc_day", "g"]).n.sum().rename("risk_pass")
risk_n = L.groupby(["ny_date", "g"]).n.sum().rename("risk_pass")
st = B.copy()
st["g"] = np.select([st.cc == "1", st.cc == "86"], ["+1", "+86"], "other")
st["d"] = st.statistic_date.dt.strftime("%Y-%m-%d")
sg = st.groupby(["d", "g"])[["sent_num", "filled_num"]].sum()
rows = []
for basis, rk in (("stats date = UTC day", risk_u), ("stats date = NY day", risk_n)):
    j = sg.join(rk.rename_axis(["d", "g"]), how="inner")
    j["ratio_stats_sent_to_risk_pass"] = (j.sent_num / j.risk_pass).round(3)
    j = j.reset_index(); j.insert(0, "basis", basis)
    rows.append(j)
cm = pd.concat(rows)
cm = cm[cm.d >= "2026-08-01"]
out(cm, "dr035_completeness.csv")
sd = cm[cm.g == "+1"].groupby("basis").ratio_stats_sent_to_risk_pass.agg(lambda s: round(float(s[(s.index >= 0)].std()), 3))
print(best.to_string())
print(pd.DataFrame(rows[0]).query("g == '+1' and d >= '2026-09-15'")[["d", "sent_num", "risk_pass", "ratio_stats_sent_to_risk_pass"]].to_string(index=False))
