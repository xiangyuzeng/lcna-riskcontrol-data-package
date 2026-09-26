-- name: p1_keys_ruleDetail_elem
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: JSON/column structure, all scenes, NY 2026-09-25 (keys and presence counts only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-25 04:00:00 .. 2026-09-26 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 17:34

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, l.scene_id, k.k AS json_key,
  COUNT(DISTINCT l.id) AS n_rows, COUNT(*) AS n_elements
FROM (SELECT id, scene_id, CASE WHEN JSON_TYPE(JSON_EXTRACT(response_strategy_engine, '$.re.ruleDetail')) = 'STRING' AND JSON_VALID(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.ruleDetail'))) THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.ruleDetail')) AS JSON) ELSE JSON_EXTRACT(response_strategy_engine, '$.re.ruleDetail') END AS arr
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND JSON_VALID(response_strategy_engine)) l,
  JSON_TABLE(JSON_EXTRACT(l.arr, '$'), '$[*]' COLUMNS (e JSON PATH '$')) a,
  JSON_TABLE(JSON_KEYS(a.e), '$[*]' COLUMNS (k VARCHAR(128) PATH '$')) k
GROUP BY l.scene_id, k.k
