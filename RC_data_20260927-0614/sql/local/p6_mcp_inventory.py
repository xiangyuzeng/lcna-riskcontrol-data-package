#!/usr/bin/env python3
"""DR-013 evidence as a result file (counts only, no server names): number of servers per engine behind the MCP server
mcp-db-gateway (tool list_servers, called here), servers covered by the P1 fleet sweep (results/_runlog.csv), and
schemas named ods_* found by that sweep (results/p1_fleet_sweep_mysql.csv). --redshift-status records the outcome of
the redshift MCP list_clusters call made in this session (the call itself is not scriptable from here).
Run through _local_only/gw.sh (reads the gateway address at run time; never printed)."""
import argparse, os, sys
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
sys.path.insert(0, os.path.join(PKG, "toolkit"))
import shard_runner  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--redshift-status", required=True)
a = ap.parse_args()
gw = shard_runner.Gateway(); gw.connect()
try:
    srv = gw.call("list_servers", {})
finally:
    gw.close()
rl = pd.read_csv(os.path.join(R, "_runlog.csv"), dtype=str)
fs = pd.read_csv(os.path.join(R, "p1_fleet_sweep_mysql.csv"), dtype=str)
ods = fs[(fs.match_type == "schema") & fs.schema_name.str.startswith("ods_")]
rows = [("mcp-db-gateway", f"list_servers：{k} 服务器数", len(v)) for k, v in sorted(srv.items())]
for n_ in ("p1_fleet_sweep_mysql", "p1_fleet_sweep_pg"):
    r = rl[rl.name == n_]
    if len(r):
        rows.append(("mcp-db-gateway", f"P1 名字扫描覆盖（{n_}）", r.iloc[-1, 2]))
rows.append(("mcp-db-gateway", "名字扫描发现的 ods_* 库", len(ods)))
rows.append(("redshift", "list_clusters", a.redshift_status))
out = pd.DataFrame(rows, columns=["mcp_server", "item", "value"]).assign(checked_ny=shard_runner.ny_now().strftime("%Y-%m-%d %H:%M"))
out.to_csv(os.path.join(R, "p0_mcp_inventory.csv"), index=False)
print(out.to_string(index=False))
