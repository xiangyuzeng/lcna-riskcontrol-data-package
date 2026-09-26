-- name: p2_text_column_scan
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2: config free-text columns: how many values look like IP/email/long digits/URL/host:port (counts only)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-26 17:48

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.* FROM (
SELECT 't_rms_engine_access' AS table_name, 'access_name' AS column_name, COUNT(*) AS n_rows, SUM(access_name IS NOT NULL AND access_name <> '') AS n_nonempty,
  SUM(access_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(access_name)) AS n_json, MAX(CHAR_LENGTH(access_name)) AS max_len,
  COUNT(DISTINCT access_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_access
UNION ALL
SELECT 't_rms_engine_access' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_access
UNION ALL
SELECT 't_rms_engine_access' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_access
UNION ALL
SELECT 't_rms_engine_scene' AS table_name, 'scene_name' AS column_name, COUNT(*) AS n_rows, SUM(scene_name IS NOT NULL AND scene_name <> '') AS n_nonempty,
  SUM(scene_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(scene_name)) AS n_json, MAX(CHAR_LENGTH(scene_name)) AS max_len,
  COUNT(DISTINCT scene_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_scene
UNION ALL
SELECT 't_rms_engine_scene' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_scene
UNION ALL
SELECT 't_rms_engine_scene' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_scene
UNION ALL
SELECT 't_rms_engine_para' AS table_name, 'para_name' AS column_name, COUNT(*) AS n_rows, SUM(para_name IS NOT NULL AND para_name <> '') AS n_nonempty,
  SUM(para_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(para_name)) AS n_json, MAX(CHAR_LENGTH(para_name)) AS max_len,
  COUNT(DISTINCT para_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_para
UNION ALL
SELECT 't_rms_engine_para' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_para
UNION ALL
SELECT 't_rms_engine_para' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_para
UNION ALL
SELECT 't_rms_engine_resultcode' AS table_name, 'result_name' AS column_name, COUNT(*) AS n_rows, SUM(result_name IS NOT NULL AND result_name <> '') AS n_nonempty,
  SUM(result_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(result_name)) AS n_json, MAX(CHAR_LENGTH(result_name)) AS max_len,
  COUNT(DISTINCT result_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_resultcode
UNION ALL
SELECT 't_rms_engine_resultcode' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_resultcode
UNION ALL
SELECT 't_rms_engine_resultcode' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_resultcode
UNION ALL
SELECT 't_rms_engine_rule' AS table_name, 'rule_name' AS column_name, COUNT(*) AS n_rows, SUM(rule_name IS NOT NULL AND rule_name <> '') AS n_nonempty,
  SUM(rule_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(rule_name)) AS n_json, MAX(CHAR_LENGTH(rule_name)) AS max_len,
  COUNT(DISTINCT rule_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_rule
UNION ALL
SELECT 't_rms_engine_rule' AS table_name, 'condition_value' AS column_name, COUNT(*) AS n_rows, SUM(condition_value IS NOT NULL AND condition_value <> '') AS n_nonempty,
  SUM(condition_value REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(condition_value)) AS n_json, MAX(CHAR_LENGTH(condition_value)) AS max_len,
  COUNT(DISTINCT condition_value) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_rule
UNION ALL
SELECT 't_rms_engine_rule' AS table_name, 'rule_express' AS column_name, COUNT(*) AS n_rows, SUM(rule_express IS NOT NULL AND rule_express <> '') AS n_nonempty,
  SUM(rule_express REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(rule_express)) AS n_json, MAX(CHAR_LENGTH(rule_express)) AS max_len,
  COUNT(DISTINCT rule_express) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_rule
UNION ALL
SELECT 't_rms_engine_rule' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_rule
UNION ALL
SELECT 't_rms_engine_rule' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_rule
UNION ALL
SELECT 't_rms_engine_strategy' AS table_name, 'strategy_name' AS column_name, COUNT(*) AS n_rows, SUM(strategy_name IS NOT NULL AND strategy_name <> '') AS n_nonempty,
  SUM(strategy_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(strategy_name)) AS n_json, MAX(CHAR_LENGTH(strategy_name)) AS max_len,
  COUNT(DISTINCT strategy_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_strategy
UNION ALL
SELECT 't_rms_engine_strategy' AS table_name, 'strategy_express' AS column_name, COUNT(*) AS n_rows, SUM(strategy_express IS NOT NULL AND strategy_express <> '') AS n_nonempty,
  SUM(strategy_express REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(strategy_express)) AS n_json, MAX(CHAR_LENGTH(strategy_express)) AS max_len,
  COUNT(DISTINCT strategy_express) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_strategy
UNION ALL
SELECT 't_rms_engine_strategy' AS table_name, 'description' AS column_name, COUNT(*) AS n_rows, SUM(description IS NOT NULL AND description <> '') AS n_nonempty,
  SUM(description REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(description)) AS n_json, MAX(CHAR_LENGTH(description)) AS max_len,
  COUNT(DISTINCT description) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_strategy
UNION ALL
SELECT 't_rms_engine_strategy' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_strategy
UNION ALL
SELECT 't_rms_engine_strategy' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_strategy
UNION ALL
SELECT 't_rms_engine_strategy_relation' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_strategy_relation
UNION ALL
SELECT 't_rms_engine_strategy_relation' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_strategy_relation
UNION ALL
SELECT 't_rms_engine_list_feature' AS table_name, 'feature_name' AS column_name, COUNT(*) AS n_rows, SUM(feature_name IS NOT NULL AND feature_name <> '') AS n_nonempty,
  SUM(feature_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(feature_name)) AS n_json, MAX(CHAR_LENGTH(feature_name)) AS max_len,
  COUNT(DISTINCT feature_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_list_feature
UNION ALL
SELECT 't_rms_engine_list_feature' AS table_name, 'input_paras' AS column_name, COUNT(*) AS n_rows, SUM(input_paras IS NOT NULL AND input_paras <> '') AS n_nonempty,
  SUM(input_paras REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(input_paras)) AS n_json, MAX(CHAR_LENGTH(input_paras)) AS max_len,
  COUNT(DISTINCT input_paras) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_list_feature
UNION ALL
SELECT 't_rms_engine_list_feature' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_list_feature
UNION ALL
SELECT 't_rms_engine_list_feature' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_list_feature
UNION ALL
SELECT 't_rms_engine_third_feature' AS table_name, 'feature_name' AS column_name, COUNT(*) AS n_rows, SUM(feature_name IS NOT NULL AND feature_name <> '') AS n_nonempty,
  SUM(feature_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(feature_name)) AS n_json, MAX(CHAR_LENGTH(feature_name)) AS max_len,
  COUNT(DISTINCT feature_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_third_feature
UNION ALL
SELECT 't_rms_engine_third_feature' AS table_name, 'input_paras' AS column_name, COUNT(*) AS n_rows, SUM(input_paras IS NOT NULL AND input_paras <> '') AS n_nonempty,
  SUM(input_paras REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(input_paras)) AS n_json, MAX(CHAR_LENGTH(input_paras)) AS max_len,
  COUNT(DISTINCT input_paras) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_third_feature
UNION ALL
SELECT 't_rms_engine_third_feature' AS table_name, 'third_label' AS column_name, COUNT(*) AS n_rows, SUM(third_label IS NOT NULL AND third_label <> '') AS n_nonempty,
  SUM(third_label REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(third_label)) AS n_json, MAX(CHAR_LENGTH(third_label)) AS max_len,
  COUNT(DISTINCT third_label) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_third_feature
UNION ALL
SELECT 't_rms_engine_third_feature' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_third_feature
UNION ALL
SELECT 't_rms_engine_third_feature' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_third_feature
UNION ALL
SELECT 't_rms_engine_tool' AS table_name, 'tool_name' AS column_name, COUNT(*) AS n_rows, SUM(tool_name IS NOT NULL AND tool_name <> '') AS n_nonempty,
  SUM(tool_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(tool_name)) AS n_json, MAX(CHAR_LENGTH(tool_name)) AS max_len,
  COUNT(DISTINCT tool_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_tool
UNION ALL
SELECT 't_rms_engine_tool' AS table_name, 'tool_classpath' AS column_name, COUNT(*) AS n_rows, SUM(tool_classpath IS NOT NULL AND tool_classpath <> '') AS n_nonempty,
  SUM(tool_classpath REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(tool_classpath)) AS n_json, MAX(CHAR_LENGTH(tool_classpath)) AS max_len,
  COUNT(DISTINCT tool_classpath) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_tool
UNION ALL
SELECT 't_rms_engine_tool' AS table_name, 'input_paras' AS column_name, COUNT(*) AS n_rows, SUM(input_paras IS NOT NULL AND input_paras <> '') AS n_nonempty,
  SUM(input_paras REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(input_paras)) AS n_json, MAX(CHAR_LENGTH(input_paras)) AS max_len,
  COUNT(DISTINCT input_paras) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_tool
UNION ALL
SELECT 't_rms_engine_tool' AS table_name, 'output_paras' AS column_name, COUNT(*) AS n_rows, SUM(output_paras IS NOT NULL AND output_paras <> '') AS n_nonempty,
  SUM(output_paras REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(output_paras)) AS n_json, MAX(CHAR_LENGTH(output_paras)) AS max_len,
  COUNT(DISTINCT output_paras) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_tool
UNION ALL
SELECT 't_rms_engine_tool' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_tool
UNION ALL
SELECT 't_rms_engine_tool' AS table_name, 'operator' AS column_name, COUNT(*) AS n_rows, SUM(operator IS NOT NULL AND operator <> '') AS n_nonempty,
  SUM(operator REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(operator)) AS n_json, MAX(CHAR_LENGTH(operator)) AS max_len,
  COUNT(DISTINCT operator) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_tool
UNION ALL
SELECT 't_rms_engine_block_metric' AS table_name, 'metric_name' AS column_name, COUNT(*) AS n_rows, SUM(metric_name IS NOT NULL AND metric_name <> '') AS n_nonempty,
  SUM(metric_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(metric_name)) AS n_json, MAX(CHAR_LENGTH(metric_name)) AS max_len,
  COUNT(DISTINCT metric_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_block_metric
UNION ALL
SELECT 't_rms_engine_block_metric' AS table_name, 'metricql' AS column_name, COUNT(*) AS n_rows, SUM(metricql IS NOT NULL AND metricql <> '') AS n_nonempty,
  SUM(metricql REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(metricql)) AS n_json, MAX(CHAR_LENGTH(metricql)) AS max_len,
  COUNT(DISTINCT metricql) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_block_metric
UNION ALL
SELECT 't_rms_engine_block_metric' AS table_name, 'remarks' AS column_name, COUNT(*) AS n_rows, SUM(remarks IS NOT NULL AND remarks <> '') AS n_nonempty,
  SUM(remarks REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remarks)) AS n_json, MAX(CHAR_LENGTH(remarks)) AS max_len,
  COUNT(DISTINCT remarks) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_block_metric
UNION ALL
SELECT 't_rms_engine_block_metric' AS table_name, 'create_user' AS column_name, COUNT(*) AS n_rows, SUM(create_user IS NOT NULL AND create_user <> '') AS n_nonempty,
  SUM(create_user REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(create_user)) AS n_json, MAX(CHAR_LENGTH(create_user)) AS max_len,
  COUNT(DISTINCT create_user) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_block_metric
UNION ALL
SELECT 't_rms_engine_block_strategy' AS table_name, 'rules' AS column_name, COUNT(*) AS n_rows, SUM(rules IS NOT NULL AND rules <> '') AS n_nonempty,
  SUM(rules REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(rules)) AS n_json, MAX(CHAR_LENGTH(rules)) AS max_len,
  COUNT(DISTINCT rules) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_block_strategy
UNION ALL
SELECT 't_rms_engine_block_strategy' AS table_name, 'expression' AS column_name, COUNT(*) AS n_rows, SUM(expression IS NOT NULL AND expression <> '') AS n_nonempty,
  SUM(expression REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(expression)) AS n_json, MAX(CHAR_LENGTH(expression)) AS max_len,
  COUNT(DISTINCT expression) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_block_strategy
UNION ALL
SELECT 't_rms_engine_block_strategy' AS table_name, 'remark' AS column_name, COUNT(*) AS n_rows, SUM(remark IS NOT NULL AND remark <> '') AS n_nonempty,
  SUM(remark REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(remark)) AS n_json, MAX(CHAR_LENGTH(remark)) AS max_len,
  COUNT(DISTINCT remark) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_block_strategy
UNION ALL
SELECT 't_rms_engine_block_strategy' AS table_name, 'create_user' AS column_name, COUNT(*) AS n_rows, SUM(create_user IS NOT NULL AND create_user <> '') AS n_nonempty,
  SUM(create_user REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(create_user)) AS n_json, MAX(CHAR_LENGTH(create_user)) AS max_len,
  COUNT(DISTINCT create_user) AS n_distinct FROM luckyus_iriskcontrolservice.t_rms_engine_block_strategy
UNION ALL
SELECT 't_scene' AS table_name, 'create_name' AS column_name, COUNT(*) AS n_rows, SUM(create_name IS NOT NULL AND create_name <> '') AS n_nonempty,
  SUM(create_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(create_name)) AS n_json, MAX(CHAR_LENGTH(create_name)) AS max_len,
  COUNT(DISTINCT create_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_scene
UNION ALL
SELECT 't_scene' AS table_name, 'modify_name' AS column_name, COUNT(*) AS n_rows, SUM(modify_name IS NOT NULL AND modify_name <> '') AS n_nonempty,
  SUM(modify_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z0-9.-]+:[0-9]{2,5}') AS n_pii_or_secret_like, SUM(JSON_VALID(modify_name)) AS n_json, MAX(CHAR_LENGTH(modify_name)) AS max_len,
  COUNT(DISTINCT modify_name) AS n_distinct FROM luckyus_iriskcontrolservice.t_scene
) x
