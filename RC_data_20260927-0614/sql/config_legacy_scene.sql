-- name: config_legacy_scene
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P2: whole-table export of the rule-engine definition table (free text masked as whole cells; operator columns masked; secret-like columns dropped)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:35

-- export of luckyus_iriskcontrolservice.t_scene; dropped (secret-like): -; operator columns masked: ['create_emp', 'create_name', 'modify_emp', 'modify_name']
SELECT /*+ MAX_EXECUTION_TIME(10000) */
  `id`,
  `scene_type`,
  `async`,
  `open`,
  `online`,
  CASE WHEN `tenant` REGEXP '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`tenant`), '字符>') ELSE `tenant` END AS `tenant`,
  `deleted`,
  CASE WHEN `create_emp` IS NULL OR CAST(`create_emp` AS CHAR) = '' THEN `create_emp` ELSE '<已屏蔽:操作人>' END AS `create_emp`,
  CASE WHEN `create_name` IS NULL OR CAST(`create_name` AS CHAR) = '' THEN `create_name` ELSE '<已屏蔽:操作人>' END AS `create_name`,
  `create_time`,
  CASE WHEN `modify_emp` IS NULL OR CAST(`modify_emp` AS CHAR) = '' THEN `modify_emp` ELSE '<已屏蔽:操作人>' END AS `modify_emp`,
  CASE WHEN `modify_name` IS NULL OR CAST(`modify_name` AS CHAR) = '' THEN `modify_name` ELSE '<已屏蔽:操作人>' END AS `modify_name`,
  `modify_time`
FROM luckyus_iriskcontrolservice.t_scene
ORDER BY `id`
LIMIT 5000
