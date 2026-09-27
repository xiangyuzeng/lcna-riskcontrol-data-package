-- name: toolkit_tests/tk03_extra_recall_sms
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: toolkit re-test (P6 review): tk03 extra recall of strategy_GbsajBR69can (pass_class=1), sms_only=1, NY 2026-09-20:2026-09-26
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-20 04:00:00 .. 2026-09-27 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push", "strategy_id": "strategy_GbsajBR69can", "pass_class": "1", "sms_only": "1"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-27 08:08

-- tk03_extra_recall: 额外召回 of one PRE-ONLINE strategy = the hits whose outcome it would change if put online, by
-- country code. Non-PASS strategies (REJECT / REVIEW ...): hits whose final result is PASS ({pass_class}=0).
-- PASS-class strategies: hits whose final result is NOT already PASS ({pass_class}=1) — counting all their hits, or
-- their PASS hits, would overstate what they change (2026-09-26 review: strategy_GbsajBR69can).
-- Params : {scene}; {strategy_id}; {pass_class} = 0 | 1 (1 when the strategy's disposition is PASS);
--          {sms_only} = 1 -> SMS rule of P3 (email empty or absent in the CAST $.para), 0 -> all rows of the scene; window.
-- Merge  : tk_merge.py tk03 <csv> --home-cc 1 -> PV / distinct phones per window, split home vs other country codes.
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc,
  TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc, COUNT(*) AS extra_recall_pv, COUNT(DISTINCT l.sharding_key) AS extra_recall_phones
FROM (SELECT result, country_code, sharding_key, response_strategy_engine AS resp, request_strategy_engine AS req
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}'
        AND (({pass_class} = 0 AND result = 'PASS') OR ({pass_class} = 1 AND result <> 'PASS'))) l
WHERE JSON_CONTAINS(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitPreOnlineStrategy')) AS JSON), JSON_OBJECT('strategyId', '{strategy_id}'))
  AND ({sms_only} = 0 OR COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.req, '$.para')) AS JSON), '$.email')), '') = '')
GROUP BY cc
