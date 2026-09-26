-- name: p1_fleet_sweep_mysql
-- servers: every gateway server of the engine (via MCP server mcp-db-gateway)
-- purpose: P1: every gateway MySQL server: information_schema names matching risk-control keywords (names/comments only, no data)
-- run (NY): 2026-09-26 17:41

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.match_type, x.schema_name, x.table_name, x.column_name, x.comment_text
FROM (
  SELECT 'schema' AS match_type, SCHEMA_NAME AS schema_name, '' AS table_name, '' AS column_name, '' AS comment_text
  FROM information_schema.SCHEMATA
  WHERE SCHEMA_NAME NOT IN ('mysql', 'sys', 'performance_schema', 'information_schema')
    AND SCHEMA_NAME REGEXP 'risk|rms|ods_|doris|strateg|captcha|verif'
  UNION ALL
  SELECT 'table', TABLE_SCHEMA, TABLE_NAME, '', TABLE_COMMENT
  FROM information_schema.TABLES
  WHERE TABLE_SCHEMA NOT IN ('mysql', 'sys', 'performance_schema', 'information_schema')
    AND TABLE_NAME REGEXP 'riskcontrol|risk|rms_|strateg|policy|rule|feature|scene|scenario|access_log|black|white|name_?list|templist|metric|result_?code|captcha|verify_?code|verifycode|backfill|filled|sms.*verif|verif.*code'
  UNION ALL
  SELECT 'column', TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, COLUMN_COMMENT
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA NOT IN ('mysql', 'sys', 'performance_schema', 'information_schema')
    AND COLUMN_NAME REGEXP 'riskcontrol|risk_|strategy_id|rule_id|feature_id|scene_id|black_?list|white_?list|captcha|verify_?code|filled|hit_strategy'
) x
ORDER BY x.match_type, x.schema_name, x.table_name, x.column_name
LIMIT 3000
