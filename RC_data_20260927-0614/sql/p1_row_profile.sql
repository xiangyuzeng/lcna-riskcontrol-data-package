-- name: p1_row_profile
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: JSON/column structure, all scenes, NY 2026-09-26 (keys and presence counts only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-26 04:00:00 .. 2026-09-27 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-27 06:23

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, scene_id, tenant, access_id, type,
  COUNT(*) AS n_rows,
  SUM(JSON_VALID(request_strategy_engine)) AS req_engine_json,
  SUM(JSON_VALID(response_strategy_engine)) AS resp_engine_json,
  SUM(JSON_VALID(response)) AS response_json,
  SUM(JSON_VALID(request)) AS request_json,
  SUM(request IS NOT NULL AND request <> '') AS request_nonempty,
  SUM(JSON_VALID(extend)) AS extend_json,
  SUM(extend IS NOT NULL AND extend <> '') AS extend_nonempty,
  SUM(JSON_TYPE(JSON_EXTRACT(request_strategy_engine, '$.para')) = 'STRING') AS para_is_string,
  SUM(JSON_TYPE(JSON_EXTRACT(response_strategy_engine, '$.re.featureDetail')) = 'ARRAY') AS fd_is_array,
  SUM(JSON_TYPE(JSON_EXTRACT(response_strategy_engine, '$.re.featureDetail')) = 'STRING') AS fd_is_string,
  SUM(JSON_TYPE(JSON_EXTRACT(response_strategy_engine, '$.re.hitStrategy')) = 'STRING') AS hit_is_string,
  SUM(JSON_TYPE(JSON_EXTRACT(response_strategy_engine, '$.re.ruleDetail')) = 'ARRAY') AS rd_is_array,
  SUM(country_code IS NULL OR country_code = '') AS cc_col_empty,
  SUM(phone IS NOT NULL AND phone <> '') AS phone_col_nonempty,
  SUM(email IS NOT NULL AND email <> '') AS email_col_nonempty,
  SUM(user_no IS NOT NULL AND user_no <> '') AS user_no_col_nonempty,
  SUM(ip IS NOT NULL AND ip <> '') AS ip_col_nonempty,
  SUM(ip_city IS NOT NULL AND ip_city <> '') AS ip_city_col_nonempty,
  SUM(ip_province IS NOT NULL AND ip_province <> '') AS ip_province_col_nonempty,
  SUM(country IS NOT NULL AND country <> '') AS country_col_nonempty,
  SUM(city IS NOT NULL AND city <> '') AS city_col_nonempty,
  SUM(did IS NOT NULL AND did <> '') AS did_col_nonempty,
  SUM(device_id IS NOT NULL AND device_id <> '') AS device_id_col_nonempty,
  SUM(tongdun_device_id IS NOT NULL AND tongdun_device_id <> '') AS tongdun_device_id_col_nonempty,
  SUM(sharding_key IS NOT NULL AND sharding_key <> '') AS sharding_key_nonempty
FROM luckyus_iriskcontrolservice.{tbl}
WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}'
GROUP BY scene_id, tenant, access_id, type
