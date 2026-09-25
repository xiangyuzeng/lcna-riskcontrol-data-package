-- name: p2_oplog_row_keys
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: t_operation_log before/after rows[*] keys by module (keys only)
-- kind: agg; windows: 25 [2026-09-01 04:00:00 .. 2026-09-26 04:00:00) UTC
-- params: {}
-- run (NY): 2026-09-25 09:10

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.module, x.src, JSON_TYPE(JSON_EXTRACT(x.j, '$.rows')) AS rows_type, k.k AS row_key, COUNT(*) AS n
FROM (SELECT module, 'before_data' AS src, CAST(before_data AS JSON) AS j FROM luckyus_iriskcontrolservice.t_operation_log
      WHERE operation_time >= '{utc_start}' AND operation_time < '{utc_end}' AND JSON_VALID(before_data)
      UNION ALL
      SELECT module, 'after_data', CAST(after_data AS JSON) FROM luckyus_iriskcontrolservice.t_operation_log
      WHERE operation_time >= '{utc_start}' AND operation_time < '{utc_end}' AND JSON_VALID(after_data)) x,
  JSON_TABLE(JSON_EXTRACT(x.j, '$.rows'), '$[*]' COLUMNS (r JSON PATH '$')) rr,
  JSON_TABLE(JSON_KEYS(rr.r), '$[*]' COLUMNS (k VARCHAR(128) PATH '$')) k
GROUP BY x.module, x.src, rows_type, k.k
