#!/usr/bin/env python3
"""P4: write 04_数据问题结论.md. Every number is read from results/ (runner outputs and local aggregates of this run);
the per-DR status lines are also written to results/p4_dr_status.csv (README totals are computed from it)."""
import os
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import T  # noqa: E402

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
fi = lambda v: f"{int(round(float(v))):,}"
fi1 = lambda v: f"{float(v):,.1f}"
pc = lambda v, d=1: f"{100 * float(v):.{d}f}%"
L = ["# 04 数据问题结论", "",
     "> 2026-10-10 生成。数据窗口：7 日 = 纽约日 2026-10-03…10-09；桥接序列 = 纽约日 09-27…10-09；E1 行级抽取 = UTC 2026-09-22 15:00 → 10-10 04:00（只在本机）；L1 长序列 = 纽约日 2026-06-01…10-09。",
     "> 口径：「短信」= `$.para.email` 为空或不存在（DR-002）；「全部行」= 全部 LKUS_push 行。每个数字都标了口径与窗口；去重手机号只在同一窗口、同一分组内有效，不跨天、不跨组相加。",
     "> DR 清单来自内联的 `DATA_REQUESTS.md`（桌面 2026-10-09 副本，38 条）。本轮分类：运行 DR-030…038；常设 DR-003、010、012（复测）、013、014、015、016、017、018；短节 DR-002、022；跳过 DR-028、029。", ""]
ST = []


def sec(dr, title, q, sql, res, concl, conf, who, status):
    global L
    L += [f'<a id="{dr.lower()}"></a>', "", f"## {dr} {title}", "",
          f"- **问题**：{q}", f"- **SQL**：{sql}", f"- **结果**：{res}", f"- **结论**：{concl}", f"- **置信度**：{conf}",
          f"- **该问谁确认**：{who}", f"- **新状态**：{status}", ""]
    ST.append({"dr": dr, "title": title, "status": status})


# ---------------- DR-030 ----------------
if ex("dr030_period_rates.csv"):
    pr = rd("dr030_period_rates.csv"); rs = rd("dr030_retries_summary.csv").iloc[0]; tl = rd("dr030_timeline.csv", dtype=str)
    o = pr[pr.cc_group == "other"].set_index("period")
    cx = rd("dr030_crosscheck_tk10.csv").iloc[0] if ex("dr030_crosscheck_tk10.csv") else None
    dist = rd("dr030_retry_distribution.csv")
    po = lambda p, c: fi(o.loc[p, c])
    tline = "；".join(f"{r.operation_time_utc} {r.field}: {r.before if isinstance(r.before, str) else '—'} → {r.after}" for r in tl.itertuples() if r.field in ("(object)", "status"))
    sec("DR-030", "43Na 上线前后按小时的变化与被拒号码的重试",
        "`strategy_43NaEzJmiQFk` 2026-09-23 14:43:34 UTC 转上线前后，它的条件成立的非 +1 短信请求是立即还是逐步减少？被它唯一拦下的号码有没有回来、间隔多长？",
        "E1（`sql/e1.sql`，本机）+ `sql/local/dr030_local.py`；纯 SQL 核对 `sql/dr030_tk10_43na.sql`（tk10）",
        f"时间线（`results/dr030_timeline.csv`）：{tline}。按小时 × 区号组：`results/dr030_hourly.csv`。"
        f"每 24 小时速率（短信，非 +1/+86，`results/dr030_period_rates.csv`）：条件成立的请求 预上线期（{o.loc['pre_online', 'hours']} 小时）{po('pre_online', 'cond_met_per_24h')}"
        f"（前半 {po('pre_online / 1st half', 'cond_met_per_24h')}、后半 {po('pre_online / 2nd half', 'cond_met_per_24h')}）→ 上线后第一个 24 小时 {po('online_first_24h', 'cond_met_per_24h')}"
        f"（前半 {po('online_first_24h / 1st half', 'cond_met_per_24h')}、后半 {po('online_first_24h / 2nd half', 'cond_met_per_24h')}）→ 第 2 天至纽约日 09-26 {po('online_day2_to_09-26', 'cond_met_per_24h')}"
        f" → 纽约日 09-27…10-02 {po('online_NY_09-27_to_10-02', 'cond_met_per_24h')} → 10-03…10-09 {po('online_NY_10-03_to_10-09', 'cond_met_per_24h')}；"
        f"同期全部非 +1/+86 短信请求 {po('pre_online', 'requests_per_24h')} → {po('online_first_24h', 'requests_per_24h')} → {po('online_day2_to_09-26', 'requests_per_24h')} → {po('online_NY_09-27_to_10-02', 'requests_per_24h')} → {po('online_NY_10-03_to_10-09', 'requests_per_24h')}；"
        f"它唯一拦下的 {po('pre_online', 'unique_rejects_per_24h')}（预上线期，按「若上线」计）→ {po('online_first_24h', 'unique_rejects_per_24h')} → {po('online_day2_to_09-26', 'unique_rejects_per_24h')} → {po('online_NY_09-27_to_10-02', 'unique_rejects_per_24h')} → {po('online_NY_10-03_to_10-09', 'unique_rejects_per_24h')}。"
        f"重试（`results/dr030_retries_summary.csv`、`results/dr030_retry_distribution.csv`；号码只在本机用加盐哈希对齐）：上线后被它唯一拦下的号码 {fi(rs.numbers_uniquely_rejected)} 个，其中 {fi(rs.numbers_with_any_later_request)} 个（{pc(rs.share_with_later_request)}）在窗口内再次请求，共 {fi(rs.later_requests_total)} 次；"
        f"距下一次请求的中位数 {rs.median_minutes_to_next_request} 分钟（90 分位 {rs.p90_minutes_to_next_request} 分钟）；{fi(rs.numbers_later_passed)} 个号码后来至少有一次 PASS；{fi(rs.numbers_with_later_request_after_24h)} 个号码在首次被拒 24 小时后仍有请求。"
        + (lambda z: f"基线敏感性（`results/dr030_baseline_sensitivity.csv`）：以预上线期整段 / 前半 / 后半为基线，上线后第一个 24 小时条件成立的请求是基线的 {z('pre_online', 'online_first_24h')} / {z('pre_online / 1st half', 'online_first_24h')} / {z('pre_online / 2nd half', 'online_first_24h')}，纽约日 10-03…10-09 是 {z('pre_online', 'online_NY_10-03_to_10-09')} / {z('pre_online / 1st half', 'online_NY_10-03_to_10-09')} / {z('pre_online / 2nd half', 'online_NY_10-03_to_10-09')}。")(
            lambda b, a: (lambda q: pc(q.ratio_after_to_baseline.iloc[0], 0))(rd("dr030_baseline_sensitivity.csv").query("baseline == @b and after == @a and metric == 'cond_met_per_24h'")))
        + (f"纯 SQL 核对：tk10 与 E1 在 {fi(cx.cells)} 个格子（纽约日 × 区号组 × 阶段 × 最终结果，短信）上请求数不一致 {int(cx.requests_mismatch)} 格、唯一拦截不一致 {int(cx.unique_mismatch)} 格（`results/dr030_crosscheck_tk10.csv`）。" if cx is not None else ""),
        "上线后条件成立的请求在**第一个 24 小时内就降了一大截**（预上线期后半的速率最高，上线后前半最低），之后在数百 / 24 小时的水平上逐步下降，没有回到预上线期的水平；被它唯一拦下的号码约六成在窗口内再次请求、下一次请求的中位间隔约 1 分钟，再试的号码里一半多只再试一两次、其余再试 3 次以上（最多一档 21–50 次），少数在 24 小时后仍回来（分布见 `results/dr030_retry_distribution.csv`）。"
        "**计数分解，非因果**：预上线期只有约 23 小时且正处高峰，上线时刻也可能与攻击方自己的节奏重合；计数分不开「攻击方对 43Na 的反应」与「同时发生的减少」。重试数里同一号码可能也被其它策略拦，`若无 43Na` 的推算只在请求量与其它策略判定不变时成立：重试使它偏高，攻击方减量使它偏低。",
        "中（计数可复核；方向判断依赖时间形状，不是对照实验）", "—（数据）；结论给段枝宏", "已答复")

# ---------------- DR-031 ----------------
if ex("dr031_ip_split_share.csv"):
    cv = rd("dr031_code_versions.csv", dtype=str); sh = rd("dr031_ip_split_share.csv"); ab = rd("dr031_after_switch_by_cc.csv", dtype={"cc": str})
    s15 = sh[sh.code_set == "15 original"].set_index("ip_geo")
    a15 = ab[ab.in_15.astype(str) == "True"].groupby("ip_geo")[["requests", "online_hits", "unique_rejects", "still_pass"]].sum()
    a6 = ab[ab.in_15.astype(str) == "False"][["requests", "online_hits", "unique_rejects", "still_pass"]].sum()
    byc = rd("dr031_ip_split_by_cc.csv", dtype={"cc": str})
    k92 = byc[byc.cc == "92"].set_index("ip_geo").requests
    g = lambda s, k: s.get(k, 0)
    sec("DR-031", "strategy_bYXaOJ4qXtW4 能拦到多少（按 IP 条件拆分）",
        "bYXa 的 15 个区号，按「IP 在美国 / IP 国家 = 号码国家 / 两者都不是（策略条件成立）」拆分的请求与 PASS；状态变化之后的在线命中、仍然放行的数、现行区号列表。",
        "配置 `results/config_strategy.csv`、`results/config_rule.csv`、`results/p2_oplog_timeline.csv`；E1 + `sql/local/dr031_034_local.py`；纯 SQL 核对 `sql/dr034_tk10_bYXa.sql`、`sql/dr031_tk11_bYXa.sql`（tk11）",
        f"区号规则 `rule_CrVrUuDk1hHJ` 的版本（`results/dr031_code_versions.csv`）：创建时 {cv.n.iloc[0]} 个（与 DR 列的 15 个相同），**2026-10-09 01:55:30 UTC 扩成 {cv.n.iloc[-1]} 个**（加 +233、+504、+258、+998、+255、+855）。"
        f"bYXa 2026-10-09 00:56:26 UTC 转预上线、01:44:35 UTC 转上线（`results/dr034_timeline.csv`）。纽约日 10-02 起（短信，全部结果）15 个区号的请求：两者都不是 {pc(g(s15.requests_share_within_code_set, 'other'))}、IP 在美国 {pc(g(s15.requests_share_within_code_set, 'us'))}、IP 国家 = 号码国家 {pc(g(s15.requests_share_within_code_set, 'eq_phone'))}；"
        f"PASS 中三者各占 {pc(g(s15.passes_share_within_code_set, 'other'))} / {pc(g(s15.passes_share_within_code_set, 'us'))} / {pc(g(s15.passes_share_within_code_set, 'eq_phone'))}（`results/dr031_ip_split_share.csv`；逐区号 `results/dr031_ip_split_by_cc.csv`，其中 +92 的 {fi(k92.sum())} 次里两者都不是 {fi(g(k92, 'other'))}、美国 IP {fi(g(k92, 'us'))}、本国 IP {fi(g(k92, 'eq_phone'))}）。"
        f"bYXa 上线后（UTC 10-09 01:44:35 → 10-10 04:00，即到纽约日 10-09 结束，`results/dr031_after_switch_by_cc.csv`）：15 个区号里条件成立的 {fi(g(a15.requests, 'other'))} 次全部在线命中（{fi(g(a15.online_hits, 'other'))}），其中它唯一拦下 {fi(g(a15.unique_rejects, 'other'))} 次；不满足条件、仍然放行的：美国 IP {fi(g(a15.still_pass, 'us'))} 次、本国 IP {fi(g(a15.still_pass, 'eq_phone'))} 次；新加的 6 个区号 {fi(a6.requests)} 次请求、在线命中 {fi(a6.online_hits)}。"
        + (lambda q, h: "每 24 小时速率（15 个区号，短信，按每一次切换分段，`results/dr031_period_rates.csv`；不短于 6 小时的时段再分前后半，`results/dr031_period_halves.csv`）：PASS 按「两者都不是 / 美国 IP / 本国 IP」，"
           + "；".join(f"{lab}（{q[q.period == per].hours.iloc[0]} 小时）" + " / ".join(fi1(q[(q.period == per) & (q.ip_class == k)].pass_per_24h.iloc[0]) for k in ("other", "us", "eq_phone"))
                      + "（前半 " + " / ".join(fi1(h[(h.period == per) & (h.half == '1st half') & (h.ip_class == k)].pass_per_24h.iloc[0]) for k in ("other", "us", "eq_phone"))
                      + "，后半 " + " / ".join(fi1(h[(h.period == per) & (h.half == '2nd half') & (h.ip_class == k)].pass_per_24h.iloc[0]) for k in ("other", "us", "eq_phone")) + "）"
                      for lab, per in (("纽约日 10-02 起到 WvNG 上线", "NY 10-02 start -> WvNG online"), ("MZQk 预上线到 bYXa 预上线", "MZQk pre-online -> bYXa pre-online"),
                                       ("区号规则扩容后到纽约日 10-09 结束", "country rule widened -> end NY 10-09")))
           + "；其余几段都不到 1 小时，只给整段（见表）。逐日 × 区号 × 结果 × IP 类：`results/dr031_daily.csv`。")(rd("dr031_period_rates.csv").query("code_set == '15 original'"), rd("dr031_period_halves.csv"))
        + (lambda q: "基线敏感性（`results/dr031_baseline_sensitivity.csv`；「之后」= 区号规则扩容后到纽约日 10-09 结束，基线 = 之前两段不短于 6 小时的时段）：两个 IP 条件都成立的 PASS 每 24 小时都降到 0；以「" + "」/「".join({"MZQk pre-online -> bYXa pre-online": "MZQk 预上线到 bYXa 预上线", "NY 10-02 start -> WvNG online": "纽约日 10-02 起到 WvNG 上线"}.get(b, b) for b in q[(q.ip_class == "us") & (q.metric == "pass_per_24h")].baseline) + "」为基线，美国 IP 的 PASS 依次是基线的 " + " / ".join(pc(v, 0) for v in q[(q.ip_class == "us") & (q.metric == "pass_per_24h")].ratio_after_to_baseline) + "，本国 IP 的 PASS 是 " + " / ".join(pc(v, 0) for v in q[(q.ip_class == "eq_phone") & (q.metric == "pass_per_24h")].ratio_after_to_baseline) + "。计数分解，非因果。")(rd("dr031_baseline_sensitivity.csv")),
        "bYXa 按设计只拦「IP 不在美国且 IP 国家 ≠ 号码国家」的请求；上线后这部分在 15 个区号上全部被拦，**剩下的放行全部来自美国 IP 和号码本国 IP**。所以要不要补条件，看的是这两类：美国 IP 的那部分正是 DR-032 / DR-037 讨论的「NY/NJ 省份」与误伤问题；本国 IP 的那部分以量最大的 +92 为主——+92 的请求里号码本国（巴基斯坦）IP 占七成多，bYXa 按设计拦不到。"
        "美国 IP 的 PASS 速率与紧挨着的前一段（WvNG 已上线、bYXa 未上线）相比没有减少，与 10-02 起的长基线相比约为四成——这部分的下降在 bYXa 之前就有了（**计数分解，非因果**）。"
        "另外，区号规则 `rule_CrVrUuDk1hHJ` 的名称已随条件改成 21 个区号，但引用它的 WvNG、bYXa（上线）与 MZQk（预上线）的**策略名**仍写 15 个——10-09 01:55 的扩容同时扩大了这三条；eoHQ、E1HJ 是扩容之后（10-10 UTC）新建的，一开始就是 21 个（DR-034）。",
        "高（计数直接来自引擎日志；IP 类别依赖 `realIpCountry` 的准确度）", "—（数据）；结论给段枝宏", "已答复")

# ---------------- DR-032 ----------------
if ex("dr032_province_split.csv"):
    t = rd("dr032_province_split.csv")
    def cnt(pn, sets, prov=None, res=None):
        g = t[(t.period == pn) & t.code_set.isin(sets)]
        if prov:
            g = g[g.prov_class == prov]
        if res:
            g = g[g.final_result == res]
        return int(g.requests.sum())
    B, A, B8 = "baseline NY 06-01..08-31", "attack NY 09-03..10-09", "alt baseline NY 08-01..08-31"
    C15, C21, P1 = ["15 original"], ["15 original", "6 added"], ["+1 control"]
    fr = rd("dr035_fill_rate_periods.csv") if ex("dr035_fill_rate_periods.csv") else None
    f15 = fr[(fr.period == "pre-attack 06-01..09-02") & (fr.code_set == "15 original")].iloc[0] if fr is not None else None
    sec("DR-032", "15 个高价区号的 IP 省份分布（误伤估算）",
        "15 个区号的短信请求按 `realIpProvince` 是否 New York / New Jersey × 最终结果，攻击前基线 vs 攻击期；对照 +1。用来估「省份不是 NY/NJ 就拒」这类规则（eoHQ 的条件之一）在正常时期会拦掉多少。",
        "L1 `sql/l1_long.sql` → `results/l1_long.csv`；`sql/local/l1_drs.py`；省份取值 `results/p1_province_classes.csv`、`results/l1_params.csv`",
        f"15 个区号（短信，全部结果，`results/dr032_province_split.csv`）：基线（纽约日 06-01…08-31）共 {fi(cnt(B, C15))} 次，IP 省份为 NY/NJ 的 {fi(cnt(B, C15, 'nynj'))} 次，**不是 NY/NJ 的 {fi(cnt(B, C15, 'other'))} 次**（其中 PASS {fi(cnt(B, C15, 'other', 'PASS'))}）；"
        f"攻击期（09-03…10-09）共 {fi(cnt(A, C15))} 次，NY/NJ {fi(cnt(A, C15, 'nynj'))} 次，不是 NY/NJ 的 {fi(cnt(A, C15, 'other'))} 次（PASS {fi(cnt(A, C15, 'other', 'PASS'))}）。"
        f"8 月单月作备选基线：{fi(cnt(B8, C15))} 次中不是 NY/NJ 的 {fi(cnt(B8, C15, 'other'))} 次（PASS {fi(cnt(B8, C15, 'other', 'PASS'))}）。按现行 21 个区号算，基线 {fi(cnt(B, C21))} 次中不是 NY/NJ 的 {fi(cnt(B, C21, 'other'))} 次。"
        f"+1 对照：基线 {fi(cnt(B, P1, 'nynj'))}/{fi(cnt(B, P1))} = {pc(cnt(B, P1, 'nynj') / cnt(B, P1))} 落在 NY/NJ，攻击期 {pc(cnt(A, P1, 'nynj') / cnt(A, P1))}。逐区号基线：`results/dr032_baseline_by_cc.csv`。`realIpProvince` 从 6 月起每月都有值（`results/dr032_province_presence_by_month.csv`）。",
        f"如果对 15 个区号用「IP 省份不是 NY/NJ 就拒」，攻击前三个月的短信请求 **{pc(cnt(B, C15, 'other') / cnt(B, C15))} 会被拦**（{fi(cnt(B, C15, 'other'))}/{fi(cnt(B, C15))}，含 {fi(cnt(B, C15, 'other', 'PASS'))} 次当时放行的），只有 {fi(cnt(B, C15, 'nynj'))} 次来自 NY/NJ——这就是这条规则在正常时期的暴露面。"
        + (f"被拦的不一定都是真人：同期 15 个区号的回填率只有 {pc(f15.fill_rate)}（{fi(f15.filled)}/{fi(f15.sent)}，DR-035，upush 按日汇总表）；但回填数不能逐请求对上省份（DR-028），所以不知道回填的那部分在哪个州。" if f15 is not None else "")
        + f"+1 号码约 {pc(cnt(B, P1, 'nynj') / cnt(B, P1), 0)} 落在 NY/NJ、其余在美国其它州：即使是真实用户，也有一部分不在 NY/NJ。省份准确度（段枝宏的顾虑）数据无法验证。",
        "中（计数可靠；哪些是真人要配合 DR-035 回填率、DR-037 会员数一起看）", "—（数据）；结论给段枝宏", "已答复")

# ---------------- DR-033 ----------------
if ex("dr033_weekly_pass_by_cc.csv"):
    w = rd("dr033_weekly_pass_by_cc.csv", dtype={"cc": str}); fr = rd("dr033_first_pass_and_rank.csv", dtype={"cc": str})
    top = fr[fr.cc != "1"].head(6)
    sec("DR-033", "按区号的每周放行量（费用估算用）",
        "短信口径，纽约周（周日开始）× 区号的 PASS，2026-08-01 起；每个区号第一次出现 PASS 的纽约日。",
        "L1 → `sql/local/l1_drs.py`",
        f"`results/dr033_weekly_pass_by_cc.csv`（{w.ny_week_sun.nunique()} 个纽约周 × {w.cc.nunique()} 个区号；首周 08-01 起只有 {int(w[w.ny_week_sun == w.ny_week_sun.min()].days_in_window.iloc[0])} 天、末周到 10-09 为 {int(w[w.ny_week_sun == w.ny_week_sun.max()].days_in_window.iloc[0])} 天，`partial_week` 标出，另给 `pass_per_day`）。"
        f"首次 PASS 日与按公开价排序：`results/dr033_first_pass_and_rank.csv`（序列从 06-01 开始，06-01 当天就有 PASS 的区号标 `left_censored_at_06_01`）。最近 7 日 PASS × 公开单价排前几位的非 +1 区号："
        + "、".join(f"+{r.cc}（{fi(r.pass_last_7d)} 次 PASS，首次 PASS {r.first_pass_ny_date}{'，序列第一天就有，实际首次可能更早（左删失）' if int(r.left_censored_at_06_01) else ''}）" for r in top.itertuples()) + "。",
        "单价只用于排序（提示词给出的 Twilio 公开价，每国取最高运营商价），不是瑞幸的账单；乘出来的金额不要当费用报出去。",
        "高（计数）", "—（数据）", "已答复")

# ---------------- DR-034 ----------------
if ex("dr034_strategies.csv"):
    s4 = rd("dr034_strategies.csv", dtype=str); h4 = rd("dr034_daily_hits.csv"); tl4 = rd("dr034_timeline.csv", dtype=str)
    hh = h4[h4.ny_date >= "2026-10-08"].groupby(["strategy_id", "ny_date"])[["online_hits", "online_unique_reject", "preonline_hits", "preonline_unique_recall"]].sum()
    SN = {"0": "下线", "1": "上线", "2": "预上线"}
    def tline(sid):
        x = tl4[(tl4.object_id == sid) & tl4.field.isin(["(object)", "status"])]
        return " → ".join(("新建 " if r.field == "(object)" else SN.get(r.after, r.after) + " ") + r.operation_time_utc[5:] for r in x.itertuples())
    desc = []
    for r in s4.itertuples():
        st_ = SN.get(r.status, r.status)
        x = hh.loc[r.strategy_id] if r.strategy_id in hh.index.get_level_values(0) else None
        hs = "；".join(f"纽约日 {d}：在线 {fi(v.online_hits)}（唯一拦截 {fi(v.online_unique_reject)}）、预上线 {fi(v.preonline_hits)}（单独召回 {fi(v.preonline_unique_recall)}）" for d, v in x.iterrows()) if x is not None else "—"
        desc.append(f"`{r.strategy_id}`（现行{st_}，{r.result_code}，优先级 {r.exec_priority}；{hs}）")
    rt = rd("dr034_rates.csv"); sn = rd("dr034_baseline_sensitivity.csv")
    R4 = lambda sid, per, m: fi1(rt[(rt.strategy_id == sid) & (rt.period == per)][m].iloc[0])
    W, Y = "strategy_WvNGjLMgoOyn", "strategy_bYXaOJ4qXtW4"
    B0, AF, WB = "before: NY 10-02 start -> WvNG online", "after: switch -> end NY 10-09", "before: WvNG online -> bYXa online"
    HR = lambda sid, per: rt[(rt.strategy_id == sid) & (rt.period == per)].hours.iloc[0]
    halves = lambda sid, per, m: f"前半 {R4(sid, per + ' / 1st half', m)}、后半 {R4(sid, per + ' / 2nd half', m)}"
    ratios = lambda sid, base_prefix: " / ".join(pc(v, 1) for v in sn[(sn.strategy_id == sid) & sn.baseline.str.startswith(base_prefix) & (sn.metric == "pass_per_24h")].ratio_after_to_baseline)
    sec("DR-034", "09-27 以后新建或改动的策略：状态时间线、表达式与命中",
        "09-27 之后新建或改动过的策略（含规则 / 特征被改的）：操作日志里的状态变化时间、现行状态、优先级、处置、完整表达式；按纽约日的在线、预上线与单独命中（短信）。",
        "配置导出 + `results/p2_oplog_timeline.csv`；E1 + `sql/local/dr031_034_local.py`、`sql/local/dr034_rates_local.py`；纯 SQL 核对 `sql/dr034_tk10_WvNG.sql`、`sql/dr034_tk10_bYXa.sql`、`sql/dr034_tk02_MZQk_sms.sql`",
        "**时间线（UTC，`results/dr034_timeline.csv`）**：" + "；".join(f"`{r.strategy_id}` {tline(r.strategy_id)}" for r in s4.itertuples())
        + "；共用区号规则 `rule_CrVrUuDk1hHJ` 10-08 07:51 新建（15 个区号），10-09 01:55:30 扩成 21 个。"
        + f"**每 24 小时速率**（按现行 21 个区号、短信，`results/dr034_rates.csv`）：纽约日 10-02 起到 WvNG 上线（{HR(W, B0)} 小时）请求 {R4(W, B0, 'requests_per_24h')}、PASS {R4(W, B0, 'pass_per_24h')}（{halves(W, B0, 'pass_per_24h')}）；"
        f"WvNG 上线后到纽约日 10-09 结束（{HR(W, AF)} 小时）请求 {R4(W, AF, 'requests_per_24h')}、PASS {R4(W, AF, 'pass_per_24h')}（{halves(W, AF, 'pass_per_24h')}），WvNG 在线命中 {R4(W, AF, 'online_hits_per_24h')}、唯一拦截 {R4(W, AF, 'unique_reject_per_24h')}；"
        f"其中 WvNG 上线到 bYXa 上线（{HR(Y, WB)} 小时）PASS {R4(Y, WB, 'pass_per_24h')}（{halves(Y, WB, 'pass_per_24h')}）；bYXa 上线后（{HR(Y, AF)} 小时）请求 {R4(Y, AF, 'requests_per_24h')}、PASS {R4(Y, AF, 'pass_per_24h')}（{halves(Y, AF, 'pass_per_24h')}），bYXa 在线命中 {R4(Y, AF, 'online_hits_per_24h')}、唯一拦截 {R4(Y, AF, 'unique_reject_per_24h')}。"
        f"**基线敏感性**（`results/dr034_baseline_sensitivity.csv`）：WvNG 上线后的 PASS 速率是 10-02 起基线（整段 / 前半 / 后半）的 {ratios(W, 'before: NY 10-02')}；bYXa 上线后是同一组基线的 {ratios(Y, 'before: NY 10-02')}，是 WvNG 单独在线那段（整段 / 前半 / 后半）的 {ratios(Y, 'before: WvNG online')}。"
        "**逐条**（共 " + str(len(s4)) + " 条，`results/dr034_strategies.csv` 含完整表达式与改动原因；逐日命中 `results/dr034_daily_hits.csv`，去重手机号按天给、不跨天相加）：" + "；".join(desc) + "。",
        "核实了群里的几件事：WvNG 2026-10-08 07:54:28 UTC 转上线（纽约 03:54，与「约 04:00」相符），之前 07:52:56 把区号规则从 35 个区号的旧规则换成 15 个区号的新规则；MZQk 10-08 08:07:49 UTC 转预上线，至今仍是预上线，且带 UTC 02:00–09:00 时间窗（DR-018）；bYXa 10-09 01:44:35 UTC 转上线。"
        "「补进去了」= 2026-10-09 01:55:30 UTC 改了**共用的**区号规则 `rule_CrVrUuDk1hHJ`（15 → 21 个区号）：这一改同时扩大了在线的 WvNG、bYXa 与预上线的 MZQk，但这三条的策略名仍写 15 个，且**改规则没有把在线策略打回预上线**（与「改策略会退回预上线」不同）。"
        "10-10 UTC 又新建了两条预上线策略 eoHQ（01:26）与 E1HJ（02:36），建的时候规则已是 21 个区号；eoHQ 的规则 `rule_sih7inbv75df` 名称写「同手机号近1小时的访问次数 大于 2」，条件却在 01:17 改成了 `< 2`（见 `05_开放探索_20261009.md`）。"
        "速率：WvNG 上线后目标区号的 PASS 降到之前的约四分之一，bYXa 上线后再降到 WvNG 单独在线时的约六成。**计数分解，非因果**：两段都短（44 / 26 小时），bYXa 上线后的后半 PASS 反而高于前半，10-09 01:55 的区号扩容与攻击方自己的节奏都落在同一时段，计数分不开各自的作用。",
        "高（配置与日志直接对应）；速率比较为中（时段短）", "—（数据）；结论给段枝宏", "已答复")

# ---------------- DR-035 ----------------
if ex("dr035_fit_candidates.csv"):
    f = rd("dr035_fit_candidates.csv"); b = f.iloc[0]; fr = rd("dr035_fill_rate_periods.csv"); cm = rd("dr035_completeness.csv")
    get = lambda p_, s_: fr[(fr.period == p_) & (fr.code_set == s_)]
    fr15 = lambda p_: (lambda x: f"{pc(x.fill_rate.iloc[0])}（{fi(x.filled.iloc[0])}/{fi(x.sent.iloc[0])}）" if len(x) and x.sent.iloc[0] else "无发送")(get(p_, "15 original"))
    fr1 = lambda p_: (lambda x: f"{pc(x.fill_rate.iloc[0])}" if len(x) and x.sent.iloc[0] else "—")(get(p_, "+1"))
    c1 = cm[(cm.g == "+1") & (cm.basis == "stats date = UTC day")].set_index("d").ratio_stats_sent_to_risk_pass
    gap = c1[(c1.index >= "2026-09-15")]
    sec("DR-035", "upush 回填统计表按区号的回填率",
        "`t_verifycode_filled_statistics` 按日 × 区号 × 项目的发送、回填与回填率（08-01 起）：09-21 起的缺口补上没有；15 个区号攻击前 / 攻击期的回填率；新策略预上线窗口里的回填。",
        "`sql/dr035_upush_daily.sql`（只 `SUM` 分组）；个人信息检查 `sql/dr035_upush_pii_check.sql`；`sql/local/dr035_local.py`",
        f"桌面「其他地区」表的复现（`results/dr035_fit_candidates.csv`）：最佳组合 = 租户 {b.tenant}、项目 {b.project}、提供商 {b.provider}、区号口径「{b.code_set}」、日期偏移 {int(b.date_shift_days)} 天，{int(b.days)} 天中 {int(b.days_exact)} 天发送与回填都完全一致、{int(b.days_sent_exact)} 天发送一致，发送差的绝对值合计 {fi(b.abs_diff_sent)}、回填 {fi(b.abs_diff_filled)}。"
        f"用这个口径，15 个区号的回填率（回填和 / 发送和，`results/dr035_fill_rate_periods.csv`）：攻击前 06-01…09-02 {fr15('pre-attack 06-01..09-02')}；攻击期 09-03…09-20 {fr15('attack 09-03..09-20 (before the stats gap)')}；09-21…09-28 {fr15('09-21..09-28 (receipt gap)')}；09-29 至最后一天 {fr15('09-29..last day')}；"
        f"+1 同期 {fr1('pre-attack 06-01..09-02')} / {fr1('attack 09-03..09-20 (before the stats gap)')} / {fr1('09-21..09-28 (receipt gap)')} / {fr1('09-29..last day')}。"
        f"完整度（统计表发送数 / 风控短信 PASS，+1，统计日期按 UTC 日，`results/dr035_completeness.csv`）：" + "、".join(f"{d[5:]} {v}" for d, v in gap.items()) + "。逐日 × 区号：`results/dr035_daily_by_cc.csv`。",
        "统计表在 09-21…09-28 漏记了大部分 +1 发送，09-29 起完整度回到原来的水平，但**缺口期没有补回**；所以缺口期（含 43Na 的预上线窗口）的回填率不能用。15 个区号在攻击前的回填率本来就很低、攻击期接近 0；10-08 新策略的预上线窗口只有 10-08 一天的统计（10-09 的统计要 10-10 05:30 UTC 以后才写入，本次取数早于此）。"
        "每个区号的回填率只能当作折算参考，不能直接换算成某条策略的误伤数。",
        "中（复现程度见「结果」）；" + T["upush_date"], "陈晨昕（日期口径、缺口原因）", "待确认（问人：陈晨昕）")

# ---------------- DR-036 ----------------
if ex("dr036a_utc_daily_vs_doris.csv"):
    j = rd("dr036a_utc_daily_vs_doris.csv"); bc = rd("dr036bcd.csv"); e = rd("dr036e_nynj_share.csv")
    ndays = len(j); same_p = int((j.diff_pass == 0).sum()); same_t = int((j.diff_total == 0).sum())
    v = lambda c, w, m: bc[(bc.claim == c) & (bc.window == w) & (bc.metric == m)].value.iloc[0]
    e15 = e[(e.basis == "all results") & (e.code_set == "15 original")].iloc[0]; e15p = e[(e.basis == "PASS") & (e.code_set == "15 original")].iloc[0]
    sec("DR-036", "10-08 群里几个数的复核（MySQL 源库）",
        "(a) 按 UTC 日的短信总量与 PASS 和 Doris 逐日对比；(b) 日均非 +1 通过约 800、集中在五个区号、分数 0.8；(c) 10-08 非 +1 PASS 60% 非美国 IP，加「IP 国家 ≠ 号码国家」后 40%；(d) 10-08 04:00 后 PASS 80% 是 +1；(e) 20 天里 15 个区号来自 NY/NJ 的不到 1%。",
        "(a)(e) L1 → `sql/local/l1_drs.py`；(b)(c)(d) E1 → `sql/local/e1_std.py`",
        f"(a) `results/dr036a_utc_daily_vs_doris.csv`：UTC 日 09-13…10-08 共 {ndays} 天，短信口径 PASS {same_p}/{ndays} 天与 Doris 完全相同，总量 {same_t}/{ndays} 天相同，其余天差 ±1（差的绝对值合计 {fi(j.diff_total.abs().sum())}）；全部行口径每天多出几次（带 email 的请求）。"
        f"(b) 纽约日 10-01…10-07 非 +1 短信 PASS 日均 {v('b', 'NY 10-01..10-07', 'non-+1 SMS PASS per day')}，前五个区号依次是 +92、+265、+856、+375、+386（`results/dr036bcd.csv`），V3 分数 ≥0.8 的占 {pc(v('b', 'NY 10-01..10-07', 'V3 score >= 0.8 share of non-+1 PASS'))}；"
        f"(c) 纽约日 10-08 非 +1 PASS {fi(v('c', 'NY 10-08', 'non-+1 SMS PASS'))} 次，非美国 IP {pc(v('c', 'NY 10-08', 'share with non-US IP (IP country known and not US)'))}，再加「IP 国家 ≠ 号码国家」为 {pc(v('c', 'NY 10-08', 'share with non-US IP and IP country != phone country'))}；"
        f"(d) 纽约日 10-08 04:00…24:00 PASS 中 +1 占 {pc(v('d', 'NY 10-08 04:00..24:00', 'share of SMS PASS with +1'))}（00:00…04:00 只有 {pc(v('d', 'NY 10-08 00:00..04:00', 'share of SMS PASS with +1'))}）；"
        f"(e) 纽约日 09-19…10-08 共 20 天，15 个区号短信请求中 IP 省份为 New York / New Jersey 的 {fi(e15.nynj)}/{fi(e15.requests)} = {pc(e15.nynj_share)}，PASS 中 {pc(e15p.nynj_share)}（`results/dr036e_nynj_share.csv`）。",
        f"(a) MySQL 源库按「`email` 为空 = 短信」与 Doris `l2_scene='1001'` 在这 {ndays} 个 UTC 日上按日汇总一致——两边可以直接对数（也加强了 DR-002 的结论）。(b)(d) 与群里说法一致；(c) 实测比群里的 60% / 40% 高 7–9 个百分点（{pc(v('c', 'NY 10-08', 'share with non-US IP (IP country known and not US)'))} / {pc(v('c', 'NY 10-08', 'share with non-US IP and IP country != phone country'))}）；(e) 实测约 {pc(e15.nynj_share)}，**不是「不到 1%」**，量级仍很小。这是内部复核，不是为了在群里反驳。",
        "高", "—（数据）", "已答复")

# ---------------- DR-037 ----------------
if ex("dr037_members_by_cc.csv"):
    m = rd("dr037_members_by_cc.csv", dtype=str); tot = rd("dr037_members_total.csv").iloc[0]; ck = rd("dr037_crm_check.csv").iloc[0]
    m15 = m[m.code_set == "15 original"]; m6 = m[m.code_set == "6 added"]; m1 = m[m.code_set == "+1"]
    fm = lambda x: fi(x) if str(x).isdigit() else x
    show = lambda g: "、".join(f"+{r.cc} {fm(r.members)}" for r in g.itertuples())
    pay = rd("dr037_paying_by_phone_code.csv", dtype=str) if ex("dr037_paying_by_phone_code.csv") else None
    C15_ = rd("dr031_code_versions.csv", dtype=str).codes.iloc[0].split()
    _p = [x for x in m15.with_first_pay.astype(str)]
    _lo = sum(int(x) for x in _p if x.isdigit()) + sum(1 for x in _p if x == "<5"); _hi = sum(int(x) for x in _p if x.isdigit()) + 4 * sum(1 for x in _p if x == "<5")
    pay_range = f"{_lo}–{_hi} 人" if _hi > _lo else f"{_lo} 人"
    tot_empty = int(rd("dr037_members_by_cc.csv", dtype=str, keep_default_na=False).query("cc == ''").members.iloc[0]) if (rd("dr037_members_by_cc.csv", dtype=str, keep_default_na=False).cc == "").any() else 0
    _l1 = rd("l1_long.csv", dtype={"cc": str}); _l1 = _l1[(_l1.lvl == "h") & (_l1.sms == 1) & (_l1.tenant_lkus == 1) & (_l1.ny_date >= "2026-10-03") & (_l1.ny_date <= "2026-10-09") & (_l1.final_result == "PASS")]
    _w = _l1[_l1.cc.isin(C15_)].groupby("cc").n.sum().reindex(C15_).fillna(0)
    pass7_15, wk_max = int(_w.sum()), int(_w.max())
    sec("DR-037", "会员和订单按区号的汇总（只计数）",
        "按手机号区号：注册会员（存量、近 30 天新增）、有过订单的会员（近 90 天、全部）；与同区号的短信 PASS 对照，重点是 15 个区号和 +1。",
        "salescrm：`sql/dr037_crm_check.sql`、`sql/dr037_explain_crm.sql`（EXPLAIN）、`sql/dr037_crm_members.sql`（按注册月拆分，`t_user` 与同库 `t_user_profile` 在同一条语句里关联）；salesorder：`sql/dr037_order_check.sql`、`sql/dr037_explain_order.sql`、`sql/dr037_order_paying.sql`；汇总 `sql/local/dr037_038_local.py`",
        f"区号字段检查（`results/dr037_crm_check.csv`）：`t_user` {fi(ck.n_rows)} 行，`area_code` 最长 {int(ck.max_len_area_code)} 位、5 位以上数字 {int(ck.n_area_code_5plus_digits)} 个——是区号不是号码。LKUS 有效会员（status=1）合计 {fi(tot.members)}，其中有首次消费 {fi(tot.with_first_pay)}、近 90 天下过单 {fi(tot.last_order_in_90d)}、近 30 天新注册 {fi(tot.new_30d)}（`results/dr037_members_total.csv`）。"
        f"按区号（`results/dr037_members_by_cc.csv`；<5 的格子写成 `<5`，09-01 前 / 后注册的两列互补，一格 <5 时另一格写成 `>=5`；按注册月的逐月查询结果有很多小格子，只留在本机、不进包）：+1 有效会员 {fm(m1.members.iloc[0]) if len(m1) else '—'}；15 个区号：{show(m15) or '全部为 0'}；新增 6 个区号：{show(m6) or '全部为 0'}。"
        + (f"订单侧（salesorder）：已支付订单（status 20/90）的收货人区号 `take_hum_phone_code` **全部为空**（`results/dr037_order_check.csv`：近 30 天 {fi(rd('dr037_order_check.csv').n_orders.iloc[0])} 单、非空区号 0 种），所以订单不能按区号拆；只给每 30 天的付费会员总数作对照（`results/dr037_paying_by_phone_code.csv`，三个 30 天窗口去重会员不能相加）。" if ex("dr037_order_check.csv") else ""),
        (lambda pay15, pass7, wk: f"按「有过消费」（`first_pay_time` 不为空）算，15 个区号**已知区号的有消费会员共 {pay15}**（+7 {m15.set_index('cc').with_first_pay.get('7', '0')}、+60 {m15.set_index('cc').with_first_pay.get('60', '0')}、+386 {m15.set_index('cc').with_first_pay.get('386', '0')}，其余每个区号 <5 或 0；"
            f"{'、'.join('+' + c for c in sorted(set(C15_) - set(m15.cc), key=int))} 没有会员）。这**不是上限**：另有 {fi(tot_empty)} 个有效会员 `area_code` 为空（表里 `cc` 为空的一行），无法归区号。"
            f"注册时间（`members_registered_before_0901` / `_since_0901`）：+60 的 {fm(m15.set_index('cc').members.get('60'))} 个会员里 {fm(m15.set_index('cc').members_registered_before_0901.get('60'))} 个是 09-01 之前注册的，不是攻击期账号；+92 的 {m15.set_index('cc').members.get('92')} 个里 {m15.set_index('cc').members_registered_since_0901.get('92')} 个是 09-01 之后注册、都没有消费（推断：像攻击期间注册的账号，未核实）。"
            f"对照：这 15 个区号近 7 日（纽约日 10-03…10-09）每个区号的短信 PASS 在 0–{wk} 次之间、合计 {pass7} 次（L1）。所以拦掉它们的短信，可能误伤的已知有消费会员是几十人量级。注意单位不同：会员是人，PASS 是请求，不能相除当「转化率」。")(
            pay_range, fi(pass7_15), fi(wk_max)),
        "高（只计数；区号来自会员主表）", "—（数据）；结论给段枝宏", "已答复")

# ---------------- DR-038 ----------------
if ex("dr038_sw3j_20260921_v2_summary.csv"):
    s8 = rd("dr038_sw3j_20260921_v2_summary.csv"); s1 = rd("dr038_sw3j_20260921_summary.csv"); lf = rd("dr038_list_formats.csv")
    on = s8[s8.hit_list == "online"]
    s7 = rd("dr038_sw3j_7d_summary.csv") if ex("dr038_sw3j_7d_summary.csv") else pd.DataFrame()
    wl = lf[(lf.tenant == "LKUS")]
    sec("DR-038", "sw3j 2026-09-21 那 50 次命中是不是来自白名单 IP C 段",
        "`strategy_sw3jC7bvFYEX` 在纽约日 09-21 的在线命中，C 段有多少落在 LKUS 白名单 IP C 段里；号码是否在手机号白名单里（只出是 / 否计数）。",
        "`sql/dr038_list_formats.sql`、`sql/dr038_sw3j_20260921.sql`（按 `$.para.realIpc`）、`sql/dr038_sw3j_20260921_v2.sql`（按 `realIp` 前三段）、`sql/dr038_sw3j_7d.sql`；名单匹配都在同一条 SQL 里完成，只输出计数；汇总 `sql/local/dr037_038_local.py`",
        f"第一次按 `$.para.realIpc` 匹配：这 {fi(s1.hits.sum())} 次的 `realIpc` 全为空——`realIpc` 不是推送场景的请求参数（`results/p1_json_keys_summary.csv` 里 LKUS_push 只有 `realIp`），所以改用 `realIp` 的前三段重跑（v2）。"
        f"v2：纽约日 09-21 在线命中 {fi(on.hits.sum())} 次（全部 LKUS_push 行；短信 {fi(on[on.sms == 1].hits.sum())} 次），手机号 {fi(on.distinct_phones.sum())} 个，都有正常的 IPv4 C 段；C 段在当前白名单里的 {fi(on[on.ipc_in_whitelist_now == 1].hits.sum())} 次（只算 09-21 当时已存在的条目也是 {fi(on[on.ipc_in_whitelist_asof == 1].hits.sum())} 次），号码在手机号白名单里的 {fi(on[on.phone_in_whitelist_now == 1].hits.sum())} 次（`results/dr038_sw3j_20260921_v2_summary.csv`）。"
        f"LKUS 白名单条目（只计数，`results/dr038_list_formats.csv`）：" + "；".join(f"type {r.list_type} 格式 {r.content_format} {fi(r.n_entries)} 条（创建于 {str(r.first_created)[:10]}）" for r in wl.itertuples()) + "；LKUS 没有手机号白名单条目（`results/p2_list_counts.csv`）。"
        + (f"7 日（纽约日 10-03…10-09）sw3j 命中 {fi(s7.hits.sum())} 次。" if len(s7) and s7.hits.sum() else "7 日（纽约日 10-03…10-09）sw3j 没有命中（`results/dr038_sw3j_7d.csv` 为空）。"),
        "**不是**白名单 IP 段来的：09-21 的 50 次来自 1 个号码，它的 IP C 段不在白名单里，号码也不在手机号白名单里——被 sw3j 的「手机号近 1 天访问次数 ≥100」拦下。推断：它是一个一天内请求过多的号码，不是 sw3j 想防的「已加白号码被利用」的实例；在本次查的两个窗口（纽约日 09-21、10-03…10-09）里没有看到那种实例，其它日子没有查。",
        "高（白名单只有 82 条 C 段，匹配在库内完成）", "—（数据）；结论给段枝宏", "已答复")

# ---------------- standing ----------------
if ex("dr003_counter_codes_7d.csv"):
    c7 = rd("dr003_counter_codes_7d.csv"); cb = c7[c7.combo_dimension == 1]
    rc = rd("p8_counter_recheck_summary.csv") if ex("p8_counter_recheck_summary.csv") else None
    def rr(fid, var):
        x = rc[(rc.feature_id == fid) & (rc.variant.str.startswith(var))]
        return pc(x.share_eq.iloc[0]) if len(x) else "—"
    sec("DR-003", "带过滤条件 / 组合维度的累计特征（常设）",
        "带条件或组合维度的累计特征，7 日的返回码；组合维度特征是否恢复 SUCCESS；过滤条件是否生效（Part 1 第 8 点）。",
        "E1 → `sql/local/e1_std.py`、`sql/local/counter_recheck_e1.py`",
        f"组合维度（`realIp|phoneNo`）两个特征 7 日（纽约日 10-03…10-09，短信）：" + "；".join(f"`{r.feature_id}` {r.code} {fi(r.rows)} 次（{pc(r.share)}）" for r in cb.itertuples()) + "（`results/dr003_counter_codes_7d.csv`，逐日 `results/dr003_counter_codes_daily.csv`）。"
        + (f"过滤条件重算（纽约日 10-02…10-09，`results/p8_counter_recheck_summary.csv`）：`feature_e1Kmz7JqzsWc` 按条件过滤后与引擎值一致 {rr('feature_e1Kmz7JqzsWc', 'after')}、不过滤 {rr('feature_e1Kmz7JqzsWc', 'before')}；`feature_n91JeGM6gD6i` 分别 {rr('feature_n91JeGM6gD6i', 'after')} / {rr('feature_n91JeGM6gD6i', 'before')}；同维度同窗口的无条件特征作校准，一致 {rr('feature_dtoJoDcUgCcr', 'calib')} 与 {rr('feature_UOJYBEifd5Jn', 'calib')}。" if rc is not None else ""),
        "组合维度特征仍然 100% 返回 `DIMENSION_EMPTY`，用它们的策略仍不会命中——没有恢复，不需要重估 tO7D。过滤条件在日志里是生效的：按条件重算几乎完全等于引擎值，不按条件则大多不等；与 2026-09-25 包的结论一致，09-24 通告的「过滤条件不生效」在 10-02 以后的日志里看不到。",
        "高（校准特征一致率 >93%）", "贡锁泉（组合维度写法；通告所指的具体现象）", "已答复")
if ex("dr010_attack_rule.csv"):
    ar = rd("dr010_attack_rule.csv").set_index("k"); ps_ = rd("dr010_period_summary.csv"); k5 = ar.loc[5.0]; k3 = ar.loc[3.0]
    oct_ = ps_[ps_.month == "2026-10"]
    sec("DR-010", "美国号码的日常短信基线（常设）",
        "+1 号码每天、每周正常的短信 PASS 量；攻击日标记。",
        "L1 → `sql/local/l1_drs.py`",
        f"规则（`results/dr010_attack_rule.csv`）：基线 = 序列前 28 天（纽约日 06-01…06-28），中位数 {k5.baseline_median}、MAD×1.4826 = {k5.baseline_mad_scaled}；k=5 阈值 {k5.threshold} 次/天的非 +1/+86 短信请求，09-03 起 {int(k5.days_since_09_03)} 天里 {int(k5.flagged_days_since_09_03)} 天是攻击日，最后一天 {k5.last_flagged_day} 仍是；k=3 阈值 {k3.threshold}，首个标记日 {k3.first_flagged_day}。"
        f"+1 短信 PASS 日均按月 × 是否攻击日：`results/dr010_period_summary.csv`（10 月：" + "；".join(f"{r.period} {int(r.days)} 天、日均 {r.plus1_pass_mean}" for r in oct_.itertuples()) + "）；按纽约周：`results/dr010_plus1_pass_weekly.csv`；逐日序列：`results/dr010_daily_series.csv`。",
        "攻击从 09-03 起每天都在（k=5），到 10-09 仍未结束；基线参数与 09-27 包完全相同（同一组 28 天）。",
        "高", "Huanxian Zhou（基线口径是否采用）", "已答复")
if ex("dr012_summary.csv"):
    s12 = rd("dr012_summary.csv", dtype={"cid": str}).set_index(["cid", "group"]); v12 = rd("dr012_versions.csv", dtype={"cid": str})
    sh12 = rd("dr012_strategies_hit.csv", dtype={"cid": str}); cg12 = rd("dr012_ccgroup.csv", dtype={"cid": str})
    G_NA, G_OLD = "no app field", "app present, version < 1.4.30"
    row = lambda c, g: s12.loc[(c, g)]
    p1 = lambda c, g: int(cg12[(cg12.cid == c) & (cg12.group == g) & (cg12.cc_group == "+1")].rows.sum())
    vers = lambda c, g: v12[(v12.cid == c) & (v12.group == g)]
    vr = lambda c, g: (lambda x: f"{x.version.iloc[0]} 占 {fi(x.rows.iloc[0])} 次" if len(x) else "—")(vers(c, g))
    vspan = lambda c, g: (lambda x: f"{len(x)} 个版本（{min(x.version, key=lambda z: tuple(int(i) for i in z.split('.')))}…{max(x.version, key=lambda z: tuple(int(i) for i in z.split('.')))}）" if len(x) else "—")(vers(c, g))
    top_on = lambda c, g, n=3: "、".join(f"`{r.strategy_id}` {fi(r.hits)}" for r in sh12[(sh12.cid == c) & (sh12.group == g) & (sh12.list == "online")].sort_values("hits", ascending=False).head(n).itertuples()) or "无"
    line = lambda c, g, lab: f"{c} {lab} {fi(row(c, g).requests)} 次（+1 {fi(p1(c, g))}，PASS {fi(row(c, g)['pass'])}）"
    sec("DR-012", "cid 105/106 无 app 字段与 1.4.30 以下旧版 App（复测）",
        "无 `app` 字段的 105/106 请求与 1.4.30 以下的 App 版本：量、版本、区号组、最终结果、被哪些策略命中——看旧版 App（没有 reCAPTCHA，09-02 起也没了极验）要不要单独的规则。",
        "E1 → `sql/local/e1_std.py`",
        "7 日（纽约日 10-03…10-09，短信，`results/dr012_summary.csv`）四组："
        + "；".join([line("105", G_NA, "无 app"), line("105", G_OLD, "版本 <1.4.30"), line("106", G_NA, "无 app"), line("106", G_OLD, "版本 <1.4.30")]) + "。"
        f"版本（`results/dr012_versions.csv`）：105 无 app {vr('105', G_NA)}；105 旧版本 {vspan('105', G_OLD)}；106 无 app {vspan('106', G_NA)}；106 旧版本 {vspan('106', G_OLD)}。"
        f"在线策略命中最多的（`results/dr012_strategies_hit.csv`，同一请求可被多条命中）：105 无 app {top_on('105', G_NA)}；105 旧版本 {top_on('105', G_OLD)}；106 两组：{(lambda a, b: '都没有在线命中' if a == b == '无' else a + ' / ' + b)(top_on('106', G_NA), top_on('106', G_OLD))}。区号组 / token：`results/dr012_ccgroup.csv`、`results/dr012_token.csv`。",
        f"105 无 app 的流量几乎全是非 +1 区号、版本几乎都是 1.3.50，约一半放行，在线拦截主要靠 6umG、3JjE、43Na（推断：像伪造的 cid，不像真实旧版 App）。"
        f"106 的两组（无 app、旧版本）几乎全是 +1、全部放行，版本分散（推断：像真实的老 iOS 用户）。105 旧版本 {fi(row('105', G_OLD).requests)} 次里 +1 {fi(p1('105', G_OLD))} 次，量很小。"
        "是否给旧版本单独规则，要林宏鹏先说明 1.3.50 是否发布过、无 app 的 105 从哪来。",
        "中（计数可靠；「伪造 / 真实」是推断）", "林宏鹏", "待确认（问人：林宏鹏）")
sec("DR-013", "MCP 能连到哪些库，Doris 可不可达（常设）", "本轮可达的数据源与 Doris。", "`results/p0_mcp_inventory.csv`",
    "mcp-db-gateway：64 个 MySQL、1 个 PG、79 个 Redis 服务器；Grafana 有 `Doris-iriskcontrol` 数据源但 MCP 不能执行 SQL；Redshift `list_clusters` 报错（`00_环境清单.md` §2）。",
    "Doris 仍不可达，DR-002、DR-022 仍是短节。", "高", "—", "已答复")
if ex("dr014_best_candidate.csv"):
    b14 = rd("dr014_best_candidate.csv")
    sec("DR-014", "分片键抽查（常设）", "纽约日 2026-10-09 每个场景的分片键是否仍按场景组成立。", "`sql/dr014_sharding_key_by_scene_20261009.sql` → `sql/local/dr014_local.py`",
        "；".join(f"{r.scene_id} {fi(r.rows)} 行，分片键 = {r.best_candidates}（{pc(r.best_share, 0)}）" for r in b14.itertuples()) + "（`results/dr014_best_candidate.csv`、`results/dr014_summary.csv`）。"
        + " 7 日（纽约日 10-03…10-09）推送场景各分片去重手机号之和等于窗口去重数（`results/p3_distinct_users.csv`）；uid 跨分片（`results/p3_dr014_shard_spread.csv`）。",
        "推送 / 注册 / captcha 仍是完整手机号，登录 / 支付 / 下单 / 取消 / 新人券仍是 `userNo`（各 100%）；推送场景按分片相加去重手机号仍然有效，uid 不行。", "高", "—", "已答复")
if ex("p2_oplog_counts.csv"):
    op = rd("p2_oplog_counts.csv")
    sec("DR-015", "配置与名单导出（常设）", "整表导出定义表与操作日志；名单按类型 × 场景 × 来源计数。", "`sql/config_*.sql`、`sql/p2_*.sql`",
        f"17 张定义表（16 张 `t_rms_engine_*` + `t_scene`）整表导出，`02_线上配置导出.md` §1；操作日志 {fi(op.n.sum())} 次操作，{op.first_op_utc.min()} … {op.last_op_utc.max()} UTC（`results/p2_oplog_counts.csv`），09-27 之后的变化见 `02` §8 与 DR-034；名单按场景 `results/p2_list_counts_by_scene.csv`；09-27 之后的名单变化 `results/p2_list_changes.csv`。"
        + (" 运行结束时复导出（快照 #2）：`results/s2_config_strategy.csv` 等；与快照 #1 的差异见 `results/p2_snapshot_diff.csv`。" if ex("p2_snapshot_diff.csv") else ""),
        "导出成功；与 09-24 快照的对比由桌面 D1 做。", "高", "林宏鹏", "已答复")
if ex("dr016_summary_7d.csv"):
    d16 = rd("dr016_summary_7d.csv").iloc[0]
    sec("DR-016", "引擎 REVIEW 被改写为最终 PASS（常设）", "引擎 REVIEW 类结果有多少返回 PASS；引擎无结果时返回什么。", "E1 → `sql/local/e1_std.py`",
        f"7 日（纽约日 10-03…10-09，短信，`results/dr016_summary_7d.csv`）：引擎 REVIEW 类 {fi(d16.engine_review_class)} 次，返回 PASS {fi(d16.engine_review_final_pass)}（其中 reviewRepeat=true {fi(d16.engine_review_final_pass_review_repeat_true)}）、返回 REVIEW {fi(d16.engine_review_final_review)}，全部 cid {d16.engine_review_cids}；引擎无结果 {fi(d16.engine_no_result)} 次。明细 `results/dr016_engine_vs_final_7d.csv`、H5 A2 链 `results/p3_h5_a2_chain.csv`。",
        "约三分之二的引擎 REVIEW 被改写为 PASS，全部来自 H5；改写规则要应用侧说明。", "高", "林宏鹏", "待确认（问人：林宏鹏）")
if ex("dr017_above_whitelist.csv"):
    d17 = rd("dr017_above_whitelist.csv")
    sec("DR-017", "优先级高于白名单的策略（常设）", "优先级高于白名单 PASS（100000）的策略的现状与 7 日命中。", "配置 + `results/p2_hits_7d.csv` → `sql/local/e1_std.py`",
        "；".join(f"`{r.strategy_id}` 状态 {r.status}、{r.result_code}、优先级 {r.exec_priority}、7 日在线命中 {fi(r.online)}" for r in d17.itertuples()) + "（`results/dr017_above_whitelist.csv`，全部 LKUS_push 行）。",
        "与群里答复一致（sw3j 是有意的兜底；其余是已下线的极验测试策略）；7 日内 sw3j 没有命中。09-21 那批命中的来源见 DR-038。", "高", "段枝宏、田志鲔（已在群里答复）", "已答复")
if ex("dr018_time_rule_strategies.csv"):
    d18 = rd("dr018_time_rule_strategies.csv")
    act = d18[d18.status.isin([1, 2])]
    sec("DR-018", "时刻类规则按 UTC 写死，夏令时结束后偏 1 小时（常设）", "用 UTC 时刻规则的在线 / 预上线策略及命中。", "配置 + `results/p2_hits_7d.csv` → `sql/local/e1_std.py`",
        "；".join(f"`{r.strategy_id}`（状态 {r.status}，{r.conditions} UTC）7 日在线 {fi(r.online)}、预上线 {fi(r.preonline)}" for r in act.itertuples()) + "（`results/dr018_time_rule_strategies.csv`，全部 LKUS_push 行）。",
        "UTC 02:00–09:00 现在对应纽约 22:00–05:00，2026-11-01 起对应 21:00–04:00。**新增的 MZQk（预上线）也用这个窗口**（配置核实，不再是推断）；需要在 11-01 前决定是否调整。", "高", "田志鲔", "待确认（问人：田志鲔）")
# ---------------- short / skip ----------------
sec("DR-002", "推送场景里怎么区分短信和邮件（短节）", "Doris `l2_scene='1002'` 是否就是邮件。", "—",
    "本轮无新查询；Doris 不可达。旁证：DR-036(a) 显示 MySQL「`email` 为空 = 短信」与 Doris `l2_scene='1001'` 按 UTC 日汇总一致。", "等 DR-020 的 Doris 只读账号（依赖，不是临时受阻）；状态不变。", "—", "林宏鹏（`l2_scene` 的生成规则）", "部分答复（状态不变）")
sec("DR-022", "巡检大盘与源库的午夜归日差异（短节）", "Doris `access_time` 一侧的午夜归日。", "—",
    "本轮无新查询；Doris 不可达。", "等 DR-020 的 Doris 只读账号（依赖，不是临时受阻）；状态不变。", "—", "—", "部分答复（状态不变）")
sec("DR-028", "预上线策略命中的逐请求验证码回填标签（跳过）", "逐请求的回填标签。", "—", "本次跳过：前提未满足（陈晨昕的口径确认）。没有任何查询触及 upush 的行级表。",
    "前提满足前继续跳过。", "—", "陈晨昕（`mobile` 存储与回填时点）；范围批准：曾翔宇", "待取数")
sec("DR-029", "LKUS 白名单 `temp=1` 的含义（跳过）", "`temp=1` 是临时还是永久。", "—",
    "本次跳过（数据已做完，含义待林宏鹏）。本轮名单计数仍导出：LKUS 白名单 type 10006（IP C 段）" + (lambda w: f"{fi(w.n_entries.sum())} 条，`temp` 全部为 {int(w.temp.iloc[0])}" if len(w) else "—")(rd("p2_list_counts.csv").query("list_table == 't_whitelist' and tenant == 'LKUS'")) + "；`t_whitelist.temp` 的字段注释是「" + rd("p1_columns.csv", dtype=str).query("TABLE_NAME == 't_whitelist' and COLUMN_NAME == 'temp'").COLUMN_COMMENT.iloc[0] + "」（`results/p2_list_counts.csv`、`results/p1_columns.csv`）。", "按字段注释，这些 C 段都是「临时」保存；临时是否意味着会过期、何时过期，要平台说明。", "—", "林宏鹏", "待确认（问人：林宏鹏）")
open(os.path.join(PKG, "04_数据问题结论.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
pd.DataFrame(ST).to_csv(os.path.join(R, "p4_dr_status.csv"), index=False)
print("04 written:", len(ST), "sections")
