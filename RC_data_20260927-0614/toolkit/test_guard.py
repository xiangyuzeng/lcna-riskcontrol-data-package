#!/usr/bin/env python3
"""Unit tests for shard_runner.guard(): forbidden statements must raise, legitimate reads must pass."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_runner  # noqa: E402
from shard_runner import guard, GuardError  # noqa: E402
shard_runner.RESERVED.update({"ORDER", "KEY", "GROUP"})   # stands in for _local_only/reserved_words.txt (information_schema.KEYWORDS)

H = "/*+ MAX_EXECUTION_TIME(5000) */"
T = "luckyus_iriskcontrolservice.t_access_log_0000"
DAY = "create_time >= '2026-09-24 04:00:00' AND create_time < '2026-09-25 04:00:00'"
HOUR = "create_time >= '2026-09-24 04:00:00' AND create_time < '2026-09-24 05:00:00'"

REFUSE = [
    ("DELETE FROM t", "agg"),
    (f"SELECT {H} 1; DROP TABLE x", "agg"),
    ("SET SESSION group_concat_max_len=100000", "agg"),
    (f"SELECT {H} REPLACE(country_code,'+','') FROM {T} WHERE {DAY}", "agg"),
    (f"SELECT {H} id FROM {T} WHERE {DAY} FOR UPDATE", "agg"),
    (f"SELECT {H} id FROM {T} WHERE {DAY} LOCK IN SHARE MODE", "agg"),
    (f"SELECT {H} SLEEP(1)", "agg"),
    (f"SELECT {H} BENCHMARK(10, MD5('a'))", "agg"),
    ("WITH x AS (SELECT 1) SELECT * FROM x", "agg"),
    ("CALL some_proc()", "agg"),
    (f"SELECT {H} 1 INTO OUTFILE '/tmp/x'", "agg"),
    (f"SELECT {H} 1 INTO @v", "agg"),
    ("SELECT 1", "agg"),                                            # no hint
    ("SELECT /*+ MAX_EXECUTION_TIME(60000) */ 1", "agg"),           # hint above 10 s
    (f"SELECT {H} COUNT(*) FROM {T}", "agg"),                        # log table without bounds
    (f"SELECT {H} COUNT(*) FROM {T} WHERE create_time >= '2026-09-22 04:00:00' AND create_time < '2026-09-25 04:00:00'", "agg"),
    (f"SELECT {H} COUNT(*) FROM {T} l WHERE DATE(l.create_time) >= '2026-09-24 00:00:00' AND DATE(l.create_time) < '2026-09-25 00:00:00'", "agg"),
    (f"SELECT {H} id FROM {T} WHERE {DAY}", "rows"),                 # row extract wider than 1 h
    ("SHOW FULL PROCESSLIST", "agg"),
    ("LOCK TABLES t READ", "agg"),
    ("TRUNCATE t", "agg"),
    (f"SELECT {H} 1 UNION SELECT 2; KILL 5", "agg"),
    ("HANDLER t OPEN", "agg"),
    ("ANALYZE TABLE t", "agg"),
    (f"SELECT {H} DATE(create_time) AS utc_date, COUNT(*) AS n FROM {T} WHERE {DAY} GROUP BY utc_date", "agg"),   # 1064 on 2026-09-26
    (f"SELECT {H} COUNT(*) AS rank FROM {T} WHERE {DAY}", "agg"),
    (f"SELECT {H} COUNT(*) AS `order`, 1 AS key FROM {T} WHERE {DAY}", "agg"),                                        # reserved word (from KEYWORDS)
]
PASS = [
    (f"SELECT {H} DATE(create_time) AS utc_day, CAST(sharding_key AS BINARY) = CAST('x' AS BINARY) AS eq, COUNT(*) AS n FROM {T} WHERE {DAY} GROUP BY utc_day", "agg"),
    (f"SELECT {H} strategy_id, update_time FROM luckyus_iriskcontrolservice.t_rms_engine_strategy", "agg"),
    (f"SELECT {H} deleted, CAST('a' AS CHAR CHARACTER SET utf8mb4), JSON_SET('{{}}','$.a',1) FROM x", "agg"),
    (f"SELECT {H} result, COUNT(*) FROM {T} l WHERE l.{DAY.replace(' AND create_time', ' AND l.create_time')} GROUP BY result", "agg"),
    (f"SELECT {H} id FROM {T} WHERE {HOUR}", "rows"),
    ("SHOW GRANTS", "agg"),
    ("DESCRIBE luckyus_iriskcontrolservice.t_access_log_0000", "agg"),
    (f"EXPLAIN SELECT {H} COUNT(*) FROM {T} WHERE {DAY}", "agg"),
    (f"SELECT {H} TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE 't_access_log_%'", "agg"),
    (f"-- select the daily counts\nSELECT {H} COUNT(*) FROM {T} WHERE {DAY}", "agg"),
    (f"SELECT {H} u.* FROM ((SELECT {H} '0000' AS shard, COUNT(*) n FROM {T} WHERE {DAY}) UNION ALL "
     f"(SELECT {H} '0001' AS shard, COUNT(*) n FROM luckyus_iriskcontrolservice.t_access_log_0001 WHERE {DAY})) u", "agg"),
    (f"SELECT {H} TRIM(LEADING '+' FROM country_code) cc FROM {T} WHERE {DAY}", "agg"),
    ("SHOW GLOBAL STATUS LIKE 'Threads_running'", "agg"),
]

fails = 0
for sql, kind in REFUSE:
    try:
        guard(sql, kind)
        print("NOT REFUSED:", sql[:90]); fails += 1
    except GuardError:
        pass
for sql, kind in PASS:
    try:
        guard(sql, kind)
    except GuardError as e:
        print("WRONGLY REFUSED:", sql[:90], "->", e); fails += 1
print(f"guard tests: {len(REFUSE)} refuse + {len(PASS)} pass cases, failures={fails}")
sys.exit(1 if fails else 0)
