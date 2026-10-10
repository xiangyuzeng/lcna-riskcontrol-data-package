#!/usr/bin/env python3
"""One metric, one value (P6). Computes every headline metric ONCE from results/ and exposes it to the page generators
(`from metrics import M, T`); `python3 metrics.py` writes results/p6_metric_registry.csv. p6_checks.py then scans every
page for each metric's label pattern and fails on any competing value.
Each metric: value (canonical text), window, basis, source file, pattern (regex whose group must reproduce `value` wherever the
label appears on a page; None = not text-checked)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
fi = lambda v: f"{int(round(float(v))):,}"
M = {}


def put(mid, value, window, basis, source, pattern=None):
    M[mid] = {"metric_id": mid, "value": str(value), "window": window, "basis": basis, "source": source, "pattern": pattern}


T = {
    "upush_date": "`t_verifycode_filled_statistics` 按 `statistic_date` 汇总；本包按 UTC 日处理，其时区待陈晨昕确认（DR-007）",
    "dr028_skip": "本次跳过：前提未满足（陈晨昕的口径确认）",
    "doris_dep": "Doris 不可达，等 DR-020 的只读账号（依赖，不是临时受阻）",
}
if ex("p2_oplog_counts.csv") and ex("p2_oplog_timeline.csv"):
    op, tl = rd("p2_oplog_counts.csv"), rd("p2_oplog_timeline.csv")
    ops, opc, fld = int(op.n.sum()), int(tl.op_id.nunique()), len(tl)
    put("oplog_operations", fi(ops), f"{op.first_op_utc.min()}…{op.last_op_utc.max()} UTC", "t_operation_log 全部行", "results/p2_oplog_counts.csv", r"(\d[\d,]*) 次操作")
    put("oplog_ops_with_changes", fi(opc), "同上", "有白名单字段变化的操作", "results/p2_oplog_timeline.csv", r"(\d[\d,]*) 次有字段变化")
    put("oplog_changed_fields", fi(fld), "同上", "白名单字段", "results/p2_oplog_timeline.csv", r"(\d[\d,]*) 处字段变化")
    ot = op.groupby("operation_type").n.sum()
    obj = tl[tl.field == "(object)"]; upd = tl[tl.field != "(object)"]
    T["oplog"] = (f"操作日志 `t_operation_log` 共 {fi(ops)} 次操作（" + "、".join(f"{k} {fi(v)}" for k, v in ot.items()) + f"；其中 {fi(opc)} 次有字段变化，共 {fi(fld)} 处字段变化："
                  f"新增 / 删除各按 1 处计 {fi(len(obj))} 处，{fi(upd.op_id.nunique())} 次更新共 {fi(len(upd))} 处白名单字段变化；{op.first_op_utc.min()} … {op.last_op_utc.max()} UTC）")
if ex("p3_daily_result.csv"):
    dr = rd("p3_daily_result.csv"); W = f"纽约日 {dr.ny_date.min()}…{dr.ny_date.max()}"
    tot = dr[[c for c in ("sms_PASS", "sms_REJECT", "sms_REVIEW") if c in dr]].sum()
    put("sms_7d_requests", fi(tot.sum()), W, "短信口径", "results/p3_daily_result.csv", r"7 日短信请求 (\d[\d,]*) 次")
    put("sms_7d_pass", fi(tot.get("sms_PASS", 0)), W, "短信口径", "results/p3_daily_result.csv")
    put("sms_7d_reject", fi(tot.get("sms_REJECT", 0)), W, "短信口径", "results/p3_daily_result.csv")
    put("sms_7d_review", fi(tot.get("sms_REVIEW", 0)), W, "短信口径", "results/p3_daily_result.csv")
    put("push_7d_rows", fi(dr.total.sum()), W, "全部 LKUS_push 行", "results/p3_daily_result.csv", r"全部 LKUS_push 行 (\d[\d,]*) 行")
if ex("p3_pass_by_ccgroup.csv"):
    p7 = rd("p3_pass_by_ccgroup.csv").query("ny_date == '7d'").iloc[0]
    put("nonplus1_pass_share_7d", f"{100 * p7.non_plus1_share_of_pass:.1f}%", "7 日", "短信口径", "results/p3_pass_by_ccgroup.csv", r"(\d+\.\d%) 来自非 \+1")
if ex("p3_distinct_users.csv"):
    u7 = rd("p3_distinct_users.csv").query("ny_date == '7d'").iloc[0]
    put("distinct_phones_7d", fi(u7.distinct_phones), "7 日（窗口级去重）", "短信口径", "results/p3_distinct_users.csv", r"7 日去重手机号 (\d[\d,]*)")
if ex("dr030_retries_summary.csv"):
    r30 = rd("dr030_retries_summary.csv").iloc[0]
    put("dr030_numbers_uniquely_rejected", fi(r30.numbers_uniquely_rejected), "43Na 上线后至纽约日 10-09", "短信口径", "results/dr030_retries_summary.csv", r"被它唯一拦下的号码 (\d[\d,]*) 个")
    put("dr030_numbers_with_later_request", fi(r30.numbers_with_any_later_request), "同上", "短信口径", "results/dr030_retries_summary.csv")
if ex("dr010_attack_rule.csv"):
    k5 = rd("dr010_attack_rule.csv").set_index("k").loc[5.0]
    put("dr010_attack_days_since_0903", f"{int(k5.flagged_days_since_09_03)}/{int(k5.days_since_09_03)}", "纽约日 09-03…10-09", "非 +1/+86 短信请求，k=5", "results/dr010_attack_rule.csv")
if ex("dr036a_utc_daily_vs_doris.csv"):
    j = rd("dr036a_utc_daily_vs_doris.csv")
    put("dr036a_pass_days_equal", f"{int((j.diff_pass == 0).sum())}/{len(j)}", "UTC 日 09-13…10-08", "短信口径 vs Doris l2_scene=1001", "results/dr036a_utc_daily_vs_doris.csv", r"PASS (\d+/\d+) 天与 Doris 完全相同")
if ex("toolkit_tests/_test_summary.csv"):
    ts = rd("toolkit_tests/_test_summary.csv")
    put("toolkit_tests", f"{int(ts.equal.sum())}/{len(ts)}", "本包测试", "—", "results/toolkit_tests/_test_summary.csv", r"(\d+/\d+) 项核对一致")
if ex("timing.csv") and ex("_runlog.csv"):
    t, rl = rd("timing.csv"), rd("_runlog.csv")
    put("statements", fi(len(t)), "本包全部运行", "—", "results/timing.csv", r"(\d[\d,]*) 条分片语句")
    put("runs", fi(len(rl)), "本包全部运行", "—", "results/_runlog.csv", r"(\d[\d,]*) 次运行")
if ex("p2_hits_7d.csv") and ex("p3_strategies.csv"):
    h_, ps_ = rd("p2_hits_7d.csv"), rd("p3_strategies.csv")
    for sid in ("strategy_WvNGjLMgoOyn", "strategy_bYXaOJ4qXtW4"):
        put(f"{sid}_online_pv_7d_all", fi(h_[(h_.list == "online") & (h_.strategy_id == sid)].pv.sum()), "纽约日 10-03…10-09", "全部 LKUS_push 行（纯 SQL）", "results/p2_hits_7d.csv")
        r_ = ps_[(ps_.strategy_id == sid) & (ps_.list == "online")]
        put(f"{sid}_online_pv_7d_sms", fi(r_.pv.sum()), "纽约日 10-03…10-09", "短信口径（E1）", "results/p3_strategies.csv")


def write():
    df = pd.DataFrame(M.values())
    df.to_csv(os.path.join(R, "p6_metric_registry.csv"), index=False)
    return df


if __name__ == "__main__":
    print(write()[["metric_id", "value", "window"]].to_string(index=False))
