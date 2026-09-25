-- name: p1_sk_concat_check_20260924
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-014: sharding_key vs CONCAT(country_code, phone) on 2026-09-24 NY (counts only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-24 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 08:55

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, COUNT(*) AS n,
  SUM(CAST(sharding_key AS BINARY) = CAST(CONCAT(country_code, phone) AS BINARY)) AS n_sk_eq_cc_col_plus_phone_col,
  SUM(CAST(sharding_key AS BINARY) = CAST(CONCAT(country_code, JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON), '$.phoneNo'))) AS BINARY)) AS n_sk_eq_cc_col_plus_para_phone
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push'
