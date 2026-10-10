-- L1 long aggregate: the runner executed this template once per 7 NY days (8 shards per statement); runs:
-- name: l1_20260601
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-06-01 04:00:00 .. 2026-06-08 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:46
-- name: l1_20260608
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-06-08 04:00:00 .. 2026-06-15 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:47
-- name: l1_20260615
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-06-15 04:00:00 .. 2026-06-22 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:47
-- name: l1_20260622
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-06-22 04:00:00 .. 2026-06-29 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:48
-- name: l1_20260629
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-06-29 04:00:00 .. 2026-07-06 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:48
-- name: l1_20260706
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-07-06 04:00:00 .. 2026-07-13 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:49
-- name: l1_20260713
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-07-13 04:00:00 .. 2026-07-20 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:49
-- name: l1_20260720
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-07-20 04:00:00 .. 2026-07-27 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:50
-- name: l1_20260727
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-07-27 04:00:00 .. 2026-08-03 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:50
-- name: l1_20260803
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-08-03 04:00:00 .. 2026-08-10 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:51
-- name: l1_20260810
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-08-10 04:00:00 .. 2026-08-17 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:52
-- name: l1_20260817
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-08-17 04:00:00 .. 2026-08-24 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:52
-- name: l1_20260824
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-08-24 04:00:00 .. 2026-08-31 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:53
-- name: l1_20260831
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-08-31 04:00:00 .. 2026-09-07 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:54
-- name: l1_20260907
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-09-07 04:00:00 .. 2026-09-14 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:56
-- name: l1_20260914
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-09-14 04:00:00 .. 2026-09-21 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 01:59
-- name: l1_20260921
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-09-21 04:00:00 .. 2026-09-28 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 02:01
-- name: l1_20260928
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 7 [2026-09-28 04:00:00 .. 2026-10-05 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 02:02
-- name: l1_20261005
-- kind: agg; shards: 64 (0000..0063); batch: 8; windows: 5 [2026-10-05 04:00:00 .. 2026-10-10 04:00:00) UTC, chunk=day
-- run (NY): 2026-10-10 02:04

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
