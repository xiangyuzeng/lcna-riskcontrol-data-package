-- name: p0_schema_tables
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0: tables of the risk-control schemas (grouped shards)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-26 17:25

SELECT /*+ MAX_EXECUTION_TIME(5000) */ TABLE_SCHEMA,
  CASE WHEN TABLE_NAME REGEXP '^t_access_log_[0-9]{4}$' THEN 't_access_log_NNNN'
       WHEN TABLE_NAME REGEXP '^t_gateway_validate_log_[0-9]{4}$' THEN 't_gateway_validate_log_NNNN'
       ELSE TABLE_NAME END AS table_group,
  COUNT(*) AS n_tables, SUM(TABLE_ROWS) AS est_rows, ROUND(SUM(DATA_LENGTH + INDEX_LENGTH) / 1048576, 1) AS size_mb,
  ROUND(MIN(DATA_LENGTH + INDEX_LENGTH) / 1048576, 1) AS min_mb, ROUND(MAX(DATA_LENGTH + INDEX_LENGTH) / 1048576, 1) AS max_mb,
  MIN(CREATE_TIME) AS min_create_time, MAX(UPDATE_TIME) AS max_update_time, MAX(ENGINE) AS engine,
  MAX(CREATE_OPTIONS) AS create_options, MAX(TABLE_COMMENT) AS table_comment
FROM information_schema.TABLES
WHERE TABLE_SCHEMA IN ('luckyus_iriskcontrolservice', 'backup_tables')
GROUP BY TABLE_SCHEMA, table_group ORDER BY TABLE_SCHEMA, table_group
