-- name: p2_oplog_counts
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: t_operation_log per NY day: module x operation_type counts
-- kind: agg; windows: 25 [2026-09-01 04:00:00 .. 2026-09-26 04:00:00) UTC
-- params: {}
-- run (NY): 2026-09-25 09:09

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{ny_date}' AS ny_date, module, operation_type, COUNT(*) AS n,
  SUM(JSON_VALID(before_data)) AS n_before_json, SUM(JSON_VALID(after_data)) AS n_after_json,
  SUM(JSON_VALID(request_params)) AS n_request_json,
  MIN(operation_time) AS first_op_utc, MAX(operation_time) AS last_op_utc
FROM luckyus_iriskcontrolservice.t_operation_log
WHERE operation_time >= '{utc_start}' AND operation_time < '{utc_end}'
GROUP BY module, operation_type
