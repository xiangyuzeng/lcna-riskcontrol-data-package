-- name: dbg_hits
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: debug
-- kind: agg; shards: 1 (0000..0000); batch: 1; windows: 1 [2026-09-24 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 09:14

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, JSON_TYPE(l.h_on) AS t_on, JSON_TYPE(l.h_pre) AS t_pre,
  JSON_LENGTH(l.h_on) AS len_on, JSON_LENGTH(l.h_pre) AS len_pre,
  JSON_LENGTH(JSON_ARRAY(JSON_OBJECT('list', 'online', 'hits', l.h_on), JSON_OBJECT('list', 'preonline', 'hits', l.h_pre))) AS len_arr,
  JSON_TYPE(JSON_EXTRACT(JSON_ARRAY(JSON_OBJECT('list', 'online', 'hits', l.h_on), JSON_OBJECT('list', 'preonline', 'hits', l.h_pre)), '$[1].hits')) AS t_arr_pre,
  COUNT(*) AS n
FROM (SELECT CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitStrategy')) AS JSON) AS h_on,
             CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitPreOnlineStrategy')) AS JSON) AS h_pre
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') l
GROUP BY t_on, t_pre, len_on, len_pre, len_arr, t_arr_pre
