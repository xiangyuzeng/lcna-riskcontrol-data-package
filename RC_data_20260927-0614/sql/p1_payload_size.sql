-- name: p1_payload_size
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: JSON/column structure, all scenes, NY 2026-09-26 (keys and presence counts only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-26 04:00:00 .. 2026-09-27 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-27 06:24

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, scene_id, COUNT(*) AS n,
  SUM(LENGTH(request_strategy_engine)) AS bytes_request_engine,
  SUM(LENGTH(response_strategy_engine)) AS bytes_response_engine,
  SUM(LENGTH(JSON_EXTRACT(response_strategy_engine, '$.re.featureDetail'))) AS bytes_feature_detail,
  SUM(LENGTH(JSON_EXTRACT(response_strategy_engine, '$.re.ruleDetail'))) AS bytes_rule_detail,
  SUM(LENGTH(request)) AS bytes_request, SUM(LENGTH(response)) AS bytes_response
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}'
GROUP BY scene_id
