# toolkit — 北美风控取数工具包

> 2026-09-27 更新。每个模板都用本包数据跑过一次，并与另一种算法（E1 本地抽取或独立 SQL）逐项核对：55/55 项一致（`results/toolkit_tests/_test_summary.csv`）。
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

## 4. 本次测试（多数为纽约日 2026-09-20…09-26；tk01 另含 09-19 这一同期窗口，tk06 / tk07 / tk09 为 09-26，tk10 为 DR-027 窗口 09-19…09-26；挑选的策略来自数据：PRE=`strategy_GbsajBR69can`、PRE_PASS_CLASS=`1`、ON=`strategy_REnWrA7CfCdE`、TK06=`strategy_lf6DsxMdAPzy`）

| 测试 | 模板结果 | 对照 | 一致 | 备注 |
|---|---|---|---|---|
| tk01 2026-09-19 requests (all push rows) vs p4_daily_series | 5391 | 5391 | 是 |  |
| tk01 2026-09-20 requests (all push rows) vs p4_daily_series | 3551 | 3551 | 是 |  |
| tk01 2026-09-20 SMS distinct phones vs E1 | 1985 | 1985 | 是 |  |
| tk01 2026-09-20 SMS PASS +1 distinct phones vs E1 | 651 | 651 | 是 |  |
| tk01 2026-09-21 requests (all push rows) vs p4_daily_series | 4738 | 4738 | 是 |  |
| tk01 2026-09-21 SMS distinct phones vs E1 | 2525 | 2525 | 是 |  |
| tk01 2026-09-21 SMS PASS +1 distinct phones vs E1 | 980 | 980 | 是 |  |
| tk01 2026-09-22 requests (all push rows) vs p4_daily_series | 5144 | 5144 | 是 |  |
| tk01 2026-09-22 SMS distinct phones vs E1 | 2719 | 2719 | 是 |  |
| tk01 2026-09-22 SMS PASS +1 distinct phones vs E1 | 999 | 999 | 是 |  |
| tk01 2026-09-23 requests (all push rows) vs p4_daily_series | 4691 | 4691 | 是 |  |
| tk01 2026-09-23 SMS distinct phones vs E1 | 2643 | 2643 | 是 |  |
| tk01 2026-09-23 SMS PASS +1 distinct phones vs E1 | 1060 | 1060 | 是 |  |
| tk01 2026-09-24 requests (all push rows) vs p4_daily_series | 3225 | 3225 | 是 |  |
| tk01 2026-09-24 SMS distinct phones vs E1 | 1845 | 1845 | 是 |  |
| tk01 2026-09-24 SMS PASS +1 distinct phones vs E1 | 962 | 962 | 是 |  |
| tk01 2026-09-25 requests (all push rows) vs p4_daily_series | 2742 | 2742 | 是 |  |
| tk01 2026-09-25 SMS distinct phones vs E1 | 1682 | 1682 | 是 |  |
| tk01 2026-09-25 SMS PASS +1 distinct phones vs E1 | 940 | 940 | 是 |  |
| tk01 2026-09-26 requests (all push rows) vs p4_daily_series | 2792 | 2792 | 是 |  |
| tk01 2026-09-26 SMS distinct phones vs E1 | 1391 | 1391 | 是 |  |
| tk01 2026-09-26 SMS PASS +1 distinct phones vs E1 | 643 | 643 | 是 |  |
| tk02 strategy_GbsajBR69can pre-online PV 7d vs p2_hits_7d | 17834 | 17834 | 是 |  |
| tk02 2026-09-20 strategy_GbsajBR69can distinct phones vs E1 | 1328 | 1328 | 是 |  |
| tk02 2026-09-21 strategy_GbsajBR69can distinct phones vs E1 | 1886 | 1886 | 是 |  |
| tk02 2026-09-22 strategy_GbsajBR69can distinct phones vs E1 | 2110 | 2110 | 是 |  |
| tk02 2026-09-23 strategy_GbsajBR69can distinct phones vs E1 | 2027 | 2027 | 是 |  |
| tk02 2026-09-24 strategy_GbsajBR69can distinct phones vs E1 | 1469 | 1469 | 是 |  |
| tk02 2026-09-25 strategy_GbsajBR69can distinct phones vs E1 | 1336 | 1336 | 是 |  |
| tk02 2026-09-26 strategy_GbsajBR69can distinct phones vs E1 | 1112 | 1112 | 是 |  |
| tk03 strategy_GbsajBR69can extra recall PV 7d vs E1 (all push rows; pass_class=1) | 6266 | 6266 | 是 |  |
| tk02 strategy_GbsajBR69can pre-online PV 7d, sms_only=1, vs E1 SMS | 17802 | 17802 | 是 |  |
| tk02 2026-09-20 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1328 | 1328 | 是 |  |
| tk02 2026-09-21 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1884 | 1884 | 是 |  |
| tk02 2026-09-22 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 2109 | 2109 | 是 |  |
| tk02 2026-09-23 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 2027 | 2027 | 是 |  |
| tk02 2026-09-24 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1464 | 1464 | 是 |  |
| tk02 2026-09-25 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1331 | 1331 | 是 |  |
| tk02 2026-09-26 strategy_GbsajBR69can distinct phones, sms_only=1, vs E1 SMS | 1110 | 1110 | 是 |  |
| tk03 strategy_GbsajBR69can extra recall PV 7d, sms_only=1, vs E1 SMS (pass_class=1) | 6265 | 6265 | 是 |  |
| tk04 non-+1 SMS PASS rows 7d vs E1 | 6848 | 6848 | 是 |  |
| tk04 non-+1 SMS PASS ip_country=美国 vs E1 | 2998 | 2998 | 是 |  |
| tk04 non-+1 SMS PASS token_state=absent vs E1 | 644 | 644 | 是 |  |
| tk04 non-+1 SMS PASS cid=105 vs E1 | 6496 | 6496 | 是 |  |
| tk05 score-bucket cells (cc group x cid x bucket) equal to E1 | 37 | 37 | 是 | 37 cells |
| tk06 strategy_lf6DsxMdAPzy hits on NY 2026-09-26 vs p2_hits_7d | 10 | 10 | 是 | re-check output (not a test): violations 0/10; engine==recompute 0.9449, within1 0.9872 |
| tk06 strategy_lf6DsxMdAPzy SMS hits on NY 2026-09-26 (email_nonempty=0) vs E1 SMS | 10 | 10 | 是 | re-check output (not a test): SMS violations 0/10 |
| tk07 2026-09-26 SMS PASS vs E1 | 1328 | 1328 | 是 |  |
| tk07 2026-09-26 SMS REJECT vs E1 | 1455 | 1455 | 是 |  |
| tk07 2026-09-26 SMS REVIEW vs E1 | 6 | 6 | 是 |  |
| tk07 2026-09-26 online hit PV per strategy equal to p2_hits_7d | 23 | 23 | 是 | 23 strategies |
| tk08 strategy_REnWrA7CfCdE PV cells (day x cid x geo) equal to E1 | 22 | 22 | 是 | 22 cells |
| tk08 strategy_REnWrA7CfCdE distinct-phone cells equal to E1 | 22 | 22 | 是 | 22 cells |
| tk09 2026-09-26 SMS engine x final cells equal to E1 | 4 | 4 | 是 | 4 cells |
| tk10 strategy_43NaEzJmiQFk unique-REJECT cells equal to E1 (DR-027 window) | 348 | 348 | 是 | 348 cells |

测试原始输出：`results/toolkit_tests/`；每个测试实际执行的 SQL：`sql/toolkit_tests/`；比对脚本 `sql/local/p5_toolkit_tests.py`。

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
