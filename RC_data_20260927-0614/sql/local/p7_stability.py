#!/usr/bin/env python3
"""P7 stability: compare the re-runs results/p7_stab_*.csv with the original results for the same windows.
  - p7_stab_daily_series (NY 2026-09-25)   vs results/p4_daily_series.csv rows of that day
  - p7_stab_hits (NY 2026-09-25)            vs results/p2_hits_7d.csv rows of that day
  - p7_stab_dr014 (NY 2026-09-26)           vs results/dr014_sharding_key_by_scene_20260926.csv
Writes results/p7_stability.csv."""
import os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n))
rows = []
a = rd("p7_stab_daily_series.csv"); b = rd("p4_daily_series.csv"); b = b[b.ny_date == "2026-09-25"]
rows.append({"query": "p4_daily_series NY 2026-09-25 (rows by cc group x result)", "original": int(b.n.sum()), "rerun": int(a.n.sum())})
a = rd("p7_stab_hits.csv"); b = rd("p2_hits_7d.csv"); b = b[b.ny_date == "2026-09-25"]
rows.append({"query": "p2_hits_7d NY 2026-09-25 (strategy hit PV)", "original": int(b.pv.sum()), "rerun": int(a.pv.sum())})
a = rd("p7_stab_dr014.csv"); b = rd("dr014_sharding_key_by_scene_20260926.csv")
rows.append({"query": "dr014 NY 2026-09-26 (rows; sharding_key = user_no column)", "original": f"{int(b.n.sum())}; {int(b.sk_eq_user_no_col.sum())}",
             "rerun": f"{int(a.n.sum())}; {int(a.sk_eq_user_no_col.sum())}"})
out = pd.DataFrame(rows); out["equal"] = out.original.astype(str) == out.rerun.astype(str)
out.to_csv(os.path.join(R, "p7_stability.csv"), index=False); print(out.to_string(index=False))
