#!/usr/bin/env python3
"""P3: write 03_近7日数据画像_<end>.md. Every number is read from results/ (p3_* from sql/local/p3_profile.py on the E1
extract, dr016/017/018 from sql/local/p4_new_drs.py, pure-SQL results from the runner); commentary is generated from
those numbers. Each table states its basis (SMS rule vs all LKUS_push rows) and window."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
pct = lambda x: f"{100 * x:.1f}%"
esc = lambda v: "" if pd.isna(v) else str(v).replace("|", "\\|")
fi = lambda v: f"{int(v):,}"

dr, pc, du, sp = rd("p3_daily_result.csv"), rd("p3_pass_by_ccgroup.csv"), rd("p3_distinct_users.csv"), rd("p3_dr014_shard_spread.csv")
ca, st, lk, cx = rd("p3_cid_app_profile.csv"), rd("p3_strategies.csv"), rd("p3_pass_leakage.csv"), rd("p3_crosscheck.csv")
c7, cd, h5, rm = rd("p3_counter_codes_7d.csv"), rd("p3_counter_codes_daily.csv"), rd("p3_h5_a2_chain.csv").iloc[0], rd("p3_review_matrix.csv")
v3c, v3f, ccs, dgr = rd("p3_v3_codes.csv"), rd("p3_v3_fid_daily.csv"), rd("p3_cc_spelling.csv"), rd("p3_daily_ccgroup_result.csv")
ep, ev = rd("p3_empty_app_profile.csv"), rd("p3_empty_app_versions.csv")
d16, d17, d18 = rd("dr016_summary_7d.csv").iloc[0], rd("dr017_reject_above_whitelist.csv"), rd("dr018_time_rule_strategies.csv")
tl, h7 = rd("p2_oplog_timeline.csv"), rd("p2_hits_7d.csv")
ca.columns = ["v3_lo" if c.startswith("v3_<") else "v3_mid" if (c.startswith("v3_") and "-" in c) else "v3_hi" if c.startswith("v3_>=") else
              "n_pass" if c == "pass" else c for c in ca.columns]
start, end = dr.ny_date.min(), dr.ny_date.max()
utc0 = f"{start} 04:00"
sw = tl[(tl.object_id == "strategy_43NaEzJmiQFk") & (tl.field == "status") & (tl.after.astype(str) == "1")].operation_time_utc.iloc[-1]
sw_day = (pd.Timestamp(sw) - pd.Timedelta(hours=4)).strftime("%Y-%m-%d")
utc1 = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d") + " 04:00"
tot = dr[["sms_PASS", "sms_REJECT", "sms_REVIEW"]].sum(); N = int(tot.sum())
allrows = int(dr.total.sum()); email = allrows - N
W7 = f"纽约日 {start}…{end}（7 日）"
SMS = f"短信口径（`$.para.email` 为空或不存在），{W7}"
ALL = f"全部 LKUS_push 行，{W7}"
L = [f"# 03 近 7 日数据画像（LKUS_push 短信，{start} … {end} 纽约日）", "",
     f"> 数据：`aws-luckyus-iriskcontrolservice-rw` 64 个日志分片；窗口按 America/New_York 自然日，UTC 界限 `[{utc0}, {utc1})`（EDT，UTC−4，窗口内无夏令时切换）。",
     "> 取数：E1 行级抽取（每条语句 ≤1 小时 × 16 分片，只含标量与加盐哈希，只存本机 `_local_only/`，不进包）→ 本地汇总（`sql/local/p3_profile.py`）。"
     "表头数字另用纯 SQL 聚合核对，结果见 §0。",
     f"> **两种口径**：「短信」= LKUS_push 中 `$.para.email` 为空或不存在的请求（DR-002），本窗口 {fi(N)} 行；「全部」= 全部 LKUS_push 行，{fi(allrows)} 行（多出的 {email} 行带非空 email）。"
     "每张表的表头下写明所用口径与窗口。", "",
     "## 0. 数字核对", "", "| 核对项 | 单元格数 | 不一致 | 纯 SQL 合计 | 本地(E1) 合计 |", "|---|---|---|---|---|"]
for r in cx.itertuples():
    L.append(f"| {r.check} | {r.cells} | {r.mismatching_cells} | {fi(r.sql_total)} | {fi(r.e1_total)} |")
L += ["", f"- {len(cx)} 项核对共 {fi(cx.cells.sum())} 格，不一致 {fi(cx.mismatching_cells.sum())} 格：E1 本地汇总与纯 SQL 聚合{'逐格相同，下文的 E1 数字与纯 SQL 等价' if cx.mismatching_cells.sum() == 0 else '有差异，见上表'}。",
      "- 纯 SQL 来源：`sql/p4_daily_series.sql` → `results/p4_daily_series.csv`；`sql/p2_hits_7d.sql` → `results/p2_hits_7d.csv`。本地来源：`sql/e1_a.sql`、`sql/e1_b.sql`（E1）→ `results/p3_crosscheck.csv`。", ""]
# 1 daily results
rv_cids = ca[ca.review > 0]
L += ["## 1. 每日请求与最终结果", "", f"口径：{SMS}（「全部」列为全部 LKUS_push 行）。", "",
      "| 纽约日 | PASS | REJECT | REVIEW | 短信合计 | REJECT 占比 | 全部 LKUS_push |", "|---|---|---|---|---|---|---|"]
for r in dr.itertuples():
    n = r.sms_PASS + r.sms_REJECT + r.sms_REVIEW
    L.append(f"| {r.ny_date} | {fi(r.sms_PASS)} | {fi(r.sms_REJECT)} | {fi(r.sms_REVIEW)} | {fi(n)} | {pct(r.sms_REJECT / n)} | {fi(r.total)} |")
daily = dr.sms_PASS + dr.sms_REJECT + dr.sms_REVIEW
oth = dgr[dgr.cc_group == "other"].set_index("ny_date").drop(columns=["cc_group"]).sum(axis=1)
rule10 = rd("dr010_attack_rule.csv") if os.path.exists(os.path.join(R, "dr010_attack_rule.csv")) else None
L += [f"| **7 日** | **{fi(tot.sms_PASS)}** | **{fi(tot.sms_REJECT)}** | **{fi(tot.sms_REVIEW)}** | **{fi(N)}** | **{pct(tot.sms_REJECT / N)}** | **{fi(allrows)}** |", "",
      f"- 7 日 {fi(N)} 次短信请求，{pct(tot.sms_REJECT / N)} 被拦截；REVIEW {fi(tot.sms_REVIEW)} 次，全部来自 cid " + "、".join(str(c) for c in rv_cids.cid.unique()) + "（§8）。",
      f"- 短信日量 {fi(daily.min())}–{fi(daily.max())}：纽约日 {dr.ny_date[dr.ny_date <= sw_day].min()}…{sw_day} 为 {fi(daily[dr.ny_date <= sw_day].min())}–{fi(daily[dr.ny_date <= sw_day].max())}，"
      f"{dr.ny_date[dr.ny_date > sw_day].min()}…{dr.ny_date.max()}（`strategy_43NaEzJmiQFk` 于 {sw} UTC 转上线之后）为 {fi(daily[dr.ny_date > sw_day].min())}–{fi(daily[dr.ny_date > sw_day].max())}；每日非 +1/+86 请求 {fi(oth.min())}–{fi(oth.max())} 次"
      + (f"，攻击前基线（DR-010，{rule10.baseline.iloc[0]}）中位数 {fi(rule10.baseline_median.iloc[0])} 次。" if rule10 is not None else "。"),
      "- 来源：`results/p3_daily_result.csv`。", ""]
# 2 cc groups
L += ["## 2. 区号分组与 PASS 构成", "", f"口径：{SMS}。`country_code` 写法：{'；'.join(f'{r.cc_form} {fi(r.rows)} 行' for r in ccs.itertuples())}（`plus`=带 `+`；全部 LKUS_push 行口径）。"
      "统计时对 `1` 与 `+1` 两种写法都归入 +1。", "",
      "| 纽约日 | PASS | 其中 +1 | +86 | 其它区号 | 非 +1 占 PASS |", "|---|---|---|---|---|---|"]
for r in pc.itertuples():
    L.append(f"| {r.ny_date} | {fi(r.pass_total)} | {fi(r.pass_plus1)} | {fi(r.pass_plus86)} | {fi(r.pass_other)} | {pct(r.non_plus1_share_of_pass)} |")
p7 = pc[pc.ny_date == "7d"].iloc[0]; pdays = pc.iloc[:-1]
lo2 = pdays.sort_values("non_plus1_share_of_pass").iloc[0]
L += ["", f"- 7 日放行 {fi(p7.pass_total)} 次，其中 **{pct(p7.non_plus1_share_of_pass)} 来自非 +1 号码**（{fi(p7.pass_total - p7.pass_plus1)} 次）；+1 放行 {fi(p7.pass_plus1)} 次（日均 {p7.pass_plus1 / len(pdays):,.0f}）。",
      f"- 非 +1 放行占比在 {pct(pdays.non_plus1_share_of_pass.min())}–{pct(pdays.non_plus1_share_of_pass.max())} 之间，{lo2.ny_date} 最低；"
      "逐日见上表；非 +1 放行次数的计数拆分（43Na 唯一拦截、余项的请求量与放行率两部分、按是否满足 43Na 条件拆分的请求；计数分解，非因果；DR-027 自己的窗口）见 `04_数据问题结论.md#dr-027`。",
      "- 来源：`results/p3_pass_by_ccgroup.csv`、`results/p3_daily_ccgroup_result.csv`。", ""]
# 3 users
u7 = du[du.ny_date == "7d"].iloc[0]; ph, ui = sp.iloc[0], sp.iloc[1]
L += ["## 3. 去重手机号与 uid", "",
      f"口径：{SMS}。手机号 = `sharding_key`（= 带 `+` 的区号 + 手机号），uid = `$.para.uid`；两者都在 SQL 里做加盐 SHA-256 后在本地去重（跨分片精确）。**7 日行是整个窗口的去重数，不是逐日相加。**", "",
      "| 纽约日 | 请求 | 去重手机号 | 去重 uid | 放行手机号 | 其中 +1 放行手机号 | 按分片相加的 uid（会重复计） |", "|---|---|---|---|---|---|---|"]
for r in du.itertuples():
    L.append(f"| {r.ny_date} | {fi(r.requests)} | {fi(r.distinct_phones)} | {fi(r.distinct_uids)} | {fi(r.pass_distinct_phones)} | {fi(r.pass_plus1_distinct_phones)} | {fi(r.sum_per_shard_distinct_uids)} |")
L += ["", f"- 同一手机号只出现在 1 个分片（全部 LKUS_push 行口径，{W7}：{fi(ph.distinct)} 个手机号，跨分片 {int(ph.in_more_than_one_shard)} 个）→ 按分片 `COUNT(DISTINCT sharding_key)` 相加即精确值（DR-014）。",
      f"- uid 不是分片键：同口径 {fi(ui.distinct)} 个 uid 中 {fi(ui.in_more_than_one_shard)} 个出现在多个分片（最多 {int(ui.max_shards_per_identity)} 个），按分片相加会把 7 日短信 uid 从 {fi(u7.distinct_uids)} 高估到 {fi(u7.sum_per_shard_distinct_uids)}。",
      "- 来源：`results/p3_distinct_users.csv`、`results/p3_dr014_shard_spread.csv`。", ""]
# 4 cid x app
L += ["## 4. cid × app", "", f"口径：{SMS}。V3 分段 <0.3 / 0.3–0.8 / ≥0.8 / 无分数。", "",
      "| cid | 来源枚举 | app | 请求 | PASS 占比 | token 缺失 | token 为空 | V3<0.3 | V3 0.3–0.8 | V3≥0.8 | 无分数 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for r in ca.itertuples():
    L.append(f"| {r.cid} | {r.cid_origin} | {r.app} | {fi(r.requests)} | {pct(r.pass_share)} | {pct(r.token_absent_share)} | {pct(r.token_empty_share)} | "
             f"{pct(r.v3_lo)} | {pct(r.v3_mid)} | {pct(r.v3_hi)} | {pct(r.v3_missing_share)} |")
a105 = ca[(ca.cid == 105) & (ca.app != "<absent>")].iloc[0]; a106 = ca[(ca.cid == 106) & (ca.app != "<absent>")].iloc[0]
noapp = ca[ca.app == "<absent>"]
fids = v3f.dropna(subset=["v3_fid"]).groupby("v3_fid").with_score.sum()
L += ["", f"- Android（105，带 app）PASS 仅 {pct(a105.pass_share)}，V3<0.3 占 {pct(a105.v3_lo)}、V3≥0.8 占 {pct(a105.v3_hi)}；iOS（106，带 app）PASS {pct(a106.pass_share)}。",
      "- `app` 键缺失的行：" + "；".join(f"cid {r.cid} {fi(r.requests)} 次，token 缺失 {pct(r.token_absent_share)}、无分数 {pct(r.v3_missing_share)}、PASS {pct(r.pass_share)}" for r in noapp.itertuples()) + "（DR-012 / DR-006）。",
      "- V3 分数按**形状**取（任一 reCAPTCHA 特征的 apiResp 里有 `riskAnalysis.score`）。本窗口带分数的行全部来自 " + "、".join(f"`{f}`（{fi(n)} 行）" for f, n in fids.items() if n) +
      "；返回码分布见 `results/p3_v3_codes.csv`（`THIRD_FEATURE_RECAPTCHA_TOKEN_EMPTY` " + fi(v3c[v3c.v3_code == "THIRD_FEATURE_RECAPTCHA_TOKEN_EMPTY"].rows.sum()) + " 行）。",
      "- 来源：`results/p3_cid_app_profile.csv`、`results/p3_v3_codes.csv`、`results/p3_v3_fid_daily.csv`。", ""]
# 4.1 empty app
def share(cid, stt, dim, val):
    g = ep[(ep.cid == cid) & (ep.app_state == stt) & (ep.dimension == dim) & (ep.value.astype(str) == val)]
    return g.share_within_cid_app_state.iloc[0] if len(g) else 0.0
L += ["### 4.1 cid 105/106 有无 app 的对比（DR-012）", "", f"口径：{SMS}。", "",
      "| cid | app | 请求 | 最常见版本（行数） | 非 +1 区号 | IP 在美国 | REJECT | token 缺失 |", "|---|---|---|---|---|---|---|---|"]
for (cid, stt), g in ev.groupby(["cid", "app_state"]):
    n = int(g.rows.sum()); v = g.sort_values("rows", ascending=False).iloc[0]
    L.append(f"| {cid} | {'缺失' if stt == 'absent' else '有'} | {fi(n)} | {v.version}（{fi(v.rows)}） | {pct(1 - share(cid, stt, 'cc_group', '+1'))} | {pct(share(cid, stt, 'ip_country', '美国'))} | "
             f"{pct(share(cid, stt, 'final_result', 'REJECT'))} | {pct(share(cid, stt, 'token_state', 'absent'))} |")
L += ["", "- 版本分布全表：`results/p3_empty_app_versions.csv`。",
      "- UA 家族对两组都是 `luckin_app`（UA 本身不能区分有无 app），明细：`results/p3_empty_app_profile.csv`。", ""]
# 5 strategies
on = st[st.list == "online"].sort_values("pv", ascending=False).head(15)
L += ["## 5. 策略命中", "", f"口径：{SMS}。命中数按请求计；去重手机号是 7 日窗口去重。", "", "### 5.1 在线策略（命中次数前 15）", "",
      "| strategy_id | 处置 | 命中 | 去重手机号 | 名称 |", "|---|---|---|---|---|"]
for r in on.itertuples():
    L.append(f"| `{r.strategy_id}` | {r.result_name} | {fi(r.pv)} | {fi(r.uv_phones)} | {esc(r.strategy_name)} |")
onall = st[st.list == "online"]; top3 = onall.sort_values("pv", ascending=False).head(3)
n43 = onall[onall.strategy_id == "strategy_43NaEzJmiQFk"]
L += ["", f"- 7 日有命中的在线策略 {len(onall)} 条，前 3 名（" + "、".join(f"`{r.strategy_id}`" for r in top3.itertuples()) + f"）合计 {fi(top3.pv.sum())} 次，占在线命中 {pct(top3.pv.sum() / onall.pv.sum())}（同一请求可命中多条，占比按命中次数算）。"]
if len(n43):
    p43 = st[(st.list == "preonline") & (st.strategy_id == "strategy_43NaEzJmiQFk")]
    c27 = rd("dr027_e1_cells.csv"); aft = int(c27[(c27.phase == "after") & (c27.sms == 1)].s_preonline_hits.sum())
    L += [f"- `strategy_43NaEzJmiQFk` 于 {sw} UTC 转上线，窗口内在线命中 {fi(n43.pv.iloc[0])} 次；此前的预上线命中" + (f"（{fi(p43.pv.iloc[0])} 次，含切换后仍记在预上线名单的 {aft} 次）" if len(p43) else "") + "计入 5.2。"]
pre = st[st.list == "preonline"].copy()
pr = pre[pre.result_name != "PASS"].sort_values("extra_recall_pv", ascending=False)
L += ["", "### 5.2 预上线策略的额外召回", "",
      "额外召回 = 它若上线会改变结果的命中：非 PASS 类策略取最终结果是 PASS 的命中；PASS 类策略取最终结果不是 PASS 的命中（单列在表后）。", "",
      "| strategy_id | 处置 | 命中 | 额外召回（次） | 额外召回手机号 | 其中非 +1 | 其中 +1 | 名称 |", "|---|---|---|---|---|---|---|---|"]
for r in pr.itertuples():
    L.append(f"| `{r.strategy_id}` | {r.result_name} | {fi(r.pv)} | {fi(r.extra_recall_pv)} | {fi(r.extra_recall_phones)} | {fi(r.extra_recall_non_plus1_pv)} | {fi(r.extra_recall_plus1_pv)} | {esc(r.strategy_name)} |")
pp = pre[pre.result_name == "PASS"]
top2 = pr.head(2)
plus1 = pr[pr.extra_recall_plus1_pv > 0]
stw = tl[(tl.field == "status") & (tl.object_kind == "strategyId") & (tl.operation_time_utc >= utc0) & (tl.operation_time_utc < utc1)]
promo = stw[(stw.before.astype(str) == "2") & (stw.after.astype(str) == "1")]
newpre = stw[(stw.before.astype(str) == "0") & (stw.after.astype(str) == "2")]
demo = stw[(stw.before.astype(str) == "1") & (stw.after.astype(str) == "2")]
enab = tl[(tl.field == "status") & (tl.object_kind != "strategyId") & (tl.before.astype(str) == "0") & (tl.after.astype(str) == "1") & (tl.operation_time_utc >= utc0) & (tl.operation_time_utc < utc1)]
def promo_txt(r):
    d_ = demo[(demo.object_id == r.object_id) & (demo.operation_time_utc <= r.operation_time_utc)]
    if len(d_):
        return f"`{r.object_id}`（上线中于 {d_.operation_time_utc.iloc[-1]} UTC 转预上线，{r.operation_time_utc} UTC 转回上线）"
    return f"`{r.object_id}`（{r.operation_time_utc} UTC 由预上线转上线）"
cs = rd("config_strategy.csv", dtype=str)
zero = sorted(set(cs[(cs.scene_id == "LKUS_push") & (cs.status == "2")].strategy_id) - set(pre.strategy_id))
L += ["", "PASS 类预上线策略（额外召回 = 最终结果**不是** PASS 的命中，即它上线后会改成 PASS 的请求）：" + ("；".join(f"`{r.strategy_id}` 命中 {fi(r.pv)}，额外召回 {fi(r.extra_recall_pv)}（其中 +1 {fi(r.extra_recall_plus1_pv)}）" for r in pp.itertuples()) or "无") + "。", "",
      "- 额外召回最大的非 PASS 预上线策略：" + "、".join(f"`{r.strategy_id}`（{fi(r.extra_recall_pv)} 次，非 +1 {fi(r.extra_recall_non_plus1_pv)}）" for r in top2.itertuples()) + "。",
      "- 会打到 +1 号码的非 PASS 预上线策略：" + ("、".join(f"`{r.strategy_id}`（+1 额外召回 {fi(r.extra_recall_plus1_pv)}）" for r in plus1.itertuples()) or "无") + "——上线前必须核误伤。",
      "- 窗口内策略的状态切换（操作日志）：" + ("；".join([f"`{r.object_id}`（{r.operation_time_utc} UTC 由 0 转预上线）" for r in newpre.itertuples()] + [promo_txt(r) for r in promo.itertuples()]) or "无") + "；两段命中分别计入 5.1 与 5.2。"
      + (f"另有 {len(enab)} 个规则 / 特征于 {enab.operation_time_utc.min()}…{enab.operation_time_utc.max()} UTC 新建并启用（status 0 → 1）。" if len(enab) else ""),
      f"- 当前另有 {len(zero)} 条 LKUS_push 预上线策略 7 日 0 命中（额外召回 0）：" + ("、".join(f"`{z}`" for z in zero) or "无") + "（`results/config_strategy.csv`）。",
      "- 来源：`results/p3_strategies.csv`（策略名来自配置导出，含手机号的已屏蔽）。", ""]
# 6 leakage
nl = int(lk[lk.dimension == "cid"].rows.sum())
L += ["## 6. 放行泄漏（非 +1 的短信 PASS）", "", f"口径：{SMS}，最终结果 PASS 且区号不是 +1：共 {fi(nl)} 次（`results/p3_pass_leakage.csv`）。", ""]
for dim, title, k in (("cc", "按区号（前 10）", 10), ("ip_country", "按 IP 国家（前 8）", 8), ("phone_ne_ip_country", "手机号国家 ≠ IP 国家（1=不同）", 5),
                      ("cid", "按 cid", 5), ("token_state", "按 token 状态", 5), ("v3_bucket", "按 V3 分数段", 5), ("app_state", "按 app 键", 5)):
    g = lk[lk.dimension == dim].head(k)
    L.append(f"**{title}**：" + "；".join(f"{esc(r.value)} {fi(r.rows)}（{pct(r.share)}）" for r in g.itertuples()))
    L.append("")
us = lk[(lk.dimension == "ip_country") & (lk.value == "美国")]
tk = lk[(lk.dimension == "token_state")]
vb = lk[(lk.dimension == "v3_bucket")]
L += [f"- 泄漏里 IP 在美国的占 {pct(us.share.iloc[0]) if len(us) else '0%'}，条件写成 `realIpCountry 不等于 美国` 的策略天然放过这部分。",
      f"- token 缺失或为空合计 {pct(tk[tk.value.isin(['absent', 'empty'])].share.sum())}；V3≥0.8 占 {pct(vb[vb.value == '>=0.8'].share.sum())}——分数阈值类策略对这部分无效。", ""]
# 7 counters
bad = c7[c7.code != "SUCCESS"].sort_values("rows", ascending=False)
days = sorted(cd.ny_date.unique())
cond_ids = rd("p3_param_lists.csv").set_index("list").loc["cond_or_combo_counter_ids"].ids.split()
L += ["## 7. 累计特征返回码", "", f"口径：{SMS}。7 日内出现过非 SUCCESS 返回码的累计特征（`results/p3_counter_codes_7d.csv`；逐日见 `results/p3_counter_codes_daily.csv`）：", "",
      "| feature_id | 名称 | 返回码 | 次数 | 占该特征评估次数 |", "|---|---|---|---|---|"]
for r in bad.itertuples():
    L.append(f"| `{r.feature_id}` | {r.feature_name} | {r.code} | {fi(r.rows)} | {pct(r.share)} |")
L += ["", "逐日（带条件或组合维度的累计特征，DR-003 / DR-004）：", "", "| feature_id | 返回码 | " + " | ".join(days) + " |", "|---|---|" + "---|" * len(days)]
for (fid, code), g in cd[cd.feature_id.isin(cond_ids)].groupby(["feature_id", "code"]):
    m = dict(zip(g.ny_date, g.rows))
    L.append(f"| `{fid}` | {code} | " + " | ".join(fi(m.get(x, 0)) for x in days) + " |")
chg = tl[tl.object_id.isin(cond_ids) & tl.field.isin(["input_conditions", "input_hasCondition", "input_dimension"]) & (tl.operation_time_utc >= utc0)]
L += ["", "- `COUNTER_FEATURE_CONDITION_MISS` = 当前请求不满足该特征的过滤条件（仍返回计数值，规则照常使用，见 DR-003）；`PARAMS_ERROR` / `DIMENSION_EMPTY` 才是没有值——引用它的策略会一直 0 命中。",
      "- 同期的配置变化（操作日志，`results/p2_oplog_timeline.csv`）：" + "；".join(f"{r.operation_time_utc} UTC `{r.object_id}` {r.field} `{esc(r.before)}` → `{esc(r.after)}`" for r in chg.itertuples()) + "。", ""]
# 8 H5 chain
fr = rm[(rm.cid == 108) & (rm.final_result == "REVIEW")].rows.sum()
L += ["## 8. H5 A2 二次校验链路（cid 108）", "", f"口径：{SMS}。", "", "| 环节 | 次数 |", "|---|---|",
      f"| H5 短信请求 | {fi(h5.h5_requests)} |", f"| 最终返回 REVIEW | {fi(h5.final_review)} |",
      f"| 其中响应带 `model`（挑战参数） | {fi(h5.final_review_with_response_model)} |",
      f"| `reviewRepeat=true` 的请求（A2 复验） | {fi(h5.review_repeat_true)} |",
      f"| 其中 30 分钟内同一手机号先有 REVIEW | {fi(h5.review_repeat_true_linked_to_prior_review_30min)} |",
      f"| A2 复验结果：PASS / REJECT / 再次 REVIEW | {fi(h5.review_repeat_true_final_pass)} / {fi(h5.review_repeat_true_final_reject)} / {fi(h5.review_repeat_true_final_review)} |",
      f"| 引擎判 REVIEW、最终返回 PASS | {fi(h5.engine_review_final_pass)}（其中 reviewRepeat=true {fi(h5.engine_review_final_pass_with_review_repeat_true)}） |", "",
      f"- 最终 REVIEW {fi(h5.final_review)} 次中带挑战参数 {fi(h5.final_review_with_response_model)} 次；A2 复验 {fi(h5.review_repeat_true)} 次，{fi(h5.review_repeat_true_linked_to_prior_review_30min)} 次能在 30 分钟内接上同号码的前一次 REVIEW。",
      f"- 引擎判 REVIEW 而返回 PASS 的 {fi(h5.engine_review_final_pass)} 次里，{fi(h5.engine_review_final_pass - h5.engine_review_final_pass_with_review_repeat_true)} 次不是 A2 复验（`reviewRepeat=false`）——改写规则待林宏鹏说明（DR-016）。",
      "- 来源：`results/p3_h5_a2_chain.csv`、`results/p3_review_matrix.csv`。", ""]
# 9 standing items
L += ["## 9. 常设项（DR-016 / DR-017 / DR-018）", "",
      f"**DR-016 引擎结果 vs 最终结果**（{SMS}，`results/dr016_summary_7d.csv`、`results/dr016_engine_vs_final_7d.csv`）：引擎 REVIEW {fi(d16.engine_review_total)} 次，"
      f"最终 PASS {fi(d16.engine_review_final_pass)}（其中 cid 108 {fi(d16.engine_review_final_pass_cid108)}，reviewRepeat=true {fi(d16.engine_review_final_pass_review_repeat_true)}）、最终 REVIEW {fi(d16.engine_review_final_review)}；"
      f"引擎结果为空 {fi(d16.engine_empty_rows)} 次（其中最终 PASS {fi(d16.engine_empty_final_pass)}）。31 天分 cid × 版本的表在 2026-09-26 包（DR-024）。", "",
      "**DR-017 优先级高于白名单的非 PASS 策略**（配置 + 7 日命中，全部 LKUS 场景，`results/dr017_reject_above_whitelist.csv`）：", "",
      "| 场景 | strategy_id | 状态 | 处置 | 优先级 | 白名单优先级 | 7日在线命中（全部行） | 7日在线命中（短信） | 最后修改 (UTC) |", "|---|---|---|---|---|---|---|---|---|"]
for r in d17.itertuples():
    L.append(f"| `{r.scene_id}` | `{r.strategy_id}` | {r.status} | {r.result_code} | {r.exec_priority} | {r.whitelist_pass_priority} | {fi(r.hits_online_pv_7d_all_push_rows)} | {fi(r.hits_7d_sms_rows_e1)} | {r.update_time_utc} |")
on17 = d17[d17.status == 1]
L += ["", f"- {len(d17)} 条非 PASS 策略的优先级高于白名单 PASS，其中上线 {len(on17)} 条" + ("（" + "、".join(f"`{r.strategy_id}` 7 日在线命中 {fi(r.hits_online_pv_7d_all_push_rows)} 次" for r in on17.itertuples()) + "）" if len(on17) else "")
      + "；排序是否有意待段枝宏、田志鲔确认（DR-017）。"]
L += ["", "**DR-018 使用 UTC 时刻规则的上线 / 预上线策略**（配置 + 7 日命中，全部 LKUS_push 行，`results/dr018_time_rule_strategies.csv`）：", "",
      "| strategy_id | 状态 | 处置 | 时刻条件（UTC） | 7日在线命中 | 7日预上线命中 | 最后修改 (UTC) |", "|---|---|---|---|---|---|---|"]
for r in d18.itertuples():
    L.append(f"| `{r.strategy_id}` | {r.status} | {r.result_code} | {r.time_conditions_utc} | {fi(r.hits_online_pv_7d_all_push_rows)} | {fi(r.hits_preonline_pv_7d_all_push_rows)} | {r.update_time} |")
L += ["", "- 2026-11-01 夏令时结束后，UTC 02:00–09:00 对应的纽约时间从 22:00–05:00 变为 21:00–04:00（DR-018，待田志鲔决定是否改写）。", "",
      "<details><summary>附：SQL 与脚本</summary>", "",
      "- E1 抽取模板：`sql/e1_a.sql`、`sql/e1_b.sql`（同一模板，参数 `{scene}` `{rc_ids}` `{counter_ids}` `{time_rule_ids}`，ID 列表由 `sql/local/p3_params.py` 从配置导出生成；`{salt}` 为运行时随机盐，未保存）。",
      "- 本地汇总：`sql/local/p3_profile.py --start --end`（`--cuts` V3 分段可调）；常设项：`sql/local/p4_new_drs.py`。",
      "- 核对用纯 SQL：`sql/p4_daily_series.sql`、`sql/p2_hits_7d.sql`。",
      "- 每条语句的耗时：`results/timing.csv`；运行记录：`results/_runlog.csv`。", "", "</details>", ""]
open(os.path.join(PKG, f"03_近7日数据画像_{end.replace('-', '')}.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("03 written", len(L))
