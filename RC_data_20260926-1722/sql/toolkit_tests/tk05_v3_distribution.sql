-- name: toolkit_tests/tk05_v3_distribution
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: toolkit test: tk05 reCAPTCHA score distribution (score by shape), NY 2026-09-19:2026-09-25
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 7 [2026-09-19 04:00:00 .. 2026-09-26 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-09-26 18:55

-- tk05_v3_distribution: reCAPTCHA score distribution by country code x cid x final result.
-- The score is taken by SHAPE: any featureDetail element whose apiResp is a JSON object with riskAnalysis.score
-- (which featureId carries it changed several times, DR-005). 'missing' = no such element.
-- Params : {scene}; window.   Merge: tk_merge.py tk05 <csv> --cuts 0.3,0.8 --home-cc 1 --watch-cc 86
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc,
  t.cc, t.cid, t.final_result, t.email_key, COALESCE(CAST(ROUND(t.score, 1) AS CHAR), 'missing') AS score_1dp, COUNT(*) AS n
FROM (SELECT TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc, l.result AS final_result,
        JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.req, '$.para')) AS JSON), '$.cid')) AS cid,
        COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.req, '$.para')) AS JSON), '$.email')), '') <> '' AS email_key,
        (SELECT MAX(CAST(JSON_EXTRACT(CAST(f.v AS JSON), '$.riskAnalysis.score') AS DECIMAL(4, 3)))
           FROM JSON_TABLE(JSON_EXTRACT(l.resp, '$.re.featureDetail'), '$[*]' COLUMNS (v LONGTEXT PATH '$.comments.apiResp')) f
          WHERE JSON_VALID(f.v) AND JSON_TYPE(CAST(f.v AS JSON)) = 'OBJECT') AS score
      FROM (SELECT result, country_code, request_strategy_engine AS req, response_strategy_engine AS resp
            FROM luckyus_iriskcontrolservice.{tbl}
            WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l) t
GROUP BY t.cc, t.cid, t.final_result, t.email_key, score_1dp
