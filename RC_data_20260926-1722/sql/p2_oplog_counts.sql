-- name: p2_oplog_counts
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2: t_operation_log per NY day (p2_oplog_counts; counts / keys only)
-- kind: agg; windows: 33 [2026-08-25 04:00:00 .. 2026-09-27 04:00:00) UTC
-- params: {}
-- run (NY): 2026-09-26 17:48

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{ny_date}' AS ny_date, module, operation_type, COUNT(*) AS n,
  SUM(JSON_VALID(before_data)) AS n_before_json, SUM(JSON_VALID(after_data)) AS n_after_json,
  SUM(JSON_VALID(request_params)) AS n_request_json,
  MIN(operation_time) AS first_op_utc, MAX(operation_time) AS last_op_utc
FROM luckyus_iriskcontrolservice.t_operation_log
WHERE operation_time >= '{utc_start}' AND operation_time < '{utc_end}'
GROUP BY module, operation_type
