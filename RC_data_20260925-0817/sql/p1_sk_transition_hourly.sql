-- name: p1_sk_transition_hourly
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-014: hour of the sharding_key change on 2026-08-18 NY (boolean counts only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-08-18 04:00:00 .. 2026-08-19 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 08:54

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, DATE_FORMAT(t.create_time, '%Y-%m-%d %H:00') AS utc_hour,
  COUNT(*) AS n, SUM(t.sk_eq_full) AS n_sk_eq_fullphone, SUM(t.sk_eq_uid) AS n_sk_eq_uid, SUM(t.full_absent) AS n_fullphone_absent
FROM (SELECT create_time,
        CAST(sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON), '$.fullPhoneNo')) AS BINARY) AS sk_eq_full,
        CAST(sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON), '$.uid')) AS BINARY) AS sk_eq_uid,
        JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON), '$.fullPhoneNo') IS NULL AS full_absent
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') t
GROUP BY utc_hour
