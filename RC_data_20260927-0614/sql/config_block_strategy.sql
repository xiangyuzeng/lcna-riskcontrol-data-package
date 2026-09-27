-- name: config_block_strategy
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2: whole-table export of the rule-engine definition table (free text masked as whole cells; operator columns masked; secret-like columns dropped)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:35

-- export of luckyus_iriskcontrolservice.t_rms_engine_block_strategy; dropped (secret-like): -; operator columns masked: ['create_user', 'update_user']
SELECT /*+ MAX_EXECUTION_TIME(10000) */
  `id`,
  CASE WHEN `block_strategy_id` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`block_strategy_id`), '字符>') ELSE `block_strategy_id` END AS `block_strategy_id`,
  CASE WHEN `strategy_period` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`strategy_period`), '字符>') ELSE `strategy_period` END AS `strategy_period`,
  CASE WHEN `rules` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`rules`), '字符>') ELSE `rules` END AS `rules`,
  CASE WHEN `expression` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`expression`), '字符>') ELSE `expression` END AS `expression`,
  `action`,
  `status`,
  `strategy_type`,
  CASE WHEN `union_id` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`union_id`), '字符>') ELSE `union_id` END AS `union_id`,
  CASE WHEN `create_user` IS NULL OR CAST(`create_user` AS CHAR) = '' THEN `create_user` ELSE '<已屏蔽:操作人>' END AS `create_user`,
  CASE WHEN `update_user` IS NULL OR CAST(`update_user` AS CHAR) = '' THEN `update_user` ELSE '<已屏蔽:操作人>' END AS `update_user`,
  `create_time`,
  `update_time`,
  CASE WHEN `remark` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`remark`), '字符>') ELSE `remark` END AS `remark`
FROM luckyus_iriskcontrolservice.t_rms_engine_block_strategy
ORDER BY `id`
LIMIT 5000
