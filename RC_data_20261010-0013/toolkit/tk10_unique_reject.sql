-- tk10_unique_reject (DR-027): for ONE strategy, per NY day x country-code group x SMS flag x phase (before / after the
-- strategy's status switch) x final result: requests, and how many requests the strategy hit as the ONLY REJECT-class
-- strategy — online hits with no other online REJECT-class hit, or pre-online hits with no online REJECT-class hit at all.
-- "REJECT-class" = hit elements whose resultName is in {reject_names} (read from config_resultcode at run time).
-- Counts only. Rows can be summed over shards and over rows of the same window (no distinct counts here).
-- Params : {scene}; {strategy_id}; {switch_utc} ('YYYY-MM-DD HH:MM:SS', e.g. the t_operation_log time of the status change);
--          {reject_names} quoted list, e.g. 'REJECT'; window {utc_start}/{utc_end} (<= 1 NY day; use --ny-days).
-- Merge  : sum every count column over shards per (ny_date, cc_group, sms, phase, final_result).
SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{shard}' AS shard, '{ny_date}' AS ny_date, t.cc_group, t.sms, t.phase, t.final_result,
  COUNT(*) AS requests,
  SUM(t.s_on) AS s_online_hits,
  SUM(t.s_pre) AS s_preonline_hits,
  SUM(t.s_on = 1 AND t.other_rej_on = 0) AS s_online_only_reject,
  SUM(t.s_pre = 1 AND t.other_rej_on = 0) AS s_preonline_no_online_reject,
  SUM(t.other_rej_on > 0) AS other_online_reject_hit
FROM (SELECT
        CASE WHEN TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) = '1' THEN '+1'
             WHEN TRIM(LEADING '+' FROM COALESCE(l.country_code, '')) = '86' THEN '+86'
             WHEN COALESCE(l.country_code, '') = '' THEN 'unknown' ELSE 'other' END AS cc_group,
        CASE WHEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.pa, '$.email')), '') <> '' THEN 0 ELSE 1 END AS sms,
        CASE WHEN l.ct < '{switch_utc}' THEN 'before' ELSE 'after' END AS phase,
        l.result AS final_result,
        COALESCE(JSON_CONTAINS(l.h_on, JSON_OBJECT('strategyId', '{strategy_id}')), 0) AS s_on,
        COALESCE(JSON_CONTAINS(l.h_pre, JSON_OBJECT('strategyId', '{strategy_id}')), 0) AS s_pre,
        (SELECT COUNT(*) FROM JSON_TABLE(JSON_EXTRACT(l.h_on, '$'), '$[*]'
            COLUMNS (sid VARCHAR(64) PATH '$.strategyId', rn VARCHAR(64) PATH '$.resultName')) j
          WHERE j.rn IN ({reject_names}) AND j.sid <> '{strategy_id}') AS other_rej_on
      FROM (SELECT create_time AS ct, result, country_code,
              CAST(JSON_UNQUOTE(JSON_EXTRACT(request_strategy_engine, '$.para')) AS JSON) AS pa,
              CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitStrategy')) AS JSON) AS h_on,
              CAST(JSON_UNQUOTE(JSON_EXTRACT(response_strategy_engine, '$.re.hitPreOnlineStrategy')) AS JSON) AS h_pre
            FROM luckyus_iriskcontrolservice.{tbl}
            WHERE create_time >= '{utc_start}' AND create_time < '{utc_end}' AND scene_id = '{scene}') l) t
GROUP BY t.cc_group, t.sms, t.phase, t.final_result
