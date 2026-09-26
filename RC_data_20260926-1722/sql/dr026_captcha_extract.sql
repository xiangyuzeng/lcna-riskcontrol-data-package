-- name: dr026_captcha_extract
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-026: LKUS_captcha rows on NY 2026-09-24, row-level with salted hashes only (local only, never packaged)
-- kind: rows; shards: 64 (0000..0063); batch: 16; windows: 24 [2026-09-24 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=hour
-- params: {"scene": "LKUS_captcha"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:46

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, l.id, l.create_time, l.result AS final_result,
  JSON_UNQUOTE(JSON_EXTRACT(l.response_strategy_engine, '$.re.resultName')) AS engine_result,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.cid')) AS cid,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.captchaScene')) AS captcha_scene,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.eventName')) AS event_name,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.verifyCodeType')) AS verify_code_type,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.verifyCodeTypeName')) AS verify_code_type_name,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.reviewRepeat')) AS review_repeat,
  CASE WHEN JSON_EXTRACT(l.pa, '$.recaptchaV2Token') IS NULL THEN 'absent' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.recaptchaV2Token')) = '' THEN 'empty' ELSE 'present' END AS v2_token_state,
  CASE WHEN JSON_EXTRACT(l.pa, '$.recaptchaV3Token') IS NULL THEN 'absent' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.recaptchaV3Token')) = '' THEN 'empty' ELSE 'present' END AS v3_token_state,
  TRIM(LEADING '+' FROM l.country_code) AS cc,
  LEFT(SHA2(CONCAT('{salt}', NULLIF(l.sharding_key, '')), 256), 16) AS sk_h,
  LEFT(SHA2(CONCAT('{salt}', NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.fullPhoneNo')), '')), 256), 16) AS phone_h,
  LEFT(SHA2(CONCAT('{salt}', NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.uid')), '')), 256), 16) AS uid_h,
  LEFT(SHA2(CONCAT('{salt}', NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIp')), '')), 256), 16) AS ip_h
FROM (SELECT id, create_time, result, country_code, sharding_key, response_strategy_engine,
        CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l
