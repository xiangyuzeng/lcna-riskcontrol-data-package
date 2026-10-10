-- name: dr037_meta_upush
-- server: aws-luckyus-upush-rw (via MCP server mcp-db-gateway)
-- purpose: DR-037 discovery: push-service member copy and area-code-like columns on upush (information_schema only)
-- kind: agg; windows: 1
-- params: {"tables": "'t_lucky_member'"}
-- run (NY): 2026-10-10 01:19

SELECT /*+ MAX_EXECUTION_TIME(8000) */ c.TABLE_SCHEMA AS sch, c.TABLE_NAME AS tbl, c.ORDINAL_POSITION AS pos, c.COLUMN_NAME AS col, c.DATA_TYPE AS dtype,
  LEFT(c.COLUMN_COMMENT, 60) AS cmt, t.TABLE_ROWS AS est_rows,
  (SELECT GROUP_CONCAT(DISTINCT s.INDEX_NAME) FROM information_schema.STATISTICS s WHERE s.TABLE_SCHEMA = c.TABLE_SCHEMA AND s.TABLE_NAME = c.TABLE_NAME AND s.COLUMN_NAME = c.COLUMN_NAME) AS idx
FROM information_schema.COLUMNS c JOIN information_schema.TABLES t ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
WHERE c.TABLE_SCHEMA NOT IN ('mysql', 'sys', 'performance_schema', 'information_schema')
  AND (c.TABLE_NAME IN ({tables}) OR c.COLUMN_NAME REGEXP 'area_code|country_code|phone_code|mobile_area')
ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
