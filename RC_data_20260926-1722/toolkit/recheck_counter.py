#!/usr/bin/env python3
"""tk06 step 2: recompute a counter feature from the tk06 extract and check one rule on it. Prints counts only.

  python3 recheck_counter.py --extract ../_local_only/raw/<name>.csv.gz --feature-id feature_X \
      --op '>' --threshold 30 --eval-from '2026-09-24 04:00:00' [--config ../results/config_counter_features.csv]

Counter definition (period, counter PV/UV, dimension, countValue, conditions) is read from the config export.
Recompute convention (calibrated in DR-003): same dimension value, window (t - period, t] including the current
request, counting only requests on which the engine evaluated the feature; rows before --eval-from are warm-up.
Output: rows evaluated, engine == recompute share, strategy hits, hits whose rule does NOT hold on the recomputed
value (violations), and non-hits where the rule would hold on the recomputed value (only a candidate: the strategy's
other rules may still be false)."""
import argparse, json, sys
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--extract", required=True); ap.add_argument("--feature-id", required=True)
ap.add_argument("--op", required=True, choices=[">", ">=", "<", "<=", "=="]); ap.add_argument("--threshold", type=float, required=True)
ap.add_argument("--eval-from", required=True); ap.add_argument("--config", default="../results/config_counter_features.csv")
ap.add_argument("--out")
a = ap.parse_args()
cfg = pd.read_csv(a.config).set_index("feature_id").loc[a.feature_id]
DIM = {"countryCode": "cc", "phoneNo": "phone_h", "realIp": "ip_h", "realIpc": "ipc_h", "uid": "uid_h", "realIpCountry": "ip_country", "tenant": None}
dim = json.loads(cfg.dimension) if str(cfg.dimension).startswith('"') else cfg.dimension
if dim not in DIM:
    sys.exit(f"dimension {dim!r} not supported by this extract")
uv = int(cfg.counter) == 1
cv = DIM.get(cfg.count_value) if uv else None
if uv and not cv:
    sys.exit(f"countValue {cfg.count_value!r} not supported by this extract")
conds = json.loads(cfg.conditions) if isinstance(cfg.conditions, str) and cfg.conditions.startswith("[") else []
d = pd.read_csv(a.extract, dtype=str).drop_duplicates("id")
d["t"] = pd.to_datetime(d.create_time); d = d.sort_values(["t", "id"]).reset_index(drop=True)
fv = d.feature_code_value.map(lambda s: json.loads(s) if isinstance(s, str) else [None, None])
d["code"], d["val"] = fv.str[0], pd.to_numeric(fv.str[1], errors="coerce")
mask = d.code.notna().values
for c in [c for c in conds if str(c).strip()]:
    if c.startswith("NOT_EQUAL_STRING(realIpCountry,"):
        mask &= (d.ip_country.fillna("") != c.split("'")[1]).values
    elif c.startswith("FIELD_BLANK(recaptchaV3Token") or c.startswith("FIELD_NOT_EXISTS(recaptchaV3Token") or c == "recaptchaV3Token==''":
        mask &= d.token_state.isin(["absent", "empty"]).values
    else:
        sys.exit(f"condition {c!r} not supported")
ts = d.t.values.astype("datetime64[s]").astype(np.int64); period = int(float(cfg.period_s))
key = d[DIM[dim]].fillna("") if DIM[dim] else pd.Series([""] * len(d))
ev = (d.t >= pd.Timestamp(a.eval_from)).values
rec = np.full(len(d), np.nan)
for _, idx in key.groupby(key).indices.items():
    idx = np.sort(idx); m = mask[idx]; tm = ts[idx][m]; vals = d[cv].values[idx][m] if uv else None
    for i in idx:
        if not ev[i]:
            continue
        lo_, hi_ = np.searchsorted(tm, ts[i] - period, side="left"), np.searchsorted(tm, ts[i], side="right")
        rec[i] = len(set(vals[lo_:hi_])) if uv else hi_ - lo_
ops = {">": np.greater, ">=": np.greater_equal, "<": np.less, "<=": np.less_equal, "==": np.equal}
holds = ops[a.op](rec, a.threshold)
E = ev & (d.code == "SUCCESS").values
hit = d.strategy_hit.astype(int).values > 0
res = {"feature_id": a.feature_id, "rule": f"value {a.op} {a.threshold:g}", "rows_evaluated": int(E.sum()),
       "engine_eq_recompute_share": round(float((d.val.values[E] == rec[E]).mean()), 4) if E.sum() else None,
       "engine_within1_share": round(float((np.abs(d.val.values[E] - rec[E]) <= 1).mean()), 4) if E.sum() else None,
       "strategy_hits": int((hit & ev).sum()), "hits_rule_holds_on_recompute": int((hit & ev & holds).sum()),
       "violations_hit_but_rule_false_on_recompute": int((hit & ev & ~holds).sum()),
       "nonhits_rule_true_on_recompute": int((~hit & E & holds).sum()),
       "engine_rule_true": int((E & ops[a.op](d.val.values, a.threshold)).sum())}
out = pd.DataFrame([res]); print(out.T.to_string(header=False))
if a.out:
    out.to_csv(a.out, index=False)
