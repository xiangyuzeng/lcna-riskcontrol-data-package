-- name: dr003_long
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-003: per NY day, conditional counter vs unconditional sibling (same dimension/window/count): code counts, equality, cond>sibling (impossible if the filter works). a=n91JeGM6gD6i vs UOJYBEifd5Jn; b=dqBHKec09Wwa vs UOJYBEifd5Jn; c=e1Kmz7JqzsWc vs dtoJoDcUgCcr
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 36 [2026-08-20 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {"cond_a": "feature_n91JeGM6gD6i", "sib_a": "feature_UOJYBEifd5Jn", "cond_b": "feature_dqBHKec09Wwa", "cond_c": "feature_e1Kmz7JqzsWc", "sib_c": "feature_dtoJoDcUgCcr"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 09:48

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, COUNT(*) AS n_push_rows,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) IS NOT NULL) AS a_rows,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) = 'SUCCESS') AS a_success, SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) = 'COUNTER_FEATURE_CONDITION_MISS') AS a_condition_miss,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) = 'COUNTER_FEATURE_PARAMS_ERROR') AS a_params_error,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS') AS a_both_success,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[1]')) AS DECIMAL(14,2)) = CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2))) AS a_success_eq_sibling,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[1]')) AS DECIMAL(14,2)) > CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2))) AS a_success_gt_sibling,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2)) >= 5 AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[1]')) AS DECIMAL(14,2)) = CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2))) AS a_success_eq_sibling_sib5,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2)) >= 5) AS a_success_sib5,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_a}[1]')) AS DECIMAL(14,2)) < 0.5 * CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2))) AS a_success_lt_half_sibling,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) IS NOT NULL) AS b_rows,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) = 'SUCCESS') AS b_success, SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) = 'COUNTER_FEATURE_CONDITION_MISS') AS b_condition_miss,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) = 'COUNTER_FEATURE_PARAMS_ERROR') AS b_params_error,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS') AS b_both_success,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[1]')) AS DECIMAL(14,2)) = CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2))) AS b_success_eq_sibling,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[1]')) AS DECIMAL(14,2)) > CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2))) AS b_success_gt_sibling,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2)) >= 5 AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[1]')) AS DECIMAL(14,2)) = CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2))) AS b_success_eq_sibling_sib5,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2)) >= 5) AS b_success_sib5,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_b}[1]')) AS DECIMAL(14,2)) < 0.5 * CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_a}[1]')) AS DECIMAL(14,2))) AS b_success_lt_half_sibling,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) IS NOT NULL) AS c_rows,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) = 'SUCCESS') AS c_success, SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) = 'COUNTER_FEATURE_CONDITION_MISS') AS c_condition_miss,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) = 'COUNTER_FEATURE_PARAMS_ERROR') AS c_params_error,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[0]')) = 'SUCCESS') AS c_both_success,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[1]')) AS DECIMAL(14,2)) = CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[1]')) AS DECIMAL(14,2))) AS c_success_eq_sibling,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[1]')) AS DECIMAL(14,2)) > CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[1]')) AS DECIMAL(14,2))) AS c_success_gt_sibling,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[1]')) AS DECIMAL(14,2)) >= 5 AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[1]')) AS DECIMAL(14,2)) = CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[1]')) AS DECIMAL(14,2))) AS c_success_eq_sibling_sib5,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[1]')) AS DECIMAL(14,2)) >= 5) AS c_success_sib5,
  SUM(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[0]')) = 'SUCCESS' AND JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[0]')) = 'SUCCESS' AND CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{cond_c}[1]')) AS DECIMAL(14,2)) < 0.5 * CAST(JSON_UNQUOTE(JSON_EXTRACT(y.j, '$.{sib_c}[1]')) AS DECIMAL(14,2))) AS c_success_lt_half_sibling
FROM (SELECT l.id,
        (SELECT JSON_OBJECTAGG(f.fid, JSON_ARRAY(f.code, f.v))
           FROM JSON_TABLE(JSON_EXTRACT(l.resp, '$.re.featureDetail'), '$[*]'
             COLUMNS (fid VARCHAR(64) PATH '$.featureId', code VARCHAR(64) PATH '$.code', v VARCHAR(64) PATH '$.comments.apiResp')) f
          WHERE f.fid IN ('{cond_a}', '{sib_a}', '{cond_b}', '{cond_c}', '{sib_c}')) AS j
      FROM (SELECT id, response_strategy_engine AS resp FROM luckyus_iriskcontrolservice.{tbl}
            WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') l) y
