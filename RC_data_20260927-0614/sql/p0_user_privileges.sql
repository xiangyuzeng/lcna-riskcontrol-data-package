-- name: p0_user_privileges
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0: p0_user_privileges
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:16

SELECT /*+ MAX_EXECUTION_TIME(5000) */ x.level, x.object_name, x.PRIVILEGE_TYPE, x.IS_GRANTABLE
FROM (
  SELECT 'global' AS level, '*.*' AS object_name, PRIVILEGE_TYPE, IS_GRANTABLE, GRANTEE
  FROM information_schema.USER_PRIVILEGES
  UNION ALL
  SELECT 'schema', TABLE_SCHEMA, PRIVILEGE_TYPE, IS_GRANTABLE, GRANTEE FROM information_schema.SCHEMA_PRIVILEGES
  UNION ALL
  SELECT 'table', CONCAT(TABLE_SCHEMA, '.', TABLE_NAME), PRIVILEGE_TYPE, IS_GRANTABLE, GRANTEE FROM information_schema.TABLE_PRIVILEGES
) x
WHERE x.GRANTEE = CONCAT('''', SUBSTRING_INDEX(CURRENT_USER(), '@', 1), '''@''', SUBSTRING_INDEX(CURRENT_USER(), '@', -1), '''')
ORDER BY x.level, x.object_name, x.PRIVILEGE_TYPE
