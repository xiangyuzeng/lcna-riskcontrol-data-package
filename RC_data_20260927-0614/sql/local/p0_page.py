#!/usr/bin/env python3
"""P0: write 00_环境清单.md from this run's P0 results (results/p0_*.csv, timing.csv)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
sv, gp, lat, sch, st = rd("p0_server_vars.csv").iloc[0], rd("p0_show_grants_parsed.csv"), rd("p0_select1_latency.csv"), rd("p0_schemata.csv"), rd("p0_schema_tables.csv")
rw, rs = rd("p0_reserved_words.csv", keep_default_na=False), rd("p0_redis_iriskcontrol.csv").iloc[1]
t = rd("timing.csv"); t = t[t.name.str.startswith("p0_timing_b")]
routines = 0 if os.path.getsize(os.path.join(R, "p0_routines.csv")) < 5 else len(rd("p0_routines.csv"))
val_a, val_b = rd("p0_runner_validation.csv", dtype=str), rd("p0_runner_validation_mcp_direct.csv", dtype=str)
same = val_a.sort_values(list(val_a.columns)).reset_index(drop=True).equals(val_b.sort_values(list(val_b.columns)).reset_index(drop=True))
al = st[st.table_group == "t_access_log_NNNN"].iloc[0]; gv = st[st.table_group == "t_gateway_validate_log_NNNN"].iloc[0]
s_ = sorted(lat.seconds)
inv = rd("p0_mcp_inventory.csv", dtype=str)
iv = lambda k: inv[inv.item == k].value.iloc[0]
inv_srv = "、".join(f"{iv(f'list_servers：{e} 服务器数')} 个 {n}" for e, n in (("mysql", "MySQL"), ("postgres", "PostgreSQL"), ("redis", "Redis")))
inv_ods, inv_rs, inv_t = iv("名字扫描发现的 ods_* 库"), iv("list_clusters"), inv.checked_ny.iloc[0]
L = ["# 00 环境清单", "",
     "> 2026-09-27（America/New_York）06:14 开始。全程只读。所有连接只写 MCP server 名，不写地址。", "",
     "## 1. 本轮输入", "",
     "- 提示词 M1（桌面 2026-09-26 第六轮修订版）与 `DATA_REQUESTS.md` 都**随对话消息内联提供**；`DATA_REQUESTS.md` 是桌面 2026-09-26 副本（28 条 DR，DR-001…DR-028，变更记录最后一条「2026-09-26（第六轮）」）。以这份内联副本为准。",
     "- 本轮 DR：DR-027（待取数）+ 常设项 DR-003、010、013、014、015、016、017、018；DR-002、DR-022 只写短节（Doris 依赖）；DR-028 前提未满足，跳过；运行中新开 DR-029（清单未覆盖，见 `04_数据问题结论.md#dr-029`）。",
     "- 上一轮包 `RC_data_20260926-1722/`、`RC_data_20260925-0817/`：只读取、复用其工具与脚本，未修改；**数字一律本次重新查询**。",
     "- 桌面项目「风控SOP_Wiki_20260924」：不在本机，未读取。", "",
     "## 2. MCP server 与可达性", "", "| MCP server | 能做什么 | 本次用途 | 结论 |", "|---|---|---|---|",
     f"| `mcp-db-gateway` | `list_servers` / `mysql_query` / `postgres_query` / `redis_command` | 唯一的数据通道；只用查询工具 | {inv_srv}；名字扫描发现的 `ods_*` 库 {inv_ods} 个（{inv_t} 复查，`results/p0_mcp_inventory.csv`） |",
     "| `grafana-lucky` | PromQL、LogQL、看板与数据源元数据 | 读看板面板 SQL 文本 | 有 Doris 数据源 `Doris-iriskcontrol`（database `ods_luckyus_iriskcontrol`），**没有执行 SQL 的工具** → Doris 不可达（DR-013、DR-020） |",
     f"| `redshift` | `list_clusters` 等 | 可达性检查 | `list_clusters` {inv_rs}，未能获取（`results/p0_mcp_inventory.csv`） |",
     "| 其它（cloudwatch / eks / billing / pricing / docs / prometheus / dataprocessing） | 非风控数据 | 未使用 | — |", "",
     "## 3. 风控库", "", "| 项 | 值 | 证据 |", "|---|---|---|",
     "| 实例 | `aws-luckyus-iriskcontrolservice-rw` | — |",
     f"| 引擎 | MySQL {sv.version}（{sv.version_comment}） | `results/p0_server_vars.csv` |",
     f"| 只读标志 | `read_only={sv.read_only}`、`innodb_read_only={sv.innodb_read_only}`、`super_read_only={sv.super_read_only}` → **主库** | 同上 |",
     f"| 时区 | `time_zone={sv.time_zone}`、`system_time_zone={sv.system_time_zone}` | 同上 |",
     f"| 账号权限 | 全局 {'、'.join(f'`{p}`' for p in gp.privilege)}，**没有写权限** | `results/p0_show_grants_parsed.csv`、`results/p0_user_privileges.csv` |",
     f"| 存储过程 | 系统库以外 {routines} 个（守卫另外拒绝 `CALL`） | `results/p0_routines.csv` |",
     f"| 保留字 | `information_schema.KEYWORDS` 中 RESERVED=1 的 {len(rw)} 个，供守卫检查列别名 | `results/p0_reserved_words.csv` |",
     f"| `SELECT 1` 往返 | 5 次：最小 / 中位 / 最大 {s_[0]:.3f} / {s_[2]:.3f} / {s_[-1]:.3f} s | `results/p0_select1_latency.csv` |",
     f"| 可见库 | " + "、".join(f"`{r.SCHEMA_NAME}`（{r.n_tables} 张表）" for r in sch.itertuples() if r.SCHEMA_NAME in ("luckyus_iriskcontrolservice", "backup_tables")) + " + 系统库 | `results/p0_schemata.csv` |",
     f"| 分片 | `t_access_log_0000…0063` 共 {int(al.n_tables)} 张，估算 {int(al.est_rows):,} 行；`t_gateway_validate_log_0000…0063` {int(gv.n_tables)} 张，估算 {int(gv.est_rows)} 行 | `results/p0_schema_tables.csv` |",
     "| 负载 | 每批取数前自动查 `information_schema.PROCESSLIST` 聚合 | `results/processlist_checks.csv` |", "",
     "## 4. 其它数据源", "", "| 来源 | 结论 | 证据 |", "|---|---|---|",
     "| Doris `ods_luckyus_iriskcontrol.t_iriskcontrol_log` | **未能获取：Doris 不可达**（等 DR-020 的只读账号） | DR-013 |",
     "| Grafana「北美风控巡检大盘」 | 短信面板 SQL 与 2026-09-26 读到的逐字相同：短信 = `l2_scene='1001'`，按纽约日分桶，非当地 = `country_code <> '+1'` | `results/p0_grafana_patrol_panels.md` |",
     f"| Redis `luckyus-iriskcontrol` | 只执行 `DBSIZE` 与 `INFO keyspace`：db0 {int(rs['keys']):,} 个键，{int(rs.expires):,} 个带过期时间，平均 TTL {int(rs.avg_ttl_ms):,} ms | `results/p0_redis_iriskcontrol.csv` |",
     "| upush `luckyus_iupushsms.t_verifycode_filled_statistics` | 本轮没有需要它的 DR（DR-007 待陈晨昕、DR-028 前提未满足），未读数据 | — |", "",
     "## 5. 脚本通道与守卫", "",
     "- 环境变量 `MCP_DB_GATEWAY_SSE` 未设置；执行器运行时从本机 Claude MCP 配置读取 `mcp-db-gateway` 的地址，只放进子进程环境，不打印、不落盘。",
     "- 执行器 `toolkit/shard_runner.py`（复用 2026-09-26 版并加两处）：",
     "  - **列别名守卫**：别名不能是 MySQL 保留字（上表，实时读取）或内建函数名（如 `utc_date`；2026-09-26 曾因 `AS utc_date` 报 1064）；",
     "  - **只留合并结果**：聚合运行默认不再写每分片的小文件（`--parts` 才写），包内文件数大幅减少。",
     "- 守卫单测 `toolkit/test_guard.py`：27 条应拒绝（含 3 条别名用例）+ 13 条应放行，0 失败。",
     f"- 校验：同一条语句（0000 分片、纽约日 2026-09-26、按场景 × 结果计数）经执行器与经 MCP 直调，{len(val_a)} 行{'完全一致' if same else '**不一致**'}（`results/p0_runner_validation.csv` vs `results/p0_runner_validation_mcp_direct.csv`）。", "",
     "## 6. 批量大小测试（纽约日 2026-09-26，LKUS_push，逐元素展开 featureDetail）", "",
     "| 每条语句分片数 | 语句数 | 单条中位 | 单条最长 | 合计 |", "|---|---|---|---|---|"]
for b in (1, 4, 8, 16):
    x = t[t.name == f"p0_timing_b{b}"]
    L.append(f"| {b} | {len(x)} | {x.seconds.median():.2f} s | {x.seconds.max():.2f} s | {x.seconds.sum():.1f} s |")
L += ["", "- **决定：聚合语句每条 16 个分片、≤1 个纽约日；跨月的逐日聚合（DR-010 序列）从 8 个分片起步；行级抽取每条 16 个分片、≤1 小时**，带 `/*+ MAX_EXECUTION_TIME(10000) */`（主库）。单条 >3 s 时执行器自动减半批量。",
      "- EXPLAIN（0000 分片）走 `idx_create_time_sharding_key`（`results/explain/p0_timing_b16_shard0.csv`）；计时明细 `results/timing.csv`。", "",
      "## 7. 团队已有代码（运行目录内，相对路径）", "",
      "| 路径 | 本次 |", "|---|---|",
      "| `sms_attack/pull_20d.py`、`sms_attack/sql/08_riskcontrol_20d.sql` | 方法已被执行器与 E1 抽取吸收（服务端 `JSON_TABLE` 摊平，只取标量） |",
      "| `doris_check/` | Doris 仍不可达 |",
      "| `RC_data_20260926-1722/`、`RC_data_20260925-0817/` | 复用 `toolkit/`、`sql/local/` 与 SQL 模板；未修改 |",
      "| `SQL-cookbook*` | 本机未找到 |"]
open(os.path.join(PKG, "00_环境清单.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("00 written", len(L))
