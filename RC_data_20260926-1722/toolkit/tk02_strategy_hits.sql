-- tk02_strategy_hits: PV of ONE strategy, online or pre-online, by final result x country code ('group' rows), plus
-- EXACT distinct phones per window ('window' row; a phone can hit with different final results, so group-level
-- distinct counts must not be summed). Distinct phones add up across shards (DR-014), not across windows.
-- Params : {scene}; {strategy_id}; {hit_list} = hitStrategy (online) | hitPreOnlineStrategy (pre-online); window.
-- Merge  : tk_merge.py tk02 <csv> [--home-cc 1]
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{utc_start}' AS window_start_utc, x.*
FROM (
  SELECT 'group' AS level, l.result AS final_result, TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc,
         COUNT(*) AS pv, NULL AS uv_phones
  FROM luckyus_iriskcontrolservice.{tbl} l
  WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = '{scene}'
    AND JSON_CONTAINS(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.response_strategy_engine, '$.re.{hit_list}')) AS JSON), JSON_OBJECT('strategyId', '{strategy_id}'))
  GROUP BY l.result, cc
  UNION ALL
  SELECT 'window', NULL, NULL, COUNT(*), COUNT(DISTINCT l.sharding_key)
  FROM luckyus_iriskcontrolservice.{tbl} l
  WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = '{scene}'
    AND JSON_CONTAINS(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.response_strategy_engine, '$.re.{hit_list}')) AS JSON), JSON_OBJECT('strategyId', '{strategy_id}'))
) x
