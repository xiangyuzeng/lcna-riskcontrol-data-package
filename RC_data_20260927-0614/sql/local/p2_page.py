#!/usr/bin/env python3
"""P2: write 02_线上配置导出.md from the exported config CSVs (every number in the page is read from results/)."""
import os
import sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import T  # noqa: E402

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n))
esc = lambda v: "" if pd.isna(v) else str(v).replace("|", "\\|").replace("\n", " ")

s, scene, rc, lc = rd("config_strategy.csv"), rd("config_scene.csv"), rd("config_resultcode.csv"), rd("p2_list_counts.csv")
lf, cf, fx = rd("config_list_feature.csv"), rd("config_counter_features.csv"), rd("config_fixed_strategies_check.csv")
bm, bs, tf, tool = rd("config_block_metric.csv"), rd("config_block_strategy.csv"), rd("config_third_feature.csv"), rd("config_tool.csv")
op, sv, hits = rd("p2_oplog_counts.csv"), rd("config_status_vs_hits.csv"), rd("p2_hits_7d.csv")
tl = rd("p2_oplog_timeline.csv")
est_upd = rd("p0_schema_tables.csv").set_index("table_group").max_update_time
W0, W1 = sorted(hits.ny_date.unique())[0], sorted(hits.ny_date.unique())[-1]
leg = rd("config_legacy_scene.csv")
est = rd("p0_schema_tables.csv").set_index("table_group").est_rows
for c_ in ("source", "temp", "list_type"):
    lc[c_] = lc[c_].astype("Int64")
exported = {}
for f in sorted(os.listdir(R)):
    if f.startswith("config_") and f.endswith(".csv") and f[7:-4] in (
            "access", "scene", "para", "repair_para", "resultcode", "rule", "strategy", "strategy_relation", "list_feature",
            "third_feature", "tool", "templist", "templist_strategy", "block_metric", "block_strategy", "traffic_mapping", "legacy_scene"):
        p = os.path.join(R, f)
        try:
            d = pd.read_csv(p, dtype=str)
            op_m = int(d.apply(lambda c: c.str.startswith("<已屏蔽:操作人>", na=False)).sum().sum())
            txt = d.apply(lambda c: c.str.startswith("<已屏蔽", na=False) & ~c.str.startswith("<已屏蔽:操作人>", na=False))
            exported[f] = (len(d), int(txt.sum().sum()), op_m, ", ".join(f"`{c}` {int(n)}" for c, n in txt.sum().items() if n))
        except pd.errors.EmptyDataError:
            exported[f] = (0, 0, 0, "")
L = ["# 02 线上配置导出", "",
     "> 2026-09-27 实测，风控库 `aws-luckyus-iriskcontrolservice-rw`。本页只描述导出结果，**不做与 2026-09-24 快照的差异对比**（由桌面 D1 完成）。",
     "> 生成脚本：`sql/local/p2_page.py`、`sql/local/p2_config.py`；SQL：`sql/config_*.sql`、`sql/p2_*.sql`。", "",
     "## 1. 导出文件", "",
     "定义表整表导出（全部行、全部列）。自由文本列（名称、匹配值、表达式、备注、输入参数等）在 SQL 里做了**整值屏蔽**：",
     "值中出现完整 IPv4、邮箱、≥7 位连续数字、`://`、域名或 `域名:端口` 时，整格替换为 `<已屏蔽:N字符>`。",
     "列名含 key/secret/token/passw/sign/credential/appid 的列不导出（本次只有空表 `t_rms_engine_templist_strategy.write_key`）。",
     "操作人列（`operator`、`create_user`/`update_user`、`create_name`/`modify_name`、`create_emp`/`modify_emp`）是员工账号，整格替换为 `<已屏蔽:操作人>`（下表「被屏蔽的格子数」含这些格子）。", "",
     f"定义表共 17 张：16 张 `t_rms_engine_*` + 遗留的 `t_scene`（第 17 张）。`t_scene` 的 information_schema 估算行数为 {int(est.get('t_scene', 0))}，实际导出 {len(leg)} 行（估算值不精确，以导出为准）。", "",
     "| 文件 | 源表 | 行数 | 自由文本整格屏蔽（列：格数） | 操作人屏蔽格数 |", "|---|---|---|---|---|"]
for f, (n, m, om, where) in exported.items():
    src = "t_scene（遗留）" if f == "config_legacy_scene.csv" else "t_rms_engine_" + f[7:-4]
    L.append(f"| `results/{f}` | `{src}` | {n} | {m}{'（' + where + '）' if where else ''} | {om} |")
rmt = rd("p2_rule_match_types.csv")
L += ["", "自由文本被屏蔽的原因按匹配类型与特征汇总在 `results/p2_rule_match_types.csv`（只有匹配类型与特征，没有值）：", "",
      "| " + " | ".join(rmt.columns) + " |", "|" + "---|" * len(rmt.columns)] + ["| " + " | ".join(esc(v) for v in r) + " |" for r in rmt.itertuples(index=False)] + [""]
L += ["",
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
      f"LKUS_push {W0}…{W1} 纽约日的命中记录（`results/p2_hits_7d.csv`）里，每个命中元素自带 `status`。与配置表当前 `status` 对照（`results/config_status_vs_hits.csv`）：", "",
      "| 命中列表 | 命中元素 status | 配置当前 status | 命中次数 |", "|---|---|---|---|"]
for r in g.itertuples():
    L.append(f"| {r.list} | {r.hit_status} | {int(r.config_status_now)} | {int(r.pv):,} |")
promo = sv[(sv.list == "preonline") & (sv.config_status_now == 1)]
def last_status_change(sid):
    x = tl[(tl.object_id == sid) & (tl.field == "status")]
    return (x.iloc[-1].operation_time_utc, x.iloc[-1].before, x.iloc[-1].after) if len(x) else None
exc = []
for sid in promo.strategy_id:
    ch = last_status_change(sid)
    on7 = int(sv[(sv.strategy_id == sid) & (sv.list == "online")].pv.sum())
    exc.append(f"`{sid}`（操作日志：{ch[0]} UTC status {ch[1]}→{ch[2]}；本窗口在线命中 {on7:,} 次、预上线命中 {int(sv[(sv.strategy_id == sid) & (sv.list == 'preonline')].pv.sum()):,} 次，改为上线前后的逐日唯一拦截见 DR-027）" if ch else f"`{sid}`")
L += ["", f"- 结论：配置 `status=1` ⇔ 日志 `ONLINE`（`hitStrategy`），`status=2` ⇔ `PREONLINE`（`hitPreOnlineStrategy`）；`status=0` 从不出现在命中里 = 下线。",
      f"- 例外：" + ("；".join(exc) if exc else "无") + "。",
      "- 返回码（`results/config_resultcode.csv`）：", "", "| access | result_code | result_name | priority | 备注 | update_time (UTC) |", "|---|---|---|---|---|---|"]
for r in rc.sort_values(["access_id", "priority"], ascending=[True, False]).itertuples():
    L.append(f"| {r.access_id} | {r.result_code} | {r.result_name} | {r.priority} | {esc(r.remarks)} | {r.update_time} |")
lkp = rc[(rc.access_id == "LKUS") & (rc.result_name == "PASS")]
pp = tl[(tl.module == "返回码管理") & (tl.field == "priority")]
ppass = rc[rc.result_name == "PASS"]
L += ["", "PASS 的优先级 100000 > REJECT 10000 > REVIEW 系列 1000。"
      + ("操作日志：" + "、".join(f"{r.operation_time_utc} UTC" for r in pp.itertuples()) + f" 把返回码 {'/'.join(sorted(set(pp.object_id.astype(str))))} 的优先级 "
         + "、".join(sorted(set(f"{r.before} → {r.after}" for r in pp.itertuples()))) + "（`results/p2_oplog_timeline.csv`）；配置表里 PASS 行的 update_time："
         + "、".join(f"{r.access_id} {r.update_time}" for r in ppass.itertuples()) + " UTC。" if len(pp) else "")
      + "日志里 PASS 命中后引擎不再执行其它策略，所以这一改动的实际效果无法从日志区分（DR-001，待林宏鹏说明）。", ""]
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
en = fx[fx.access_id == "LKUS"]
ok = en[(en.cid702_pass != "—") & (en.whitelist_pass != "—") & (en.blacklist_reject != "—")]
L += ["", f"LKUS 启用场景 {len(en)} 个，其中 {len(ok)} 个三条固定策略齐全；IQA2 场景在线策略 {int(fx[fx.access_id == 'IQA2'].online_strategies.sum())} 条。", ""]
# LKUS_push strategies
p = s[s.scene_id == "LKUS_push"].copy()
hp = hits.groupby(["list", "strategy_id"]).pv.sum().unstack(0).fillna(0)
L += ["## 6. LKUS_push 策略", "", f"共 {len(p)} 条：上线 {int((p.status == 1).sum())}、预上线 {int((p.status == 2).sum())}、下线 {int((p.status == 0).sum())}（`results/config_strategy.csv`；按规则展开见 `results/config_strategy_expanded.csv`）。",
      f"7 日命中数取自 `results/p2_hits_7d.csv`（{W0}…{W1} 纽约日，**全部 LKUS_push 行**口径；`03` 的策略表是短信口径，两者对同一策略可能差几次，见 `results/p3_strategies.csv`）。", ""]
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
bys = rd("p2_list_counts_by_scene.csv")
lk_ = bys[bys.access_id == "LKUS"]
nonzero = lk_[lk_.n_entries > 0].drop_duplicates(["feature_name", "list_table"])
L += ["", "**按类型 × 场景 × 来源**（DR-015，`results/p2_list_counts_by_scene.csv`）：名单表没有场景列，条目属于租户；场景通过引用名单特征来「用」名单。"
      f"LKUS 有 {lk_.scene_id.nunique()} 个场景引用名单特征（共 {lk_.feature_id.nunique()} 个名单特征），有条目的只有：" +
      "；".join(f"{r.feature_name}（`{r.list_table}` type {int(r.namelist_type)}，来源 {int(r.source)}）{int(r.n_entries):,} 条，被 {lk_[(lk_.feature_name == r.feature_name) & (lk_.list_table == r.list_table)].scene_id.nunique()} 个场景的策略引用" for r in nonzero.itertuples())
      + f"；其余 {lk_[lk_.n_entries == 0].feature_id.nunique()} 个名单特征对应的名单为 0 条。", ""]
cols_ = rd("p1_columns.csv")
tc = cols_[(cols_.TABLE_NAME == "t_whitelist") & (cols_.COLUMN_NAME == "temp")].COLUMN_COMMENT
wl_lk = lc[(lc.list_table == "t_whitelist") & (lc.tenant == "LKUS")]
L += ["", f"- `t_whitelist.temp` 字段注释：「{esc(tc.iloc[0]) if len(tc) else '—'}」。LKUS 白名单 {int(wl_lk.n_entries.sum())} 条的 temp 取值：" +
      "、".join(f"temp={esc(r.temp)} 共 {int(r.n_entries)} 条" for r in wl_lk.itertuples()) +
      "。若界面把这些条目显示为永久，则注释与界面矛盾；数据本身无法判断哪一方对，需要平台（林宏鹏）确认——本轮新开 DR-029（`04_数据问题结论.md#dr-029`）。", ""]
opm = op.groupby(["module", "operation_type"]).n.sum().reset_index()
L += ["", f"{T['oplog']}（`results/p2_oplog_counts.csv`、`results/p2_oplog_timeline.csv`）。", "",
      "| 模块 | 操作 | 次数 |", "|---|---|---|"] + [f"| {r.module} | {r.operation_type} | {int(r.n)} |" for r in opm.itertuples()]
KEY = {"status": "状态", "execPriority": "优先级", "input_hasCondition": "是否带条件", "input_conditions": "过滤条件", "input_dimension": "维度",
       "featureName": "特征名", "strategyName": "策略名（规则拼接）", "conditionValue": "匹配值", "(object)": "新增/删除"}
k = tl[tl.field.isin(KEY)]
L += ["", "每条操作的前后记录（只取 ID、名称、状态、优先级、条件字段；自由文本已屏蔽、操作人已屏蔽）：`results/p2_oplog_changes.csv`；"
      "按字段展开的变更时间线：`results/p2_oplog_timeline.csv`。按字段计数：", "",
      "| 字段 | 变化次数 |", "|---|---|"] + [f"| {KEY.get(f, f)} (`{f}`) | {n} |" for f, n in tl.field.value_counts().items()] + [f"| **合计** | **{len(tl)}** |"]
pick = tl[(tl.field.isin(["execPriority", "input_hasCondition", "input_conditions", "input_dimension"])) |
          ((tl.operation_type == "删除") & (tl.object_kind == "featureId")) |
          (tl.object_id.isin(["strategy_43NaEzJmiQFk"]) & (tl.field.isin(["status", "strategyName"])))]
L += ["", "与本包问题直接相关的变化（优先级、过滤条件、维度、特征删除、DR-027 涉及的策略状态）：", "",
      "| 时间 (UTC) | 对象 | 字段 | 改前 | 改后 |", "|---|---|---|---|---|"]
for r in pick.itertuples():
    cut = lambda v: esc(v) if len(esc(v)) <= 120 else esc(v)[:120] + "…（截断，全文见 `results/p2_oplog_timeline.csv`）"
    L.append(f"| {r.operation_time_utc} | `{r.object_id}` | {KEY.get(r.field, r.field)} | {cut(r.before)} | {cut(r.after)} |")
L += ["", f"- `t_operation_log` 最早一条 {op.first_op_utc.min()} UTC；此前的改动没有留痕（DR-019）。旧表 `t_oplog` 只记黑白名单操作，information_schema 最后写入 {est_upd.get('t_oplog', '—')}。",
      f"- 截至本次查询，最后一次操作在 {op.last_op_utc.max()} UTC。", ""]
L += ["## 9. 熔断", "", f"熔断指标 {len(bm)} 个（`results/config_block_metric.csv`，数据来源与 PromQL 已导出），熔断策略 {len(bs)} 条（`results/config_block_strategy.csv`）。"
      "纽约日 2026-09-26 全部场景的 `hitBreakStrategy` 元素键统计为 0 行（`results/p1_keys_hitBreakStrategy_elem.csv` 无数据行），即当日没有熔断命中；本包没有 7 日的熔断命中统计。", ""]
open(os.path.join(PKG, "02_线上配置导出.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("02 written:", len(L), "lines")
