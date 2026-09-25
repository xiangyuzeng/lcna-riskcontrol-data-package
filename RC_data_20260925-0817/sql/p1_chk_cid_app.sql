-- name: p1_chk_cid_app
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: LKUS_push 7 NY days: field consistency / cid x app / country pairs (aggregates only)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-18 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 08:39

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, t.cid, t.app, t.cid_origin, t.result_col, COUNT(*) AS n
FROM (SELECT JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.cid')) AS cid,
        CASE WHEN JSON_EXTRACT(l.pa, '$.app') IS NULL THEN '<absent>' WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.app')) = '' THEN '<empty>' ELSE JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.app')) END AS app,
        CASE WHEN JSON_VALID(l.request) THEN JSON_UNQUOTE(JSON_EXTRACT(l.request, '$.cidOriginEnum')) END AS cid_origin,
        l.result AS result_col
FROM (SELECT id, result, response, country_code, phone, user_no, sharding_key, request,
             CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa,
             JSON_EXTRACT(response_strategy_engine, '$.re') AS re
      FROM luckyus_iriskcontrolservice.{tbl}
      WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') l) t
GROUP BY t.cid, t.app, t.cid_origin, t.result_col
