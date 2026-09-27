-- name: p1_partitions
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P1: risk-control schema metadata (p1_partitions)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:22

SELECT /*+ MAX_EXECUTION_TIME(10000) */ TABLE_NAME, COUNT(*) AS n_partition_rows, SUM(PARTITION_NAME IS NOT NULL) AS n_named_partitions
FROM information_schema.PARTITIONS WHERE TABLE_SCHEMA = 'luckyus_iriskcontrolservice'
GROUP BY TABLE_NAME HAVING n_named_partitions > 0
