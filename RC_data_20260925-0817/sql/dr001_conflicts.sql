-- name: dr001_conflicts
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-001: per request, online-hit composition (PASS/REJECT/REVIEW present, result of highest / lowest execPriority hit, result of bestStrategyId) x final result, per NY day 2026-08-25..2026-09-24
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 31 [2026-08-25 04:00:00 .. 2026-09-25 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-25 09:59

SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date,
  x.n_online, x.has_pass, x.has_reject, x.has_review, x.top_result, x.low_result, x.best_result,
  x.max_pass_prio, x.max_reject_prio, x.final_result, x.engine_result, COUNT(*) AS n
FROM (
  SELECT l.id, l.result AS final_result, JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.resultName')) AS engine_result,
    (SELECT COUNT(*) FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
        COLUMNS (sid VARCHAR(64) PATH '$.strategyId')) h) AS n_online,
    (SELECT MAX(h.rn = 'PASS') FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
        COLUMNS (rn VARCHAR(32) PATH '$.resultName')) h) AS has_pass,
    (SELECT MAX(h.rn = 'REJECT') FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
        COLUMNS (rn VARCHAR(32) PATH '$.resultName')) h) AS has_reject,
    (SELECT MAX(h.rn LIKE 'REVIEW%') FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
        COLUMNS (rn VARCHAR(32) PATH '$.resultName')) h) AS has_review,
    (SELECT h.rn FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
        COLUMNS (rn VARCHAR(32) PATH '$.resultName', ep INT PATH '$.execPriority')) h ORDER BY h.ep DESC, h.rn LIMIT 1) AS top_result,
    (SELECT h.rn FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
        COLUMNS (rn VARCHAR(32) PATH '$.resultName', ep INT PATH '$.execPriority')) h ORDER BY h.ep ASC, h.rn LIMIT 1) AS low_result,
    (SELECT h.rn FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
        COLUMNS (sid VARCHAR(64) PATH '$.strategyId', rn VARCHAR(32) PATH '$.resultName')) h
      WHERE h.sid = JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.bestStrategyId')) LIMIT 1) AS best_result,
    (SELECT MAX(CASE WHEN h.rn = 'PASS' THEN h.ep END) FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
        COLUMNS (rn VARCHAR(32) PATH '$.resultName', ep INT PATH '$.execPriority')) h) AS max_pass_prio,
    (SELECT MAX(CASE WHEN h.rn = 'REJECT' THEN h.ep END) FROM JSON_TABLE(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.resp, '$.re.hitStrategy')) AS JSON), '$[*]'
        COLUMNS (rn VARCHAR(32) PATH '$.resultName', ep INT PATH '$.execPriority')) h) AS max_reject_prio
  FROM (SELECT id, result, response_strategy_engine AS resp FROM luckyus_iriskcontrolservice.{tbl}
        WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l
) x
GROUP BY x.n_online, x.has_pass, x.has_reject, x.has_review, x.top_result, x.low_result, x.best_result,
  x.max_pass_prio, x.max_reject_prio, x.final_result, x.engine_result
