#!/usr/bin/env python3
"""P6: update toolkit/README.md for this package. Starts from the Part 4 README text (kept in _local_only/part4_README.md the
first time this runs), replaces §4 (tests) with this run's results/toolkit_tests/_test_summary.csv, adds the tk11 rows and a
section listing every change this package made to its copy of the toolkit."""
import os, re, shutil, subprocess, sys
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = os.path.join(PKG, "_local_only", "part4_README.md")
dst = os.path.join(PKG, "toolkit", "README.md")
if not os.path.exists(src):
    shutil.copy(dst, src)
t = open(src, encoding="utf-8").read()
ts = pd.read_csv(os.path.join(PKG, "results", "toolkit_tests", "_test_summary.csv"))
picks = dict(l.split("=", 1) for l in subprocess.run([sys.executable, os.path.join(PKG, "sql", "local", "p5_pick.py")], capture_output=True, text=True, check=True).stdout.split("\n") if "=" in l)
esc = lambda v: "" if pd.isna(v) else str(v).replace("|", "\\|")
t = re.sub(r"^> 2026-09-27 更新。.*$", f"> 2026-10-10 更新（RC_data_20261010-0013）。Part 4 原文 + 本包的改动（§6）。每个模板都用本包数据跑过一次，并与另一种算法（E1 本地抽取或独立 SQL）逐项核对：{int(ts.equal.sum())}/{len(ts)} 项一致（`results/toolkit_tests/_test_summary.csv`）。", t, count=1, flags=re.M)
t = t.replace("| `tk_merge.py` | tk01–tk05 的合并步骤（跨分片汇总） |",
              "| `tk11_bypass_watch.sql` | **新**（2026-10-10）：一条策略的目标区号里，按纽约日 × 区号 × IP 类别 × 是否被它命中 × 最终结果计数——没被命中而 PASS 的就是「绕过」 |\n| `tk_merge.py` | tk01–tk05 的合并步骤（跨分片汇总） |")
i, j = t.index("## 4. 本次测试"), t.index("## 5. 每个模板的要点")
sec4 = ["## 4. 本次测试（纽约日 2026-10-03…10-09；tk01 为 10-09 与前 7 天同一时段，tk06 / tk07 / tk09 为 10-09，tk10 为 43Na 纽约日 09-22…10-09 与 bYXa / WvNG 纽约日 10-02…10-09，tk11 为 bYXa；挑选的策略来自数据："
        + "、".join(f"{k}=`{v}`" for k, v in picks.items() if k in ("PRE", "PRE_PASS_CLASS", "ON", "TK06_STRATEGY")) + "）", "",
        "| 测试 | 模板结果 | 对照 | 一致 | 备注 |", "|---|---|---|---|---|"]
sec4 += [f"| {esc(r.test)} | {esc(r.toolkit)} | {esc(r.reference)} | {'是' if r.equal else '**否**'} | {esc(r.note)} |" for r in ts.itertuples()]
sec4 += ["", "测试原始输出：`results/toolkit_tests/` 与 `results/dr030_tk10_43na.csv`、`results/dr034_tk10_*.csv`、`results/dr031_tk11_bYXa.csv`；每个测试实际执行的 SQL：`sql/toolkit_tests/`、`sql/dr0*.sql`；比对脚本 `sql/local/p5_toolkit_tests.py`。", "", ""]
t = t[:i] + "\n".join(sec4) + t[j:]
t = t.rstrip("\n") + "\n- **tk11**：参数 `strategy_id`、`target_ccs`（从配置导出里这条策略的 countryCode INCLUDE 规则读，不手写）、`us_values`（美国在 `realIpCountry` 里的取值，如 `'美国'`）、`sms_only`；`ip_class`：unknown / us / eq_phone（IP 国家 = 号码国家）/ other；`s_hit`：online / preonline / none。\n"
t += "\n".join(["", "## 6. 本包（2026-10-10）对 Part 4 原文的改动", "",
                "本目录 22 个文件：Part 4 的 19 个（按原文写入后核对 sha256，19/19 一致；之后只改了 `shard_runner.py` 与 `README.md` 两个，其余 17 个未改，`privacy_allowlist.txt` 也未改）+ 2026-09-27 包原样带来的 `privacy_scan.py`、`ny_day_bounds.py` + 新模板 `tk11_bypass_watch.sql`。", "",
                "| 文件 | 改动 | 原因 |", "|---|---|---|",
                "| `shard_runner.py` | 新增 `prod_window_ok()`：命令开始时先检查一次（不在窗口就记一行日志后退出，什么也不发），之后每条语句发送前再检查；纽约时间不在 22:00–05:30 就不发送 | 团队 2026-10-08 规定生产库批量取数只在纽约时间 22:00–06:00；05:30 留 30 分钟余量 |",
                "| `shard_runner.py` | EXPLAIN 门槛：`Extra` 为 `No matching min/max row`、`Impossible WHERE` 或 `no matching row in const table`（窗口内没有行、什么也不扫）时当作「空」放行；`type = ALL` 的大表扫描仍拒绝；`run` 按窗口逐个 EXPLAIN，直到遇到一个正常走索引的窗口为止（第一个窗口为空时不再只看它） | 2026-09-27 安静时段的新鲜度检查曾被门槛误拦；只看第一个窗口会在它为空时漏检后面的窗口 |",
                "| `tk11_bypass_watch.sql` | 新模板；短信判定与其它模板一致（`COALESCE(JSON_UNQUOTE(JSON_EXTRACT(para,'$.email')),'') = ''`），对齐后两种口径（`sms_only=1/0`）在纽约日 10-02…10-09 重跑，与 E1 逐格一致 | 备份同学每天盯 10-08 新策略有没有被绕过 |",
                "| `README.md` | 本节、§1 的 tk11 一行、§4 测试表、§5 的 tk11 要点 | 记录改动 |", "",
                "改动后自测：`test_guard.py` 仍为 27 + 13 条、0 失败；EXPLAIN 门槛三种情况（走索引 → 通过、空区间 → 「空」、全表扫描 → 拒绝）都按预期。", ""])
open(dst, "w", encoding="utf-8").write(t)
print("toolkit README written; tests", int(ts.equal.sum()), "/", len(ts))
