-- name: p7_stab_l1
-- server: aws-luckyus-iriskcontrolservice-rw (via MCP server mcp-db-gateway)
-- purpose: P7 stability re-run of L1 for NY 2026-10-05
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 1 [2026-10-05 04:00:00 .. 2026-10-06 04:00:00) UTC, chunk=day
-- params: {"us_values": "'美国'", "nynj_values": "'New York','New Jersey'"}
-- merge: rows from every shard/window are concatenated; aggregate locally (sum counts)
-- run (NY): 2026-10-10 02:39

-- L1 long aggregate (counts only), one NY day per statement: 'h' rows = UTC hour x cc x final result x SMS flag x phone present x
-- IP geography class x IP province class x tenant flag; 'd' rows = NY day x cc x final result x SMS flag x tenant flag with exact
-- distinct phones over all results and over PASS (sharding_key; add up across shards and across cc for LKUS_push, never across days).
-- ip_geo: unknown (no IP country) / us (IP country in {us_values}) / eq_phone (IP country = phone country) / other.
-- prov_class: missing / nynj (province in {nynj_values}) / other. Country and province values come from the data (p1_province_classes).
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, x.*
FROM (
  SELECT 'h' AS lvl, t.utc_hour, t.cc, t.final_result, t.sms, t.phone_present, t.ip_geo, t.prov_class, t.tenant_lkus, COUNT(*) AS n, NULL AS n_pass, NULL AS n_phones, NULL AS n_phones_pass
  FROM (SELECT DATE_FORMAT(l.create_time, '%Y-%m-%d %H') AS utc_hour,
          TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc, l.result AS final_result,
          CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') NOT IN ('', 'null') THEN 0 ELSE 1 END AS sms,
          CASE WHEN NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneNo')), 'null'), '') IS NOT NULL THEN 1 ELSE 0 END AS phone_present,
          CASE WHEN NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')), 'null'), '') IS NULL THEN 'unknown'
               WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')) IN ({us_values}) THEN 'us'
               WHEN CAST(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpCountry')) AS BINARY) = CAST(COALESCE(NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.phoneCountry')), 'null'), ''), '') AS BINARY) THEN 'eq_phone'
               ELSE 'other' END AS ip_geo,
          CASE WHEN NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpProvince')), 'null'), '') IS NULL THEN 'missing'
               WHEN JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.realIpProvince')) IN ({nynj_values}) THEN 'nynj' ELSE 'other' END AS prov_class,
          CASE WHEN l.tenant = 'LKUS' THEN 1 ELSE 0 END AS tenant_lkus
        FROM (SELECT create_time, tenant, result, country_code, CASE WHEN JSON_VALID(request_strategy_engine) AND JSON_VALID(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para'))) THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) END AS pa
              FROM luckyus_iriskcontrolservice.{tbl}
              WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = 'LKUS_push') l) t
  GROUP BY t.utc_hour, t.cc, t.final_result, t.sms, t.phone_present, t.ip_geo, t.prov_class, t.tenant_lkus
  UNION ALL
  SELECT 'd', NULL, d.cc, NULL, d.sms, NULL, NULL, NULL, d.tenant_lkus, COUNT(*), SUM(d.final_result = 'PASS'),
         COUNT(DISTINCT NULLIF(d.sk, '')), COUNT(DISTINCT CASE WHEN d.final_result = 'PASS' THEN NULLIF(d.sk, '') END)
  FROM (SELECT TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) AS cc, l.result AS final_result, l.sharding_key AS sk,
          CASE WHEN JSON_VALID(l.request_strategy_engine) AND JSON_VALID(JSON_UNQUOTE(JSON_EXTRACT(l.request_strategy_engine, '$.para')))
                    AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(CAST(JSON_UNQUOTE(JSON_EXTRACT(l.request_strategy_engine, '$.para')) AS JSON), '$.email')), '') NOT IN ('', 'null') THEN 0 ELSE 1 END AS sms,
          CASE WHEN l.tenant = 'LKUS' THEN 1 ELSE 0 END AS tenant_lkus
        FROM luckyus_iriskcontrolservice.{tbl} l
        WHERE l.create_time >= '{utc_start}' AND l.create_time < '{utc_end}' AND l.scene_id = 'LKUS_push') d
  GROUP BY d.cc, d.sms, d.tenant_lkus
) x
