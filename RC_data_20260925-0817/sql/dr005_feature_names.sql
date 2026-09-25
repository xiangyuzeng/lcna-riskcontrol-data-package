-- name: dr005_feature_names
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-005: featureId x feature name seen per NY day and scene (tenant LKUS), 2026-08-20..2026-09-24
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 36 [2026-08-20 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 09:37

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, l.scene_id, f.fid AS feature_id, f.nm AS feature_name, COUNT(*) AS n_rows
FROM luckyus_iriskcontrolservice.{tbl} l,
  JSON_TABLE(JSON_EXTRACT(l.response_strategy_engine, '$.re.featureDetail'), '$[*]'
    COLUMNS (fid VARCHAR(64) PATH '$.featureId', nm VARCHAR(512) PATH '$.name')) f
WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.tenant = 'LKUS'
GROUP BY l.scene_id, f.fid, f.nm
