-- name: p5_checkpoint_edges
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: checkpoint: rows in the 10 minutes around the window start
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-08-21 20:04:00 .. 2026-08-21 20:14:00) UTC, chunk=hour
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:48

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc,
  COUNT(*) AS rows_no_cc_filter,
  SUM(country_code IS NOT NULL AND country_code <> '') AS rows_cc_filter,
  SUM(result = 'PASS' AND country_code IS NOT NULL AND country_code <> '') AS pass_cc_filter,
  SUM(result = 'REJECT' AND country_code IS NOT NULL AND country_code <> '') AS reject_cc_filter,
  SUM(result = 'REVIEW' AND country_code IS NOT NULL AND country_code <> '') AS review_cc_filter
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND tenant = 'LKUS' AND scene_id = 'LKUS_push'
