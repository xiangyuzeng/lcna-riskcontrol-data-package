#!/usr/bin/env python3
"""P1: build dictionary/<table>.md pages from information_schema results (no data values).

Inputs : results/p1_columns.csv, results/p1_indexes.csv, results/p0_schema_tables.csv,
         results/p1_table_roles.csv (hand-classified role per table, written by this script's caller),
         results/p1_json_keys_summary.csv (for t_access_log_0000 JSON structure)
Output : dictionary/<table>.md (one per risk-control table; shard families get one page on shard 0000),
         dictionary/_空表与遗留表.md for empty tables.
"""
import os
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R, D = os.path.join(PKG, "results"), os.path.join(PKG, "dictionary")
os.makedirs(D, exist_ok=True)

cols = pd.read_csv(os.path.join(R, "p1_columns.csv"), dtype=str).fillna("")
idx = pd.read_csv(os.path.join(R, "p1_indexes.csv"), dtype=str).fillna("")
size = pd.read_csv(os.path.join(R, "p0_schema_tables.csv"), dtype=str).fillna("")
roles = pd.read_csv(os.path.join(R, "p1_table_roles.csv"), dtype=str).fillna("")


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def size_row(t):
    g = "t_access_log_NNNN" if t.startswith("t_access_log_") else (
        "t_gateway_validate_log_NNNN" if t.startswith("t_gateway_validate_log_") else t)
    r = size[size.table_group == g]
    return r.iloc[0] if len(r) else None


empty_pages = []
for t, g in cols.groupby("TABLE_NAME", sort=True):
    role = roles[roles.table_name == t]
    role = role.iloc[0] if len(role) else None
    s = size_row(t)
    est = s["est_rows"] if s is not None else ""
    if s is not None and str(est) in ("0", "0.0") and not t.startswith("t_access_log"):
        empty_pages.append((t, s, g, role))
        continue
    lines = [f"# {t}", ""]
    if role is not None:
        lines += [f"- 角色：**{role.role}**", f"- 说明：{role.note}"]
    if s is not None:
        fam = " （同结构分片 64 张，此页以 0000 为代表）" if t.endswith("_0000") else ""
        lines += [f"- 表注释：{s.table_comment}{fam}",
                  f"- 规模（information_schema 估算）：{int(float(s.est_rows)):,} 行（单表），{s.size_mb} MB" if not fam else
                  f"- 规模（information_schema 估算，64 张合计）：{int(float(s.est_rows)):,} 行，{s.size_mb} MB；单表 {s.min_mb}–{s.max_mb} MB",
                  f"- 建表：{s.min_create_time}；最近写入（UPDATE_TIME）：{s.max_update_time or '—'}"]
    lines += ["- 来源：`sql/p1_columns.sql`、`sql/p1_indexes.sql`、`sql/p0_schema_tables.sql`（information_schema，未读数据）", "",
              "## 字段", "", "| # | 字段 | 类型 | 可空 | 键 | 默认 | 注释 |", "|---|---|---|---|---|---|---|"]
    for _, c in g.sort_values("ORDINAL_POSITION", key=lambda x: x.astype(int)).iterrows():
        lines.append(f"| {c.ORDINAL_POSITION} | `{c.COLUMN_NAME}` | {c.COLUMN_TYPE} | {c.IS_NULLABLE} | {c.COLUMN_KEY} | "
                     f"{esc(c.COLUMN_DEFAULT)} | {esc(c.COLUMN_COMMENT)} |")
    ig = idx[idx.TABLE_NAME == t]
    if len(ig):
        lines += ["", "## 索引", "", "| 索引 | 唯一 | 列（顺序） |", "|---|---|---|"]
        for iname, ii in ig.groupby("INDEX_NAME"):
            cols_ = ", ".join(ii.sort_values("SEQ_IN_INDEX", key=lambda x: x.astype(int)).COLUMN_NAME)
            lines.append(f"| `{iname}` | {'否' if ii.NON_UNIQUE.iloc[0] == '1' else '是'} | {cols_} |")
    extra = os.path.join(R, f"p1_dict_extra_{t}.md")
    if os.path.exists(extra):
        lines += ["", open(extra, encoding="utf-8").read().strip()]
    with open(os.path.join(D, f"{t}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

lines = ["# 空表与遗留表（information_schema 估算 0 行）", "",
         "这些表在 `luckyus_iriskcontrolservice` 中存在但估算行数为 0（或整组分片为空）。只记录结构，不读数据。", ""]
for t, s, g, role in empty_pages:
    lines += [f"## {t}", "", f"- 表注释：{s.table_comment}；建表 {s.min_create_time}；UPDATE_TIME {s.max_update_time or '—'}"]
    if role is not None:
        lines.append(f"- 角色：{role.role}；{role.note}")
    lines.append("- 字段：" + "、".join(f"`{c}`" for c in g.sort_values("ORDINAL_POSITION", key=lambda x: x.astype(int)).COLUMN_NAME))
    lines.append("")
with open(os.path.join(D, "_空表与遗留表.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"pages: {len(cols.TABLE_NAME.unique()) - len(empty_pages)} + empty-table page ({len(empty_pages)} tables)")
