# RC_data_20260926-1722 — 北美风控数据包（数据层）

> 给桌面项目 D1 导入、生成《北美风控数据字典与取数手册》（LCNA-RC-2026-004）用。全程只读，未写任何数据库。
> 所有数字来自本次会话执行的查询：SQL 在 `sql/`，原始结果在 `results/`，本地汇总脚本在 `sql/local/`。

## 1. 运行信息

| 项 | 值 |
|---|---|
| 运行日期 | 2026-09-26（America/New_York），17:22 开始 |
| 数据窗口 | 近 7 日 = 纽约日 2026-09-19…2026-09-25，UTC `[2026-09-19 04:00, 2026-09-26 04:00)`；E1 另含 2026-09-18 暖机日 |
| 其它窗口 | DR-003 纽约日 2026-08-25…09-25；DR-010 2026-06-01…09-25；DR-024 2026-08-25…09-24；DR-025 UTC 2026-09-06…09-27；DR-007 UTC 日 2026-08-25 起；复现基准 UTC `[2026-08-21 20:09, 2026-09-10 20:09)` |
| 数据模式 | 脚本执行（`toolkit/shard_runner.py`，经 MCP server `mcp-db-gateway` 的 `mysql_query`）；MCP 直调用于校验（8/8 行一致） |
| 数据库 | `aws-luckyus-iriskcontrolservice-rw`（MySQL 8.4.9，**主库**，账号只有 SELECT/PROCESS/EXECUTE）；upush `aws-luckyus-upush-rw` 只读了一张按日汇总表；元数据另查了全部 64 个 MySQL + 1 个 PG |
| 执行量 | 102 次运行、3,752 条分片语句（`results/_runlog.csv`、`results/timing.csv`）；单条最长 7.67 s，无超时 |
| DR 清单 | 用户在运行中提供的 `DATA_REQUESTS.md`（2026-09-26 版，未放在运行目录）；开始时按提示词附录 A 执行，收到后按清单补齐（见 RUN_LOG） |

## 2. 做了什么

| 文件 | 内容 |
|---|---|
| `00_环境清单.md` | MCP server、库、权限、主从、批量大小测试、Redis 规模、Grafana 面板 SQL |
| `01_数据源与表清单.md` + `dictionary/` | 风控库全部表（角色、规模、字段、索引）、JSON 结构、字段口径、字段注释与数据不符之处、全量名字扫描 |
| `02_线上配置导出.md` + `results/config_*.csv` | 17 张定义表整表导出（自由文本整值屏蔽、操作人屏蔽）、状态语义、名单条数（含按场景）、操作日志时间线 |
| `03_近7日数据画像_20260925.md` | 短信按日 / 区号 / 去重用户 / cid×app / 策略 / 泄漏 / 返回码 / H5 A2 链路 / 常设项 DR-016–018 |
| `04_数据问题结论.md` | 每个 DR 一节（锚点 `dr-xxx`） |
| `05_取数手册与常见坑.md` | 口径、JSON 路径、批量与速度、坑 |
| `06_评估指标计算手册.md` | 调用量、用户量、同期、命中、额外召回、准确率、规则复核、巡检、tk08/tk09、OTP 回填率 |
| `toolkit/` | 执行器、守卫、9 个模板（tk01–tk09，新增 tk08/tk09）、合并脚本、巡检、隐私扫描；测试 44/44 项一致 |

## 3. 主要发现

| # | 发现 | 数字 | 结果文件 |
|---|---|---|---|
| 1 | 近 7 日短信请求近一半被拦，放行里过半是非 +1 号码，最后两天明显回落 | 29,450 次：PASS 15,424 / REJECT 13,949 / REVIEW 77；PASS 中非 +1 占 51.1%；2026-09-24、2026-09-25 非 +1 占比降到 33.9%、29.7% | `results/p3_daily_result.csv`、`results/p3_pass_by_ccgroup.csv` |
| 2 | 分片键因场景而异（DR-021） | push / register / captcha = 完整手机号（2026-09-19 100.0%、2026-09-22 100.0%、2026-09-25 100.0%）；grant_new_user_coupon、login、payment、physical_order_cancel、physical_order_create = `userNo`（三天均 100%） | `results/dr021_best_candidate.csv`、`results/dr021_summary.csv` |
| 3 | App 确实收到过 REVIEW；REVIEW_18_ICON 全部来自 1.4.30 以下版本（DR-024） | REVIEW_18_ICON 65 次（2026-08-25…2026-09-02）全部 <1.4.30；09-16/17 App 的 REVIEW 类引擎结果 27 次，全部 ≥1.4.30，其中最终返回 REVIEW 14 次 | `results/dr024_engine_vs_final.csv`、`results/dr024_app_review_by_day.csv` |
| 4 | upush 回填统计表从 2026-09-21 起漏记绝大部分 +1 发送（DR-007） | +1「统计发送 / 风控放行」09-20 以前 0.84–0.94，09-22…09-25 0.06–0.08；base UTC 2026-08-25..2026-09-20 +1 回填率 95.9%，+86 93.0%，+92 0.2% | `results/dr007_daily_ccgroup.csv`、`results/dr007_fill_rate_by_cc.csv` |
| 5 | 组合维度特征仍取不到值；`e1Kmz7JqzsWc` 修好后引用它的策略才开始命中（DR-003 / DR-004 / DR-025） | 2026-09-25 两个组合维度特征 DIMENSION_EMPTY 5,340/5,340；`strategy_NrsClIxvGxWc` 首次命中在特征修好之后 | `results/dr003_codes_daily_pivot.csv`、`results/dr025_hourly_summary.csv` |
| 6 | `strategy_AxAlIdejVA8m` 改写前的时间窗不可能成立（DR-025） | 改写前（原条件「时间 >22:00 且 <05:00」）命中 0 次；2026-09-14 03:12 UTC 改为 02:00–09:00 后的第一个小时即开始命中；`strategy_43NaEzJmiQFk` 09-23 14:43 UTC 转上线前后命中干净切换 | `results/dr025_hourly_summary.csv`、`results/dr025_hourly_hits_43na.csv` |
| 7 | 攻击仍在持续（DR-010） | k=5 规则：2026-09-03 起 23 个攻击日（阈值 338.1/天非 +1/+86 请求），最近一天仍超阈值 | `results/dr010_attack_rule.csv`、`results/dr010_daily_series.csv` |
| 8 | 105 无 app 的请求全部自报 1.4.30 以下版本、不带 token（DR-012） | 无 app 1,905 次：≥1.4.30 占 0.0%、带 token 0.0%；有 app 19,975 次：≥1.4.30 占 99.5% | `results/dr012_cid105_app_vs_noapp_summary.csv` |
| 9 | 引擎 REVIEW 仍有一部分被改写为 PASS，全部在 H5（DR-016） | 7 日引擎 REVIEW 179 次中 102 次返回 PASS | `results/dr016_summary_7d.csv` |
| 10 | 仍有 REJECT 策略排在白名单之前（DR-017） | `strategy_sw3jC7bvFYEX` 优先级 100001，7 日在线命中 50 | `results/dr017_reject_above_whitelist.csv` |
| 11 | 预上线里额外召回最大的是 PASS 类 `strategy_GbsajBR69can`；非 PASS 类是 `strategy_MGj5bfGOijOi`、`strategy_x37TInaHsvPQ` | `strategy_MGj5bfGOijOi` 4,022 次（非 +1 4,022）；`strategy_x37TInaHsvPQ` 2,573 次（非 +1 2,573） | `results/p3_strategies.csv` |
| 12 | LKUS_captcha 与短信 REVIEW 的对应（DR-026） | 按手机号：REVIEW 15/15 能对上；captcha 15/15 行 | `results/dr026_match_summary.csv` |
| 13 | 团队手册复现基准可复现 | rows_no_cc_filter 64,935；rows_cc_filter 64,935（基准 64,931，差 +4）；pass_cc_filter 41,632（基准 41,629，差 +3）；reject_cc_filter 23,122（基准 23,121，差 +1）；review_cc_filter 181（基准 181，差 +0） | `results/p5_checkpoint_summary.csv` |

## 4. 数字溯源（表头数字）

| 数字 | SQL | 本地脚本 | 结果 |
|---|---|---|---|
| 7 日短信请求与结果（29,450；全部 LKUS_push 29,482） | `sql/e1_a.sql`、`sql/e1_b.sql`；纯 SQL 核对 `sql/p4_daily_series.sql` | `sql/local/p3_profile.py` | `results/p3_daily_result.csv`、`results/p3_crosscheck.csv`（0 个不一致单元格） |
| 非 +1 放行 51.1% | 同上 | 同上 | `results/p3_pass_by_ccgroup.csv` |
| 7 日去重手机号 13,599 / uid 8,948 | `sql/e1_*.sql` | `sql/local/p3_profile.py` | `results/p3_distinct_users.csv` |
| 策略命中与额外召回 | `sql/p2_hits_7d.sql`；`sql/e1_*.sql` | `sql/local/p3_profile.py` | `results/p2_hits_7d.csv`、`results/p3_strategies.csv` |
| DR-003 / DR-004 返回码 | `sql/dr003_codes_daily.sql` | `sql/local/p4_agg_drs.py` | `results/dr003_codes_summary.csv`、`results/dr003_codes_daily_pivot.csv` |
| DR-007 回填 | `sql/dr007_upush_daily.sql`、`sql/dr007_risk_utc_daily.sql` | `sql/local/p4_agg_drs.py`、`sql/local/p4_new_drs.py` | `results/dr007_*.csv` |
| DR-010 攻击日 | `sql/p4_daily_series.sql` | `sql/local/p4_agg_drs.py` | `results/dr010_*.csv` |
| DR-012 / 016 / 017 / 018 / 023 | `sql/e1_*.sql`、`sql/p2_hits_7d.sql` | `sql/local/p4_new_drs.py` | `results/dr012_*.csv`、`results/dr016_*.csv`、`results/dr017_*.csv`、`results/dr018_*.csv`、`results/dr023_*.csv` |
| DR-021 分片键 | `sql/dr021_sharding_key_by_scene*.sql` | `sql/local/p4_agg_drs.py` | `results/dr021_*.csv` |
| DR-022 午夜归日 | `sql/dr022_reject_per_minute.sql`、`sql/dr022_seconds_*.sql` | `sql/local/p4_agg_drs.py` | `results/dr022_*.csv` |
| DR-024 引擎 vs 最终 | `sql/dr024_engine_vs_final.sql` | `sql/local/p4_agg_drs.py` | `results/dr024_*.csv` |
| DR-025 改动前后命中 | `sql/dr025_hourly_hits.sql`、`sql/dr025_hourly_hits_43na.sql` | `sql/local/p4_agg_drs.py` | `results/dr025_*.csv` |
| DR-026 captcha 对应 | `sql/dr026_captcha_extract.sql`（本机）+ E1 | `sql/local/p4_new_drs.py` | `results/dr026_*.csv` |
| 配置条数 / 状态语义 / 操作日志 | `sql/config_*.sql`、`sql/p2_*.sql` | `sql/local/p2_config.py`、`sql/local/p2_oplog_timeline.py`、`sql/local/p2_list_by_scene.py` | `results/config_*.csv`、`results/p2_*.csv` |
| 复现基准 | `sql/p5_checkpoint*.sql` | `sql/local/p4_agg_drs.py` | `results/p5_checkpoint_summary.csv` |
| 工具包测试 | `sql/toolkit_tests/` | `sql/local/p5_toolkit_tests.py` | `results/toolkit_tests/_test_summary.csv` |
| 稳定性复跑 | 同原查询 | `sql/local/p7_stability.py` | `results/p7_stability.csv`（3/3 一致） |

## 5. 未取到的数据与原因

| 来源 | 状态 |
|---|---|
| Doris `ods_luckyus_iriskcontrol.t_iriskcontrol_log` | 未能获取：Doris 不可达（gateway 无 `ods_*` 库；`grafana-lucky` 有数据源但没有 SQL 查询工具，DR-020） |
| Redshift | 未能获取：`redshift` MCP `list_clusters` 报错 |
| Redis `luckyus-iriskcontrol` 内容 | 只执行了 `DBSIZE` / `INFO keyspace`（§3 允许的范围） |
| upush 其它表（逐条发送 / 回填） | 只读元数据；§3.2 只放开 `t_verifycode_filled_statistics` 的按日聚合 |
| 桌面项目文件与 `_inbox/` | 本机不存在：未读取；zip 通过交接仓库与手工复制送达 |

## 6. DR 汇总

| DR | 新状态 | 一句话 |
|---|---|---|
| [DR-002](04_数据问题结论.md#dr-002) | 部分答复（本次受阻：Doris 不可达，见 DR-020） | 规则不变（email 非空 → 邮件）；7 日 32 行带 email；与 `l2_scene` 对照仍受阻于 Doris |
| [DR-003](04_数据问题结论.md#dr-003) | 已答复 | e1K 条件为空致 PARAMS_ERROR 至 09-24 07:24 UTC 已修；dqBH 09-24 去掉条件；组合维度仍 DIMENSION_EMPTY |
| [DR-004](04_数据问题结论.md#dr-004) | 已答复 | 仍未修好：2026-09-25 DIMENSION_EMPTY 5,340/5,340，未重估 |
| [DR-007](04_数据问题结论.md#dr-007) | 待确认（问人：陈晨昕） | base 期 +1 回填率 95.9%、攻击区号≈0；统计表 09-21 起漏记约九成 +1 发送；OTP 口径只能按区号折算 |
| [DR-010](04_数据问题结论.md#dr-010) | 已答复 | k=5：2026-09-03 起 23 个攻击日，仍在持续；攻击日 +1 放行日均与非攻击月同量级 |
| [DR-012](04_数据问题结论.md#dr-012) | 待确认（问人：林宏鹏） | 有 app 的 105 99.5% ≥1.4.30；无 app 的全部 <1.4.30、无 token；1.3.50 是否存在待林宏鹏 |
| [DR-013](04_数据问题结论.md#dr-013) | 已答复 | Doris 仍不可达（gateway 无 ods_*；Grafana MCP 无 SQL 工具） |
| [DR-014](04_数据问题结论.md#dr-014) | 已答复 | 仍成立（2026-09-25 抽查 100%）；uid 跨分片 |
| [DR-015](04_数据问题结论.md#dr-015) | 已答复 | 17 张定义表 + 名单按类型 × 场景 × 来源计数 + 操作日志时间线已导出 |
| [DR-016](04_数据问题结论.md#dr-016) | 待确认（问人：林宏鹏） | 7 日引擎 REVIEW 179 次中 102 次返回 PASS（全部 H5） |
| [DR-017](04_数据问题结论.md#dr-017) | 待确认（问人：段枝宏、田志鲔） | `strategy_sw3jC7bvFYEX` 优先级 100001 仍上线、7 日 50 次 |
| [DR-018](04_数据问题结论.md#dr-018) | 待确认（问人：田志鲔） | 3 条策略用 UTC 时刻规则（上线 1、预上线 2） |
| [DR-020](04_数据问题结论.md#dr-020) | 已答复 | 不能：Grafana MCP 无 SQL 工具；需数据平台开 Doris 只读账号 |
| [DR-023](04_数据问题结论.md#dr-023) | 已答复 | 新模板 tk08 + 7 日全量表（去重手机号行内精确） |
| [DR-021](04_数据问题结论.md#dr-021) | 已答复 | push / register / captcha 按完整手机号，login / payment / 下单 / 取消 / 新人券按 userNo，三天均 100% |
| [DR-022](04_数据问题结论.md#dr-022) | 部分答复（本次受阻：Doris 不可达，见 DR-020） | 源库午夜前后 10 分钟 REJECT 18 / 29 次；Doris 一侧待 DR-020 |
| [DR-024](04_数据问题结论.md#dr-024) | 已答复 | REVIEW_18_ICON 65 次全部 <1.4.30；09-16/17 App REVIEW 类 27 次（≥1.4.30） |
| [DR-025](04_数据问题结论.md#dr-025) | 已答复 | AxAl 改写前 0 次（原时间窗不可能成立）；NrsCl 至特征修好后才命中；bTCE 前后无明显跳变 |
| [DR-026](04_数据问题结论.md#dr-026) | 已答复 | 按手机号对上 15/15 个 REVIEW；captcha 15/15 行 |

合计（由脚本从 04 的「新状态」行计算）：已答复 12、待确认 5、部分答复 2（共 19 条）。
本轮未处理（沿用 `DATA_REQUESTS.md` 的状态）：DR-001 待确认（问人：林宏鹏）、DR-005 已答复、DR-006 已答复、DR-008 已答复、DR-009 已答复、DR-011 已答复、DR-019 待确认（问人：林宏鹏）。

## 7. 事实更正候选（提示词 §2 / 附录 A / `DATA_REQUESTS.md` 与数据不符之处）

| 原说法 | 数据显示 | 证据 |
|---|---|---|
| 提示词 §2.4「Sharding key: `CONCAT(country_code, phone)`」（未区分场景） | 只对 push / register / captcha 成立；login、payment、下单、取消、新人券的分片键是 `userNo`（三个抽查日均 100%） | DR-021，`results/dr021_best_candidate.csv` |
| 提示词 §2.3「App 不能 REVIEW；7 日到 09-24 所有 REVIEW 都来自 H5」 | 最近 7 日（09-19…09-25）仍然全部来自 H5；但 09-16/17 有 1.4.30 以上版本的 App 请求被引擎判 `REVIEW_15_NINE`、部分最终返回 REVIEW，08-25…09-02 的 `REVIEW_18_ICON` 全部来自 1.4.30 以下版本 | DR-024，`results/dr024_app_review_by_day.csv` |
| 提示词 §2.2「一个带条件的累计特征 11 天 PARAMS_ERROR」 | 已在 2026-09-24 07:24 UTC 修好（补上条件），此后该特征返回 SUCCESS / CONDITION_MISS；引用它的 `strategy_NrsClIxvGxWc` 从此开始命中 | DR-003、DR-025，`results/dr003_codes_daily_pivot.csv`、`results/dr025_hourly_summary.csv` |
| 附录 A DR-004「组合维度修好后重估」 | 2026-09-25 仍 100% `DIMENSION_EMPTY`，条件不满足 | DR-004 |
| `DATA_REQUESTS.md` DR-015 答复「名单只按租户计数」 | 名单表没有场景列；本轮经名单特征映射到场景：LKUS 只有手机号黑名单与 IP C 段白名单有条目，其余名单特征对应 0 条 | `results/p2_list_counts_by_scene.csv` |
| `DATA_REQUESTS.md` DR-007「汇总表最适合做误伤核对」 | 2026-09-21 起统计表只记下约 7% 的 +1 发送（此前约 92%），这些日子不能用来算回填率；09-20 以前可用 | DR-007，`results/dr007_daily_ccgroup.csv` |
| 上一轮包 `sql/p1_sk_transition_hourly.sql` 注释「分片键变化的小时」 | 2026-08-18 变化的是请求参数新增 `fullPhoneNo`，分片键规则没有变（本包的该 SQL 注释已改正） | `results/p1_sk_transition_hourly.csv` |
| 提示词 §2.4 `t_scene`「估算 31 行」 | 实际导出 32 行（information_schema 估算不精确） | `results/config_legacy_scene.csv`、`results/p0_schema_tables.csv` |
| 库内字段注释（`t_rms_engine_rule.rule_id`「特征ID」、`t_rms_engine_para.para_id/para_name`「场景ID/场景名称」、`t_rms_engine_tool.tool_type` 3=累计特征工具） | 与数据不符（仍未改） | `results/p1_comment_vs_data.csv` |

## 8. 建议的后续分析

1. **DR-020 开通 Doris 只读账号后**：先出 `l2_scene` × 是否带 email × 纽约日计数（DR-002），再按 `access_time` 复算 DR-022 的午夜窗口。
2. **OTP 硬标签**：在允许范围内放开 `t_sent_verifycode_sms` / `t_collect_verifycode` 的逐行关联（加盐哈希、只在本机），把预上线策略的额外召回与误伤换成逐请求口径；09-21 起统计表的缺口要推送团队先修回执。
3. **上线前核误伤**：会打到 +1 号码的预上线策略（`03` §5.2 与 `results/dr007_otp_basis.csv` 里折算回填占比高的）逐条用 tk03 + OTP 口径复核。
4. **组合维度特征修好后**：用 tk02 / tk03 重估 `strategy_tO7DZkJ1g0C2`（DR-004）。
5. **2026-11-01 夏令时结束前**：复核 UTC 02:00–09:00 时刻规则（DR-018）。
6. **非 push 场景的取数**：按 `userNo` 分片（DR-021）；去重手机号不能按分片相加，要行级抽取在本地去重。

## 9. 交接

- zip：`RC_data_package_20260926-1722.zip`（+ `.sha256`）在运行目录；同时推送到交接仓库 `lcna-riskcontrol-data-package`（桌面 D1 接受仓库归档 `<repo>-main.zip`）。
- 桌面 `_inbox/` 不在本机：请把 zip 放进桌面项目的 `_inbox/`，然后在桌面跑 D1。
