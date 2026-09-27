#!/usr/bin/env python3
"""P5: cross-check every toolkit test output (results/toolkit_tests/) against this run's P3/P4 results computed another
way (E1 local extract or independent SQL). Strategy IDs come from _local_only/p5_picks.txt (picked from the data by
sql/local/p5_pick.py). Writes results/toolkit_tests/_test_summary.csv (and merged tk outputs)."""
import json, os, subprocess, sys
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, T, RAW = os.path.join(PKG, "results"), os.path.join(PKG, "results", "toolkit_tests"), os.path.join(PKG, "_local_only", "raw")
K = os.path.join(PKG, "toolkit")
picks = dict(kv.split("=") for kv in open(os.path.join(PKG, "_local_only", "p5_picks.txt")).read().split())
PRE, ON, TK6, PRE_PC = picks["PRE"], picks["ON"], picks["TK06"], int(picks.get("PRE_PASS_CLASS", 0))
rows = []


def add(test, a, b, note=""):
    rows.append({"test": test, "toolkit": a, "reference": b, "equal": a == b, "note": note})


def merge(tpl, name, *extra, out_name=None):
    out = os.path.join(T, out_name or f"{tpl}_merged.csv")
    subprocess.run([sys.executable, os.path.join(K, "tk_merge.py"), tpl, os.path.join(T, f"{name}.csv"), "--out", out, *extra],
                   check=True, stdout=subprocess.DEVNULL)
    return pd.read_csv(out)


ny = lambda s: (pd.to_datetime(s) - pd.Timedelta(hours=4)).dt.strftime("%Y-%m-%d")
e = pd.concat([pd.read_csv(os.path.join(RAW, f), dtype=str) for f in ("e1_a.csv.gz", "e1_b.csv.gz")]).drop_duplicates("id")
e["ny"] = ny(e.create_time)
sms = e.email_present == "0"
# tk01 ---------------------------------------------------------------------------------------------------------
m = merge("tk01", "tk01_volume_users", "--home-cc", "1", "--watch-cc", "86"); m["ny"] = ny(m.window_start_utc)
u = pd.read_csv(os.path.join(R, "p3_distinct_users.csv")).set_index("ny_date")
ds = pd.read_csv(os.path.join(R, "p4_daily_series.csv")).groupby("ny_date").n.sum()
for r in m.itertuples():
    add(f"tk01 {r.ny} requests (all push rows) vs p4_daily_series", int(r.requests), int(ds.loc[r.ny]))
    if r.ny in u.index:
        add(f"tk01 {r.ny} SMS distinct phones vs E1", int(r.phones_sms), int(u.loc[r.ny, "distinct_phones"]))
        add(f"tk01 {r.ny} SMS PASS +1 distinct phones vs E1", int(r.phones_sms_pass_home), int(u.loc[r.ny, "pass_plus1_distinct_phones"]))
# tk02 / tk03 --------------------------------------------------------------------------------------------------
t2 = merge("tk02", "tk02_strategy_hits"); t2["ny"] = ny(t2.window_start_utc)
h = pd.read_csv(os.path.join(R, "p2_hits_7d.csv"))
add(f"tk02 {PRE} pre-online PV 7d vs p2_hits_7d", int(t2.pv.sum()), int(h[(h.list == "preonline") & (h.strategy_id == PRE)].pv.sum()))
hit = e.hits_preonline.fillna("[]").map(lambda s: any(x.split("|")[0] == PRE for x in json.loads(s)))
x = e[hit].groupby("ny").phone_h.nunique()
for r in t2.itertuples():
    add(f"tk02 {r.ny} {PRE} distinct phones vs E1", int(r.distinct_phones), int(x.get(r.ny, 0)))
t3 = merge("tk03", "tk03_extra_recall")
W7 = sorted(t2.ny.unique()); LAST = W7[-1]
xr = e[hit & ((e.final_result != "PASS") if PRE_PC else (e.final_result == "PASS")) & e.ny.isin(W7)]
add(f"tk03 {PRE} extra recall PV 7d vs E1 (all push rows; pass_class={PRE_PC})", int(t3.extra_recall_pv.sum()), int(len(xr)))
# tk02 / tk03 with sms_only=1 (SMS rule of P3) -------------------------------------------------------------------
if os.path.exists(os.path.join(T, "tk02_strategy_hits_sms.csv")):
    t2s = merge("tk02", "tk02_strategy_hits_sms", out_name="tk02_sms_merged.csv"); t2s["ny"] = ny(t2s.window_start_utc)
    add(f"tk02 {PRE} pre-online PV 7d, sms_only=1, vs E1 SMS", int(t2s.pv.sum()), int((hit & sms & e.ny.isin(W7)).sum()))
    xs = e[hit & sms].groupby("ny").phone_h.nunique()
    for r in t2s.itertuples():
        add(f"tk02 {r.ny} {PRE} distinct phones, sms_only=1, vs E1 SMS", int(r.distinct_phones), int(xs.get(r.ny, 0)))
if os.path.exists(os.path.join(T, "tk03_extra_recall_sms.csv")):
    t3s = merge("tk03", "tk03_extra_recall_sms", out_name="tk03_sms_merged.csv")
    add(f"tk03 {PRE} extra recall PV 7d, sms_only=1, vs E1 SMS (pass_class={PRE_PC})", int(t3s.extra_recall_pv.sum()), int((xr.email_present == "0").sum()))
# tk04 ---------------------------------------------------------------------------------------------------------
t4 = pd.read_csv(os.path.join(T, "tk04_pass_leakage.csv"), dtype={"email_key": str})
lk = pd.read_csv(os.path.join(R, "p3_pass_leakage.csv"))
add("tk04 non-+1 SMS PASS rows 7d vs E1", int(t4[t4.email_key.astype(int) == 0].rows_pass.sum()), int(lk[lk.dimension == "cid"].rows.sum()))
tv = merge("tk04", "tk04_pass_leakage", "--sms-only")
for dim, val in (("ip_country", "美国"), ("token_state", "absent"), ("cid", "105")):
    a_ = tv[(tv.dimension == dim) & (tv.value.astype(str) == val)].rows.sum()
    b_ = lk[(lk.dimension == dim) & (lk.value.astype(str) == val)].rows.sum()
    add(f"tk04 non-+1 SMS PASS {dim}={val} vs E1", int(a_), int(b_))
# tk05 ---------------------------------------------------------------------------------------------------------
t5 = merge("tk05", "tk05_v3_distribution", "--cuts", "0.3,0.8", "--home-cc", "1", "--watch-cc", "86", "--sms-only")
v = pd.read_csv(os.path.join(R, "p3_v3_by_ccgroup_cid.csv"), dtype={"cid": str})
t5["cid"] = t5.cid.astype(str)
gm = {"home": "+1", "watch": "+86", "other": "other", "unknown": "unknown"}
t5["cc_group"] = t5.group.map(gm)
j = t5.merge(v, left_on=["cc_group", "cid", "bucket"], right_on=["cc_group", "cid", "v3_bucket"], how="outer").fillna(0)
add("tk05 score-bucket cells (cc group x cid x bucket) equal to E1", int((j.n == j.rows).sum()), int(len(j)), f"{len(j)} cells")
# tk06 ---------------------------------------------------------------------------------------------------------
t6 = pd.read_csv(os.path.join(T, f"tk06_recheck_{TK6}.csv")).iloc[0]
hits25 = h[(h.list == "online") & (h.strategy_id == TK6) & (h.ny_date == LAST)].pv.sum()
add(f"tk06 {TK6} hits on NY {LAST} vs p2_hits_7d", int(t6.strategy_hits), int(hits25),
    f"re-check output (not a test): violations {int(t6.violations_hit_but_rule_false_on_recompute)}/{int(t6.strategy_hits)}; engine==recompute {t6.engine_eq_recompute_share}, within1 {t6.engine_within1_share}")
if "strategy_hits_sms" in t6:
    on6 = e.hits_online.fillna("[]").map(lambda s_: any(x.split("|")[0] == TK6 for x in json.loads(s_)))
    add(f"tk06 {TK6} SMS hits on NY {LAST} (email_nonempty=0) vs E1 SMS", int(t6.strategy_hits_sms), int((on6 & sms & (e.ny == LAST)).sum()),
        f"re-check output (not a test): SMS violations {int(t6.violations_sms)}/{int(t6.strategy_hits_sms)}")
# tk07 ---------------------------------------------------------------------------------------------------------
p = pd.read_csv(os.path.join(T, f"tk07_patrol_{LAST.replace('-', '')}.csv"), dtype=str); p["n"] = p.n.astype(float).astype(int)
dr = pd.read_csv(os.path.join(R, "p3_daily_result.csv")).set_index("ny_date").loc[LAST]
res = p[(p.kind == "result") & (p.k3 == "0")].groupby("k1").n.sum()
for k in ("PASS", "REJECT", "REVIEW"):
    add(f"tk07 {LAST} SMS {k} vs E1", int(res.get(k, 0)), int(dr[f"sms_{k}"]))
onh = p[p.kind == "online_hit"].groupby("k1").n.sum()
hh = h[(h.list == "online") & (h.ny_date == LAST)].groupby("strategy_id").pv.sum()
jj = pd.concat([onh.rename("a"), hh.rename("b")], axis=1).fillna(0)
add(f"tk07 {LAST} online hit PV per strategy equal to p2_hits_7d", int((jj.a == jj.b).sum()), int(len(jj)), f"{len(jj)} strategies")
# tk08 ---------------------------------------------------------------------------------------------------------
t8 = pd.read_csv(os.path.join(T, "tk08_strategy_cid_geo.csv"), dtype={"cid": str})
t8["ny"] = ny(t8.window_start_utc)
g8 = t8[t8.level == "group"].groupby(["ny", "cid", "geo_mismatch"]).pv.sum()
d23 = pd.read_csv(os.path.join(R, "dr027_strategy_day_cid_geo.csv"), dtype={"cid": str})
d23 = d23[(d23.list == "online") & (d23.strategy_id == ON) & d23.ny_date.isin(W7)].set_index(["ny_date", "cid", "geo_mismatch"]).hit_pv
jj = pd.concat([g8.rename("a"), d23.rename("b")], axis=1).fillna(0)
add(f"tk08 {ON} PV cells (day x cid x geo) equal to E1", int((jj.a == jj.b).sum()), int(len(jj)), f"{len(jj)} cells")
c8 = t8[t8.level == "cidgeo"].groupby(["ny", "cid", "geo_mismatch"]).distinct_phones.sum()
u23 = pd.read_csv(os.path.join(R, "dr027_strategy_day_cid_geo.csv"), dtype={"cid": str})
u23 = u23[(u23.list == "online") & (u23.strategy_id == ON) & u23.ny_date.isin(W7)].set_index(["ny_date", "cid", "geo_mismatch"]).distinct_phones
jj = pd.concat([c8.rename("a"), u23.rename("b")], axis=1).fillna(0)
add(f"tk08 {ON} distinct-phone cells equal to E1", int((jj.a == jj.b).sum()), int(len(jj)), f"{len(jj)} cells")
# tk09 ---------------------------------------------------------------------------------------------------------
t9 = pd.read_csv(os.path.join(T, "tk09_engine_vs_final.csv"), dtype={"cid": str})
t9 = t9[t9.sms == 1].groupby(["engine_result", "final_result"]).n.sum()
e25 = e[(e.ny == LAST) & sms].assign(engine_result=lambda d: d.engine_result.fillna("<none>")).groupby(["engine_result", "final_result"]).id.count()
jj = pd.concat([t9.rename("a"), e25.rename("b")], axis=1).fillna(0)
add(f"tk09 {LAST} SMS engine x final cells equal to E1", int((jj.a == jj.b).sum()), int(len(jj)), f"{len(jj)} cells")
# tk10 ---------------------------------------------------------------------------------------------------------
cx27 = pd.read_csv(os.path.join(R, "dr027_crosscheck.csv"))
r10 = cx27[cx27.check.str.startswith("tk10")].iloc[0]
add("tk10 strategy_43NaEzJmiQFk unique-REJECT cells equal to E1 (DR-027 window)", int(r10.cells - r10.mismatching_cells), int(r10.cells), f"{int(r10.cells)} cells")
out = pd.DataFrame(rows); out.to_csv(os.path.join(T, "_test_summary.csv"), index=False)
pd.set_option("display.width", 200)
print(out.to_string(index=False)); print("all equal:", bool(out.equal.all()))
