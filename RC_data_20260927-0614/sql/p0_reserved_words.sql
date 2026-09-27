-- name: p0_reserved_words
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0: p0_reserved_words
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-09-27 06:17

SELECT /*+ MAX_EXECUTION_TIME(5000) */ WORD AS word FROM information_schema.KEYWORDS WHERE RESERVED = 1 ORDER BY WORD
