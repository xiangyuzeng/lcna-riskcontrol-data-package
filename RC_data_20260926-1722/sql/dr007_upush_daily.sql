-- name: dr007_upush_daily
-- server: aws-luckyus-upush-rw (via MCP server mcp-db-gateway)
-- purpose: DR-007: t_verifycode_filled_statistics SUM(sent_num), SUM(filled_num) by statistic_date x country code x project (the only upush data read allowed)
-- kind: agg; windows: 1
-- params: {"date_from": "2026-08-25"}
-- run (NY): 2026-09-26 18:46

SELECT /*+ MAX_EXECUTION_TIME(10000) */ statistic_date, TRIM(LEADING '+' FROM COALESCE(area_code, '')) AS cc, from_app_name AS project,
  SUM(sent_num) AS sent_num, SUM(filled_num) AS filled_num, COUNT(*) AS n_stat_rows
FROM luckyus_iupushsms.t_verifycode_filled_statistics
WHERE statistic_date >= '{date_from}'
GROUP BY statistic_date, cc, project
ORDER BY statistic_date, cc, project
