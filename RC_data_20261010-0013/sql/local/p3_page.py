#!/usr/bin/env python3
"""P3: write 03_近7日数据画像_20261009.md from results/p3_*.csv (E1 local profile), the bridge series (L1) and the standing
items; every number is read from results/ at generation time."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
fi = lambda v: f"{int(round(float(v))):,}"
pc = lambda v, d=1: f"{100 * float(v):.{d}f}%"
esc = lambda v: "" if pd.isna(v) else str(v).replace("|", "\\|")
dr, pcg, du = rd("p3_daily_result.csv"), rd("p3_pass_by_ccgroup.csv"), rd("p3_distinct_users.csv")
ca, st_, lk, cx = rd("p3_cid_app_profile.csv", dtype={"cid": str}), rd("p3_strategies.csv"), rd("p3_pass_leakage.csv"), rd("p3_crosscheck.csv")
h5, v3 = rd("p3_h5_a2_chain.csv").iloc[0], rd("p3_v3_by_ccgroup_cid.csv", dtype={"cid": str})
br = rd("bridge_daily_series.csv")
W0, W1 = dr.ny_date.min(), dr.ny_date.max()
sms_cols = [c for c in dr.columns if c.startswith("sms_")]
tot = dr[sms_cols].sum()
u7 = du[du.ny_date == "7d"].iloc[0]
p7 = pcg[pcg.ny_date == "7d"].iloc[0]
L = ["# 03 近 7 日数据画像（纽约日 2026-10-03…2026-10-09）", "",
     f"> 2026-10-10 生成。窗口 = 纽约日 {W0}…{W1}（UTC 2026-10-03 04:00 → 10-10 04:00）。主口径 = **短信**（`$.para.email` 为空或不存在）；另标「全部 LKUS_push 行」的地方含少量带 email 的请求。",
     "> 方法：行级抽取 E1（`sql/e1.sql`，只在本机，身份字段是加盐哈希）→ 本地汇总 `sql/local/p3_profile.py` → 与纯 SQL 逐格核对（L1 `sql/l1_long.sql`、tk07 `sql/p3_tk07_7d.sql`、`sql/p2_hits_7d.sql`）。", "",
     "## 0. 与纯 SQL 的核对", "", "| 核对 | 格子数 | 不一致 | SQL 合计 | E1 合计 |", "|---|---|---|---|---|"]
L += [f"| {r.check} | {r.cells} | {r.mismatching_cells} | {fi(r.sql_total)} | {fi(r.e1_total)} |" for r in cx.itertuples()]
L += ["", "## 1. 按天：结果与区号组", "",
      "> 策略时点（纽约时间，`results/dr034_timeline.csv`）：WvNG 10-08 03:54 上线，bYXa 10-08 21:44 上线；所以 10-08 只有部分时段有 WvNG、几乎没有 bYXa，**10-09 是两条都在线的第一个完整纽约日**。", "",
      f"7 日短信请求 {fi(tot.sum())} 次：PASS {fi(tot.get('sms_PASS', 0))}、REJECT {fi(tot.get('sms_REJECT', 0))}、REVIEW {fi(tot.get('sms_REVIEW', 0))}；全部 LKUS_push 行 {fi(dr.total.sum())} 行（`results/p3_daily_result.csv`）。"
      f"短信 PASS 中 {pc(p7.non_plus1_share_of_pass)} 来自非 +1 号码（`results/p3_pass_by_ccgroup.csv`）。", "",
      "| 纽约日 | 短信请求 | PASS | REJECT | REVIEW | PASS 中 +1 | +86 | 其他 | 非 +1 占 PASS |", "|---|---|---|---|---|---|---|---|---|"]
pg = pcg[pcg.ny_date != "7d"].set_index("ny_date")
for r in dr.itertuples():
    g = pg.loc[r.ny_date]
    L.append(f"| {r.ny_date} | {fi(getattr(r, 'sms_PASS', 0) + getattr(r, 'sms_REJECT', 0) + getattr(r, 'sms_REVIEW', 0))} | {fi(getattr(r, 'sms_PASS', 0))} | {fi(getattr(r, 'sms_REJECT', 0))} | {fi(getattr(r, 'sms_REVIEW', 0))} | {fi(g.pass_plus1)} | {fi(g.pass_plus86)} | {fi(g.pass_other)} | {pc(g.non_plus1_share_of_pass)} |")
L += ["", "10-08（WvNG 上线）、10-09（bYXa 上线）两天非 +1 占比明显下降；时间重合不等于因果（见 DR-034、`05_开放探索_20261009.md`）。", "",
      "## 2. 去重用户", "",
      f"7 日去重手机号 {fi(u7.distinct_phones)}（短信，窗口级去重，按加盐的 `sharding_key` 哈希在本机去重）；去重 uid {fi(u7.distinct_uids)}；PASS 去重手机号 {fi(u7.pass_distinct_phones)}，其中 +1 {fi(u7.pass_plus1_distinct_phones)}（`results/p3_distinct_users.csv`；逐日数不能相加）。"
      f"各分片去重手机号之和 {fi(u7.sum_per_shard_distinct_phones)}（与窗口去重相同 = 同一号码只在一个分片），uid 之和 {fi(u7.sum_per_shard_distinct_uids)}（uid 跨分片，见 `results/p3_dr014_shard_spread.csv`）。", "",
      "## 3. cid × app", "", "| cid | 来源枚举 | app | 请求 | PASS 占比 | token 不存在 | token 为空 | V3 <0.3 | 0.3–0.8 | ≥0.8 | 无分数 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
vb = [c for c in ca.columns if c.startswith("v3_")]
for _, r in ca.head(12).iterrows():
    L.append(f"| {r.cid} | {esc(r.cid_origin)} | {'（无 app 键）' if r.app == '<absent>' else esc(r.app)} | {fi(r.requests)} | {pc(r.pass_share)} | {pc(r.token_absent_share)} | {pc(r.token_empty_share)} | " + " | ".join(pc(r[c]) for c in vb) + " |")
L += ["", "全表 `results/p3_cid_app_profile.csv`（短信）。无 app 的 105/106 请求：UA 类别、版本、区号组、IP 国家见 `results/p3_empty_app_profile.csv`、`results/p3_empty_app_versions.csv`，与 DR-012 复测一致。", "",
      "## 4. 策略命中与额外召回", "",
      "在线命中前 10 与预上线命中前 10（短信；**额外召回**：REJECT / REVIEW 类 = 命中且最终 PASS；PASS 类 = 命中且最终不是 PASS）。全部 LKUS_push 行的命中见 `results/p2_hits_7d.csv`（纯 SQL）。", "",
      "| 列表 | strategy_id | 处置 | 命中 | 去重手机号 | 额外召回 | 其中非 +1 | 名称 |", "|---|---|---|---|---|---|---|---|"]
for lst in ("online", "preonline"):
    for r in st_[st_.list == lst].head(10).itertuples():
        L.append(f"| {'在线' if lst == 'online' else '预上线'} | `{r.strategy_id}` | {r.result_name} | {fi(r.pv)} | {fi(r.uv_phones)} | {fi(r.extra_recall_pv) if lst == 'preonline' else '—'} | {fi(r.extra_recall_non_plus1_pv) if lst == 'preonline' else '—'} | {esc(r.strategy_name)[:60]} |")
L += ["", "## 5. 非 +1 放行（泄漏）画像", ""]
for dim, name in (("cc", "区号"), ("ip_country", "IP 国家"), ("phone_ne_ip_country", "号码国家 ≠ IP 国家"), ("cid", "cid"), ("token_state", "token")):
    g = lk[lk.dimension == dim].head(8)
    L.append(f"- **{name}**：" + "；".join(f"{esc(r.value)} {fi(r.rows)}（{pc(r.share)}）" for r in g.itertuples()))
L += [f"- 非 +1 短信 PASS 共 {fi(lk[lk.dimension == 'cid'].rows.sum())} 次（`results/p3_pass_leakage.csv`）。", "",
      "## 6. V3 分数", "",
      "按区号组 × cid × 分数段：`results/p3_v3_by_ccgroup_cid.csv`；分数直方图 `results/p3_v3_score_hist.csv`；按天承载分数的特征 `results/p3_v3_fid_daily.csv`。"
      + "非 +1（other）Android：" + "；".join(f"{r.v3_bucket} {pc(r.share_within_ccgroup_cid)}" for r in v3[(v3.cc_group == "other") & (v3.cid == "105")].itertuples()) + "。", "",
      "## 7. 累计特征返回码（DR-003 常设）", "",
      "7 日每个累计特征的返回码：`results/p3_counter_codes_7d.csv`（逐日 `results/p3_counter_codes_daily.csv`）；带条件 / 组合维度的特征与过滤条件重算见 `04_数据问题结论.md#dr-003`。", "",
      "## 8. H5 A2 链（REVIEW → reviewRepeat）", "",
      f"H5（cid 108）短信请求 {fi(h5.h5_requests)}，最终 REVIEW {fi(h5.final_review)}；`reviewRepeat=true` {fi(h5.review_repeat_true)} 次，其中 30 分钟内能对上之前一次 REVIEW 的 {fi(h5.review_repeat_true_linked_to_prior_review_30min)}；"
      f"`reviewRepeat=true` 的最终结果 PASS {fi(h5.review_repeat_true_final_pass)} / REVIEW {fi(h5.review_repeat_true_final_review)} / REJECT {fi(h5.review_repeat_true_final_reject)}（`results/p3_h5_a2_chain.csv`、`results/p3_review_matrix.csv`）。", "",
      "## 9. 常设项", "",
      "- DR-016 引擎结果 vs 最终结果、DR-017 优先级高于白名单的策略、DR-018 UTC 时刻规则：见 `04_数据问题结论.md` 对应小节（`results/dr016_summary_7d.csv`、`results/dr017_above_whitelist.csv`、`results/dr018_time_rule_strategies.csv`）。", "",
      "## 10. 桥接序列（纽约日 2026-09-27…10-09，供桌面接上 09-27 包）", "",
      "| 纽约日 | 短信请求 | +1 PASS | +86 PASS | 其他 PASS | PASS 合计 | 非 +1 占 PASS | 当日结束的 24 小时窗口里 PASS 最大值 |", "|---|---|---|---|---|---|---|---|"]
for _, r in br.iterrows():
    L.append(f"| {r.ny_date} | {fi(r.sms_requests)} | {fi(r.get('+1_PASS', 0))} | {fi(r.get('+86_PASS', 0))} | {fi(r.get('other_PASS', 0))} | {fi(r.pass_total)} | {pc(r.non_plus1_share_of_pass)} | {fi(r.max_rolling_24h_sms_pass)} |")
al = rd("bridge_alert_check.csv").iloc[0]
L += ["", f"来源 `results/bridge_daily_series.csv`（L1，短信，结果 × 区号组全列）。按小时滚动 24 小时的短信 PASS：自 2026-06-01 起最大 {fi(al.max_rolling_24h_sms_pass)}（截止于 UTC {al.at_end_hour_utc}），09-27 以后最大 {fi(al.max_since_09_27)}；超过 5000 的小时数 {int(al.hours_above_5000)}（`results/bridge_alert_check.csv`，按整点滚动，与告警的精确窗口可能差几分钟）。", ""]
open(os.path.join(PKG, "03_近7日数据画像_20261009.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("03 written", len(L))
