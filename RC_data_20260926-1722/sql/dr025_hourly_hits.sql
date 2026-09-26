-- name: dr025_hourly_hits
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-025 / DR-004 / DR-017: hourly online and pre-online hits of the named strategies, UTC 2026-09-06 .. 2026-09-27 (09-26 partial)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 21 [2026-09-06 00:00:00 .. 2026-09-27 00:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push", "strategy_ids": "'strategy_bTCEWBZggaAP','strategy_AxAlIdejVA8m','strategy_NrsClIxvGxWc','strategy_tO7DZkJ1g0C2','strategy_sw3jC7bvFYEX'"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:32

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, x.utc_hour, x.list, x.strategy_id, x.hit_status, x.final_result, COUNT(*) AS pv,
  COUNT(DISTINCT x.sk) AS uv_phones
FROM (
  SELECT DATE_FORMAT(l.create_time, '%Y-%m-%d %H:00') AS utc_hour, 'online' AS list, j.strategy_id, j.hit_status, l.result AS final_result, l.sharding_key AS sk
  FROM (SELECT create_time, result, sharding_key, CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitStrategy')) AS JSON) AS h
        FROM luckyus_iriskcontrolservice.{tbl}
        WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l,
    JSON_TABLE(JSON_EXTRACT(l.h, '$'), '$[*]' COLUMNS (strategy_id VARCHAR(64) PATH '$.strategyId', hit_status VARCHAR(16) PATH '$.status')) j
  WHERE j.strategy_id IN ({strategy_ids})
  UNION ALL
  SELECT DATE_FORMAT(l.create_time, '%Y-%m-%d %H:00'), 'preonline', j.strategy_id, j.hit_status, l.result, l.sharding_key
  FROM (SELECT create_time, result, sharding_key, CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitPreOnlineStrategy')) AS JSON) AS h
        FROM luckyus_iriskcontrolservice.{tbl}
        WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l,
    JSON_TABLE(JSON_EXTRACT(l.h, '$'), '$[*]' COLUMNS (strategy_id VARCHAR(64) PATH '$.strategyId', hit_status VARCHAR(16) PATH '$.status')) j
  WHERE j.strategy_id IN ({strategy_ids})
) x
GROUP BY x.utc_hour, x.list, x.strategy_id, x.hit_status, x.final_result
