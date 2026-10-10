SELECT /*+ MAX_EXECUTION_TIME(10000) */ '{utc_start}' AS window_start_utc, '{shard_range}' AS shard_range, u.k AS cc, COUNT(DISTINCT u.s) AS shards_seen, SUM(u.r = 'PASS') AS sms_pass, COUNT(*) AS sms_requests
FROM (SELECT b.s, b.r, b.m,
        CASE WHEN TRIM(COALESCE(b.c, '')) = '' THEN 'empty'
             WHEN TRIM(LEADING '+' FROM TRIM(b.c)) REGEXP '^[0-9][0-9]?[0-9]?[0-9]?$' THEN TRIM(LEADING '+' FROM TRIM(b.c))
             ELSE 'invalid' END AS k
      FROM ({branches}) b) u
WHERE u.m = 0 AND u.k NOT IN ('1', '86')
GROUP BY u.k
