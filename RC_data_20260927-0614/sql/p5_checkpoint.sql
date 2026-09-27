-- name: p5_checkpoint
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: reproducibility checkpoint: team cookbook window, 20 x 24 h ending 2026-09-10 20:09 UTC, with and without the country_code filter
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 20 [2026-08-21 20:09:00 .. 2026-09-10 20:09:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-27 07:09

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc,
  COUNT(*) AS rows_no_cc_filter,
  SUM(country_code IS NOT NULL AND country_code <> '') AS rows_cc_filter,
  SUM(result = 'PASS' AND country_code IS NOT NULL AND country_code <> '') AS pass_cc_filter,
  SUM(result = 'REJECT' AND country_code IS NOT NULL AND country_code <> '') AS reject_cc_filter,
  SUM(result = 'REVIEW' AND country_code IS NOT NULL AND country_code <> '') AS review_cc_filter
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND tenant = 'LKUS' AND scene_id = 'LKUS_push'
