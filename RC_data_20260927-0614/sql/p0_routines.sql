-- name: p0_routines
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0: p0_routines
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:16

SELECT /*+ MAX_EXECUTION_TIME(5000) */ ROUTINE_SCHEMA, ROUTINE_TYPE, ROUTINE_NAME, SECURITY_TYPE
FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA NOT IN ('sys', 'mysql', 'performance_schema', 'information_schema')
ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME LIMIT 500
