-- name: p2_rule_match_types
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2: rules with PII-like values: condition type / feature only (no values)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-26 17:48

SELECT /*+ MAX_EXECUTION_TIME(10000) */ r.condition_type, r.feature_type, r.feature_id,
  r.condition_value REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}' AS has_ipv4_full, r.condition_value REGEXP '[0-9]{7,}' AS has_digits7,
  r.rule_name REGEXP '[0-9]{7,}' AS name_has_digits7, r.rule_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}' AS name_has_ipv4,
  CHAR_LENGTH(r.condition_value) AS value_len, r.status, COUNT(*) AS n
FROM luckyus_iriskcontrolservice.t_rms_engine_rule r
WHERE r.condition_value REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[0-9]{7,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}' OR r.rule_name REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[0-9]{7,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}'
GROUP BY r.condition_type, r.feature_type, r.feature_id, has_ipv4_full, has_digits7, name_has_digits7, name_has_ipv4, value_len, r.status
