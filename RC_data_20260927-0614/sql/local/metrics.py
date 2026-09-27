#!/usr/bin/env python3
"""One metric, one value (P6). Computes every headline metric ONCE from results/ and exposes it to the page generators
(`from metrics import M, T`); `python3 metrics.py` writes results/p6_metric_registry.csv. p6_checks.py then scans every
page for each metric's label pattern and fails on any competing value.

Each metric: value (canonical text), window, basis, source file, pattern (regex whose groups must reproduce `value`
wherever the label appears on a page; None = not text-checked)."""
import os, re
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
ex = lambda n: os.path.exists(os.path.join(R, n)) and os.path.getsize(os.path.join(R, n)) > 5
rd = lambda n, **kw: pd.read_csv(os.path.join(R, n), **kw)
fi = lambda v: f"{int(v):,}"
M = {}


def put(mid, value, window, basis, source, pattern=None):
    M[mid] = {"metric_id": mid, "value": str(value), "window": window, "basis": basis, "source": source, "pattern": pattern}


# ---- canonical sentences (text that must read the same on every page) ----------------------------------------------
T = {
    "upush_date": "`t_verifycode_filled_statistics` 按 `statistic_date` 汇总；本包按 UTC 日处理，其时区待陈晨昕确认（DR-007）",
    "dr028_skip": "DR-028 前提未满足（陈晨昕尚未确认 `mobile` 的存储方式与回填时点），本轮跳过：§3.2 不变",
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
    put("oplog_field_changes_updates", fi(len(upd)), "同上", "更新操作中的白名单字段变化（不含新增/删除）", "results/p2_oplog_timeline.csv")
    T["oplog"] = (f"操作日志 `t_operation_log` 共 {fi(ops)} 次操作（" + "、".join(f"{k} {fi(v)}" for k, v in ot.items()) + f"；其中 {fi(opc)} 次有字段变化，共 {fi(fld)} 处字段变化："
                  f"新增 / 删除各按 1 处计 {fi(len(obj))} 处，{fi(upd.op_id.nunique())} 次更新共 {fi(len(upd))} 处白名单字段变化；{op.first_op_utc.min()} … {op.last_op_utc.max()} UTC）")
if ex("p3_daily_result.csv"):
    dr = rd("p3_daily_result.csv"); W = f"纽约日 {dr.ny_date.min()}…{dr.ny_date.max()}"
    tot = dr[["sms_PASS", "sms_REJECT", "sms_REVIEW"]].sum()
    put("sms_7d_requests", fi(tot.sum()), W, "短信口径", "results/p3_daily_result.csv", r"(\d[\d,]*) 次短信请求")
    put("sms_7d_pass", fi(tot.sms_PASS), W, "短信口径", "results/p3_daily_result.csv")
    put("sms_7d_reject", fi(tot.sms_REJECT), W, "短信口径", "results/p3_daily_result.csv")
    put("sms_7d_review", fi(tot.sms_REVIEW), W, "短信口径", "results/p3_daily_result.csv")
    put("push_7d_rows", fi(dr.total.sum()), W, "全部 LKUS_push 行", "results/p3_daily_result.csv", r"全部 LKUS_push 行[^0-9]{0,12}(\d[\d,]*) 行")
if ex("p3_pass_by_ccgroup.csv"):
    p7 = rd("p3_pass_by_ccgroup.csv").query("ny_date == '7d'").iloc[0]
    put("nonplus1_pass_share_7d", f"{100 * p7.non_plus1_share_of_pass:.1f}%", "7 日", "短信口径", "results/p3_pass_by_ccgroup.csv", r"(\d+\.\d%) 来自非 \+1")
if ex("p3_distinct_users.csv"):
    u7 = rd("p3_distinct_users.csv").query("ny_date == '7d'").iloc[0]
    put("distinct_phones_7d", fi(u7.distinct_phones), "7 日（窗口级去重）", "短信口径", "results/p3_distinct_users.csv", r"7 日去重手机号 (\d[\d,]*)")
if ex("p3_strategies.csv") and ex("p2_hits_7d.csv"):
    ps_, h_ = rd("p3_strategies.csv"), rd("p2_hits_7d.csv")
    for sid in ("strategy_GbsajBR69can",):
        r_ = ps_[(ps_.strategy_id == sid) & (ps_.list == "preonline")] if "list" in ps_ else ps_[ps_.strategy_id == sid]
        if len(r_):
            put(f"{sid}_preonline_pv_7d_sms", fi(r_.pv.iloc[0]), "纽约日 7 日", "短信口径（E1）", "results/p3_strategies.csv")
            put(f"{sid}_extra_recall_7d_sms", fi(r_.extra_recall_pv.iloc[0]), "纽约日 7 日", "短信口径（E1；PASS 类 = 最终非 PASS 的命中）", "results/p3_strategies.csv")
        put(f"{sid}_preonline_pv_7d_all", fi(h_[(h_.list == "preonline") & (h_.strategy_id == sid)].pv.sum()), "纽约日 7 日", "全部 LKUS_push 行（纯 SQL）", "results/p2_hits_7d.csv")
    if ex("toolkit_tests/tk03_extra_recall.csv"):
        put("strategy_GbsajBR69can_extra_recall_7d_all", fi(rd("toolkit_tests/tk03_extra_recall.csv").extra_recall_pv.sum()), "纽约日 7 日", "全部 LKUS_push 行（tk03，sms_only=0）", "results/toolkit_tests/tk03_extra_recall.csv")
if ex("dr027_summary.csv"):
    sm_ = rd("dr027_summary.csv")
    for r in sm_.itertuples():
        put(f"dr027_{r.metric}", r.value, r.window, r.basis, "results/dr027_summary.csv")
if ex("toolkit_tests/_test_summary.csv"):
    ts = rd("toolkit_tests/_test_summary.csv")
    put("toolkit_tests", f"{int(ts.equal.sum())}/{len(ts)}", "本包测试", "—", "results/toolkit_tests/_test_summary.csv", r"(\d+/\d+) 项核对一致")
if ex("timing.csv") and ex("_runlog.csv"):
    t, rl = rd("timing.csv"), rd("_runlog.csv")
    put("statements", fi(len(t)), "本包全部运行", "—", "results/timing.csv", r"(\d[\d,]*) 条分片语句")
    put("runs", fi(len(rl)), "本包全部运行", "—", "results/_runlog.csv", r"(\d[\d,]*) 次运行")
if ex("dr027_daily_decomposition.csv"):
    dd = rd("dr027_daily_decomposition.csv")
    for r in dd.itertuples():
        put(f"dr027_uniq_after_{r.ny_date}", fi(r.s_online_only_reject_non_plus1), r.ny_date, "短信口径，非 +1", "results/dr027_daily_decomposition.csv")
        put(f"dr027_pass_non_plus1_{r.ny_date}", fi(r.pass_non_plus1), r.ny_date, "短信口径，非 +1", "results/dr027_daily_decomposition.csv")


def write():
    df = pd.DataFrame(M.values())
    df.to_csv(os.path.join(R, "p6_metric_registry.csv"), index=False)
    return df


if __name__ == "__main__":
    print(write()[["metric_id", "value", "window"]].to_string(index=False))
