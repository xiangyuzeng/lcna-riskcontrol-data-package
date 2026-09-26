#!/usr/bin/env python3
"""P1: merge the per-shard key-presence results (results/p1_keys_*.csv, results/p1_row_profile.csv)
into one table: scene x JSON source x key -> rows carrying the key, share of the scene's rows.
Input windows: one America/New_York day (see the header of sql/p1_keys_*.sql). Output:
results/p1_scene_rows.csv, results/p1_json_keys_summary.csv. Keys only, never values."""
import glob, os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")

prof = pd.read_csv(os.path.join(R, "p1_row_profile.csv"))
num = [c for c in prof.columns if c not in ("shard", "scene_id", "tenant", "access_id", "type")]
scene = prof.groupby(["scene_id", "tenant", "access_id", "type"], dropna=False)[num].sum().reset_index()
scene.to_csv(os.path.join(R, "p1_scene_rows.csv"), index=False)
tot = prof.groupby("scene_id")["n_rows"].sum()

out = []
for f in sorted(glob.glob(os.path.join(R, "p1_keys_*.csv"))):
    src = os.path.basename(f)[len("p1_keys_"):-4]
    if os.path.getsize(f) < 5:
        print(f"no rows: {os.path.basename(f)} (source never carries element keys in this window)")
        continue
    df = pd.read_csv(f)
    agg = {"n_rows": "sum"} | ({"n_elements": "sum"} if "n_elements" in df.columns else {})
    g = df.groupby(["scene_id", "json_key"]).agg(agg).reset_index()
    g.insert(0, "source", src)
    g["scene_rows"] = g["scene_id"].map(tot)
    g["share_of_scene_rows"] = (g["n_rows"] / g["scene_rows"]).round(4)
    out.append(g)
keys = pd.concat(out, ignore_index=True).sort_values(["scene_id", "source", "n_rows"], ascending=[True, True, False])
keys.to_csv(os.path.join(R, "p1_json_keys_summary.csv"), index=False)
print(f"scenes={scene.scene_id.nunique()} rows={int(prof.n_rows.sum())} key-rows={len(keys)}")
