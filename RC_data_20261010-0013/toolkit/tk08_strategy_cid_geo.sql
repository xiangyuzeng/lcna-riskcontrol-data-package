-- tk08_strategy_cid_geo (DR-023): hits of ONE strategy (online or pre-online) by cid x (phoneCountry != realIpCountry)
-- x final result ('group' rows: PV and distinct phones), plus 'cidgeo' rows with distinct phones per cid x geo_mismatch
-- over all final results. Distinct phones are exact within a row (sharding_key = full phone; one phone lives in one
-- shard, so per-shard values add up across shards) but must NOT be added across rows or across windows.
-- Basis: SMS rule (email empty or absent) when sms_only=1, else all rows of the scene.
-- Params : {scene}; {strategy_id}; {hit_list} = hitStrategy | hitPreOnlineStrategy; {sms_only} = 1 | 0; window (<= 1 NY day).
-- Merge  : sum pv / distinct_phones over shards per (window_start_utc, level, cid, geo_mismatch, final_result).
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc, x.*
FROM (
  SELECT 'group' AS level, t.cid, t.geo_mismatch, t.final_result, COUNT(*) AS pv, COUNT(DISTINCT t.sk) AS distinct_phones
  FROM (SELECT l.result AS final_result, l.sharding_key AS sk,
          COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.cid')), '<none>') AS cid,
          CASE WHEN CAST(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneCountry')), '') AS BINARY)
                  = CAST(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')), '') AS BINARY) THEN 0 ELSE 1 END AS geo_mismatch
        FROM (SELECT result, sharding_key, CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa,
                CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.{hit_list}')) AS JSON) AS h
              FROM luckyus_iriskcontrolservice.{tbl}
              WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l
        WHERE JSON_CONTAINS(l.h, JSON_OBJECT('strategyId', '{strategy_id}'))
          AND ({sms_only} = 0 OR COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') = '')) t
  GROUP BY t.cid, t.geo_mismatch, t.final_result
  UNION ALL
  SELECT 'cidgeo', t.cid, t.geo_mismatch, '*', COUNT(*), COUNT(DISTINCT t.sk)
  FROM (SELECT l.sharding_key AS sk,
          COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.cid')), '<none>') AS cid,
          CASE WHEN CAST(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneCountry')), '') AS BINARY)
                  = CAST(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')), '') AS BINARY) THEN 0 ELSE 1 END AS geo_mismatch
        FROM (SELECT sharding_key, CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa,
                CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.{hit_list}')) AS JSON) AS h
              FROM luckyus_iriskcontrolservice.{tbl}
              WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l
        WHERE JSON_CONTAINS(l.h, JSON_OBJECT('strategyId', '{strategy_id}'))
          AND ({sms_only} = 0 OR COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') = '')) t
  GROUP BY t.cid, t.geo_mismatch
) x
