-- name: p2_json_column_keys
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2: config JSON columns: type and top-level keys only
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:39

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.* FROM (
SELECT 't_rms_engine_third_feature' AS table_name, 'input_paras' AS column_name, JSON_TYPE(CAST(input_paras AS JSON)) AS json_type,
  CAST(COALESCE(JSON_KEYS(CAST(input_paras AS JSON)), JSON_KEYS(CAST(input_paras AS JSON), '$[0]')) AS CHAR) AS top_keys, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_third_feature WHERE JSON_VALID(input_paras) GROUP BY json_type, top_keys
UNION ALL
SELECT 't_rms_engine_list_feature' AS table_name, 'input_paras' AS column_name, JSON_TYPE(CAST(input_paras AS JSON)) AS json_type,
  CAST(COALESCE(JSON_KEYS(CAST(input_paras AS JSON)), JSON_KEYS(CAST(input_paras AS JSON), '$[0]')) AS CHAR) AS top_keys, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_list_feature WHERE JSON_VALID(input_paras) GROUP BY json_type, top_keys
UNION ALL
SELECT 't_rms_engine_tool' AS table_name, 'input_paras' AS column_name, JSON_TYPE(CAST(input_paras AS JSON)) AS json_type,
  CAST(COALESCE(JSON_KEYS(CAST(input_paras AS JSON)), JSON_KEYS(CAST(input_paras AS JSON), '$[0]')) AS CHAR) AS top_keys, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_tool WHERE JSON_VALID(input_paras) GROUP BY json_type, top_keys
UNION ALL
SELECT 't_rms_engine_tool' AS table_name, 'output_paras' AS column_name, JSON_TYPE(CAST(output_paras AS JSON)) AS json_type,
  CAST(COALESCE(JSON_KEYS(CAST(output_paras AS JSON)), JSON_KEYS(CAST(output_paras AS JSON), '$[0]')) AS CHAR) AS top_keys, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_tool WHERE JSON_VALID(output_paras) GROUP BY json_type, top_keys
UNION ALL
SELECT 't_rms_engine_block_metric' AS table_name, 'metricql' AS column_name, JSON_TYPE(CAST(metricql AS JSON)) AS json_type,
  CAST(COALESCE(JSON_KEYS(CAST(metricql AS JSON)), JSON_KEYS(CAST(metricql AS JSON), '$[0]')) AS CHAR) AS top_keys, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_block_metric WHERE JSON_VALID(metricql) GROUP BY json_type, top_keys
UNION ALL
SELECT 't_rms_engine_block_strategy' AS table_name, 'rules' AS column_name, JSON_TYPE(CAST(rules AS JSON)) AS json_type,
  CAST(COALESCE(JSON_KEYS(CAST(rules AS JSON)), JSON_KEYS(CAST(rules AS JSON), '$[0]')) AS CHAR) AS top_keys, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_block_strategy WHERE JSON_VALID(rules) GROUP BY json_type, top_keys
UNION ALL
SELECT 't_rms_engine_block_strategy' AS table_name, 'expression' AS column_name, JSON_TYPE(CAST(expression AS JSON)) AS json_type,
  CAST(COALESCE(JSON_KEYS(CAST(expression AS JSON)), JSON_KEYS(CAST(expression AS JSON), '$[0]')) AS CHAR) AS top_keys, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_block_strategy WHERE JSON_VALID(expression) GROUP BY json_type, top_keys
UNION ALL
SELECT 't_rms_engine_rule' AS table_name, 'condition_value' AS column_name, JSON_TYPE(CAST(condition_value AS JSON)) AS json_type,
  CAST(COALESCE(JSON_KEYS(CAST(condition_value AS JSON)), JSON_KEYS(CAST(condition_value AS JSON), '$[0]')) AS CHAR) AS top_keys, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_rule WHERE JSON_VALID(condition_value) GROUP BY json_type, top_keys
UNION ALL
SELECT 't_rms_engine_strategy' AS table_name, 'strategy_express' AS column_name, JSON_TYPE(CAST(strategy_express AS JSON)) AS json_type,
  CAST(COALESCE(JSON_KEYS(CAST(strategy_express AS JSON)), JSON_KEYS(CAST(strategy_express AS JSON), '$[0]')) AS CHAR) AS top_keys, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_strategy WHERE JSON_VALID(strategy_express) GROUP BY json_type, top_keys
) x ORDER BY x.table_name, x.column_name, x.n DESC
