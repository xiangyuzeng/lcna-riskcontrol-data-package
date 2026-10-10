-- name: dr035_upush_daily
-- server: aws-luckyus-upush-rw (via MCP server mcp-db-gateway)
-- purpose: DR-035: t_verifycode_filled_statistics SUM(sent) / SUM(filled) by statistic_date x project x provider x tenant x area code, from 2026-06-01 (aggregate only, §3.2 exception)
-- kind: agg; windows: 1
-- params: {"date_from": "2026-06-01"}
-- run (NY): 2026-10-10 02:23

SELECT /*+ MAX_EXECUTION_TIME(10000) */ statistic_date, from_app_name AS project, provider, tenant, TRIM(LEADING '+' FROM COALESCE(area_code, '')) AS cc,
  SUM(sent_num) AS sent_num, SUM(filled_num) AS filled_num, COUNT(*) AS n_stat_rows
FROM luckyus_iupushsms.t_verifycode_filled_statistics
WHERE statistic_date >= '{date_from}'
GROUP BY statistic_date, project, provider, tenant, cc
ORDER BY statistic_date, project, provider, tenant, cc
