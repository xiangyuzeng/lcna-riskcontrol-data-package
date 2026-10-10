-- name: p0_reserved_words
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P0: MySQL reserved words (information_schema.KEYWORDS, RESERVED=1) for the alias guard
-- kind: agg; windows: 1
-- params: {}
-- run (NY): 2026-10-10 00:15

SELECT /*+ MAX_EXECUTION_TIME(5000) */ WORD AS word FROM information_schema.KEYWORDS WHERE RESERVED = 1 ORDER BY WORD
