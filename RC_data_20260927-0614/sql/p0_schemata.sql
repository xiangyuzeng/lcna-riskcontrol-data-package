-- name: p0_schemata
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0: p0_schemata
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:16

SELECT /*+ MAX_EXECUTION_TIME(5000) */ s.SCHEMA_NAME, s.DEFAULT_CHARACTER_SET_NAME, s.DEFAULT_COLLATION_NAME,
  (SELECT COUNT(*) FROM information_schema.TABLES t WHERE t.TABLE_SCHEMA = s.SCHEMA_NAME) AS n_tables
FROM information_schema.SCHEMATA s ORDER BY s.SCHEMA_NAME
