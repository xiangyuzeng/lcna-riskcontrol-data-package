#!/usr/bin/env python3
"""P0: write 00_环境清单.md from this run's P0 results (results/p0_*.csv, timing.csv)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
sv, gp, sch, st = rd("p0_server_vars.csv").iloc[0], rd("p0_show_grants_parsed.csv"), rd("p0_schemata.csv"), rd("p0_schema_tables.csv")
rw, rs = rd("p0_reserved_words.csv", keep_default_na=False), rd("p0_redis_iriskcontrol.csv", dtype=str)
inv = rd("p0_mcp_inventory.csv", dtype=str)
t = rd("timing.csv"); t = t[t.name.str.startswith("p0_timing_b")]
routines = 0 if os.path.getsize(os.path.join(R, "p0_routines.csv")) < 5 else len(rd("p0_routines.csv"))
va, vb = rd("p0_runner_validation_mcp_direct.csv"), None
al = st[st.table_group == "t_access_log_NNNN"].iloc[0]; gv = st[st.table_group == "t_gateway_validate_log_NNNN"].iloc[0]
L = ["# 00 环境清单", "",
     "> 2026-10-10（America/New_York）00:13 开始（Step A–C 只读侦察与计划在 2026-10-09 22:16 起）。全程只读。连接只写 MCP server 名，不写地址。", "",
     "## 1. 本轮输入", "",
     "- 提示词 M1 与 `DATA_REQUESTS.md` 都**随对话消息内联提供**：`DATA_REQUESTS.md` 是桌面 2026-10-09 副本（38 条 DR，DR-001…DR-038，变更记录最后一条「2026-10-09（第八轮，为第四次 M1 准备）：新增 DR-034～DR-038」）。以这份内联副本为准；Part 4 的工具包也是内联提供（19 个文件，sha256 与清单 19/19 一致）。",
     "- 本轮 DR 分类：**运行** DR-030…DR-038；**常设** DR-003、010、013、014、015、016、017、018 + P3 常设项 + DR-012 复测；**短节** DR-002、DR-022（Doris 依赖）；**跳过** DR-028（前提未满足：陈晨昕的口径确认）、DR-029（数据已做完，含义待林宏鹏）。",
     "- 之前的三个包 `RC_data_20260925-0817/`、`RC_data_20260926-1722/`、`RC_data_20260927-0614/` 都已完成：只读取、复用其工具与脚本，未修改；**数字一律本次重新查询**。",
     "- 桌面项目「风控SOP_Wiki_20260924」不在本机，未读取。",
     "- **用户在计划评审时的两项决定（2026-10-09）**：(1) 执行器从本机 MCP 配置读取 `mcp-db-gateway` 的地址，只放进子进程环境，不打印、不落盘——这一条覆盖了本轮 Part 1 第 11 点（「不要查找地址」）；(2) 所有数据窗口截止纽约日 2026-10-09（包在 10-10 00:13 开始，正好是「运行日之前最后一个完整纽约日」）。",
     "- **生产库取数时段**：团队 2026-10-08 起规定，生产库的批量统计取数只在纽约时间 22:00–06:00 进行；本包执行器在每条语句前检查，05:30 后不再发送（见 `toolkit/README.md`）。", "",
     "## 2. MCP server 与数据源（只写名字）", "", "| MCP server | 能做什么 | 能触达 | 能否写 | 本次用途 |", "|---|---|---|---|---|"]
for r in inv.itertuples():
    L.append(f"| `{r.mcp_server}` | {r.tools} | {r.reaches} | {r.write_capability} | {r.this_run} |")
L += ["", "- Grafana 数据源有 `Doris-iriskcontrol`，但 `grafana-lucky` 没有执行 SQL 的工具 → **Doris 不可达**（DR-013、DR-020）。",
      "- 本次查询的数据库服务器只有 4 台（都经 `mcp-db-gateway` 的只读查询工具）：风控库、upush（只读按日汇总表）、salescrm 与 salesorder（DR-037，只出聚合）。其余服务器只在 P1 名字扫描时读 `information_schema` 的表名。", "",
      "## 3. 风控库", "", "| 项 | 值 | 证据 |", "|---|---|---|",
      "| 实例 | `aws-luckyus-iriskcontrolservice-rw` | — |",
      f"| 引擎 | MySQL {sv.version}（{sv.version_comment}） | `results/p0_server_vars.csv` |",
      f"| 只读标志 | `read_only={sv.read_only}`、`innodb_read_only={sv.innodb_read_only}`、`super_read_only={sv.super_read_only}` → **主库** | 同上 |",
      f"| 时区 | `time_zone={sv.time_zone}`、`system_time_zone={sv.system_time_zone}` | 同上 |",
      f"| 账号权限 | 全局 `SELECT`、`PROCESS`、`EXECUTE`，**没有写权限**；upush、salescrm、salesorder 三台同样 | `results/p0_show_grants_parsed.csv`、`results/p0_user_privileges.csv` |",
      f"| 存储过程 | 系统库以外 {routines} 个（守卫另外拒绝 `CALL`） | `results/p0_routines.csv` |",
      f"| 保留字 | `information_schema.KEYWORDS` 中 RESERVED=1 的 {len(rw)} 个，供守卫检查列别名 | `results/p0_reserved_words.csv` |",
      f"| 可见库 | " + "、".join(f"`{r.SCHEMA_NAME}`（{r.n_tables} 张表）" for r in sch.itertuples() if r.SCHEMA_NAME in ("luckyus_iriskcontrolservice", "backup_tables")) + " + 系统库 | `results/p0_schemata.csv` |",
      f"| 分片 | `t_access_log_0000…0063` 共 {int(al.n_tables)} 张，估算 {int(al.est_rows):,} 行，64 张列结构完全一致；`t_gateway_validate_log_0000…0063` {int(gv.n_tables)} 张，估算 {int(gv.est_rows)} 行 | `results/p0_schema_tables.csv`、`results/p1_shard_column_identity.csv` |",
      "| 负载 | 每批取数前自动查 `information_schema.PROCESSLIST` 聚合 | `results/processlist_checks.csv` |", "",
      "## 4. 其它数据源", "", "| 来源 | 结论 | 证据 |", "|---|---|---|",
      "| Doris `ods_luckyus_iriskcontrol.t_iriskcontrol_log` | **未能获取：Doris 不可达**（等 DR-020 的只读账号） | DR-013 |",
      f"| Redis `luckyus-iriskcontrol` | 只执行 `INFO keyspace` 与 `DBSIZE`：db0 {int(rs['keys'].iloc[0]):,} 个键、{int(rs.expires.iloc[0]):,} 个带过期时间、平均 TTL {rs.avg_ttl_ms.iloc[0]} ms；几秒后 `DBSIZE` {int(rs['keys'].iloc[1]):,} | `results/p0_redis_iriskcontrol.csv` |",
      "| upush `luckyus_iupushsms.t_verifycode_filled_statistics` | 按日汇总表（无个人信息），DR-035 只用 `SUM` 分组读取 | `04_数据问题结论.md#dr-035` |",
      "| salescrm / salesorder | DR-037 只出计数（Part 1 第 7 点批准的范围），先 `information_schema` 发现、再 EXPLAIN、按月拆分 | `01_数据源与表清单.md` §10 |", "",
      "## 5. 脚本通道与守卫", "",
      "- 环境变量 `MCP_DB_GATEWAY_SSE` 未设置；按用户决定，本机包装脚本（只在 `_local_only/`，不进包）运行时从 MCP 配置读出地址，只放进执行器子进程的环境。",
      "- 执行器 `toolkit/shard_runner.py` 用 Part 4 原文（sha256 一致），本包副本改了两处（详见 `toolkit/README.md`）：",
      "  - **生产取数时段检查**：每条语句发送前检查纽约时间是否在 22:00–05:30，不在就不发送并退出；",
      "  - **EXPLAIN 门槛把空区间当作通过**：`No matching min/max row` 表示窗口内没有行、什么也不扫，不是坏执行计划；`type = ALL` 的大表扫描仍然拒绝。",
      "- 守卫单测 `toolkit/test_guard.py`：27 条应拒绝 + 13 条应放行，0 失败（改动前后各跑一次）。",
      f"- 校验：同一条语句（0000 分片、纽约日 2026-10-09、按场景 × 结果计数）经执行器与经 MCP 直调，{len(va)} 行{'完全一致' if bool(va.equal.all()) else '**不一致**'}（`results/p0_runner_validation_mcp_direct.csv`）。", "",
      "## 6. 批量大小测试（纽约日 2026-10-09，LKUS_push，逐元素展开 featureDetail，0000…0015 分片）", "",
      "| 每条语句分片数 | 语句数 | 单条中位 | 单条最长 | 合计 |", "|---|---|---|---|---|"]
for b in (1, 4, 8, 16):
    x = t[t.name == f"p0_timing_b{b}"]
    L.append(f"| {b} | {len(x)} | {x.seconds.median():.2f} s | {x.seconds.max():.2f} s | {x.seconds.sum():.1f} s |")
L += ["", "- **决定：轻量的按日聚合每条 16 个分片、≤1 个纽约日；长序列（L1）与命中类模板（tk02/03/08/10）从 8 个分片起步；行级抽取（E1）每条 16 个分片、≤1 小时**，都带 `/*+ MAX_EXECUTION_TIME(10000) */`（主库）。单条 >3 s 时执行器自动减半批量。",
      "- 每次调用执行器还有约 15 s 的连接开销（查询本身多在 1 s 内），所以长抽取按天（E1）或按 7 天（L1）一次调用。", "",
      "## 7. 团队已有代码（运行目录内，相对路径）", "", "| 路径 | 本次 |", "|---|---|",
      "| `sms_attack/`（`pull_20d.py`、`mcp_client.py`、`sms_attack/sql/08_riskcontrol_20d.sql`、`otp_fill/`） | 方法已被执行器与 E1 吸收；其中个别脚本内嵌了网关地址，**本次没有用它们连库** |",
      "| `doris_check/` | 门店 / 人事的 Doris 核对笔记，与风控无关；Doris 仍不可达 |",
      "| `RC_data_20260927-0614/` 等三个包 | 复用 `toolkit/`、`sql/local/` 与 SQL 模板；未修改 |",
      "| `SQL-cookbook*` | 本机未找到 |"]
open(os.path.join(PKG, "00_环境清单.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("00 written", len(L))
