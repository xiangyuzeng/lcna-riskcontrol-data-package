-- name: dr025_hourly_hits_43na
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-025 supplement / DR-NEW: hourly online vs pre-online hits of strategy_43NaEzJmiQFk around its 2026-09-23 14:43 UTC status change 2 -> 1 (09-26 partial)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 5 [2026-09-22 00:00:00 .. 2026-09-27 00:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push", "strategy_ids": "'strategy_43NaEzJmiQFk'"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:49

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
