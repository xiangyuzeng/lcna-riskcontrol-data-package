-- name: dr003_codes_daily
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-003 standing: daily status-code counts of every conditional or combo-dimension counter feature, LKUS_push, NY 2026-08-25..09-25
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 32 [2026-08-25 04:00:00 .. 2026-09-26 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push", "feature_ids": "'feature_21ATCUslkRsv','feature_3XkBz0wNh6RW','feature_AemrK847uPtt','feature_bvE9FL19wqag','feature_dqBHKec09Wwa','feature_e1Kmz7JqzsWc','feature_gskDZ8XLrG4s','feature_lN0hU25v6JRT','feature_n91JeGM6gD6i','feature_vApWJ93xOLe3'"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:11

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, f.fid AS feature_id, f.code, COUNT(*) AS n,
  SUM(f.v IS NULL OR f.v = '') AS n_empty_value
FROM luckyus_iriskcontrolservice.{tbl} l,
  JSON_TABLE(JSON_EXTRACT(l.response_strategy_engine, '$.re.featureDetail'), '$[*]'
    COLUMNS (fid VARCHAR(64) PATH '$.featureId', code VARCHAR(64) PATH '$.code', v VARCHAR(64) PATH '$.comments.apiResp')) f
WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = '{scene}' AND f.fid IN ({feature_ids})
GROUP BY f.fid, f.code
