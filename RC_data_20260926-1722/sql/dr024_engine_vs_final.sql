-- name: dr024_engine_vs_final
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-024 / DR-016: NY day x cid x app state x app-version class (numeric, split at 1.4.30) x SMS flag x engine resultName x final result, LKUS_push, NY 2026-08-25..09-24
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 31 [2026-08-25 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push", "min_version_num": "1004030"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:19

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, t.cid, t.app_state, t.version_class, t.sms,
  t.engine_result, t.final_result, COUNT(*) AS n, COUNT(DISTINCT t.sk) AS n_distinct_phones
FROM (SELECT l.sharding_key AS sk, l.result AS final_result,
        COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.response_strategy_engine, '$.re.resultName')), '<none>') AS engine_result,
        COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.cid')), '<none>') AS cid,
        CASE WHEN JSON_EXTRACT(l.pa, '$.app') IS NULL THEN 'absent' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.app')) = '' THEN 'empty' ELSE 'present' END AS app_state,
        CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.version')), '') NOT REGEXP '^[0-9]+\\.[0-9]+\\.[0-9]+' THEN 'no_version'
             WHEN CAST(SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.version')), '.', 1) AS UNSIGNED) * 1000000
                + CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.version')), '.', 2), '.', -1) AS UNSIGNED) * 1000
                + CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.version')), '.', 3), '.', -1) AS UNSIGNED) >= {min_version_num}
             THEN 'ge_min' ELSE 'lt_min' END AS version_class,
        CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') <> '' THEN 0 ELSE 1 END AS sms
      FROM (SELECT result, sharding_key, response_strategy_engine,
              CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa
            FROM luckyus_iriskcontrolservice.{tbl}
            WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l) t
GROUP BY t.cid, t.app_state, t.version_class, t.sms, t.engine_result, t.final_result
