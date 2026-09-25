-- name: p1_dr007_upush_columns
-- server: aws-luckyus-upush-rw (via MCP server mcp-db-gateway)
-- purpose: DR-007 (strict scope): information_schema metadata of the SMS verification-code tables; no data read
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-25 08:56

SELECT /*+ MAX_EXECUTION_TIME(10000) */ c.TABLE_NAME, c.ORDINAL_POSITION, c.COLUMN_NAME, c.COLUMN_TYPE, c.IS_NULLABLE, c.COLUMN_KEY, c.COLUMN_COMMENT
FROM information_schema.COLUMNS c
WHERE c.TABLE_SCHEMA = 'luckyus_iupushsms'
  AND c.TABLE_NAME IN ('t_sent_verifycode_sms', 't_collect_verifycode', 't_verifycode_filled_statistics',
                       't_verifycode_filled_mobile_statistics', 't_msg_rule', 'sms_black_list', 'sms_white_list')
ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
