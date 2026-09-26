-- name: p1_shard_index_identity
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: risk-control schema metadata (p1_shard_index_identity)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-26 17:30

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.family, x.INDEX_NAME, x.SEQ_IN_INDEX, x.COLUMN_NAME, x.NON_UNIQUE, x.n_tables
FROM (
  SELECT LEFT(TABLE_NAME, CHAR_LENGTH(TABLE_NAME) - 5) AS family, INDEX_NAME, SEQ_IN_INDEX, COLUMN_NAME, NON_UNIQUE, COUNT(*) AS n_tables
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = 'luckyus_iriskcontrolservice' AND TABLE_NAME REGEXP '^t_(access_log|gateway_validate_log)_[0-9]{4}$'
  GROUP BY family, INDEX_NAME, SEQ_IN_INDEX, COLUMN_NAME, NON_UNIQUE
) x ORDER BY x.family, x.INDEX_NAME, x.SEQ_IN_INDEX
