-- name: dr007_risk_utc_daily
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-007: LKUS_push per UTC day x country code x SMS flag x final result (UTC days to match upush statistic_date)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 33 [2026-08-25 00:00:00 .. 2026-09-27 00:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:42

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, DATE(t.create_time) AS utc_day, t.cc, t.sms, t.final_result, COUNT(*) AS n,
  COUNT(DISTINCT t.sk) AS n_distinct_phones
FROM (SELECT create_time, result AS final_result, sharding_key AS sk,
        CASE WHEN COALESCE(country_code, '') = '' THEN '<none>' ELSE TRIM(LEADING '+' FROM country_code) END AS cc,
        CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON), '$.email')), '') <> '' THEN 0 ELSE 1 END AS sms
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') t
GROUP BY utc_day, t.cc, t.sms, t.final_result
