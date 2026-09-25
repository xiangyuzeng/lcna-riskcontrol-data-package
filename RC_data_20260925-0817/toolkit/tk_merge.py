#!/usr/bin/env python3
"""Merge step for the toolkit templates (shard_runner.py writes one CSV row per shard x window x group).
  python3 tk_merge.py tk01 results/<name>.csv [--home-cc 1] [--watch-cc 86] [--sms-only]
  python3 tk_merge.py tk02|tk03 results/<name>.csv [--home-cc 1]
  python3 tk_merge.py tk04 results/<name>.csv [--sms-only]
  python3 tk_merge.py tk05 results/<name>.csv [--cuts 0.3,0.8] [--home-cc 1] [--watch-cc 86] [--sms-only]
Country codes are given without '+'. --sms-only drops rows whose request carried an email key (DR-002 rule).
Distinct-phone columns are summed across shards (valid: one phone lives in one shard, DR-014) but never across windows.
Prints a table and, with --out, writes it as CSV."""
import argparse
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("template"); ap.add_argument("csv")
ap.add_argument("--home-cc", default="1"); ap.add_argument("--watch-cc", default="86")
ap.add_argument("--cuts", default="0.3,0.8"); ap.add_argument("--sms-only", action="store_true"); ap.add_argument("--out")
a = ap.parse_args()
home, watch = set(a.home_cc.split(",")), set(a.watch_cc.split(","))
d = pd.read_csv(a.csv, dtype={"cc": str, "cid": str})
if a.sms_only and "email_key" in d:
    d = d[d.email_key.astype(int) == 0]
grp = lambda cc: cc.fillna("").map(lambda c: "home" if c in home else "watch" if c in watch else "unknown" if c == "" else "other")
if a.template == "tk01":
    g, w = d[d.level == "group"].copy(), d[d.level == "window"]
    g["group"] = grp(g.cc)
    out = g.pivot_table(index="window_start_utc", columns=["group", "final_result"], values="requests", aggfunc="sum", fill_value=0)
    out.columns = [f"{x}_{r}" for x, r in out.columns]
    out["requests"] = g.groupby("window_start_utc").requests.sum()
    for c in ("phones_all", "phones_sms", "phones_sms_pass", "phones_sms_pass_home"):
        out[c] = w.groupby("window_start_utc")[c].sum()          # exact: window-level distinct, summed across shards only
    out = out.fillna(0).astype(int).reset_index()
elif a.template == "tk02":
    g, w = d[d.level == "group"].copy(), d[d.level == "window"]
    g["group"] = grp(g.cc)
    out = g.groupby("window_start_utc").agg(pv=("pv", "sum")).join(
        g[g.group == "home"].groupby("window_start_utc").pv.sum().rename("pv_home")).join(
        g[g.final_result == "PASS"].groupby("window_start_utc").pv.sum().rename("pv_final_pass")).join(
        w.groupby("window_start_utc").uv_phones.sum().rename("distinct_phones")).fillna(0).astype(int).reset_index()
elif a.template == "tk03":
    d["group"] = grp(d.cc)                                          # grouped by cc only: a phone has one cc -> exact
    out = d.groupby("window_start_utc").agg(extra_recall_pv=("extra_recall_pv", "sum"), extra_recall_phones=("extra_recall_phones", "sum")).join(
        d[d.group == "home"].groupby("window_start_utc").extra_recall_pv.sum().rename("pv_home")).fillna(0).astype(int).reset_index()
elif a.template == "tk04":
    n = d.rows_pass.sum()
    parts = []
    for dim in ("cc", "ip_country", "phone_ne_ip_country", "cid", "token_state", "app_key", "email_key"):
        g = d.groupby(dim).rows_pass.sum().reset_index(name="rows").rename(columns={dim: "value"})
        g.insert(0, "dimension", dim); g["share"] = (g.rows / n).round(4)
        parts.append(g.sort_values("rows", ascending=False))
    out = pd.concat(parts, ignore_index=True)
elif a.template == "tk05":
    lo, hi = (float(x) for x in a.cuts.split(","))
    sc = pd.to_numeric(d.score_1dp, errors="coerce")
    d["bucket"] = pd.Series(["missing"] * len(d), index=d.index).where(sc.isna(), (sc < lo).map({True: f"<{lo}", False: None}))
    d.loc[sc.notna() & (sc >= lo) & (sc < hi), "bucket"] = f"{lo}-{hi}"
    d.loc[sc.notna() & (sc >= hi), "bucket"] = f">={hi}"
    d["group"] = grp(d.cc)
    out = d.groupby(["group", "cid", "bucket"]).n.sum().reset_index()
    out["share_within_group_cid"] = (out.n / out.groupby(["group", "cid"]).n.transform("sum")).round(4)
else:
    raise SystemExit("unknown template")
pd.set_option("display.width", 200)
print(out.to_string(index=False))
if a.out:
    out.to_csv(a.out, index=False)
