#!/usr/bin/env python3
"""DR-001: when online hits disagree, which result is returned? Input results/dr001_conflicts.csv (SQL aggregate,
LKUS_push, NY 2026-08-25..2026-09-24). Output results/dr001_hypotheses.csv, results/dr001_conflict_patterns.csv.
Hypotheses tested on conflict rows (online hits with >= 2 different result classes):
 H1 lowest execPriority hit decides; H2 highest execPriority hit decides; H3 severity REJECT > REVIEW > PASS;
 H4 return-code priority PASS > REJECT > REVIEW; H5 result of bestStrategyId. REVIEW_xx codes count as REVIEW."""
import os
import numpy as np
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
d = pd.read_csv(os.path.join(R, "dr001_conflicts.csv"))
cls = lambda s: s.fillna("").astype(str).str.replace(r"^REVIEW.*", "REVIEW", regex=True)
for c in ("top_result", "low_result", "best_result", "final_result", "engine_result"):
    d[c] = cls(d[c])
d["n_classes"] = d[["has_pass", "has_reject", "has_review"]].fillna(0).sum(axis=1)
d["period"] = np.select([d.ny_date <= "2026-09-07", d.ny_date == "2026-09-08"], ["A: 08-25..09-07", "B: 09-08 (change at 23:29 NY)"], "C: 09-09..09-24")
d["H3"] = np.where(d.has_reject == 1, "REJECT", np.where(d.has_review == 1, "REVIEW", "PASS"))
d["H4"] = np.where(d.has_pass == 1, "PASS", np.where(d.has_reject == 1, "REJECT", "REVIEW"))
c = d[d.n_classes >= 2]
rows = []
for per, g in list(c.groupby("period")) + [("all", c)]:
    n = g.n.sum()
    r = {"period": per, "conflict_rows": int(n)}
    for h, col in (("H1_lowest_priority_wins", "low_result"), ("H2_highest_priority_wins", "top_result"), ("H3_REJECT>REVIEW>PASS", "H3"),
                   ("H4_PASS>REJECT>REVIEW", "H4"), ("H5_bestStrategyId", "best_result")):
        r[h] = round(float(g.loc[g[col] == g.final_result, "n"].sum() / n), 4) if n else np.nan
        r[h + "_engine"] = round(float(g.loc[g[col] == g.engine_result, "n"].sum() / n), 4) if n else np.nan
    rows.append(r)
pd.DataFrame(rows).to_csv(os.path.join(R, "dr001_hypotheses.csv"), index=False)
pat = c.groupby(["period", "has_pass", "has_reject", "has_review", "top_result", "max_pass_prio", "max_reject_prio", "engine_result", "final_result"],
                dropna=False).n.sum().reset_index().sort_values(["period", "n"], ascending=[True, False])
pat.to_csv(os.path.join(R, "dr001_conflict_patterns.csv"), index=False)
allrows = d.groupby(["period", "n_classes"]).n.sum().unstack(fill_value=0)
allrows.reset_index().to_csv(os.path.join(R, "dr001_rows_by_class_count.csv"), index=False)
print(pd.DataFrame(rows).to_string(index=False)); print(allrows); print(pat.head(30).to_string(index=False))
