#!/usr/bin/env python3
"""Point 8 / DR-003 method: is the counter-feature filter applied? Recompute every conditional counter feature from E1 and compare
with the value the engine logged, per NY day, two ways: "after filter" (count only requests meeting the feature's condition) and
"before filter" (count every request). Calibration: an unconditional counter with the same dimension, window and counting mode
(found in the config, not by name) must match the engine under the same recompute.
Recompute convention (DR-003, 2026-09-25 package): same dimension value, window (t - period, t] including the current request,
counting only requests on which the engine evaluated the feature; LKUS_push rows only (E1). Values compared where the engine code is
SUCCESS. Supported dimensions: countryCode, phoneNo, realIp, realIpc, uid, phoneCountry; count values: phoneNo, realIpCity,
countryCode, userNo, realIpCountry; conditions: NOT_EQUAL_STRING(realIpCountry,'x'), FIELD_BLANK / FIELD_NOT_EXISTS(recaptchaV3Token).
Output: results/p8_counter_recheck_daily.csv, results/p8_counter_recheck_summary.csv (shares only)."""
import json, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1lib import out, load_e1, R  # noqa: E402

EVAL_FROM = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2026-10-02 04:00:00")
cf = pd.read_csv(os.path.join(R, "config_counter_features.csv"), dtype=str)
DIM = {"countryCode": "cc", "phoneNo": "pno_h", "realIp": "ip_h", "realIpc": "ipc_h", "uid": "uid_h", "phoneCountry": "phone_country"}
CV = {"phoneNo": "pno_h", "realIpCity": "ip_city", "countryCode": "cc", "userNo": "userno_h", "realIpCountry": "ip_country"}
d = load_e1()
d = d.sort_values(["create_time", "shard", "id"]).reset_index(drop=True)
ts = d.create_time.values.astype("datetime64[s]").astype(np.int64)
cj = d.counters_json.map(lambda s: json.loads(s) if isinstance(s, str) and s.startswith("{") else {})


def cond_mask(conds):
    m = np.ones(len(d), bool)
    for c in conds:
        c = str(c).strip()
        if not c:
            continue
        if c.startswith("NOT_EQUAL_STRING(realIpCountry,"):
            m &= (d.ip_country.fillna("") != c.split("'")[1]).values
        elif c.startswith(("FIELD_BLANK(recaptchaV3Token", "FIELD_NOT_EXISTS(recaptchaV3Token")):
            m &= d.token_state.isin(["absent", "empty"]).values
        else:
            return None
    return m


def recompute(fid, dim, period, uv, cv, mask):
    fv = cj.map(lambda j: j.get(fid))
    code = fv.map(lambda v: v[0] if isinstance(v, list) else None)
    val = pd.to_numeric(fv.map(lambda v: v[1] if isinstance(v, list) else None), errors="coerce")
    evald = code.notna().values
    m = mask & evald
    key = d[DIM[dim]].fillna("").values
    vals = d[CV[cv]].fillna("").values if uv else None
    rec = np.full(len(d), np.nan)
    ev = (d.create_time >= EVAL_FROM).values
    for k, idx in pd.Series(np.arange(len(d))).groupby(key).groups.items():
        idx = np.asarray(idx); mi = m[idx]; tm = ts[idx][mi]
        vv = vals[idx][mi] if uv else None
        for i in idx[ev[idx] & evald[idx]]:
            lo, hi = np.searchsorted(tm, ts[i] - period, side="left"), np.searchsorted(tm, ts[i], side="right")   # same convention as toolkit/recheck_counter.py
            rec[i] = len(set(vv[lo:hi])) if uv else hi - lo
    return code, val, rec, ev


rows = []
targets = []
for r in cf.itertuples():
    conds = json.loads(r.conditions) if isinstance(r.conditions, str) and r.conditions.startswith("[") else []
    real = [c for c in conds if str(c).strip()]
    if real and r.dimension in DIM:
        targets.append((r, real))
for r, real in targets:
    uv = r.counter == "1"
    cal = cf[(cf.dimension == r.dimension) & (cf.period_s == r.period_s) & (cf.counter == r.counter) & (cf.count_value.fillna("") == (r.count_value if isinstance(r.count_value, str) else ""))
             & (cf.conditions.fillna("[]").map(lambda s: not [c for c in json.loads(s) if str(c).strip()] if s.startswith("[") else True))]
    variants = [(r.feature_id, "after filter (feature's own condition)", cond_mask(real)), (r.feature_id, "before filter (no condition)", np.ones(len(d), bool))]
    variants += [(c, "calibration: unconditional twin", np.ones(len(d), bool)) for c in cal.feature_id]
    for fid, label, mask in variants:
        if mask is None:
            rows.append({"feature_id": fid, "variant": label, "note": "condition not supported"}); continue
        code, val, rec, ev = recompute(fid, r.dimension, int(float(r.period_s)), uv, r.count_value if uv else None, mask)
        E = ev & (code == "SUCCESS").values
        df = pd.DataFrame({"ny_date": d.ny_date, "E": E, "eq": (val.values == rec) & E, "w1": (np.abs(val.values - rec) <= 1) & E,
                           "nonsuccess": ev & code.notna().values & (code != "SUCCESS").values})
        g = df.groupby("ny_date").agg(evaluated_success=("E", "sum"), engine_eq_recompute=("eq", "sum"), within1=("w1", "sum"),
                                      non_success=("nonsuccess", "sum")).reset_index()
        g = g[g.evaluated_success + g.non_success > 0]
        g["share_eq"] = (g.engine_eq_recompute / g.evaluated_success.replace(0, np.nan)).round(4)
        g.insert(0, "target_feature", r.feature_id); g.insert(1, "feature_id", fid); g.insert(2, "variant", label)
        rows.append(g)
daily = pd.concat([x for x in rows if isinstance(x, pd.DataFrame)], ignore_index=True)
out(daily, "p8_counter_recheck_daily.csv")
s = daily.groupby(["target_feature", "feature_id", "variant"]).agg(days=("ny_date", "nunique"), evaluated=("evaluated_success", "sum"),
                                                                     n_eq=("engine_eq_recompute", "sum"), within1=("within1", "sum"),
                                                                     non_success=("non_success", "sum")).reset_index()
s["share_eq"] = (s.n_eq / s.evaluated.replace(0, np.nan)).round(4); s["share_within1"] = (s.within1 / s.evaluated.replace(0, np.nan)).round(4)
s.insert(0, "eval_window", f"[{EVAL_FROM}, end of E1) UTC; warm-up from E1 start")
out(s, "p8_counter_recheck_summary.csv")
print(s.to_string(index=False))
