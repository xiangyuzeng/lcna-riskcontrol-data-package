# toolkit — 北美风控取数工具包

> 2026-09-25 编写，每个模板都用本包数据跑过一次，并与包内另一种算法的结果逐格核对（`results/toolkit_tests/_test_summary.csv`，全部一致）。
> 数据源：MCP server `mcp-db-gateway` 的 `mysql_query` 工具 → `aws-luckyus-iriskcontrolservice-rw` / `luckyus_iriskcontrolservice.t_access_log_0000…0063`。
> 只读。连接地址从不写进任何文件。

## 1. 文件

| 文件 | 用途 |
|---|---|
| `shard_runner.py` | 取数执行器：语句守卫 → EXPLAIN 门槛 → 64 分片按批（默认 16 个/条）顺序执行 → 写 `sql/<name>.sql` 与 `results/<name>.csv` |
| `test_guard.py` | 守卫单测（24 条应拒绝 + 12 条应放行） |
| `ny_day_bounds.py` | 纽约自然日 → UTC 起止（夏令时安全） |
| `same_hours.py` | 目标时段 + 前 N 天同一时段的 UTC 窗口列表（给 `--windows-file`） |
| `tk01_volume_users.sql` | 调用量：按区号 × 最终结果 × email 键计数；窗口级精确去重手机号 |
| `tk02_strategy_hits.sql` | 单条策略（在线或预上线）命中 PV；窗口级去重手机号 |
| `tk03_extra_recall.sql` | 预上线策略的额外召回（命中且最终 PASS） |
| `tk04_pass_leakage.sql` | 非本国区号的放行画像 |
| `tk05_v3_distribution.sql` | reCAPTCHA 分数分布（按形状取分） |
| `tk06_rule_recheck_extract.sql` + `recheck_counter.py` | 累计特征规则复核：本地重算计数、只输出违例条数 |
| `tk07_daily_patrol.sql` + `patrol.py` | 每日巡检一页纸 |
| `tk_merge.py` | tk01–tk05 的合并步骤（跨分片汇总） |
| `privacy_scan.py` | 交付前隐私扫描（提示词附录 B 原文） |

## 2. 运行方式

**脚本方式**（推荐，结果和 SQL 自动落盘）：

```bash
export MCP_DB_GATEWAY_SSE=<mcp-db-gateway 的 SSE 地址>      # 向 DBA 要，不要写进文件
export PYTHONDONTWRITEBYTECODE=1
cd RC_data_<stamp>
python3 toolkit/shard_runner.py run --name <结果名> --template toolkit/<模板>.sql \
    --param scene=LKUS_push [--param k=v ...] --ny-days 2026-09-24:2026-09-24 [--batch 16]
python3 toolkit/tk_merge.py tk01 results/<结果名>.csv --home-cc 1 --watch-cc 86 --sms-only
```

- 时间窗口：`--ny-days A:B`（按纽约日，每天一条语句）、`--utc 'A~B' --chunk day|hour`，或 `--windows-file`（每行一个 `UTC起~UTC止`）。
- 行级抽取（只有 tk06）必须 `--kind rows --local`：每条语句 ≤1 小时，结果只写 `_local_only/raw/`，身份字段是加盐哈希（盐每次运行随机生成，存在 `_local_only/.run_salt`，用完即删）。
- 每次批量前 runner 自动查进程负载；单条 >3 s 自动把批量减半；超时不重跑。

**MCP 直调方式**（没有脚本环境时）：在 Claude Code 里调用 `mcp-db-gateway` 的 `mysql_query`，`server=aws-luckyus-iriskcontrolservice-rw`。把模板里的 `{tbl}` 换成 `t_access_log_0000` … `t_access_log_0063`、`{shard}` 换成四位分片号、`{utc_start}/{utc_end}` 换成 UTC 字面量（`python3 toolkit/ny_day_bounds.py 7` 可打印），每条最多 UNION ALL 16 个分片、最多 1 天。发送前先 `python3 toolkit/shard_runner.py check <文件>` 过守卫。

## 3. 去重口径（重要）

- 分片键 `sharding_key` = 带 `+` 的完整手机号（DR-014）：同一手机号只在一个分片，所以**同一窗口内**各分片的 `COUNT(DISTINCT sharding_key)` 可以直接相加。
- **不能跨分组相加**：同一手机号同一天可能既 PASS 又 REJECT。tk01/tk02 输出里 `level=window` 的行才是精确的去重手机号；`level=group` 的行只给次数。
- **不能跨窗口相加**：多天去重要用行级抽取（tk06 方式）在本地去重。
- uid 不是分片键，跨分片会重复（7 日按分片相加 18,133，真值 9,059），SQL 方式无法得到精确值。

## 4. 各模板参数与本次示例

| 模板 | 参数 | 本次测试（纽约日） | 结果 | 对照 |
|---|---|---|---|---|
| tk01 | `scene`、`home_ccs`（如 `'1'`） | 2026-09-24 + 前 7 天同一时段 | 09-24：请求 3,225；短信去重手机号 1,845；+1 放行手机号 962 | 与 E1 本地精确去重逐日一致 |
| tk02 | `scene`、`strategy_id`、`hit_list`（`hitStrategy`/`hitPreOnlineStrategy`） | `strategy_MGj5bfGOijOi` 预上线，09-18…09-24 | PV 13,202；09-24 去重手机号 466 | 与 `results/p2_hits_7d.csv` 及 E1 一致 |
| tk03 | `scene`、`strategy_id` | 同上 | 额外召回 4,517 | 与 `results/p3_strategies.csv` 一致 |
| tk04 | `scene`、`home_ccs` | 09-18…09-24，`'1'` | 非 +1 短信放行 8,795 | 与 `results/p3_pass_leakage.csv` 一致 |
| tk05 | `scene`；合并时 `--cuts 0.3,0.8` | 09-18…09-24 | 37 个格子（区号组 × cid × 分数段） | 与 `results/p3_v3_by_ccgroup_cid.csv` 逐格一致 |
| tk06 | `scene`、`feature_id`、`strategy_id`；复核时 `--op --threshold --eval-from` | `strategy_REnWrA7CfCdE` 的"区号近60分钟访问次数 > 30"，09-24（前置 1 小时暖机） | 命中 277，重算下规则不成立（违例）0；引擎值与重算相等 92.7%、±1 内 98.6% | 命中数与 `results/p2_hits_7d.csv` 一致 |
| tk07 | `--day`、`--scene`、`--home-cc` | 2026-09-24 | 短信 PASS 1,718 / REJECT 1,478 / REVIEW 15；非 +1 放行 582（33.9%） | 与 `03` 及 `results/p2_hits_7d.csv` 一致 |

测试原始输出：`results/toolkit_tests/`；每个测试实际执行的 SQL：`sql/toolkit_tests/`。

## 5. 每个模板的要点

- **tk01**：每日调用量与"近 7 日同期"。`python3 toolkit/same_hours.py 2026-09-24T00:00 2026-09-25T00:00 --prev 7 > w.txt`，再 `run --windows-file w.txt`。
- **tk02**：`hit_list=hitPreOnlineStrategy` 统计预上线命中。命中判断用 `JSON_CONTAINS(..., JSON_OBJECT('strategyId', ...))`，只认 ID，不认策略名。
- **tk03**：额外召回 = 预上线命中且最终 PASS；是否打到本国用户看 `pv_home`。
- **tk04**：`home_ccs` 是不带 `+` 的带引号列表；合并时 `--sms-only` 去掉带 email 的请求（DR-002）。
- **tk05**：分数取任一 reCAPTCHA 特征 apiResp 里的 `riskAnalysis.score`——承载分数的 featureId 在 2026-08/09 切换过多次（DR-005），不要按特征名或单一 ID 取。
- **tk06**：计数口径已用无条件特征校准（DR-003）：同一维度值、窗口 (t−period, t]、含当前请求、只计引擎评估过该特征的请求。目前支持的维度：countryCode / phoneNo / realIp / realIpc / uid / realIpCountry；条件支持 `NOT_EQUAL_STRING(realIpCountry,…)` 与 token 为空/不存在。窗口长的特征要相应加长暖机（1 天特征要 24 小时）。
- **tk07**：`patrol.py --day <纽约日>` 一条命令出巡检页；`--no-query` 只用已有结果重排版面。
