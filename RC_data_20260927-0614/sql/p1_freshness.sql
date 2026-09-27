-- name: p1_freshness
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: newest create_time vs UTC_TIMESTAMP (timezone check), last 7 UTC hours (hourly statements)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-27 04:00:00 .. 2026-09-27 11:00:00) UTC, chunk=hour
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-27 06:23

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, MAX(create_time) AS newest_create_time, UTC_TIMESTAMP() AS utc_now, COUNT(*) AS n_last_window
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}'
