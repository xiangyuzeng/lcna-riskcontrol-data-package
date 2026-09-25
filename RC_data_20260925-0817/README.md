# RC_data_20260925-0817 — 北美风控数据包（数据层）

> 给桌面项目 D1 导入、生成《北美风控数据字典与取数手册》（LCNA-RC-2026-004）用。全程只读，未写任何数据库。
> 所有数字来自本次会话执行的查询：SQL 在 `sql/`，原始结果在 `results/`，本地汇总脚本在 `sql/local/`。

## 1. 运行信息

| 项 | 值 |
|---|---|
| 运行日期 | 2026-09-25（America/New_York），08:17 开始；10:42–11:55 按用户要求暂停后续跑 |
| 数据窗口 | 近 7 日 = 纽约日 2026-09-18…2026-09-24，UTC `[2026-09-18 04:00, 2026-09-25 04:00)`；E1 另含 09-17 暖机日 |
| 其它窗口 | DR-001 2026-08-25…09-24；DR-003/005 2026-08-20…09-24；DR-010 2026-06-01…09-24；复现基准 UTC `[2026-08-21 20:09, 2026-09-10 20:09)` |
| 数据模式 | 脚本执行（`toolkit/shard_runner.py`，经 MCP server `mcp-db-gateway` 的 `mysql_query`）；MCP 直调只用于校验（9/9 行一致） |
| 数据库 | `aws-luckyus-iriskcontrolservice-rw`（MySQL 8.4.9，**主库**，账号只有 SELECT/PROCESS/EXECUTE）；元数据另查了全部 64 个 MySQL + 1 个 PG |
| 执行量 | 约 100 次运行、4,000 余条只读语句（`results/_runlog.csv`、`results/timing.csv`）；单条最长 5.96 s，无超时 |

## 2. 做了什么

| 文件 | 内容 |
|---|---|
| `00_环境清单.md` | MCP server、库、权限、主从、批量大小测试、保护规则 |
| `01_数据源与表清单.md` + `dictionary/` | 风控库全部表（角色、规模、字段、索引）、JSON 结构、字段口径、全量名字扫描 |
| `02_线上配置导出.md` + `results/config_*.csv` | 16 张引擎配置表整表导出（自由文本整值屏蔽）、状态语义实测、名单条数、操作日志时间线 |
| `03_近7日数据画像_20260924.md` | 短信按日/区号/cid×app/策略/泄漏/计数特征返回码/H5 A2 链路 |
| `04_数据问题结论.md` | DR-001…DR-015 + DR-NEW-1…4（每条带锚点 `dr-xxx`） |
| `05_取数手册与常见坑.md` | 口径、JSON 路径、批量与速度、坑 |
| `06_评估指标计算手册.md` | 调用量、用户量、同期、命中、额外召回、准确率、规则复核 |
| `toolkit/` | 执行器、守卫、7 个已测试模板（tk01–tk07）、合并脚本、巡检、隐私扫描；见 `toolkit/README.md` |

## 3. 主要发现

| # | 发现 | 数字 | 结果文件 |
|---|---|---|---|
| 1 | 近 7 日短信请求近一半被拦，放行里过半是非 +1 号码 | 31,807 次：PASS 16,478 / REJECT 15,267 / REVIEW 62；PASS 中非 +1 占 53.4% | `results/p3_daily_result.csv`、`results/p3_pass_by_ccgroup.csv` |
| 2 | 带过滤条件的累计特征**过滤是生效的**；真正的故障是 `feature_e1Kmz7JqzsWc` 条件列表为空 | 与过滤后重算吻合 88.5%–99.2%；e1K 在 09-13…09-24 07:24 UTC 100% `PARAMS_ERROR`，`strategy_NrsClIxvGxWc` 修复前 0 命中、修复后 54 | `results/dr003_conditional_vs_recompute.csv`、`results/dr003_long.csv`、`results/dr003_nrscl_gate_check.csv` |
| 3 | 组合维度 `realIp\|phoneNo` 从改配置起取不到值 | 自 2026-09-20 02:39 UTC 起 100% `DIMENSION_EMPTY`；`strategy_tO7DZkJ1g0C2` 此前 1,010 命中、此后 0 | `results/p3_counter_codes_daily.csv`、`results/p2_oplog_changes.csv` |
| 4 | 在线 PASS 与在线 REJECT 从不同时命中：PASS 命中即停；一条 REJECT 策略排在白名单之上 | 31 天 375 次冲突全部是 REJECT+REVIEW（REJECT 375/375）；PASS 命中的 2,314 次全部单命中；`strategy_sw3jC7bvFYEX` 优先级 100001 | `results/dr001_*.csv` |
| 5 | 时刻类规则按 UTC 比较，请求里从不带 `accessTime` | 36,753 次评估按 UTC 吻合 100%（±1 小时仅 92–94%） | `results/dr008_time_rule_offsets.csv` |
| 6 | 分片键是完整手机号；uid 跨分片 | 全部 LKUS_push 行：14,119 个手机号 0 个跨分片；9,069 个 uid 中 1,932 个跨分片 | `results/p3_dr014_shard_spread.csv`、`results/p1_sk_concat_check_*.csv` |
| 7 | 预上线里额外召回最大的是 `MGj5bfGOijOi` / `x37TInaHsvPQ`，全部是非 +1 | 4,517 / 2,872 次（7 日） | `results/p3_strategies.csv` |
| 8 | 105 且无 app 的请求疑为伪造旧版本 | 2,289 次，99.2% 自报 1.3.50、98.4% 非 +1、无 token | `results/dr012_*.csv` |
| 9 | cid 702 是自助机 | `SELF_SERVICE_MACHINE_US`，7 日 518 次全部放行 | `results/dr006_*.csv` |
| 10 | 团队手册复现基准可复现 | 64,931/41,629/23,121/181 → 64,935/41,632/23,122/181（边缘 10 分钟有 16/21 行） | `results/p5_checkpoint*.csv` |

## 4. 数字溯源（表头数字）

| 数字 | SQL | 本地脚本 | 结果 |
|---|---|---|---|
| 7 日请求与结果（31,832 / 31,807） | `sql/e1_a.sql`、`sql/e1_b.sql`；纯 SQL 核对 `sql/p4_daily_series.sql` | `sql/local/p3_profile.py` | `results/p3_daily_result.csv`、`results/p3_crosscheck.csv`（0 不一致） |
| 非 +1 放行 53.4% | 同上 | 同上 | `results/p3_pass_by_ccgroup.csv` |
| 去重手机号 14,109 / uid 9,059 | `sql/e1_*.sql` | `sql/local/p3_profile.py` | `results/p3_distinct_users.csv` |
| 策略命中与额外召回 | `sql/p2_hits_7d.sql`；`sql/e1_*.sql` | `sql/local/p3_profile.py` | `results/p2_hits_7d.csv`、`results/p3_strategies.csv` |
| DR-001 375 次冲突、2,314 次单命中 | `sql/dr001_conflicts.sql` | `sql/local/p4_dr001.py` | `results/dr001_*.csv` |
| DR-003 88.5%–99.2% 与 PARAMS_ERROR | `sql/dr003_long.sql`、`sql/e1_*.sql`、`sql/p2_oplog_changes.sql` | `sql/local/p4_dr003_recompute.py` | `results/dr003_*.csv` |
| DR-004 DIMENSION_EMPTY 100% | `sql/e1_*.sql`、`sql/p2_oplog_changes.sql` | `sql/local/p3_profile.py` | `results/p3_counter_codes_daily.csv` |
| DR-008 UTC 100% | `sql/e1_*.sql`（`time_rules_json`） | `sql/local/p4_dr_local.py` | `results/dr008_time_rule_offsets.csv` |
| DR-010 +1 放行日均 | `sql/p4_daily_series.sql` | `sql/local/p4_dr_local.py` | `results/dr010_*.csv` |
| 配置条数 / 状态语义 | `sql/config_*.sql`、`sql/p2_hits_7d.sql` | `sql/local/p2_config.py` | `results/config_*.csv` |
| 复现基准 64,935 | `sql/p5_checkpoint*.sql` | — | `results/p5_checkpoint*.csv` |
| 工具包测试 | `sql/toolkit_tests/` | `sql/local/p5_toolkit_tests.py` | `results/toolkit_tests/_test_summary.csv`（全部一致） |

## 5. 未取到的数据与原因

| 来源 | 状态 |
|---|---|
| Doris `ods_luckyus_iriskcontrol.t_iriskcontrol_log` | 未能获取：Doris 不可达（本会话没有 MCP server 连 Doris；64 个 MySQL 上也没有 `ods_*` 库） |
| Redshift | 未能获取：`redshift` MCP `list_clusters` 报错 |
| Redis `luckyus-iriskcontrol` 内容 | 未查询：§3 只允许 SQL 只读语句；只记录实例名 |
| upush 短信验证码回填**数据** | 用户选择严格范围：只读了元数据（DR-007 部分答复） |
| `t_oplog` 数据 | 无时间索引、内容为名单条目：只读元数据 |
| 桌面项目文件与 `_inbox/` | 不在本机：未读取，zip 需要手工复制 |
| `DATA_REQUESTS.md` | 运行目录没有：DR 清单用提示词附录 A |

## 6. DR 汇总

| DR | 新状态 | 一句话 |
|---|---|---|
| DR-001 | 部分答复 | 在线 PASS 与在线 REJECT 从未同时命中（PASS 命中即停）；冲突只有 REJECT+REVIEW，REJECT 375/375 |
| DR-002 | 部分答复 | 每行都带手机号，0.08% 另带 email；规则 `$.para.email` 非空 → 邮件候选，待 Doris `l2_scene` 对照 |
| DR-003 | 已答复 | 过滤生效；`e1Kmz7JqzsWc` 条件为空 → 11 天无值；`dqBHKec09Wwa` 09-24 被改为无条件 |
| DR-004 | 已答复 | 组合维度自 09-20 02:39 UTC 起 100% `DIMENSION_EMPTY`，`tO7DZkJ1g0C2` 失效 |
| DR-005 | 已答复 | 按 featureId 改名的只有 4 个；"reCAPTCHA 改名"是两个特征来回切换 |
| DR-006 | 已答复 | cid 702 = 自助机 |
| DR-007 | 部分答复 | 回填在 `luckyus_iupushsms.t_sent_verifycode_sms.filled` 等（只看元数据） |
| DR-008 | 已答复 | 时刻规则按 UTC 比较；请求不带 `accessTime` |
| DR-009 | 已答复 | 分数越高越像真人 |
| DR-010 | 已答复 | +1 放行攻击期日均 1,209（6 月 1,253、7 月 1,048）；k=5 规则把 09-03 起 22 天标为攻击日 |
| DR-011 | 已答复 | 攻击流量分数普遍偏高（非 +1/+86 Android 中位数 0.8，与 +1 Android 相同；均值 0.63 vs 0.77） |
| DR-012 | 部分答复 | 105 无 app 疑伪造 1.3.50；106 无 app 是真实旧版用户 |
| DR-013 | 已答复 | 只有 `mcp-db-gateway` 可达；主库；Doris 不可达 |
| DR-014 | 已答复 | 分片键 = 完整手机号 |
| DR-015 | 已答复 | 配置与名单表可读，已导出 / 计数 |
| DR-NEW-1…4 | 新问题（待取数） | REVIEW 被改写为 PASS；REJECT 排在白名单之上；时刻规则 UTC 写死遇夏令时；配置留痕只从 09-02 开始 |

合计：已答复 10、部分答复 4、无法用数据回答 0；新问题 4（D1 编号）。

## 7. 事实更正候选（提示词 §2 / 附录 A 与数据不符之处）

| 原说法 | 数据显示 | 证据 |
|---|---|---|
| §2.4 推送场景参数含 email、phoneNoHead7、phoneNoMd5、uuidKey、accessTime、shumeng/shumei/tongdun 设备号 | 请求里只带 13 个必有键 + recaptcha/reviewRepeat/app/userNo/email；其余是 `t_rms_engine_para` 的**配置**，请求里从不出现 | `results/p1_json_keys_summary.csv`、`results/config_para.csv` |
| §2.2"带过滤条件的累计特征不应用过滤" | 08-27…09-24 的日志里过滤都生效；问题是空条件列表与 09-24 去掉条件 | DR-003 |
| §2.4 featureDetail"约 20 KB/行" | LKUS_push 平均 11,911 B（整个引擎返回 27,304 B） | `results/p1_payload_size.csv` |
| §2.4"V3 分数取 `feature_TLXI8MNiNglz`" | 09-18 以前多次挂在 `feature_MHv7nra5Z6T5` 上；要按形状取 | DR-005、`results/p3_v3_fid_daily.csv` |
| §2.2"PASS 与 REJECT 同时命中时 PASS 胜"（DR-001 的前提） | 这种情况在日志里不发生：PASS 命中后不再执行其它策略；且有 REJECT 排在 PASS 之前 | DR-001、DR-NEW-2 |
| §2.3"App 不支持 REVIEW，REVIEW 在 105/106 等同拦截" | 7 日 REVIEW 全部来自 H5；引擎 REVIEW 类结果约一半最终返回 PASS | `results/p3_review_matrix.csv`、DR-NEW-1 |
| §2.4 `country_code` 带 `+` | 成立，且列与参数 100% 一致、没有不带 `+` 的写法 | `results/p1_chk_consistency.csv` |

## 8. 建议的后续分析

1. 拿到 upush 按日回填汇总（`t_verifycode_filled_statistics`，无个人信息）后，按区号把"额外召回"与"误伤"都换成 OTP 口径复算（DR-007）。
2. 请林宏鹏确认引擎短路规则与 REVIEW→PASS 改写条件，再重做 DR-001 / DR-NEW-1。
3. 11-01 夏令时结束前复核 02:00–09:00 UTC 时间窗（在线 `6cR0ThwOf1mO` 等，DR-NEW-3）。
4. 按"105 且无 app 且版本 1.3.50"建观察型策略，先测误伤（DR-012）。
5. 修好组合维度写法后，用 tk02 / tk03 重估 `strategy_tO7DZkJ1g0C2` 的额外召回（DR-004）。
