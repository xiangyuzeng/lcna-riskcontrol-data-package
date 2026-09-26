#!/usr/bin/env python3
"""P6: write README.md (package entry point). Numbers are read from results/; the DR table and its totals row are parsed
from 04_数据问题结论.md (the「新状态」line of each section), never typed by hand."""
import glob, os, re
from collections import Counter
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
dr, pc, du, st3 = rd("p3_daily_result.csv"), rd("p3_pass_by_ccgroup.csv"), rd("p3_distinct_users.csv"), rd("p3_strategies.csv")
tot = dr[["sms_PASS", "sms_REJECT", "sms_REVIEW"]].sum(); N = int(tot.sum()); allrows = int(dr.total.sum())
p7 = pc[pc.ny_date == "7d"].iloc[0]; u7 = du[du.ny_date == "7d"].iloc[0]
start, end = dr.ny_date.min(), dr.ny_date.max()
t = rd("timing.csv"); rl = rd("_runlog.csv")
ar = rd("dr010_attack_rule.csv"); k5 = ar[ar.k == 5].iloc[0]
bc = rd("dr021_best_candidate.csv")
e24 = rd("dr024_engine_vs_final.csv"); e24 = e24[e24.sms == 1]
icon = e24[e24.engine_result == "REVIEW_18_ICON"]
app_rev = rd("dr024_app_review_by_day.csv"); a1617 = app_rev[app_rev.ny_date.isin(["2026-09-16", "2026-09-17"])]
d16 = rd("dr016_summary_7d.csv").iloc[0]; d17 = rd("dr017_reject_above_whitelist.csv"); on17 = d17[d17.status == 1]
p3d = rd("dr003_codes_daily_pivot.csv"); last = p3d.ny_date.max()
cmb = p3d[(p3d.ny_date == last) & p3d.feature_id.isin(["feature_AemrK847uPtt", "feature_bvE9FL19wqag"])]
v12 = rd("dr012_cid105_app_vs_noapp_summary.csv").set_index("app_state")
ts = rd("toolkit_tests/_test_summary.csv")
cx = rd("p3_crosscheck.csv")
pre = st3[(st3.list == "preonline") & (st3.result_name != "PASS")].sort_values("extra_recall_pv", ascending=False)
ck = rd("p5_checkpoint_summary.csv") if ex("p5_checkpoint_summary.csv") else None
stab = rd("p7_stability.csv") if ex("p7_stability.csv") else None
push_sk = bc[bc.scene_id == "LKUS_push"]; user_sc = sorted(bc[bc.best_candidates.str.contains("userNo") & bc.scene_id.str.startswith("LKUS")].scene_id.unique())
phone_sc = sorted(bc[bc.best_candidates.str.contains("fullPhoneNo")].scene_id.unique())
F = []
F.append(("近 7 日短信请求近一半被拦，放行里过半是非 +1 号码，最后两天明显回落",
          f"{fi(N)} 次：PASS {fi(tot.sms_PASS)} / REJECT {fi(tot.sms_REJECT)} / REVIEW {fi(tot.sms_REVIEW)}；PASS 中非 +1 占 {pct(p7.non_plus1_share_of_pass)}；{dr.ny_date.iloc[-2]}、{end} 非 +1 占比降到 {pct(pc.iloc[-3].non_plus1_share_of_pass)}、{pct(pc.iloc[-2].non_plus1_share_of_pass)}",
          "`results/p3_daily_result.csv`、`results/p3_pass_by_ccgroup.csv`"))
F.append(("分片键因场景而异（DR-021）", "push / register / captcha = 完整手机号（" + "、".join(f"{r.ny_date} {pct(r.best_share)}" for r in push_sk.itertuples()) + "）；"
          + "、".join(s_.replace("LKUS_", "") for s_ in user_sc) + " = `userNo`（三天均 100%）", "`results/dr021_best_candidate.csv`、`results/dr021_summary.csv`"))
F.append(("App 确实收到过 REVIEW；REVIEW_18_ICON 全部来自 1.4.30 以下版本（DR-024）",
          f"REVIEW_18_ICON {fi(icon.n.sum())} 次（{icon.ny_date.min()}…{icon.ny_date.max()}）全部 <1.4.30；09-16/17 App 的 REVIEW 类引擎结果 {fi(a1617.n.sum())} 次，全部 ≥1.4.30，其中最终返回 REVIEW {fi(a1617[a1617.final_result.str.startswith('REVIEW')].n.sum())} 次",
          "`results/dr024_engine_vs_final.csv`、`results/dr024_app_review_by_day.csv`"))
fr7 = rd("dr007_fill_rate_by_cc.csv", dtype={"cc": str}); fr7b = fr7[fr7.period.str.startswith("base")].set_index("cc")
dg7 = rd("dr007_daily_ccgroup.csv"); dg7 = dg7[dg7.ccg == "+1"]
r_before = dg7[dg7.utc_date <= "2026-09-20"].upush_sent_per_risk_pass; r_after = dg7[(dg7.utc_date >= "2026-09-22") & (dg7.utc_date <= "2026-09-25")].upush_sent_per_risk_pass
F.append(("upush 回填统计表从 2026-09-21 起漏记绝大部分 +1 发送（DR-007）",
          f"+1「统计发送 / 风控放行」09-20 以前 {r_before.min():.2f}–{r_before.max():.2f}，09-22…09-25 {r_after.min():.2f}–{r_after.max():.2f}；{fr7b.period.iloc[0]} +1 回填率 {pct(fr7b.loc['1'].fill_rate)}，+86 {pct(fr7b.loc['86'].fill_rate)}，+92 {pct(fr7b.loc['92'].fill_rate)}",
          "`results/dr007_daily_ccgroup.csv`、`results/dr007_fill_rate_by_cc.csv`"))
F.append(("组合维度特征仍取不到值；`e1Kmz7JqzsWc` 修好后引用它的策略才开始命中（DR-003 / DR-004 / DR-025）",
          f"{last} 两个组合维度特征 DIMENSION_EMPTY {fi(cmb.get('COUNTER_FEATURE_DIMENSION_EMPTY', pd.Series([0])).sum())}/{fi(cmb.rows.sum())}；`strategy_NrsClIxvGxWc` 首次命中在特征修好之后",
          "`results/dr003_codes_daily_pivot.csv`、`results/dr025_hourly_summary.csv`"))
F.append(("`strategy_AxAlIdejVA8m` 改写前的时间窗不可能成立（DR-025）", "改写前（原条件「时间 >22:00 且 <05:00」）命中 0 次；2026-09-14 03:12 UTC 改为 02:00–09:00 后的第一个小时即开始命中；`strategy_43NaEzJmiQFk` 09-23 14:43 UTC 转上线前后命中干净切换",
          "`results/dr025_hourly_summary.csv`、`results/dr025_hourly_hits_43na.csv`"))
F.append(("攻击仍在持续（DR-010）", f"k=5 规则：{k5.first_flagged_day} 起 {int(k5.flagged_days)} 个攻击日（阈值 {k5.threshold}/天非 +1/+86 请求），最近一天仍超阈值", "`results/dr010_attack_rule.csv`、`results/dr010_daily_series.csv`"))
F.append(("105 无 app 的请求全部自报 1.4.30 以下版本、不带 token（DR-012）",
          f"无 app {fi(v12.loc['absent'].rows)} 次：≥1.4.30 占 {pct(v12.loc['absent'].share_ge_min)}、带 token {pct(v12.loc['absent'].share_token_present)}；有 app {fi(v12.loc['present'].rows)} 次：≥1.4.30 占 {pct(v12.loc['present'].share_ge_min)}",
          "`results/dr012_cid105_app_vs_noapp_summary.csv`"))
F.append(("引擎 REVIEW 仍有一部分被改写为 PASS，全部在 H5（DR-016）", f"7 日引擎 REVIEW {fi(d16.engine_review_total)} 次中 {fi(d16.engine_review_final_pass)} 次返回 PASS", "`results/dr016_summary_7d.csv`"))
F.append(("仍有 REJECT 策略排在白名单之前（DR-017）", "；".join(f"`{r.strategy_id}` 优先级 {r.exec_priority}，7 日在线命中 {fi(r.hits_online_pv_7d_all_push_rows)}" for r in on17.itertuples()), "`results/dr017_reject_above_whitelist.csv`"))
F.append(("预上线里额外召回最大的是 PASS 类 `" + st3[(st3.list == 'preonline') & (st3.result_name == 'PASS')].sort_values('pv', ascending=False).strategy_id.iloc[0] + "`；非 PASS 类是 " + "、".join(f"`{s}`" for s in pre.strategy_id.head(2)),
          "；".join(f"`{r.strategy_id}` {fi(r.extra_recall_pv)} 次（非 +1 {fi(r.extra_recall_non_plus1_pv)}）" for r in pre.head(2).itertuples()), "`results/p3_strategies.csv`"))
if ex("dr026_match_summary.csv"):
    ms = rd("dr026_match_summary.csv").iloc[0]
    F.append(("LKUS_captcha 与短信 REVIEW 的对应（DR-026）", f"按手机号：REVIEW {fi(ms.review_rows_with_any_captcha_same_key_same_day)}/{fi(ms.sms_final_review_rows)} 能对上；captcha {fi(ms.captcha_rows_matching_a_review)}/{fi(ms.captcha_rows_day)} 行", "`results/dr026_match_summary.csv`"))
if ck is not None:
    F.append(("团队手册复现基准可复现", "；".join(f"{r.metric} {fi(r.this_run)}" + (f"（基准 {fi(r.reference)}，差 {int(r.diff):+d}）" if str(r.reference) not in ("", "nan") else "") for r in ck.itertuples() if r.metric.endswith("_cc_filter")), "`results/p5_checkpoint_summary.csv`"))
L = [f"# RC_data_{stamp} — 北美风控数据包（数据层）", "",
     "> 给桌面项目 D1 导入、生成《北美风控数据字典与取数手册》（LCNA-RC-2026-004）用。全程只读，未写任何数据库。",
     "> 所有数字来自本次会话执行的查询：SQL 在 `sql/`，原始结果在 `results/`，本地汇总脚本在 `sql/local/`。", "",
     "## 1. 运行信息", "", "| 项 | 值 |", "|---|---|",
     f"| 运行日期 | 2026-09-26（America/New_York），{stamp[-4:-2]}:{stamp[-2:]} 开始 |",
     f"| 数据窗口 | 近 7 日 = 纽约日 {start}…{end}，UTC `[{start} 04:00, {(pd.Timestamp(end) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')} 04:00)`；E1 另含 {(pd.Timestamp(start) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')} 暖机日 |",
     "| 其它窗口 | DR-003 纽约日 2026-08-25…09-25；DR-010 2026-06-01…09-25；DR-024 2026-08-25…09-24；DR-025 UTC 2026-09-06…09-27；DR-007 UTC 日 2026-08-25 起；复现基准 UTC `[2026-08-21 20:09, 2026-09-10 20:09)` |",
     f"| 数据模式 | 脚本执行（`toolkit/shard_runner.py`，经 MCP server `mcp-db-gateway` 的 `mysql_query`）；MCP 直调用于校验（8/8 行一致） |",
     "| 数据库 | `aws-luckyus-iriskcontrolservice-rw`（MySQL 8.4.9，**主库**，账号只有 SELECT/PROCESS/EXECUTE）；upush `aws-luckyus-upush-rw` 只读了一张按日汇总表；元数据另查了全部 64 个 MySQL + 1 个 PG |",
     f"| 执行量 | {len(rl):,} 次运行、{len(t):,} 条分片语句（`results/_runlog.csv`、`results/timing.csv`）；单条最长 {t.seconds.max():.2f} s，无超时 |",
     "| DR 清单 | 用户在运行中提供的 `DATA_REQUESTS.md`（2026-09-26 版，未放在运行目录）；开始时按提示词附录 A 执行，收到后按清单补齐（见 RUN_LOG） |", "",
     "## 2. 做了什么", "", "| 文件 | 内容 |", "|---|---|",
     "| `00_环境清单.md` | MCP server、库、权限、主从、批量大小测试、Redis 规模、Grafana 面板 SQL |",
     "| `01_数据源与表清单.md` + `dictionary/` | 风控库全部表（角色、规模、字段、索引）、JSON 结构、字段口径、字段注释与数据不符之处、全量名字扫描 |",
     "| `02_线上配置导出.md` + `results/config_*.csv` | 17 张定义表整表导出（自由文本整值屏蔽、操作人屏蔽）、状态语义、名单条数（含按场景）、操作日志时间线 |",
     f"| `03_近7日数据画像_{end.replace('-', '')}.md` | 短信按日 / 区号 / 去重用户 / cid×app / 策略 / 泄漏 / 返回码 / H5 A2 链路 / 常设项 DR-016–018 |",
     "| `04_数据问题结论.md` | 每个 DR 一节（锚点 `dr-xxx`） |",
     "| `05_取数手册与常见坑.md` | 口径、JSON 路径、批量与速度、坑 |",
     "| `06_评估指标计算手册.md` | 调用量、用户量、同期、命中、额外召回、准确率、规则复核、巡检、tk08/tk09、OTP 回填率 |",
     f"| `toolkit/` | 执行器、守卫、9 个模板（tk01–tk09，新增 tk08/tk09）、合并脚本、巡检、隐私扫描；测试 {int(ts.equal.sum())}/{len(ts)} 项一致 |", "",
     "## 3. 主要发现", "", "| # | 发现 | 数字 | 结果文件 |", "|---|---|---|---|"]
L += [f"| {i} | {a} | {b} | {c} |" for i, (a, b, c) in enumerate(F, 1)]
L += ["", "## 4. 数字溯源（表头数字）", "", "| 数字 | SQL | 本地脚本 | 结果 |", "|---|---|---|---|",
      f"| 7 日短信请求与结果（{fi(N)}；全部 LKUS_push {fi(allrows)}） | `sql/e1_a.sql`、`sql/e1_b.sql`；纯 SQL 核对 `sql/p4_daily_series.sql` | `sql/local/p3_profile.py` | `results/p3_daily_result.csv`、`results/p3_crosscheck.csv`（{int(cx.mismatching_cells.sum())} 个不一致单元格） |",
      f"| 非 +1 放行 {pct(p7.non_plus1_share_of_pass)} | 同上 | 同上 | `results/p3_pass_by_ccgroup.csv` |",
      f"| 7 日去重手机号 {fi(u7.distinct_phones)} / uid {fi(u7.distinct_uids)} | `sql/e1_*.sql` | `sql/local/p3_profile.py` | `results/p3_distinct_users.csv` |",
      "| 策略命中与额外召回 | `sql/p2_hits_7d.sql`；`sql/e1_*.sql` | `sql/local/p3_profile.py` | `results/p2_hits_7d.csv`、`results/p3_strategies.csv` |",
      "| DR-003 / DR-004 返回码 | `sql/dr003_codes_daily.sql` | `sql/local/p4_agg_drs.py` | `results/dr003_codes_summary.csv`、`results/dr003_codes_daily_pivot.csv` |",
      "| DR-007 回填 | `sql/dr007_upush_daily.sql`、`sql/dr007_risk_utc_daily.sql` | `sql/local/p4_agg_drs.py`、`sql/local/p4_new_drs.py` | `results/dr007_*.csv` |",
      "| DR-010 攻击日 | `sql/p4_daily_series.sql` | `sql/local/p4_agg_drs.py` | `results/dr010_*.csv` |",
      "| DR-012 / 016 / 017 / 018 / 023 | `sql/e1_*.sql`、`sql/p2_hits_7d.sql` | `sql/local/p4_new_drs.py` | `results/dr012_*.csv`、`results/dr016_*.csv`、`results/dr017_*.csv`、`results/dr018_*.csv`、`results/dr023_*.csv` |",
      "| DR-021 分片键 | `sql/dr021_sharding_key_by_scene*.sql` | `sql/local/p4_agg_drs.py` | `results/dr021_*.csv` |",
      "| DR-022 午夜归日 | `sql/dr022_reject_per_minute.sql`、`sql/dr022_seconds_*.sql` | `sql/local/p4_agg_drs.py` | `results/dr022_*.csv` |",
      "| DR-024 引擎 vs 最终 | `sql/dr024_engine_vs_final.sql` | `sql/local/p4_agg_drs.py` | `results/dr024_*.csv` |",
      "| DR-025 改动前后命中 | `sql/dr025_hourly_hits.sql`、`sql/dr025_hourly_hits_43na.sql` | `sql/local/p4_agg_drs.py` | `results/dr025_*.csv` |",
      "| DR-026 captcha 对应 | `sql/dr026_captcha_extract.sql`（本机）+ E1 | `sql/local/p4_new_drs.py` | `results/dr026_*.csv` |",
      "| 配置条数 / 状态语义 / 操作日志 | `sql/config_*.sql`、`sql/p2_*.sql` | `sql/local/p2_config.py`、`sql/local/p2_oplog_timeline.py`、`sql/local/p2_list_by_scene.py` | `results/config_*.csv`、`results/p2_*.csv` |",
      "| 复现基准 | `sql/p5_checkpoint*.sql` | `sql/local/p4_agg_drs.py` | `results/p5_checkpoint_summary.csv` |",
      "| 工具包测试 | `sql/toolkit_tests/` | `sql/local/p5_toolkit_tests.py` | `results/toolkit_tests/_test_summary.csv` |"]
if stab is not None:
    L.append(f"| 稳定性复跑 | 同原查询 | `sql/local/p7_stability.py` | `results/p7_stability.csv`（{int(stab.equal.sum())}/{len(stab)} 一致） |")
L += ["", "## 5. 未取到的数据与原因", "", "| 来源 | 状态 |", "|---|---|",
      "| Doris `ods_luckyus_iriskcontrol.t_iriskcontrol_log` | 未能获取：Doris 不可达（gateway 无 `ods_*` 库；`grafana-lucky` 有数据源但没有 SQL 查询工具，DR-020） |",
      "| Redshift | 未能获取：`redshift` MCP `list_clusters` 报错 |",
      "| Redis `luckyus-iriskcontrol` 内容 | 只执行了 `DBSIZE` / `INFO keyspace`（§3 允许的范围） |",
      "| upush 其它表（逐条发送 / 回填） | 只读元数据；§3.2 只放开 `t_verifycode_filled_statistics` 的按日聚合 |",
      "| 桌面项目文件与 `_inbox/` | 本机不存在：未读取；zip 通过交接仓库与手工复制送达 |", "",
      "## 6. DR 汇总", "", "| DR | 新状态 | 一句话 |", "|---|---|---|"]
L += [f"| [{d}](04_数据问题结论.md#{d.lower()}) | {s} | {one.get(d, t_)} |" for d, t_, s in drs]
L += ["", "合计（由脚本从 04 的「新状态」行计算）：" + "、".join(f"{k} {v}" for k, v in sorted(cnt.items())) + f"（共 {len(drs)} 条）。",
      "本轮未处理（沿用 `DATA_REQUESTS.md` 的状态）：DR-001 待确认（问人：林宏鹏）、DR-005 已答复、DR-006 已答复、DR-008 已答复、DR-009 已答复、DR-011 已答复、DR-019 待确认（问人：林宏鹏）。", ""]
fc = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "p6_fact_corrections.md"), encoding="utf-8").read().strip()
nx = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "p6_next_analyses.md"), encoding="utf-8").read().strip()
L += ["## 7. 事实更正候选（提示词 §2 / 附录 A / `DATA_REQUESTS.md` 与数据不符之处）", "", fc, "", "## 8. 建议的后续分析", "", nx, "",
      "## 9. 交接", "",
      "- zip：`RC_data_package_" + stamp + ".zip`（+ `.sha256`）在运行目录；同时推送到交接仓库 `lcna-riskcontrol-data-package`（桌面 D1 接受仓库归档 `<repo>-main.zip`）。",
      "- 桌面 `_inbox/` 不在本机：请把 zip 放进桌面项目的 `_inbox/`，然后在桌面跑 D1。"]
open(os.path.join(PKG, "README.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("README written;", dict(cnt))
