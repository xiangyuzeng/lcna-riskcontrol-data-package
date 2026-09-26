-- name: p1_chk_consistency
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: LKUS_push NY 2026-09-19..09-25: consistency / cid x app / country pairs / email signals (aggregates only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-19 04:00:00 .. 2026-09-26 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 17:34

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, t.*, COUNT(*) AS n
FROM (SELECT
  l.result AS result_col,
  JSON_UNQUOTE(JSON_EXTRACT(l.response, '$.result')) AS response_result,
  JSON_UNQUOTE(JSON_EXTRACT(l.response, '$.code')) AS response_code,
  JSON_UNQUOTE(JSON_EXTRACT(l.re, '$.resultName')) AS re_result_name,
  JSON_UNQUOTE(JSON_EXTRACT(l.re, '$.resultCode')) AS re_result_code,
  CASE WHEN l.country_code IS NULL OR l.country_code = '' THEN 'empty' WHEN l.country_code LIKE '+%' THEN 'plus' ELSE 'bare' END AS cc_col_form,
  CASE WHEN JSON_EXTRACT(l.pa, '$.countryCode') IS NULL THEN 'absent' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.countryCode')) = '' THEN 'empty'
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.countryCode')) LIKE '+%' THEN 'plus' ELSE 'bare' END AS cc_para_form,
  CAST(TRIM(LEADING '+' FROM l.country_code) AS BINARY) = CAST(TRIM(LEADING '+' FROM JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.countryCode'))) AS BINARY) AS cc_col_eq_para,
  CAST(TRIM(LEADING '+' FROM JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.fullPhoneNo'))) AS BINARY) = CAST(CONCAT(TRIM(LEADING '+' FROM JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.countryCode'))), JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo'))) AS BINARY) AS full_eq_cc_phone,
  CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.fullPhoneNo')) AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo')) AS BINARY) AS full_eq_phone,
  CAST(l.phone AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo')) AS BINARY) AS phone_col_eq_para,
  JSON_EXTRACT(l.pa, '$.email') IS NOT NULL AS email_key,
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') <> '' AS email_nonempty,
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo')), '') <> '' AS phone_nonempty,
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.uid')), '') <> '' AS uid_nonempty,
  CHAR_LENGTH(l.sharding_key) AS sk_len,
  l.sharding_key REGEXP '^[0-9]+$' AS sk_digits,
  l.sharding_key REGEXP '^[0-9a-f]{32}$' AS sk_hex32,
  CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.uid')) AS BINARY) AS sk_eq_uid,
  CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo')) AS BINARY) AS sk_eq_phone,
  CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.fullPhoneNo')) AS BINARY) AS sk_eq_full,
  CAST(l.sharding_key AS BINARY) = CAST(CONCAT(TRIM(LEADING '+' FROM JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.countryCode'))), JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo'))) AS BINARY) AS sk_eq_ccphone,
  CAST(l.sharding_key AS BINARY) = CAST(l.user_no AS BINARY) AS sk_eq_user_no_col,
  CAST(l.sharding_key AS BINARY) = CAST(l.phone AS BINARY) AS sk_eq_phone_col,
  CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userNo')) AS BINARY) AS sk_eq_userno,
  CAST(l.sharding_key AS BINARY) = CAST(MD5(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.uid'))) AS BINARY) AS sk_eq_md5_uid,
  CAST(l.sharding_key AS BINARY) = CAST(MD5(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo'))) AS BINARY) AS sk_eq_md5_phone,
  CAST(l.sharding_key AS BINARY) = CAST(CAST(l.id AS CHAR) AS BINARY) AS sk_eq_id
FROM (SELECT id, result, response, country_code, phone, user_no, sharding_key, request,
             CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa,
             JSON_EXTRACT(response_strategy_engine, '$.re') AS re
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') l) t
GROUP BY t.result_col, t.response_result, t.response_code, t.re_result_name, t.re_result_code, t.cc_col_form, t.cc_para_form,
  t.cc_col_eq_para, t.full_eq_cc_phone, t.full_eq_phone, t.phone_col_eq_para, t.email_key, t.email_nonempty, t.phone_nonempty,
  t.uid_nonempty, t.sk_len, t.sk_digits, t.sk_hex32, t.sk_eq_uid, t.sk_eq_phone, t.sk_eq_full, t.sk_eq_ccphone, t.sk_eq_user_no_col,
  t.sk_eq_phone_col, t.sk_eq_userno, t.sk_eq_md5_uid, t.sk_eq_md5_phone, t.sk_eq_id
