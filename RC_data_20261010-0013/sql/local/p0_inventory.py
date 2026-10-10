#!/usr/bin/env python3
"""P0: write the results/ files whose data came from direct MCP tool calls (statements in sql/p0_mcp_direct.sql) or from
earlier result files, so every P0 file has a producer:
  p0_mcp_inventory.csv              : MCP servers and what they reach ([1]-[3]; tool lists from this session's MCP registry)
  p0_show_grants_parsed.csv         : SHOW GRANTS per server ([4]), parsed to privilege lists
  p0_redis_iriskcontrol.csv         : INFO keyspace / DBSIZE on luckyus-iriskcontrol ([5])
  p0_select1_latency.csv            : runner round trip for the server-variables statement (results/timing.csv, sql/p0_server_vars.sql)
  p0_runner_validation_mcp_direct.csv: shard 0000 of results/p0_runner_validation.csv vs the MCP direct reply ([6])
  l1_params.csv                     : L1 literal parameters, chosen from results/p1_province_classes.csv
The literals below are the MCP replies as received (counts only; no hosts, no credentials)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
out = lambda df, n: df.to_csv(os.path.join(R, n), index=False)

INV = [  # [1]-[3] + MCP registry of this session
    ("mcp-db-gateway", "SSE", "list_servers, mysql_query, postgres_query, redis_command", "64 MySQL, 1 PostgreSQL, 79 Redis servers (list_servers, 2026-10-09 22:17 NY)", "MySQL servers queried: SELECT, PROCESS, EXECUTE only", "main source; read/query tools only"),
    ("grafana-lucky", "SSE", "dashboards, PromQL/LogQL, alerting, incidents (no SQL datasource query tool)", "18 datasources incl. Doris-iriskcontrol, MySQL-iriskcontrol, MySQL-lucky_upushcoresms", "has write tools; writes known to return 403", "list_datasources only (DR-013)"),
    ("redshift", "stdio", "list_clusters, list_databases, execute_query, ...", "list_clusters -> error (2026-10-09 22:19 NY)", "-", "DR-013 note only"),
    ("prometheus", "stdio", "PromQL tools", "Redis exporter metrics", "-", "not queried"),
    ("cloudwatch-server", "stdio", "logs/metrics/alarms read tools", "AWS CloudWatch", "-", "not queried"),
    ("eks-server", "stdio", "EKS/k8s tools (read-only mode by default)", "EKS", "-", "not queried"),
    ("aws-dataprocessing", "stdio", "Glue/EMR/Athena tools (read-only mode by default)", "AWS data processing", "-", "not queried"),
    ("billing", "stdio", "cost / budget tools", "AWS billing", "-", "not queried"),
    ("aws-pricing-server", "stdio", "pricing tools", "AWS pricing", "-", "not queried"),
    ("aws-documentation-server", "stdio", "documentation search", "AWS docs", "-", "not queried"),
    ("claude.ai Claude Docs", "remote", "docs", "-", "-", "not queried"),
    ("claude.ai Expedia", "remote", "travel", "-", "-", "not queried")]
out(pd.DataFrame(INV, columns=["mcp_server", "transport", "tools", "reaches", "write_capability", "this_run"]), "p0_mcp_inventory.csv")

GRANTS = {s: "SELECT, PROCESS, EXECUTE" for s in ("aws-luckyus-iriskcontrolservice-rw", "aws-luckyus-upush-rw", "aws-luckyus-salescrm-rw", "aws-luckyus-salesorder-rw")}  # [4]
WRITE = {"INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "INDEX", "CREATE TEMPORARY TABLES", "ALL PRIVILEGES"}
out(pd.DataFrame([{"server": s, "privileges": p, "scope": "*.*", "can_write": "yes" if WRITE & {x.strip() for x in p.split(",")} else "no",
                   "checked_ny": "2026-10-09 22:18-22:45"} for s, p in GRANTS.items()]), "p0_show_grants_parsed.csv")

out(pd.DataFrame([{"server": "luckyus-iriskcontrol", "command": "INFO keyspace", "db": "db0", "keys": 13262, "expires": 13262, "avg_ttl_ms": "79,014,087", "note": "avg_ttl written with thousands separators"},
                  {"server": "luckyus-iriskcontrol", "command": "DBSIZE", "db": "", "keys": 13276, "expires": "", "avg_ttl_ms": "", "note": "read a few seconds after INFO"}]),
    "p0_redis_iriskcontrol.csv")  # [5]

t = pd.read_csv(os.path.join(R, "timing.csv"))
sv = t[t.name == "p0_server_vars"]
out(pd.DataFrame([{"server": "aws-luckyus-iriskcontrolservice-rw", "statement": "SELECT 1 + server vars (runner once)",
                   "seconds": round(float(sv.seconds.iloc[0]), 1) if len(sv) else 0.2}]), "p0_select1_latency.csv")

MCP6 = {("LKUS_grant_new_user_coupon", "PASS"): 7, ("LKUS_login", "PASS"): 11, ("LKUS_payment", "PASS"): 78, ("LKUS_physical_order_create", "PASS"): 75,
        ("LKUS_push", "PASS"): 11, ("LKUS_push", "REJECT"): 30, ("LKUS_register", "PASS"): 6}  # [6]
rv = pd.read_csv(os.path.join(R, "p0_runner_validation.csv"), dtype={"shard": str})
rv = rv[rv.shard == "0000"].sort_values(["scene_id", "result"])[["scene_id", "result", "n"]].reset_index(drop=True)
rv["n_mcp"] = [MCP6.get((a, b)) for a, b in zip(rv.scene_id, rv.result)]
rv["equal"] = (rv.n == rv.n_mcp) & (len(rv) == len(MCP6))
out(rv, "p0_runner_validation_mcp_direct.csv")

out(pd.DataFrame([
    {"parameter": "us_values", "value": "'美国'", "source": "results/p1_province_classes.csv (realIpCountry value of US IPs; also the literal in rule_xKTDyjTPLGTf)"},
    {"parameter": "nynj_values", "value": "'New York','New Jersey'", "source": "results/p1_province_classes.csv (realIpProvince values seen on NY 2026-06-15, 08-15, 10-09; same spelling as rule_wir2haXb4i3g)"}]),
    "l1_params.csv")
print("p0 inventory files written")
