-- name: p0_runner_validation
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0: runner validation, rows per scene x result on NY 2026-10-09 (counts only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-10-09 04:00:00 .. 2026-10-10 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-10-10 00:16

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, scene_id, result, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}'
GROUP BY scene_id, result
ORDER BY scene_id, result
