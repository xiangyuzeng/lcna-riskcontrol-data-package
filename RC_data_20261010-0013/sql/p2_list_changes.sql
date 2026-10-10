-- name: p2_list_changes
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2 / exploration: list entries created or modified since 2026-09-27 by stored day x type x tenant x source (counts only; contents never selected)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-10-10 01:05

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.* FROM (
  SELECT 't_blacklist' AS list_table, type AS list_type, tenant, source, 'created' AS change_kind, DATE(create_time) AS stored_day, COUNT(*) AS n_entries
  FROM luckyus_iriskcontrolservice.t_blacklist WHERE create_time >= '2026-09-27 00:00:00' GROUP BY type, tenant, source, DATE(create_time)
  UNION ALL
  SELECT 't_blacklist', type, tenant, source, 'modified_only', DATE(modify_time), COUNT(*)
  FROM luckyus_iriskcontrolservice.t_blacklist WHERE modify_time >= '2026-09-27 00:00:00' AND create_time < '2026-09-27 00:00:00' GROUP BY type, tenant, source, DATE(modify_time)
  UNION ALL
  SELECT 't_whitelist', type, tenant, source, 'created', DATE(create_time), COUNT(*)
  FROM luckyus_iriskcontrolservice.t_whitelist WHERE create_time >= '2026-09-27 00:00:00' GROUP BY type, tenant, source, DATE(create_time)
  UNION ALL
  SELECT 't_whitelist', type, tenant, source, 'modified_only', DATE(modify_time), COUNT(*)
  FROM luckyus_iriskcontrolservice.t_whitelist WHERE modify_time >= '2026-09-27 00:00:00' AND create_time < '2026-09-27 00:00:00' GROUP BY type, tenant, source, DATE(modify_time)
) x ORDER BY x.list_table, x.tenant, x.list_type, x.stored_day
