-- name: toolkit_tests/tk01_volume_users
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: toolkit test: tk01 for NY 2026-09-26 and the same hours on each of the previous 7 days
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 8 [2026-09-26 04:00:00 .. 2026-09-20 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push", "home_ccs": "'1'"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-27 07:12

-- tk01_volume_users: requests of one scene by country code x final result x non-empty email flag `email_key` ('group' rows), plus EXACT
-- distinct phones per window ('window' row): all requests, SMS requests (email empty or absent), SMS PASS, SMS PASS with a
-- home country code. Distinct phones must NOT be summed across groups (a phone can be PASS and REJECT the same day);
-- the 'window' row gives them directly. Across shards they add up (sharding_key = full phone, DR-014); across
-- windows they do not.
-- Params : {scene}; {home_ccs} quoted list without '+' (e.g. '1'); window {utc_start}/{utc_end} (<= 1 day per
--          statement; use --windows-file from same_hours.py for the same hours on each of the previous 7 days).
-- Merge  : tk_merge.py tk01 <csv> --home-cc 1 --watch-cc 86 [--sms-only]
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc, x.*
FROM (
  SELECT 'group' AS level, t.cc, t.final_result, t.email_key, COUNT(*) AS requests,
         NULL AS phones_all, NULL AS phones_sms, NULL AS phones_sms_pass, NULL AS phones_sms_pass_home
  FROM (SELECT TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc, l.result AS final_result,
          COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.request_strategy_engine, '$.para')) AS JSON), '$.email')), '') <> '' AS email_key
        FROM luckyus_iriskcontrolservice.{tbl} l
        WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = '{scene}') t
  GROUP BY t.cc, t.final_result, t.email_key
  UNION ALL
  SELECT 'window', NULL, NULL, NULL, COUNT(*), COUNT(DISTINCT w.sk),
         COUNT(DISTINCT CASE WHEN w.email_key = 0 THEN w.sk END),
         COUNT(DISTINCT CASE WHEN w.email_key = 0 AND w.final_result = 'PASS' THEN w.sk END),
         COUNT(DISTINCT CASE WHEN w.email_key = 0 AND w.final_result = 'PASS' AND w.cc IN ({home_ccs}) THEN w.sk END)
  FROM (SELECT TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc, l.result AS final_result, l.sharding_key AS sk,
          COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.request_strategy_engine, '$.para')) AS JSON), '$.email')), '') <> '' AS email_key
        FROM luckyus_iriskcontrolservice.{tbl} l
        WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = '{scene}') w
) x
