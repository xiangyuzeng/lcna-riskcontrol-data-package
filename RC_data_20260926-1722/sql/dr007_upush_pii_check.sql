-- name: dr007_upush_pii_check
-- server: aws-luckyus-upush-rw (via MCP server mcp-db-gateway)
-- purpose: DR-007: shape check of t_verifycode_filled_statistics before reading it (lengths / patterns only)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-26 18:46

SELECT /*+ MAX_EXECUTION_TIME(10000) */ COUNT(*) AS n_rows, MIN(statistic_date) AS min_date, MAX(statistic_date) AS max_date,
  COUNT(DISTINCT area_code) AS n_area_codes, MAX(CHAR_LENGTH(area_code)) AS max_len_area_code,
  SUM(area_code REGEXP '[0-9]{5,}') AS n_area_code_5plus_digits,
  COUNT(DISTINCT from_app_name) AS n_projects, MAX(CHAR_LENGTH(from_app_name)) AS max_len_project,
  SUM(from_app_name REGEXP '[0-9]{7,}|@') AS n_project_digits_or_at,
  COUNT(DISTINCT provider) AS n_providers, SUM(provider REGEXP '[0-9]{7,}|@') AS n_provider_digits_or_at,
  COUNT(DISTINCT tenant) AS n_tenants, SUM(tenant REGEXP '[0-9]{7,}|@') AS n_tenant_digits_or_at
FROM luckyus_iupushsms.t_verifycode_filled_statistics
