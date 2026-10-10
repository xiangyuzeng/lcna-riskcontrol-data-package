-- tk11_bypass_watch (2026-10-10, new): traffic in a strategy's target country codes, per NY day x cc x IP class x whether the
-- strategy hit (online / pre-online / not at all) x final result. "Bypass" = target-code requests the strategy did not hit,
-- split by IP class so the reason is visible (e.g. IP in the US, IP country = phone country). Counts only.
-- ip_class: unknown (no IP country) / us (IP country in {us_values}) / eq_phone (IP country = phone country) / other.
-- SMS rule as tk02 / tk03 / tk08: {sms_only} = 1 keeps rows whose $.para.email is empty or absent.
-- Params : {scene}; {strategy_id}; {target_ccs} quoted list without '+' (read it from the strategy's countryCode rule in the
--          config export, never typed by hand); {us_values} quoted list (e.g. '美国'); {sms_only} = 1 | 0; window <= 1 NY day.
-- Merge  : sum n over shards per (ny_date, cc, ip_class, s_hit, final_result).
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, t.cc, t.ip_class, t.s_hit, t.final_result, COUNT(*) AS n
FROM (SELECT TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc, l.result AS final_result,
        CASE WHEN NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')), 'null'), '') IS NULL THEN 'unknown'
             WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')) IN ({us_values}) THEN 'us'
             WHEN CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')) AS BINARY) = CAST(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneCountry')), '') AS BINARY) THEN 'eq_phone'
             ELSE 'other' END AS ip_class,
        CASE WHEN JSON_CONTAINS(l.h_on, JSON_OBJECT('strategyId', '{strategy_id}')) THEN 'online'
             WHEN JSON_CONTAINS(l.h_pre, JSON_OBJECT('strategyId', '{strategy_id}')) THEN 'preonline' ELSE 'none' END AS s_hit
      FROM (SELECT result, country_code,
              CASE WHEN JSON_VALID(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para'))) THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) END AS pa,
              CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitStrategy')) AS JSON) AS h_on,
              CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitPreOnlineStrategy')) AS JSON) AS h_pre
            FROM luckyus_iriskcontrolservice.{tbl}
            WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}'
              AND TRIM(LEADING '+' FROM COALESCE(country_code, '')) IN ({target_ccs})) l
      WHERE {sms_only} = 0 OR COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') = '') t
GROUP BY t.cc, t.ip_class, t.s_hit, t.final_result
