#!/usr/bin/env python3
"""Point 8: write 05_开放探索_20261009.md from this run's results (every number read from results/)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
fi = lambda v: f"{int(round(float(v))):,}"
pc = lambda v, d=1: f"{100 * float(v):.{d}f}%"
x1 = rd("x1_codes_weekly.csv", dtype={"cc": str}).set_index("cc")
P, Lw = "pass prior 09-26..10-02", "pass last 10-03..10-09"
RQp, RQl = "requests prior 09-26..10-02", "requests last 10-03..10-09"
x2 = rd("x2_bypass_after_switch.csv"); x3 = rd("x3_shifts.csv"); br = rd("bridge_daily_series.csv").set_index("ny_date")
rc = rd("p8_counter_recheck_summary.csv"); h4 = rd("dr034_daily_hits.csv"); rule = rd("config_rule.csv", dtype=str).set_index("rule_id")
cv = rd("dr031_code_versions.csv", dtype=str); tlx = rd("dr034_timeline.csv", dtype=str)
lch = rd("p2_list_changes.csv") if ex("p2_list_changes.csv") else pd.DataFrame()
eo = h4[(h4.strategy_id == "strategy_eoHQ6Qs0FRqp") & (h4.ny_date == "2026-10-09")].iloc[0]
after = x2[x2.period == "after bYXa online"]
by_geo = after[(~after.new_online_hit.astype(bool)) & (after.final_result == "PASS")].groupby("ip_geo").requests.sum()
not_in = x1[(x1.in_current_country_rule == 0) & (x1.index != "1") & (x1.index != "86") & (x1[Lw] > 0)].sort_values("rank_value_last_week", ascending=False).head(6)
ipn = x3[(x3.dimension == "ip_country_top") & (x3.basis == "requests")].pivot_table(index="value", columns="week", values="n")
r_ = lambda fid, v: rc[(rc.feature_id == fid) & rc.variant.str.startswith(v)].share_eq.iloc[0]
F = []


def add(title, evidence, q, who, rel):
    F.append((title, evidence, q, who, rel))


tlo = rd("p2_oplog_timeline.csv", dtype=str); tlo = tlo[tlo.operation_time_utc >= "2026-09-27"]
kinds = tlo.object_kind.value_counts()
x3p = x3[x3.basis == "PASS"]
sh3 = lambda dim, val, wk: x3p[(x3p.dimension == dim) & (x3p.value.astype(str) == val) & (x3p.week == wk)].share_within_week.sum()
WP, WL = "prior 09-26..10-02", "last 10-03..10-09"
add("共用的区号规则被扩了，引用它的三条策略跟着变了，策略名没改",
    f"`rule_CrVrUuDk1hHJ` 2026-10-09 01:55:30 UTC 由 {cv.n.iloc[0]} 个区号改成 {cv.n.iloc[-1]} 个，规则名也同步改成了 {cv.n.iloc[-1]} 个（`results/dr031_code_versions.csv`、`results/config_rule.csv`、`results/dr034_timeline.csv`）；"
    "当时已引用它的在线 `strategy_WvNGjLMgoOyn`、`strategy_bYXaOJ4qXtW4` 与预上线 `strategy_MZQkGORFiZbP` 随之扩大，三条的策略名仍写 15 个区号，WvNG、bYXa 改后仍是上线；"
    "预上线的 eoHQ、E1HJ 是扩容之后（10-10 01:26、02:36 UTC）新建的，一开始就是 21 个（`results/config_strategy_relation.csv`、`results/dr034_strategies.csv`）。",
    "「10-09 把 6 个区号加进了共用的区号规则，WvNG、bYXa、MZQk 也一起扩到了 21 个区号，但这三条的策略名还是 15 个。这是有意的吗？以后改共用规则时要不要同步改策略名，或者给每条策略单独一份规则？」", "段枝宏",
    "补充 Part 2 §2.2「改在线策略会退回预上线」：本例中改**规则**没有让引用它的在线策略退回预上线（DR-034）。")
add("eoHQ 的一条规则：名字写「大于 2」，条件是「小于 2」",
    f"`rule_sih7inbv75df` 名称「{rule.loc['rule_sih7inbv75df', 'rule_name']}」，条件 `{rule.loc['rule_sih7inbv75df', 'condition_type']} {rule.loc['rule_sih7inbv75df', 'condition_value']}`（`results/config_rule.csv`）；2026-10-10 01:17:16 UTC 由 `>` 改成 `<`（`results/dr034_timeline.csv`）。"
    f"预上线的 `strategy_eoHQ6Qs0FRqp` 10-10 01:26 UTC 才建，所以纽约日 10-09 只覆盖 21:26–24:00：这段时间命中 {fi(eo.preonline_hits)} 次、{fi(eo.preonline_hit_phones)} 个号码，一次命中对应一个号码（`results/dr034_daily_hits.csv`）。推断：命中的是每个号码当小时的第一次请求，而不是「访问次数大于 2」。",
    "「eoHQ 里『同手机号近1小时的访问次数 大于 2』这条规则，条件实际是小于 2，10-09 晚上两个半小时的命中都是一个号码一次。是要拦第一次请求，还是名字对、条件写反了？」", "段枝宏（贡锁泉复核）",
    "新问题；影响 eoHQ 上线前的评估（DR-034）。")
add("过滤条件在日志里是生效的（09-24 通告的问题看不到）",
    f"纽约日 10-02…10-09 重算：`feature_e1Kmz7JqzsWc` 按条件过滤后与引擎值一致 {pc(r_('feature_e1Kmz7JqzsWc', 'after'))}、不过滤 {pc(r_('feature_e1Kmz7JqzsWc', 'before'))}；`feature_n91JeGM6gD6i` {pc(r_('feature_n91JeGM6gD6i', 'after'))} / {pc(r_('feature_n91JeGM6gD6i', 'before'))}；同维度同窗口的无条件特征校准 {pc(r_('feature_dtoJoDcUgCcr', 'calib'))}、{pc(r_('feature_UOJYBEifd5Jn', 'calib'))}（`results/p8_counter_recheck_summary.csv`，逐日 `results/p8_counter_recheck_daily.csv`）。",
    "「节后日志里，两个带过滤条件的累计特征都按条件计数（重算和引擎值基本一致）。09-24 说的『配置过滤条件无法生效』具体是哪种情况？修好了吗？在确认前，新建带条件的累计特征可以放开吗？」", "贡锁泉",
    "与 2026-09-25 包 DR-003 一致（那时也看到过滤生效）；本轮在 10-01 之后复核仍成立。")
add("bYXa 上线后，目标区号里还在放行的只剩美国 IP 和本国 IP",
    f"bYXa 上线后到纽约日 10-09 结束（UTC 10-09 01:44 → 10-10 04:00），目标区号里没被新策略命中、最终 PASS 的：美国 IP {fi(by_geo.get('us', 0))} 次、本国 IP {fi(by_geo.get('eq_phone', 0))} 次、其它 {fi(by_geo.get('other', 0))} 次（`results/x2_bypass_after_switch.csv`；按区号见 `results/x2_nonplus1_pass_after_byxa.csv`）。",
    "「bYXa 把『IP 不在美国且不在号码本国』的都拦住了。剩下的放行来自美国 IP 和号码本国 IP——美国 IP 那部分要不要靠 eoHQ 的『省份不是纽约/新泽西』来补？按 DR-032，这条在攻击前也会拦掉这些区号 99% 的请求，误伤怎么评估？本国 IP 那部分要不要看回填率再定？」", "段枝宏",
    "支持 DR-031 的拆分结论；省份条件的暴露面见 DR-032，会员数见 DR-037。")
add("不在 21 个区号里、单价较高、近一周有放行的区号",
    "近 7 日（纽约日 10-03…10-09）有短信 PASS、但不在现行 21 个区号里的区号，按提示词给的 Twilio 公开价 × PASS 排序（只用于排序，不是瑞幸的账单）："
    + "；".join(f"+{c}（{r.phone_country}，PASS {fi(r[P])} → {fi(r[Lw])}，请求 {fi(r[RQp])} → {fi(r[RQl])}，公开价 ${r.usd_public_price}）" for c, r in not_in.iterrows())
    + "（前一周 09-26…10-02 → 近一周 10-03…10-09，`results/x1_codes_weekly.csv` 的 `rank_value_last_week` 列）。",
    f"「+62（印度尼西亚）不在 21 个区号里，近一周请求是前一周的 {x1.loc['62', RQl] / x1.loc['62', RQp]:.2f} 倍（{fi(x1.loc['62', RQp])} → {fi(x1.loc['62', RQl])}）、PASS 是 {x1.loc['62', Lw] / x1.loc['62', P]:.2f} 倍（{fi(x1.loc['62', P])} → {fi(x1.loc['62', Lw])}），公开单价在这几个里最高。要不要加进区号规则？其余几个量还小，先观察吗？」", "段枝宏（David 出数）",
    "延续 10-08 段枝宏「看有哪些价格高的国家没在策略里」的要求；周序列见 DR-033。")
add("马拉维（+265）号码一周翻倍；斯洛文尼亚 IP 变多",
    f"+265 短信请求 {fi(x1.loc['265', RQp])} → {fi(x1.loc['265', RQl])}、PASS {fi(x1.loc['265', P])} → {fi(x1.loc['265', Lw])}（前一周 09-26…10-02 → 近一周 10-03…10-09，`results/x1_codes_weekly.csv`）；非 +1 短信请求里 IP 国家为斯洛文尼亚的 {fi(ipn.loc['斯洛文尼亚', WP])} → {fi(ipn.loc['斯洛文尼亚', WL])}、美国 IP {fi(ipn.loc['美国', WP])} → {fi(ipn.loc['美国', WL])}（`results/x3_shifts.csv`）。",
    "「近一周马拉维号码的请求翻倍、IP 在斯洛文尼亚的请求明显增多。+265 已经在 21 个区号里；要不要按 IP 国家再看一次（例如斯洛文尼亚 IP 配非斯洛文尼亚号码）？」", "田志鲔",
    "新观察；与 DR-031 的 IP 拆分一起看（DR-031 的按 IP 类拆分在这里仍成立）。")
add("非 +1 放行占比在 10-08、10-09 明显下降（计数，不是因果）",
    f"非 +1 占短信 PASS：纽约日 10-03…10-07 在 {pc(br.loc['2026-10-03', 'non_plus1_share_of_pass'])}–{pc(br.loc['2026-10-04', 'non_plus1_share_of_pass'])} 之间，10-08 {pc(br.loc['2026-10-08', 'non_plus1_share_of_pass'])}，10-09 {pc(br.loc['2026-10-09', 'non_plus1_share_of_pass'])}（`results/bridge_daily_series.csv`）；同期 WvNG（10-08 03:54 纽约时间上线）与 bYXa（10-08 21:44）上线。",
    "「10-08、10-09 非 +1 放行占比从四成多降到两成左右，时间上和 WvNG、bYXa 上线对得上。要不要按『上线后看命中量和单独命中量』的口径，每天在群里报一次这两条的数？」", "段枝宏",
    "与 09-29 段枝宏「上线后看命中量和单独命中量」一致；每 24 小时速率见 DR-034。计数时间重合不等于因果。")
add("分数、cid、版本两周几乎没变",
    f"非 +1 短信 PASS 中 V3 ≥0.8 的占比前一周 {pc(sh3('v3_bucket', '>=0.8', WP))}、近一周 {pc(sh3('v3_bucket', '>=0.8', WL))}；cid 105 {pc(sh3('cid', '105', WP))} / {pc(sh3('cid', '105', WL))}；版本 <1.4.30 {pc(sh3('version_class', '< 1.4.30', WP))} / {pc(sh3('version_class', '< 1.4.30', WL))}（`results/x3_shifts.csv`）；按小时分布 `results/x4_hour_of_day.csv`。",
    f"「非 +1 的放行里，V3 分数 ≥0.8 的两周都占 {pc(sh3('v3_bucket', '>=0.8', WL), 0)} 左右。以 V3 分数为条件的拦截规则对这部分没有作用；以后还要不要加分数阈值类规则，还是改用区号、IP、频次类条件？」", "段枝宏",
    "确认 DR-011（攻击流量分数普遍偏高）仍成立。")
add("09-27 之后的名单与配置改动",
    (("名单：" + "；".join(f"`{r.list_table}` type {r.list_type} {r.change_kind} {int(r.n_entries)} 条" for r in lch.itertuples())) if len(lch) else "名单：09-27 之后黑白名单没有新增或修改（`results/p2_list_changes.csv` 为空；物理删除看不到）。")
    + f"配置：09-27 之后操作日志里 {fi(len(tlo))} 处字段改动，按「时间 × 对象」合并后是 {fi(tlo.groupby(['operation_time_utc', 'object_id']).ngroups)} 笔（规则 {fi(kinds.get('ruleId', 0))} 处、第三方特征 {fi(kinds.get('featureId', 0))} 处、策略 {fi(kinds.get('strategyId', 0))} 处，`results/p2_oplog_timeline.csv`；涉及的策略见 `results/dr034_timeline.csv`）。",
    f"「09-27 以后改了 {fi(tlo.groupby(['operation_time_utc', 'object_id']).ngroups)} 次规则、特征和策略，其中一次改的是在线策略共用的规则。这些改动有没有审批或通知？以后要不要每次改完在群里贴一行（改了什么、影响哪些在线策略）？」", "段枝宏",
    "名单部分与 DR-015 一致；配置改动是 DR-034 的输入。")
L = ["# 05 开放探索（纽约日 2026-09-25…10-09）", "",
     "> Part 1 第 8 点要求的开放探索：找改变以前结论或带来新问题的东西。数据：E1（本机行级抽取，只出计数）、L1、配置导出与操作日志。每条写：证据（文件与数字）→ 一个可以直接发群的问题（找谁）→ 它证实或改写了以前的哪条结论。",
     "> 单价只用于排序，不是瑞幸的账单。所有比较只是计数，不是因果。", ""]
for i, (t, e, q, w, rel) in enumerate(F, 1):
    L += [f"## {i}. {t}", "", f"- **证据**：{e}", f"- **可发群的问题**：{q}", f"- **找谁**：{w}", f"- **与以前结论的关系**：{rel}", ""]
L += ["## 没有新开 DR", "", "以上发现需要的数据本轮都拿到了；剩下的都是要人回答的问题，没有新开 DR-039。", ""]
open(os.path.join(PKG, "05_开放探索_20261009.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("05 explore written", len(F))
