#!/usr/bin/env python3
"""P2: generate the whole-table export SELECT for every rule-engine definition table from the live column list
(results/p1_columns.csv), applying the export rules:
  * columns whose name contains key/secret/token/passw/sign/credential/appid are not exported;
  * operator columns (operator, create_/modify_/update_ name/user/emp/id) are replaced by '<已屏蔽:操作人>' when non-empty;
  * every free-text cell (char/varchar/text/json) is replaced as a whole by '<已屏蔽:N字符>' when it contains a full IPv4,
    an email, >=7 consecutive digits, '://', a domain or a domain:port.
Writes _local_only/tpl/config_<name>.sql (the runner saves the executed copy under sql/)."""
import os, re
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cols = pd.read_csv(os.path.join(PKG, "results", "p1_columns.csv"))
SECRET_LIKE = re.compile(r"key|secret|token|passw|sign|credential|appid", re.I)
OPER = re.compile(r"^(operator|(create|modify|update)_(name|user|emp|id|by))$", re.I)
PAT = (r"[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|[0-9]{7,}|://|"
       r"[A-Za-z0-9-]+\\.(com|net|org|io|us|cn|internal|local|aws)\\b|[A-Za-z][A-Za-z0-9-]*\\.[A-Za-z0-9.-]+:[0-9]{2,5}")
TABLES = {t: "config_" + t.replace("t_rms_engine_", "") for t in sorted(cols.TABLE_NAME.unique()) if t.startswith("t_rms_engine_")}
TABLES["t_scene"] = "config_legacy_scene"
out = os.path.join(PKG, "_local_only", "tpl")
for t, name in TABLES.items():
    sel, dropped, masked = [], [], []
    for r in cols[cols.TABLE_NAME == t].sort_values("ORDINAL_POSITION").itertuples():
        c, ty = r.COLUMN_NAME, str(r.COLUMN_TYPE).lower()
        if SECRET_LIKE.search(c):
            dropped.append(c); continue
        if OPER.match(c):
            masked.append(c)
            sel.append(f"CASE WHEN `{c}` IS NULL OR CAST(`{c}` AS CHAR) = '' THEN `{c}` ELSE '<已屏蔽:操作人>' END AS `{c}`"); continue
        if re.match(r"(var)?char|.*text|json", ty):
            sel.append(f"CASE WHEN `{c}` REGEXP '{PAT}' THEN CONCAT('<已屏蔽:', CHAR_LENGTH(`{c}`), '字符>') ELSE `{c}` END AS `{c}`")
        else:
            sel.append(f"`{c}`")
    sql = (f"-- export of luckyus_iriskcontrolservice.{t}; dropped (secret-like): {dropped or '-'}; operator columns masked: {masked or '-'}\n"
           "SELECT /*+ MAX_EXECUTION_TIME(10000) */\n  " + ",\n  ".join(sel) +
           f"\nFROM luckyus_iriskcontrolservice.{t}\nORDER BY `id`\nLIMIT 5000\n")
    open(os.path.join(out, name + ".sql"), "w", encoding="utf-8").write(sql)
    print(f"{name}: {len(sel)} columns, dropped={dropped}, operator-masked={masked}")
