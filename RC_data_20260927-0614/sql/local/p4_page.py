#!/usr/bin/env python3
"""P4: write 04_数据问题结论.md — one section per DR worked on in this run (anchor <a id="dr-xxx"></a>), fixed fields.
Every number is read from results/ of this run; canonical sentences come from metrics.T. The per-DR「新状态」lines are
the single source for the README totals (sql/local/p6_readme.py parses them)."""
import os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from metrics import T  # noqa: E402

PKG = os.path.dirname(os.path.dirname(HERE))
R = os.path.join(PKG, "results")
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
fi = lambda v: f"{int(v):,}"
pct = lambda x: f"{100 * x:.1f}%"
esc = lambda v: "" if pd.isna(v) else str(v).replace("|", "\\|")
S, B = {}, []


def sec(dr, title, q, sql, res, concl, conf, who, status, line):
    S[dr] = (status, line)
    B.extend([f'<a id="{dr.lower()}"></a>', "", f"## {dr} {title}", "", f"- **问题**：{q}", f"- **SQL**：{sql}", f"- **结果**：{res}",
              f"- **结论**：{concl}", f"- **置信度**：{conf}", f"- **谁确认**：{who}", f"- **新状态**：{status}", "", "---", ""])


def table(df):
    return ("\n\n  | " + " | ".join(map(str, df.columns)) + " |\n  |" + "---|" * len(df.columns) + "\n" + "\n".join(
        "  | " + " | ".join(esc(f"{v:,}" if isinstance(v, int) else v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n\n")


k1 = rd("p1_chk_consistency.csv"); n7 = int(k1.n.sum()); win = sorted(k1.ny_date.unique()); W7 = f"纽约日 {win[0]}…{win[-1]}"
dr3 = rd("p3_daily_result.csv")
# ================= DR-002 (short: Doris dependency) =================
em_day = k1.groupby("ny_date").apply(lambda g: pd.Series({"rows": int(g.n.sum()), "email_nonempty": int(g[g.email_nonempty == 1].n.sum())}), include_groups=False).reset_index()
em = int(em_day.email_nonempty.sum())
sec("DR-002", "推送场景怎么区分短信和邮件",
    "Doris 里 `l2_scene='1001'` 是否就是短信、`'1002'` 是否就是邮件？源库没有这一列，用什么规则区分？（`DATA_REQUESTS.md`：部分答复，剩 Doris 一侧）",
    "`sql/p1_chk_consistency.sql`（源库一侧的例行复核）",
    f"源库一侧（{W7}，全部 LKUS_push {fi(n7)} 行）：全部带非空 `phoneNo`，`$.para.email` 非空 {em} 行，其余按短信计；每行恰好落在一类。逐日 email 行数："
    + "、".join(f"{r.ny_date} {r.email_nonempty}/{fi(r.rows)}" for r in em_day.itertuples()) + "（`results/p1_chk_consistency.csv`）。",
    f"源库规则不变。Doris 一侧（`l2_scene='1002'` 的直接对照）没有做：{T['doris_dep']}。",
    "中（源库规则稳定；缺数仓对照）", "林宏鹏（`l2_scene` 的生成规则）；数据平台（Doris 只读账号，DR-020）",
    f"部分答复（{T['doris_dep']}）", f"源库规则不变（7 日 email 非空 {em} 行）；Doris 一侧等 DR-020")
# ================= DR-003 (standing, from E1) =================
cc = rd("p3_counter_codes_daily.csv")
cond = rd("p3_param_lists.csv").set_index("list").loc["cond_or_combo_counter_ids"].ids.split()
c3 = cc[cc.feature_id.isin(cond)]
piv = c3.pivot_table(index=["feature_id", "code"], columns="ny_date", values="rows", aggfunc="sum", fill_value=0).reset_index()
combo = c3[c3.feature_id.isin(["feature_AemrK847uPtt", "feature_bvE9FL19wqag"])]
combo_ok = int(combo[combo.code == "SUCCESS"].rows.sum()); combo_all = int(combo.rows.sum())
e1k = c3[c3.feature_id == "feature_e1Kmz7JqzsWc"]; e1k_pe = int(e1k[e1k.code == "COUNTER_FEATURE_PARAMS_ERROR"].rows.sum())
e1k_pe_days = e1k[(e1k.code == "COUNTER_FEATURE_PARAMS_ERROR") & (e1k.rows > 0)].ny_date
e1k_last_pe_day = e1k_pe_days.max() if len(e1k_pe_days) else "—"
tl = rd("p2_oplog_timeline.csv")
sx = rd("config_strategy_expanded.csv", dtype=str)
e1k_last_pe_n = int(e1k[(e1k.code == "COUNTER_FEATURE_PARAMS_ERROR") & (e1k.ny_date == e1k_last_pe_day)].rows.sum()) if len(e1k_pe_days) else 0
e1k_fx = tl[(tl.object_id == "feature_e1Kmz7JqzsWc") & (tl.field == "input_conditions")].operation_time_utc
e1k_fix = e1k_fx.iloc[-1] if len(e1k_fx) else "—"
w7_utc = f"{win[0]} 04:00:00"                                          # NY midnight (EDT) of the first 7-day window day
chg3 = tl[tl.object_id.isin(cond) & tl.field.isin(["input_conditions", "input_hasCondition", "input_dimension"]) & (tl.operation_time_utc >= w7_utc)]
pre3 = tl[tl.object_id.isin(["feature_AemrK847uPtt", "feature_bvE9FL19wqag"]) & (tl.field == "input_dimension") & (tl.operation_time_utc < w7_utc)].tail(2)
sec("DR-003", "带条件 / 组合维度累计特征的返回码（常设）",
    "每个带过滤条件或组合维度的累计特征，每天返回 `SUCCESS` / `CONDITION_MISS` / `PARAMS_ERROR` / `DIMENSION_EMPTY` 各多少？组合维度特征是否恢复 SUCCESS？",
    "E1 抽取 `sql/e1_a.sql`、`sql/e1_b.sql` → `sql/local/p3_profile.py`（特征列表 `sql/local/p3_params.py`：非空条件或组合维度，加操作日志里带过条件的）",
    f"短信口径，纽约日 {cc.ny_date.min()}…{cc.ny_date.max()}（7 日），逐日特征评估次数（`results/p3_counter_codes_daily.csv`）：" + table(piv)
    + "  窗口内这些特征的条件 / 维度变化（只列 input_conditions / input_hasCondition / input_dimension 三个字段，全部字段见 `results/p2_oplog_timeline.csv`）：" + ("；".join(f"{r.operation_time_utc} UTC `{r.object_id}` {r.field}" for r in chg3.itertuples()) or "无") + "。"
    + ("组合维度两个特征的维度改动在窗口开始之前（" + "、".join(f"`{r.object_id}` {r.operation_time_utc} UTC" for r in pre3.itertuples()) + "），本窗口 7 天都在改动之后。" if len(pre3) else "")
    + "".join(f"`{f_}` 不在表中：引用它的策略只在 {'、'.join(sorted(set(sx[sx.feature_id == f_].scene_id)))}（status {'/'.join(sorted(set(sx[sx.feature_id == f_].status.astype(str))))}），LKUS_push 请求不计算它（`results/config_strategy_expanded.csv`）。"
              for f_ in sorted(set(chg3.object_id) - set(cc.feature_id)) if (sx[sx.feature_id == f_].scene_id != "LKUS_push").all() and len(sx[sx.feature_id == f_])),
    f"组合维度两个特征本窗口 SUCCESS {fi(combo_ok)} / {fi(combo_all)} 次——{'仍未修好（全部 `DIMENSION_EMPTY`），不重估 `strategy_tO7DZkJ1g0C2`' if combo_ok == 0 else '已恢复部分 SUCCESS，需用 tk02/tk03 重估 `strategy_tO7DZkJ1g0C2`'}；"
    f"`feature_e1Kmz7JqzsWc` 本窗口 PARAMS_ERROR {fi(e1k_pe)} 次；按纽约日，最后出现在 {e1k_last_pe_day}（当日 {fi(e1k_last_pe_n)} 次），此后每天为 0。"
    f"操作日志同一天 {e1k_fix} UTC 有该特征的条件修改；本包只有逐日计数，没有按小时核对两者先后。",
    "高（逐日全量计数）", "贡锁泉、林宏鹏（组合维度写法）", "已答复",
    f"组合维度 SUCCESS {fi(combo_ok)}/{fi(combo_all)}（{'仍坏' if combo_ok == 0 else '部分恢复'}）；e1K PARAMS_ERROR 只到 {e1k_last_pe_day}")
# ================= DR-010 (standing) =================
ar = rd("dr010_attack_rule.csv"); ps = rd("dr010_period_summary.csv"); ds = rd("dr010_daily_series.csv")
k5 = ar[ar.k == 5].iloc[0]; k3 = ar[ar.k == 3].iloc[0]; last = ds.iloc[-1]
tm_ = rd("timing.csv"); n_half = int(((tm_.name == "p4_daily_series") & (tm_.batch < 8)).sum())
sec("DR-010", "美国号码短信日基线与攻击日（常设）",
    "刷新 +1 短信放行基线与攻击日：固定基线 = 序列前 28 天（序列从 2026-06-01 开始），指标 = 每日非 +1/+86 短信请求量，攻击日 = 中位数 + k × MAD（MAD×1.4826），迭代剔除；k=5 默认、k=3 敏感性。",
    f"`sql/p4_daily_series.sql`（纽约日 2026-06-01…{ds.ny_date.max()}，每条 8 分片起步，{n_half} 条单条超过 3 s 后自动减半为 4）；计算 `sql/local/p4_agg_drs.py`",
    f"短信口径（纽约日逐日序列 `results/dr010_daily_series.csv`）。基线 {k5.baseline}：中位数 {k5.baseline_median}、MAD×1.4826 = {k5.baseline_mad_scaled}。k=5 阈值 {k5.threshold}，首个攻击日 {k5.first_flagged_day}，共 {int(k5.flagged_days)} 天；"
    f"k=3 阈值 {k3.threshold}，首个攻击日 {k3.first_flagged_day}，共 {int(k3.flagged_days)} 天（`results/dr010_attack_rule.csv`）。按月 × 是否攻击日（k=5）的日均（`results/dr010_period_summary.csv`）：" + table(ps)
    + f"  最后一天 {last.ny_date}（短信口径）：非 +1/+86 请求 {fi(last.non_plus1_plus86_requests)}，+1 放行 {fi(last.plus1_pass)}（`results/dr010_daily_series.csv`）。",
    f"最后一天{'仍高于' if last.attack_flag_k5 == 1 else '已低于'} k=5 阈值；已知攻击起点只用于检验，规则给出的首个攻击日为 {k5.first_flagged_day}。",
    "高（全量逐日计数）", "Huanxian Zhou（基线口径）", "已答复",
    f"k=5：{k5.first_flagged_day} 起 {int(k5.flagged_days)} 个攻击日；{last.ny_date} {'仍在攻击日' if last.attack_flag_k5 == 1 else '已不是攻击日'}")
# ================= DR-013 (standing) =================
inv = rd("p0_mcp_inventory.csv") if ex("p0_mcp_inventory.csv") else None
inv_txt = ("；".join(f"{r.mcp_server} {r.item}：{r.value}" for r in inv.itertuples()) + "（`results/p0_mcp_inventory.csv`）") if inv is not None else "—"
sec("DR-013", "MCP 能连到哪些库，Doris 可不可达（常设）", "本环境能否读到 Doris `ods_luckyus_iriskcontrol`？",
    "`sql/p0_*.sql`、`sql/p1_fleet_sweep_mysql.sql`；Grafana 数据源元数据与面板 SQL（MCP server `grafana-lucky`）",
    inv_txt + "；`grafana-lucky` 有数据源 `Doris-iriskcontrol` 但没有执行 SQL 的工具（`00_环境清单.md` §2）。",
    "Doris 仍不可达。", "高（服务器清单与工具列表直接读取）", "数据平台（DR-020）", "已答复", "Doris 仍不可达")
# ================= DR-014 (standing) =================
b14 = rd("dr014_best_candidate.csv"); lk14 = b14[b14.scene_id.str.startswith("LKUS")]
sk = rd("p1_sk_concat_check_20260926.csv"); sp = rd("p3_dr014_shard_spread.csv")
t14 = lk14[["scene_id", "scene_group", "best_candidates", "best_share", "rows"]].copy(); t14["best_share"] = t14.best_share.map(pct)
sec("DR-014", "分片键抽查（常设，按场景组）",
    "分片键是否仍成立：push / register / captcha = 完整手机号，login / payment / 下单 / 取消 / 新人券 = `userNo`？",
    "`sql/p1_sk_concat_check_20260926.sql`、`sql/dr014_sharding_key_by_scene_20260926.sql`（DR-021 的写法，只做二进制相等计数）；汇总 `sql/local/p4_agg_drs.py`",
    f"纽约日 2026-09-26，各场景相等占比最高的候选（`results/dr014_best_candidate.csv`）：" + table(t14)
    + f"  LKUS_push：{fi(sk.n.sum())} 行中 `sharding_key = CONCAT(country_code, phone)` {fi(sk.n_sk_eq_cc_col_plus_phone_col.sum())} 行（`results/p1_sk_concat_check_20260926.csv`）；"
    f"E1（全部 LKUS_push 行，纽约日 {rd('p3_daily_result.csv').ny_date.min()}…{rd('p3_daily_result.csv').ny_date.max()}）{fi(sp.iloc[0].distinct)} 个手机号跨分片 {int(sp.iloc[0].in_more_than_one_shard)} 个，uid {fi(sp.iloc[1].distinct)} 个中 {fi(sp.iloc[1].in_more_than_one_shard)} 个跨分片（`results/p3_dr014_shard_spread.csv`）。",
    "按场景组仍成立。当天没有数据的场景未核。", f"高（二进制相等计数；{len(t14)} 个场景的最佳候选相等占比 {'均为 100%' if (lk14.best_share == 1).all() else '见表'}）", "林宏鹏", "已答复",
    "按场景组仍成立（手机号组 / userNo 组，2026-09-26）；uid 跨分片")
# ================= DR-015 (standing) =================
cfg_n = {f[7:-4]: (len(pd.read_csv(os.path.join(R, f))) if os.path.getsize(os.path.join(R, f)) > 5 else 0) for f in os.listdir(R) if f.startswith("config_") and f.endswith(".csv")}
bys = rd("p2_list_counts_by_scene.csv"); lkb = bys[bys.access_id == "LKUS"]
nz = lkb[lkb.n_entries > 0].drop_duplicates(["feature_name", "list_table"])
sec("DR-015", "配置与变更日志导出（常设）", "每轮导出线上配置与操作日志；名单按类型 × 场景 × 来源计数。",
    "`sql/config_*.sql`、`sql/p2_list_counts.sql`、`sql/p2_oplog_*.sql`；`sql/local/p2_list_by_scene.py`",
    f"17 张定义表整表导出（策略 {cfg_n.get('strategy', 0)}、规则 {cfg_n.get('rule', 0)}、第三方/累计特征 {cfg_n.get('third_feature', 0)}、参数 {cfg_n.get('para', 0)}…）；{T['oplog']}。"
    "名单按场景（`results/p2_list_counts_by_scene.csv`）：LKUS 有条目的只有 " + "；".join(f"{r.feature_name} {fi(r.n_entries)} 条" for r in nz.itertuples()) + "。",
    "已导出；与 2026-09-24 快照、与上一包的差异由桌面 D1 计算。", "高（整表导出，行数见 `02`）", "—", "已答复", "17 张定义表 + 名单按类型 × 场景 × 来源 + 操作日志时间线已导出")
# ================= DR-016 / 017 / 018 (standing, 待确认) =================
d16 = rd("dr016_summary_7d.csv").iloc[0]
sec("DR-016", "引擎 REVIEW 类结果被改写为最终 PASS（常设计数）", "引擎判 REVIEW 却返回 PASS、引擎无结果却返回 PASS 的次数。",
    "E1 → `sql/local/p4_new_drs.py`",
    f"{W7}，短信口径：引擎 REVIEW {fi(d16.engine_review_total)} 次，最终 PASS {fi(d16.engine_review_final_pass)}（其中 cid 108 {fi(d16.engine_review_final_pass_cid108)}、reviewRepeat=true {fi(d16.engine_review_final_pass_review_repeat_true)}）、最终 REVIEW {fi(d16.engine_review_final_review)}；引擎结果为空 {fi(d16.engine_empty_rows)} 次（`results/dr016_summary_7d.csv`）。",
    "改写仍在发生；数据侧已做完，改写条件需要平台说明。", "高（计数）", "林宏鹏", "待确认（问人：林宏鹏）",
    f"7 日引擎 REVIEW {fi(d16.engine_review_total)} 次中 {fi(d16.engine_review_final_pass)} 次返回 PASS")
d17 = rd("dr017_reject_above_whitelist.csv"); on17 = d17[d17.status == 1]
sec("DR-017", "优先级高于白名单的策略（常设）", "`strategy_sw3jC7bvFYEX` 等优先级高于白名单 PASS 的非 PASS 策略的当前优先级、状态与命中。",
    "配置 + `sql/p2_hits_7d.sql` → `sql/local/p4_new_drs.py`",
    f"全部 LKUS 场景 {len(d17)} 条，其中上线 {len(on17)} 条：" + "；".join(f"`{r.strategy_id}`（{r.scene_id}，{r.result_code}，优先级 {r.exec_priority}，7 日在线命中 {fi(r.hits_online_pv_7d_all_push_rows)}）" for r in on17.itertuples())
    + "（`results/dr017_reject_above_whitelist.csv`，全部 LKUS_push 行）。",
    "仍有 REJECT 策略排在白名单之前；是否有意需要策略负责人确认。", "高（配置事实）", "段枝宏、田志鲔", "待确认（问人：段枝宏、田志鲔）",
    "；".join(f"`{r.strategy_id}` 优先级 {r.exec_priority}、7 日 {fi(r.hits_online_pv_7d_all_push_rows)} 次" for r in on17.itertuples()) or "无上线策略")
d18 = rd("dr018_time_rule_strategies.csv")
sec("DR-018", "UTC 时刻规则遇夏令时（常设）", "使用 UTC 时刻规则的上线 / 预上线策略及其命中；2026-11-01 夏令时结束后对应的纽约时间偏 1 小时。",
    "配置 + `sql/p2_hits_7d.sql` → `sql/local/p4_new_drs.py`",
    table(d18[["strategy_id", "status", "result_code", "time_conditions_utc", "hits_online_pv_7d_all_push_rows", "hits_preonline_pv_7d_all_push_rows", "update_time"]]) + f"  （{W7}，全部 LKUS_push 行，`results/dr018_time_rule_strategies.csv`）",
    "UTC 02:00–09:00 目前对应纽约 22:00–05:00，11-01 之后对应 21:00–04:00。是否改写要策略负责人决定。", "高（配置事实）", "田志鲔", "待确认（问人：田志鲔）",
    f"{len(d18)} 条策略用 UTC 时刻规则（上线 {int((d18.status == 1).sum())}、预上线 {int((d18.status == 2).sum())}）")
# ================= DR-022 (short: Doris dependency) =================
sec("DR-022", "巡检大盘与源库的午夜归日差异", "纽约日 09-18、09-19 两天，大盘（Doris）与源库的短信 REJECT 各差 2 次：是否因 `access_time` 与 `create_time` 归到了不同自然日？（部分答复，剩 Doris 一侧）",
    "—（源库一侧已在 2026-09-26 包完成，本轮不重跑）", "本轮没有新查询。",
    f"Doris `access_time` 一侧没有做：{T['doris_dep']}。", "—", "数据平台（DR-020）",
    f"部分答复（{T['doris_dep']}）", "源库一侧已答（上一包）；Doris 一侧等 DR-020")
# ================= DR-027 =================
dd = rd("dr027_daily_decomposition.csv"); cx = rd("dr027_crosscheck.csv"); cells = rd("dr027_e1_cells.csv")
sm = rd("dr027_summary.csv").set_index("metric").value; sens = rd("dr027_baseline_sensitivity.csv")
sdrop = sm["drop"]
st27 = "strategy_43NaEzJmiQFk"
sw = tl[(tl.object_id == st27) & (tl.field == "status") & (tl.after.astype(str) == "1")].operation_time_utc.iloc[-1]
t_new = tl[(tl.object_id == st27) & (tl.field == "(object)")].operation_time_utc
t_pre = tl[(tl.object_id == st27) & (tl.field == "status") & (tl.after.astype(str) == "2")].operation_time_utc
days = dd.ny_date.tolist(); sw_day = (pd.Timestamp(sw) - pd.Timedelta(hours=4)).strftime("%Y-%m-%d")
before = dd[dd.ny_date < sw_day]; after = dd[dd.ny_date > sw_day]
pr = rd("dr027_period_rates.csv").set_index("period")
P_PRE, P_ON = pr.loc["pre-online (would-be unique REJECT)"], pr.loc["online (actual unique REJECT)"]
P1 = pr.loc["pre-online, part 1 (before NY midnight)"] if "pre-online, part 1 (before NY midnight)" in pr.index else None
P2 = pr.loc["pre-online, part 2 (NY 09-23 morning)"] if "pre-online, part 2 (NY 09-23 morning)" in pr.index else None
tdd = dd[["ny_date", "phase_on_day", "requests_+1", "pass_+1", "requests_+86", "pass_+86", "requests_other", "pass_other", "pass_non_plus1",
          "s_preonline_no_online_reject_non_plus1", "s_preonline_no_online_reject_non_plus1_final_pass",
          "s_online_only_reject_non_plus1", "s_online_only_reject_non_plus1_would_be_pass",
          "s_online_only_reject_non_plus1_would_be_pass_distinct_phones", "pass_non_plus1_if_strategy_absent"]].copy()
tdd.columns = ["纽约日", "当日阶段", "+1 请求", "+1 放行", "+86 请求", "+86 放行", "其它区号请求", "其它区号放行", "非 +1 放行",
               "43Na 预上线唯一拒（切换前）", "其中实际放行", "43Na 在线唯一拒（切换后）", "其中无其它 REVIEW 命中", "其去重手机号",
               "若无 43Na 的非 +1 放行（推算，请求量与其它判定不变时的上限）"]
aft_sw = int(dd.s_preonline_no_online_reject_non_plus1_after_switch.sum())
u_cc = cells.groupby("cc_group")[["s_online_only_reject", "s_preonline_no_online_reject"]].sum().sum(axis=1)
w0_utc = (pd.Timestamp(days[0]) + pd.Timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
oncfg = tl[(tl.operation_time_utc >= w0_utc) & tl.field.isin(["status", "execPriority", "strategyName", "strategyExpress"]) & tl.object_kind.eq("strategyId")]
st_now = rd("config_strategy.csv", dtype=str).set_index("strategy_id").status
FLD = {"status": "状态", "execPriority": "优先级", "strategyName": "名称", "strategyExpress": "规则组合"}


def chg(r):
    return f"{FLD[r.field]} `{esc(r.before)}` → `{esc(r.after)}`"


# strategies whose name changed: features they use whose dimension changed in the window (the real logic change)
dimchg = tl[(tl.operation_time_utc >= w0_utc) & (tl.field == "input_dimension")]
notes = []
for sid in sorted(set(oncfg[oncfg.field == "strategyName"].object_id)):
    fs = set(sx[sx.strategy_id == sid].feature_id)
    dc = dimchg[dimchg.object_id.isin(fs)]
    if len(dc):
        notes.append(f"`{sid}` 名称变化前，它引用的 " + "、".join(f"`{r.object_id}` 于 {r.operation_time_utc} UTC 维度 {esc(r.before)} → {esc(r.after)}" for r in dc.itertuples())
                     + f"；该策略当前 status {st_now.get(sid, '—')}" + ("（预上线，不影响最终结果）" if st_now.get(sid) == "2" else ""))
# the +86 exclusion added to strategy_rDf6oPcZ8ydk: +86 SMS REJECT by NY day (E1)
p86 = cells[(cells.cc_group == "+86") & (cells.sms == 1)].groupby(["ny_date", "final_result"]).requests.sum().unstack(fill_value=0)
r86 = p86.get("REJECT", pd.Series(0, index=p86.index)); q86 = cells[(cells.cc_group == "+86") & (cells.sms == 1)].groupby("ny_date").requests.sum()
rdf = oncfg[(oncfg.object_id == "strategy_rDf6oPcZ8ydk")]
g29 = rd("dr027_strategy_day_cid_geo.csv", dtype={"cid": str})
g29 = g29[(g29.strategy_id == "strategy_29nE1qd56otz") & (g29.list == "online") & (g29.geo_mismatch == 1)].groupby("ny_date").hit_pv.sum()
sb = sens[sens.before_days.str.contains(r"\.\.")]; s1 = sens[~sens.before_days.str.contains(r"\.\.")]
rng = lambda d_: f"{100 * d_.unique_share_of_drop.min():.0f}%–{100 * d_.unique_share_of_drop.max():.0f}%"
ph = dd[dd.ny_date > sw_day].s_online_only_reject_non_plus1_would_be_pass_distinct_phones
sec("DR-027", "09-24、09-25 非 +1 放行下降的原因",
    "非 +1 号码的短信 PASS 在纽约日 09-24、09-25 明显下降：是 `strategy_43NaEzJmiQFk` 在 2026-09-23 14:43 UTC 转上线后拦下的，还是攻击量本身下降？",
    "`toolkit/tk10_unique_reject.sql` → `sql/dr027_tk10_43na.sql`（纯 SQL）；`toolkit/tk08_strategy_cid_geo.sql` → `sql/dr027_tk08_43na_*.sql`；E1 本地复算 `sql/local/dr027_local.py`",
    f"**本条自己的窗口：纽约日 {days[0]}…{days[-1]}**（与 P3 的 7 日窗口不同），短信口径，只出计数。43Na 的时间取操作日志：{t_new.iloc[0] if len(t_new) else '—'} UTC 新建（status 0），"
    f"{t_pre.iloc[0] if len(t_pre) else '—'} UTC 转预上线，{sw} UTC 转上线（纽约日 {sw_day} 为混合日）；此前没有它的命中。"
    "「43Na 唯一拒」= 43Na 命中、且没有其它在线 REJECT 类策略命中（切换前按预上线命中，切换后按在线命中；REJECT 类返回码名取自 `results/config_resultcode.csv`）。"
    "纯 SQL 与 E1 逐格核对（`results/dr027_crosscheck.csv`）：" + "；".join(f"{r.check}：{r.cells} 格，不一致 {r.mismatching_cells}" for r in cx.itertuples())
    + "（「无其它 REVIEW 命中」的过滤、去重手机号与下面的精确时段数字只来自 E1）。逐日（`results/dr027_daily_decomposition.csv`）：" + table(tdd)
    + f"  43Na 唯一拒只出现在「其它区号」组：+1 组 {fi(u_cc.get('+1', 0))} 次、+86 组 {fi(u_cc.get('+86', 0))} 次（`results/dr027_e1_cells.csv`）。"
    f"切换后仍按预上线记录的唯一拒另有 {aft_sw} 次（纽约日 {sw_day}），不计入「切换前」列。「若无 43Na」= 实际放行 + 「其中无其它 REVIEW 命中」，按请求次数计：被拒号码的重试（改后每天 {fi(ph.min())}–{fi(ph.max())} 个号码）使它偏高；若请求减少是攻击方对 43Na 的反应（见结论 ④），没有 43Na 时请求会更多，它又会偏低；只在请求量与其它策略判定不变时是上限。"
    + "\n\n  窗口内上线 / 预上线策略的状态、优先级、名称变化（操作日志）：" + ("；".join(f"{r.operation_time_utc} UTC `{r.object_id}` {chg(r)}" for r in oncfg.itertuples()) or "无") + "。"
    + ("".join(f"{n_}。" for n_ in notes))
    + (f"`strategy_rDf6oPcZ8ydk` 的规则组合改动（{rdf.operation_time_utc.min()} UTC）加上了「区号不是86 / 区号不是+86」两条规则（见其名称变化）；+86 短信被拒（所有策略合计）逐日 " + "、".join(f"{d_[5:]} {int(r86.get(d_, 0))}" for d_ in days)
       + f"，+86 短信请求每天 {int(q86.min())}–{int(q86.max())} 次（`results/dr027_e1_cells.csv`）。" if len(rdf) else "")
    + ("`strategy_29nE1qd56otz`（在线）号码国家 ≠ IP 国家的命中逐日 " + "、".join(f"{d_[5:]} {int(g29.get(d_, 0))}" for d_ in days) + "（`results/dr027_strategy_day_cid_geo.csv`）。" if len(g29) else "")
    + "逐策略逐日命中（全部策略 × 纽约日 × cid × 国家是否一致）：`results/dr027_strategy_day_cid_geo.csv`；43Na 的 tk08 结果：`results/dr027_tk08_43na_hitStrategy.csv`、`results/dr027_tk08_43na_hitPreOnlineStrategy.csv`。",
    f"下面是计数分解，不是因果证明（`results/dr027_summary.csv`）。① 改前 {len(before)} 天（{before.ny_date.min()}…{before.ny_date.max()}）非 +1 放行日均 {sm.pass_non_plus1_before_mean:,.0f}，"
    f"改后 {len(after)} 天（{after.ny_date.min()}…{after.ny_date.max()}）日均 {sm.pass_non_plus1_after_mean:,.0f}，下降 {sdrop:,.0f}。"
    f"② 改后 43Na 每天唯一拦下、且没有其它 REVIEW 命中的非 +1 请求日均 {sm.unique_block_would_be_pass_mean_after:,.0f} 次；若没有 43Na，按其它命中这些请求会放行，改后日均放行会是 {sm.pass_if_strategy_absent_mean_after:,.0f}"
    f"（推算：假设请求量与其它策略判定不变）。按这组天数，它相当于下降的约 {100 * sm.unique_share_of_drop:.0f}%；所试 {len(sens)} 组天数组合（改前取 {'、'.join(sorted(set(sens.before_days)))}；改后取 {'、'.join(sorted(set(sens.after_days)))}）下为 {rng(sens)}：多日改前基线 {rng(sb)}，只用 {'、'.join(sorted(set(s1.before_days)))} 一天时 {rng(s1)}（`results/dr027_baseline_sensitivity.csv`）。"
    f"③ 其余约 {100 * sm.residual_share_of_drop:.0f}%（日均 {sm.residual:,.0f}）不是单一因素：按改前放行率 {100 * sm.pass_rate_before:.1f}%，非 +1 请求从日均 {sm.requests_non_plus1_before_mean:,.0f} 降到 {sm.requests_non_plus1_after_mean:,.0f} 对应约 {sm.volume_effect_at_before_pass_rate:,.0f}/日（减少的请求几乎都是 43Na 条件成立的请求，见 ④）；"
    f"改后非 +1 请求若把 43Na 唯一拦下的算作放行，放行率为 {100 * sm.pass_rate_after_if_strategy_absent:.1f}%（{sm.pass_if_strategy_absent_mean_after:,.0f} / {sm.requests_non_plus1_after_mean:,.0f}），高于改前，抵消约 {-sm.rate_effect_remaining_traffic:,.0f}/日（其它在线 REJECT 类命中在非 +1 请求中的占比 {100 * sm.other_online_reject_share_before:.1f}% → {100 * sm.other_online_reject_share_after:.1f}%）。"
    f"④ 与 43Na 预上线的 {P_PRE.hours} 小时相比，上线后变少的非 +1 请求几乎都是 43Na 条件成立的请求（`results/dr027_period_rates.csv`）：43Na 命中（任一名单）的非 +1 短信请求每 24 小时 {P_PRE.strategy_match_requests_per_24h:,.0f} → {P_ON.strategy_match_requests_per_24h:,.0f}，"
    f"其余非 +1 请求 {P_PRE.no_match_requests_per_24h:,.0f} → {P_ON.no_match_requests_per_24h:,.0f}"
    + (f"（按预上线前后两半分别为 {P1.strategy_match_requests_per_24h:,.0f} / {P2.strategy_match_requests_per_24h:,.0f} 与 {P1.no_match_requests_per_24h:,.0f} / {P2.no_match_requests_per_24h:,.0f}）" if P1 is not None and P2 is not None else "")
    + f"。{t_pre.iloc[0] if len(t_pre) else ''} UTC 之前没有 43Na，改前 4 天的大部分无法按此拆分。计数无法区分这是攻击方对 43Na 的反应，还是这类流量恰好在同一时间减少。"
    + (f"⑤ 预上线期只有 {P_PRE.hours} 小时（{P_PRE.utc_from}…{P_PRE.utc_to} UTC），后半段（{P2.utc_from}…{P2.utc_to} UTC）是高峰：非 +1 请求每 24 小时 {P2.non_plus1_requests_per_24h:,.0f}，前半段 {P1.non_plus1_requests_per_24h:,.0f}；"
       f"所以预上线期「若上线会唯一拦下」每 24 小时 {P_PRE.unique_reject_hits_per_24h:,.0f} 与上线后实际每 24 小时 {P_ON.unique_reject_hits_per_24h:,.0f} 的对比波动大。" if P1 is not None and P2 is not None else "")
    + f"⑥ 窗口内其它变化（上面的操作日志）：`strategy_rDf6oPcZ8ydk` 的改动只会减少它对 +86 的命中，方向是增加放行；+86 短信被拒（所有策略合计，逐日见上）自改动次日起为 0，所以它不能解释放行下降。`strategy_tO7DZkJ1g0C2` 为预上线，不影响最终结果。",
    "中（唯一拦截计数纯 SQL 与 E1 两法一致；「无其它 REVIEW 命中」过滤、精确时段速率与条件拆分只来自 E1；「若无 43Na」是推算）", "—（数据）；结论给段枝宏", "已答复",
    f"非 +1 放行日均 {sm.pass_non_plus1_before_mean:,.0f}（改前）→ {sm.pass_non_plus1_after_mean:,.0f}（改后）；43Na 唯一拦截 {sm.unique_block_would_be_pass_mean_after:,.0f}/日 ≈ 下降的 {100 * sm.unique_share_of_drop:.0f}%（推算；所试 {len(sens)} 组天数组合下 {rng(sens)}）；"
    f"与预上线期相比，变少的请求几乎都是 43Na 条件成立的请求（计数分解，非因果）")
# ================= DR-028 (skipped) =================
sec("DR-028", "预上线策略命中的逐请求验证码回填标签（有前提）",
    "对 7 日预上线策略的命中请求逐请求判断验证码是否回填，按策略 × 区号组 × 是否回填出计数。",
    "—", "本轮没有查询。", T["dr028_skip"] + "。", "—", "陈晨昕（数据口径）；范围批准：曾翔宇",
    "待取数（本次受阻：前提未满足）", "前提未满足，本轮跳过")
# ================= DR-029 (new this run: t_whitelist.temp) =================
cols_ = rd("p1_columns.csv") if ex("p1_columns.csv") else None
lc = rd("p2_list_counts.csv"); wl = lc[(lc.list_table == "t_whitelist") & (lc.tenant == "LKUS")]
tcm = cols_[(cols_.TABLE_NAME == "t_whitelist") & (cols_.COLUMN_NAME == "temp")].COLUMN_COMMENT if cols_ is not None else pd.Series([], dtype=str)
sec("DR-029", "`t_whitelist.temp` 的注释与界面显示是否一致（本轮新开）",
    "LKUS 白名单条目的 `temp` 取值与字段注释「1 临时，0 永久」对应；界面上这些条目显示为临时还是永久？以哪一边为准？（`DATA_REQUESTS.md` 没有覆盖：DR-015 只要求名单计数）",
    "`sql/p2_list_counts.sql`；字段注释 `sql/p1_columns.sql`",
    f"字段注释：「{esc(tcm.iloc[0]) if len(tcm) else '—'}」（`results/p1_columns.csv`）；LKUS 白名单 {fi(wl.n_entries.sum())} 条：" + "、".join(f"temp={int(r.temp)} 共 {fi(r.n_entries)} 条" for r in wl.groupby("temp", as_index=False).n_entries.sum().itertuples()) + "（`results/p2_list_counts.csv`）。",
    "数据只能给出取值与注释；界面如何显示、哪一边对，需要平台回答（由人回答，不是数据问题）。", "高（取值计数）；含义待确认", "林宏鹏",
    "待确认（问人：林宏鹏）", f"LKUS 白名单 {fi(wl.n_entries.sum())} 条 temp 取值与注释的含义需平台确认")
# ---------------- write ----------------
ORDER = sorted(S, key=lambda d: int(d.split("-")[1]))
head = ["# 04 数据问题结论（DR）", "",
        "> 2026-09-27 实测。DR 清单：随对话内联提供的 `DATA_REQUESTS.md`（桌面 2026-09-26 副本，28 条，最后一条变更「2026-09-26（第六轮）」）。本轮做 DR-027（待取数）与常设项 DR-003、010、013、014、015、016、017、018；"
        "DR-002、DR-022 的剩余部分在 Doris 一侧，只写短节；DR-028 前提未满足，跳过；新开 DR-029（本轮发现、清单未覆盖，由人回答）。其余 DR 本轮不做数据工作，状态沿用清单。",
        "> 每条给出 SQL（`sql/`）、本地脚本（`sql/local/`）与结果文件（`results/`）；数字全部来自本次会话执行的查询。`create_time` 为 UTC；「纽约日」= America/New_York 自然日。",
        f"> 口径：**短信** = LKUS_push 中 `$.para.email` 为空或不存在；**全部** = 全部 LKUS_push 行。**7 日** = {W7}；DR-027 另有自己的窗口（见该节）。**E1** = 行级抽取（纽约日 {days[0]}…{days[-1]}，只含标量与加盐哈希，只存本机）。", "",
        "| DR | 新状态 | 一句话 |", "|---|---|---|"]
head += [f"| [{d}](#{d.lower()}) | {S[d][0]} | {S[d][1]} |" for d in ORDER]
head += ["", "---", ""]
open(os.path.join(PKG, "04_数据问题结论.md"), "w", encoding="utf-8").write("\n".join(head + B) + "\n")
print("04 written:", len(S), "DRs")
