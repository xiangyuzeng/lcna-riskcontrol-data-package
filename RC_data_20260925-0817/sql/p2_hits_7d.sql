-- name: p2_hits_7d
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: LKUS_push 7 NY days: every online / pre-online strategy hit with the status, resultName, execPriority recorded in the hit element, by final result; PV and distinct phones (sharding_key, additive across shards)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-18 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 09:15

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, x.list, x.strategy_id, x.hit_status, x.result_name,
  x.exec_priority, x.strategy_type, x.vaild, x.final_result, COUNT(*) AS pv, COUNT(DISTINCT x.sk) AS uv_phones
FROM (
  SELECT 'online' AS list, j.strategy_id, j.hit_status, j.result_name, j.exec_priority, j.strategy_type, j.vaild,
         l.result AS final_result, l.sharding_key AS sk
  FROM (SELECT result, sharding_key, CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitStrategy')) AS JSON) AS h
        FROM luckyus_iriskcontrolservice.{tbl}
        WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l,
    JSON_TABLE(JSON_EXTRACT(l.h, '$'), '$[*]' COLUMNS (strategy_id VARCHAR(64) PATH '$.strategyId', hit_status VARCHAR(16) PATH '$.status',
      result_name VARCHAR(32) PATH '$.resultName', exec_priority VARCHAR(16) PATH '$.execPriority',
      strategy_type VARCHAR(8) PATH '$.strategyType', vaild VARCHAR(8) PATH '$.vaild')) j
  UNION ALL
  SELECT 'preonline' AS list, j.strategy_id, j.hit_status, j.result_name, j.exec_priority, j.strategy_type, j.vaild,
         l.result AS final_result, l.sharding_key AS sk
  FROM (SELECT result, sharding_key, CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitPreOnlineStrategy')) AS JSON) AS h
        FROM luckyus_iriskcontrolservice.{tbl}
        WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l,
    JSON_TABLE(JSON_EXTRACT(l.h, '$'), '$[*]' COLUMNS (strategy_id VARCHAR(64) PATH '$.strategyId', hit_status VARCHAR(16) PATH '$.status',
      result_name VARCHAR(32) PATH '$.resultName', exec_priority VARCHAR(16) PATH '$.execPriority',
      strategy_type VARCHAR(8) PATH '$.strategyType', vaild VARCHAR(8) PATH '$.vaild')) j
) x
GROUP BY x.list, x.strategy_id, x.hit_status, x.result_name, x.exec_priority, x.strategy_type, x.vaild, x.final_result
