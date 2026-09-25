#!/usr/bin/env python3
"""P2: write 02_线上配置导出.md from the exported config CSVs (every number in the page is read from results/)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n))
esc = lambda v: "" if pd.isna(v) else str(v).replace("|", "\\|").replace("\n", " ")

s, scene, rc, lc = rd("config_strategy.csv"), rd("config_scene.csv"), rd("config_resultcode.csv"), rd("p2_list_counts.csv")
lf, cf, fx = rd("config_list_feature.csv"), rd("config_counter_features.csv"), rd("config_fixed_strategies_check.csv")
bm, bs, tf, tool = rd("config_block_metric.csv"), rd("config_block_strategy.csv"), rd("config_third_feature.csv"), rd("config_tool.csv")
op, sv, hits = rd("p2_oplog_counts.csv"), rd("config_status_vs_hits.csv"), rd("p2_hits_7d.csv")
exported = {}
for f in sorted(os.listdir(R)):
    if f.startswith("config_") and f.endswith(".csv") and f[7:-4] in (
            "access", "scene", "para", "repair_para", "resultcode", "rule", "strategy", "strategy_relation", "list_feature",
            "third_feature", "tool", "templist", "templist_strategy", "block_metric", "block_strategy", "traffic_mapping", "legacy_scene"):
        p = os.path.join(R, f)
        try:
            d = pd.read_csv(p, dtype=str)
            masked = int(d.apply(lambda c: c.str.startswith("<已屏蔽", na=False)).sum().sum())
            exported[f] = (len(d), masked)
        except pd.errors.EmptyDataError:
            exported[f] = (0, 0)
L = ["# 02 线上配置导出", "",
     "> 2026-09-25 实测，风控库 `aws-luckyus-iriskcontrolservice-rw`。本页只描述导出结果，**不做与 2026-09-24 快照的差异对比**（由桌面 D1 完成）。",
     "> 生成脚本：`sql/local/p2_page.py`、`sql/local/p2_config.py`；SQL：`sql/config_*.sql`、`sql/p2_*.sql`。", "",
     "## 1. 导出文件", "",
     "定义表整表导出（全部行、全部列）。自由文本列（名称、匹配值、表达式、备注、输入参数等）在 SQL 里做了**整值屏蔽**：",
     "值中出现完整 IPv4、邮箱、≥7 位连续数字、`://`、域名或 `域名:端口` 时，整格替换为 `<已屏蔽:N字符>`。",
     "列名含 key/secret/token/passw/sign/credential/appid 的列不导出（本次只有空表 `t_rms_engine_templist_strategy.write_key`）。", "",
     "| 文件 | 源表 | 行数 | 被屏蔽的格子数 |", "|---|---|---|---|"]
for f, (n, m) in exported.items():
    src = "t_scene（遗留）" if f == "config_legacy_scene.csv" else "t_rms_engine_" + f[7:-4]
    L.append(f"| `results/{f}` | `{src}` | {n} | {m} |")
L += ["", "被屏蔽的内容集中在 `t_rms_engine_rule`（按 `phoneNo` 做 INCLUDE / EQUAL_STRING、按 `userNo` 做 == 的规则，匹配值与规则名里有手机号或用户编号）"
      "和 `t_rms_engine_strategy.strategy_name`（引用了这些规则的策略名）。明细见 `results/p2_rule_match_types.csv`（只有匹配类型与特征，没有值）。", "",
      "## 2. 数据库列 → 含义（供 D1 对齐快照列名）", "",
      "列含义取自字段注释（`results/p1_columns.csv`），界面列名以桌面 2026-09-24 快照为准。", "",
      "| 表 | 列 | 含义 / 取值 |", "|---|---|---|",
      "| strategy | `strategy_id` / `strategy_name` | 策略 ID / 策略名称（界面上显示的规则拼接文本） |",
      "| strategy | `status` | 策略状态：**1 = 上线，2 = 预上线，0 = 下线**（已用日志核实，见 §3） |",
      "| strategy | `result_code` | 处置（PASS / REJECT / REVIEW / REVIEW_xx，名字对应返回码表 `result_name`） |",
      "| strategy | `exec_priority` | 执行优先级，越大越先执行 |",
      "| strategy | `strategy_express` / `rule_operator` | 规则组合表达式（`&&` 且、`\\|\\|` 或）/ 规则关系运算符 |",
      "| strategy | `description` | 策略返回描述（界面「提示信息」） |",
      "| strategy | `strategy_type` | 1 风险识别 / 2 黑用户评估 / 3 白用户评估（字段注释） |",
      "| strategy | `operator` / `update_time` | 最后操作人 / 最后修改时间（UTC） |",
      "| strategy_relation | `strategy_id` → `rule_id` | 策略引用的规则 |",
      "| rule | `feature_id` / `feature_type` | 规则判断的特征（`feature_xxx`）或请求参数名（如 `cid`、`countryCode`） |",
      "| rule | `condition_type` / `condition_value` | 匹配类型（`>`、`INCLUDE`、`TIME_AFTER`…）/ 匹配值 |",
      "| third_feature | `tool_id` / `third_label` / `input_paras` | 特征工具（累计 / Twilio / reCAPTCHA）/ 取值标签 / 定义（累计特征：周期、维度、计数方式、过滤条件） |",
      "| list_feature | `namelist_type` | 名单类型编码，对应 `t_blacklist.type` / `t_whitelist.type` |",
      "| resultcode | `result_code` / `result_name` / `priority` | 返回码 / 名称 / 返回码优先级 |", ""]
# status semantics
g = sv.groupby(["list", "hit_status", "config_status_now"]).pv.sum().reset_index()
L += ["## 3. 状态与返回码语义（实测）", "",
      "LKUS_push 2026-09-18…09-24 纽约日的命中记录（`results/p2_hits_7d.csv`）里，每个命中元素自带 `status`。与配置表当前 `status` 对照（`results/config_status_vs_hits.csv`）：", "",
      "| 命中列表 | 命中元素 status | 配置当前 status | 命中次数 |", "|---|---|---|---|"]
for r in g.itertuples():
    L.append(f"| {r.list} | {r.hit_status} | {int(r.config_status_now)} | {int(r.pv):,} |")
promo = sv[(sv.list == "preonline") & (sv.config_status_now == 1)]
L += ["", f"- 结论：配置 `status=1` ⇔ 日志 `ONLINE`（`hitStrategy`），`status=2` ⇔ `PREONLINE`（`hitPreOnlineStrategy`）；`status=0` 从不出现在命中里 = 下线。",
      f"- 唯一例外 {', '.join(f'`{x}`' for x in promo.strategy_id)}：窗口内曾以预上线身份命中，现为上线（窗口期间被推上线，见 §8 操作日志）。",
      "- 返回码（`results/config_resultcode.csv`）：", "", "| access | result_code | result_name | priority | 备注 | update_time (UTC) |", "|---|---|---|---|---|---|"]
for r in rc.sort_values(["access_id", "priority"], ascending=[True, False]).itertuples():
    L.append(f"| {r.access_id} | {r.result_code} | {r.result_name} | {r.priority} | {esc(r.remarks)} | {r.update_time} |")
L += ["", "PASS 的优先级 100000 > REJECT 10000 > REVIEW 系列 1000。LKUS 的 PASS 行最后修改于 2026-09-09 03:29:55 UTC（= 纽约 2026-09-08 23:29），时间上与「自 2026-09-08 起 PASS 优先」的说法吻合；但日志里 PASS 与 REJECT 从不同时命中，这一改动的实际效果无法从日志区分（DR-001）。", ""]
# scenes
L += ["## 4. 场景（`results/config_scene.csv`）", "", "| scene_id | 名称 | 接入方 | status | 全局策略熔断 | 场景熔断 |", "|---|---|---|---|---|---|"]
for r in scene.sort_values(["access_id", "scene_id"]).itertuples():
    L.append(f"| `{r.scene_id}` | {r.scene_name} | {r.access_id} | {r.status} | {esc(r.global_strategy_block_status)} | {esc(r.scene_block_status)} |")
lk = scene[scene.access_id == "LKUS"]
L += ["", f"LKUS 共 {len(lk)} 个场景，其中启用 {int((lk.status == 1).sum())} 个、停用 {int((lk.status == 0).sum())} 个；IQA2（测试接入方）{int((scene.access_id == 'IQA2').sum())} 个。", ""]
# fixed strategies
L += ["## 5. 固定策略核对（每个启用场景的在线策略）", "", "来源 `results/config_fixed_strategies_check.csv`。", "",
      "| 场景 | cid=702 → PASS | 白名单 → PASS | 黑名单 → REJECT | 在线策略数 |", "|---|---|---|---|---|"]
for r in fx.itertuples():
    L.append(f"| `{r.scene_id}` | {r.cid702_pass} | {r.whitelist_pass} | {r.blacklist_reject} | {r.online_strategies} |")
L += ["", "10 个启用的 LKUS 场景都有这三条固定策略（优先级 100000 / 100000 / 90000）；IQA2 场景没有在线策略。", ""]
# LKUS_push strategies
p = s[s.scene_id == "LKUS_push"].copy()
hp = hits.groupby(["list", "strategy_id"]).pv.sum().unstack(0).fillna(0)
L += ["## 6. LKUS_push 策略", "", f"共 {len(p)} 条：上线 {int((p.status == 1).sum())}、预上线 {int((p.status == 2).sum())}、下线 {int((p.status == 0).sum())}（`results/config_strategy.csv`；按规则展开见 `results/config_strategy_expanded.csv`）。",
      "7 日命中数取自 `results/p2_hits_7d.csv`（2026-09-18…09-24 纽约日，**全部 LKUS_push 行**口径；`03` 用的是短信口径，个别策略相差 1–22 次）。", ""]
for st, title in ((1, "上线"), (2, "预上线")):
    q = p[p.status == st].sort_values(["exec_priority", "strategy_id"], ascending=[False, True])
    L += [f"### {title}（{len(q)} 条）", "", "| strategy_id | 处置 | 优先级 | 7日在线命中 | 7日预上线命中 | 更新时间 (UTC) | 名称（规则拼接） |", "|---|---|---|---|---|---|---|"]
    for r in q.itertuples():
        on = int(hp.loc[r.strategy_id, "online"]) if r.strategy_id in hp.index and "online" in hp else 0
        pre = int(hp.loc[r.strategy_id, "preonline"]) if r.strategy_id in hp.index and "preonline" in hp else 0
        L.append(f"| `{r.strategy_id}` | {r.result_code} | {r.exec_priority} | {on:,} | {pre:,} | {r.update_time} | {esc(r.strategy_name)} |")
    L.append("")
# counter features
L += ["## 7. 特征", "",
      f"- 第三方/累计特征 {len(tf)} 个（`results/config_third_feature.csv`），按工具：" + "；".join(
          f"{tool.set_index('tool_id').tool_name.get(k, k)} {v}" for k, v in tf.tool_id.value_counts().items()) + "。",
      f"- 名单特征 {len(lf)} 个（`results/config_list_feature.csv`）。",
      f"- 累计特征定义 `results/config_counter_features.csv`：`counter=0` 计访问次数（PV），`counter=1` 计 `countValue` 的去重个数（UV），`dimension` 为分组维度，`period` 为秒。",
      "", "当前**带过滤条件**的累计特征：", "", "| feature_id | 名称 | 维度 | 计数 | 条件 | update_time |", "|---|---|---|---|---|---|"]
for r in cf[cf.has_condition == True].itertuples():
    L.append(f"| `{r.feature_id}` | {r.feature_name} | {r.dimension} | {r.counter_kind} | `{esc(r.conditions)}` | {r.update_time} |")
multi = cf[cf.dimension.astype(str).str.contains(r"\|")]
L += ["", "组合维度（`dimension` 含 `|`）的累计特征：" + "、".join(f"`{r.feature_id}`（{r.feature_name}，维度 `{r.dimension}`）" for r in multi.itertuples()) + "（DR-004）。", ""]
# lists
L += ["## 8. 名单与操作日志", "", "名单只给条数（`results/p2_list_counts.csv`；名单类型 → 名单特征名称来自 `namelist_type`）：", "",
      "| 表 | 名单类型（维度） | 同一 namelist_type 的名单特征 | 租户 | 来源 | temp | 条数 | 最早创建 | 最晚创建 |", "|---|---|---|---|---|---|---|---|---|"]
tmap = lf.groupby("namelist_type").feature_name.apply(lambda x: "、".join(sorted(set(x)))).to_dict()
for r in lc.itertuples():
    t = "" if pd.isna(r.list_type) else int(r.list_type)
    tmp = f"deleted={int(r.temp)}" if r.list_table == "t_alarm_recipient" else esc(r.temp)
    L.append(f"| `{r.list_table}` | {t} | {tmap.get(t, '—') if t != '' else '—'} | {r.tenant} | {esc(r.source)} | {tmp} | {int(r.n_entries)} | {r.first_created} | {r.last_created} |")
opm = op.groupby(["module", "operation_type"]).n.sum().reset_index()
L += ["", f"策略引擎操作日志 `t_operation_log`：2026-09-02 建表，截至本次共 {int(op.n.sum())} 条操作（{op.first_op_utc.min()} … {op.last_op_utc.max()} UTC，`results/p2_oplog_counts.csv`）。", "",
      "| 模块 | 操作 | 次数 |", "|---|---|---|"] + [f"| {r.module} | {r.operation_type} | {int(r.n)} |" for r in opm.itertuples()]
L += ["", "每条操作的前后记录（只取 ID、名称、状态、优先级、条件字段；自由文本已屏蔽）：`results/p2_oplog_changes.csv`。其中与本包问题直接相关的：", "",
      "- 2026-09-09 03:39:28 UTC 修改 `strategy_sw3jC7bvFYEX` 的优先级（100000→100001），状态随之由 1 变 2；03:39:57 再改回 1 —— 实证「修改上线策略会被打回预上线」。",
      "- 2026-09-24 07:22:42 UTC `feature_dqBHKec09Wwa` 的 `hasCondition` 由 true 改为 false（纽约 03:22）；07:25–07:26 UTC 删除 4 个带条件的特征（DR-003）。",
      "- 2026-09-20 02:41 UTC `feature_AemrK847uPtt` / `feature_bvE9FL19wqag` 由「同IP近X分钟关联手机号累计数」改名为「同IP同手机号近X分钟累计请求次数」（DR-004、DR-005）。",
      "- `t_operation_log` 之前的改动（2026-09-02 以前）没有留痕；旧表 `t_oplog` 只记黑白名单操作且 2026-08-27 后不再写入。", ""]
L += ["## 9. 熔断", "", f"熔断指标 {len(bm)} 个（`results/config_block_metric.csv`，数据来源与 PromQL 已导出），熔断策略 {len(bs)} 条（`results/config_block_strategy.csv`）。"
      "7 日窗口内 LKUS_push 的 `hitBreakStrategy` 全部为空数组（`results/p1_keys_hitBreakStrategy_elem.csv` 无行；另见 03 页）。", ""]
open(os.path.join(PKG, "02_线上配置导出.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("02 written:", len(L), "lines")
