-- name: p1_columns
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: risk-control schema metadata (p1_columns)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-26 17:29

SELECT /*+ MAX_EXECUTION_TIME(10000) */ TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY,
  COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'luckyus_iriskcontrolservice'
  AND (TABLE_NAME NOT REGEXP '^t_(access_log|gateway_validate_log)_[0-9]{4}$' OR TABLE_NAME IN ('t_access_log_0000', 't_gateway_validate_log_0000'))
ORDER BY TABLE_NAME, ORDINAL_POSITION
