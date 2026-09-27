-- name: p0_server_vars
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0: p0_server_vars
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:15

SELECT /*+ MAX_EXECUTION_TIME(5000) */ @@version AS version, @@version_comment AS version_comment,
  @@read_only AS read_only, @@innodb_read_only AS innodb_read_only, @@super_read_only AS super_read_only,
  @@transaction_read_only AS transaction_read_only, @@time_zone AS time_zone, @@system_time_zone AS system_time_zone,
  @@max_execution_time AS max_execution_time, @@group_concat_max_len AS group_concat_max_len,
  @@information_schema_stats_expiry AS is_stats_expiry, UTC_TIMESTAMP() AS utc_now, NOW() AS db_now
