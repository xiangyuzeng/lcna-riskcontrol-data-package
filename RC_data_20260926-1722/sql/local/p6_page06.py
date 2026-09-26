#!/usr/bin/env python3
"""P6: write 06_评估指标计算手册.md. Worked-example numbers are read from this run's toolkit test outputs
(results/toolkit_tests/) and P3 results, so the page always matches the result files."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, T = os.path.join(PKG, "results"), os.path.join(PKG, "results", "toolkit_tests")
rd = lambda p: pd.read_csv(p)
fi = lambda v: f"{int(v):,}"
pct = lambda x: f"{100 * x:.1f}%"
picks = dict(kv.split("=") for kv in open(os.path.join(PKG, "_local_only", "p5_picks.txt")).read().split())
PRE, ON, TK6 = picks["PRE"], picks["ON"], picks["TK06"]
t1 = rd(os.path.join(T, "tk01_merged.csv")); t1["ny"] = (pd.to_datetime(t1.window_start_utc) - pd.Timedelta(hours=4)).dt.strftime("%Y-%m-%d")
t1 = t1.sort_values("ny"); last = t1.iloc[-1]; prev = t1.iloc[:-1]
t2 = rd(os.path.join(T, "tk02_merged.csv")); t3 = rd(os.path.join(T, "tk03_merged.csv"))
t6 = rd(os.path.join(T, f"tk06_recheck_{TK6}.csv")).iloc[0]
ts = rd(os.path.join(T, "_test_summary.csv"))
lk = rd(os.path.join(R, "p3_pass_leakage.csv")); nl = int(lk[lk.dimension == "cid"].rows.sum())
share = lambda d, v: lk[(lk.dimension == d) & (lk.value.astype(str).isin(v))].share.sum()
pat = open(os.path.join(T, "tk07_patrol_20260925.md"), encoding="utf-8").read().splitlines()
pline = [l for l in pat if l.startswith("- ")]
fr = rd(os.path.join(R, "dr007_fill_rate_by_cc.csv")) if os.path.exists(os.path.join(R, "dr007_fill_rate_by_cc.csv")) else None
L = ["# 06 评估指标计算手册", "",
     "> 2026-09-26 编写。每个指标给出：定义、用哪个模板（`toolkit/`）、怎么算、本包的示例数字（全部来自本包的模板测试，`results/toolkit_tests/`）。",
     "> 通用约定：LKUS_push；「短信」= `$.para.email` 为空或不存在；纽约自然日；本国区号 = `+1`（参数 `home_ccs`，可换）。模板测试的对照结果见 `results/toolkit_tests/_test_summary.csv`"
     f"（{int(ts.equal.sum())}/{len(ts)} 项一致）。", "",
     "## 1. 调用量与用户量（tk01）", "",
     "- **调用量**：窗口内请求次数，按最终结果（PASS/REJECT/REVIEW）与区号组拆分。",
     "- **用户量**：窗口内去重手机号（`sharding_key`）。**只能用 tk01 输出里 `level=window` 的行**：同一窗口内各分片可以相加，但不能跨分组、跨窗口相加（`05` §5 第 4 条）。uid 维度的用户量用 SQL 得不到精确值（uid 跨分片），要行级抽取在本地去重。",
     f"- **示例（纽约日 {last.ny}）**：LKUS_push 请求 {fi(last.requests)} 次；短信去重手机号 {fi(last.phones_sms)}；+1 放行手机号 {fi(last.phones_sms_pass_home)}（`results/toolkit_tests/tk01_merged.csv`，与 E1 本地去重一致）。", "",
     "## 2. 近 7 日同期（tk01 + same_hours.py）", "",
     "- **定义**：目标时段与前 7 天同一钟点的时段比较（例如今天 00:00–10:00 对比过去 7 天各自的 00:00–10:00）。",
     "- **做法**：`python3 toolkit/same_hours.py <开始> <结束> --prev 7 > w.txt` → `shard_runner.py run --template toolkit/tk01_volume_users.sql --windows-file w.txt` → `tk_merge.py tk01`。每一行是一个窗口，直接比较同一列。",
     f"- **示例**：{last.ny} 整天 vs 前 7 天（{prev.ny.iloc[0]}…{prev.ny.iloc[-1]}）：LKUS_push 请求 {fi(last.requests)} vs " + " / ".join(fi(v) for v in prev.requests)
     + f"；短信去重手机号 {fi(last.phones_sms)} vs 前 7 天 {fi(prev.phones_sms.min())}–{fi(prev.phones_sms.max())}（`requests`、`phones_sms` 列）。",
     "- **门槛**：审批材料里的「相对门槛」按这里的同期对比计算；绝对量门槛（调用量 / 用户量）直接取 §1。", "",
     "## 3. 命中量（tk02）", "",
     "- **定义**：一条策略在窗口内的命中次数（PV）与去重手机号（UV）。`hit_list=hitStrategy` 统计在线命中，`hitPreOnlineStrategy` 统计预上线命中。按策略 ID 认，不按名称。",
     f"- **示例**：`{PRE}`（预上线命中最多的策略，本包按数据挑选）7 日命中 {fi(t2.pv.sum())} 次（全部 LKUS_push 行），逐日去重手机号 {fi(t2.distinct_phones.min())}–{fi(t2.distinct_phones.max())}（`results/toolkit_tests/tk02_merged.csv`；逐日去重不能相加）。",
     "- **按 cid 与国家是否一致拆分**：tk08（DR-023），见 §9。", "",
     "## 4. 额外召回（tk03）", "",
     "- **定义**：预上线策略命中、但最终结果是 PASS 的请求——该策略上线后**新增**处置的量。按总命中排序会误导：命中很多、却早已被在线策略拦掉的策略，上线后省不下短信。",
     "- **做法**：tk03（只取最终 PASS 的请求）；`pv_home` 列看是否打到本国号码（误伤风险）。PASS 类预上线策略的「额外召回」含义相反（把非 PASS 改成 PASS），单独看。",
     f"- **示例**：`{PRE}` 7 日额外召回 {fi(t3.extra_recall_pv.sum())} 次，其中 +1 {fi(t3.pv_home.sum())} 次（`results/toolkit_tests/tk03_merged.csv`）；全部预上线策略见 `03` §5.2（`results/p3_strategies.csv`）。", "",
     "## 5. 准确率", "",
     "- **定义**：命中中被证实为黑产的比例。对**全部命中**用 SQL 重算规则逻辑（确认命中是规则真的成立，而不是计数器异常），再加至少两类证据。",
     "- **本包能提供的部分**：",
     f"  1. **规则复核（tk06）**：对命中集合重算计数特征，统计「命中但重算后规则不成立」的违例数。示例：`{TK6}` 的规则 `{t6.rule}`（特征 `{t6.feature_id}`），纽约日 2026-09-25 命中 {fi(t6.strategy_hits)} 次，违例 {fi(t6.violations_hit_but_rule_false_on_recompute)}；引擎计数与重算相等 {pct(t6.engine_eq_recompute_share)}、±1 内 {pct(t6.engine_within1_share)}（`results/toolkit_tests/tk06_recheck_{TK6}.csv`）。",
     "  2. **证据类维度**（tk04 / tk08 / E1 口径，均为聚合）：区号是否为攻击区号、手机号国家 ≠ IP 国家、token 缺失或为空、app 键缺失且自报旧版本（DR-012）、V3 低分。",
     "  3. **OTP 回填**（DR-007）：本包只能读 `t_verifycode_filled_statistics` 的按日 × 区号汇总，得到的是**区号级**回填率；用它折算命中里的真人比例要假设命中与该区号全部请求回填率相同（`results/dr007_otp_basis.csv`，标为折算）。逐请求的回填硬标签需要逐行关联，不在本包允许范围内。",
     "- **计算**：准确率 = 命中中「规则复核通过且至少两类证据成立」的请求数 ÷ 命中数；「暂无法判断」单列，不算进分子，也不直接当误伤。", "",
     "## 6. 规则复核（tk06）", "",
     "- **做法**：`tk06_rule_recheck_extract.sql` 行级抽取（`--kind rows --local`，每条 ≤1 小时，只存本机）→ `recheck_counter.py --feature-id … --op … --threshold … --eval-from …`。计数定义自动读取 `results/config_counter_features.csv`（周期、维度、PV/UV、过滤条件）。",
     "- **口径**：同一维度值、窗口 (t−period, t]、含当前请求、只计引擎评估过该特征的请求（2026-09-25 包 DR-003 校准）。窗口前留出与特征周期等长的暖机时间（1 天特征要 24 小时）。",
     "- **输出**：只有条数（命中数、违例数、非命中但重算成立数、引擎与重算一致率）。", "",
     "## 7. 放行泄漏与分数分布（tk04 / tk05）", "",
     f"- **放行泄漏**：非本国区号的 PASS，按区号、IP 国家、手机号国家 ≠ IP 国家、cid、token 状态、app 键拆分。示例：7 日 {fi(nl)} 次，其中 IP 在美国 {pct(share('ip_country', ['美国']))}、token 缺失或为空 {pct(share('token_state', ['absent', 'empty']))}、V3≥0.8 占 {pct(share('v3_bucket', ['>=0.8']))}（`03` §6）。",
     "- **分数分布**：`tk05` + `tk_merge.py tk05 --cuts 0.3,0.8`。分段点是参数；分数越高越像真人（2026-09-25 包 DR-009）。", "",
     "## 8. 每日巡检（tk07）", "",
     "`patrol.py --day <纽约日>` 输出一页：短信 PASS/REJECT/REVIEW、非本国区号放行占比、在线与预上线命中前 10（含其中最终 PASS 的次数）。示例 `results/toolkit_tests/tk07_patrol_20260925.md`：", ""] + pline + ["",
     "## 9. 命中按 cid × 国家是否一致拆分（tk08，DR-023）", "",
     "- **定义**：一条策略（在线或预上线）的命中按 cid × (`phoneCountry` ≠ `realIpCountry`) × 最终结果拆分的 PV 与去重手机号；`sms_only=1` 为短信口径。",
     f"- **示例**：`{ON}`（在线命中最多的 REJECT 策略）7 日，结果 `results/toolkit_tests/tk08_strategy_cid_geo.csv`；全部策略的 7 日表 `results/dr023_strategy_day_cid_geo.csv`。", "",
     "## 10. 引擎结果 vs 最终结果（tk09，DR-016 / DR-024）", "",
     "- **定义**：按纽约日 × cid × app 状态 × 版本组（数值比较，以 `min_version_num` 为界）统计引擎结果与最终结果的组合；用于监控 REVIEW 被改写为 PASS。",
     "- **示例**：纽约日 2026-09-25，`results/toolkit_tests/tk09_engine_vs_final.csv`；31 天见 `results/dr024_engine_vs_final.csv`。"]
if fr is not None:
    L += ["", "## 11. OTP 回填率（DR-007）", "",
          "- **来源**：`aws-luckyus-upush-rw` / `luckyus_iupushsms.t_verifycode_filled_statistics`（本包允许的唯一 upush 读数：按日 × 区号 × 项目 SUM）。按 UTC 日汇总，与风控日志关联要按 UTC 日。",
          "- **用法**：区号级回填率 = SUM(filled_num) / SUM(sent_num)；「发送 / 风控放行」比值明显下降的日子说明统计表漏记，不能用来算回填率（`results/dr007_daily_ccgroup.csv`）。"]
open(os.path.join(PKG, "06_评估指标计算手册.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("06 written", len(L))
