#!/usr/bin/env python3
"""P1: write 01_数据源与表清单.md; every number is read from results/ (runner outputs of this run)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
st, roles, sr = rd("p0_schema_tables.csv"), rd("p1_table_roles.csv"), rd("p1_scene_rows.csv")
k, ca, rs = rd("p1_chk_consistency.csv"), rd("p1_cid_app_summary.csv", dtype={"cid": str}), rd("p1_result_sources_summary.csv")
fr, sci, sii, part = rd("p1_freshness.csv"), rd("p1_shard_column_identity.csv"), rd("p1_shard_index_identity.csv"), rd("p1_partitions.csv") if os.path.getsize(os.path.join(R, "p1_partitions.csv")) > 5 else pd.DataFrame()
fs, em, cvd = rd("p1_fleet_sweep_mysql.csv"), rd("p1_dr002_email_signals.csv"), rd("p1_comment_vs_data.csv")
up_t = rd("p1_dr007_upush_tables.csv")
fsp = os.path.join(R, "p1_fleet_sweep_pg.csv")
pg_hits = 0 if os.path.getsize(fsp) < 5 else len(pd.read_csv(fsp))
esc = lambda v: "" if pd.isna(v) else str(v).replace("|", "\\|")
win = sorted(k.ny_date.unique()); W = f"{win[0]}…{win[-1]}"
fresh = fr.dropna(subset=["newest_create_time"])
lag = (pd.to_datetime(fresh.utc_now.max()) - pd.to_datetime(fresh.newest_create_time.max())).total_seconds()
st_i = st.set_index("table_group")
fam = sci.groupby("family").apply(lambda g: (g.n_tables == g.n_family).all(), include_groups=False)
ncol = sci.groupby("family").size()
nidx = sii.groupby("family").INDEX_NAME.nunique()
sc_tot = sr.groupby("scene_id").n_rows.sum().sort_values(ascending=False)
n7 = int(k.n.sum())
res = rs.groupby("result_col").n.sum()
diff = rs[rs.result_col != rs.re_result_name]
L = ["# 01 数据源与表清单", "",
     "> 2026-09-26 实测。所有表名来自 information_schema；所有数字来自本次会话执行的 SQL（`sql/`）与结果（`results/`）。逐表字段见 `dictionary/`。", "",
     "## 1. 结论先看", "", "| 问题 | 答案 | 证据 |", "|---|---|---|",
     "| 风控数据在哪 | `aws-luckyus-iriskcontrolservice-rw` / `luckyus_iriskcontrolservice`：请求日志 64 分片 + 引擎配置 16 张 `t_rms_engine_*`（+ 遗留 `t_scene`）+ 黑白名单 + 操作日志 | `results/p0_schema_tables.csv` |",
     "| 主库还是从库 | **主库**（`read_only=0`），账号只有 SELECT / PROCESS / EXECUTE | `results/p0_server_vars.csv`、`results/p0_user_privileges.csv` |",
     f"| 其它服务器有没有风控表 | 64 个 MySQL + 1 个 PG 名字扫描（{len(fs)} 条命中，PG {pg_hits} 条）：风控引擎只在上面这一台；短信侧 upush 有验证码与短信名单表（推送业务域，只记名字与元数据） | `results/p1_fleet_sweep_mysql.csv`、`results/p1_fleet_sweep_pg.csv` |",
     "| Doris `ods_luckyus_iriskcontrol` | **未能获取：Doris 不可达**。gateway 上没有 `ods_*` 库；Grafana 有数据源但 MCP 不能执行 SQL（DR-020） | `00_环境清单.md` |",
     f"| 64 个分片结构是否一致 | " + "；".join(f"`{f}_NNNN` {ncol[f]} 列 × 64 张、{nidx[f]} 个索引，" + ("完全一致" if fam[f] else "**不一致**") for f in fam.index) + f"；分区 {len(part)} 个 | `results/p1_shard_column_identity.csv`、`results/p1_shard_index_identity.csv`、`results/p1_partitions.csv` |",
     f"| 时间列时区 | `create_time` = UTC（最新一行比 `UTC_TIMESTAMP()` 早 {lag:.0f} s） | `results/p1_freshness.csv` |",
     "| 分片键 | LKUS_push：`sharding_key = CONCAT(country_code, phone)`（带 `+` 的完整手机号）→ 同一手机号只在一个分片；其它场景见 DR-021 | §5、DR-014、DR-021 |",
     "| 短信 vs 邮件 | LKUS_push 每一行都带手机号；极少数行另带非空 `email` | §6、DR-002 |", "",
     "## 2. 风控库 `luckyus_iriskcontrolservice` 表清单", "",
     "角色决定能不能导出内容：**配置（定义表）** 整表导出；**名单/条目表** 只计数；**日志** 只做带时间谓词的聚合。角色来源 `results/p1_table_roles.csv`（按字段注释与含义人工分类）；估算行数来自 information_schema（`results/p0_schema_tables.csv`），与精确计数可能不同。", "",
     "| 表 | 角色 | 估算行数 | 最近写入（UPDATE_TIME，UTC） | 说明 |", "|---|---|---|---|---|"]
for r in roles.itertuples():
    g = "t_access_log_NNNN" if r.table_name == "t_access_log_0000" else ("t_gateway_validate_log_NNNN" if r.table_name == "t_gateway_validate_log_0000" else r.table_name)
    if g not in st_i.index:
        continue
    x = st_i.loc[g]
    name = f"`{g.replace('NNNN', '0000…0063')}`（64 张）" if "NNNN" in g else f"`{g}`"
    L.append(f"| {name} | {r.role} | {int(x.est_rows):,} | {esc(x.max_update_time) or '—'} | {esc(r.note)} |")
L += ["", "`backup_tables` schema 存在但没有表（`results/p0_schemata.csv`）。库内（系统库以外）没有存储过程/函数（`results/p0_routines.csv`）。", "",
      "## 3. 日志分片 `t_access_log_NNNN`", "",
      f"- 64 张同构；单表 {st_i.loc['t_access_log_NNNN'].min_mb}–{st_i.loc['t_access_log_NNNN'].max_mb} MB；索引 " + "、".join(f"`{i}({', '.join(g.sort_values('SEQ_IN_INDEX').COLUMN_NAME)})`" for i, g in sii[sii.family == 't_access_log'].groupby('INDEX_NAME')) + "。",
      f"- 纽约日 2026-09-25 全部场景 {int(sc_tot.sum()):,} 行，其中 LKUS_push {int(sc_tot.get('LKUS_push', 0)):,} 行；当天出现 {len(sc_tot)} 个 `scene_id`（" + "、".join(f"`{s}` {n:,}" for s, n in sc_tot.items()) + "）（`results/p1_scene_rows.csv`）。",
      "- JSON 结构（只列键）与每行体积见 `dictionary/t_access_log_0000.md`。要点：`$.para` 是被再次编码的 JSON 字符串；`$.re.featureDetail`、`$.re.ruleDetail` 是原生数组；`$.re.hitStrategy`、`hitPreOnlineStrategy`、`hitBreakStrategy` 是字符串里装数组。", "",
      f"## 4. 字段口径（LKUS_push，{W} 纽约日，{n7:,} 行）", "", "| 口径 | 实测 | 来源 |", "|---|---|---|",
      f"| 最终结果（返回调用方） | `result` 列 = `response.$.result`：{int(rs[rs.result_col == rs.response_result].n.sum()):,}/{n7:,} 一致；PASS {int(res.get('PASS', 0)):,} / REJECT {int(res.get('REJECT', 0)):,} / REVIEW {int(res.get('REVIEW', 0)):,} | `results/p1_result_sources_summary.csv` |",
      f"| 引擎结果 `re.resultName` | 与最终结果不同的 {int(diff.n.sum())} 行：" + "；".join(f"引擎 {r.re_result_name} → 最终 {r.result_col} {int(r.n)} 行" for r in diff.itertuples()) + "（DR-016） | 同上 |",
      "| `response.code` | " + " / ".join(f"{a}={b}" for a, b in rs.drop_duplicates('result_col')[['result_col', 'response_code']].itertuples(index=False)) + " | 同上 |",
      f"| `country_code` | 列与 `$.para.countryCode` 带 `+` 的 {int(k[k.cc_col_form == 'plus'].n.sum()):,}/{n7:,}，二者相等 {int(k[k.cc_col_eq_para == 1].n.sum()):,}/{n7:,} | `results/p1_chk_consistency.csv` |",
      f"| `fullPhoneNo` | = 去 `+` 的 `countryCode` 拼 `phoneNo`：{int(k[k.full_eq_cc_phone == 1].n.sum()):,}/{n7:,} | 同上 |",
      "| `phoneCountry` / `realIpCountry` | 都是中文国家名，可直接比较是否相等 | `results/p1_cc_phone_country.csv` |",
      "| `ip_city/ip_province/country/city` 基础列 | 全部场景为空；IP 地理取 `$.para.realIp*` | `results/p1_scene_rows.csv` |", "",
      f"cid × app（同一窗口，全部 LKUS_push 行，`results/p1_cid_app_summary.csv`；`cidOriginEnum` 来自 `request.$.cidOriginEnum`）：", "",
      "| cid | app | cidOriginEnum | 请求 | PASS | REJECT | REVIEW | PASS 占比 |", "|---|---|---|---|---|---|---|---|"]
for r in ca.itertuples():
    L.append(f"| {r.cid} | {'（键不存在）' if r.app == '<absent>' else ('（空字符串）' if r.app == '<empty>' else r.app)} | {r.cid_origin} | {int(r.total):,} | {int(r.PASS):,} | {int(r.REJECT):,} | {int(r.REVIEW):,} | {r.pass_share * 100:.1f}% |")
emk = em.groupby("email_key").n.sum()
L += ["", "「app 为空」在源库里都是 `app` 键不存在" + ("" if (ca.app == "<empty>").any() else "，没有出现空字符串") + "。", "",
      "## 5. 分片键（DR-014 / DR-021）", "",
      "- 见 `dictionary/t_access_log_0000.md`「分片键」：LKUS_push `sharding_key = CONCAT(country_code, phone)`，同一手机号只落一个分片，按分片 `COUNT(DISTINCT sharding_key)` 在**同一窗口、同一分组**内可以直接相加；`uid` 不是分片键，不能相加。",
      "- 2026-08-18 请求参数新增 `fullPhoneNo`，此后 `sharding_key = fullPhoneNo`；分片键规则本身没有变化。",
      "- 非 push 场景的分片键：DR-021。", "",
      "## 6. 短信 vs 邮件（DR-002）", "",
      f"- {W} 窗口 LKUS_push {n7:,} 行全部带非空 `$.para.phoneNo`（`results/p1_chk_consistency.csv` `phone_nonempty`）；带非空 `email` 的 {int(k[k.email_nonempty == 1].n.sum())} 行（{k[k.email_nonempty == 1].n.sum() / n7 * 100:.2f}%），这些行同样带手机号（`results/p1_dr002_email_signals.csv`）。",
      "- 源库**没有**逐行的短信/邮件标记（没有 `l2_scene`）。本包的「短信」口径：`$.para.email` 为空或不存在；非空为邮件候选。Grafana 巡检大盘用 Doris 的 `l2_scene='1001'`（`results/p0_grafana_patrol_panels.md`），两者能否逐行对上需要 Doris（DR-020）。", "",
      "## 7. 其它服务器上「名字像风控」的表（只记名字，未读数据）", "",
      "全量名字扫描（`results/p1_fleet_sweep_mysql.csv`，关键词见 `sql/p1_fleet_sweep_mysql.sql`）的命中大多是别的业务域的「规则 / 策略 / 名单」（告警策略、灰度规则、限流规则、营销触达黑名单、支付场景等），与风控引擎无关。和风控相邻的只有短信侧：", "",
      "| 服务器 / schema | 表 | 表注释 | 估算行数 | UPDATE_TIME (UTC) |", "|---|---|---|---|---|"]
for r in up_t.itertuples():
    L.append(f"| `aws-luckyus-upush-rw` / `{r.TABLE_SCHEMA}` | `{r.TABLE_NAME}` | {esc(r.TABLE_COMMENT)} | {int(r.TABLE_ROWS):,} | {esc(r.UPDATE_TIME)} |")
L += ["", "其中只有 `t_verifycode_filled_statistics`（按日 × 项目 × 提供商 × 区号的发送数/填充数）在本包允许范围内读数（只做 SUM，DR-007）；其余只读元数据（`results/p1_dr007_upush_columns.csv`、`results/p1_dr007_upush_indexes.csv`）。", "",
      "## 8. 字段注释与数据不符", "", "| 表.字段 | 库内注释 | 数据显示 |", "|---|---|---|"]
L += [f"| `{r.table}.{r.column}` | {esc(r.db_comment)} | {esc(r.what_the_data_shows)} |" for r in cvd.itertuples()]
L += ["", "## 9. 未取的数据源", "", "| 来源 | 原因 |", "|---|---|",
      "| Doris `ods_luckyus_iriskcontrol.t_iriskcontrol_log` | 未能获取：Doris 不可达（DR-013 / DR-020） |",
      "| Redshift | 未能获取：`redshift` MCP `list_clusters` 报错 |",
      "| Redis `luckyus-iriskcontrol` 内容 | 只执行 `DBSIZE` / `INFO keyspace`（§3 允许的范围），不读键 |",
      "| upush 其它表的数据 | 只读元数据（§3.2 只放开 `t_verifycode_filled_statistics` 的聚合） |",
      "| `t_oplog`、`t_blacklist`、`t_whitelist`、`t_alarm_recipient` 的内容 | 内容是名单条目或个人信息：只计数 / 只读元数据 |"]
open(os.path.join(PKG, "01_数据源与表清单.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("01 written", len(L))
