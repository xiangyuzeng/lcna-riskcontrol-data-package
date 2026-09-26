-- name: p2_oplog_row_keys
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2: t_operation_log per NY day (p2_oplog_row_keys; counts / keys only)
-- kind: agg; windows: 33 [2026-08-25 04:00:00 .. 2026-09-27 04:00:00) UTC
-- params: {}
-- run (NY): 2026-09-26 17:49

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.module, x.src, JSON_TYPE(JSON_EXTRACT(x.j, '$.rows')) AS rows_type, k.k AS row_key, COUNT(*) AS n
FROM (SELECT module, 'before_data' AS src, CAST(before_data AS JSON) AS j FROM luckyus_iriskcontrolservice.t_operation_log
      WHERE operation_time >= '{utc_start}' AND operation_time < '{utc_end}' AND JSON_VALID(before_data)
      UNION ALL
      SELECT module, 'after_data', CAST(after_data AS JSON) FROM luckyus_iriskcontrolservice.t_operation_log
      WHERE operation_time >= '{utc_start}' AND operation_time < '{utc_end}' AND JSON_VALID(after_data)) x,
  JSON_TABLE(JSON_EXTRACT(x.j, '$.rows'), '$[*]' COLUMNS (r JSON PATH '$')) rr,
  JSON_TABLE(JSON_KEYS(rr.r), '$[*]' COLUMNS (k VARCHAR(128) PATH '$')) k
GROUP BY x.module, x.src, rows_type, k.k
