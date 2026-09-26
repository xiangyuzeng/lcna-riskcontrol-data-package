-- tk09_engine_vs_final (DR-024 / DR-016): per NY day, cid x app state x app-version class x SMS flag x engine result
-- ($.re.resultName) x final result (`result` column = response.$.result): request count and distinct phones.
-- version_class compares the version NUMERICALLY (major*1000000 + minor*1000 + patch) against {min_version_num}
-- (e.g. 1.4.30 -> 1004030); as text, '1.4.9' > '1.4.30'. Distinct phones: exact within a row, never add across rows.
-- Params : {scene}; {min_version_num}; window (<= 1 NY day; use --ny-days).
-- Merge  : sum n / n_distinct_phones over shards per (ny_date, cid, app_state, version_class, sms, engine_result, final_result).
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
