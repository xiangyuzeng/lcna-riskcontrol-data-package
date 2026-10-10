# toolkit — 北美风控取数工具包

> 2026-10-10 更新（RC_data_20261010-0013）。Part 4 原文 + 本包的改动（§6）。每个模板都用本包数据跑过一次，并与另一种算法（E1 本地抽取或独立 SQL）逐项核对：61/61 项一致（`results/toolkit_tests/_test_summary.csv`）。
> 数据源：MCP server `mcp-db-gateway` 的 `mysql_query` 工具 → `aws-luckyus-iriskcontrolservice-rw` / `luckyus_iriskcontrolservice.t_access_log_0000…0063`。只读。连接地址从不写进任何文件。

## 1. 文件

| 文件 | 用途 |
|---|---|
| `shard_runner.py` | 取数执行器：语句守卫 → EXPLAIN 门槛 → 64 分片按批（默认 16 个/条）顺序执行 → 写 `sql/<name>.sql` 与 `results/<name>.csv`；单条 >3 s 自动减半批量；超时不重跑 |
| `test_guard.py` | 守卫单测（应拒绝 / 应放行各一组） |
| `ny_day_bounds.py` | 纽约自然日 → UTC 起止（夏令时安全；提示词附录 C） |
| `same_hours.py` | 目标时段 + 前 N 天同一时段的 UTC 窗口列表（给 `--windows-file`） |
| `tk01_volume_users.sql` | 调用量：区号 × 最终结果 × email 标记计数；窗口级精确去重手机号 |
| `tk02_strategy_hits.sql` | 单条策略（在线或预上线）命中 PV；窗口级去重手机号；参数 `sms_only`（1 = 短信口径） |
| `tk03_extra_recall.sql` | 预上线策略的额外召回（非 PASS 类：命中且最终 PASS；PASS 类：命中且最终不是 PASS；参数 `pass_class`、`sms_only`） |
| `tk04_pass_leakage.sql` | 非本国区号的放行画像 |
| `tk05_v3_distribution.sql` | reCAPTCHA 分数分布（按形状取分） |
| `tk06_rule_recheck_extract.sql` + `recheck_counter.py` | 累计特征规则复核：本地重算计数（用全部行）、只输出违例条数；抽取带 `email_nonempty`，输出另给短信口径的命中与违例 |
| `tk07_daily_patrol.sql` + `patrol.py` | 每日巡检一页纸（结果与区号占比为短信口径；策略命中表为全部 LKUS_push 行） |
| `tk08_strategy_cid_geo.sql` | （DR-023）单条策略命中按 cid × (phoneCountry ≠ realIpCountry) × 最终结果，PV 与去重手机号 |
| `tk09_engine_vs_final.sql` | （DR-024 / DR-016）纽约日 × cid × app 状态 × 版本组（数值比较）× 引擎结果 × 最终结果 |
| `tk10_unique_reject.sql` | **新**（DR-027）：单条策略作为唯一 REJECT 类命中的请求数，按纽约日 × 区号组 × 阶段（状态变化前 / 后）× 最终结果 |
| `tk11_bypass_watch.sql` | **新**（2026-10-10）：一条策略的目标区号里，按纽约日 × 区号 × IP 类别 × 是否被它命中 × 最终结果计数——没被命中而 PASS 的就是「绕过」 |
| `tk_merge.py` | tk01–tk05 的合并步骤（跨分片汇总） |
| `privacy_scan.py` | 交付前隐私扫描（提示词附录 B 原文） |
| `privacy_allowlist.txt` | 扫描白名单：已核实不是个人信息的命中（`<sha1> <理由>`） |
| `package.py` | P7 打包：写 `MANIFEST.md`、zip（不含 `_local_only/`）与 `.sha256`；扫描未清零时拒绝运行 |

## 2. 运行方式

**脚本方式**（推荐，结果和 SQL 自动落盘）：

```bash
export MCP_DB_GATEWAY_SSE=<mcp-db-gateway 的 SSE 地址>      # 向 DBA 要，不要写进文件
export PYTHONDONTWRITEBYTECODE=1
cd RC_data_<stamp>
python3 toolkit/shard_runner.py run --name <结果名> --template toolkit/<模板>.sql \
    --param scene=LKUS_push [--param k=v ...] --ny-days 2026-09-26:2026-09-26 [--batch 16]
python3 toolkit/tk_merge.py tk01 results/<结果名>.csv --home-cc 1 --watch-cc 86 --sms-only
```

- 时间窗口：`--ny-days A:B`（按纽约日，每天一条语句）、`--utc 'A~B' --chunk day|hour`，或 `--windows-file`（每行一个 `UTC起~UTC止`）。
- 行级抽取（tk06）必须 `--kind rows --local`：每条语句 ≤1 小时，结果只写 `_local_only/raw/`，身份字段是加盐哈希（盐每次运行随机生成，存在 `_local_only/.run_salt`，用完即删）。
- 每次批量前执行器自动查进程负载（`information_schema.PROCESSLIST` 聚合）；单条 >3 s 自动把批量减半；超时不重跑。

**MCP 直调方式**（没有脚本环境时）：在 Claude Code 里调用 `mcp-db-gateway` 的 `mysql_query`，`server=aws-luckyus-iriskcontrolservice-rw`。把模板里的 `{tbl}` 换成 `t_access_log_0000` … `t_access_log_0063`、`{shard}` 换成四位分片号、`{utc_start}/{utc_end}` 换成 UTC 字面量（`python3 toolkit/ny_day_bounds.py 7` 可打印），每条最多 UNION ALL 16 个分片、最多 1 天。发送前先 `python3 toolkit/shard_runner.py check <文件>` 过守卫。

## 3. 去重口径（重要）

- LKUS_push 的分片键 `sharding_key` = 带 `+` 的完整手机号（DR-014）：**同一窗口、同一分组内**各分片的 `COUNT(DISTINCT sharding_key)` 可以直接相加。
- **不能跨分组相加**（同一手机号同一天可能既 PASS 又 REJECT）：tk01/tk02 输出里 `level=window` 的行才是窗口级去重；tk08 的 `cidgeo` 行是 cid × 国家组内的去重。
- **不能跨窗口相加**：多天去重要用行级抽取（tk06 方式）在本地去重。
- uid 不是 LKUS_push 的分片键；登录 / 支付 / 下单等场景按 `userNo` 分片（DR-014），在这些场景里去重手机号不能按分片相加。

## 4. 本次测试（纽约日 2026-10-03…10-09；tk01 为 10-09 与前 7 天同一时段，tk06 / tk07 / tk09 为 10-09，tk10 为 43Na 纽约日 09-22…10-09 与 bYXa / WvNG 纽约日 10-02…10-09，tk11 为 bYXa；挑选的策略来自数据：PRE=`strategy_GbsajBR69can`、PRE_PASS_CLASS=`1`、ON=`strategy_WvNGjLMgoOyn`、TK06_STRATEGY=`strategy_lf6DsxMdAPzy`）

| 测试 | 模板结果 | 对照 | 一致 | 备注 |
|---|---|---|---|---|
| tk01 2026-10-02 requests (all push rows) vs L1 | 3003 | 3003 | 是 |  |
| tk01 2026-10-03 requests (all push rows) vs L1 | 3359 | 3359 | 是 |  |
| tk01 2026-10-03 SMS distinct phones vs E1 | 2026 | 2026 | 是 |  |
| tk01 2026-10-03 SMS PASS +1 distinct phones vs E1 | 1230 | 1230 | 是 |  |
| tk01 2026-10-04 requests (all push rows) vs L1 | 2692 | 2692 | 是 |  |
| tk01 2026-10-04 SMS distinct phones vs E1 | 1590 | 1590 | 是 |  |
| tk01 2026-10-04 SMS PASS +1 distinct phones vs E1 | 789 | 789 | 是 |  |
| tk01 2026-10-05 requests (all push rows) vs L1 | 2848 | 2848 | 是 |  |
| tk01 2026-10-05 SMS distinct phones vs E1 | 1614 | 1614 | 是 |  |
| tk01 2026-10-05 SMS PASS +1 distinct phones vs E1 | 852 | 852 | 是 |  |
| tk01 2026-10-06 requests (all push rows) vs L1 | 2829 | 2829 | 是 |  |
| tk01 2026-10-06 SMS distinct phones vs E1 | 1598 | 1598 | 是 |  |
| tk01 2026-10-06 SMS PASS +1 distinct phones vs E1 | 927 | 927 | 是 |  |
| tk01 2026-10-07 requests (all push rows) vs L1 | 3457 | 3457 | 是 |  |
| tk01 2026-10-07 SMS distinct phones vs E1 | 1820 | 1820 | 是 |  |
| tk01 2026-10-07 SMS PASS +1 distinct phones vs E1 | 916 | 916 | 是 |  |
| tk01 2026-10-08 requests (all push rows) vs L1 | 2896 | 2896 | 是 |  |
| tk01 2026-10-08 SMS distinct phones vs E1 | 1636 | 1636 | 是 |  |
| tk01 2026-10-08 SMS PASS +1 distinct phones vs E1 | 948 | 948 | 是 |  |
| tk01 2026-10-09 requests (all push rows) vs L1 | 2129 | 2129 | 是 |  |
| tk01 2026-10-09 SMS distinct phones vs E1 | 1389 | 1389 | 是 |  |
| tk01 2026-10-09 SMS PASS +1 distinct phones vs E1 | 894 | 894 | 是 |  |
| tk02 strategy_GbsajBR69can pre-online PV 7d vs p2_hits_7d | 15571 | 15571 | 是 |  |
| tk02 2026-10-03 strategy_GbsajBR69can distinct phones vs E1 | 1682 | 1682 | 是 |  |
| tk02 2026-10-04 strategy_GbsajBR69can distinct phones vs E1 | 1299 | 1299 | 是 |  |
| tk02 2026-10-05 strategy_GbsajBR69can distinct phones vs E1 | 1318 | 1318 | 是 |  |
| tk02 2026-10-06 strategy_GbsajBR69can distinct phones vs E1 | 1317 | 1317 | 是 |  |
| tk02 2026-10-07 strategy_GbsajBR69can distinct phones vs E1 | 1431 | 1431 | 是 |  |
| tk02 2026-10-08 strategy_GbsajBR69can distinct phones vs E1 | 1397 | 1397 | 是 |  |
| tk02 2026-10-09 strategy_GbsajBR69can distinct phones vs E1 | 1169 | 1169 | 是 |  |
| tk03 strategy_GbsajBR69can extra recall PV 7d vs E1 (all push rows; pass_class=1) | 4936 | 4936 | 是 |  |
| tk02 strategy_GbsajBR69can pre-online PV 7d, sms_only=1, vs E1 SMS | 15549 | 15549 | 是 |  |
| tk02 2026-10-03 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1680 | 1680 | 是 |  |
| tk02 2026-10-04 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1298 | 1298 | 是 |  |
| tk02 2026-10-05 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1316 | 1316 | 是 |  |
| tk02 2026-10-06 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1316 | 1316 | 是 |  |
| tk02 2026-10-07 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1430 | 1430 | 是 |  |
| tk02 2026-10-08 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1396 | 1396 | 是 |  |
| tk02 2026-10-09 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1167 | 1167 | 是 |  |
| tk03 strategy_GbsajBR69can extra recall PV 7d, sms_only=1, vs E1 SMS (pass_class=1) | 4936 | 4936 | 是 |  |
| tk04 non-+1 SMS PASS rows 7d vs E1 | 4874 | 4874 | 是 |  |
| tk04 non-+1 SMS PASS ip_country=美国 vs E1 | 1550 | 1550 | 是 |  |
| tk04 non-+1 SMS PASS token_state=absent vs E1 | 333 | 333 | 是 |  |
| tk04 non-+1 SMS PASS cid=105 vs E1 | 4446 | 4446 | 是 |  |
| tk05 score-bucket cells (cc group x cid x bucket) equal to E1 | 36 | 36 | 是 | 36 cells |
| tk06 strategy_lf6DsxMdAPzy hits on NY 2026-10-09 vs p2_hits_7d | 7 | 7 | 是 | re-check output (not a test): violations 0/7; engine==recompute 0.9869, within1 0.9995 |
| tk06 strategy_lf6DsxMdAPzy SMS hits on NY 2026-10-09 (email_nonempty=0) vs E1 SMS | 7 | 7 | 是 | re-check output (not a test): SMS violations 0/7 |
| tk07 2026-10-09 SMS PASS vs E1 | 1261 | 1261 | 是 |  |
| tk07 2026-10-09 SMS REJECT vs E1 | 848 | 848 | 是 |  |
| tk07 2026-10-09 SMS REVIEW vs E1 | 17 | 17 | 是 |  |
| tk07 2026-10-09 online hit PV per strategy equal to p2_hits_7d | 23 | 23 | 是 | 23 strategies |
| tk08 strategy_WvNGjLMgoOyn PV cells (day x cid x geo) all rows equal to E1 | 8 | 8 | 是 | 8 cells |
| tk08 strategy_WvNGjLMgoOyn distinct-phone cells all rows equal to E1 | 8 | 8 | 是 | 8 cells |
| tk08 strategy_WvNGjLMgoOyn PV cells (day x cid x geo) sms_only=1 equal to E1 | 8 | 8 | 是 | 8 cells |
| tk08 strategy_WvNGjLMgoOyn distinct-phone cells sms_only=1 equal to E1 | 8 | 8 | 是 | 8 cells |
| tk09 2026-10-09 SMS engine x final cells equal to E1 | 4 | 4 | 是 | 4 cells |
| tk10 strategy_43NaEzJmiQFk cells (requests and unique REJECT) equal to E1, NY 09-23..10-09 SMS | 101 | 101 | 是 | 101 cells |
| tk10 strategy_bYXaOJ4qXtW4 cells equal to E1 (NY 2026-10-02..2026-10-09, both bases) | 57 | 57 | 是 | 57 cells |
| tk10 strategy_WvNGjLMgoOyn cells equal to E1 (NY 2026-10-02..2026-10-09, both bases) | 59 | 59 | 是 | 59 cells |
| tk11 strategy_bYXaOJ4qXtW4 bypass-watch cells equal to E1 (sms_only=1) | 397 | 397 | 是 | 397 cells |
| tk11 strategy_bYXaOJ4qXtW4 bypass-watch cells equal to E1 (all rows) | 397 | 397 | 是 | 397 cells |

测试原始输出：`results/toolkit_tests/` 与 `results/dr030_tk10_43na.csv`、`results/dr034_tk10_*.csv`、`results/dr031_tk11_bYXa.csv`；每个测试实际执行的 SQL：`sql/toolkit_tests/`、`sql/dr0*.sql`；比对脚本 `sql/local/p5_toolkit_tests.py`。

## 5. 每个模板的要点

- **tk01**：每日调用量与「近 7 日同期」。`python3 toolkit/same_hours.py 2026-09-26T00:00 2026-09-27T00:00 --prev 7 > w.txt`，再 `run --windows-file w.txt`。`email_key` = `$.para.email` 非空；`--sms-only` 去掉这些行。
- **tk02**：`hit_list=hitPreOnlineStrategy` 统计预上线命中；`sms_only=1` 只算短信（`$.para.email` 为空或不存在），`0` 算全部行。命中判断用 `JSON_CONTAINS(..., JSON_OBJECT('strategyId', ...))`，只认 ID，不认策略名。
- **tk03**：额外召回 = 它上线后会改变结果的命中；PASS 类策略用 `pass_class=1`（取最终不是 PASS 的命中）；`sms_only` 同 tk02。是否打到本国用户看 `pv_home`。
- **tk04**：`home_ccs` 是不带 `+` 的带引号列表；合并时 `--sms-only` 去掉带 email 的请求（DR-002）。
- **tk05**：分数取任一 reCAPTCHA 特征 apiResp 里的 `riskAnalysis.score`——承载分数的 featureId 历史上切换过（DR-005），不要按特征名或单一 ID 取。
- **tk06**：计数口径：同一维度值、窗口 (t−period, t]、含当前请求、只计引擎评估过该特征的请求。支持的维度：countryCode / phoneNo / realIp / realIpc / uid / realIpCountry；条件支持 `NOT_EQUAL_STRING(realIpCountry,…)` 与 token 为空/不存在。窗口长的特征要相应加长暖机（1 天特征要 24 小时）。
- **tk07**：`patrol.py --day <纽约日>` 一条命令出巡检页；`--no-query` 只用已有结果重排版面。
- **tk08**：参数 `strategy_id`、`hit_list`、`sms_only`（1 = 短信口径）；`group` 行按最终结果拆，`cidgeo` 行给 cid × 国家组内的去重手机号。国家比较用 `CAST(... AS BINARY)`，空值视为空字符串。
- **tk09**：参数 `min_version_num`（1.4.30 → 1004030）；版本不是 `a.b.c` 形式的归入 `no_version`。
- **tk10**：参数 `strategy_id`、`switch_utc`（操作日志里状态变化的 UTC 时刻）、`reject_names`（带引号的列表，如 `'REJECT'`）；`s_online_only_reject` = 在线命中且无其它在线 REJECT 类命中，`s_preonline_no_online_reject` = 预上线命中且无在线 REJECT 类命中。
- **tk11**：参数 `strategy_id`、`target_ccs`（从配置导出里这条策略的 countryCode INCLUDE 规则读，不手写）、`us_values`（美国在 `realIpCountry` 里的取值，如 `'美国'`）、`sms_only`；`ip_class`：unknown / us / eq_phone（IP 国家 = 号码国家）/ other；`s_hit`：online / preonline / none。

## 6. 本包（2026-10-10）对 Part 4 原文的改动

本目录 22 个文件：Part 4 的 19 个（按原文写入后核对 sha256，19/19 一致；之后只改了 `shard_runner.py` 与 `README.md` 两个，其余 17 个未改，`privacy_allowlist.txt` 也未改）+ 2026-09-27 包原样带来的 `privacy_scan.py`、`ny_day_bounds.py` + 新模板 `tk11_bypass_watch.sql`。

| 文件 | 改动 | 原因 |
|---|---|---|
| `shard_runner.py` | 新增 `prod_window_ok()`：命令开始时先检查一次（不在窗口就记一行日志后退出，什么也不发），之后每条语句发送前再检查；纽约时间不在 22:00–05:30 就不发送 | 团队 2026-10-08 规定生产库批量取数只在纽约时间 22:00–06:00；05:30 留 30 分钟余量 |
| `shard_runner.py` | EXPLAIN 门槛：`Extra` 为 `No matching min/max row`、`Impossible WHERE` 或 `no matching row in const table`（窗口内没有行、什么也不扫）时当作「空」放行；`type = ALL` 的大表扫描仍拒绝；`run` 按窗口逐个 EXPLAIN，直到遇到一个正常走索引的窗口为止（第一个窗口为空时不再只看它） | 2026-09-27 安静时段的新鲜度检查曾被门槛误拦；只看第一个窗口会在它为空时漏检后面的窗口 |
| `tk11_bypass_watch.sql` | 新模板；短信判定与其它模板一致（`COALESCE(JSON_UNQUOTE(JSON_EXTRACT(para,'$.email')),'') = ''`），对齐后两种口径（`sms_only=1/0`）在纽约日 10-02…10-09 重跑，与 E1 逐格一致 | 备份同学每天盯 10-08 新策略有没有被绕过 |
| `README.md` | 本节、§1 的 tk11 一行、§4 测试表、§5 的 tk11 要点 | 记录改动 |

改动后自测：`test_guard.py` 仍为 27 + 13 条、0 失败；EXPLAIN 门槛三种情况（走索引 → 通过、空区间 → 「空」、全表扫描 → 拒绝）都按预期。
