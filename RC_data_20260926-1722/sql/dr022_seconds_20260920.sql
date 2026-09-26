-- name: dr022_seconds_20260920
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-022: per-second counts by final result within +-2 minutes of NY midnight starting 2026-09-20 (create_time)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-20 03:58:00 .. 2026-09-20 04:02:00) UTC, chunk=hour
-- params: {"scene": "LKUS_push", "boundary_utc": "2026-09-20 04:00:00"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:42

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, TIMESTAMPDIFF(SECOND, '{boundary_utc}', t.create_time) AS sec_from_ny_midnight,
  t.final_result, t.sms, COUNT(*) AS n
FROM (SELECT create_time, result AS final_result,
        CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON), '$.email')), '') <> '' THEN 0 ELSE 1 END AS sms
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') t
GROUP BY sec_from_ny_midnight, t.final_result, t.sms
