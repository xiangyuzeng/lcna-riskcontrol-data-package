-- name: dr031_tk11_bYXa
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-031 / tk11 test: requests in strategy_bYXaOJ4qXtW4's current country-code list by NY day x cc x IP class x hit state x final result, SMS basis (email empty or absent), NY 2026-10-02..10-09 (re-run after aligning the SMS rule with tk02)
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 8 [2026-10-02 04:00:00 .. 2026-10-10 04:00:00) UTC, chunk=day
-- params: {"scene": "LKUS_push", "strategy_id": "strategy_bYXaOJ4qXtW4", "target_ccs": "'7','60','92','213','220','223','233','251','254','255','258','264','265','375','380','386','504','855','856','992','998'", "us_values": "'美国'", "sms_only": "1"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-10-10 02:53

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
