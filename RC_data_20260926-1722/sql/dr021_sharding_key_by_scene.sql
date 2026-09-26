-- name: dr021_sharding_key_by_scene
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-021: per scene, how often sharding_key equals each candidate identity key (binary comparison counts only), NY 2026-09-19
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-19 04:00:00 .. 2026-09-20 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:39

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, l.scene_id, COUNT(*) AS n,
  SUM(COALESCE(l.sharding_key, '') = '') AS sk_empty,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(CONCAT(l.country_code, l.phone) AS BINARY)) AS sk_eq_cc_col_phone_col,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(CONCAT(TRIM(LEADING '+' FROM l.country_code), l.phone) AS BINARY)) AS sk_eq_bare_cc_phone_col,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(l.phone AS BINARY)) AS sk_eq_phone_col,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(l.user_no AS BINARY)) AS sk_eq_user_no_col,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(CONCAT(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.countryCode')), JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo'))) AS BINARY)) AS sk_eq_para_cc_phone,
  SUM(JSON_EXTRACT(l.pa, '$.fullPhoneNo') IS NOT NULL) AS has_fullPhoneNo,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.fullPhoneNo')) AS BINARY)) AS sk_eq_fullPhoneNo,
  SUM(JSON_EXTRACT(l.pa, '$.phoneNo') IS NOT NULL) AS has_phoneNo,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo')) AS BINARY)) AS sk_eq_phoneNo,
  SUM(JSON_EXTRACT(l.pa, '$.uid') IS NOT NULL) AS has_uid,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.uid')) AS BINARY)) AS sk_eq_uid,
  SUM(JSON_EXTRACT(l.pa, '$.userNo') IS NOT NULL) AS has_userNo,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.userNo')) AS BINARY)) AS sk_eq_userNo,
  SUM(JSON_EXTRACT(l.pa, '$.realIp') IS NOT NULL) AS has_realIp,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIp')) AS BINARY)) AS sk_eq_realIp,
  SUM(JSON_EXTRACT(l.pa, '$.orderNo') IS NOT NULL) AS has_orderNo,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.orderNo')) AS BINARY)) AS sk_eq_orderNo,
  SUM(JSON_EXTRACT(l.pa, '$.phoneNoEncryption') IS NOT NULL) AS has_phoneNoEncryption,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNoEncryption')) AS BINARY)) AS sk_eq_phoneNoEncryption,
  SUM(JSON_EXTRACT(l.pa, '$.maskPhoneNo') IS NOT NULL) AS has_maskPhoneNo,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.maskPhoneNo')) AS BINARY)) AS sk_eq_maskPhoneNo,
  SUM(JSON_EXTRACT(l.pa, '$.shopId') IS NOT NULL) AS has_shopId,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.shopId')) AS BINARY)) AS sk_eq_shopId,
  SUM(JSON_EXTRACT(l.pa, '$.sceneId') IS NOT NULL) AS has_sceneId,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.sceneId')) AS BINARY)) AS sk_eq_sceneId,
  SUM(JSON_EXTRACT(l.pa, '$.tenant') IS NOT NULL) AS has_tenant,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.tenant')) AS BINARY)) AS sk_eq_tenant,
  SUM(JSON_EXTRACT(l.pa, '$.shumeiDevId') IS NOT NULL) AS has_shumeiDevId,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.shumeiDevId')) AS BINARY)) AS sk_eq_shumeiDevId,
  SUM(JSON_EXTRACT(l.pa, '$.tongdunBlackBox') IS NOT NULL) AS has_tongdunBlackBox,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.tongdunBlackBox')) AS BINARY)) AS sk_eq_tongdunBlackBox,
  SUM(JSON_EXTRACT(l.pa, '$.shumengDevId') IS NOT NULL) AS has_shumengDevId,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.shumengDevId')) AS BINARY)) AS sk_eq_shumengDevId,
  SUM(JSON_EXTRACT(l.pa, '$.invitationCode') IS NOT NULL) AS has_invitationCode,
  SUM(CAST(l.sharding_key AS BINARY) = CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.invitationCode')) AS BINARY)) AS sk_eq_invitationCode,
  SUM(l.sharding_key REGEXP '^[+]') AS sk_starts_plus,
  SUM(l.sharding_key REGEXP '^[0-9]+$') AS sk_all_digits,
  MIN(CHAR_LENGTH(l.sharding_key)) AS sk_len_min, MAX(CHAR_LENGTH(l.sharding_key)) AS sk_len_max
FROM (SELECT scene_id, sharding_key, country_code, phone, user_no,
        CASE WHEN JSON_VALID(request_strategy_engine) AND JSON_VALID(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para'))) THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) END AS pa
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}') l
GROUP BY l.scene_id
