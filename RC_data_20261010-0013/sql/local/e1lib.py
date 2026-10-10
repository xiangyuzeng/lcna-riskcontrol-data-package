#!/usr/bin/env python3
"""Shared loader for the E1 row-level extract (local only; never packaged) and for the L1 long aggregate.

E1  : _local_only/raw/e1_YYYYMMDD.csv.gz (sql/e1_*.sql), one row per LKUS_push request, identities are salted hashes.
L1  : results/l1_long.csv (counts only), built by l1_merge.py from the local parts.
Every script that writes into results/ must go through out(), which refuses hash-like columns (`*_h`)."""
import glob, json, os
import numpy as np
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, RAW = os.path.join(PKG, "results"), os.path.join(PKG, "_local_only", "raw")
NY = "America/New_York"


def out(df, name, index=False):
    bad = [c for c in df.columns if str(c).endswith("_h")]
    if bad:
        raise SystemExit(f"refusing to write hash columns {bad} to {name}")
    p = os.path.join(R, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    df.to_csv(p, index=index)
    return df


def ver_num(v):
    """Version a.b.c -> a*1000000 + b*1000 + c (numeric, never as text: '1.4.9' > '1.4.30' as text)."""
    try:
        p = [int("".join(ch for ch in x if ch.isdigit()) or 0) for x in str(v).split(".")[:3]]
        return p[0] * 1000000 + p[1] * 1000 + p[2] if len(p) == 3 else np.nan
    except Exception:
        return np.nan


def _hits(s):
    return [x.split("|") for x in json.loads(s)] if isinstance(s, str) and s.startswith("[") else []


def load_e1(cuts=(0.3, 0.8), v3_ids=None):
    files = sorted(glob.glob(os.path.join(RAW, "e1_*.csv.gz")))
    if not files:
        raise SystemExit("no E1 parts in _local_only/raw/")
    d = pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)
    d = d.drop_duplicates(["shard", "id"])                     # ids are per shard; dedupe on (shard, id)
    d["create_time"] = pd.to_datetime(d.create_time)
    ny = d.create_time.dt.tz_localize("UTC").dt.tz_convert(NY)
    d["ny_date"], d["ny_hour"] = ny.dt.strftime("%Y-%m-%d"), ny.dt.hour
    d["utc_date"], d["utc_hour"] = d.create_time.dt.strftime("%Y-%m-%d"), d.create_time.dt.strftime("%Y-%m-%d %H")
    d["cc"] = d.cc_raw.fillna("").str.lstrip("+")
    d["cc_form"] = np.where(d.cc_raw.fillna("") == "", "empty", np.where(d.cc_raw.fillna("").str.startswith("+"), "plus", "bare"))
    d["cc_group"] = np.select([d.cc == "1", d.cc == "86", d.cc == ""], ["+1", "+86", "unknown"], "other")
    d["sms"] = d.email_present.astype(int) == 0
    d["app_state"] = np.where(d.app == "<absent>", "absent", np.where(d.app == "<empty>", "empty", "present"))
    d["phone_ne_ip_country"] = (d.phone_country.fillna("") != d.ip_country.fillna("")).astype(int)
    d["ip_geo"] = np.select([d.ip_country.fillna("") == "", d.ip_country == "美国", d.ip_country == d.phone_country.fillna("")],
                            ["unknown", "us", "eq_phone"], "other")
    d["version_num"] = d.version.map(ver_num)
    lo, hi = cuts

    def v3(row):
        if not isinstance(row, str):
            return (None, np.nan, None, None)
        els = [e for e in json.loads(row) if e]
        for e in els:
            if e.get("score") is not None:
                return (e.get("code"), float(e["score"]), e.get("valid"), e.get("fid"))
        for e in els:
            if v3_ids and e.get("fid") in v3_ids:
                return (e.get("code"), np.nan, e.get("valid"), e.get("fid"))
        return (els[0].get("code"), np.nan, None, els[0].get("fid")) if els else (None, np.nan, None, None)
    vv = d.recaptcha_json.map(v3)
    d["v3_code"], d["v3_score"], d["v3_valid"], d["v3_fid"] = vv.str[0], vv.str[1], vv.str[2], vv.str[3]
    d["v3_bucket"] = np.select([d.v3_score.isna(), d.v3_score < lo, d.v3_score < hi], ["missing", f"<{lo}", f"{lo}-{hi}"], f">={hi}")
    d["on"], d["pre"] = d.hits_online.map(_hits), d.hits_preonline.map(_hits)
    d["on_ids"] = d.on.map(lambda L: {x[0] for x in L})
    d["pre_ids"] = d.pre.map(lambda L: {x[0] for x in L})
    d["on_reject_ids"] = d.on.map(lambda L: {x[0] for x in L if str(x[1]).upper().startswith("REJECT")})
    d["rules"] = d.rules_json.map(lambda s: json.loads(s) if isinstance(s, str) and s.startswith("{") else {})
    return d.reset_index(drop=True)


def unique_reject(d, sid, reject_prefix="REJECT"):
    """tk10 semantics per request: online hit with no other online REJECT-class hit, or pre-online hit with no online
    REJECT-class hit at all."""
    other = d.on.map(lambda L: sum(1 for x in L if str(x[1]).upper().startswith(reject_prefix) and x[0] != sid))
    s_on = d.on_ids.map(lambda s: sid in s)
    s_pre = d.pre_ids.map(lambda s: sid in s)
    return s_on & (other == 0), s_pre & (other == 0), s_on, s_pre


def load_l1():
    return pd.read_csv(os.path.join(R, "l1_long.csv"), dtype={"cc": str, "shard": str})
