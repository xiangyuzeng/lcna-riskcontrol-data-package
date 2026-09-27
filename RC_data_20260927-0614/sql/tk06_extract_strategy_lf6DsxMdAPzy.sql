-- name: tk06_extract_strategy_lf6DsxMdAPzy
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: toolkit re-test (P6 review): tk06 row-level extract with email_nonempty, strategy_lf6DsxMdAPzy / feature_lydpDiga6SB9, NY 2026-09-26 plus warm-up (local only)
-- kind: rows; shards: 64 (0000..0063); batch: 16; windows: 26 [2026-09-26 02:55:00 .. 2026-09-27 04:00:00) UTC, chunk=hour
-- params: {"scene": "LKUS_push", "feature_id": "feature_lydpDiga6SB9", "strategy_id": "strategy_lf6DsxMdAPzy"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-27 08:09

-- tk06_rule_recheck_extract: ROW-LEVEL extract for recheck_counter.py (run with --kind rows --local, 1-hour chunks;
-- output stays in _local_only/, identities are salted hashes that never leave the machine).
-- Per request: time, dimension keys (hashed), the engine's value/code for {feature_id}, and whether {strategy_id} hit
-- (online or pre-online), and email_nonempty (SMS rule of P3: 1 = email non-empty in the CAST $.para = not SMS).
-- The counter is recomputed over ALL rows (the engine counts every request of the scene); email_nonempty only splits
-- the reported hits. Params: {scene}, {feature_id}, {strategy_id}, {salt} (random per run), window.
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, l.id, l.create_time,
  TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc,
  LEFT(SHA2(CONCAT('{salt}', NULLIF(l.sharding_key, '')), 256), 16) AS phone_h,
  LEFT(SHA2(CONCAT('{salt}', NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIp')), '')), 256), 16) AS ip_h,
  LEFT(SHA2(CONCAT('{salt}', NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.uid')), '')), 256), 16) AS uid_h,
  LEFT(SHA2(CONCAT('{salt}', NULLIF(SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIp')), '.', 3), '')), 256), 16) AS ipc_h,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')) AS ip_country,
  (COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') <> '') AS email_nonempty,
  CASE WHEN JSON_EXTRACT(l.pa, '$.recaptchaV3Token') IS NULL THEN 'absent'
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.recaptchaV3Token')) = '' THEN 'empty' ELSE 'present' END AS token_state,
  (SELECT JSON_ARRAY(f.code, f.v) FROM JSON_TABLE(JSON_EXTRACT(l.resp, '$.re.featureDetail'), '$[*]'
      COLUMNS (fid VARCHAR(64) PATH '$.featureId', code VARCHAR(64) PATH '$.code', v VARCHAR(64) PATH '$.comments.apiResp')) f
    WHERE f.fid = '{feature_id}' LIMIT 1) AS feature_code_value,
  COALESCE(JSON_CONTAINS(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), JSON_OBJECT('strategyId', '{strategy_id}')), 0)
  + COALESCE(JSON_CONTAINS(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitPreOnlineStrategy')) AS JSON), JSON_OBJECT('strategyId', '{strategy_id}')), 0) AS strategy_hit
FROM (SELECT id, create_time, country_code, sharding_key, response_strategy_engine AS resp,
        CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l
