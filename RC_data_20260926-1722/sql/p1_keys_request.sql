-- name: p1_keys_request
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: JSON/column structure, all scenes, NY 2026-09-25 (keys and presence counts only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-25 04:00:00 .. 2026-09-26 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 17:31

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, l.scene_id, k.k AS json_key, COUNT(*) AS n_rows
FROM (SELECT scene_id, CAST(request AS JSON) AS j
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND JSON_VALID(request)) l,
  JSON_TABLE(JSON_KEYS(l.j), '$[*]' COLUMNS (k VARCHAR(128) PATH '$')) k
GROUP BY l.scene_id, k.k
