-- name: toolkit_tests/tk03_extra_recall
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: toolkit test: tk03 extra recall of strategy_GbsajBR69can, NY 2026-09-19:2026-09-25
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-19 04:00:00 .. 2026-09-26 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push", "strategy_id": "strategy_GbsajBR69can"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:53

-- tk03_extra_recall: 额外召回 of one PRE-ONLINE strategy = its hits whose final result is PASS
-- (what it would additionally act on if put online), by country code.
-- Params : {scene}; {strategy_id}; window.
-- Merge  : tk_merge.py tk03 <csv> --home-cc 1 -> PV / distinct phones per window, split home vs other country codes.
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc,
  TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc, COUNT(*) AS extra_recall_pv, COUNT(DISTINCT l.sharding_key) AS extra_recall_phones
FROM (SELECT result, country_code, sharding_key, response_strategy_engine AS resp
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}' AND result = 'PASS') l
WHERE JSON_CONTAINS(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitPreOnlineStrategy')) AS JSON), JSON_OBJECT('strategyId', '{strategy_id}'))
GROUP BY cc
