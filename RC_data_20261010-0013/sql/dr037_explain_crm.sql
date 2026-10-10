-- name: dr037_explain_crm
-- server: aws-luckyus-salescrm-rw (via MCP server mcp-db-gateway)
-- purpose: DR-037: EXPLAIN of the member query on one month (plan only)
-- kind: agg; windows: 1 [2026-09-01 00:00:00 .. 2026-10-01 00:00:00) UTC
-- params: {"new30_start": "2026-09-10 04:00:00", "d90_start": "2026-07-12 04:00:00"}
-- run (NY): 2026-10-10 02:23

EXPLAIN SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{utc_start}' AS month_start_utc, TRIM(LEADING '+' FROM COALESCE(u.area_code, '')) AS cc, u.status AS user_status,
  COUNT(*) AS members, SUM(u.create_time >= '{new30_start}') AS new_30d,
  SUM(p.first_pay_time IS NOT NULL) AS with_first_pay, SUM(p.first_order_time IS NOT NULL) AS with_first_order,
  SUM(p.last_order_time >= '{d90_start}') AS last_order_in_90d, SUM(COALESCE(p.finish_order, 0) > 0) AS with_finished_order,
  SUM(p.user_no IS NULL) AS no_profile_row
FROM luckyus_sales_crm.t_user u
LEFT JOIN luckyus_sales_crm.t_user_profile p ON p.user_no = u.user_no
WHERE u.create_time >= '{utc_start}' AND u.create_time < '{utc_end}' AND u.tenant = 'LKUS'
GROUP BY cc, user_status
