#!/usr/bin/env python3
"""P6 mechanical checks (no DB):
 1. every `results/...` / `sql/...` / `dictionary/...` / `toolkit/...` path cited in the pages exists;
 2. every integer >= 100 written on README / 00-06 pages occurs in some results/*.csv (or cited .md) -> unmatched list;
 3. package contract (prompt section 6) files exist;
 4. the gateway host (read at run time from the environment, never printed) does not occur in any package file.
Writes results/p6_checks.csv (counts + unmatched numbers for manual review)."""
import glob, os, re, sys
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(PKG)
pages = ["README.md"] + sorted(glob.glob("0[0-6]_*.md")) + ["toolkit/README.md", "NEXT_RUN_改进建议.md"]
out = []
# 1 cited paths
missing = []
for p in pages:
    for m in re.findall(r"`((?:results|sql|dictionary|toolkit)/[^`\s]+)`", open(p, encoding="utf-8").read()):
        if "<" in m:                     # placeholder such as sql/<name>.sql
            continue
        pat = m.replace("<", "*").replace(">", "*").replace("…", "*")
        pat = re.sub(r"\*+", "*", pat)
        if not glob.glob(pat) and not glob.glob(pat + "*"):
            missing.append(f"{p}: {m}")
out.append(("cited paths missing", len(missing), "; ".join(missing[:30])))
# 2 numbers
corpus = []
for f in glob.glob("results/**/*.csv", recursive=True) + glob.glob("results/**/*.md", recursive=True):
    corpus.append(open(f, encoding="utf-8", errors="replace").read())
corpus = "\n".join(corpus)
num_tokens = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?", corpus))
num_tokens |= {m.replace(",", "") for m in re.findall(r'"(\d{1,3}(?:,\d{3})+)"', corpus)}   # quoted "3,390" cells
num_tokens |= {str(int(round(float(x)))) for x in list(num_tokens) if "." in x}    # pages show rounded values
unmatched = []
for p in pages:
    txt = open(p, encoding="utf-8").read()
    for n in re.findall(r"(?<![\w.\-_/])\d{1,3}(?:,\d{3})+(?![\d%])|(?<![\w.\-_/:])\d{3,}(?![\d%.:\-_])", txt):
        v = n.replace(",", "")
        if re.fullmatch(r"20[2-3]\d", v) or len(v) >= 8:
            continue
        if v not in num_tokens and v + ".0" not in num_tokens:
            unmatched.append(f"{p} → {n}")
out.append(("integers >= 100 not found verbatim in results/", len(unmatched), "; ".join(sorted(set(unmatched)))))
# 3 contract
need = ["README.md", "MANIFEST.md", "RUN_LOG.md", "NEXT_RUN_改进建议.md", "00_环境清单.md", "01_数据源与表清单.md", "02_线上配置导出.md",
        "04_数据问题结论.md", "05_取数手册与常见坑.md", "06_评估指标计算手册.md", "toolkit/README.md", "toolkit/privacy_scan.py",
        "toolkit/ny_day_bounds.py", "toolkit/shard_runner.py"]
miss = [f for f in need if not os.path.exists(f)] + ([] if glob.glob("03_近7日数据画像_*.md") else ["03_近7日数据画像_*.md"]) \
       + ([] if glob.glob("dictionary/*.md") else ["dictionary/"]) + ([] if glob.glob("sql/*.sql") else ["sql/"]) \
       + ([] if glob.glob("results/*.csv") else ["results/"]) + ([] if glob.glob("toolkit/*.sql") else ["toolkit/*.sql"])
out.append(("contract files missing", len(miss), "; ".join(miss)))
# 4 endpoint leak
url = os.environ.get("MCP_DB_GATEWAY_SSE", "")
host = re.sub(r"^\w+://", "", url).split("/")[0]
bits = [b for b in {url, host, host.split(":")[0]} if b]
hits = 0
for f in glob.glob("**/*", recursive=True):
    if os.path.isfile(f) and not f.startswith("_local_only"):
        t = open(f, "rb").read()
        hits += any(b.encode() in t for b in bits)
out.append(("files containing the gateway endpoint", hits if bits else -1, "endpoint not provided" if not bits else ""))
# 5 absolute paths / hosts of this machine or its network: patterns are read at run time from _local_only/ (never shipped)
lp = os.path.join("_local_only", "leak_patterns.txt")
pats = [l.strip() for l in open(lp, encoding="utf-8") if l.strip()] if os.path.exists(lp) else []
pats.append(r"~/")                                                     # home-relative paths
leak = []
for f in glob.glob("**/*", recursive=True):
    if os.path.isfile(f) and not f.startswith("_local_only") and f not in ("sql/local/p6_checks.py", "results/p6_checks.csv") and f.endswith((".md", ".csv", ".sql", ".py", ".txt", ".sh", ".json")):
        t = open(f, encoding="utf-8", errors="replace").read()
        for pat in pats:
            if re.search(pat, t):
                leak.append(f"{f}: {pat}")
out.append(("files with absolute paths / internal hosts", len(leak) if len(pats) > 1 else -1, "; ".join(leak[:20]) or ("" if len(pats) > 1 else "_local_only/leak_patterns.txt missing")))
pyc = [os.path.join(r_, d) for r_, ds_, _ in os.walk(".") for d in ds_ if d == "__pycache__" and not r_.startswith("./_local_only")]
out.append(("__pycache__ folders (carry absolute paths; delete before hand-over)", len(pyc), "; ".join(pyc)))
# 6 README DR totals = statuses parsed from 04
st = re.findall(r"^- \*\*新状态\*\*：(\S+?)(?:（|$)", open("04_数据问题结论.md", encoding="utf-8").read(), flags=re.M)
from collections import Counter
cnt = Counter(st)
rd_ = open("README.md", encoding="utf-8").read()
m = re.search(r"合计（由脚本从 04 的「新状态」行计算）：(.+)", rd_)
exp = "、".join(f"{k} {v}" for k, v in sorted(cnt.items()))
out.append(("README DR totals equal 04 statuses", 0 if (m and m.group(1).strip().startswith(exp)) else 1, f"04: {exp} | README: {m.group(1) if m else 'missing'}"))
# 7 one metric, one value: every registry metric's label pattern must reproduce the registry value on every page
sys.path.insert(0, os.path.join(PKG, "sql", "local"))
import metrics  # noqa: E402
metrics.write()
bad7 = []
for mid, m in metrics.M.items():
    if not m["pattern"]:
        continue
    for p in pages:
        for mt in re.finditer(m["pattern"], open(p, encoding="utf-8").read()):
            got = "/".join(mt.groups()) if len(mt.groups()) > 1 else mt.group(1)
            if got.replace(",", "") != m["value"].replace(",", ""):
                bad7.append(f"{p}: {mid} page={got} registry={m['value']}")
out.append(("metric values differing from the registry (one metric, one value)", len(bad7), "; ".join(bad7[:30])))
# 8 canonical wording: the upush date column is described only one way; deliver_time never named as its basis
bad8 = []
for p in pages:
    t_ = open(p, encoding="utf-8").read()
    if "statistic_date" in t_ and metrics.T["upush_date"] not in t_:
        bad8.append(f"{p}: statistic_date without the canonical sentence")
    if "deliver_time" in t_:
        bad8.append(f"{p}: mentions deliver_time")
out.append(("non-canonical upush date wording", len(bad8), "; ".join(bad8)))
import csv
with open("results/p6_checks.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["check", "count", "detail"]); w.writerows(out)
for c, n, d in out:
    print(f"{c}: {n}" + (f"\n   {d[:1500]}" if d else ""))
