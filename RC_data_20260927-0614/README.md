# RC_data_20260927-0614 — 北美风控数据包（数据层）

> 给桌面项目 D1 导入、生成《北美风控数据字典与取数手册》（LCNA-RC-2026-004）用。全程只读，未写任何数据库。
> 所有数字来自本次会话执行的查询：SQL 在 `sql/`，原始结果在 `results/`，本地汇总脚本在 `sql/local/`；主要指标（50 项，含窗口与口径）登记在 `results/p6_metric_registry.csv`，其中带标签模式的由 `sql/local/p6_checks.py` 逐页核对。

## 1. 运行信息

| 项 | 值 |
|---|---|
| 运行日期 | 2026-09-27（America/New_York），06:14 开始 |
| 输入 | 提示词 M1（桌面 2026-09-26 第六轮修订版）与 `DATA_REQUESTS.md` 都**随对话消息内联提供**；`DATA_REQUESTS.md` = 桌面 2026-09-26 副本（28 条 DR，变更记录最后一条「2026-09-26（第六轮）」） |
| 数据窗口 | 近 7 日 = 纽约日 2026-09-20…2026-09-26；**DR-027 自己的窗口** = 纽约日 2026-09-19…2026-09-26；E1 行级抽取覆盖后者 |
| 其它窗口 | DR-010 纽约日 2026-06-01…2026-09-26；DR-014 纽约日 2026-09-26；操作日志 纽约日 2026-08-25 起；复现基准 UTC `[2026-08-21 20:09, 2026-09-10 20:09)` |
| 数据模式 | 脚本执行（`toolkit/shard_runner.py`，经 MCP server `mcp-db-gateway` 的 `mysql_query`）；MCP 直调用于校验 |
| MCP server | `mcp-db-gateway`（唯一的数据通道）；`grafana-lucky`（只读看板面板 SQL 与数据源元数据，没有执行 SQL 的工具）；`redshift`（只做可达性检查，`list_clusters` 报错） |
| 数据库 | `aws-luckyus-iriskcontrolservice-rw`（MySQL 8.4.9，**主库**，账号只有 SELECT/PROCESS/EXECUTE）；元数据另查了全部 64 个 MySQL + 1 个 PG |
| 执行量 | 97 次运行、3,390 条分片语句（`results/_runlog.csv`、`results/timing.csv`）；单条最长 5.01 s，无超时 |

## 2. 做了什么

| 文件 | 内容 |
|---|---|
| `00_环境清单.md` | 输入来源、MCP server、库、权限、主从、批量测试、别名守卫、Redis 规模 |
| `01_数据源与表清单.md` + `dictionary/` | 风控库全部表、JSON 结构、字段口径、字段注释与数据不符之处、全量名字扫描 |
| `02_线上配置导出.md` + `results/config_*.csv` | 17 张定义表整表导出、状态语义、名单按类型 × 场景 × 来源、操作日志时间线 |
| `03_近7日数据画像_20260926.md` | 短信按日 / 区号 / 去重用户 / cid×app / 策略（含 PASS 类额外召回的正确口径）/ 泄漏 / 返回码 / H5 A2 链路 / 常设项 |
| `04_数据问题结论.md` | 本轮做的每个 DR 一节（锚点 `dr-xxx`） |
| `05_取数手册与常见坑.md`、`06_评估指标计算手册.md` | 口径、JSON 路径、速度、坑；指标算法与模板 |
| `toolkit/` | 执行器（新增别名守卫、默认只留合并结果）、tk01–tk10（新增 tk10 唯一拦截；tk03 支持 PASS 类）；工具包测试 55/55 项核对一致 |

## 3. 主要发现

| # | 发现 | 数字 | 结果文件 |
|---|---|---|---|
| 1 | DR-027：非 +1 放行下降中，`strategy_43NaEzJmiQFk` 的唯一拦截约占 35%（推算；所试 12 组天数组合下 26%–54%）；与预上线期相比，变少的请求几乎都是 43Na 条件成立的请求（计数分解，非因果） | 短信口径，非 +1：放行日均 1,401（改前 纽约日 2026-09-19…2026-09-22）→ 533（改后 2026-09-24…2026-09-26）；43Na 唯一拦截 301/日（若无 43Na 推算 834，请求量与其它判定不变时的上限）；43Na 条件成立的请求每 24 小时（预上线期 → 上线后） 2,865 → 682，其余 1,147 → 1,246；纯 SQL 与 E1 逐格一致（348 格不一致 0；4 格不一致 0；4 格不一致 0） | `results/dr027_summary.csv`、`results/dr027_period_rates.csv`、`results/dr027_baseline_sensitivity.csv`、`results/dr027_crosscheck.csv` |
| 2 | 近 7 日短信请求与放行构成 | 26,848 次短信请求：PASS 14,079 / REJECT 12,697 / REVIEW 72；PASS 中 48.6% 来自非 +1 | `results/p3_daily_result.csv`、`results/p3_pass_by_ccgroup.csv` |
| 3 | 攻击仍在（DR-010） | 短信口径，k=5：2026-09-03 起 24 个攻击日；2026-09-26 非 +1/+86 请求 2,005（阈值 338.1） | `results/dr010_attack_rule.csv`、`results/dr010_daily_series.csv` |
| 4 | 组合维度特征仍取不到值（DR-003 常设） | 两个组合维度特征的评估次数合计（短信口径，纽约日 2026-09-20…2026-09-26）：SUCCESS 0 / 52,636 | `results/p3_counter_codes_daily.csv` |
| 5 | 分片键按场景组仍成立（DR-014 常设） | 纽约日 2026-09-26：captcha phone 100.0%；grant_new_user_coupon userNo 100.0%；login userNo 100.0%；payment userNo 100.0%；physical_order_cancel userNo 100.0%；physical_order_create userNo 100.0%；push phone 100.0%；register phone 100.0% | `results/dr014_best_candidate.csv` |
| 6 | 预上线额外召回（PASS 类按「最终不是 PASS」计） | 短信口径，纽约日 2026-09-20…2026-09-26：非 PASS 类最大 `strategy_MGj5bfGOijOi` 3,592、`strategy_x37TInaHsvPQ` 2,162；PASS 类 `strategy_GbsajBR69can` 命中 17,802、额外召回 6,265（全部 LKUS_push 行：命中 17,834、额外召回 6,266） | `results/p3_strategies.csv`、`results/p2_hits_7d.csv`、`results/toolkit_tests/tk03_extra_recall.csv` |
| 7 | 引擎 REVIEW 仍被改写为 PASS（DR-016 常设） | 短信口径，7 日引擎 REVIEW 168 次中 96 次返回 PASS | `results/dr016_summary_7d.csv` |
| 8 | 仍有 REJECT 策略排在白名单之前（DR-017 常设） | 全部 LKUS_push 行：`strategy_sw3jC7bvFYEX` 优先级 100001，7 日在线命中 50 | `results/dr017_reject_above_whitelist.csv` |
| 9 | 团队手册复现基准可复现（差异在窗口边界之内） | rows_no_cc_filter 64,935；rows_cc_filter 64,935（基准 64,931，差 +4）；pass_cc_filter 41,632（基准 41,629，差 +3）；reject_cc_filter 23,122（基准 23,121，差 +1）；review_cc_filter 181（基准 181，差 +0）。基准的起止秒没有记录；窗口起点、终点各 ±5 分钟（共 10 分钟）内分别有 16 / 21 行，差异都小于这个量，按边界秒差解释；本次比基准多而不是少，不是数据保留造成的缺失 | `results/p5_checkpoint_summary.csv` |

## 4. 数字溯源（表头数字）

| 数字 | SQL | 本地脚本 | 结果 |
|---|---|---|---|
| 7 日短信请求与结果（26,848） | `sql/e1_a.sql`、`sql/e1_b.sql`；纯 SQL 核对 `sql/p4_daily_series.sql`、`sql/p2_hits_7d.sql` | `sql/local/p3_profile.py` | `results/p3_daily_result.csv`、`results/p3_crosscheck.csv` |
| DR-027 拆分 | `sql/dr027_tk10_43na.sql`、`sql/dr027_tk08_43na_*.sql`；E1 `sql/e1_*.sql` | `sql/local/dr027_local.py` | `results/dr027_summary.csv`、`results/dr027_period_rates.csv`、`results/dr027_baseline_sensitivity.csv`、`results/dr027_*.csv` |
| DR-003 返回码 | `sql/e1_*.sql` | `sql/local/p3_profile.py` | `results/p3_counter_codes_daily.csv` |
| DR-010 攻击日 | `sql/p4_daily_series.sql` | `sql/local/p4_agg_drs.py` | `results/dr010_*.csv` |
| DR-014 分片键 | `sql/dr014_sharding_key_by_scene_20260926.sql`、`sql/p1_sk_concat_check_20260926.sql`；跨分片去重 E1 `sql/e1_*.sql` | `sql/local/p4_agg_drs.py`、`sql/local/p3_profile.py` | `results/dr014_*.csv`、`results/p3_dr014_shard_spread.csv` |
| DR-016 / 017 / 018 | `sql/e1_*.sql`、`sql/p2_hits_7d.sql`、`sql/config_*.sql` | `sql/local/p4_new_drs.py` | `results/dr016_*.csv`、`results/dr017_*.csv`、`results/dr018_*.csv` |
| 配置 / 名单 / 操作日志 | `sql/config_*.sql`、`sql/p2_*.sql` | `sql/local/p2_config.py`、`sql/local/p2_oplog_timeline.py`、`sql/local/p2_list_by_scene.py` | `results/config_*.csv`、`results/p2_*.csv` |
| 复现基准 | `sql/p5_checkpoint*.sql` | `sql/local/p4_agg_drs.py` | `results/p5_checkpoint_summary.csv` |
| 工具包测试 | `sql/toolkit_tests/`、`sql/tk06_extract_*.sql`、`sql/dr027_tk10_43na.sql` | `sql/local/p5_toolkit_tests.py` | `results/toolkit_tests/_test_summary.csv` |
| DR-029 白名单 temp | `sql/p2_list_counts.sql`、`sql/p1_columns.sql` | `sql/local/p4_page.py` | `results/p2_list_counts.csv`、`results/p1_columns.csv` |
| 同一指标只有一个值 | — | `sql/local/metrics.py`、`sql/local/p6_checks.py` | `results/p6_metric_registry.csv`、`results/p6_checks.csv` |
| 稳定性复跑 | 同原查询 | `sql/local/p7_stability.py` | `results/p7_stability.csv`（3/3 条复跑一致） |

## 5. 未取到的数据与原因

| 来源 | 状态 |
|---|---|
| Doris `ods_luckyus_iriskcontrol.t_iriskcontrol_log` | 未能获取：Doris 不可达，等 DR-020 的只读账号（依赖，不是临时受阻）（DR-002、DR-022 的 Doris 一侧） |
| Redshift | 未能获取：`redshift` MCP `list_clusters` 报错 |
| Redis `luckyus-iriskcontrol` 内容 | 只执行 `DBSIZE` / `INFO keyspace` |
| upush 逐行回填（DR-028） | DR-028 前提未满足（陈晨昕尚未确认 `mobile` 的存储方式与回填时点），本轮跳过：§3.2 不变 |
| 桌面项目与 `_inbox/` | 本机不存在：zip 与 `.sha256` 需手工放进桌面 `_inbox/` |

## 6. DR 汇总

本轮处理：

| DR | 新状态 | 一句话 |
|---|---|---|
| [DR-002](04_数据问题结论.md#dr-002) | 部分答复（Doris 不可达，等 DR-020 的只读账号（依赖，不是临时受阻）） | 源库规则不变（7 日 email 非空 35 行）；Doris 一侧等 DR-020 |
| [DR-003](04_数据问题结论.md#dr-003) | 已答复 | 组合维度 SUCCESS 0/52,636（仍坏）；e1K PARAMS_ERROR 只到 2026-09-24 |
| [DR-010](04_数据问题结论.md#dr-010) | 已答复 | k=5：2026-09-03 起 24 个攻击日；2026-09-26 仍在攻击日 |
| [DR-013](04_数据问题结论.md#dr-013) | 已答复 | Doris 仍不可达 |
| [DR-014](04_数据问题结论.md#dr-014) | 已答复 | 按场景组仍成立（手机号组 / userNo 组，2026-09-26）；uid 跨分片 |
| [DR-015](04_数据问题结论.md#dr-015) | 已答复 | 17 张定义表 + 名单按类型 × 场景 × 来源 + 操作日志时间线已导出 |
| [DR-016](04_数据问题结论.md#dr-016) | 待确认（问人：林宏鹏） | 7 日引擎 REVIEW 168 次中 96 次返回 PASS |
| [DR-017](04_数据问题结论.md#dr-017) | 待确认（问人：段枝宏、田志鲔） | `strategy_sw3jC7bvFYEX` 优先级 100001、7 日 50 次 |
| [DR-018](04_数据问题结论.md#dr-018) | 待确认（问人：田志鲔） | 3 条策略用 UTC 时刻规则（上线 1、预上线 2） |
| [DR-022](04_数据问题结论.md#dr-022) | 部分答复（Doris 不可达，等 DR-020 的只读账号（依赖，不是临时受阻）） | 源库一侧已答（上一包）；Doris 一侧等 DR-020 |
| [DR-027](04_数据问题结论.md#dr-027) | 已答复 | 非 +1 放行日均 1,401（改前）→ 533（改后）；43Na 唯一拦截 301/日 ≈ 下降的 35%（推算；所试 12 组天数组合下 26%–54%）；与预上线期相比，变少的请求几乎都是 43Na 条件成立的请求（计数分解，非因果） |
| [DR-028](04_数据问题结论.md#dr-028) | 待取数（本次受阻：前提未满足） | 前提未满足，本轮跳过 |
| [DR-029](04_数据问题结论.md#dr-029) | 待确认（问人：林宏鹏） | LKUS 白名单 82 条 temp 取值与注释的含义需平台确认 |

合计（由脚本从 04 的「新状态」行计算）：已答复 6、待取数 1、待确认 4、部分答复 2（共 13 条）。

本轮未处理（状态沿用 `DATA_REQUESTS.md`）：DR-001 待确认（问人：林宏鹏）、DR-004 已答复、DR-005 已答复、DR-006 已答复、DR-007 待确认（问人：陈晨昕）、DR-008 已答复、DR-009 已答复、DR-011 已答复、DR-012 待确认（问人：林宏鹏）、DR-019 待确认（问人：林宏鹏）、DR-020 已答复、DR-021 已答复、DR-023 已答复、DR-024 已答复、DR-025 已答复、DR-026 已答复。

## 7. 事实更正候选（提示词 §2 / 附录 A / `DATA_REQUESTS.md` 与数据不符之处）

| 原说法 | 数据显示 | 证据 |
|---|---|---|
| `DATA_REQUESTS.md` DR-027：「改动前按预上线命中」统计 43Na 的唯一拦截，隐含改动前的每一天都有它的预上线命中 | `strategy_43NaEzJmiQFk` 于 2026-09-22 15:32:11 UTC 新建（status 0）、15:32:17 UTC 转预上线（操作日志），此前没有它的命中；「改动前」只有约 23 小时可比，而且其后半段是高峰，所以本包另按精确时段给出每 24 小时的速率，并单列时段两半 | `results/p2_oplog_timeline.csv`、`results/dr027_period_rates.csv` |
| `DATA_REQUESTS.md` DR-027 的两种解释（43Na 拦下 vs 攻击量本身下降）是互斥的 | 两者在计数上分不开：与 43Na 预上线的约 23 小时相比，上线后减少的非 +1 请求几乎都是 43Na 条件成立的请求（其余非 +1 请求的变化见 04 ④）；计数无法区分攻击方对 43Na 的反应与巧合 | `04_数据问题结论.md#dr-027`、`results/dr027_period_rates.csv` |
| 2026-09-26 包 `03` §2：非 +1 放行下降「时间上与 2026-09-24 07:22–07:26 UTC 的特征条件修改相邻」 | 那几处改动中，仍在配置里的 3 个特征只被预上线（status 2）策略引用，其中 `feature_vApWJ93xOLe3` 只用于 LKUS_virtual_order_create；另 4 个是删除操作，这 4 个特征在操作日志里从未被任何规则引用、7 日内也没有被评估；而纽约日 2026-09-23 的非 +1 短信放行率在 14:43:34 UTC 43Na 上线前为 42.3%、上线后为 22.4%，下降早于这些改动 | `results/p2_oplog_timeline.csv`、`results/p2_oplog_changes.csv`、`results/config_strategy_expanded.csv`、`results/p3_counter_codes_daily.csv`、`results/dr027_e1_cells.csv` |
| 2026-09-26 包 `03` §5.2 / `results/p3_strategies.csv`：PASS 类预上线策略 `strategy_GbsajBR69can` 的「额外召回」取最终结果为 PASS 的命中 | PASS 类策略上线后改变的是最终**不是** PASS 的命中；本包按此口径重算（`toolkit/tk03_extra_recall.sql` 参数 `pass_class`） | `results/p3_strategies.csv`（列 `extra_recall_definition`） |
| 2026-09-26 包对操作日志的计数说法不一（不同页分别写 195 与 194，都称为「操作」） | 操作日志 `t_operation_log` 共 195 次操作（删除 5、新增 55、更新 135；其中 194 次有字段变化，共 299 处字段变化：新增 / 删除各按 1 处计 60 处，134 次更新共 239 处白名单字段变化；2026-09-02T11:43:59 … 2026-09-24T07:26:13 UTC）；本包各页统一这一句 | `results/p2_oplog_counts.csv`、`results/p2_oplog_timeline.csv` |

## 8. 建议的后续分析

1. **43Na 的效果评估**（给段枝宏）：与 43Na 预上线的约 23 小时相比，上线后减少的非 +1 请求几乎都是 43Na 条件成立的请求（`results/dr027_period_rates.csv`）。下一步按小时看 2026-09-23 14:43 UTC 前后这部分请求是立即减少还是逐步减少，并按号码去重看被拒号码是否重试（`results/dr027_daily_decomposition.csv` 已有逐日去重号码数）；每日用 tk10 / tk08 复跑，观察攻击方是否绕开它的条件（cid 105、号码国家 ≠ IP 国家、uid 关联计数）。
2. **DR-020 开通 Doris 只读账号后**：补 DR-002 的 `l2_scene='1002'` 对照与 DR-022 的 `access_time` 一侧。
3. **DR-028**：陈晨昕确认 `mobile` 存储方式与回填时点、并由用户批准放开 §3.2 后，做预上线命中的逐请求回填标签。
4. **组合维度特征修好后**：用 tk02 / tk03 重估 `strategy_tO7DZkJ1g0C2`（DR-003 常设项会自动发现 SUCCESS 恢复）。
5. **2026-11-01 夏令时结束前**：复核 UTC 02:00–09:00 时刻规则（DR-018）。
6. **DR-029 有答复后**：若界面把 temp=1 的白名单显示为永久，把字段注释的更正写进数据字典。

## 9. 交接

- zip：`RC_data_package_20260927-0614.zip` 与 `RC_data_package_20260927-0614.zip.sha256` 在运行目录；**两个文件都要**放进桌面项目的 `_inbox/`，再在桌面跑 D1。
- 交接仓库 `lcna-riskcontrol-data-package` 是 **public**：按提示词 P7 第 7 步本轮没有推送；把它改成私有或删除旧包由用户决定。
