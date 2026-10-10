-- name: dr037_crm_check
-- server: aws-luckyus-salescrm-rw (via MCP server mcp-db-gateway)
-- purpose: DR-037: t_user area_code format check and time range (counts / lengths only)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-10-10 02:23

SELECT /*+ MAX_EXECUTION_TIME(10000) */ COUNT(*) AS n_rows, MIN(create_time) AS min_create, MAX(create_time) AS max_create,
  COUNT(DISTINCT area_code) AS n_area_codes, MAX(CHAR_LENGTH(area_code)) AS max_len_area_code, SUM(area_code REGEXP '[0-9]{5,}') AS n_area_code_5plus_digits,
  SUM(area_code IS NULL OR area_code = '') AS n_area_code_empty, COUNT(DISTINCT tenant) AS n_tenants, SUM(tenant = 'LKUS') AS n_lkus
FROM luckyus_sales_crm.t_user
