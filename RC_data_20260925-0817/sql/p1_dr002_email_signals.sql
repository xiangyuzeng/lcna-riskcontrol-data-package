-- name: p1_dr002_email_signals
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-002 / DR-NEW: rows with an email key, a response.model key, or engine result != final result (counts only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-18 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 08:58

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, t.email_key, t.model_key, t.model_type, t.model_len,
  t.cid, t.result_col, t.re_result_name, t.cc_group, t.app_state, COUNT(*) AS n
FROM (SELECT
    JSON_EXTRACT(l.pa, '$.email') IS NOT NULL AS email_key,
    JSON_EXTRACT(l.response, '$.model') IS NOT NULL AS model_key,
    JSON_TYPE(JSON_EXTRACT(l.response, '$.model')) AS model_type,
    CHAR_LENGTH(JSON_UNQUOTE(JSON_EXTRACT(l.response, '$.model'))) AS model_len,
    JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.cid')) AS cid,
    l.result AS result_col,
    JSON_UNQUOTE(JSON_EXTRACT(l.re, '$.resultName')) AS re_result_name,
    CASE WHEN TRIM(LEADING '+' FROM l.country_code) = '1' THEN '+1' WHEN TRIM(LEADING '+' FROM l.country_code) = '86' THEN '+86'
         WHEN l.country_code IS NULL OR l.country_code = '' THEN 'unknown' ELSE 'other' END AS cc_group,
    CASE WHEN JSON_EXTRACT(l.pa, '$.app') IS NULL THEN 'absent' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.app')) = '' THEN 'empty' ELSE 'present' END AS app_state
  FROM (SELECT result, response, country_code,
          CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa,
          JSON_EXTRACT(response_strategy_engine, '$.re') AS re
        FROM luckyus_iriskcontrolservice.{tbl}
        WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') l
) t
WHERE t.email_key = 1 OR t.model_key = 1 OR t.re_result_name <> t.result_col
GROUP BY t.email_key, t.model_key, t.model_type, t.model_len, t.cid, t.result_col, t.re_result_name, t.cc_group, t.app_state
