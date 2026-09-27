-- name: p0_runner_validation
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0: runner vs direct MCP call, shard 0000, NY 2026-09-26
-- kind: agg; shards: 1 (0000..0000); batch: 1; windows: 1 [2026-09-26 04:00:00 .. 2026-09-27 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-27 06:19

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, scene_id, result, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}'
GROUP BY scene_id, result
ORDER BY scene_id, result
