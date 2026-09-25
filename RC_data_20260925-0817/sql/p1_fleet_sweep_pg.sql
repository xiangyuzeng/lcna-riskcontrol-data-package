-- name: p1_fleet_sweep_pg
-- servers: every gateway server of the engine (via MCP server mcp-db-gateway)
-- purpose: gateway PostgreSQL server: information_schema names matching risk-control keywords
-- run (NY): 2026-09-25 08:29

SELECT 'table' AS match_type, table_schema AS schema_name, table_name, '' AS column_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND table_name ~* 'riskcontrol|risk|rms_|strateg|policy|rule|feature|scene|scenario|access_log|black|white|name_?list|templist|metric|result_?code|captcha|verify_?code|verifycode|backfill|filled'
UNION ALL
SELECT 'column', table_schema, table_name, column_name
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND column_name ~* 'riskcontrol|risk_|strategy_id|rule_id|feature_id|scene_id|black_?list|white_?list|captcha|verify_?code|filled|hit_strategy'
LIMIT 3000
