#!/usr/bin/env python3
"""tk07: daily patrol for one America/New_York day -> one-page Markdown.
  MCP_DB_GATEWAY_SSE=<mcp-db-gateway SSE endpoint> python3 patrol.py --day 2026-09-24 [--scene LKUS_push] [--home-cc 1] [--out patrol.md]
Runs tk07_daily_patrol.sql through shard_runner.py (all shards, 16 per statement, one statement per 16 shards),
then prints: requests by final result (SMS rule: no email key), non-home-country PASS share, top online strategies,
top pre-online strategies and their 额外召回 (hits whose final result is PASS)."""
import argparse, os, subprocess, sys
import pandas as pd
from ny_day_bounds import ny_day_bounds_utc
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__)); PKG = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument("--day", required=True); ap.add_argument("--scene", default="LKUS_push"); ap.add_argument("--home-cc", default="1")
ap.add_argument("--name", default=None); ap.add_argument("--out", default=None); ap.add_argument("--top", type=int, default=10)
ap.add_argument("--no-query", action="store_true", help="only rebuild the page from an existing results/<name>.csv")
a = ap.parse_args()
name = a.name or f"patrol_{a.day.replace('-', '')}"
cmd = [sys.executable, os.path.join(HERE, "shard_runner.py"), "run", "--name", name, "--template", os.path.join(HERE, "tk07_daily_patrol.sql"),
       "--ny-days", f"{a.day}:{a.day}", "--batch", "16", "--param", f"scene={a.scene}", "--desc", f"daily patrol {a.day} NY"]
if not a.no_query and subprocess.call(cmd) != 0:
    sys.exit("runner failed")
d = pd.read_csv(os.path.join(PKG, "results", f"{name}.csv"), dtype=str); d["n"] = d.n.astype(float).astype(int)
home = set(a.home_cc.split(","))
r = d[(d.kind == "result") & (d.k3 == "0")]
tot = r.groupby("k1").n.sum()
pas = r[r.k1 == "PASS"]; nonhome = pas[~pas.k2.isin(home)].n.sum()
s, e, off = ny_day_bounds_utc(date.fromisoformat(a.day))
L = [f"# 每日巡检 {a.day}（{a.scene}，纽约日 = UTC [{s}, {e})）", "",
     f"- 短信请求（`$.para.email` 为空或不存在）：{int(tot.sum()):,}；PASS {int(tot.get('PASS', 0)):,} / REJECT {int(tot.get('REJECT', 0)):,} / REVIEW {int(tot.get('REVIEW', 0)):,}",
     f"- PASS 中非本国区号（{','.join('+' + h for h in home)} 以外）：{int(nonhome):,}（{nonhome / max(1, pas.n.sum()):.1%}）", ""]
for kind, title in (("online_hit", "在线策略命中"), ("preonline_hit", "预上线策略命中")):
    h = d[d.kind == kind]
    g = h.groupby(["k1", "k2"]).n.sum().reset_index().sort_values("n", ascending=False).head(a.top)
    extra = h[h.k3 == "PASS"].groupby("k1").n.sum()
    L += [f"## {title}（前 {a.top}；全部 LKUS_push 行，不分短信 / 邮件）", "", "| strategy_id | 处置 | 命中 | 其中最终 PASS |", "|---|---|---|---|"]
    L += [f"| `{x.k1}` | {x.k2} | {x.n:,} | {int(extra.get(x.k1, 0)):,} |" for x in g.itertuples()] + [""]
md = "\n".join(L) + "\n"
print(md)
if a.out:
    open(a.out, "w", encoding="utf-8").write(md)
