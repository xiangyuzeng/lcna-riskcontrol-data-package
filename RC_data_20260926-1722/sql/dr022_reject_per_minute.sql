-- name: dr022_reject_per_minute
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-022: per-minute counts by final result, UTC [2026-09-19 03:50, 04:10) = NY 09-18 23:50 .. 09-19 00:10 (create_time)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-19 03:50:00 .. 2026-09-19 04:10:00) UTC, chunk=hour
-- params: {"scene": "LKUS_push"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:32

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, DATE_FORMAT(t.create_time, '%Y-%m-%d %H:%i') AS utc_minute, t.final_result, t.sms,
  t.cc_group, COUNT(*) AS n
FROM (SELECT create_time, result AS final_result,
        CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON), '$.email')), '') <> '' THEN 0 ELSE 1 END AS sms,
        CASE WHEN TRIM(LEADING '+' FROM country_code) = '1' THEN '+1' WHEN TRIM(LEADING '+' FROM country_code) = '86' THEN '+86'
             WHEN COALESCE(country_code, '') = '' THEN 'unknown' ELSE 'other' END AS cc_group
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') t
GROUP BY utc_minute, t.final_result, t.sms, t.cc_group
