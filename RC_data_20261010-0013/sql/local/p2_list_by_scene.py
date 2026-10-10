#!/usr/bin/env python3
"""P2 / DR-015: list entry counts by list type x scene x source.
The list tables (t_blacklist / t_whitelist) have no scene column: entries belong to a tenant (= access_id) and a list type
(`type` = namelist_type). A scene "uses" a list when one of its strategies references a list feature of that
namelist_type / check_type (1 = 黑名单 -> t_blacklist, 2 = 白名单 -> t_whitelist). Counts only, never contents.
Inputs: results/config_list_feature.csv, config_strategy_expanded.csv, p2_list_counts.csv. Output: results/p2_list_counts_by_scene.csv"""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n))
lf, x, lc = rd("config_list_feature.csv"), rd("config_strategy_expanded.csv"), rd("p2_list_counts.csv")
lc = lc[lc.list_table.isin(["t_blacklist", "t_whitelist"])].copy()
lc["check_type"] = lc.list_table.map({"t_blacklist": 1, "t_whitelist": 2})
use = x[x.feature_id.isin(lf.feature_id)].drop(columns=["feature_name"], errors="ignore").merge(lf[["feature_id", "feature_name", "namelist_type", "check_type", "access_id"]], on="feature_id")
use = use.groupby(["scene_id", "access_id", "feature_id", "feature_name", "namelist_type", "check_type"]).agg(
    strategies_online=("status", lambda s: int((s == 1).sum())), strategies_preonline=("status", lambda s: int((s == 2).sum())),
    strategies_offline=("status", lambda s: int((s == 0).sum()))).reset_index()
out = use.merge(lc[["tenant", "list_type", "check_type", "source", "temp", "n_entries"]], left_on=["access_id", "namelist_type", "check_type"],
                right_on=["tenant", "list_type", "check_type"], how="left").drop(columns=["tenant", "list_type"])
out["n_entries"] = out.n_entries.fillna(0).astype(int)
out["list_table"] = out.check_type.map({1: "t_blacklist", 2: "t_whitelist"})
out["note"] = "entries belong to the tenant, shared by every scene of that tenant that references the list"
out.sort_values(["access_id", "scene_id", "check_type", "namelist_type"]).to_csv(os.path.join(R, "p2_list_counts_by_scene.csv"), index=False)
print(out[["scene_id", "feature_name", "list_table", "namelist_type", "source", "n_entries", "strategies_online"]].to_string(index=False))
