#!/usr/bin/env python3
"""P7 stability: compare the three re-runs (results/p7_stab_*.csv, run at the end of the DB phase) with the original results.
  - p7_stab_l1    (NY 2026-10-05) vs results/l1_long.csv rows of that day ('h' counts, 'd' distinct phones)
  - p7_stab_hits  (NY 2026-10-05) vs results/p2_hits_7d.csv rows of that day
  - p7_stab_dr014 (NY 2026-10-09) vs results/dr014_sharding_key_by_scene_20261009.csv
Writes results/p7_stability.csv."""
import os
import pandas as pd
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n))
rows = []
a = rd("p7_stab_l1.csv"); b = rd("l1_long.csv"); b = b[b.ny_date == "2026-10-05"]
rows.append({"query": "L1 NY 2026-10-05: requests ('h' rows)", "original": int(b[b.lvl == "h"].n.sum()), "rerun": int(a[a.lvl == "h"].n.sum())})
rows.append({"query": "L1 NY 2026-10-05: distinct phones ('d' rows, summed over cc)", "original": int(b[b.lvl == "d"].n_phones.sum()), "rerun": int(a[a.lvl == "d"].n_phones.sum())})
a = rd("p7_stab_hits.csv"); b = rd("p2_hits_7d.csv"); b = b[b.ny_date == "2026-10-05"]
rows.append({"query": "p2_hits_7d NY 2026-10-05 (strategy hit PV)", "original": int(b.pv.sum()), "rerun": int(a.pv.sum())})
a = rd("p7_stab_dr014.csv"); b = rd("dr014_sharding_key_by_scene_20261009.csv")
rows.append({"query": "DR-014 NY 2026-10-09 (rows; sharding_key = user_no column)", "original": f"{int(b.n.sum())}; {int(b.sk_eq_user_no_col.sum())}",
             "rerun": f"{int(a.n.sum())}; {int(a.sk_eq_user_no_col.sum())}"})
out = pd.DataFrame(rows); out["equal"] = out.original.astype(str) == out.rerun.astype(str)
out.to_csv(os.path.join(R, "p7_stability.csv"), index=False); print(out.to_string(index=False))
