-- name: p1_freshness
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: newest create_time vs UTC_TIMESTAMP (timezone check), last 2 UTC hours
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 2 [2026-09-26 20:00:00 .. 2026-09-26 22:00:00) UTC, chunk=hour
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 17:30

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, MAX(create_time) AS newest_create_time, UTC_TIMESTAMP() AS utc_now, COUNT(*) AS n_last_window
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}'
