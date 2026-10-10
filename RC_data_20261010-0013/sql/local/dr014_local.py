#!/usr/bin/env python3
"""DR-014 standing: per scene, which candidate key the sharding key equals (DR-021 method), from
results/dr014_sharding_key_by_scene_<day>.csv -> results/dr014_summary.csv and results/dr014_best_candidate.csv (counts only)."""
import os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
f14 = sorted(f for f in os.listdir(R) if f.startswith("dr014_sharding_key_by_scene_") and f.endswith(".csv"))[-1]
k = pd.read_csv(os.path.join(R, f14))
num = [c for c in k.columns if c.startswith(("sk_eq", "has_", "sk_empty", "sk_starts", "sk_all")) or c == "n"]
g = k.groupby(["ny_date", "scene_id"])[num].sum().reset_index()
for c in [c for c in num if c.startswith("sk_eq")]:
    g[c.replace("sk_eq_", "share_eq_")] = (g[c] / g.n).round(4)
eq = [c for c in g.columns if c.startswith("share_eq_")]
best = []
for r in g.itertuples(index=False):
    rr = r._asdict(); mx = max(rr[c] for c in eq)
    at_max = sorted(c.replace("share_eq_", "") for c in eq if rr[c] == mx)
    nxt = sorted(((rr[c], c.replace("share_eq_", "")) for c in eq if rr[c] < mx), reverse=True)[:1]
    grp = "phone" if "fullPhoneNo" in at_max else ("userNo" if "userNo" in at_max else "other")
    best.append({"ny_date": r.ny_date, "scene_id": r.scene_id, "rows": r.n, "best_candidates": "+".join(at_max), "best_share": mx,
                 "scene_group": grp, "next_best": f"{nxt[0][1]} {nxt[0][0]}" if nxt else "", "sk_empty": r.sk_empty})
g.to_csv(os.path.join(R, "dr014_summary.csv"), index=False)
b = pd.DataFrame(best); b.to_csv(os.path.join(R, "dr014_best_candidate.csv"), index=False)
print(b.to_string(index=False))
