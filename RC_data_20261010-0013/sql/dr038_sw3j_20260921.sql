-- name: dr038_sw3j_20260921
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: DR-038: strategy_sw3jC7bvFYEX hits on NY 2026-09-21 matched inside SQL against the LKUS whitelist (IP C segment / phone): yes-no counts only
-- kind: agg; shards: 64 (0000..0063); batch: 16; windows: 1 [2026-09-21 04:00:00 .. 2026-09-22 04:00:00) UTC, chunk=day
-- params: {"strategy_id": "strategy_sw3jC7bvFYEX", "ipc_type": "10006", "phone_type": "10001"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-10-10 02:20

-- DR-038: hits of one strategy in one window, matched inside this statement against the LKUS whitelist (IP C segment type {ipc_type},
-- phone type {phone_type}); only yes/no counts leave the database. "asof" = only list entries created before the request.
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, t.hit_list, t.sms, t.final_result, t.ipc_format,
  t.ipc_in_whitelist_now, t.ipc_in_whitelist_asof, t.phone_in_whitelist_now, COUNT(*) AS hits, COUNT(DISTINCT t.sk) AS distinct_phones
FROM (SELECT l.result AS final_result, l.sharding_key AS sk,
        CASE WHEN JSON_CONTAINS(l.h_on, JSON_OBJECT('strategyId', '{strategy_id}')) THEN 'online' ELSE 'preonline' END AS hit_list,
        CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') NOT IN ('', 'null') THEN 0 ELSE 1 END AS sms,
        CASE WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpc')) REGEXP '^[0-9]{1,3}(\\.[0-9]{1,3}){2}$' THEN 'a.b.c'
             WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpc')) REGEXP '^[0-9]{1,3}(\\.[0-9]{1,3}){3}$' THEN 'a.b.c.d'
             WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpc')), '') IN ('', 'null') THEN 'empty' ELSE 'other' END AS ipc_format,
        EXISTS (SELECT 1 FROM luckyus_iriskcontrolservice.t_whitelist w WHERE w.tenant = 'LKUS' AND w.type = {ipc_type}
                  AND SUBSTRING_INDEX(w.content, '.', 3) = SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpc')), '.', 3)) AS ipc_in_whitelist_now,
        EXISTS (SELECT 1 FROM luckyus_iriskcontrolservice.t_whitelist w WHERE w.tenant = 'LKUS' AND w.type = {ipc_type} AND w.create_time <= l.ct
                  AND SUBSTRING_INDEX(w.content, '.', 3) = SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpc')), '.', 3)) AS ipc_in_whitelist_asof,
        EXISTS (SELECT 1 FROM luckyus_iriskcontrolservice.t_whitelist w WHERE w.tenant = 'LKUS' AND w.type = {phone_type}
                  AND TRIM(LEADING '+' FROM w.content) IN (TRIM(LEADING '+' FROM l.sharding_key), JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo')))) AS phone_in_whitelist_now
      FROM (SELECT create_time AS ct, result, sharding_key,
              CASE WHEN JSON_VALID(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para'))) THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) END AS pa,
              CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitStrategy')) AS JSON) AS h_on,
              CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitPreOnlineStrategy')) AS JSON) AS h_pre
            FROM luckyus_iriskcontrolservice.{tbl}
            WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') l
      WHERE JSON_CONTAINS(l.h_on, JSON_OBJECT('strategyId', '{strategy_id}')) OR JSON_CONTAINS(l.h_pre, JSON_OBJECT('strategyId', '{strategy_id}'))) t
GROUP BY t.hit_list, t.sms, t.final_result, t.ipc_format, t.ipc_in_whitelist_now, t.ipc_in_whitelist_asof, t.phone_in_whitelist_now
