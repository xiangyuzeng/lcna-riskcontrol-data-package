-- name: p1_indexes
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: risk-control schema metadata: p1_indexes
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-25 08:30

SELECT /*+ MAX_EXECUTION_TIME(10000) */ TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME, INDEX_TYPE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'luckyus_iriskcontrolservice'
  AND (TABLE_NAME NOT REGEXP '^t_(access_log|gateway_validate_log)_[0-9]{4}$' OR TABLE_NAME IN ('t_access_log_0000', 't_gateway_validate_log_0000'))
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
