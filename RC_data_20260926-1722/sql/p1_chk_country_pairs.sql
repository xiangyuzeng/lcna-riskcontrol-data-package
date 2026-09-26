-- name: p1_chk_country_pairs
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: LKUS_push NY 2026-09-19..09-25: consistency / cid x app / country pairs / email signals (aggregates only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-19 04:00:00 .. 2026-09-26 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 17:38

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, t.phone_country, t.real_ip_country, t.cc, COUNT(*) AS n
FROM (SELECT JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneCountry')) AS phone_country, JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')) AS real_ip_country,
        TRIM(LEADING '+' FROM JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.countryCode'))) AS cc
FROM (SELECT id, result, response, country_code, phone, user_no, sharding_key, request,
             CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa,
             JSON_EXTRACT(response_strategy_engine, '$.re') AS re
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') l) t
GROUP BY t.phone_country, t.real_ip_country, t.cc
