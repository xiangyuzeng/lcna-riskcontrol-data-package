#!/usr/bin/env python3
"""Parameters for the SQL cross-checks, read from this run's config export and op-log timeline (nothing hardcoded):
  SW_<tag>   : UTC time of the strategy's LAST status change to online (1) in t_operation_log (tk10 switch_utc)
  RN         : quoted list of REJECT-class result names (config_resultcode)
  CCS_<tag>  : quoted list (no '+') of the country codes in the strategy's current countryCode INCLUDE rule
Prints shell assignments; also writes results/q7_params.csv."""
import os, re
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n), dtype=str)
t, st, rule, rc = rd("p2_oplog_timeline.csv"), rd("config_strategy.csv"), rd("config_rule.csv"), rd("config_resultcode.csv")
TAGS = {"43NA": "strategy_43NaEzJmiQFk", "BYXA": "strategy_bYXaOJ4qXtW4", "WVNG": "strategy_WvNGjLMgoOyn"}
rows, outl = [], []
for tag, sid in TAGS.items():
    x = t[(t.object_id == sid) & (t.field == "status") & (t.after == "1")].sort_values("operation_time_utc")
    sw = x.operation_time_utc.iloc[-1] if len(x) else ""
    expr = st.set_index("strategy_id").strategy_express.get(sid, "")
    rids = re.findall(r"rule_[A-Za-z0-9]+", str(expr))
    cr = rule[rule.rule_id.isin(rids) & (rule.feature_id == "countryCode") & (rule.condition_type == "INCLUDE")]
    ccs = sorted({c.strip().lstrip("+") for v in cr.condition_value.dropna() for c in v.split(",") if c.strip()}, key=lambda c: (len(c), c))
    outl += [f"SW_{tag}='{sw}'", "CCS_%s=\"%s\"" % (tag, ",".join(f"'{c}'" for c in ccs))]
    rows.append({"tag": tag, "strategy_id": sid, "switch_utc_last_to_online": sw, "country_rule": " ".join(cr.rule_id), "n_codes": len(ccs), "codes": " ".join(ccs)})
rn = sorted(set(rc[rc.result_name.str.upper().str.startswith("REJECT")].result_name))
outl.append("RN=\"%s\"" % ",".join(f"'{v}'" for v in rn))
rows.append({"tag": "RN", "codes": " ".join(rn)})
pd.DataFrame(rows).to_csv(os.path.join(R, "q7_params.csv"), index=False)
print("\n".join(outl))
