-- name: p1_upush_indexes
-- server: aws-luckyus-upush-rw (via MCP server mcp-db-gateway)
-- purpose: P1: information_schema metadata of the upush verification-code tables (names/metadata only, no data)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:34

SELECT /*+ MAX_EXECUTION_TIME(10000) */ TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX, COLUMN_NAME, NON_UNIQUE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'luckyus_iupushsms'
  AND TABLE_NAME IN ('t_sent_verifycode_sms', 't_collect_verifycode', 't_verifycode_filled_statistics', 't_verifycode_filled_mobile_statistics')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
