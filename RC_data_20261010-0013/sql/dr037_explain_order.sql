-- name: dr037_explain_order
-- server: aws-luckyus-salesorder-rw (via MCP server mcp-db-gateway)
-- purpose: DR-037: EXPLAIN of the paying-user query on one 30-day window (plan only)
-- kind: agg; windows: 1 [2026-09-10 04:00:00 .. 2026-10-10 04:00:00) UTC
-- params: {}
-- run (NY): 2026-10-10 02:24

EXPLAIN SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{utc_start}' AS window_start_utc, '{utc_end}' AS window_end_utc,
  TRIM(LEADING '+' FROM COALESCE(m.take_hum_phone_code, '')) AS cc, o.currency_code,
  COUNT(*) AS paid_orders, COUNT(DISTINCT o.user_no) AS paying_users
FROM luckyus_sales_order.t_order o LEFT JOIN luckyus_sales_order.t_order_member m ON m.order_id = o.id
WHERE o.pay_time >= '{utc_start}' AND o.pay_time < '{utc_end}' AND o.tenant = 'LKUS' AND o.status IN (20, 90)
GROUP BY cc, o.currency_code
