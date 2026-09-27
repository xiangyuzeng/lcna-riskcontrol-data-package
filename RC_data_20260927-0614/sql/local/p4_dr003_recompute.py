#!/usr/bin/env python3
"""DR-003: do counter features with filter conditions count only the matching events?

Method (local, from the E1 extract; engine values come from featureDetail.comments.apiResp of each counter feature):
 1. Calibrate on unconditional siblings with the same dimension / window / counting mode:
      feature_UOJYBEifd5Jn  区号近60分钟的访问次数          PV  countryCode 3600 s
      feature_dtoJoDcUgCcr  同区号近60分钟对应手机号个数    UV(phoneNo) countryCode 3600 s
    For every request, recompute the count over LKUS_push requests of the same country code in the preceding
    window and compare with the engine value. Several window conventions are tried; the best one is kept.
 2. With the calibrated convention, recompute each conditional feature twice - over all requests (filter ignored)
    and over only the requests meeting its condition (filter applied) - and see which one equals the engine value.
      feature_n91JeGM6gD6i  PV of requests with realIpCountry != '美国'
      feature_dqBHKec09Wwa  PV of requests whose recaptchaV3Token is absent or ''  (condition set until 2026-09-24 07:22 UTC)
      feature_e1Kmz7JqzsWc  UV(phone) of requests whose recaptchaV3Token is blank (conditions list non-empty from 2026-09-24 07:24 UTC)
Pairs and conditions are taken from results/config_counter_features.csv and results/p2_oplog_changes.csv.
Output: results/dr003_calibration.csv, results/dr003_conditional_vs_recompute.csv, results/dr003_daily.csv
"""
import json, os
import numpy as np
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, RAW = os.path.join(PKG, "results"), os.path.join(PKG, "_local_only", "raw")
FEATS = ["feature_UOJYBEifd5Jn", "feature_dtoJoDcUgCcr", "feature_n91JeGM6gD6i", "feature_dqBHKec09Wwa", "feature_e1Kmz7JqzsWc"]

d = pd.concat([pd.read_csv(os.path.join(RAW, f), dtype=str) for f in ("e1_a.csv.gz", "e1_b.csv.gz")], ignore_index=True).drop_duplicates("id")
d["t"] = pd.to_datetime(d.create_time)
d["cc"] = d.cc_raw.fillna("").str.lstrip("+")
d = d.sort_values(["t", "id"]).reset_index(drop=True)
cj = d.counters_json.map(lambda s: json.loads(s) if isinstance(s, str) else {})
for f in FEATS:
    d[f + "_code"] = cj.map(lambda j, f=f: (j.get(f) or [None, None])[0])
    d[f + "_val"] = pd.to_numeric(cj.map(lambda j, f=f: (j.get(f) or [None, None])[1]), errors="coerce")
d["cond_nonus"] = d.ip_country.fillna("") != "美国"
d["cond_token_blank"] = d.token_state.isin(["absent", "empty"])
ny = d.t.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
d["ny_date"] = ny
EVAL = (d.ny_date >= "2026-09-18")          # evaluation rows; 2026-09-17 NY is warm-up only
ts = d.t.values.astype("datetime64[s]").astype(np.int64)


def window_counts(mask, uv=False, width=3600, left_closed=False, include_self=True, shift=0):
    """For every row, count rows (same cc, satisfying mask) with time in the window ending at the row's time."""
    out = np.full(len(d), np.nan)
    for cc, idx in d.groupby("cc").indices.items():
        idx = np.sort(idx)
        t = ts[idx] + 0
        m = mask[idx]
        tm, im = t[m], idx[m]
        ph = d.phone_h.values[im]
        for k, i in enumerate(idx):
            if not EVAL[i]:
                continue
            hi = ts[i] + shift
            lo = hi - width
            a = np.searchsorted(tm, lo, side="left" if left_closed else "right")
            b = np.searchsorted(tm, hi, side="right" if include_self else "left")
            if uv:
                out[i] = len(set(ph[a:b]))
            else:
                out[i] = b - a
    return out


ALL = np.ones(len(d), bool)
EVALD = {f: d[f + "_code"].notna().values for f in FEATS}   # requests on which the engine evaluated the feature
cal = []
best = {}
for fid, uv in (("feature_UOJYBEifd5Jn", False), ("feature_dtoJoDcUgCcr", True)):
    ok = EVAL & (d[fid + "_code"] == "SUCCESS") & d[fid + "_val"].notna()
    for base_name, base in (("all push requests", ALL), ("requests evaluating the feature", EVALD[fid])):
      for left_closed in (False, True):
        for include_self in (True, False):
            rc = window_counts(base, uv=uv, left_closed=left_closed, include_self=include_self)
            diff = rc[ok] - d.loc[ok, fid + "_val"].values
            cal.append({"feature_id": fid, "counted_population": base_name, "left_closed": left_closed, "include_current": include_self, "rows": int(ok.sum()),
                        "exact_match": round(float((diff == 0).mean()), 4), "within_1": round(float((np.abs(diff) <= 1).mean()), 4),
                        "within_2": round(float((np.abs(diff) <= 2).mean()), 4), "median_diff": float(np.median(diff)),
                        "mean_abs_diff": round(float(np.abs(diff).mean()), 3)})
cal = pd.DataFrame(cal).sort_values(["feature_id", "exact_match"], ascending=[True, False])
cal.to_csv(os.path.join(R, "dr003_calibration.csv"), index=False)
conv = cal.groupby("feature_id").head(1).set_index("feature_id")
print(cal.to_string(index=False))

res, daily = [], []
specs = [("feature_n91JeGM6gD6i", False, "cond_nonus", "feature_UOJYBEifd5Jn", None),
         ("feature_dqBHKec09Wwa", False, "cond_token_blank", "feature_UOJYBEifd5Jn", "2026-09-24 07:22:42"),
         ("feature_e1Kmz7JqzsWc", True, "cond_token_blank", "feature_dtoJoDcUgCcr", None)]
for fid, uv, cond, sib, until in specs:
    c = conv.loc[sib]
    lc, inc = bool(c.left_closed), bool(c.include_current)
    pop = EVALD[fid] if c.counted_population == "requests evaluating the feature" else ALL
    rec_all = window_counts(pop, uv=uv, left_closed=lc, include_self=inc)
    rec_flt = window_counts(pop & d[cond].values, uv=uv, left_closed=lc, include_self=inc)
    base = EVAL & d[fid + "_val"].notna()
    if until:
        base &= d.t < pd.Timestamp(until)
    for code in ("SUCCESS", "COUNTER_FEATURE_CONDITION_MISS"):
        ok = base & (d[fid + "_code"] == code)
        if ok.sum() == 0:
            continue
        v = d.loc[ok, fid + "_val"].values
        res.append({"feature_id": fid, "code": code, "period": f"< {until} UTC" if until else "whole window", "rows": int(ok.sum()),
                    "engine_eq_recompute_unfiltered": round(float((v == rec_all[ok]).mean()), 4),
                    "engine_eq_recompute_filtered": round(float((v == rec_flt[ok]).mean()), 4),
                    "engine_within1_unfiltered": round(float((np.abs(v - rec_all[ok]) <= 1).mean()), 4),
                    "engine_within1_filtered": round(float((np.abs(v - rec_flt[ok]) <= 1).mean()), 4),
                    "rows_where_filter_changes_count": int((rec_all[ok] != rec_flt[ok]).sum()),
                    "median_engine": float(np.median(v)), "median_unfiltered": float(np.median(rec_all[ok])),
                    "median_filtered": float(np.median(rec_flt[ok])), "calibration_convention": f"population={c.counted_population}; left_closed={lc}, include_current={inc}"})
        g = pd.DataFrame({"ny_date": d.loc[ok, "ny_date"].values, "eq_unf": v == rec_all[ok], "eq_flt": v == rec_flt[ok],
                          "differs": rec_all[ok] != rec_flt[ok]})
        dd = g.groupby("ny_date").agg(rows=("eq_unf", "size"), share_eq_unfiltered=("eq_unf", "mean"),
                                      share_eq_filtered=("eq_flt", "mean"), rows_filter_matters=("differs", "sum")).reset_index()
        dd.insert(0, "code", code); dd.insert(0, "feature_id", fid)
        daily.append(dd)
    d[fid + "_rec_all"], d[fid + "_rec_flt"] = rec_all, rec_flt
pd.DataFrame(res).to_csv(os.path.join(R, "dr003_conditional_vs_recompute.csv"), index=False)
pd.concat(daily).round(4).to_csv(os.path.join(R, "dr003_daily.csv"), index=False)
keep = ["id"] + [c for c in d.columns if c.endswith(("_rec_all", "_rec_flt", "_val", "_code")) and c.split("_rec")[0].split("_val")[0].split("_code")[0] in FEATS]
d.loc[EVAL, keep].to_csv(os.path.join(RAW, "dr003_recompute_rows.csv.gz"), index=False)   # local only (row-level)
print(pd.DataFrame(res).to_string(index=False))
