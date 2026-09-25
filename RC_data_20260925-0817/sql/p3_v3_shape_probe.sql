-- name: p3_v3_shape_probe
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: shape of reCAPTCHA feature apiResp (types, lengths, top-level keys; no values)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-24 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {"rc_ids": "'feature_MDSagDqKF5R8','feature_nm9NTGYLKhWV','feature_rgdTqV4sNtjl','feature_TLXI8MNiNglz','feature_MHv7nra5Z6T5','feature_P1s9xYQJsdt3'"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 09:20

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, f.fid, f.code, JSON_VALID(f.v) AS v_json,
  CASE WHEN JSON_VALID(f.v) THEN JSON_TYPE(CAST(f.v AS JSON)) END AS v_type,
  CASE WHEN f.v IS NULL THEN 'null' WHEN CHAR_LENGTH(f.v) = 0 THEN '0' WHEN CHAR_LENGTH(f.v) <= 40 THEN '1-40' WHEN CHAR_LENGTH(f.v) <= 400 THEN '41-400' ELSE '>400' END AS v_len,
  CASE WHEN JSON_VALID(f.v) AND JSON_TYPE(CAST(f.v AS JSON)) = 'OBJECT' THEN CAST(JSON_KEYS(CAST(f.v AS JSON)) AS CHAR) END AS v_keys,
  CASE WHEN JSON_VALID(f.v) AND JSON_TYPE(CAST(f.v AS JSON)) = 'OBJECT' THEN JSON_EXTRACT(CAST(f.v AS JSON), '$.riskAnalysis.score') IS NOT NULL END AS has_score,
  COUNT(*) AS n
FROM luckyus_iriskcontrolservice.{tbl} l,
  JSON_TABLE(JSON_EXTRACT(l.response_strategy_engine, '$.re.featureDetail'), '$[*]'
    COLUMNS (fid VARCHAR(64) PATH '$.featureId', code VARCHAR(64) PATH '$.code', v LONGTEXT PATH '$.comments.apiResp')) f
WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = 'LKUS_push'
  AND f.fid IN ({rc_ids})
GROUP BY f.fid, f.code, v_json, v_type, v_len, v_keys, has_score
