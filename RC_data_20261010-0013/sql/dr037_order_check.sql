-- name: dr037_order_check
-- server: aws-luckyus-salesorder-rw (via MCP server mcp-db-gateway)
-- purpose: DR-037: phone-code format check on paid orders of the last 30 days (counts / lengths only)
-- kind: agg; windows: 1 [2026-09-10 04:00:00 .. 2026-10-10 04:00:00) UTC
-- params: {}
-- run (NY): 2026-10-10 02:24

SELECT /*+ MAX_EXECUTION_TIME(10000) */ COUNT(*) AS n_orders, COUNT(DISTINCT m.take_hum_phone_code) AS n_codes, MAX(CHAR_LENGTH(m.take_hum_phone_code)) AS max_len_code,
  SUM(m.take_hum_phone_code REGEXP '[0-9]{5,}') AS n_code_5plus_digits, SUM(m.order_id IS NULL) AS n_no_member_row,
  COUNT(DISTINCT o.country_code) AS n_order_country_codes, MAX(CHAR_LENGTH(o.country_code)) AS max_len_order_country_code
FROM luckyus_sales_order.t_order o LEFT JOIN luckyus_sales_order.t_order_member m ON m.order_id = o.id
WHERE o.pay_time >= '{utc_start}' AND o.pay_time < '{utc_end}' AND o.tenant = 'LKUS' AND o.status IN (20, 90)
