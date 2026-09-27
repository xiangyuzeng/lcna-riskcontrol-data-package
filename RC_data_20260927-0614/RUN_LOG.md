# RUN_LOG — RC_data_20260927-0614

> 时间为 America/New_York。计划（Step C）已获用户批准。
> 输入来源：提示词 M1（桌面 2026-09-26 第六轮修订版）与 `DATA_REQUESTS.md` 都**随对话消息内联提供**（`DATA_REQUESTS.md` = 桌面 2026-09-26 副本，28 条 DR，变更记录最后一条「2026-09-26（第六轮）」）；以这份内联副本为准。

| 时间 (NY) | 阶段 | 事件 | 状态 | 说明 |
|---|---|---|---|---|
| 2026-09-27 06:15 | P0 | start | — | setup + inventory; prompt and DATA_REQUESTS.md (desktop copy 2026-09-26, 28 DRs, last entry 2026-09-26（第六轮）) received inline in the chat; DR list = DR-027 + standing DR-003/010/013/014/015/016/017/018; DR-002/022 short (Doris dependency); DR-028 skipped (precondition not met) |
| 2026-09-27 06:20 | P0 | end | DONE | primary, SELECT/PROCESS/EXECUTE only; 64 shards; runner = MCP direct 7/7; batch 16 (8 for cross-month); alias guard from information_schema.KEYWORDS (259 reserved) + --no-parts default; Doris/Redshift unreachable; Redis 12,786 keys |
| 2026-09-27 06:20 | P1 | start | — | structure + 7-day checks + fleet sweep |
| 2026-09-27 06:23 | P1 | note | — | chain stopped at p1_freshness: EXPLAIN gate refused because shard 0000 had no rows in the last hour (No matching min/max row, nothing scanned); freshness window widened to the last 7 UTC hours and chain resumed |
| 2026-09-27 06:34 | P1 | queries | DONE | structure, JSON keys, 7-day checks, DR-014 spot check, fleet sweep, upush metadata |
| 2026-09-27 06:34 | P2 | start | — | 补记：P2 第一条运行在 P1 最后一条（p1_upush_indexes，06:34:40 完成）之后开始（`results/_runlog.csv`） |
| 2026-09-27 06:42 | P2 | queries | DONE | 17 definition tables, lists, op-log (NY 08-25..09-26), 7-day hits |
| 2026-09-27 06:43 | P1 | end | DONE | 64 shards identical; JSON keys; 7-day checks (NY 09-20..09-26); DR-014 spot check NY 09-26; fleet sweep; upush metadata; 01 + dictionary/ written |
| 2026-09-27 06:43 | P2 | end | DONE | 17 definition tables (operator masked); lists by type x scene x source; op-log 195 operations (194 with field changes, 299 changed fields), last 2026-09-24 07:26:13 UTC; 02 written |
| 2026-09-27 06:42 | P3 | start | — | 补记：E1 抽取在 p2_hits_7d（06:42:48 完成）之后开始（`results/_runlog.csv`） |
| 2026-09-27 06:51 | P3 | extract | DONE | E1 NY 09-19..09-26 hourly, local only |
| 2026-09-27 06:51 | P4 | start | — | 补记：P4 查询在 E1（e1_b，06:51:19 完成）之后开始（`results/_runlog.csv`） |
| 2026-09-27 07:12 | P4 | queries | DONE | DR-010 series (batch 8), DR-027 tk10 + tk08, checkpoint |
| 2026-09-27 07:12 | P5 | start | — | toolkit test queries |
| 2026-09-27 07:21 | P3 | end | DONE | E1 32,274 rows (NY 09-19..09-26, 768 hourly statements, local only); profile NY 09-20..09-26; cross-checks 3/3, 0 mismatching cells; PASS-class 额外召回 fixed |
| 2026-09-27 07:21 | P4 | end | DONE | 12 DR sections; DR-027 tk10 vs E1 348 cells / tk08 vs E1 8 cells, 0 mismatches; DR-010 series 06-01..09-26 at 8 shards; checkpoint reproduced (+4 rows) |
| 2026-09-27 07:21 | P5 | end | DONE | tk01–tk10 tested once; all checks equal (results/toolkit_tests/_test_summary.csv); tk06 re-check 0/10 violations |
| 2026-09-27 07:21 | P7 | stability | — | 3 key re-runs before final page generation |
| 2026-09-27 07:21 | P6 | start | — | 补记：P7 稳定性复跑之后开始写 05 / 06 / README / NEXT_RUN，建指标注册表与自检 |
| 2026-09-27 08:10 | P6 | retest | DONE | 离线复核指出 tk02 / tk03 / tk06 缺短信口径：tk02、tk03 加 `sms_only`，tk06 抽取加 `email_nonempty`，两种口径重测（tk02/tk03 各 2 次运行，tk06 抽取 104 条语句，行级只存本机）；巡检页为口径标注重跑；`list_servers` 计数写入 results/p0_mcp_inventory.csv；工具包测试 55/55 一致 |
| 2026-09-27 08:34 | P6 | review | DONE | 离线复核两轮（7 + 3 个代理，只读包内文件，不连库、不读 _local_only）：数字全部可由 results/ 复算，未发现个人信息或密钥；据此改写 DR-027 结论（计数分解、基线敏感性、条件拆分）、补口径标注、新开 DR-029（04 现为 13 节）、DR-013 计数落文件、自检加强 |
| 2026-09-27 08:34 | P6 | end | DONE | 00–06、README、NEXT_RUN、toolkit/README 已重生成；p6_checks：路径缺失 0、端点 0、本机路径/内网 0、__pycache__ 0、README 合计 = 04、指标冲突 0（MANIFEST 在 P7 生成）；全部运行 97 次、3,390 条分片语句 |
| 2026-09-27 08:34 | P7 | end | DONE — MANIFEST and zip follow | 稳定性 3/3 一致（results/p7_stability.csv）；隐私扫描 400 个文件，unresolved 0（allowlisted 1：Redis 平均 TTL）；盐已删除；交接仓库为 public，按覆盖项不做第 7 步（无 git 操作）；zip 与 .sha256 留在运行目录 |
