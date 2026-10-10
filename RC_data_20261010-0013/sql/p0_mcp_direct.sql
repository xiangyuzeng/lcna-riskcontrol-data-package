-- name: p0_mcp_direct
-- purpose: P0 statements sent directly through MCP tools (not through toolkit/shard_runner.py), one at a time, 2026-10-09 22:17 .. 2026-10-10 00:16 NY.
--          Their outputs were transcribed into results/ by sql/local/p0_inventory.py (the literals in that script are the MCP replies).
-- No connection details are recorded here; only MCP server and tool names.

-- [1] mcp-db-gateway / list_servers                         -> results/p0_mcp_inventory.csv (server counts by engine)
-- [2] grafana-lucky / list_datasources                      -> results/p0_mcp_inventory.csv (Doris-iriskcontrol exists; no SQL tool)
-- [3] redshift / list_clusters                              -> results/p0_mcp_inventory.csv (returned an error)

-- [4] mcp-db-gateway / mysql_query, one call per server:
--     aws-luckyus-iriskcontrolservice-rw, aws-luckyus-upush-rw, aws-luckyus-salescrm-rw, aws-luckyus-salesorder-rw
--                                                           -> results/p0_show_grants_parsed.csv
SHOW GRANTS;

-- [5] mcp-db-gateway / redis_command, server luckyus-iriskcontrol (two calls, a few seconds apart)
--                                                           -> results/p0_redis_iriskcontrol.csv
-- INFO keyspace
-- DBSIZE

-- [6] mcp-db-gateway / mysql_query, server aws-luckyus-iriskcontrolservice-rw: the runner-validation statement for shard 0000 only
--     (same text as sql/p0_runner_validation.sql with {shard}=0000, {tbl}=t_access_log_0000, NY day 2026-10-09)
--                                                           -> results/p0_runner_validation_mcp_direct.csv
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '0000' AS shard, scene_id, result, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_access_log_0000
WHERE create_time >= '2026-10-09 04:00:00' AND create_time < '2026-10-10 04:00:00'
GROUP BY scene_id, result
ORDER BY scene_id, result;
