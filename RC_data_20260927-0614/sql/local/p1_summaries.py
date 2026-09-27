#!/usr/bin/env python3
"""P1: small summaries cited by 01_数据源与表清单.md (inputs are runner outputs listed per block)."""
import os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
# cid x app x cidOriginEnum x final result (results/p1_chk_cid_app.csv, 2026-09-18..24 NY)
c = pd.read_csv(os.path.join(R, "p1_chk_cid_app.csv"), dtype={"cid": str})
g = c.pivot_table(index=["cid", "app", "cid_origin"], columns="result_col", values="n", aggfunc="sum", fill_value=0).reset_index()
for k in ("PASS", "REJECT", "REVIEW"):
    if k not in g:
        g[k] = 0
g["total"] = g[["PASS", "REJECT", "REVIEW"]].sum(axis=1)
g["pass_share"] = (g.PASS / g.total).round(4)
g.sort_values("total", ascending=False).to_csv(os.path.join(R, "p1_cid_app_summary.csv"), index=False)
# final-result sources (results/p1_chk_consistency.csv)
k = pd.read_csv(os.path.join(R, "p1_chk_consistency.csv"))
k.groupby(["result_col", "response_result", "response_code", "re_result_name", "re_result_code"], dropna=False).n.sum() \
 .reset_index().to_csv(os.path.join(R, "p1_result_sources_summary.csv"), index=False)
# country value formats (results/p1_chk_country_pairs.csv)
p = pd.read_csv(os.path.join(R, "p1_chk_country_pairs.csv"), dtype=str); p["n"] = p.n.astype(int)
p.groupby(["cc", "phone_country"]).n.sum().reset_index().sort_values("n", ascending=False) \
 .to_csv(os.path.join(R, "p1_cc_phone_country.csv"), index=False)
print(g.sort_values("total", ascending=False).to_string(index=False))
