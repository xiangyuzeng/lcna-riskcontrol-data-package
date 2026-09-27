-- name: config_templist_strategy
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2: whole-table export of the rule-engine definition table (free text masked as whole cells; operator columns masked; secret-like columns dropped)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:38

-- export of luckyus_iriskcontrolservice.t_rms_engine_templist_strategy; dropped (secret-like): ['write_key']; operator columns masked: ['operator']
SELECT /*+ MAX_EXECUTION_TIME(10000) */
  `id`,
  `list_index`,
  CASE WHEN `strategy_id` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`strategy_id`), '字符>') ELSE `strategy_id` END AS `strategy_id`,
  CASE WHEN `access_id` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`access_id`), '字符>') ELSE `access_id` END AS `access_id`,
  CASE WHEN `scene_id` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`scene_id`), '字符>') ELSE `scene_id` END AS `scene_id`,
  CASE WHEN `remarks` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`remarks`), '字符>') ELSE `remarks` END AS `remarks`,
  CASE WHEN `operator` IS NULL OR CAST(`operator` AS CHAR) = '' THEN `operator` ELSE '<已屏蔽:操作人>' END AS `operator`,
  `update_time`,
  `create_time`
FROM luckyus_iriskcontrolservice.t_rms_engine_templist_strategy
ORDER BY `id`
LIMIT 5000
