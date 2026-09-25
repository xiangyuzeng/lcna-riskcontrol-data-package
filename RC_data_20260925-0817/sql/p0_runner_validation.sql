-- name: p0_runner_validation
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: runner vs direct MCP call: shard 0, one NY day, counts by scene x result
-- kind: agg; shards: 1 (0000..0000); batch: 1; windows: 1 [2026-09-24 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 08:25

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, scene_id, result, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}'
GROUP BY scene_id, result
ORDER BY scene_id, result
