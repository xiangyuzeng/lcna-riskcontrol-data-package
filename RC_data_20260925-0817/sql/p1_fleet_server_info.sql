-- name: p1_fleet_server_info
-- servers: every gateway server of the engine (via MCP server mcp-db-gateway)
-- purpose: every gateway MySQL server: version, read-only flags, user schema names
-- run (NY): 2026-09-25 08:28

SELECT /*+ MAX_EXECUTION_TIME(10000) */ VERSION() AS version, @@read_only AS read_only, @@innodb_read_only AS innodb_read_only,
  (SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME NOT IN ('mysql', 'sys', 'performance_schema', 'information_schema')) AS n_user_schemas,
  (SELECT JSON_ARRAYAGG(SCHEMA_NAME) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME NOT IN ('mysql', 'sys', 'performance_schema', 'information_schema')) AS user_schemas
