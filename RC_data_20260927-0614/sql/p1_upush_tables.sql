-- name: p1_upush_tables
-- server: aws-luckyus-upush-rw (via MCP server mcp-db-gateway)
-- purpose: P1: information_schema metadata of the upush verification-code tables (names/metadata only, no data)
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:34

SELECT /*+ MAX_EXECUTION_TIME(10000) */ TABLE_SCHEMA, TABLE_NAME, TABLE_ROWS, CREATE_TIME, UPDATE_TIME, TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'luckyus_iupushsms'
  AND TABLE_NAME REGEXP 'verif|code|fill|black|white|msg_rule|sms_sent_0000|sms_receipt_0000|sms_deliver_record'
ORDER BY TABLE_NAME
