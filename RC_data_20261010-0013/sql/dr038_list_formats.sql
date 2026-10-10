-- name: dr038_list_formats
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-038: whitelist entry formats by type x tenant (pattern classes and counts only; contents never selected)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-10-10 02:20

SELECT /*+ MAX_EXECUTION_TIME(10000) */ 't_whitelist' AS list_table, type AS list_type, tenant,
  CASE WHEN content REGEXP '^[0-9]{1,3}(\\.[0-9]{1,3}){2}$' THEN 'a.b.c'
       WHEN content REGEXP '^[0-9]{1,3}(\\.[0-9]{1,3}){2}\\.(\\*|0|x)$' THEN 'a.b.c.(*|0|x)'
       WHEN content REGEXP '^[0-9]{1,3}(\\.[0-9]{1,3}){3}$' THEN 'a.b.c.d'
       WHEN content REGEXP '^\\+?[0-9]{6,}$' THEN 'digits'
       ELSE 'other' END AS content_format,
  COUNT(*) AS n_entries, MIN(create_time) AS first_created, MAX(create_time) AS last_created, MAX(modify_time) AS last_modified
FROM luckyus_iriskcontrolservice.t_whitelist
GROUP BY type, tenant, content_format
