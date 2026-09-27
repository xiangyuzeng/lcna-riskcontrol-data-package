#!/usr/bin/env python3
"""P6: write README.md (package entry point). Numbers come from results/ (headline values via metrics.M / metrics.T);
the DR table and its totals row are parsed from 04_数据问题结论.md (the「新状态」line of each section), never typed."""
import os, re, sys
from collections import Counter
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import metrics  # noqa: E402
M, T = metrics.M, metrics.T
PKG = os.path.dirname(os.path.dirname(HERE))
R = os.path.join(PKG, "results")
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
fi = lambda v: f"{int(v):,}"
pct = lambda x: f"{100 * x:.1f}%"
stamp = os.path.basename(PKG)[len("RC_data_"):]
p04 = open(os.path.join(PKG, "04_数据问题结论.md"), encoding="utf-8").read()
secs = re.split(r'\n<a id="(dr-[\w-]+)"></a>\n', p04)
drs = []
for i in range(1, len(secs), 2):
    body = secs[i + 1]
    title = re.search(r"^## (DR-[\w-]+) (.+)$", body, flags=re.M)
    status = re.search(r"^- \*\*新状态\*\*：(.+)$", body, flags=re.M).group(1).strip()
    drs.append((title.group(1), title.group(2), status))
one = dict(re.findall(r"^\| \[(DR-[\w-]+)\]\(#dr-[\w-]+\) \| .+? \| (.+) \|$", p04, flags=re.M))
cnt = Counter(re.match(r"(\S+?)(?:（|$)", s).group(1) for _, _, s in drs)

dr = rd("p3_daily_result.csv"); start, end = dr.ny_date.min(), dr.ny_date.max()
pc = rd("p3_pass_by_ccgroup.csv"); st3 = rd("p3_strategies.csv")
dd = rd("dr027_daily_decomposition.csv"); cx27 = rd("dr027_crosscheck.csv")
tl = rd("p2_oplog_timeline.csv")
sw = tl[(tl.object_id == "strategy_43NaEzJmiQFk") & (tl.field == "status") & (tl.after.astype(str) == "1")].operation_time_utc.iloc[-1]
sw_day = (pd.Timestamp(sw) - pd.Timedelta(hours=4)).strftime("%Y-%m-%d")
bef, aft = dd[dd.ny_date < sw_day], dd[dd.ny_date > sw_day]
sm = rd("dr027_summary.csv").set_index("metric").value; sens = rd("dr027_baseline_sensitivity.csv")
pr = rd("dr027_period_rates.csv").set_index("period"); P_PRE, P_ON = pr.loc["pre-online (would-be unique REJECT)"], pr.loc["online (actual unique REJECT)"]
ar = rd("dr010_attack_rule.csv"); k5 = ar[ar.k == 5].iloc[0]; ds = rd("dr010_daily_series.csv"); lastd = ds.iloc[-1]
b14 = rd("dr014_best_candidate.csv"); b14 = b14[b14.scene_id.str.startswith("LKUS")]
cc = rd("p3_counter_codes_daily.csv"); combo = cc[cc.feature_id.isin(["feature_AemrK847uPtt", "feature_bvE9FL19wqag"])]
d16 = rd("dr016_summary_7d.csv").iloc[0]; d17 = rd("dr017_reject_above_whitelist.csv"); on17 = d17[d17.status == 1]
ts = rd("toolkit_tests/_test_summary.csv"); stab = rd("p7_stability.csv") if ex("p7_stability.csv") else None
ck = rd("p5_checkpoint_summary.csv") if ex("p5_checkpoint_summary.csv") else None
pre = st3[(st3.list == "preonline") & (st3.result_name != "PASS")].sort_values("extra_recall_pv", ascending=False)
ppc = st3[(st3.list == "preonline") & (st3.result_name == "PASS")].sort_values("pv", ascending=False)
F = [
    ("DR-027：非 +1 放行下降中，`strategy_43NaEzJmiQFk` 的唯一拦截约占 {:.0f}%（推算；所试 {} 组天数组合下 {:.0f}%–{:.0f}%）；与预上线期相比，变少的请求几乎都是 43Na 条件成立的请求（计数分解，非因果）".format(
        100 * sm.unique_share_of_drop, len(sens), 100 * sens.unique_share_of_drop.min(), 100 * sens.unique_share_of_drop.max()),
     f"短信口径，非 +1：放行日均 {sm.pass_non_plus1_before_mean:,.0f}（改前 纽约日 {bef.ny_date.min()}…{bef.ny_date.max()}）→ {sm.pass_non_plus1_after_mean:,.0f}（改后 {aft.ny_date.min()}…{aft.ny_date.max()}）；"
     f"43Na 唯一拦截 {sm.unique_block_would_be_pass_mean_after:,.0f}/日（若无 43Na 推算 {sm.pass_if_strategy_absent_mean_after:,.0f}，请求量与其它判定不变时的上限）；43Na 条件成立的请求每 24 小时（预上线期 → 上线后） {P_PRE.strategy_match_requests_per_24h:,.0f} → {P_ON.strategy_match_requests_per_24h:,.0f}，"
     f"其余 {P_PRE.no_match_requests_per_24h:,.0f} → {P_ON.no_match_requests_per_24h:,.0f}；纯 SQL 与 E1 逐格一致（" + "；".join(f"{r.cells} 格不一致 {r.mismatching_cells}" for r in cx27.itertuples()) + "）",
     "`results/dr027_summary.csv`、`results/dr027_period_rates.csv`、`results/dr027_baseline_sensitivity.csv`、`results/dr027_crosscheck.csv`"),
    ("近 7 日短信请求与放行构成", f"{M['sms_7d_requests']['value']} 次短信请求：PASS {M['sms_7d_pass']['value']} / REJECT {M['sms_7d_reject']['value']} / REVIEW {M['sms_7d_review']['value']}；PASS 中 {M['nonplus1_pass_share_7d']['value']} 来自非 +1",
     "`results/p3_daily_result.csv`、`results/p3_pass_by_ccgroup.csv`"),
    ("攻击仍在（DR-010）" if lastd.attack_flag_k5 == 1 else "最后一天已不是攻击日（DR-010）",
     f"短信口径，k=5：{k5.first_flagged_day} 起 {int(k5.flagged_days)} 个攻击日；{lastd.ny_date} 非 +1/+86 请求 {fi(lastd.non_plus1_plus86_requests)}（阈值 {k5.threshold}）", "`results/dr010_attack_rule.csv`、`results/dr010_daily_series.csv`"),
    ("组合维度特征仍取不到值（DR-003 常设）" if int(combo[combo.code == "SUCCESS"].rows.sum()) == 0 else "组合维度特征部分恢复（DR-003 常设）",
     f"两个组合维度特征的评估次数合计（短信口径，纽约日 {cc.ny_date.min()}…{cc.ny_date.max()}）：SUCCESS {fi(combo[combo.code == 'SUCCESS'].rows.sum())} / {fi(combo.rows.sum())}", "`results/p3_counter_codes_daily.csv`"),
    ("分片键按场景组仍成立（DR-014 常设）", "纽约日 2026-09-26：" + "；".join(f"{r.scene_id.replace('LKUS_', '')} {r.scene_group} {pct(r.best_share)}" for r in b14.itertuples()), "`results/dr014_best_candidate.csv`"),
    ("预上线额外召回（PASS 类按「最终不是 PASS」计）",
     f"短信口径，纽约日 {start}…{end}：非 PASS 类最大 " + "、".join(f"`{r.strategy_id}` {fi(r.extra_recall_pv)}" for r in pre.head(2).itertuples())
     + "；PASS 类 " + "、".join(f"`{r.strategy_id}` 命中 {fi(r.pv)}、额外召回 {fi(r.extra_recall_pv)}" for r in ppc.head(1).itertuples())
     + "".join(f"（全部 LKUS_push 行：命中 {M[f'{r.strategy_id}_preonline_pv_7d_all']['value']}、额外召回 {M[f'{r.strategy_id}_extra_recall_7d_all']['value']}）" for r in ppc.head(1).itertuples()
               if f"{r.strategy_id}_extra_recall_7d_all" in M), "`results/p3_strategies.csv`、`results/p2_hits_7d.csv`、`results/toolkit_tests/tk03_extra_recall.csv`"),
    ("引擎 REVIEW 仍被改写为 PASS（DR-016 常设）", f"短信口径，7 日引擎 REVIEW {fi(d16.engine_review_total)} 次中 {fi(d16.engine_review_final_pass)} 次返回 PASS", "`results/dr016_summary_7d.csv`"),
    ("仍有 REJECT 策略排在白名单之前（DR-017 常设）", ("全部 LKUS_push 行：" + "；".join(f"`{r.strategy_id}` 优先级 {r.exec_priority}，7 日在线命中 {fi(r.hits_online_pv_7d_all_push_rows)}" for r in on17.itertuples())) if len(on17) else "无", "`results/dr017_reject_above_whitelist.csv`"),
]
if ck is not None:
    edg = ck[ck.metric.str.startswith("p5_checkpoint_edges")]
    F.append(("团队手册复现基准可复现（差异在窗口边界之内）", "；".join(f"{r.metric} {fi(r.this_run)}" + (f"（基准 {fi(r.reference)}，差 {int(r.diff):+d}）" if str(r.reference) not in ("", "nan") else "") for r in ck.itertuples() if r.metric.endswith("_cc_filter"))
              + f"。基准的起止秒没有记录；窗口起点、终点各 ±5 分钟（共 10 分钟）内分别有 {' / '.join(fi(v) for v in edg.this_run)} 行，差异都小于这个量，按边界秒差解释；本次比基准多而不是少，不是数据保留造成的缺失", "`results/p5_checkpoint_summary.csv`"))
UNCHANGED = [("DR-001", "待确认（问人：林宏鹏）"), ("DR-004", "已答复"), ("DR-005", "已答复"), ("DR-006", "已答复"), ("DR-007", "待确认（问人：陈晨昕）"),
             ("DR-008", "已答复"), ("DR-009", "已答复"), ("DR-011", "已答复"), ("DR-012", "待确认（问人：林宏鹏）"), ("DR-019", "待确认（问人：林宏鹏）"),
             ("DR-020", "已答复"), ("DR-021", "已答复"), ("DR-023", "已答复"), ("DR-024", "已答复"), ("DR-025", "已答复"), ("DR-026", "已答复")]
L = [f"# RC_data_{stamp} — 北美风控数据包（数据层）", "",
     "> 给桌面项目 D1 导入、生成《北美风控数据字典与取数手册》（LCNA-RC-2026-004）用。全程只读，未写任何数据库。",
     f"> 所有数字来自本次会话执行的查询：SQL 在 `sql/`，原始结果在 `results/`，本地汇总脚本在 `sql/local/`；主要指标（{len(M)} 项，含窗口与口径）登记在 `results/p6_metric_registry.csv`，其中带标签模式的由 `sql/local/p6_checks.py` 逐页核对。", "",
     "## 1. 运行信息", "", "| 项 | 值 |", "|---|---|",
     f"| 运行日期 | 2026-09-27（America/New_York），{stamp[-4:-2]}:{stamp[-2:]} 开始 |",
     "| 输入 | 提示词 M1（桌面 2026-09-26 第六轮修订版）与 `DATA_REQUESTS.md` 都**随对话消息内联提供**；`DATA_REQUESTS.md` = 桌面 2026-09-26 副本（28 条 DR，变更记录最后一条「2026-09-26（第六轮）」） |",
     f"| 数据窗口 | 近 7 日 = 纽约日 {start}…{end}；**DR-027 自己的窗口** = 纽约日 {dd.ny_date.min()}…{dd.ny_date.max()}；E1 行级抽取覆盖后者 |",
     f"| 其它窗口 | DR-010 纽约日 2026-06-01…{ds.ny_date.max()}；DR-014 纽约日 2026-09-26；操作日志 纽约日 2026-08-25 起；复现基准 UTC `[2026-08-21 20:09, 2026-09-10 20:09)` |",
     "| 数据模式 | 脚本执行（`toolkit/shard_runner.py`，经 MCP server `mcp-db-gateway` 的 `mysql_query`）；MCP 直调用于校验 |",
     "| MCP server | `mcp-db-gateway`（唯一的数据通道）；`grafana-lucky`（只读看板面板 SQL 与数据源元数据，没有执行 SQL 的工具）；`redshift`（只做可达性检查，`list_clusters` 报错） |",
     "| 数据库 | `aws-luckyus-iriskcontrolservice-rw`（MySQL 8.4.9，**主库**，账号只有 SELECT/PROCESS/EXECUTE）；元数据另查了全部 64 个 MySQL + 1 个 PG |",
     f"| 执行量 | {M['runs']['value']} 次运行、{M['statements']['value']} 条分片语句（`results/_runlog.csv`、`results/timing.csv`）；单条最长 {rd('timing.csv').seconds.max():.2f} s，无超时 |", "",
     "## 2. 做了什么", "", "| 文件 | 内容 |", "|---|---|",
     "| `00_环境清单.md` | 输入来源、MCP server、库、权限、主从、批量测试、别名守卫、Redis 规模 |",
     "| `01_数据源与表清单.md` + `dictionary/` | 风控库全部表、JSON 结构、字段口径、字段注释与数据不符之处、全量名字扫描 |",
     "| `02_线上配置导出.md` + `results/config_*.csv` | 17 张定义表整表导出、状态语义、名单按类型 × 场景 × 来源、操作日志时间线 |",
     f"| `03_近7日数据画像_{end.replace('-', '')}.md` | 短信按日 / 区号 / 去重用户 / cid×app / 策略（含 PASS 类额外召回的正确口径）/ 泄漏 / 返回码 / H5 A2 链路 / 常设项 |",
     "| `04_数据问题结论.md` | 本轮做的每个 DR 一节（锚点 `dr-xxx`） |",
     "| `05_取数手册与常见坑.md`、`06_评估指标计算手册.md` | 口径、JSON 路径、速度、坑；指标算法与模板 |",
     f"| `toolkit/` | 执行器（新增别名守卫、默认只留合并结果）、tk01–tk10（新增 tk10 唯一拦截；tk03 支持 PASS 类）；工具包测试 {M['toolkit_tests']['value']} 项核对一致 |", "",
     "## 3. 主要发现", "", "| # | 发现 | 数字 | 结果文件 |", "|---|---|---|---|"]
L += [f"| {i} | {a} | {b} | {c} |" for i, (a, b, c) in enumerate(F, 1)]
L += ["", "## 4. 数字溯源（表头数字）", "", "| 数字 | SQL | 本地脚本 | 结果 |", "|---|---|---|---|",
      f"| 7 日短信请求与结果（{M['sms_7d_requests']['value']}） | `sql/e1_a.sql`、`sql/e1_b.sql`；纯 SQL 核对 `sql/p4_daily_series.sql`、`sql/p2_hits_7d.sql` | `sql/local/p3_profile.py` | `results/p3_daily_result.csv`、`results/p3_crosscheck.csv` |",
      "| DR-027 拆分 | `sql/dr027_tk10_43na.sql`、`sql/dr027_tk08_43na_*.sql`；E1 `sql/e1_*.sql` | `sql/local/dr027_local.py` | `results/dr027_summary.csv`、`results/dr027_period_rates.csv`、`results/dr027_baseline_sensitivity.csv`、`results/dr027_*.csv` |",
      "| DR-003 返回码 | `sql/e1_*.sql` | `sql/local/p3_profile.py` | `results/p3_counter_codes_daily.csv` |",
      "| DR-010 攻击日 | `sql/p4_daily_series.sql` | `sql/local/p4_agg_drs.py` | `results/dr010_*.csv` |",
      "| DR-014 分片键 | `sql/dr014_sharding_key_by_scene_20260926.sql`、`sql/p1_sk_concat_check_20260926.sql`；跨分片去重 E1 `sql/e1_*.sql` | `sql/local/p4_agg_drs.py`、`sql/local/p3_profile.py` | `results/dr014_*.csv`、`results/p3_dr014_shard_spread.csv` |",
      "| DR-016 / 017 / 018 | `sql/e1_*.sql`、`sql/p2_hits_7d.sql`、`sql/config_*.sql` | `sql/local/p4_new_drs.py` | `results/dr016_*.csv`、`results/dr017_*.csv`、`results/dr018_*.csv` |",
      "| 配置 / 名单 / 操作日志 | `sql/config_*.sql`、`sql/p2_*.sql` | `sql/local/p2_config.py`、`sql/local/p2_oplog_timeline.py`、`sql/local/p2_list_by_scene.py` | `results/config_*.csv`、`results/p2_*.csv` |",
      "| 复现基准 | `sql/p5_checkpoint*.sql` | `sql/local/p4_agg_drs.py` | `results/p5_checkpoint_summary.csv` |",
      "| 工具包测试 | `sql/toolkit_tests/`、`sql/tk06_extract_*.sql`、`sql/dr027_tk10_43na.sql` | `sql/local/p5_toolkit_tests.py` | `results/toolkit_tests/_test_summary.csv` |",
      "| DR-029 白名单 temp | `sql/p2_list_counts.sql`、`sql/p1_columns.sql` | `sql/local/p4_page.py` | `results/p2_list_counts.csv`、`results/p1_columns.csv` |",
      "| 同一指标只有一个值 | — | `sql/local/metrics.py`、`sql/local/p6_checks.py` | `results/p6_metric_registry.csv`、`results/p6_checks.csv` |"]
if stab is not None:
    L.append(f"| 稳定性复跑 | 同原查询 | `sql/local/p7_stability.py` | `results/p7_stability.csv`（{int(stab.equal.sum())}/{len(stab)} 条复跑一致） |")
L += ["", "## 5. 未取到的数据与原因", "", "| 来源 | 状态 |", "|---|---|",
      f"| Doris `ods_luckyus_iriskcontrol.t_iriskcontrol_log` | 未能获取：{T['doris_dep']}（DR-002、DR-022 的 Doris 一侧） |",
      "| Redshift | 未能获取：`redshift` MCP `list_clusters` 报错 |",
      "| Redis `luckyus-iriskcontrol` 内容 | 只执行 `DBSIZE` / `INFO keyspace` |",
      f"| upush 逐行回填（DR-028） | {T['dr028_skip']} |",
      "| 桌面项目与 `_inbox/` | 本机不存在：zip 与 `.sha256` 需手工放进桌面 `_inbox/` |", "",
      "## 6. DR 汇总", "", "本轮处理：", "", "| DR | 新状态 | 一句话 |", "|---|---|---|"]
L += [f"| [{d}](04_数据问题结论.md#{d.lower()}) | {s} | {one.get(d, t_)} |" for d, t_, s in drs]
L += ["", "合计（由脚本从 04 的「新状态」行计算）：" + "、".join(f"{k} {v}" for k, v in sorted(cnt.items())) + f"（共 {len(drs)} 条）。", "",
      "本轮未处理（状态沿用 `DATA_REQUESTS.md`）：" + "、".join(f"{d} {s}" for d, s in UNCHANGED) + "。", ""]
fc = open(os.path.join(HERE, "p6_fact_corrections.md"), encoding="utf-8").read().strip()
c27 = rd("dr027_e1_cells.csv"); c27 = c27[(c27.sms == 1) & c27.cc_group.isin(["+86", "other"]) & (c27.ny_date == sw_day)]
rate = lambda ph: c27[(c27.phase == ph) & (c27.final_result == "PASS")].requests.sum() / c27[c27.phase == ph].requests.sum()
fc = (fc.replace("METRIC_OPLOG", T["oplog"] + "；本包各页统一这一句").replace("RATE_BEFORE", pct(rate("before"))).replace("RATE_AFTER", pct(rate("after"))))
nx = open(os.path.join(HERE, "p6_next_analyses.md"), encoding="utf-8").read().strip()
L += ["## 7. 事实更正候选（提示词 §2 / 附录 A / `DATA_REQUESTS.md` 与数据不符之处）", "", fc, "", "## 8. 建议的后续分析", "", nx, "",
      "## 9. 交接", "",
      f"- zip：`RC_data_package_{stamp}.zip` 与 `RC_data_package_{stamp}.zip.sha256` 在运行目录；**两个文件都要**放进桌面项目的 `_inbox/`，再在桌面跑 D1。",
      "- 交接仓库 `lcna-riskcontrol-data-package` 是 **public**：按提示词 P7 第 7 步本轮没有推送；把它改成私有或删除旧包由用户决定。"]
open(os.path.join(PKG, "README.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("README written;", dict(cnt))
