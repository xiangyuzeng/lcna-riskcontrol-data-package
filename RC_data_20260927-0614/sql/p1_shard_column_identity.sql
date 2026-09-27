-- name: p1_shard_column_identity
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: risk-control schema metadata (p1_shard_column_identity)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:22

SELECT /*+ MAX_EXECUTION_TIME(10000) */ x.family, x.COLUMN_NAME, x.ORDINAL_POSITION, x.COLUMN_TYPE, x.IS_NULLABLE, x.n_tables, x.n_family
FROM (
  SELECT c.family, c.COLUMN_NAME, c.ORDINAL_POSITION, c.COLUMN_TYPE, c.IS_NULLABLE, COUNT(*) AS n_tables, f.n_family
  FROM (SELECT LEFT(TABLE_NAME, CHAR_LENGTH(TABLE_NAME) - 5) AS family, TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = 'luckyus_iriskcontrolservice' AND TABLE_NAME REGEXP '^t_(access_log|gateway_validate_log)_[0-9]{4}$') c
  JOIN (SELECT LEFT(TABLE_NAME, CHAR_LENGTH(TABLE_NAME) - 5) AS family, COUNT(*) AS n_family
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = 'luckyus_iriskcontrolservice' AND TABLE_NAME REGEXP '^t_(access_log|gateway_validate_log)_[0-9]{4}$'
        GROUP BY family) f ON f.family = c.family
  GROUP BY c.family, c.COLUMN_NAME, c.ORDINAL_POSITION, c.COLUMN_TYPE, c.IS_NULLABLE, f.n_family
) x
ORDER BY x.family, x.ORDINAL_POSITION
