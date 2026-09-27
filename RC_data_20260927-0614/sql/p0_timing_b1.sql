-- name: p0_timing_b1
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0 timing test: featureId x code counts, LKUS_push, NY 2026-09-26, batch 1
-- kind: agg; shards: 64 (0000..0063); batch: 1; windows: 1 [2026-09-26 04:00:00 .. 2026-09-27 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-27 06:17

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, f.featureId, f.code, COUNT(*) AS n,
  SUM(f.v IS NULL OR f.v = '') AS empty_value
FROM luckyus_iriskcontrolservice.{tbl} l,
  JSON_TABLE(JSON_EXTRACT(l.response_strategy_engine, '$.re.featureDetail'), '$[*]'
    COLUMNS (featureId VARCHAR(64) PATH '$.featureId', code VARCHAR(64) PATH '$.code',
             v VARCHAR(64) PATH '$.comments.apiResp')) f
WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = 'LKUS_push'
GROUP BY f.featureId, f.code
