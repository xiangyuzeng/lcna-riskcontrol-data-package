#!/usr/bin/env python3
"""P6: write README.md (package entry point). Numbers are read from results/ and the metric registry; the DR totals row is computed
from results/p4_dr_status.csv, which p4_page.py writes from the same status lines as 04."""
import os, sys
from collections import Counter
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics  # noqa: E402
M, T = metrics.M, metrics.T
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
fi = lambda v: f"{int(round(float(v))):,}"
pc = lambda v, d=1: f"{100 * float(v):.{d}f}%"
v = lambda k: M[k]["value"] if k in M else "—"
stt = rd("p4_dr_status.csv")
cnt = Counter(s.split("（")[0] for s in stt.status)
r30 = rd("dr030_retries_summary.csv").iloc[0]; cx30 = rd("dr030_crosscheck_tk10.csv").iloc[0]
sh = rd("dr031_ip_split_share.csv"); s15 = sh[sh.code_set == "15 original"].set_index("ip_geo")
ab = rd("dr031_after_switch_by_cc.csv"); a15 = ab[ab.in_15.astype(str) == "True"].groupby("ip_geo").still_pass.sum()
k5 = rd("dr010_attack_rule.csv").set_index("k").loc[5.0]
rc = rd("p8_counter_recheck_summary.csv"); rr = lambda f, x: pc(rc[(rc.feature_id == f) & rc.variant.str.startswith(x)].share_eq.iloc[0])
e36 = rd("dr036e_nynj_share.csv"); e15 = e36[(e36.basis == "all results") & (e36.code_set == "15 original")].iloc[0]
br = rd("bridge_daily_series.csv").set_index("ny_date")
al = rd("bridge_alert_check.csv").iloc[0]
c3 = rd("dr003_counter_codes_7d.csv"); cb = c3[c3.combo_dimension == 1]
fr35 = rd("dr035_fill_rate_periods.csv"); f35 = lambda per: (lambda x: pc(x, 1 if x >= 0.01 else 2))(fr35[(fr35.period == per) & (fr35.code_set == "15 original")].fill_rate.iloc[0])
cm35 = rd("dr035_completeness.csv"); gap35 = cm35[(cm35.g == "+1") & (cm35.basis == "stats date = UTC day") & (cm35.d >= "2026-09-22") & (cm35.d <= "2026-09-28")].ratio_stats_sent_to_risk_pass
d18 = rd("dr018_time_rule_strategies.csv"); d18 = d18[d18.status.isin([1, 2])]
s12 = rd("dr012_summary.csv", dtype={"cid": str}).set_index(["cid", "group"]); n12 = s12.loc[("105", "no app field")]
cs = rd("config_strategy.csv", dtype=str); gee = cs[cs.result_code.astype(str).str.upper().str.startswith("REVIEW_15")]
h4 = rd("dr034_daily_hits.csv"); eo = h4[(h4.strategy_id == "strategy_eoHQ6Qs0FRqp") & (h4.ny_date == "2026-10-09")].iloc[0]
rt4 = rd("dr034_rates.csv"); r4 = lambda sid, per, m: f"{rt4[(rt4.strategy_id == sid) & (rt4.period == per)][m].iloc[0]:,.1f}"
dp = rd("dr032_province_split.csv"); dpb = dp[(dp.period == "baseline NY 06-01..08-31") & (dp.code_set == "15 original")]
dp_out, dp_all, dp_out_pass = int(dpb[dpb.prov_class == "other"].requests.sum()), int(dpb.requests.sum()), int(dpb[(dpb.prov_class == "other") & (dpb.final_result == "PASS")].requests.sum())
m37 = rd("dr037_members_by_cc.csv", dtype=str, keep_default_na=False); m15 = m37[m37.code_set == "15 original"]
_p = list(m15.with_first_pay); lo37 = sum(int(x) for x in _p if x.isdigit()) + _p.count("<5"); hi37 = lo37 + 3 * _p.count("<5")
empty37 = int(m37[m37.cc == ""].members.iloc[0]) if (m37.cc == "").any() else 0
fr33 = rd("dr033_first_pass_and_rank.csv", dtype={"cc": str}); top33 = fr33[fr33.cc != "1"].head(3)
lch = rd("p2_list_changes.csv") if ex("p2_list_changes.csv") else pd.DataFrame()
wl = rd("p2_list_counts.csv").query("list_table == 't_whitelist' and tenant == 'LKUS'")
bc36 = rd("dr036bcd.csv"); v36 = lambda c, w, m: bc36[(bc36.claim == c) & (bc36.window == w) & (bc36.metric == m)].value.iloc[0]
L = ["# RC_data_20261010-0013 — 北美风控数据包（第四次 M1）", "",
     "## 1. 本包是什么", "",
     "| 项 | 内容 |", "|---|---|",
     "| 开始时间 | 2026-10-10 00:13（America/New_York）；Step A–C 只读侦察与计划从 2026-10-09 22:16 起 |",
     "| 输入 | 提示词 M1、`DATA_REQUESTS.md`（桌面 2026-10-09 副本，38 条 DR，最后一条变更记录「2026-10-09（第八轮，为第四次 M1 准备）：新增 DR-034～DR-038」）与 Part 4 工具包都**随对话消息内联提供** |",
     "| 数据窗口 | 7 日 = 纽约日 2026-10-03…10-09；桥接序列 = 纽约日 09-27…10-09；E1 行级抽取（只在本机）= UTC 2026-09-22 15:00 → 10-10 04:00；L1 长序列 = 纽约日 2026-06-01…10-09 |",
     "| 数据模式 | 脚本执行器 `toolkit/shard_runner.py` 经 MCP server `mcp-db-gateway` 的只读查询工具（地址按用户决定从本机 MCP 配置读入子进程，不落盘）；几条元数据查询直接用 MCP 工具 |",
     "| 数据库 | 风控库 `aws-luckyus-iriskcontrolservice-rw`（**主库**，账号只有 SELECT / PROCESS / EXECUTE）；upush（只读按日汇总表）；salescrm、salesorder（DR-037，只出聚合）。Doris、Redshift 不可达 |",
     "| 取数时段 | 团队规定生产库批量取数只在纽约时间 22:00–06:00；本包全部数据库语句在 2026-10-09 22:17 … 2026-10-10 当晚窗口内完成（`RUN_LOG.md`） |",
     "| 交接 | zip 与 `.sha256` 留在运行目录；桌面 `_inbox/` 不在本机（第 6 步未做）；交接仓库 `lcna-riskcontrol-data-package` 是 public → 第 7 步整步跳过 |", "",
     "## 2. 做了什么", "",
     "- P0 环境与守卫（`00_环境清单.md`）；P1 数据源与字典（`01_数据源与表清单.md`、`dictionary/`）；P2 配置导出两次（开始与结束，`02_线上配置导出.md`）。",
     "- P3 7 日短信画像（`03_近7日数据画像_20261009.md`）；P4 全部 DR（`04_数据问题结论.md`）；开放探索（`05_开放探索_20261009.md`）。",
     "- P5 工具包：Part 4 原文 + 两处改动（生产时段检查、空区间放行）+ 新模板 tk11（绕过监控）；全部模板用本包数据测过（`toolkit/README.md`，" + v("toolkit_tests") + " 项核对一致）。",
     f"- 全部运行 {v('runs')} 次运行、{v('statements')} 条分片语句（`results/_runlog.csv`、`results/timing.csv`）。", "",
     "## 3. 主要发现", "",
     f"1. **共用区号规则被扩，引用它的策略跟着变了**：`rule_CrVrUuDk1hHJ` 2026-10-09 01:55:30 UTC 从 15 个区号扩到 21 个（规则名已同步改）；在线的 WvNG、bYXa 与预上线的 MZQk 随之扩大，三条的策略名仍写 15 个，改规则也没让在线的退回预上线；eoHQ、E1HJ 是之后新建的，一开始就是 21 个（`results/dr031_code_versions.csv`、`results/dr034_timeline.csv`；DR-034）。",
     f"2. **bYXa 的条件在 15 个区号上全部生效，剩下的放行只来自美国 IP 与号码本国 IP**：纽约日 10-02 起 15 个区号的短信请求中，两个 IP 条件都成立的占 {pc(s15.requests_share_within_code_set.get('other', 0))}；上线后仍放行的是美国 IP {fi(a15.get('us', 0))} 次、本国 IP {fi(a15.get('eq_phone', 0))} 次（`results/dr031_ip_split_share.csv`、`results/dr031_after_switch_by_cc.csv`；DR-031）。",
     f"3. **43Na 上线后第一个 24 小时内，它的条件成立的请求就大幅减少；被拒号码约六成会再试**：上线后被它唯一拦下的号码 {fi(r30.numbers_uniquely_rejected)} 个，{pc(r30.share_with_later_request)} 再次请求，距下次请求中位数 {r30.median_minutes_to_next_request} 分钟；tk10 与 E1 逐格一致（{int(cx30.cells)} 格，0 不一致）（`results/dr030_*.csv`；DR-030，计数分解，非因果）。",
     f"4. **MySQL 源库与 Doris 按 UTC 日汇总一致**：UTC 日 09-13…10-08 短信 PASS {v('dr036a_pass_days_equal')} 天与 Doris 完全相同，总量最多差 1（`results/dr036a_utc_daily_vs_doris.csv`；DR-036）。",
     f"5. **攻击仍在**：k=5 下纽约日 09-03…10-09 每天都是攻击日（{v('dr010_attack_days_since_0903')}）；非 +1 占短信 PASS 在 10-08、10-09 降到 {pc(br.loc['2026-10-08', 'non_plus1_share_of_pass'])}、{pc(br.loc['2026-10-09', 'non_plus1_share_of_pass'])}（`results/dr010_attack_rule.csv`、`results/bridge_daily_series.csv`）。",
     f"6. **过滤条件在日志里生效**：按条件重算与引擎值一致 {rr('feature_e1Kmz7JqzsWc', 'after')} / {rr('feature_n91JeGM6gD6i', 'after')}，不按条件只有 {rr('feature_e1Kmz7JqzsWc', 'before')} / {rr('feature_n91JeGM6gD6i', 'before')}（`results/p8_counter_recheck_summary.csv`）；组合维度特征仍 100% `DIMENSION_EMPTY`（DR-003）。",
     "7. **eoHQ 的一条规则名实不符**：`rule_sih7inbv75df` 名称「大于 2」，条件是 `< 2`（10-10 01:17 UTC 改），命中的是每个号码当小时的第一次请求（`results/config_rule.csv`、`results/dr034_daily_hits.csv`；`05_开放探索_20261009.md` §2）。",
     f"8. **「IP 省份不是 NY/NJ 就拒」在正常时期也会拦掉 15 个区号几乎全部请求**：攻击前三个月（纽约日 06-01…08-31）15 个区号的短信请求 {fi(dp_out)}/{fi(dp_all)} 不在 NY/NJ（含 {fi(dp_out_pass)} 次当时放行的）；攻击期 20 天来自 NY/NJ 的约 {pc(e15.nynj_share)}，不是「不到 1%」（`results/dr032_province_split.csv`、`results/dr036e_nynj_share.csv`；DR-032、DR-036）。", "",
     "## 4. 来源对照（主要数字 → SQL → 结果）", "", "| 数字 | SQL | 结果 |", "|---|---|---|",
     f"| 7 日短信请求 {v('sms_7d_requests')} 次（纽约日 10-03…10-09） | `sql/e1.sql`（E1，本机）→ `sql/local/p3_profile.py`；核对 `sql/l1_long.sql`、`sql/p3_tk07_7d.sql` | `results/p3_daily_result.csv`、`results/p3_crosscheck.csv` |",
     f"| 短信 PASS 中 {v('nonplus1_pass_share_7d')} 来自非 +1（7 日） | 同上 | `results/p3_pass_by_ccgroup.csv` |",
     f"| 7 日去重手机号 {v('distinct_phones_7d')}（短信） | 同上 | `results/p3_distinct_users.csv` |",
     f"| 被 43Na 唯一拦下的号码 {v('dr030_numbers_uniquely_rejected')} 个 | `sql/e1.sql` → `sql/local/dr030_local.py`；核对 `sql/dr030_tk10_43na.sql` | `results/dr030_retries_summary.csv`、`results/dr030_crosscheck_tk10.csv` |",
     f"| Doris 对数 PASS {v('dr036a_pass_days_equal')} 天相同 | `sql/l1_long.sql` → `sql/local/l1_drs.py` | `results/dr036a_utc_daily_vs_doris.csv` |",
     f"| 攻击日 {v('dr010_attack_days_since_0903')}（k=5） | `sql/l1_long.sql` → `sql/local/l1_drs.py` | `results/dr010_attack_rule.csv` |",
     f"| {T.get('oplog', '操作日志')} | `sql/p2_oplog_counts.sql`、`sql/p2_oplog_changes.sql` | `results/p2_oplog_counts.csv`、`results/p2_oplog_timeline.csv` |",
     f"| 工具包 {v('toolkit_tests')} 项核对一致 | `sql/toolkit_tests/`、`sql/dr0*` | `results/toolkit_tests/_test_summary.csv` |", "",
     "## 5. 没拿到的数据", "", "| 来源 | 原因 |", "|---|---|",
     f"| Doris `ods_luckyus_iriskcontrol` | 未能获取：{T['doris_dep']}；DR-002、DR-022 写短节 |",
     "| Redshift | 未能获取：`redshift` MCP `list_clusters` 报错 |",
     "| upush 行级表（逐请求回填标签） | DR-028 前提未满足，本次跳过 |",
     "| 纽约日 10-09 的 upush 回填统计 | 统计表在次日 05:30 UTC 以后才写入，本包取数时最新只到 10-08 |",
     "| 会员注册区号 × 订单 | 会员与订单在两台服务器，不能关联（Part 1 第 7 点禁止跨服务器匹配）；改用 salescrm 同库的 `t_user_profile` |", "",
     "## 6. DR 汇总", "", "| DR | 新状态 | 一句话 |", "|---|---|---|"]
ONE = {"DR-030": "上线后第一个 24 小时内，它的条件成立的请求大幅减少；约六成被拒号码再试，中位间隔约 1 分钟（计数分解，非因果）",
       "DR-031": "两个 IP 条件都成立的请求上线后全部被拦；剩余放行来自美国 IP 与本国 IP（计数分解，非因果）；区号规则已扩到 21 个",
       "DR-032": "按「不是 NY/NJ 就拒」，攻击前 15 个区号 " + pc(dp_out / dp_all) + " 的短信请求会被拦；+1 约 87% 在 NY/NJ",
       "DR-033": "按纽约周 × 区号的 PASS 与首次 PASS 日；单价只用于排序",
       "DR-034": "6 条新策略的时间线与逐日命中；WvNG / bYXa 上线后目标区号 PASS 速率依次降到约 1/4、再到约 6 成（计数分解，非因果）",
       "DR-035": "统计表 09-21…09-28 漏记、09-29 起恢复但未补回；15 个区号回填率攻击前就很低",
       "DR-036": "Doris 对数按 UTC 日汇总一致；a、b、d 相符；c 高 7–9 个百分点；e 约 " + pc(e15.nynj_share) + "（不是不到 1%）",
       "DR-037": f"15 个区号已知区号的有消费会员 {lo37}–{hi37} 人；不是上限（{fi(empty37)} 个会员区号为空）",
       "DR-038": "09-21 的 50 次来自 1 个号码，C 段与号码都不在白名单（推断：不是被利用的白名单）",
       "DR-003": "组合维度仍全 DIMENSION_EMPTY；过滤条件生效",
       "DR-010": "攻击从 09-03 起每天都在，到 10-09 未停",
       "DR-012": "105 无 app 仍几乎全是非 +1、版本 1.3.50；106 旧版本像真实用户",
       "DR-013": "Doris 仍不可达", "DR-014": "分片键按场景组仍 100%", "DR-015": "配置两次导出；名单无变化",
       "DR-016": "约三分之二引擎 REVIEW 改写为 PASS，全在 H5", "DR-017": "与群里答复一致；7 日无命中",
       "DR-018": "MZQk 也用 UTC 02:00–09:00；11-01 前要定", "DR-002": "等 Doris 账号", "DR-022": "等 Doris 账号",
       "DR-028": "本次跳过：前提未满足（陈晨昕的口径确认）", "DR-029": "数据已做完，含义待林宏鹏"}
for r in stt.itertuples():
    L.append(f"| [{r.dr}](04_数据问题结论.md#{r.dr.lower()}) | {r.status} | {ONE.get(r.dr, '')} |")
L += ["", "合计（由脚本从 04 的「新状态」行计算）：" + "、".join(f"{k} {n}" for k, n in sorted(Counter(stt.status.str.replace(r'（.*', '', regex=True).str.strip()).items())) + "。", "",
      "## 7. 事实更正候选（提示词 §2 / 附录 A 与数据不符的地方）", "",
      "1. §2.2「编辑在线策略会悄悄退回预上线」只对**策略本身**的编辑成立；本例中改它引用的**规则**没有（`rule_CrVrUuDk1hHJ` 10-09 01:55:30 UTC 扩区号后，WvNG、bYXa 仍是上线，`results/dr034_timeline.csv`、`results/config_strategy.csv`）。",
      "2. §2.2「操作日志 195 次、最后一次 09-24 07:26:13 UTC」已过时：" + T.get("oplog", "") + "。",
      "3. 附录 A DR-018「推送场景 02:00–09:00 UTC 窗口被在线 6cR0 和两条预上线策略使用」：现在还有第三条预上线策略 `strategy_MZQkGORFiZbP`（`results/dr018_time_rule_strategies.csv`）。",
      f"4. DR-036(e) 群里「不到 1%」：实测 20 天约 {pc(e15.nynj_share)}（`results/dr036e_nynj_share.csv`）。",
      f"5. DR-036(c) 群里「60%、加条件后 40%」：实测纽约日 10-08 为 {pc(v36('c', 'NY 10-08', 'share with non-US IP (IP country known and not US)'))} 与 {pc(v36('c', 'NY 10-08', 'share with non-US IP and IP country != phone country'))}，高 7–9 个百分点（`results/dr036bcd.csv`）。", "",
      "## 8. 给桌面：可直接用于群聊的问题与行动项", "",
      "只用汇总数，不含任何能识别个人的信息；该问谁见 `04_数据问题结论.md` 对应 DR 的「该问谁确认」。", "",
      "**待发群的问题**", "",
      "| 问题 | 本包能回答什么（汇总数） | 位置 |", "|---|---|---|",
      f"| bYXa 两个 IP 条件的覆盖（DR-031） | 能：纽约日 10-02 起 15 个区号短信请求中两个条件都成立的占 {pc(s15.requests_share_within_code_set.get('other', 0))}；上线后到纽约日 10-09 结束仍放行的：美国 IP {fi(a15.get('us', 0))} 次、本国 IP {fi(a15.get('eq_phone', 0))} 次 | `04#dr-031`、`results/dr031_*.csv` |",
      f"| 按区号的回填率能否作准确率证据（DR-035） | 部分：15 个区号回填率攻击前 {f35('pre-attack 06-01..09-02')}、09-03…09-20 {f35('attack 09-03..09-20 (before the stats gap)')}、09-29 起 {f35('09-29..last day')}；+1 统计完整度在 09-22…09-28 只有 {gap35.min():.2f}–{gap35.max():.2f}，缺口期不能用；日期时区待确认 | `04#dr-035`、`results/dr035_*.csv` |",
      "| 11-01 夏令时后 UTC 02:00–09:00 窗口（DR-018、DR-034） | 能：用这个窗口的策略 7 日命中：" + "、".join(f"`{r.strategy_id[9:13]}` {'在线' if r.status == 1 else '预上线'} {fi(r.online if r.status == 1 else r.preonline)} 次" for r in d18.itertuples()) + "；11-01 起对应纽约 21:00–04:00 | `04#dr-018`、`results/dr018_time_rule_strategies.csv` |",
      f"| 累计特征过滤条件的 bug 修好没有（第 8 点） | 能：纽约日 10-02…10-09 按条件重算与引擎值一致 {rr('feature_e1Kmz7JqzsWc', 'after')} / {rr('feature_n91JeGM6gD6i', 'after')}，不按条件 {rr('feature_e1Kmz7JqzsWc', 'before')} / {rr('feature_n91JeGM6gD6i', 'before')}；通告所指的具体现象仍需开发说明 | `05_开放探索_20261009.md` §3、`results/p8_counter_recheck_summary.csv` |",
      f"| 白名单 `temp = 1`（DR-029） | 只有数据：LKUS IP C 段白名单 {fi(wl.n_entries.sum())} 条全部 `temp = 1`，字段注释「1 临时，0 永久」；是否会过期要平台说明 | `04#dr-029`、`results/p2_list_counts.csv` |",
      "| 组合维度特征返回 `DIMENSION_EMPTY`（DR-003） | 能：仍 100% `DIMENSION_EMPTY`，" + "、".join(f"`{r.feature_id}` {fi(r.rows)} 次" for r in cb.itertuples()) + "（7 日短信） | `04#dr-003`、`results/dr003_counter_codes_7d.csv` |",
      f"| 名单改动由谁审批 | **数据回答不了**；只能看到 09-27 以后名单新增或修改 {fi(lch.n_entries.sum()) if len(lch) else 0} 条 | `results/p2_list_changes.csv` |",
      f"| 1.4.30 以下旧版 App（DR-012 复测） | 能：7 日 cid 105 无 app {fi(n12.requests)} 次（非 +1 {fi(n12.non_plus1)}、PASS {fi(n12['pass'])}），版本几乎都是 1.3.50；106 旧版本与无 app 几乎全是 +1、全部放行 | `04#dr-012`、`results/dr012_*.csv` |",
      f"| 仍在配置里的极验时期策略 | 能：处置为 REVIEW_15_NINE 的策略 {len(gee)} 条，全部是下线状态（0）；删不删要策略负责人定 | `02` §11、`results/config_strategy.csv` |",
      "| （新）共用区号规则被扩、策略名未改 | 能：规则 15 → 21 个区号（10-09 01:55:30 UTC），WvNG、bYXa、MZQk 三条策略名仍写 15 个 | `05_开放探索_20261009.md` §1 |",
      f"| （新）eoHQ 规则名「大于 2」实为 `< 2` | 能：纽约日 10-09 预上线命中 {fi(eo.preonline_hits)} 次、{fi(eo.preonline_hit_phones)} 个号码（一次命中对应一个号码） | `05_开放探索_20261009.md` §2 |", "",
      "**备份同学的行动项**", "",
      "| 行动项 | 本包提供（汇总数） | 位置 |", "|---|---|---|",
      f"| 每日巡检数 | 桥接序列纽约日 09-27…10-09：短信结果 × 区号组、非 +1 占 PASS（10-08 {pc(br.loc['2026-10-08', 'non_plus1_share_of_pass'])}、10-09 {pc(br.loc['2026-10-09', 'non_plus1_share_of_pass'])}）；滚动 24 小时短信 PASS 的最大值，09-27…10-09 为 {fi(al.max_since_09_27)}，这段时间没有超过 5000 | `03` §10、`results/bridge_daily_series.csv`、`results/bridge_alert_check.csv`；每天跑 `toolkit/patrol.py` |",
      f"| 盯 10-08 新策略有没有被绕过 | WvNG 上线后目标区号 PASS 每 24 小时 {r4('strategy_WvNGjLMgoOyn', 'after: switch -> end NY 10-09', 'pass_per_24h')}、bYXa 上线后 {r4('strategy_bYXaOJ4qXtW4', 'after: switch -> end NY 10-09', 'pass_per_24h')}（之前 {r4('strategy_WvNGjLMgoOyn', 'before: NY 10-02 start -> WvNG online', 'pass_per_24h')}）；tk11 按 IP 类别看目标区号里没被命中而 PASS 的 | `04#dr-034`、`results/dr034_rates.csv`、`results/dr031_tk11_bYXa.csv`、`toolkit/tk11_bypass_watch.sql` |",
      "| 每周按区号的 PASS（费用估算） | 近 7 日 PASS 最多的非 +1 区号：" + "、".join(f"+{r.cc} {fi(r.pass_last_7d)} 次" for r in top33.itertuples()) + "；单价只用于排序，不是账单 | `04#dr-033`、`results/dr033_*.csv` |",
      f"| 高价区号的误伤证据 | 攻击前 15 个区号 {fi(dp_out)}/{fi(dp_all)} 次请求不在 NY/NJ（DR-032）；已知区号的有消费会员 {lo37}–{hi37} 人（DR-037）；攻击前回填率 {f35('pre-attack 06-01..09-02')}（DR-035） | `04#dr-032`、`04#dr-037`、`04#dr-035` |", "",
      "## 9. 建议的后续分析", "",
      "1. bYXa、WvNG 上线一周后，用 tk02 / tk10 / tk11 复看命中量、单独命中量与绕过（按纽约日）。",
      "2. eoHQ 若按现条件上线，先用 E1 方法评估它会拦多少 +1 首次请求（误伤）。",
      "3. 回填口径（`mobile` 存储与回填时点）确认后做 DR-028（逐请求回填标签）。",
      "4. 11-01 夏令时切换前后各一天，按小时看 UTC 时间窗策略的命中平移（DR-018）。",
      "5. Doris 账号到位后补 DR-002、DR-022 的 Doris 一侧。", ""]
open(os.path.join(PKG, "README.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("README written", len(L))
