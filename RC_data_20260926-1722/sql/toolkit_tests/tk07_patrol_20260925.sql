-- name: toolkit_tests/tk07_patrol_20260925
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: daily patrol 2026-09-25 NY
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-25 04:00:00 .. 2026-09-26 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:58

-- tk07_daily_patrol: morning check numbers for one America/New_York day (run via patrol.py).
-- Per shard: final result x country code x email_key (= non-empty $.para.email), plus online / pre-online hit counts per strategy.
-- All k1/k2/k3 are converted to one collation: table columns and JSON_TABLE columns differ, and UNION refuses
-- mixed collations (MySQL error 1271).
-- Params : {scene}; window = one NY day ({utc_start}/{utc_end} from ny_day_bounds.py).
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, x.kind, x.k1, x.k2, x.k3, SUM(x.n) AS n
FROM (
  SELECT 'result' AS kind,
         CONVERT(l.result USING utf8mb4) COLLATE utf8mb4_0900_ai_ci AS k1,
         CONVERT(TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) USING utf8mb4) COLLATE utf8mb4_0900_ai_ci AS k2,
         CONVERT(CAST(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.request_strategy_engine, '$.para')) AS JSON), '$.email')), '') <> '' AS CHAR) USING utf8mb4) COLLATE utf8mb4_0900_ai_ci AS k3,
         1 AS n
  FROM luckyus_iriskcontrolservice.{tbl} l
  WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = '{scene}'
  UNION ALL
  SELECT 'online_hit', CONVERT(h.sid USING utf8mb4) COLLATE utf8mb4_0900_ai_ci, CONVERT(h.rn USING utf8mb4) COLLATE utf8mb4_0900_ai_ci,
         CONVERT(l.result USING utf8mb4) COLLATE utf8mb4_0900_ai_ci, 1
  FROM luckyus_iriskcontrolservice.{tbl} l,
    JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.response_strategy_engine, '$.re.hitStrategy')) AS JSON), '$[*]'
      COLUMNS (sid VARCHAR(64) PATH '$.strategyId', rn VARCHAR(32) PATH '$.resultName')) h
  WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = '{scene}'
  UNION ALL
  SELECT 'preonline_hit', CONVERT(h.sid USING utf8mb4) COLLATE utf8mb4_0900_ai_ci, CONVERT(h.rn USING utf8mb4) COLLATE utf8mb4_0900_ai_ci,
         CONVERT(l.result USING utf8mb4) COLLATE utf8mb4_0900_ai_ci, 1
  FROM luckyus_iriskcontrolservice.{tbl} l,
    JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.response_strategy_engine, '$.re.hitPreOnlineStrategy')) AS JSON), '$[*]'
      COLUMNS (sid VARCHAR(64) PATH '$.strategyId', rn VARCHAR(32) PATH '$.resultName')) h
  WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = '{scene}'
) x
GROUP BY x.kind, x.k1, x.k2, x.k3
