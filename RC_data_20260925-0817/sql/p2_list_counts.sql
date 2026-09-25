-- name: p2_list_counts
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: black/white list and alarm-recipient entry counts by type x tenant x source (contents never selected)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-25 09:09

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.* FROM (
  SELECT 't_blacklist' AS list_table, type AS list_type, tenant, source, NULL AS temp, COUNT(*) AS n_entries,
         MIN(create_time) AS first_created, MAX(create_time) AS last_created, MAX(modify_time) AS last_modified
  FROM luckyus_iriskcontrolservice.t_blacklist GROUP BY type, tenant, source
  UNION ALL
  SELECT 't_whitelist', type, tenant, source, temp, COUNT(*), MIN(create_time), MAX(create_time), MAX(modify_time)
  FROM luckyus_iriskcontrolservice.t_whitelist GROUP BY type, tenant, source, temp
  UNION ALL
  SELECT 't_alarm_recipient', NULL, tenant, NULL, deleted, COUNT(*), MIN(create_time), MAX(create_time), MAX(modify_time)
  FROM luckyus_iriskcontrolservice.t_alarm_recipient GROUP BY tenant, deleted
) x ORDER BY x.list_table, x.tenant, x.list_type
