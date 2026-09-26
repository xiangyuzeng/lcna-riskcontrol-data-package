#!/usr/bin/env python3
"""P4: write 04_数据问题结论.md — one section per DR (anchor <a id="dr-xxx"></a>), fixed fields.
Every number is read from results/ of this run. The per-DR「新状态」lines are the single source for the README totals
(sql/local/p6_readme.py parses them)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
fi = lambda v: f"{int(v):,}"
pct = lambda x: f"{100 * x:.1f}%"
esc = lambda v: "" if pd.isna(v) else str(v).replace("|", "\\|")
S = {}          # DR -> (status, one-liner)
B = []          # body lines


def sec(dr, title, q, sql, res, concl, conf, who, status, line):
    S[dr] = (status, line)
    B.extend([f'<a id="{dr.lower()}"></a>', "", f"## {dr} {title}", "", f"- **问题**：{q}", f"- **SQL**：{sql}", f"- **结果**：{res}",
              f"- **结论**：{concl}", f"- **置信度**：{conf}", f"- **谁确认**：{who}", f"- **新状态**：{status}", "", "---", ""])


def table(df, cols=None, n=None):
    df = df if cols is None else df[cols]
    df = df if n is None else df.head(n)
    return "\n\n  | " + " | ".join(df.columns) + " |\n  |" + "---|" * len(df.columns) + "\n" + "\n".join(
        "  | " + " | ".join(esc(f"{v:,}" if isinstance(v, int) else v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n\n"


k1 = rd("p1_chk_consistency.csv"); n7 = int(k1.n.sum()); win = sorted(k1.ny_date.unique()); W7 = f"纽约日 {win[0]}…{win[-1]}"
# ---------------- DR-002 ----------------
em = int(k1[k1.email_nonempty == 1].n.sum()); ek = int(k1[k1.email_key == 1].n.sum())
sec("DR-002", "推送场景如何区分短信与邮件",
    "Doris 里 `l2_scene='1001'` 是否就是短信、`'1002'` 是否就是邮件？源库 `t_access_log_*` 没有这一列，用什么规则区分？（`DATA_REQUESTS.md`：部分答复，待 Doris 里 `l2_scene='1002'` 的直接对照）",
    "`sql/p1_chk_consistency.sql`、`sql/p1_dr002_email_signals.sql`；Grafana 面板 SQL 原文 `results/p0_grafana_patrol_panels.md`",
    f"{W7} LKUS_push {fi(n7)} 行全部带非空 `phoneNo`；带 `email` 键 {ek} 行、非空 email {em} 行（`results/p1_chk_consistency.csv`）。Grafana 巡检大盘的短信口径是 Doris `l1_scene='1000' AND l2_scene='1001'`。",
    "规则不变：`$.para.email` 非空 → 邮件候选，其余为短信；每行恰好落在一类。与 Doris `l2_scene='1002'` 的直接对照仍做不了——Doris 不可达（DR-020）。",
    "中（规则与数据一致，但缺数仓对照）", "林宏鹏（`l2_scene` 的生成规则）",
    "部分答复（本次受阻：Doris 不可达，见 DR-020）", f"规则不变（email 非空 → 邮件）；7 日 {em} 行带 email；与 `l2_scene` 对照仍受阻于 Doris")
# ---------------- DR-003 ----------------
s3 = rd("dr003_codes_summary.csv"); p3 = rd("dr003_codes_daily_pivot.csv")
codes = [c for c in s3.columns if c.startswith("COUNTER_FEATURE") or c == "SUCCESS"]
t3 = s3[["feature_id", "feature_name_now", "first_day", "last_day", "rows"] + [c for c in codes if not c.endswith("_share")]].copy()
e1k = p3[p3.feature_id == "feature_e1Kmz7JqzsWc"].set_index("ny_date")
dq = p3[p3.feature_id == "feature_dqBHKec09Wwa"].set_index("ny_date")
last = p3.ny_date.max()
tl = rd("p2_oplog_timeline.csv")
chg = tl[tl.object_id.isin(s3.feature_id) & tl.field.isin(["input_conditions", "input_hasCondition", "input_dimension"])]
sec("DR-003", "带条件 / 组合维度累计特征的返回码（常设）",
    "每个带过滤条件或组合维度的累计特征，每天返回 `SUCCESS` / `CONDITION_MISS` / `PARAMS_ERROR` / `DIMENSION_EMPTY` 各多少？",
    "`sql/dr003_codes_daily.sql`（特征列表由 `sql/local/p3_params.py` 从配置与操作日志生成）；汇总 `sql/local/p4_agg_drs.py`",
    f"LKUS_push、纽约日 2026-08-25…{last}，逐日见 `results/dr003_codes_daily_pivot.csv`，合计：" + table(t3) +
    "  同期的条件 / 维度变化（`results/p2_oplog_timeline.csv`）：" + "；".join(f"{r.operation_time_utc} UTC `{r.object_id}` {r.field}：`{esc(r.before)[:70]}` → `{esc(r.after)[:70]}`" for r in chg.itertuples()),
    f"`feature_e1Kmz7JqzsWc` 从上线到 2026-09-24 07:24 UTC 条件列表为空，返回 `PARAMS_ERROR`（合计 {fi(s3.set_index('feature_id').loc['feature_e1Kmz7JqzsWc', 'COUNTER_FEATURE_PARAMS_ERROR'])} 次）；补上条件后 {last} 当天 PARAMS_ERROR {fi(e1k.loc[last].get('COUNTER_FEATURE_PARAMS_ERROR', 0))} 次。"
    f"`feature_dqBHKec09Wwa` 在 2026-09-24 07:22 UTC 去掉条件，{last} 当天 CONDITION_MISS {fi(dq.loc[last].get('COUNTER_FEATURE_CONDITION_MISS', 0))} 次（=不再过滤）。组合维度两个特征见 DR-004。"
    + "其余特征：" + "；".join(f"`{r.feature_id}` " + "、".join(f"{c.replace('COUNTER_FEATURE_', '')} {fi(r[c])}" for c in codes if not c.endswith('_share') and r[c] > 0) for _, r in s3[~s3.feature_id.isin(['feature_e1Kmz7JqzsWc', 'feature_dqBHKec09Wwa', 'feature_AemrK847uPtt', 'feature_bvE9FL19wqag'])].iterrows()) + "。",
    "高（逐日全量计数）", "贡锁泉（09-24 公告所指现象是否就是这几处）", "已答复",
    "e1K 条件为空致 PARAMS_ERROR 至 09-24 07:24 UTC 已修；dqBH 09-24 去掉条件；组合维度仍 DIMENSION_EMPTY")
# ---------------- DR-004 ----------------
cmb = p3[p3.feature_id.isin(["feature_AemrK847uPtt", "feature_bvE9FL19wqag"])]
cmb_last = cmb[cmb.ny_date == last]
de = int(cmb_last.get("COUNTER_FEATURE_DIMENSION_EMPTY", pd.Series([0])).sum()); tot_last = int(cmb_last.rows.sum())
h25 = rd("dr025_daily_summary.csv") if ex("dr025_daily_summary.csv") else None
to7 = h25[h25.strategy_id == "strategy_tO7DZkJ1g0C2"] if h25 is not None else pd.DataFrame()
sec("DR-004", "组合维度特征修好之后重估（条件运行）",
    "组合维度 `realIp|phoneNo` 的累计特征修好后，用 tk02 / tk03 重估其策略的命中与额外召回。",
    "`sql/dr003_codes_daily.sql`、`sql/dr025_hourly_hits.sql`",
    f"{last} 两个组合维度特征共评估 {fi(tot_last)} 次，其中 `DIMENSION_EMPTY` {fi(de)} 次（`results/dr003_codes_daily_pivot.csv`）。"
    + ("引用它们的 `strategy_tO7DZkJ1g0C2` 每日命中（UTC 日，`results/dr025_daily_summary.csv`）：" + table(to7.drop(columns=["strategy_id"])) if len(to7) else ""),
    "特征**仍未修好**（维度自 2026-09-20 02:39/02:40 UTC 改为 `realIp|phoneNo` 后一直取不到值），本轮的运行条件不满足，未重估。修好后用 tk02 / tk03 重跑。",
    "高", "林宏鹏（组合维度的正确写法）", "已答复", f"仍未修好：{last} DIMENSION_EMPTY {fi(de)}/{fi(tot_last)}，未重估")
# ---------------- DR-007 ----------------
if ex("dr007_join_utc_day_cc.csv"):
    pc7 = rd("dr007_upush_pii_check.csv").iloc[0]
    dg = rd("dr007_daily_ccgroup.csv"); fr = rd("dr007_fill_rate_by_cc.csv"); p1d = dg[dg.ccg == "+1"]
    base_p, rec_p = sorted(fr.period.unique())
    fb = fr[fr.period == base_p].set_index("cc"); frc = fr[fr.period == rec_p].set_index("cc")
    otp = rd("dr007_otp_basis.csv") if ex("dr007_otp_basis.csv") else None
    fb.index = fb.index.astype(str); frc.index = frc.index.astype(str)
    sec("DR-007", "短信验证码回填：按日 × 区号与风控放行对照",
        "读 `t_verifycode_filled_statistics` 的按日汇总（发送 / 填充，按日 × 区号），与短信画像按日 × 区号关联，把额外召回与误伤放到 OTP 回填口径上。",
        "`sql/dr007_upush_pii_check.sql`、`sql/dr007_upush_daily.sql`（`aws-luckyus-upush-rw`，只做 SUM）、`sql/dr007_risk_utc_daily.sql`；关联 `sql/local/p4_agg_drs.py`" + ("、`sql/local/p4_new_drs.py`" if otp is not None else ""),
        f"统计表形状检查：{fi(pc7.n_rows)} 行，{pc7.min_date}…{pc7.max_date}，区号 {int(pc7.n_area_codes)} 种、最长 {int(pc7.max_len_area_code)} 字符、含 5 位以上数字的区号 {int(pc7.n_area_code_5plus_digits)} 个；项目 / 提供商 / 租户里含 7 位数字或 @ 的值 {int(pc7.n_project_digits_or_at + pc7.n_provider_digits_or_at + pc7.n_tenant_digits_or_at)} 个 → 无个人信息（`results/dr007_upush_pii_check.csv`）。"
        "+1 按 UTC 日（`results/dr007_daily_ccgroup.csv`）：" + table(p1d[["utc_date", "risk_sms_requests", "risk_sms_pass", "upush_sent", "upush_filled", "upush_fill_rate", "upush_sent_per_risk_pass"]].tail(14)) +
        f"  区号级回填率（`results/dr007_fill_rate_by_cc.csv`）：{base_p} +1 {pct(fb.loc['1'].fill_rate) if '1' in fb.index else '—'}；{rec_p} +1 {pct(frc.loc['1'].fill_rate) if '1' in frc.index else '—'}。"
        + ("  OTP 口径折算（短信口径、7 日、非 PASS 预上线策略；折算真人数 = Σ 区号额外召回 × 该区号 base 期回填率）：" + table(otp.drop(columns=["basis"]).head(12)) if otp is not None else ""),
        f"+1 的「统计表发送数 / 风控短信放行」在 {p1d[p1d.utc_date <= '2026-09-20'].utc_date.min()}…2026-09-20 为 {p1d[p1d.utc_date <= '2026-09-20'].upush_sent_per_risk_pass.min():.2f}–{p1d[p1d.utc_date <= '2026-09-20'].upush_sent_per_risk_pass.max():.2f}，"
        f"2026-09-21 降到 {p1d[p1d.utc_date == '2026-09-21'].upush_sent_per_risk_pass.iloc[0]:.2f}，2026-09-22 起只有 {p1d[(p1d.utc_date >= '2026-09-22') & (p1d.utc_date <= '2026-09-25')].upush_sent_per_risk_pass.min():.2f}–{p1d[(p1d.utc_date >= '2026-09-22') & (p1d.utc_date <= '2026-09-25')].upush_sent_per_risk_pass.max():.2f}——"
        "统计表从 09-21 起漏记了绝大部分 +1 发送（与团队 09-25 记录的「Twilio OTP 账号送达回执 09-21 19:04 UTC 起中断、统计表只收有回执的发送」一致），而记下来的那部分回填率照旧约 95%。"
        f"所以回填率只能用 {base_p} 的数：+1 {pct(fb.loc['1'].fill_rate)}；攻击主力区号接近 0（如 " + "、".join(f"+{c} {pct(fb.loc[c].fill_rate)}" for c in [c for c in ['265', '92', '375', '264', '386', '992'] if c in fb.index]) + "）。"
        "统计表按 `statistic_date` 汇总，本包按 UTC 日与风控日志关联（统计日的时区需陈晨昕确认）。"
        "OTP 口径的额外召回只能按区号回填率**折算**（假设命中请求与该区号全部发送的回填率相同，`results/dr007_otp_basis.csv`），不是逐请求的硬标签；逐请求判定需要逐行关联，不在本包允许范围内。",
        "中（聚合口径可靠；折算依赖同回填率假设；09-21 起的统计缺口需推送团队确认）", "陈晨昕（统计表口径、`statistic_date` 的时区、09-21 起的缺口）",
        "待确认（问人：陈晨昕）", f"base 期 +1 回填率 {pct(fb.loc['1'].fill_rate)}、攻击区号≈0；统计表 09-21 起漏记约九成 +1 发送；OTP 口径只能按区号折算")
else:
    sec("DR-007", "短信验证码回填：按日 × 区号与风控放行对照", "…", "—", "未能获取：upush 汇总未取到", "—", "—", "陈晨昕", "待取数（本次受阻：upush 汇总未取到）", "本次未取到")
# ---------------- DR-010 ----------------
ar = rd("dr010_attack_rule.csv"); ps = rd("dr010_period_summary.csv"); ds = rd("dr010_daily_series.csv")
k5 = ar[ar.k == 5].iloc[0]; k3 = ar[ar.k == 3].iloc[0]
sec("DR-010", "美国号码短信日基线与攻击日（常设）",
    "刷新 +1 短信放行基线与攻击日标记：固定基线 = 序列前 28 天（序列从 2026-06-01 开始），指标 = 每日非 +1/+86 短信请求量，攻击日 = 中位数 + k × MAD（MAD×1.4826），迭代剔除，k=5 为默认、k=3 为敏感性检查。",
    "`sql/p4_daily_series.sql`（纽约日 2026-06-01…" + ds.ny_date.max() + "）；计算 `sql/local/p4_agg_drs.py`",
    f"基线 {k5.baseline}：中位数 {k5.baseline_median}、MAD×1.4826 = {k5.baseline_mad_scaled}。k=5 阈值 {k5.threshold}，首个攻击日 {k5.first_flagged_day}，共 {int(k5.flagged_days)} 天；"
    f"k=3 阈值 {k3.threshold}，首个攻击日 {k3.first_flagged_day}，共 {int(k3.flagged_days)} 天（`results/dr010_attack_rule.csv`）。按月 × 是否攻击日（k=5）的 +1 短信放行日均（`results/dr010_period_summary.csv`）：" + table(ps) +
    f"  最近两天 {ds.ny_date.iloc[-2]} / {ds.ny_date.iloc[-1]}：非 +1/+86 请求 {fi(ds.non_plus1_plus86_requests.iloc[-2])} / {fi(ds.non_plus1_plus86_requests.iloc[-1])}，+1 放行 {fi(ds.plus1_pass.iloc[-2])} / {fi(ds.plus1_pass.iloc[-1])}（`results/dr010_daily_series.csv`）。",
    f"攻击仍在持续（最近一天仍高于 k=5 阈值）；+1 短信放行在攻击日与非攻击日处于同一量级，没有看到 +1 放行被挤压。已知攻击起点只用于检验：规则给出的首个攻击日为 {k5.first_flagged_day}（k=5）。",
    "高（全量逐日计数）", "田志鲔（基线口径）", "已答复", f"k=5：{k5.first_flagged_day} 起 {int(k5.flagged_days)} 个攻击日，仍在持续；攻击日 +1 放行日均与非攻击月同量级")
# ---------------- DR-012 ----------------
v12 = rd("dr012_cid105_app_vs_noapp_summary.csv"); vv = rd("dr012_cid105_versions_by_app.csv")
a0 = v12[v12.app_state == "absent"].iloc[0]; a1 = v12[v12.app_state == "present"].iloc[0]
top_abs = vv[vv.app_state == "absent"].sort_values("rows", ascending=False).head(5)
top_pre = vv[vv.app_state == "present"].sort_values("rows", ascending=False).head(8)
sec("DR-012", "cid 105 有 app 的请求的版本分布（作为无 app 组的对照）",
    "cid 105 **带** `app` 的请求版本分布，作为无 `app` 组的对照；另问林宏鹏：App 版本 1.3.50 是否存在？",
    "E1 抽取 `sql/e1_a.sql`、`sql/e1_b.sql` → `sql/local/p4_new_drs.py`（版本按数值比较）",
    f"{W7}，短信口径。无 app：{fi(a0.rows)} 次、{fi(a0.distinct_phones)} 个手机号、{int(a0.distinct_versions)} 个版本，≥1.4.30 占 {pct(a0.share_ge_min)}、+1 占 {pct(a0.share_plus1)}、带 token {pct(a0.share_token_present)}；"
    f"有 app：{fi(a1.rows)} 次、{fi(a1.distinct_phones)} 个手机号、{int(a1.distinct_versions)} 个版本，≥1.4.30 占 {pct(a1.share_ge_min)}、+1 占 {pct(a1.share_plus1)}、带 token {pct(a1.share_token_present)}（`results/dr012_cid105_app_vs_noapp_summary.csv`）。"
    "无 app 的版本：" + "、".join(f"{r.version}（{fi(r.rows)}）" for r in top_abs.itertuples()) + "；有 app 的前 8 个版本：" + "、".join(f"{r.version}（{fi(r.rows)}）" for r in top_pre.itertuples()) + "（`results/dr012_cid105_versions_by_app.csv`）。",
    f"两组版本几乎不重叠：带 app 的请求 {pct(a1.share_ge_min)} 在 1.4.30 及以上，无 app 的全部低于 1.4.30。无 app 组不带 token、几乎全是非 +1，与攻击流量特征一致；"
    "它自报的旧版本是否真实存在只能由客户端团队确认。",
    "中（数据对比清楚；「伪造」是推断）", "林宏鹏（1.3.50 是否存在；无 app 的 105 请求从哪里来）", "待确认（问人：林宏鹏）",
    f"有 app 的 105 {pct(a1.share_ge_min)} ≥1.4.30；无 app 的全部 <1.4.30、无 token；1.3.50 是否存在待林宏鹏")
# ---------------- DR-013 ----------------
sec("DR-013", "MCP 能连到哪些库；Doris 是否可达（常设）",
    "本环境能否读到 Doris `ods_luckyus_iriskcontrol`？",
    "`sql/p0_*.sql`、`sql/p1_fleet_sweep_mysql.sql`；Grafana 数据源元数据（MCP server `grafana-lucky`）",
    "`mcp-db-gateway`：64 个 MySQL + 1 个 PG，均无 `ods_*` 库；风控库为主库、账号只有 SELECT/PROCESS/EXECUTE（`results/p0_server_vars.csv`、`results/p0_user_privileges.csv`）。`grafana-lucky` 有数据源 `Doris-iriskcontrol`（database `ods_luckyus_iriskcontrol`），但 MCP 没有执行 SQL 数据源查询的工具。Redshift `list_clusters` 报错。",
    "Doris 仍不可达。", "高", "—", "已答复", "Doris 仍不可达（gateway 无 ods_*；Grafana MCP 无 SQL 工具）")
# ---------------- DR-014 ----------------
sk = rd("p1_sk_concat_check_20260925.csv"); sp = rd("p3_dr014_shard_spread.csv")
sec("DR-014", "分片键抽查（常设）",
    "LKUS_push 的 `sharding_key = CONCAT(country_code, phone)` 是否仍成立？",
    "`sql/p1_sk_concat_check_20260925.sql`；E1 本地核对 `sql/local/p3_profile.py`",
    f"纽约日 2026-09-25：{fi(sk.n.sum())} 行中 {fi(sk.n_sk_eq_cc_col_plus_phone_col.sum())} 行成立（`results/p1_sk_concat_check_20260925.csv`）。{W7} 全部 LKUS_push 行 {fi(sp.iloc[0].distinct)} 个手机号跨分片 {int(sp.iloc[0].in_more_than_one_shard)} 个；uid {fi(sp.iloc[1].distinct)} 个中 {fi(sp.iloc[1].in_more_than_one_shard)} 个跨分片（`results/p3_dr014_shard_spread.csv`）。",
    "仍成立：同一手机号只在一个分片；uid 跨分片。非 push 场景见 DR-021。", "高", "—", "已答复", "仍成立（2026-09-25 抽查 100%）；uid 跨分片")
# ---------------- DR-015 ----------------
cfg_n = {f[7:-4]: len(pd.read_csv(os.path.join(R, f))) if os.path.getsize(os.path.join(R, f)) > 5 else 0 for f in os.listdir(R) if f.startswith("config_") and f.endswith(".csv")}
tln = rd("p2_oplog_timeline.csv")
sec("DR-015", "配置与变更日志导出（常设）",
    "每轮导出线上配置与操作日志。",
    "`sql/config_*.sql`、`sql/p2_list_counts.sql`、`sql/p2_oplog_*.sql`",
    f"17 张定义表整表导出（策略 {cfg_n.get('strategy', 0)}、规则 {cfg_n.get('rule', 0)}、第三方/累计特征 {cfg_n.get('third_feature', 0)}、参数 {cfg_n.get('para', 0)}…），名单只给条数；操作日志 {tln.op_id.nunique()} 次操作、{len(tln)} 处字段变化，{tln.operation_time_utc.min()} … {tln.operation_time_utc.max()} UTC。详见 `02_线上配置导出.md`。",
    "已导出；名单按类型 × 场景 × 来源的条数见 `results/p2_list_counts_by_scene.csv`（名单条目属于租户，场景经名单特征引用）。与 2026-09-24 快照的差异由桌面 D1 计算。", "高", "—", "已答复",
    "17 张定义表 + 名单按类型 × 场景 × 来源计数 + 操作日志时间线已导出")
# ---------------- DR-016 ----------------
d16 = rd("dr016_summary_7d.csv").iloc[0]
d24s = rd("dr024_summary_31d.csv") if ex("dr024_summary_31d.csv") else None
extra16 = ""
if d24s is not None:
    rv_ = d24s.engine_result.astype(str).str.startswith("REVIEW")
    rp = d24s[rv_ & (d24s.final_result == "PASS")].n.sum(); rt = d24s[rv_].n.sum()
    ep_ = d24s[(d24s.engine_result.isin(["<none>", ""])) & (d24s.final_result == "PASS")].n.sum()
    extra16 = f"31 天（纽约日 2026-08-25…09-24，短信口径，`results/dr024_summary_31d.csv`）：引擎 REVIEW 类（REVIEW / REVIEW_15_NINE / REVIEW_18_ICON）{fi(rt)} 次中最终 PASS {fi(rp)}；引擎无结果且最终 PASS {fi(ep_)} 次。"
sec("DR-016", "引擎结果被改写（常设计数）",
    "引擎判 REVIEW 却返回 PASS、引擎无结果却返回 PASS 的次数。改写规则需要开发说明。",
    "E1 → `sql/local/p4_new_drs.py`；31 天 `sql/dr024_engine_vs_final.sql`",
    f"{W7}，短信口径：引擎 REVIEW {fi(d16.engine_review_total)} 次，最终 PASS {fi(d16.engine_review_final_pass)}（全部 cid 108 的 {fi(d16.engine_review_final_pass_cid108)} 次里 reviewRepeat=true {fi(d16.engine_review_final_pass_review_repeat_true)}）、最终 REVIEW {fi(d16.engine_review_final_review)}；引擎结果为空 {fi(d16.engine_empty_rows)} 次（`results/dr016_summary_7d.csv`）。" + extra16,
    "改写仍在发生且只在 H5（108）；一部分是 A2 复验后的放行，其余不是。改写条件需要平台说明。", "高（计数）；原因待确认", "林宏鹏", "待确认（问人：林宏鹏）",
    f"7 日引擎 REVIEW {fi(d16.engine_review_total)} 次中 {fi(d16.engine_review_final_pass)} 次返回 PASS（全部 H5）")
# ---------------- DR-017 ----------------
d17 = rd("dr017_reject_above_whitelist.csv"); on17 = d17[d17.status == 1]
sec("DR-017", "优先级高于白名单的非 PASS 策略（常设）",
    "列出优先级高于白名单 PASS 策略的 REJECT / REVIEW 策略的当前优先级、状态与命中。",
    "配置 `results/config_strategy.csv` + 命中 `sql/p2_hits_7d.sql` → `sql/local/p4_new_drs.py`",
    f"全部 LKUS 场景共 {len(d17)} 条，其中上线 {len(on17)} 条：" + "；".join(f"`{r.strategy_id}`（{r.scene_id}，{r.result_code}，优先级 {r.exec_priority} > 白名单 {r.whitelist_pass_priority}，7 日在线命中 {fi(r.hits_online_pv_7d_all_push_rows)}，最后修改 {r.update_time_utc} UTC）" for r in on17.itertuples())
    + "；其余为下线（`results/dr017_reject_above_whitelist.csv`）。",
    "仍有 REJECT 策略排在白名单之前，白名单号码也会被它拦。" + (" 它的命中集中在个别小时：" + "；".join(f"{r.utc_hour} UTC {fi(r.pv)} 次" for r in rd("dr025_hourly_summary.csv").query("strategy_id == 'strategy_sw3jC7bvFYEX' and pv > 0").itertuples()) + "（`results/dr025_hourly_summary.csv`）。" if ex("dr025_hourly_summary.csv") else "") + "是否有意需要策略负责人确认。", "高（配置事实）", "段枝宏、田志鲔", "待确认（问人：段枝宏、田志鲔）",
    "；".join(f"`{r.strategy_id}` 优先级 {r.exec_priority} 仍上线、7 日 {fi(r.hits_online_pv_7d_all_push_rows)} 次" for r in on17.itertuples()))
# ---------------- DR-018 ----------------
d18 = rd("dr018_time_rule_strategies.csv")
sec("DR-018", "UTC 时刻规则遇夏令时（常设）",
    "列出使用 UTC 时刻规则的上线 / 预上线策略及其命中；2026-11-01 夏令时结束后它们对应的纽约时间会偏 1 小时。",
    "配置 + `sql/p2_hits_7d.sql` → `sql/local/p4_new_drs.py`",
    table(d18[["strategy_id", "status", "result_code", "time_conditions_utc", "hits_online_pv_7d_all_push_rows", "hits_preonline_pv_7d_all_push_rows", "update_time"]]) + f"  （{W7}，全部 LKUS_push 行，`results/dr018_time_rule_strategies.csv`）",
    "UTC 02:00–09:00 目前对应纽约 22:00–05:00，11-01 之后对应 21:00–04:00。是否按纽约时间改写要策略负责人决定。", "高（配置事实）", "田志鲔", "待确认（问人：田志鲔）",
    f"{len(d18)} 条策略用 UTC 时刻规则（上线 {int((d18.status == 1).sum())}、预上线 {int((d18.status == 2).sum())}）")
# ---------------- DR-020 ----------------
sec("DR-020", "Doris 只读通道：`grafana-lucky` 能否在 §3 内查询",
    "`grafana-lucky` MCP server 能否在 §3 的约束内查询 Grafana 的 Doris 数据源？能的话先出 `l2_scene` × 是否带 email × 纽约日的计数。",
    "Grafana 数据源元数据（`list_datasources`、`get_datasource_by_uid`）与看板面板（`get_dashboard_property`）；无 SQL",
    "`grafana-lucky` 能列出数据源 `Doris-iriskcontrol`（type mysql，database `ods_luckyus_iriskcontrol`），能读看板面板 SQL 文本（`results/p0_grafana_patrol_panels.md`）；它提供的工具只有 PromQL、LogQL、看板、告警与数据源元数据，**没有执行 SQL 数据源查询的工具**。",
    "不能。通过 Grafana HTTP 接口（`/api/ds/query`）查询需要 API 令牌且不走 MCP 只读工具，不在 §3 允许范围内，未尝试。要拿到 Doris 数据，需要数据平台开一个 Doris 只读账号并接入 `mcp-db-gateway`，或部署带 SQL 数据源查询工具的 Grafana MCP。",
    "高", "数据平台 / 林宏鹏（开只读账号或接入方式）", "已答复", "不能：Grafana MCP 无 SQL 工具；需数据平台开 Doris 只读账号")
# ---------------- DR-023 ----------------
t23 = rd("dr023_strategy_day_cid_geo.csv")
top23 = t23.groupby(["list", "strategy_id"]).hit_pv.sum().sort_values(ascending=False).head(6)
tk8 = rd("toolkit_tests/_test_summary.csv") if ex("toolkit_tests/_test_summary.csv") else None
tk8r = tk8[tk8.test.str.startswith("tk08")] if tk8 is not None else pd.DataFrame()
sec("DR-023", "模板：策略 × 纽约日 × cid × (phoneCountry ≠ realIpCountry)",
    "给出（或在 tk02 上加参数）按策略 × 纽约日 × cid × 手机号国家是否 ≠ IP 国家统计命中 PV 与去重手机号的模板，只给计数并写明口径。",
    "`toolkit/tk08_strategy_cid_geo.sql`（新模板）；本包 7 日全量表由 E1 本地算 `sql/local/p4_new_drs.py`",
    f"全量表 `results/dr023_strategy_day_cid_geo.csv`（{W7}，短信口径，在线与预上线分列；去重手机号在每一行内精确，行与行之间不能相加），{len(t23):,} 行。命中最多的：" + "；".join(f"{a} `{b}` {fi(n)}" for (a, b), n in top23.items()) + "。"
    + (" 模板测试：" + "；".join(f"{r.test} {r.toolkit}/{r.reference}" for r in tk8r.itertuples()) + "（`results/toolkit_tests/_test_summary.csv`）。" if len(tk8r) else ""),
    "模板可直接用；参数 `strategy_id`、`hit_list`（在线 / 预上线）、`sms_only`、窗口（≤1 纽约日/条）。", "高", "—", "已答复", "新模板 tk08 + 7 日全量表（去重手机号行内精确）")
# ---------------- DR-021 ----------------
if ex("dr021_best_candidate.csv"):
    bc = rd("dr021_best_candidate.csv"); sm21 = rd("dr021_summary.csv")
    lk21 = bc[bc.scene_id.str.startswith("LKUS")].sort_values(["scene_id", "ny_date"])
    piv = lk21.pivot_table(index="scene_id", columns="ny_date", values="best_share", aggfunc="first")
    bestk = lk21.groupby("scene_id").best_candidates.agg(lambda s: " / ".join(sorted(set(s))))
    tbl = pd.DataFrame({"scene_id": piv.index, "相等占比最高的候选（并列用 + 连接）": bestk.reindex(piv.index).values,
                        **{f"{d} 相等占比": piv[d].map(lambda v: pct(v) if pd.notna(v) else "—").values for d in piv.columns},
                        "行数（3 天）": lk21.groupby("scene_id").rows.sum().reindex(piv.index).map(fi).values})
    push = sm21[sm21.scene_id == "LKUS_push"]
    sec("DR-021", "推送以外场景的分片键",
        "各场景 `sharding_key` 与 `CONCAT(country_code, phone)`、`userNo`、`uid` 等候选相等的行占比；推送场景抽查三天。",
        "`sql/dr021_sharding_key_by_scene.sql`、`sql/dr021_sharding_key_by_scene_0922.sql`、`sql/dr021_sharding_key_by_scene_0925.sql`（纽约日 2026-09-19 / 09-22 / 09-25，全部场景，只做二进制相等计数）；汇总 `sql/local/p4_agg_drs.py`",
        "每个场景相等占比最高的候选（`results/dr021_best_candidate.csv`；全部候选的逐项占比 `results/dr021_summary.csv`）：" + table(tbl) +
        f"  LKUS_push 三天：" + "；".join(f"{r.ny_date} {fi(r.n)} 行，= `CONCAT(country_code, phone)` {pct(r.share_eq_cc_col_phone_col)}、= `fullPhoneNo` {pct(r.share_eq_fullPhoneNo)}" for r in push.itertuples()) + "。",
        "分片键因场景而异，三天都 100% 成立：" + "；".join(f"{k}：" + "、".join(f"`{s_}`" for s_ in v) for k, v in (("完整手机号（= `CONCAT(country_code, phone)` = `fullPhoneNo`）", sorted(lk21[lk21.best_candidates.str.contains("fullPhoneNo")].scene_id.unique())), ("`userNo`（= `user_no` 列）", sorted(lk21[lk21.best_candidates.str.contains("userNo")].scene_id.unique())))) +
        "。按分片相加的去重数只对该场景的分片键成立：在 userNo 分片的场景里，同一手机号会跨分片。推送场景的规则本轮仍成立。",
        "高（全量计数）", "林宏鹏（分片规则的出处）", "已答复", "push / register / captcha 按完整手机号，login / payment / 下单 / 取消 / 新人券按 userNo，三天均 100%")
else:
    sec("DR-021", "推送以外场景的分片键", "…", "—", "—", "—", "—", "林宏鹏", "待取数（本次受阻：查询未完成）", "本次未完成")
# ---------------- DR-022 ----------------
m22 = rd("dr022_per_minute_summary.csv")
sec_files = sorted(f for f in os.listdir(R) if f.startswith("dr022_seconds_") and f.endswith(".csv"))
secs = ""
if sec_files:
    rows = []
    for f in sec_files:
        q = rd(f); q = q[q.sms == 1]
        rj = q[q.final_result == "REJECT"]
        dd_ = f[len("dr022_seconds_"):-4]
        rows.append({"纽约日起点（午夜）": f"{dd_[:4]}-{dd_[4:6]}-{dd_[6:]} 00:00", "±2 分钟内 REJECT": int(rj.n.sum()),
                     "午夜前 5 秒内": int(rj[(rj.sec_from_ny_midnight >= -5) & (rj.sec_from_ny_midnight < 0)].n.sum()),
                     "午夜后 5 秒内": int(rj[(rj.sec_from_ny_midnight >= 0) & (rj.sec_from_ny_midnight < 5)].n.sum()),
                     "午夜前后 ±30 秒": int(rj[rj.sec_from_ny_midnight.abs() <= 30].n.sum())})
    secs = "  逐秒（短信口径，`results/dr022_seconds_*.csv`）：" + table(pd.DataFrame(rows))
bef = m22[m22.ny_minute < "2026-09-19 00:00"]; aft = m22[m22.ny_minute >= "2026-09-19 00:00"]
sec("DR-022", "巡检大盘与源库的午夜归日差异",
    "纽约日 09-18、09-19 两天，巡检大盘（Doris）与源库的短信 REJECT 各差 2 次、方向相反：这 2 次是不是落在纽约午夜前后、被 Doris `access_time` 与源库 `create_time` 归到了不同自然日？",
    "`sql/dr022_reject_per_minute.sql`（UTC `[2026-09-19 03:50, 04:10)`，按 `create_time`）" + ("、`sql/dr022_seconds_*.sql`（午夜 ±2 分钟逐秒）" if sec_files else ""),
    f"纽约 09-18 23:50…23:59 短信 REJECT {fi(bef.sms_REJECT.sum())} 次，09-19 00:00…00:09 {fi(aft.sms_REJECT.sum())} 次；逐分钟见 `results/dr022_per_minute_summary.csv`：" + table(m22[["ny_minute", "sms_PASS", "sms_REJECT"]]) + secs,
    ("源库一侧：" + "；".join(f"{r['纽约日起点（午夜）'][:10]} 午夜后 5 秒内 {r['午夜后 5 秒内']} 次、午夜前 5 秒内 {r['午夜前 5 秒内']} 次" for r in rows) + "。" if sec_files else "")
    + "两套时间戳只要相差几秒，贴着午夜的 REJECT 就会落到相邻的纽约日；09-18/09-19 交界处午夜后 5 秒内正好有 REJECT，量级与「各差 2 次、方向相反」一致。"
    "要确认必须用 Doris 的 `access_time` 统计同一窗口——Doris 不可达（DR-020），这一半做不了。",
    "中（源库一侧已量化；Doris 一侧缺失）", "—（数据平台开通 Doris 后补 `access_time` 一侧）", "部分答复（本次受阻：Doris 不可达，见 DR-020）",
    f"源库午夜前后 10 分钟 REJECT {fi(bef.sms_REJECT.sum())} / {fi(aft.sms_REJECT.sum())} 次；Doris 一侧待 DR-020")
# ---------------- DR-024 ----------------
e24 = rd("dr024_engine_vs_final.csv"); e24s = e24[e24.sms == 1]
cm = e24s.groupby(["engine_result", "final_result"]).n.sum().reset_index()
icon = e24s[e24s.engine_result == "REVIEW_18_ICON"]
ic = icon.groupby(["cid", "app_state", "version_class", "final_result"]).n.sum().reset_index()
app_rev = e24s[e24s.cid.astype(str).isin(["105", "106"]) & (e24s.engine_result.str.startswith("REVIEW") | e24s.final_result.str.startswith("REVIEW"))]
ar_ = app_rev.groupby(["ny_date", "cid", "version_class", "engine_result", "final_result"]).n.sum().reset_index()
d1617 = ar_[ar_.ny_date.isin(["2026-09-16", "2026-09-17"])]
sec("DR-024", "纽约日 × cid × 引擎结果 × 最终结果（2026-08-25～09-24）",
    "每个纽约日按 cid 分，引擎结果（`re.resultName`）与最终结果（`result`）的组合各多少次？09-16、09-17 有没有 cid 105/106 的 REVIEW？31 日里 REVIEW_18_ICON 的 65 次（返回 PASS 32、REVIEW 33）是不是都来自旧版 App？App 版本以 1.4.30 为界、按数值比较。",
    "`sql/dr024_engine_vs_final.sql`（`toolkit/tk09_engine_vs_final.sql` 同一写法；`min_version_num=1004030`）；汇总 `sql/local/p4_agg_drs.py`",
    f"短信口径，纽约日 2026-08-25…09-24。全量逐日表 `results/dr024_engine_vs_final.csv`（含 app 状态、版本组、去重手机号），31 日合计：" + table(cm) +
    "  REVIEW_18_ICON 按 cid × app × 版本组：" + table(ic) + f"  出现日期 {icon.ny_date.min()} … {icon.ny_date.max()}。"
    "  cid 105/106 的 REVIEW 类（引擎或最终），09-16、09-17：" + (table(d1617) if len(d1617) else "无") + "（全部日期见 `results/dr024_app_review_by_day.csv`）",
    f"REVIEW_18_ICON 共 {fi(icon.n.sum())} 次，全部版本 < 1.4.30（{fi(icon[icon.cid.astype(str).isin(['105', '106'])].n.sum())} 次来自 App 105/106，{fi(icon[~icon.cid.astype(str).isin(['105', '106'])].n.sum())} 次来自 H5 108），只出现在 {icon.ny_date.min()}…{icon.ny_date.max()}。"
    f"09-16、09-17 App（105/106）有 REVIEW 类引擎结果 {fi(d1617.n.sum())} 次，全部是 1.4.30 及以上版本，其中最终返回 REVIEW {fi(d1617[d1617.final_result.str.startswith('REVIEW')].n.sum())} 次——App 确实收到过 REVIEW；App 收到 REVIEW 后的表现（是否等于拦截）日志里看不到，要客户端确认。",
    "高（全量计数）", "林宏鹏（App 收到 REVIEW 的处理；改写条件，见 DR-016）", "已答复",
    f"REVIEW_18_ICON {fi(icon.n.sum())} 次全部 <1.4.30；09-16/17 App REVIEW 类 {fi(d1617.n.sum())} 次（≥1.4.30）")
# ---------------- DR-025 ----------------
hs = rd("dr025_hourly_summary.csv"); nd = rd("dr025_ny_daily_summary.csv")
def span(sid, lst, a, b):
    x = hs[(hs.strategy_id == sid) & (hs.list == lst) & (hs.utc_hour >= a) & (hs.utc_hour < b)]
    return int(x.pv.sum())
ax_before = span("strategy_AxAlIdejVA8m", "preonline", "2026-09-13 00:00", "2026-09-14 03:00")
nr_before = span("strategy_NrsClIxvGxWc", "preonline", "2026-09-13 00:00", "2026-09-14 03:00")
nr_first = hs[(hs.strategy_id == "strategy_NrsClIxvGxWc") & (hs.pv > 0)].utc_hour.min()
ax_first = hs[(hs.strategy_id == "strategy_AxAlIdejVA8m") & (hs.pv > 0)].utc_hour.min()
bt_b = span("strategy_bTCEWBZggaAP", "preonline", "2026-09-23 07:00", "2026-09-24 07:00"); bt_a = span("strategy_bTCEWBZggaAP", "preonline", "2026-09-24 08:00", "2026-09-25 08:00")
bt_b3 = span("strategy_bTCEWBZggaAP", "preonline", "2026-09-21 07:00", "2026-09-24 07:00"); bt_a2 = span("strategy_bTCEWBZggaAP", "preonline", "2026-09-24 08:00", "2026-09-26 08:00")
x43 = ""
if ex("dr025_hourly_hits_43na.csv"):
    q = rd("dr025_hourly_hits_43na.csv").groupby(["utc_hour", "list"]).pv.sum().unstack(fill_value=0)
    ch_t = "2026-09-23 14:00"
    b_on, a_on = int(q[q.index < ch_t].get("online", pd.Series([0])).sum()), int(q[q.index > ch_t].get("online", pd.Series([0])).sum())
    b_pre, a_pre = int(q[q.index < ch_t].get("preonline", pd.Series([0])).sum()), int(q[q.index > ch_t].get("preonline", pd.Series([0])).sum())
    x43 = (f"  补充 `strategy_43NaEzJmiQFk`（2026-09-23 14:43:34 UTC 由预上线改为上线，`results/dr025_hourly_hits_43na.csv`，UTC 09-22 00:00…09-27 00:00，09-26 为部分日）："
           f"改动所在小时之前 在线 {fi(b_on)} / 预上线 {fi(b_pre)}，之后 在线 {fi(a_on)} / 预上线 {fi(a_pre)}。")
sec("DR-025", "三条策略在配置改动前后的命中",
    "`strategy_bTCEWBZggaAP` 在 2026-09-24 07:22 UTC（`feature_dqBHKec09Wwa` 去掉条件）前后的命中；`strategy_AxAlIdejVA8m`、`strategy_NrsClIxvGxWc` 在 09-13～09-14 时间窗规则改写前有没有命中。在线与预上线分开。",
    "`sql/dr025_hourly_hits.sql`（UTC 2026-09-06 00:00…09-27 00:00，每条 ≤1 天；09-26 为部分日）、`sql/dr025_hourly_hits_43na.sql`；汇总 `sql/local/p4_agg_drs.py`",
    "全部 LKUS_push 行口径。按纽约日（`results/dr025_ny_daily_summary.csv`；首尾两天不完整）与按 UTC 小时（`results/dr025_hourly_summary.csv`）。"
    f"`AxAlIdejVA8m`：改写（09-14 03:12:50 UTC）之前的预上线命中 {fi(ax_before)} 次（UTC 09-13 00:00…09-14 03:00），在线 0。"
    f"`NrsClIxvGxWc`：改写（09-14 03:12:40 UTC）之前 {fi(nr_before)} 次；第一次命中在 {nr_first} UTC（即 `feature_e1Kmz7JqzsWc` 修好之后，DR-003）。"
    f"`bTCEWBZggaAP`：改动前 24 小时（09-23 07:00…09-24 07:00 UTC）预上线命中 {fi(bt_b)} 次、改动后 24 小时（09-24 08:00…09-25 08:00）{fi(bt_a)} 次；改动前 72 小时 {fi(bt_b3)} 次、改动后 48 小时 {fi(bt_a2)} 次；在线 0。" + x43,
    (f"AxAl 改写前 {'没有' if ax_before == 0 else '有'}命中（{fi(ax_before)} 次），第一次命中在 {ax_first} UTC，即改写之后的第一个小时。"
     + ("改写前的条件是「时间大于 22:00 且小于 05:00」，同一天里两者不可能同时成立，所以这条策略改写前不可能命中；改写成 02:00–09:00 后才开始命中（推断，依据是规则文本与命中时间）。" if ax_before == 0 else "")
     + f"NrsCl 改写前 {fi(nr_before)} 次；它第一次命中在 {nr_first} UTC，在它引用的 `feature_e1Kmz7JqzsWc` 修好（09-24 07:24 UTC）之后的第一个 02:00–09:00 窗口——它此前 0 命中是因为特征取不到值，不只是时间窗。"
     "bTCE 在条件去掉前后没有明显跳变：该特征改成无条件后计数只会变大，但策略另外要求 token 缺失或为空且版本 ≥1.4.30，这两条限制了命中。"),
    "高（逐小时全量计数）；「不可能成立」为推断", "田志鲔（AxAl 原时间窗的本意）", "已答复",
    f"AxAl 改写前 {fi(ax_before)} 次（原时间窗不可能成立）；NrsCl 至特征修好后才命中；bTCE 前后无明显跳变")
# ---------------- DR-026 ----------------
if ex("dr026_match_summary.csv"):
    ms = rd("dr026_match_summary.csv"); cp = rd("dr026_captcha_profile.csv")
    tb = rd("dr026_time_diff_buckets.csv") if ex("dr026_time_diff_buckets.csv") else pd.DataFrame()
    st26 = rd("dr026_time_diff_stats.csv") if ex("dr026_time_diff_stats.csv") else pd.DataFrame()
    ph = ms.iloc[0]
    sec("DR-026", "LKUS_captcha 日志与短信最终 REVIEW 是否对应",
        "纽约日 2026-09-24 `LKUS_captcha` 场景日志与同日短信最终 REVIEW 是否一一对应（同一请求链路、时间先后）？",
        "`sql/dr026_captcha_extract.sql`（行级、加盐哈希、只存本机）+ E1；本地比对 `sql/local/p4_new_drs.py`",
        f"LKUS_captcha 当日 {fi(ph.captcha_rows_day)} 行；短信最终 REVIEW {fi(ph.sms_final_review_rows)} 次。按匹配键（加盐哈希只在本机比对，包里不含任何标识）：" + table(ms) +
        ("  按手机号匹配时，每个 REVIEW 取时间最近的一条 captcha（captcha 时间 − REVIEW 时间）：" + table(tb.drop(columns=["note"])) if len(tb) else "")
        + ("  时间差分位数（秒）：" + "、".join(f"{r.stat} {r.seconds}" for r in st26.itertuples()) if len(st26) else "") + "  captcha 行画像（`results/dr026_captcha_profile.csv`）：" + table(cp),
        f"见上：按手机号能对上的 REVIEW {fi(ph.review_rows_with_any_captcha_same_key_same_day)} / {fi(ph.sms_final_review_rows)}，能对上 REVIEW 的 captcha 行 {fi(ph.captcha_rows_matching_a_review)} / {fi(ph.captcha_rows_day)}。时间先后见分布。",
        "中（行数小；只凭哈希与时间关联）", "林宏鹏（captcha 场景的调用时机）", "已答复",
        f"按手机号对上 {fi(ph.review_rows_with_any_captcha_same_key_same_day)}/{fi(ph.sms_final_review_rows)} 个 REVIEW；captcha {fi(ph.captcha_rows_matching_a_review)}/{fi(ph.captcha_rows_day)} 行")
else:
    sec("DR-026", "LKUS_captcha 日志与短信最终 REVIEW 是否对应", "…", "—", "—", "—", "—", "林宏鹏", "待取数（本次受阻：抽取未完成）", "本次未完成")
# @@NEW@@
# ---------------- write ----------------
ORDER = sorted(S, key=lambda d: int(d.split("-")[1]))
head = ["# 04 数据问题结论（DR）", "",
        "> 2026-09-26 实测。DR 清单：用户在运行中提供的 `DATA_REQUESTS.md`（2026-09-26 版）——状态为「待取数」「部分答复」的逐条处理，外加常设项（DR-003、010、013、014、015，以及 P3 常设 DR-016、017、018）。"
        "DR-001、DR-019 的状态是「待确认」，本轮不做数据工作，沿用原答复。",
        "> 每条给出 SQL（`sql/`）、本地脚本（`sql/local/`）与结果文件（`results/`）。数字全部来自本次会话执行的查询。时间：`create_time` 为 UTC；「纽约日」= America/New_York 自然日。",
        "> 口径：**短信** = LKUS_push 中 `$.para.email` 为空或不存在；**全部** = 全部 LKUS_push 行。**E1** = 本包的行级抽取（纽约日 2026-09-18 暖机 + 09-19…09-25），只含标量与加盐哈希，只存本机。", "",
        "| DR | 新状态 | 一句话 |", "|---|---|---|"]
head += [f"| [{d}](#{d.lower()}) | {S[d][0]} | {S[d][1]} |" for d in ORDER]
head += ["", "---", ""]
open(os.path.join(PKG, "04_数据问题结论.md"), "w", encoding="utf-8").write("\n".join(head + B) + "\n")
print("04 written:", len(S), "DRs")
