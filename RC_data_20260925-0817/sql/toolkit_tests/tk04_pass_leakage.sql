-- name: toolkit_tests/tk04_pass_leakage
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: toolkit test: tk04 non-+1 PASS leakage, 7 NY days
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-18 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push", "home_ccs": "'1'"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 10:32

-- tk04_pass_leakage: PASS requests whose country code is NOT in the home list, profiled by country code, IP country,
-- phone country != IP country, cid, token state, app key, email key.
-- Params : {scene}; {home_ccs} = quoted list without '+', e.g. '1' or '1','86'; window.
-- Merge  : tk_merge.py tk04 <csv> -> one table per dimension (rows, share). Distinct phones add up across shards.
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc,
  t.cc, t.ip_country, t.phone_ne_ip_country, t.cid, t.token_state, t.app_key, t.email_key,
  COUNT(*) AS rows_pass, COUNT(DISTINCT t.sk) AS distinct_phones
FROM (SELECT TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc, l.sharding_key AS sk,
        JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')) AS ip_country,
        COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneCountry')), '') <> COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')), '') AS phone_ne_ip_country,
        JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.cid')) AS cid,
        CASE WHEN JSON_EXTRACT(l.pa, '$.recaptchaV3Token') IS NULL THEN 'absent'
             WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.recaptchaV3Token')) = '' THEN 'empty' ELSE 'present' END AS token_state,
        JSON_EXTRACT(l.pa, '$.app') IS NOT NULL AS app_key,
        JSON_EXTRACT(l.pa, '$.email') IS NOT NULL AS email_key
      FROM (SELECT country_code, sharding_key, CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa
            FROM luckyus_iriskcontrolservice.{tbl}
            WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}' AND result = 'PASS'
              AND TRIM(LEADING '+' FROM COALESCE(country_code, '')) NOT IN ({home_ccs})) l) t
GROUP BY t.cc, t.ip_country, t.phone_ne_ip_country, t.cid, t.token_state, t.app_key, t.email_key
