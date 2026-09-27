#!/usr/bin/env python3
"""P1: extra sections for dictionary/t_access_log_0000.md and t_rms_engine_strategy.md, written from this run's results
(results/p1_json_keys_summary.csv, p1_payload_size.csv, p1_scene_rows.csv, p1_chk_consistency.csv, p1_sk_*.csv).
Output: results/p1_dict_extra_<table>.md (merged into the dictionary page by p1_dictionary.py)."""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(PKG, "results")
rd = lambda n: pd.read_csv(os.path.join(R, n))
ks, ps, sr, k = rd("p1_json_keys_summary.csv"), rd("p1_payload_size.csv"), rd("p1_scene_rows.csv"), rd("p1_chk_consistency.csv")
skf = sorted(f for f in os.listdir(R) if f.startswith("p1_sk_concat_check_") and f.endswith(".csv"))[-1]
sk = rd(skf)
day = str(sk.ny_date.iloc[0])
win = sorted(k.ny_date.unique())
push = ks[ks.scene_id == "LKUS_push"]
SRC = [("req_top", "`request_strategy_engine`", "对象"), ("para", "`request_strategy_engine` → `$.para`", "**JSON 字符串**（需 `CAST(JSON_UNQUOTE(...) AS JSON)`）"),
       ("resp_top", "`response_strategy_engine`", "对象"), ("re", "`response_strategy_engine` → `$.re`", "对象"),
       ("response", "`response`（返回调用方）", "对象"), ("request", "`request`（rpc 输入）", "对象"), ("extend", "`extend`", "对象"),
       ("featureDetail_elem", "`$.re.featureDetail[*]`", "原生数组"), ("featureDetail_comments", "`$.re.featureDetail[*].comments`", "对象"),
       ("hitStrategy_elem", "`$.re.hitStrategy[*]`", "字符串里装数组（CAST 后展开）"), ("hitPreOnlineStrategy_elem", "`$.re.hitPreOnlineStrategy[*]`", "字符串里装数组（CAST 后展开）"),
       ("ruleDetail_elem", "`$.re.ruleDetail[*]`", "原生数组")]
L = ["## 分片键（DR-014）", "",
     f"- `sharding_key` = `CONCAT(country_code, phone)`（带 `+` 的区号 + 手机号）：纽约日 {day} LKUS_push {int(sk.n.sum()):,} 行中 {int(sk.n_sk_eq_cc_col_plus_phone_col.sum()):,} 行成立（`results/{skf}`）。",
     f"- 7 日（{win[0]}…{win[-1]}）LKUS_push {int(k.n.sum()):,} 行 `sharding_key = $.para.fullPhoneNo` 成立 {int(k[k.sk_eq_full == 1].n.sum()):,} 行（`results/p1_chk_consistency.csv`）。",
     "- 请求参数 `fullPhoneNo` 自纽约日 2026-08-18 起出现（2026-09-25 包实测，本包未复测）；分片键规则本身没有变：此前此后都等于区号 + 手机号。",
     "- 其它场景按场景组分片（login / payment / 下单 / 取消 / 新人券 = `userNo`），本包的抽查见 `04_数据问题结论.md#dr-014`。", "",
     f"## JSON 列结构（只列键，不取值；纽约日 {day}，LKUS_push，全部 64 分片）", "",
     "| 来源 | 类型 | 键（出现行占比） |", "|---|---|---|"]
for src, name, typ in SRC:
    g = push[push.source == src].sort_values("n_rows", ascending=False)
    if len(g):
        L.append(f"| {name} | {typ} | " + ", ".join(f"`{r.json_key}`({r.share_of_scene_rows * 100:.1f}%)" if r.share_of_scene_rows <= 1 else f"`{r.json_key}`" for r in g.itertuples()) + " |")
L += ["", "- 数组类来源的占比是「带该键的行 / 场景行数」，一个行里有多个元素时仍按行计。`hitBreakStrategy` 当天没有任何元素（`results/p1_keys_hitBreakStrategy_elem.csv` 为空）。", ""]
p = ps.groupby("scene_id").sum(numeric_only=True)
pp = p.loc["LKUS_push"]
L += [f"## 体积（纽约日 {day}，LKUS_push {int(pp.n):,} 行，`results/p1_payload_size.csv`）", "",
      f"- 平均每行：`response_strategy_engine` {pp.bytes_response_engine / pp.n:,.0f} B，其中 `featureDetail` {pp.bytes_feature_detail / pp.n:,.0f} B、`ruleDetail` {pp.bytes_rule_detail / pp.n:,.0f} B；`request_strategy_engine` {pp.bytes_request_engine / pp.n:,.0f} B。",
      "- 永远不要 SELECT 整个 JSON 列：在服务端用 `JSON_TABLE` / `JSON_EXTRACT` 只取标量。", ""]
s = sr.groupby("scene_id").sum(numeric_only=True)
L += [f"## 基础列的可用性（纽约日 {day}，全部场景，`results/p1_scene_rows.csv`）", "",
      f"- `ip_city`、`ip_province`、`country`、`city` 基础列：全部场景 {int(s.n_rows.sum()):,} 行中非空 {int(s[['ip_city_col_nonempty', 'ip_province_col_nonempty', 'country_col_nonempty', 'city_col_nonempty']].sum().sum())} 行 → IP 地理只能取 `$.para.realIpCountry/realIpProvince/realIpCity`。",
      "- 设备号：" + "；".join(f"`{sc}` did {int(r.did_col_nonempty)}/{int(r.n_rows)}、device_id {int(r.device_id_col_nonempty)}/{int(r.n_rows)}" for sc, r in s.iterrows() if r.did_col_nonempty or r.device_id_col_nonempty) +
      f"；`tongdun_device_id` 全部场景非空 {int(s.tongdun_device_id_col_nonempty.sum())} 行。LKUS_push 没有设备号。",
      f"- `country_code` 列与 `$.para.countryCode`：7 日 LKUS_push {int(k.n.sum()):,} 行里带 `+` 的 {int(k[k.cc_col_form == 'plus'].n.sum()):,} 行、二者相等 {int(k[k.cc_col_eq_para == 1].n.sum()):,} 行。",
      f"- `result` 列 = `response.$.result`：7 日 {int(k[k.result_col == k.response_result].n.sum()):,} / {int(k.n.sum()):,} 行一致，即返回调用方的最终结果；引擎自己的结果是 `$.re.resultName`。", ""]
open(os.path.join(R, "p1_dict_extra_t_access_log_0000.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
st = rd("config_strategy.csv")
L2 = ["## 取值（2026-09-27 导出，`results/config_strategy.csv`）", "",
      "- `status`：1 = 上线、2 = 预上线、0 = 下线（与命中元素里的 `ONLINE` / `PREONLINE` 对照核实，见 `02_线上配置导出.md` §3）。字段注释未写取值含义。",
      "- 当前计数：" + "；".join(f"{a} status={int(b)} 共 {n} 条" for (a, b), n in st.groupby(["access_id", "status"]).size().items()) + "。",
      "- `exec_priority` 越大越先执行；修改上线策略会把 `status` 打回 2（操作日志实证，见 `results/p2_oplog_timeline.csv`）。"]
open(os.path.join(R, "p1_dict_extra_t_rms_engine_strategy.md"), "w", encoding="utf-8").write("\n".join(L2) + "\n")
print(open(os.path.join(R, "p1_dict_extra_t_access_log_0000.md"), encoding="utf-8").read()[:3000])

# ---- column comments that contradict the data (checked against the exported config) -----------------------
cols = rd("p1_columns.csv")
rule, para, tool = rd("config_rule.csv"), rd("config_para.csv"), rd("config_tool.csv")
cm = lambda t, c: cols[(cols.TABLE_NAME == t) & (cols.COLUMN_NAME == c)].COLUMN_COMMENT.iloc[0]
chk = [
    ("t_rms_engine_rule", "rule_id", cm("t_rms_engine_rule", "rule_id"),
     f"值全部是 `rule_` 前缀（{int(rule.rule_id.str.startswith('rule_').sum())}/{len(rule)}）：是规则 ID，不是特征 ID（特征 ID 在 `feature_id` 列）"),
    ("t_rms_engine_rule", "status", cm("t_rms_engine_rule", "status"),
     f"这是规则表的开关，注释写成「策略状态」；取值 " + "、".join(f"{k}:{v}" for k, v in rule.status.value_counts().items())),
    ("t_rms_engine_para", "para_id", cm("t_rms_engine_para", "para_id"),
     f"值是参数名（如 `{para.para_id.iloc[0]}`），场景在 `scene_id` 列：注释写成了「场景ID」"),
    ("t_rms_engine_para", "para_name", cm("t_rms_engine_para", "para_name"),
     "值是参数的显示名，不是场景名称"),
    ("t_rms_engine_tool", "tool_type", cm("t_rms_engine_tool", "tool_type"),
     "注释说 3 = 累计特征工具，但 3 个工具（含 `累计特征工具`）全部是 " + "、".join(f"tool_type={k}" for k in sorted(tool.tool_type.unique()))),
]
cv = pd.DataFrame(chk, columns=["table", "column", "db_comment", "what_the_data_shows"])
cv.to_csv(os.path.join(R, "p1_comment_vs_data.csv"), index=False)
for t, g in cv.groupby("table"):
    p = os.path.join(R, f"p1_dict_extra_{t}.md")
    prev = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    add = ["", "## 字段注释与数据不符（2026-09-27 核对，`results/p1_comment_vs_data.csv`）", "", "| 字段 | 库内注释 | 数据显示 |", "|---|---|---|"]
    add += [f"| `{r.column}` | {r.db_comment} | {r.what_the_data_shows} |" for r in g.itertuples()]
    open(p, "w", encoding="utf-8").write(prev + "\n".join(add) + "\n")
print(cv.to_string(index=False))
