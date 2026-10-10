-- name: p1_province_classes
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1 / L1 design: realIpCountry x realIpProvince value classes on NY 2026-06-15, 08-15, 10-09 (region names and counts only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 3 [2026-06-15 04:00:00 .. 2026-10-10 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-10-10 01:09

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc, t.real_ip_country, t.real_ip_province, t.cc_is_1, COUNT(*) AS n
FROM (SELECT COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')), '<null>') AS real_ip_country,
        COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpProvince')), '<null>') AS real_ip_province,
        TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) = '1' AS cc_is_1
      FROM (SELECT country_code, CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa FROM luckyus_iriskcontrolservice.{tbl}
            WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') l) t
GROUP BY t.real_ip_country, t.real_ip_province, t.cc_is_1
