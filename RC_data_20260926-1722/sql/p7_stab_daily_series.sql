-- name: p7_stab_daily_series
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P7 stability re-run of p4_daily_series for NY 2026-09-24
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-24 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 19:01

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date,
  t.cc_group, t.result_col, t.para_valid, t.email_key, t.email_nonempty, t.email_col_nonempty, t.phone_key_nonempty, t.phone_col_nonempty,
  COUNT(*) AS n, COUNT(DISTINCT t.sk) AS n_distinct_sharding_key, SUM(t.sk_eq_full) AS n_sk_eq_fullphone
FROM (SELECT
    l.result AS result_col,
    CASE WHEN l.country_code IS NULL OR l.country_code = '' THEN 'unknown'
         WHEN TRIM(LEADING '+' FROM l.country_code) = '1' THEN '+1'
         WHEN TRIM(LEADING '+' FROM l.country_code) = '86' THEN '+86'
         ELSE 'other' END AS cc_group,
    JSON_VALID(l.pa_txt) AS para_valid,
    CASE WHEN JSON_VALID(l.pa_txt) THEN JSON_EXTRACT(CAST(l.pa_txt AS JSON), '$.email') IS NOT NULL END AS email_key,
    CASE WHEN JSON_VALID(l.pa_txt) THEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(l.pa_txt AS JSON), '$.email')), '') <> '' END AS email_nonempty,
    COALESCE(l.email, '') <> '' AS email_col_nonempty,
    CASE WHEN JSON_VALID(l.pa_txt) THEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(l.pa_txt AS JSON), '$.phoneNo')), '') <> '' END AS phone_key_nonempty,
    COALESCE(l.phone, '') <> '' AS phone_col_nonempty,
    l.sharding_key AS sk,
    CASE WHEN JSON_VALID(l.pa_txt)
         THEN CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(CAST(l.pa_txt AS JSON), '$.fullPhoneNo')) AS BINARY) END AS sk_eq_full
  FROM (SELECT result, country_code, email, phone, sharding_key,
          CASE WHEN JSON_VALID(request_strategy_engine) THEN JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) END AS pa_txt
        FROM luckyus_iriskcontrolservice.{tbl}
        WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND tenant = 'LKUS' AND scene_id = 'LKUS_push') l
) t
GROUP BY t.cc_group, t.result_col, t.para_valid, t.email_key, t.email_nonempty, t.email_col_nonempty, t.phone_key_nonempty, t.phone_col_nonempty
