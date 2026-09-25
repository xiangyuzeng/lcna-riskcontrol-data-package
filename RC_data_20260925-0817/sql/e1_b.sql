-- name: e1_b
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: E1 base extract (row-level, local only): LKUS_push, NY 2026-09-21 .. 2026-09-24, 1-hour windows
-- kind: rows; shards: 64 (0000..0063); batch: 16; windows: 96 [2026-09-21 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=hour
-- params: {"scene": "LKUS_push", "rc_ids": "'feature_MDSagDqKF5R8','feature_nm9NTGYLKhWV','feature_rgdTqV4sNtjl','feature_TLXI8MNiNglz','feature_MHv7nra5Z6T5','feature_P1s9xYQJsdt3'", "counter_ids": "'feature_SdA1CjZvNCMG','feature_pf88qk27w76j','feature_UOJYBEifd5Jn','feature_7DbBgowc2mEl','feature_JaT2oyzVtD0q','feature_lydpDiga6SB9','feature_Wg4dZ6VJBuTb','feature_Lvv9VNfLx77I','feature_ehJw66bTpI9S','feature_TXI2LFeOiXOv','feature_VkmvkRfzCItZ','feature_ml40wvr0IT6c','feature_K4e9HlaYIV90','feature_jxn9kksHnXCH','feature_FanjDbA4S666','feature_vApWJ93xOLe3','feature_Fik6gvwY1tA6','feature_53Ck9TgChpTW','feature_r1bhlQnbfRHb','feature_TGPe0mjAPwR5','feature_YkpmaKaJhcdG','feature_nnsdzZLQKPZ7','feature_6qwgYPGGuJZ4','feature_hspErCH8fSCE','feature_IPwzfPamC8eW','feature_Ym70ZsfxQKSc','feature_3numYVlg0OTP','feature_WxHUxqIN0IuS','feature_n91JeGM6gD6i','feature_dqBHKec09Wwa','feature_KtSZtJ9w7f9r','feature_VRxqkmPaw4rH','feature_RBSh0DmyLjo0','feature_VItdlLjtEYnQ','feature_LiSmRthu9NgQ','feature_19R00ZGNXmDQ','feature_dtoJoDcUgCcr','feature_e1Kmz7JqzsWc','feature_9EHsNcVBo6IN','feature_AemrK847uPtt','feature_bvE9FL19wqag','feature_Gwh0jqPAdVNL','feature_OE4u7WlFb1BT'", "time_rule_ids": "'rule_2gkMKTdcAXl6','rule_MkkOxneZSBav','rule_O9w0ltImsqUN','rule_uUsfrsSC5uK1','rule_z6WO6Vs09gzT','rule_kM0EcVvhiAiD'"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 09:27

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, l.id, l.create_time, l.result AS final_result,
  JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.resultName')) AS engine_result,
  JSON_UNQUOTE(JSON_EXTRACT(l.response, '$.code')) AS response_code,
  CASE WHEN JSON_EXTRACT(l.response, '$.model') IS NOT NULL THEN 1 ELSE 0 END AS response_has_model,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.cid')) AS cid,
  CASE WHEN JSON_EXTRACT(l.pa, '$.app') IS NULL THEN '<absent>' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.app')) = '' THEN '<empty>' ELSE JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.app')) END AS app,
  CASE WHEN JSON_VALID(l.request) THEN JSON_UNQUOTE(JSON_EXTRACT(l.request, '$.cidOriginEnum')) END AS cid_origin,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.version')) AS version,
  l.country_code AS cc_raw,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneCountry')) AS phone_country, JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')) AS ip_country, JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpProvince')) AS ip_province,
  CASE WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIp')) REGEXP '^[0-9]{1,3}(\\.[0-9]{1,3}){3}$' THEN CONCAT(SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIp')), '.', 3), '.x')
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIp')) LIKE '%:%' THEN 'ipv6' WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIp')), '') = '' THEN '<empty>' ELSE 'other' END AS ip_c,
  CASE WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) IS NULL OR JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) = '' THEN '<empty>'
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE 'okhttp%' THEN 'okhttp' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE 'Dart%' THEN 'dart' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE '%CFNetwork%' THEN 'ios_cfnetwork'
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE 'luckin%' OR JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE 'Luckin%' OR JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE '%iusluckyclient%' THEN 'luckin_app'
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE 'Mozilla%' AND JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE '%iPhone%' THEN 'browser_iphone'
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE 'Mozilla%' AND JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE '%Android%' THEN 'browser_android'
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE 'Mozilla%' AND (JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE '%Windows%' OR JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE '%Macintosh%' OR JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE '%X11%') THEN 'browser_desktop'
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) LIKE 'Mozilla%' THEN 'browser_other'
       WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')) REGEXP '^(python|curl|Go-http|Java|axios|node|PostmanRuntime|Apache-HttpClient)' THEN 'scripted'
       ELSE 'other' END AS ua_family,
  CASE WHEN SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')), '/', 1) REGEXP '^[A-Za-z][A-Za-z0-9._-]{0,30}$' THEN SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userAgent')), '/', 1) ELSE 'other' END AS ua_product,
  CASE WHEN JSON_EXTRACT(l.pa, '$.recaptchaV3Token') IS NULL THEN 'absent' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.recaptchaV3Token')) = '' THEN 'empty' ELSE 'present' END AS token_state,
  JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.recaptchaV3Enabled')) AS recaptcha_enabled, JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.recaptchaV3Action')) AS recaptcha_action, JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.reviewRepeat')) AS review_repeat,
  CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') <> '' THEN 1 ELSE 0 END AS email_present,
  CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userNo')), '') <> '' THEN 1 ELSE 0 END AS userno_present,
  LEFT(SHA2(CONCAT('{salt}', NULLIF(l.sharding_key, '')), 256), 16) AS phone_h, LEFT(SHA2(CONCAT('{salt}', NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.uid')), '')), 256), 16) AS uid_h, LEFT(SHA2(CONCAT('{salt}', NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIp')), '')), 256), 16) AS ip_h, LEFT(SHA2(CONCAT('{salt}', NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userNo')), '')), 256), 16) AS userno_h,
  (SELECT JSON_ARRAYAGG(JSON_OBJECT('fid', f.fid, 'code', f.code,
            'score', JSON_EXTRACT(CASE WHEN JSON_VALID(f.v) AND JSON_TYPE(CAST(f.v AS JSON)) = 'OBJECT' THEN CAST(f.v AS JSON) END, '$.riskAnalysis.score'),
            'valid', JSON_EXTRACT(CASE WHEN JSON_VALID(f.v) AND JSON_TYPE(CAST(f.v AS JSON)) = 'OBJECT' THEN CAST(f.v AS JSON) END, '$.tokenProperties.valid'),
            'invalid_reason', JSON_UNQUOTE(JSON_EXTRACT(CASE WHEN JSON_VALID(f.v) AND JSON_TYPE(CAST(f.v AS JSON)) = 'OBJECT' THEN CAST(f.v AS JSON) END, '$.tokenProperties.invalidReason')),
            'action', JSON_UNQUOTE(JSON_EXTRACT(CASE WHEN JSON_VALID(f.v) AND JSON_TYPE(CAST(f.v AS JSON)) = 'OBJECT' THEN CAST(f.v AS JSON) END, '$.tokenProperties.action')),
            'reasons', JSON_EXTRACT(CASE WHEN JSON_VALID(f.v) AND JSON_TYPE(CAST(f.v AS JSON)) = 'OBJECT' THEN CAST(f.v AS JSON) END, '$.riskAnalysis.reasons')))
     FROM JSON_TABLE(JSON_EXTRACT(l.resp, '$.re.featureDetail'), '$[*]' COLUMNS (fid VARCHAR(64) PATH '$.featureId', code VARCHAR(64) PATH '$.code', v LONGTEXT PATH '$.comments.apiResp')) f
     WHERE f.fid IN ({rc_ids})) AS recaptcha_json,
  (SELECT JSON_ARRAYAGG(f.fid)
     FROM JSON_TABLE(JSON_EXTRACT(l.resp, '$.re.featureDetail'), '$[*]' COLUMNS (fid VARCHAR(64) PATH '$.featureId', v LONGTEXT PATH '$.comments.apiResp')) f
     WHERE JSON_VALID(f.v) AND JSON_TYPE(CAST(f.v AS JSON)) = 'OBJECT' AND JSON_EXTRACT(CAST(f.v AS JSON), '$.riskAnalysis.score') IS NOT NULL) AS score_shaped_fids,
  (SELECT JSON_OBJECTAGG(f.fid, JSON_ARRAY(f.code, f.v))
     FROM JSON_TABLE(JSON_EXTRACT(l.resp, '$.re.featureDetail'), '$[*]' COLUMNS (fid VARCHAR(64) PATH '$.featureId', code VARCHAR(64) PATH '$.code', v VARCHAR(64) PATH '$.comments.apiResp')) f
     WHERE f.fid IN ({counter_ids})) AS counters_json,
  (SELECT JSON_ARRAYAGG(CONCAT(h.sid, '|', COALESCE(h.rn, ''), '|', COALESCE(h.ep, '')))
     FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
       COLUMNS (sid VARCHAR(64) PATH '$.strategyId', rn VARCHAR(32) PATH '$.resultName', ep VARCHAR(16) PATH '$.execPriority')) h) AS hits_online,
  (SELECT JSON_ARRAYAGG(CONCAT(h.sid, '|', COALESCE(h.rn, ''), '|', COALESCE(h.ep, '')))
     FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitPreOnlineStrategy')) AS JSON), '$[*]'
       COLUMNS (sid VARCHAR(64) PATH '$.strategyId', rn VARCHAR(32) PATH '$.resultName', ep VARCHAR(16) PATH '$.execPriority')) h) AS hits_preonline,
  JSON_LENGTH(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitBreakStrategy')) AS JSON)) AS n_break_hits,
  JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.bestStrategyId')) AS best_strategy_id,
  JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.bestPreOnlineStrategyId')) AS best_pre_strategy_id,
  (SELECT JSON_OBJECTAGG(r.rid, r.res)
     FROM JSON_TABLE(JSON_EXTRACT(l.resp, '$.re.ruleDetail'), '$[*]' COLUMNS (rid VARCHAR(64) PATH '$.ruleId', res VARCHAR(16) PATH '$.result')) r
     WHERE r.rid IN ({time_rule_ids})) AS time_rules_json,
  JSON_LENGTH(JSON_EXTRACT(l.resp, '$.re.featureDetail')) AS n_features
FROM (SELECT id, create_time, result, response, request, country_code, sharding_key, response_strategy_engine AS resp,
        CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l
