SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{utc_start}' AS window_start_utc, '{utc_end}' AS window_end_utc, '{shard_range}' AS shard_range,
  COUNT(DISTINCT u.s) AS shards_seen, SUM(DISTINCT u.s + 0) AS shard_sum, CAST(MIN(u.t) AS CHAR) AS first_utc, CAST(MAX(u.t) AS CHAR) AS last_utc,
  COUNT(*) AS rows_all, COUNT(*) - COUNT(DISTINCT u.i, u.t, COALESCE(u.c, '')) AS dup_rows, SUM(u.m) AS email_rows, SUM(1 - u.m) AS sms_total,
  SUM(u.m = 0 AND u.r = 'PASS') AS sms_pass, SUM(u.m = 0 AND u.r = 'REJECT') AS sms_reject, SUM(u.m = 0 AND u.r = 'REVIEW') AS sms_review,
  SUM(u.m = 0 AND (u.r IS NULL OR u.r NOT IN ('PASS', 'REJECT', 'REVIEW'))) AS sms_other,
  SUM(u.m = 0 AND u.r = 'PASS' AND u.k = '1') AS pass_1, SUM(u.m = 0 AND u.r = 'PASS' AND u.k = '86') AS pass_86,
  SUM(u.m = 0 AND u.r = 'PASS' AND u.k = 'empty') AS pass_empty, SUM(u.m = 0 AND u.r = 'PASS' AND u.k = 'invalid') AS pass_invalid,
  SUM(u.m = 0 AND u.r = 'PASS' AND u.k NOT IN ('1', '86', 'empty', 'invalid')) AS pass_not_us_cn,
  SUM(u.m = 0 AND u.r = 'PASS' AND u.k IN ({codes})) AS pass_21,
  SUM(u.m = 0 AND u.r = 'PASS' AND u.k NOT IN ('1', '86', 'empty', 'invalid') AND u.k NOT IN ({codes})) AS pass_not_21,
  SUM(u.m = 0 AND u.k = 'empty') AS sms_cc_empty, SUM(u.m = 0 AND u.k = 'invalid') AS sms_cc_invalid, SUM(u.m = 0 AND u.p = 0 AND u.k <> 'empty') AS sms_no_plus,
  TIMESTAMPDIFF(SECOND, MAX(u.t), '{utc_end}') AS lag_s
FROM (SELECT b.s, b.i, b.c, b.r, b.m, b.t,
        CASE WHEN TRIM(COALESCE(b.c, '')) = '' THEN 'empty'
             WHEN TRIM(LEADING '+' FROM TRIM(b.c)) REGEXP '^[0-9][0-9]?[0-9]?[0-9]?$' THEN TRIM(LEADING '+' FROM TRIM(b.c))
             ELSE 'invalid' END AS k,
        CASE WHEN LEFT(TRIM(COALESCE(b.c, '')), 1) = '+' THEN 1 ELSE 0 END AS p
      FROM ({branches}) b) u
