# RUN_LOG — RC_data_20261010-0013

运行目录：本仓库根目录（`luckin-usa-dba-ops` 工作区，非交接仓库）。时间均为 America/New_York。

| 时间 (NY) | 阶段 | 事件 | 状态 | 说明 |
|---|---|---|---|---|
| 2026-10-09 22:16 | Step A–C | plan | DONE | 只读侦察与计划；用户在计划评审时批准两项：(1) 本轮执行器从本机 MCP 配置读取 `mcp-db-gateway` 地址，只放进子进程环境，从不打印或写入文件——这一条覆盖 Part 1 第 11 点（该点要求不查找地址）；(2) 所有数据窗口截止纽约日 2026-10-09。侦察时有两条 `SHOW GRANTS` 同时发往两台不同服务器，此后所有数据库语句严格逐条 |
| 2026-10-10 00:13 | P0 | start | — | 新包（无可续跑的包；09-25/09-26/09-27 三个包均已 DONE，只读复用）；提示词与 DATA_REQUESTS.md 均以内联方式收到（桌面 2026-10-09 版，38 条 DR，最后一条变更记录「2026-10-09（第八轮，为第四次 M1 准备）：新增 DR-034～DR-038」）；DR 分类：运行 DR-030…038；常设 DR-003/010/013/014/015/016/017/018 + P3 常设项 + DR-012 复测；短节 DR-002/022（Doris）；跳过 DR-028（前提未满足：陈晨昕的口径确认）、DR-029（待林宏鹏）；生产库取数时段按团队规定限 22:00–06:00，本包执行器 05:30 后不再发语句 |
| 2026-10-10 00:14 | P0 | toolkit | DONE | Part 4 的 19 个文件写入 `toolkit/`（与 09-27 包副本逐字节相同，sha256 与大小 19/19 符合 Part 4 清单）；附录 B/C 原文写入（与 09-27 包副本相同）；`test_guard.py` 27 拒绝 + 13 放行，0 失败；隐私扫描冒烟测试正常；包内副本改动：执行器在每条语句前检查生产取数时段、EXPLAIN 门槛把空区间当作通过（见 toolkit/README） |
| 2026-10-10 00:18 | P0 | end | DONE | 主库（read_only=0），账号仅 SELECT/PROCESS/EXECUTE；MySQL 8.4.9；64 分片结构一致；执行器经本机 MCP 配置读地址（用户批准），与 MCP 直调逐格一致 7/7；别名守卫 259 个保留字；无存储过程；批量：轻量按日聚合 16 分片/条（16 分片 1 天 0.5 s），长序列与命中类 8 分片起步；Doris/Redshift 不可达；Redis 键 13,262（DBSIZE 13,276） |
| 2026-10-10 00:18 | P2 | start | — | 配置快照 #1（先于 P1，因为 E1 的参数要从配置导出） |
| 2026-10-10 00:59 | P2 | paused | — | 会话在 00:19:53 中断（定义表导出到第 4 张：config_access / block_metric / block_strategy / legacy_scene），执行器进程已不在、留下过期锁；无语句在途 |
| 2026-10-10 00:59 | P2 | resumed | — | 清除过期锁；17 张定义表全部重导出，保证同一快照时刻 |
| 2026-10-10 01:08 | P2 | queries | DONE | snapshot #1: 17 definition tables, lists (+ changes since 09-27), op-log NY 08-25..10-10 |
| 2026-10-10 01:09 | P2 | hits | DONE | p2_hits_7d NY 10-03..10-09 (all LKUS_push rows); timeline, expanded config, list-by-scene derived |
| 2026-10-10 01:19 | P1 | queries | DONE | structure, JSON keys (NY 10-09), 7-day checks (NY 10-03..10-09), province classes, DR-014 spot check NY 10-09, upush + DR-037 metadata |
| 2026-10-10 01:21 | P3 | start | — | 预检复核（只读代理，不连库）后修 E1/L1 模板：JSON_VALID 保护、JSON null 不再哈希成同一身份、去掉 IP 前缀改为类别 + 加盐 C 段哈希、加 phoneNo/countryCode/规则返回码、L1 去重手机号改为按日 × 区号（全部结果与 PASS）；冒烟测试通过后开始 E1（UTC 09-22 15:00 → 10-10 04:00）与 L1（纽约日 06-01…10-09） |
| 2026-10-10 01:46 | P3 | extract | DONE | E1 UTC 2026-09-22 15:00 .. 2026-10-10 04:00 (NY 09-22 11:00 .. 10-09 24:00), hourly, local only |
| 2026-10-10 02:05 | P4 | long-series | DONE | L1 NY 2026-06-01..10-09 (8 shards per statement), parts local, merged into results/l1_long.csv |
| 2026-10-10 02:20 | Q7 | queries | DONE | tk10 (43Na NY 09-22..10-09; bYXa, WvNG NY 10-02..10-09), tk02 MZQk, tk07 7 days, tk11 bYXa |
| 2026-10-10 02:24 | Q8 | queries | DONE | DR-038 (09-21 and 7 days), DR-035 upush aggregate, DR-037 checks + member/order aggregates |
| 2026-10-10 02:39 | Q9 | queries | DONE | toolkit tests tk01-tk11 (SMS and all-rows bases: tk01/02/03/06/07/08/11; SMS only: tk04/05/09/10), checkpoint |
| 2026-10-10 02:42 | Q10 | queries | DONE | stability re-runs, fleet name sweep, config snapshot #2 |
| 2026-10-10 02:42 | Q10 | DR-038 v2 | DONE | realIpc 不是推送场景的请求参数（09-21 那 50 次全为空），改用 realIp 前三段作 C 段重跑 |
| 2026-10-10 02:43 | DB | end | DONE | 全部数据库语句在纽约时间 2026-10-10 00:14–02:43 完成（生产取数时段内）；之后只做本机计算与写页面 |
| 2026-10-10 01:10 | P2 | end | DONE | 快照 #1：17 张定义表（操作人列已屏蔽）、名单计数（09-27 之后无变化）、操作日志（09-27 之后的 46 次操作已导出）；快照 #2（02:42）与 #1 无差异，取数期间没有新操作（`results/p2_snapshot_diff.csv`） |
| 2026-10-10 01:20 | P1 | end | DONE | 结构 / JSON 键 / 7 日核对 / 省份取值 / DR-014 抽查 / upush 与 DR-037 元数据（Q2）；名字扫描在 02:41（Q10）；01 与 dictionary 已生成 |
| 2026-10-10 02:18 | P3 | end | DONE | E1 共 18 个文件（UTC 09-22 15:00 → 10-10 04:00，本机）；7 日画像与 L1 / tk07 / p2_hits_7d 逐格核对 0 不一致（`results/p3_crosscheck.csv`）；桥接序列已出 |
| 2026-10-10 02:50 | P4 | end | DONE | 22 个 DR 小节；DR-030 tk10 vs E1 101 格 0 不一致；DR-036(a) PASS 26/26 天与 Doris 相同；DR-038 因 `realIpc` 不是推送场景参数而改用 realIp 前三段重跑（v2） |
| 2026-10-10 02:50 | P5 | end | DONE | 工具包测试 61/61 一致（tk01–tk11；短信与全部行两种口径都测的是 tk01、02、03、06、07、08、11，只测短信口径的是 tk04、05、09、10）；复现检查点 +4 行（与 09-27 包相同的窗口边界差）；tk06 复核 0/7 违例 |
| 2026-10-10 02:51 | P6 | start | — | 页面生成、指标注册表、自检、离线复核 |
| 2026-10-10 03:12 | P6 | review | DONE | 离线复核（只读包内文件，不连库、不读 _local_only）后已改：DR-032 结论方向更正（「不是 NY/NJ 就拒」在攻击前会拦 15 个区号 5,958/6,012 次请求）；DR-031、DR-034 补时间线、每 24 小时速率（含前后半）与基线敏感性，标「计数分解，非因果」；DR-037 改为「已知区号有消费会员 46–49 人，不是上限」并加 09-01 前后注册拆分（互补抑制）、逐月结果移到本机；DR-012 补四组；措辞降为「推断」处若干；README §8 每行带汇总数、不写人名；P0 直调结果补生产脚本 `sql/local/p0_inventory.py` 与 `sql/p0_mcp_direct.sql`，tk06 复核命令 `sql/local/p5_tk06_recheck.sh`；执行器加命令开始时的时段检查与逐窗口 EXPLAIN 门槛 |
| 2026-10-10 03:12 | P6 | end | DONE | 00–06、05 开放探索、README、NEXT_RUN、toolkit/README 已重生成；p6_checks：路径缺失 0、端点 0、本机路径/内网 0、__pycache__ 0、README 合计 = 04、指标冲突 0、策略效果类 DR 缺项 0（MANIFEST 在 P7 生成；16 个数是结果表行的求和、告警阈值或版本号，不逐字出现在 results/）；全部运行 158 次、4,659 条分片语句 |
| 2026-10-10 03:12 | P7 | end | DONE — MANIFEST and zip follow | 稳定性 4/4 一致（results/p7_stability.csv）；配置快照 #2 与 #1 差异 0；隐私扫描 557 个文件，unresolved 0（自动豁免：8 位以上数字 2,995、IPv4 1 = 扫描器说明里的 0.0.0.0）；盐已删除；桌面 _inbox 不在本机（第 6 步跳过）；交接仓库为 public，按覆盖项不做第 7 步（无 git 操作）；zip 与 .sha256 留在运行目录 |
